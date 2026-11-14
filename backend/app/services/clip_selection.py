"""AI candidate clip selection.

The transcript is split into overlapping context windows (about three
minutes by default) so an hour-long recording is never sent to the local
LLM in one prompt. Every window keeps absolute source timestamps.

The model returns structured JSON. Application code then:

* validates ranges against the source duration,
* snaps boundaries to word and transcript-segment boundaries,
* rejects clips that would start or end mid-sentence,
* computes a deterministic weighted "clip potential" score,
* removes heavily overlapping duplicates,
* limits the result to the configured number of clips.

The LLM never decides the final score. It only proposes moments and rough
component ratings; the weighting and conciseness calculation happen here.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from pydantic import ValidationError

from app.config import Settings
from app.schemas.clip_selection import LLMClip, LLMClipScores
from app.schemas.transcript import Transcript, TranscriptSegment, TranscriptWord
from app.services.ollama import OllamaClient, OllamaError, OllamaMalformedResponse

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float], None]

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "clip_selection.txt"

SYSTEM_PROMPT = (
    "You are a video editor selecting self-contained short-form moments. "
    "Return only JSON that matches the provided schema. Use absolute source "
    "timestamps in seconds. Never invent timestamps outside the provided "
    "context window. Reject moments that begin or end mid-sentence or that "
    "need missing context."
)

# Two proposals are treated as the same moment when their intersection over
# union is at least this value.
DEDUP_IOU_THRESHOLD = 0.55

# A short proposal that is mostly contained inside a longer one is a duplicate
# even when the union is large. Compare the intersection to the shorter clip.
DEDUP_CONTAINMENT_THRESHOLD = 0.75


class ClipSelectionError(Exception):
    """A clip-selection failure with a user-facing message."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class TranscriptChunk:
    """One overlapping context window with absolute source timestamps."""

    start: float
    end: float
    segments: tuple[TranscriptSegment, ...]

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def words(self) -> tuple[TranscriptWord, ...]:
        words = [word for segment in self.segments for word in segment.words]
        words.sort(key=lambda word: (word.start, word.end))
        return tuple(words)


@dataclass(frozen=True)
class ClipCandidate:
    """A validated, boundary-refined clip proposal."""

    start: float
    end: float
    title: str
    hook: str
    reason: str
    score: float
    component_scores: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class ClipSelector(Protocol):
    """Selects candidate clips from a stored transcript."""

    model_name: str

    def select(
        self,
        transcript: Transcript,
        duration_seconds: float,
        on_progress: ProgressCallback | None = None,
    ) -> list[ClipCandidate]:
        """Return refined, deduplicated, score-ordered candidates."""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _clean_text(value: str | None, *, limit: int = 2000) -> str:
    if not value:
        return ""
    cleaned = " ".join(str(value).split())
    return cleaned[:limit].strip()


def _report(callback: ProgressCallback | None, fraction: float) -> None:
    if callback is None:
        return
    callback(_clamp(float(fraction), 0.0, 1.0))


def build_chunks(
    segments: Sequence[TranscriptSegment],
    window_seconds: float,
    overlap_seconds: float,
) -> list[TranscriptChunk]:
    """Group segments into overlapping windows without re-basing timestamps.

    Windows start on a segment boundary and include every segment that starts
    before the target window end. The next window starts ``overlap_seconds``
    before the target end, so context that spans a boundary is visible to the
    model twice.
    """
    usable = [segment for segment in segments if segment.end > segment.start]
    if not usable:
        return []

    window = max(1.0, float(window_seconds))
    overlap = max(0.0, min(float(overlap_seconds), window - 1.0))

    chunks: list[TranscriptChunk] = []
    index = 0
    while index < len(usable):
        chunk_start = usable[index].start
        target_end = chunk_start + window

        end_index = index
        while end_index < len(usable) and usable[end_index].start < target_end:
            end_index += 1
        if end_index == index:
            end_index = index + 1

        chunk_segments = usable[index:end_index]
        chunk_end = max(segment.end for segment in chunk_segments)
        chunks.append(
            TranscriptChunk(
                start=chunk_start,
                end=chunk_end,
                segments=tuple(chunk_segments),
            )
        )

        if end_index >= len(usable):
            break

        next_start = max(chunk_start + 1.0, target_end - overlap)
        next_index = index
        while next_index < len(usable) and usable[next_index].start < next_start:
            next_index += 1
        if next_index <= index:
            next_index = index + 1
        index = next_index

    return chunks


