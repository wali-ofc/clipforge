"""Compact clip selection: deterministic shortlist plus one small LLM request.

The legacy selector sent every transcript window to Ollama one at a time and
asked for verbose JSON for each one. On CPU-only hardware that cost grew
linearly with video length and dominated the whole pipeline.

This module keeps the same external contract (``select`` returns
``ClipCandidate`` objects) but changes the shape of the work:

1. :mod:`app.services.clip_prescore` deterministically shortlists a handful of
   self-contained regions.
2. One compact request ranks the strongest of those regions.
3. Every returned timestamp is validated against the region it came from, so
   the model can never invent a moment or drift into a different topic.

The static instruction block is identical for every request and comes before
the variable candidate data, so a warm Ollama slot can reuse its prompt cache.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from pydantic import ValidationError

from app.config import Settings
from app.schemas.clip_selection import CompactClipProposal
from app.schemas.transcript import Transcript
from app.services.clip_prescore import CandidateRegion, generate_candidate_regions
from app.services.clip_selection import (
    ClipCandidate,
    ClipSelectionError,
    deduplicate_candidates,
)
from app.services.ollama import (
    OllamaChatStats,
    OllamaClient,
    OllamaError,
    OllamaMalformedResponse,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float], None]

COMPACT_PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "clip_compact_selection.txt"
)

# Static and identical on every request so the prompt prefix can be cached.
COMPACT_SYSTEM_PROMPT = (
    "You are a video editor choosing self-contained short-form moments from a "
    "pre-screened shortlist. Return only JSON that matches the provided schema. "
    "Copy start and end from the candidate region you chose, and never invent a "
    "timestamp outside the supplied regions."
)

# Fraction of the final score contributed by the model versus the deterministic
# pre-score. The model judges engagement; the pre-score keeps the result
# anchored to real transcript structure.
_MODEL_WEIGHT = 0.7
_PRESCORE_WEIGHT = 0.3

# How far a returned timestamp may sit outside its region before it is treated
# as a different moment (seconds, or a fraction of the region's length).
_CONTAINMENT_TOLERANCE_SECONDS = 1.0
_CONTAINMENT_TOLERANCE_RATIO = 0.15

# A proposal whose intersection with its region covers this much of the clip is
# still the same idea and is clamped instead of rejected.
_OVERLAP_FALLBACK_RATIO = 0.6


@dataclass
class SelectionTimings:
    """Measured cost of one selection pass. Logged, never persisted."""

    mode: str = "compact"
    candidate_count: int = 0
    prescore_seconds: float = 0.0
    candidate_generation_seconds: float = 0.0
    prompt_chars: int = 0
    prompt_tokens_estimated: int = 0
    ollama_seconds: float = 0.0
    prompt_eval_tokens: int | None = None
    prompt_eval_seconds: float | None = None
    generation_tokens: int | None = None
    generation_seconds: float | None = None
    validation_seconds: float = 0.0
    total_seconds: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "candidate_count": self.candidate_count,
            "prescore_seconds": round(self.prescore_seconds, 3),
            "candidate_generation_seconds": round(
                self.candidate_generation_seconds, 3
            ),
            "prompt_chars": self.prompt_chars,
            "prompt_tokens_estimated": self.prompt_tokens_estimated,
            "ollama_seconds": round(self.ollama_seconds, 3),
            "prompt_eval_tokens": self.prompt_eval_tokens,
            "prompt_eval_seconds": self.prompt_eval_seconds,
            "generation_tokens": self.generation_tokens,
            "generation_seconds": self.generation_seconds,
            "validation_seconds": round(self.validation_seconds, 3),
            "total_seconds": round(self.total_seconds, 3),
        }


def estimate_tokens(text: str) -> int:
    """Cheap, provider-free token estimate used for logging only."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def load_compact_instructions(path: Path | None = None) -> str:
    prompt_path = path or COMPACT_PROMPT_PATH
    try:
        return prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ClipSelectionError(
            "clip_prompt_missing",
            f"The compact clip selection prompt could not be read from "
            f"{prompt_path}. Restore backend/app/prompts/clip_compact_selection.txt "
            "and retry.",
        ) from exc


def build_compact_schema(max_items: int) -> dict[str, Any]:
    """Compact structured-output schema: rank, start, end, score, category, hook."""
    return {
        "type": "object",
        "properties": {
            "clips": {
                "type": "array",
                "maxItems": max(1, int(max_items)),
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer"},
                        "start": {"type": "number"},
                        "end": {"type": "number"},
                        "score": {"type": "number"},
                        "category": {"type": "string"},
                        "hook": {"type": "string"},
                    },
                    "required": ["rank", "start", "end", "score", "category", "hook"],
                },
            }
        },
        "required": ["clips"],
    }


def render_compact_prompt(
    instructions: str,
    regions: Sequence[CandidateRegion],
    duration_seconds: float,
    settings: Settings,
) -> str:
    """Static instructions first, variable data last, so the prefix is cacheable."""
    header = [
        f"Video length: {max(0.0, float(duration_seconds)):.1f} seconds.",
        (
            f"Clip length: {settings.clip_min_duration:.0f} to "
            f"{settings.clip_max_duration:.0f} seconds "
            f"(hard limits {settings.clip_hard_min_seconds:.0f} to "
            f"{settings.clip_hard_max_seconds:.0f})."
        ),
        f"Return at most {settings.clip_max_output} clips.",
        "Candidate regions:",
    ]
    lines = [instructions.rstrip(), "", *header]
    for index, region in enumerate(regions, start=1):
        lines.append(
            f"#{index} [{region.start:.1f}-{region.end:.1f}] "
            f"interest {region.score:.0f} | {region.text}"
        )
    return "\n".join(lines)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _intersection(start: float, end: float, region: CandidateRegion) -> float:
    return max(0.0, min(end, region.end) - max(start, region.start))


def find_region(
    start: float,
    end: float,
    regions: Sequence[CandidateRegion],
) -> tuple[CandidateRegion | None, bool]:
    """Locate the region a proposal belongs to.

    Returns ``(region, needs_clamp)``. A proposal that sits inside a region
    (within a small tolerance) needs no clamping. A proposal that mostly
    overlaps one region is clamped into it, which keeps the idea but discards
    invented timestamps. Anything else is rejected.
    """
    if end <= start:
        return None, False

    best: CandidateRegion | None = None
    best_ratio = 0.0
    for region in regions:
        tolerance = max(
            _CONTAINMENT_TOLERANCE_SECONDS,
            _CONTAINMENT_TOLERANCE_RATIO * region.duration,
        )
        if start >= region.start - tolerance and end <= region.end + tolerance:
            ratio = _intersection(start, end, region) / max(1e-6, end - start)
            if ratio >= best_ratio:
                best, best_ratio = region, ratio
    if best is not None:
        inside = best.start <= start and end <= best.end
        return best, not inside

    clip_duration = max(1e-6, end - start)
    for region in regions:
        ratio = _intersection(start, end, region) / clip_duration
        if ratio >= _OVERLAP_FALLBACK_RATIO and ratio > best_ratio:
            best, best_ratio = region, ratio
    if best is not None:
        return best, True
    return None, False


def fit_within_region(
    start: float,
    end: float,
    region: CandidateRegion,
    settings: Settings,
) -> tuple[float, float] | None:
    """Clamp a clip into its region and enforce the hard duration limits."""
    hard_min = settings.clip_hard_min_seconds
    hard_max = settings.clip_hard_max_seconds
    if region.duration < hard_min:
        return None

    start = _clamp(start, region.start, region.end)
    end = _clamp(end, region.start, region.end)
    if end <= start:
        return None

    if end - start < hard_min:
        end = min(region.end, start + hard_min)
        if end - start < hard_min:
            start = max(region.start, end - hard_min)
    if end - start > hard_max:
        end = start + hard_max

    duration = end - start
    if duration < hard_min or duration > hard_max:
        return None
    return start, end


def refine_within_region(
    start: float,
    end: float,
    region: CandidateRegion,
) -> tuple[float, float]:
    """Snap to whole transcript sentences without leaving the region.

    Boundaries only ever expand to sentence edges inside the same region, so a
    selected idea is never silently replaced with a neighbouring topic.
    """
    spans = region.unit_spans
    if not spans:
        return start, end

    earlier_starts = [span_start for span_start, _ in spans if span_start <= start + 1e-6]
    new_start = (
        max(earlier_starts) if earlier_starts else min(span_start for span_start, _ in spans)
    )

    later_ends = [span_end for _, span_end in spans if span_end >= end - 1e-6]
    new_end = (
        min(later_ends) if later_ends else max(span_end for _, span_end in spans)
    )

    new_start = max(region.start, min(new_start, region.end))
    new_end = max(region.start, min(new_end, region.end))
    if new_end <= new_start:
        return start, end
    return new_start, new_end


def _clean_hook(value: str | None, *, max_words: int = 6) -> str:
    if not value:
        return ""
    words = str(value).split()
    return " ".join(words[:max_words])[:80].strip()