def load_prompt_template(path: Path | None = None) -> str:
    """Read the editable selection prompt.

    The file is read on every selection so it can be tuned without a restart.
    """
    prompt_path = path or PROMPT_PATH
    try:
        return prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ClipSelectionError(
            "clip_prompt_missing",
            f"The clip selection prompt could not be read from {prompt_path}. "
            "Restore backend/app/prompts/clip_selection.txt and retry.",
        ) from exc


def render_prompt(
    template: str,
    chunk: TranscriptChunk,
    duration_seconds: float,
    settings: Settings,
    max_candidates: int,
) -> str:
    """Render the prompt with absolute timestamps and the current settings."""
    lines = [
        f"[{segment.start:.2f} - {segment.end:.2f}] {_clean_text(segment.text)}"
        for segment in chunk.segments
    ]
    transcript_text = "\n".join(lines)
    try:
        return template.format(
            duration_seconds=f"{duration_seconds:.1f}",
            window_start=f"{chunk.start:.1f}",
            window_end=f"{chunk.end:.1f}",
            min_clip_seconds=f"{settings.min_clip_seconds:.0f}",
            max_clip_seconds=f"{settings.max_clip_seconds:.0f}",
            hard_min_seconds=f"{settings.clip_hard_min_seconds:.0f}",
            hard_max_seconds=f"{settings.clip_hard_max_seconds:.0f}",
            max_candidates=max_candidates,
            transcript=transcript_text,
        )
    except (KeyError, ValueError) as exc:
        raise ClipSelectionError(
            "clip_prompt_invalid",
            "The clip selection prompt contains an unknown placeholder. "
            "Check backend/app/prompts/clip_selection.txt.",
        ) from exc


def build_response_schema(max_candidates: int) -> dict[str, Any]:
    """JSON schema passed to Ollama's structured-output ``format`` field."""
    return {
        "type": "object",
        "properties": {
            "clips": {
                "type": "array",
                "maxItems": max_candidates,
                "items": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "number"},
                        "end": {"type": "number"},
                        "title": {"type": "string"},
                        "hook": {"type": "string"},
                        "reason": {"type": "string"},
                        "scores": {
                            "type": "object",
                            "properties": {
                                "hook": {"type": "number"},
                                "clarity": {"type": "number"},
                                "standalone": {"type": "number"},
                                "emotion_or_interest": {"type": "number"},
                                "payoff": {"type": "number"},
                            },
                            "required": [
                                "hook",
                                "clarity",
                                "standalone",
                                "emotion_or_interest",
                                "payoff",
                            ],
                        },
                    },
                    "required": [
                        "start",
                        "end",
                        "title",
                        "hook",
                        "reason",
                        "scores",
                    ],
                },
            }
        },
        "required": ["clips"],
    }


def _snap_to_word_start(words: Sequence[TranscriptWord], value: float) -> float:
    if not words:
        return value
    for word in words:
        if word.start <= value <= word.end:
            return word.start
    return min((word.start for word in words), key=lambda start: abs(start - value))


def _snap_to_word_end(words: Sequence[TranscriptWord], value: float) -> float:
    if not words:
        return value
    for word in words:
        if word.start <= value <= word.end:
            return word.end
    return min((word.end for word in words), key=lambda end: abs(end - value))


def _segment_index_at_or_after(
    segments: Sequence[TranscriptSegment], value: float
) -> int:
    for index, segment in enumerate(segments):
        if segment.end > value:
            return index
    return len(segments) - 1


def _segment_index_at_or_before(
    segments: Sequence[TranscriptSegment], value: float
) -> int:
    for index in range(len(segments) - 1, -1, -1):
        if segments[index].start < value:
            return index
    return 0