def _clean_category(value: str | None) -> str:
    if not value:
        return "moment"
    cleaned = " ".join(str(value).split()).strip().lower()
    return cleaned[:24] or "moment"


def build_compact_candidate(
    proposal: CompactClipProposal,
    regions: Sequence[CandidateRegion],
    source_duration: float,
    settings: Settings,
) -> ClipCandidate | None:
    """Validate one model proposal and anchor it to its candidate region."""
    region, needs_clamp = find_region(float(proposal.start), float(proposal.end), regions)
    if region is None:
        logger.info(
            "Discarding a compact proposal outside every candidate region "
            "(%.2f-%.2f).",
            proposal.start,
            proposal.end,
        )
        return None

    start, end = float(proposal.start), float(proposal.end)
    if needs_clamp:
        start = _clamp(start, region.start, region.end)
        end = _clamp(end, region.start, region.end)

    if settings.clip_refine_boundaries:
        start, end = refine_within_region(start, end, region)

    fitted = fit_within_region(start, end, region, settings)
    if fitted is None:
        return None
    refined_start, refined_end = fitted

    refined_start = _clamp(refined_start, 0.0, source_duration)
    refined_end = _clamp(refined_end, 0.0, source_duration)
    duration = refined_end - refined_start
    if duration < settings.clip_hard_min_seconds or duration > settings.clip_hard_max_seconds:
        return None

    model_score = _clamp(float(proposal.score), 0.0, 10.0) * 10.0
    final_score = round(
        _MODEL_WEIGHT * model_score + _PRESCORE_WEIGHT * region.score, 2
    )
    category = _clean_category(proposal.category)
    hook = _clean_hook(proposal.hook)
    title = (hook[:1].upper() + hook[1:]) if hook else category.title()

    component_scores: dict[str, Any] = {
        "model_score": round(model_score, 2),
        "prescore": round(region.score, 2),
        "rank": int(proposal.rank),
        "category": category,
        "weights": {"model": _MODEL_WEIGHT, "prescore": _PRESCORE_WEIGHT},
        "method": "compact model+prescore blend",
        "prescore_components": region.component_scores,
    }

    return ClipCandidate(
        start=round(refined_start, 3),
        end=round(refined_end, 3),
        title=title or "Highlight",
        hook=hook,
        reason=f"{region.reason} Category: {category}.",
        score=final_score,
        component_scores=component_scores,
    )


def candidates_from_compact_payload(
    payload: dict[str, Any],
    regions: Sequence[CandidateRegion],
    source_duration: float,
    settings: Settings,
) -> list[ClipCandidate]:
    """Parse, validate, de-duplicate and rank one compact response."""
    if not isinstance(payload, dict):
        logger.warning("Ignoring compact selection: response was not an object.")
        return []

    raw_clips = payload.get("clips")
    if not isinstance(raw_clips, list):
        logger.warning("Ignoring compact selection: 'clips' was not a list.")
        return []

    candidates: list[ClipCandidate] = []
    for item in raw_clips:
        try:
            proposal = CompactClipProposal.model_validate(item)
        except ValidationError as exc:
            # Log only the error count: Pydantic error messages can echo the
            # model's text back, and we do not want transcript text in logs.
            logger.warning(
                "Skipping a malformed compact clip (%d validation error(s)).",
                len(exc.errors()),
            )
            continue
        try:
            candidate = build_compact_candidate(
                proposal, regions, source_duration, settings
            )
        except Exception:  # noqa: BLE001 - one bad clip must not stop selection
            logger.exception("Could not validate a compact clip proposal.")
            continue
        if candidate is not None:
            candidates.append(candidate)

    kept = deduplicate_candidates(candidates, settings.clip_max_output)
    return sorted(kept, key=lambda candidate: (-candidate.score, candidate.start))