def _range_duration(
    segments: Sequence[TranscriptSegment], start_index: int, end_index: int
) -> float:
    return segments[end_index].end - segments[start_index].start


def _fit_segment_range(
    segments: Sequence[TranscriptSegment],
    start_index: int,
    end_index: int,
    settings: Settings,
) -> tuple[float, float] | None:
    """Fit a whole-segment range inside the hard duration limits.

    Whole transcript segments are used so a clip never begins or ends in the
    middle of a sentence. If no combination of whole segments fits, the
    proposal is rejected rather than cutting mid-sentence.
    """
    hard_min = settings.clip_hard_min_seconds
    hard_max = settings.clip_hard_max_seconds
    target_min = settings.min_clip_seconds
    target_max = settings.max_clip_seconds

    def fits_target(i: int, j: int) -> bool:
        duration = _range_duration(segments, i, j)
        return hard_min <= duration <= target_max

    def fits_hard(i: int, j: int) -> bool:
        duration = _range_duration(segments, i, j)
        return hard_min <= duration <= hard_max

    # Too long: trim toward the target maximum while preferring to preserve
    # a complete ending/payoff (trim from the start first when possible).
    if _range_duration(segments, start_index, end_index) > target_max:
        candidate: tuple[int, int] | None = None
        for start in range(start_index, end_index + 1):
            if fits_target(start, end_index):
                candidate = (start, end_index)
                break
        if candidate is None:
            for end in range(end_index, start_index - 1, -1):
                if fits_target(start_index, end):
                    candidate = (start_index, end)
                    break
        if candidate is None:
            for start in range(start_index, end_index + 1):
                if fits_hard(start, end_index):
                    candidate = (start, end_index)
                    break
        if candidate is None:
            for end in range(end_index, start_index - 1, -1):
                if fits_hard(start_index, end):
                    candidate = (start_index, end)
                    break
        if candidate is None:
            return None
        start_index, end_index = candidate

    # Too short: extend forward, then backward, without exceeding the hard max.
    if _range_duration(segments, start_index, end_index) < target_min:
        while end_index + 1 < len(segments):
            new_end = segments[end_index + 1].end
            if new_end - segments[start_index].start > hard_max:
                break
            end_index += 1
            if new_end - segments[start_index].start >= target_min:
                break

        if _range_duration(segments, start_index, end_index) < target_min:
            while start_index - 1 >= 0:
                new_start = segments[start_index - 1].start
                if segments[end_index].end - new_start > hard_max:
                    break
                start_index -= 1
                if segments[end_index].end - new_start >= target_min:
                    break

    duration = _range_duration(segments, start_index, end_index)
    if duration < hard_min or duration > hard_max:
        return None
    return segments[start_index].start, segments[end_index].end


def _normalized_score(value: Any) -> float:
    number = _finite_float(value)
    if number is None:
        number = 5.0
    return _clamp(number / 10.0, 0.0, 1.0)


def _conciseness(duration: float, settings: Settings) -> float:
    """Reward clips inside the target range, gently penalize the hard edges."""
    target_min = settings.min_clip_seconds
    target_max = settings.max_clip_seconds
    hard_min = settings.clip_hard_min_seconds
    hard_max = settings.clip_hard_max_seconds

    if target_min <= duration <= target_max:
        return 1.0
    if duration < target_min:
        span = max(1e-6, target_min - hard_min)
        return max(0.6, 1.0 - 0.4 * (target_min - duration) / span)
    span = max(1e-6, hard_max - target_max)
    return max(0.6, 1.0 - 0.4 * (duration - target_max) / span)


def score_candidate(
    *,
    duration: float,
    scores: LLMClipScores | None,
    settings: Settings,
) -> tuple[float, dict[str, Any]]:
    """Compute the deterministic weighted clip-potential score (0-100)."""
    raw = scores or LLMClipScores()
    clarity = (_normalized_score(raw.clarity) + _normalized_score(raw.standalone)) / 2.0
    components = {
        "hook": round(_normalized_score(raw.hook) * 100.0, 2),
        "clarity": round(clarity * 100.0, 2),
        "payoff": round(_normalized_score(raw.payoff) * 100.0, 2),
        "emotion_or_interest": round(
            _normalized_score(raw.emotion_or_interest) * 100.0, 2
        ),
        "conciseness": round(_conciseness(duration, settings) * 100.0, 2),
    }

    weights = settings.clip_score_weights
    weighted = sum(
        weights[key] * (components[key] / 100.0)
        for key in weights
        if key in components
    )
    component_scores: dict[str, Any] = dict(components)
    component_scores["weights"] = {key: round(value, 4) for key, value in weights.items()}
    component_scores["method"] = "deterministic weighted clip potential"
    return round(weighted * 100.0, 2), component_scores


def build_candidate(
    raw_clip: LLMClip,
    chunk: TranscriptChunk,
    source_duration: float,
    settings: Settings,
) -> ClipCandidate | None:
    """Validate one model proposal and refine its boundaries."""
    raw_start = _finite_float(raw_clip.start)
    raw_end = _finite_float(raw_clip.end)
    if raw_start is None or raw_end is None:
        return None

    # A model may hallucinate a timestamp far outside the context window it
    # was shown. Keep the proposal inside that window and the source.
    window_start = max(0.0, min(chunk.start, source_duration))
    window_end = max(0.0, min(chunk.end, source_duration))
    if window_end <= window_start:
        return None

    raw_start = _clamp(raw_start, window_start, window_end)
    raw_end = _clamp(raw_end, window_start, window_end)
    if raw_end <= raw_start:
        return None

    words = chunk.words
    start = _snap_to_word_start(words, raw_start)
    end = _snap_to_word_end(words, raw_end)
    if end <= start:
        return None

    start_index = _segment_index_at_or_after(chunk.segments, start)
    end_index = _segment_index_at_or_before(chunk.segments, end)
    if end_index < start_index:
        return None

    fitted = _fit_segment_range(chunk.segments, start_index, end_index, settings)
    if fitted is None:
        return None

    refined_start, refined_end = fitted
    refined_start = _clamp(refined_start, 0.0, source_duration)
    refined_end = _clamp(refined_end, 0.0, source_duration)
    duration = refined_end - refined_start
    if duration < settings.clip_hard_min_seconds or duration > settings.clip_hard_max_seconds:
        return None

    score, component_scores = score_candidate(
        duration=duration,
        scores=raw_clip.scores,
        settings=settings,
    )

    title = _clean_text(raw_clip.title, limit=255) or "Untitled moment"
    hook = _clean_text(raw_clip.hook)
    reason = _clean_text(raw_clip.reason)

    return ClipCandidate(
        start=round(refined_start, 3),
        end=round(refined_end, 3),
        title=title,
        hook=hook,
        reason=reason,
        score=score,
        component_scores=component_scores,
    )


def candidates_from_payload(
    payload: dict[str, Any],
    chunk: TranscriptChunk,
    source_duration: float,
    settings: Settings,
) -> list[ClipCandidate]:
    """Parse one model response, skipping malformed clips instead of failing."""
    if not isinstance(payload, dict):
        logger.warning(
            "Ignoring clip selection for window %.1f-%.1f: response was not an object",
            chunk.start,
            chunk.end,
        )
        return []

    raw_clips = payload.get("clips")
    if not isinstance(raw_clips, list):
        logger.warning(
            "Ignoring clip selection for window %.1f-%.1f: 'clips' was not a list",
            chunk.start,
            chunk.end,
        )
        return []

    candidates: list[ClipCandidate] = []
    for item in raw_clips:
        try:
            raw_clip = LLMClip.model_validate(item)
        except ValidationError as exc:
            logger.warning(
                "Skipping a malformed clip for window %.1f-%.1f: %s",
                chunk.start,
                chunk.end,
                exc,
            )
            continue
        try:
            candidate = build_candidate(raw_clip, chunk, source_duration, settings)
        except Exception:  # noqa: BLE001 - one bad clip must not stop selection
            logger.exception(
                "Could not validate a clip proposal for window %.1f-%.1f",
                chunk.start,
                chunk.end,
            )
            continue
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _iou(left: ClipCandidate, right: ClipCandidate) -> float:
    intersection = max(0.0, min(left.end, right.end) - max(left.start, right.start))
    if intersection <= 0:
        return 0.0
    union = left.duration + right.duration - intersection
    return intersection / union if union > 0 else 0.0