class CompactOllamaClipSelector:
    """Deterministic shortlist plus a single compact Ollama request."""

    def __init__(
        self,
        settings: Settings,
        *,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.model_name = settings.ollama_model
        self._client_factory = client_factory or (lambda: OllamaClient(settings))
        self.last_timings = SelectionTimings()

    def _request(
        self, client: Any, prompt: str, schema: dict[str, Any]
    ) -> tuple[dict[str, Any], OllamaChatStats | None]:
        chat_with_stats = getattr(client, "chat_json_result", None)
        if callable(chat_with_stats):
            result = chat_with_stats(
                system=COMPACT_SYSTEM_PROMPT,
                user=prompt,
                schema=schema,
                num_predict=max(160, self.settings.clip_max_output * 90),
            )
            return result.payload, getattr(result, "stats", None)
        payload = client.chat_json(
            system=COMPACT_SYSTEM_PROMPT, user=prompt, schema=schema
        )
        return payload, None

    def select(
        self,
        transcript: Transcript,
        duration_seconds: float,
        on_progress: ProgressCallback | None = None,
    ) -> list[ClipCandidate]:
        started = time.perf_counter()
        timings = SelectionTimings(mode="compact")
        self.last_timings = timings

        if not transcript.has_speech or not transcript.segments:
            timings.total_seconds = time.perf_counter() - started
            logger.info("Clip selection (compact): no speech; nothing to select.")
            return []

        stage_timings: dict[str, float] = {}
        prescore_started = time.perf_counter()
        regions = generate_candidate_regions(
            transcript.segments,
            duration_seconds,
            self.settings,
            timing=stage_timings,
        )
        elapsed = time.perf_counter() - prescore_started
        timings.prescore_seconds = stage_timings.get(
            "unit_seconds", 0.0
        ) + stage_timings.get("scoring_seconds", 0.0)
        timings.candidate_generation_seconds = stage_timings.get(
            "selection_seconds", elapsed
        )
        timings.candidate_count = len(regions)
        if on_progress:
            on_progress(0.15)

        if not regions:
            timings.total_seconds = time.perf_counter() - started
            logger.info("Clip selection (compact): pre-scoring produced no regions.")
            return []

        instructions = load_compact_instructions()
        prompt = render_compact_prompt(
            instructions, regions, duration_seconds, self.settings
        )
        timings.prompt_chars = len(prompt)
        timings.prompt_tokens_estimated = estimate_tokens(prompt)
        schema = build_compact_schema(self.settings.clip_max_output)

        client = self._client_factory()
        try:
            ensure_ready = getattr(client, "ensure_ready", None)
            if callable(ensure_ready):
                try:
                    ensure_ready()
                except OllamaError as exc:
                    raise ClipSelectionError(exc.code, exc.message) from exc

            ollama_started = time.perf_counter()
            try:
                payload, stats = self._request(client, prompt, schema)
            except OllamaMalformedResponse as exc:
                timings.ollama_seconds = time.perf_counter() - ollama_started
                timings.total_seconds = time.perf_counter() - started
                log_selection_timings(timings)
                logger.warning(
                    "Clip selection (compact): malformed response, keeping no "
                    "clips: %s",
                    exc.message,
                )
                return []
            except OllamaError as exc:
                raise ClipSelectionError(exc.code, exc.message) from exc
            timings.ollama_seconds = time.perf_counter() - ollama_started
            if stats is not None:
                timings.prompt_eval_tokens = stats.prompt_eval_count
                timings.prompt_eval_seconds = stats.prompt_eval_seconds
                timings.generation_tokens = stats.eval_count
                timings.generation_seconds = stats.eval_seconds
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

        validation_started = time.perf_counter()
        candidates = candidates_from_compact_payload(
            payload, regions, duration_seconds, self.settings
        )
        timings.validation_seconds = time.perf_counter() - validation_started
        timings.total_seconds = time.perf_counter() - started
        log_selection_timings(timings)
        if on_progress:
            on_progress(1.0)
        return candidates


def log_selection_timings(timings: SelectionTimings) -> None:
    """Log the cost breakdown without any transcript text."""
    prompt_tokens = timings.prompt_eval_tokens
    if prompt_tokens is None:
        prompt_tokens = timings.prompt_tokens_estimated
    logger.info(
        "Clip selection (%s): %d candidate region(s); prompt %d chars (~%d tokens); "
        "pre-score %.3fs; candidates %.3fs; "
        "ollama %.1fs [prompt %s tok / %s s, generation %s tok / %s s]; "
        "validation %.3fs; total %.1fs",
        timings.mode,
        timings.candidate_count,
        timings.prompt_chars,
        prompt_tokens,
        timings.prescore_seconds,
        timings.candidate_generation_seconds,
        timings.ollama_seconds,
        timings.prompt_eval_tokens if timings.prompt_eval_tokens is not None else "?",
        (
            f"{timings.prompt_eval_seconds:.1f}"
            if timings.prompt_eval_seconds is not None
            else "?"
        ),
        timings.generation_tokens if timings.generation_tokens is not None else "?",
        (
            f"{timings.generation_seconds:.1f}"
            if timings.generation_seconds is not None
            else "?"
        ),
        timings.validation_seconds,
        timings.total_seconds,
    )