def _containment(left: ClipCandidate, right: ClipCandidate) -> float:
    """Intersection relative to the shorter clip, to catch nested duplicates."""
    intersection = max(0.0, min(left.end, right.end) - max(left.start, right.start))
    shorter = min(left.duration, right.duration)
    return intersection / shorter if shorter > 0 else 0.0


def deduplicate_candidates(
    candidates: Sequence[ClipCandidate],
    max_clips: int,
    *,
    iou_threshold: float = DEDUP_IOU_THRESHOLD,
    containment_threshold: float = DEDUP_CONTAINMENT_THRESHOLD,
) -> list[ClipCandidate]:
    """Keep the highest-scoring proposal from each overlapping group.

    Two clips are duplicates when they overlap heavily (IoU) or when one is
    mostly contained inside the other. Score ties prefer the shorter clip,
    which is usually the tighter short-form cut.
    """
    ordered = sorted(
        candidates,
        key=lambda item: (-item.score, item.duration, item.start, item.end),
    )
    kept: list[ClipCandidate] = []
    for candidate in ordered:
        if any(
            _iou(candidate, existing) >= iou_threshold
            or _containment(candidate, existing) >= containment_threshold
            for existing in kept
        ):
            continue
        kept.append(candidate)
        if len(kept) >= max_clips:
            break
    return sorted(kept, key=lambda item: (item.start, item.end))


class OllamaClipSelector:
    """Clip selection through a locally running Ollama instance."""

    def __init__(
        self,
        settings: Settings,
        *,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.model_name = settings.ollama_model
        self._client_factory = client_factory or (lambda: OllamaClient(settings))

    def select(
        self,
        transcript: Transcript,
        duration_seconds: float,
        on_progress: ProgressCallback | None = None,
    ) -> list[ClipCandidate]:
        if not transcript.has_speech or not transcript.segments:
            return []

        chunks = build_chunks(
            transcript.segments,
            self.settings.clip_window_seconds,
            self.settings.clip_window_overlap_seconds,
        )
        if not chunks:
            return []

        template = load_prompt_template()
        schema = build_response_schema(self.settings.clip_max_candidates_per_chunk)
        client = self._client_factory()

        try:
            ensure_ready = getattr(client, "ensure_ready", None)
            if callable(ensure_ready):
                try:
                    ensure_ready()
                except OllamaError as exc:
                    raise ClipSelectionError(exc.code, exc.message) from exc

            candidates: list[ClipCandidate] = []
            total = len(chunks)
            for index, chunk in enumerate(chunks):
                prompt = render_prompt(
                    template,
                    chunk,
                    duration_seconds,
                    self.settings,
                    self.settings.clip_max_candidates_per_chunk,
                )
                try:
                    payload = client.chat_json(
                        system=SYSTEM_PROMPT,
                        user=prompt,
                        schema=schema,
                    )
                except OllamaMalformedResponse as exc:
                    logger.warning(
                        "Skipping clip window %.1f-%.1f: %s",
                        chunk.start,
                        chunk.end,
                        exc.message,
                    )
                    _report(on_progress, (index + 1) / total)
                    continue
                except OllamaError as exc:
                    raise ClipSelectionError(exc.code, exc.message) from exc

                if not isinstance(payload, dict):
                    logger.warning(
                        "Skipping clip window %.1f-%.1f: response was not an object",
                        chunk.start,
                        chunk.end,
                    )
                    _report(on_progress, (index + 1) / total)
                    continue

                candidates.extend(
                    candidates_from_payload(
                        payload,
                        chunk,
                        duration_seconds,
                        self.settings,
                    )
                )
                _report(on_progress, (index + 1) / total)

            return deduplicate_candidates(candidates, self.settings.max_clips)
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
