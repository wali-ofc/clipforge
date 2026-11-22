"""Deterministic transcript pre-scoring.

This stage runs before any language model. It turns a timestamped transcript
into a short list of self-contained candidate regions, so the LLM never has to
read the whole transcript and never has to choose timestamps from scratch.

The score is deliberately multi-signal rather than keyword driven. Structural
signals (speech density, sentence boundaries, self-containment) carry most of
the weight, so a calm but well-formed statement still surfaces even when it
contains none of the emphasis words. Lexicons only nudge a region's rank.

Everything here is pure and deterministic: the same transcript and settings
always produce the same regions in the same order.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from app.config import Settings
from app.schemas.transcript import TranscriptSegment

_TOKEN_RE = re.compile(r"[a-z0-9']+")

# Intensifiers, superlatives, surprise and stake markers. These add weight but
# are never required: a region can score well without a single hit.
_EMPHASIS = frozenset(
    {
        "amazing", "awful", "best", "biggest", "brutal", "crazy", "critical",
        "dangerous", "disaster", "enormous", "essential", "everyone", "exactly",
        "fail", "failed", "failure", "finally", "huge", "incredible", "insane",
        "key", "massive", "never", "nobody", "obviously", "only", "perfect",
        "powerful", "really", "secret", "shocking", "simple", "stupid",
        "surprising", "terrible", "totally", "truth", "unbelievable", "worst",
        "wrong", "always", "literally", "actually", "guaranteed", "free",
    }
)

# Contrast, correction and disagreement markers.
_CONTRAST = frozenset(
    {
        "but", "however", "instead", "although", "though", "whereas", "except",
        "unless", "actually", "wrong", "mistake", "problem", "myth", "unlike",
        "difference", "disagree", "contrary", "yet", "rather", "despite",
    }
)

# Phrases that signal a conclusion, rule, or payoff.
_CONCLUSION_PHRASES = (
    "the rule is",
    "the key is",
    "the point is",
    "the problem is",
    "the truth is",
    "here's the thing",
    "here is the thing",
    "that's why",
    "that is why",
    "which means",
    "so the",
    "what that means",
    "the lesson",
    "the takeaway",
    "in other words",
    "bottom line",
    "what matters",
    "the reason",
)

# Openers that usually continue a previous thought instead of starting one.
_CONTINUATIONS = frozenset(
    {
        "and", "but", "so", "because", "which", "that", "or", "then", "also",
        "however", "though", "although", "while", "when", "if", "as", "like",
    }
)

# Openers that need a referent the viewer does not have yet.
_WEAK_OPENERS = frozenset(
    {
        "it", "this", "that", "these", "those", "they", "them", "their",
        "he", "him", "his", "she", "her", "we", "us", "our",
    }
)

_QUESTION_WORDS = frozenset(
    {
        "what", "why", "how", "when", "where", "who", "which", "do", "does",
        "did", "can", "could", "should", "would", "is", "are", "was", "were",
        "have", "has", "will",
    }
)

_HOOK_WORDS = frozenset(
    {
        "why", "how", "what", "never", "always", "everyone", "nobody", "secret",
        "truth", "mistake", "wrong", "best", "worst", "first", "biggest",
        "only", "stop", "start", "should", "must", "need", "you",
    }
)

_SENTENCE_END = re.compile(r"[.!?][\"'”’)\]]?$")
_NUMBER_RE = re.compile(r"\d")

# Structural signals carry most of the weight on purpose.
_WEIGHTS: dict[str, float] = {
    "speech_density": 0.16,
    "boundary": 0.22,
    "hook": 0.16,
    "emphasis": 0.14,
    "contrast": 0.10,
    "conclusion": 0.10,
    "self_contained": 0.12,
}


@dataclass(frozen=True)
class TranscriptUnit:
    """One sentence-sized chunk after merging tiny fragments."""

    start: float
    end: float
    text: str
    words: int

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(frozen=True)
class CandidateRegion:
    """A deterministic shortlist entry offered to the language model."""

    start: float
    end: float
    text: str
    score: float
    reason: str
    component_scores: dict[str, float] = field(default_factory=dict)
    # Segment spans inside this region, used for optional boundary refinement.
    unit_spans: tuple[tuple[float, float], ...] = ()

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _is_number_token(token: str) -> bool:
    return bool(_NUMBER_RE.search(token))


def _unit_text(segments: Sequence[TranscriptSegment]) -> str:
    return " ".join(segment.text.strip() for segment in segments if segment.text.strip())


def _word_count(segment: TranscriptSegment) -> int:
    if segment.words:
        return len(segment.words)
    return len(segment.text.split())


def build_units(segments: Sequence[TranscriptSegment]) -> list[TranscriptUnit]:
    """Merge fragments shorter than a beat so a unit reads like a sentence.

    Whisper sometimes emits one- or two-word segments. Starting a candidate on
    one of those would look like a mid-sentence cut, so tiny neighbours that are
    close in time are folded into a single unit.
    """
    usable = [s for s in segments if s.text.strip() and s.end > s.start]
    usable.sort(key=lambda s: (s.start, s.end))

    units: list[TranscriptUnit] = []
    buffer: list[TranscriptSegment] = []

    def flush() -> None:
        if not buffer:
            return
        units.append(
            TranscriptUnit(
                start=buffer[0].start,
                end=max(segment.end for segment in buffer),
                text=_unit_text(buffer),
                words=sum(_word_count(segment) for segment in buffer),
            )
        )
        buffer.clear()

    for segment in usable:
        if not buffer:
            buffer.append(segment)
            continue

        previous = buffer[-1]
        gap = segment.start - previous.end
        buffered_duration = max(item.end for item in buffer) - buffer[0].start
        buffered_words = sum(_word_count(item) for item in buffer)
        tiny = buffered_duration < 1.2 or buffered_words < 4
        merged_duration = segment.end - buffer[0].start

        if gap <= 1.0 and tiny and merged_duration <= 8.0:
            buffer.append(segment)
        else:
            flush()
            buffer.append(segment)

    flush()
    return units


def _score_span(
    units: Sequence[TranscriptUnit],
    start_index: int,
    end_index: int,
    internal_gaps: float,
) -> tuple[float, dict[str, float]]:
    """Score one whole-unit span on several independent signals."""
    window = units[start_index : end_index + 1]
    duration = max(0.1, units[end_index].end - units[start_index].start)
    words = sum(unit.words for unit in window)
    text = " ".join(unit.text for unit in window)
    tokens = _tokens(text)

    # --- speech density: talk per second, penalised for dead air -----------
    speaking_time = max(0.1, duration - internal_gaps)
    words_per_second = words / speaking_time
    density = _clamp(words_per_second / 2.7, 0.0, 1.0) * 100.0
    gap_ratio = internal_gaps / duration
    gap_penalty = _clamp(gap_ratio / 0.35, 0.0, 1.0) * 100.0
    speech_density = 0.8 * density + 0.2 * (100.0 - gap_penalty)

    # --- boundaries: does it start and end a thought? ----------------------
    first_text = window[0].text.strip()
    last_text = window[-1].text.strip()
    first_tokens = _tokens(first_text)
    starts_clean = 0.35 if first_tokens and first_tokens[0] in _CONTINUATIONS else 1.0
    if first_text[:1].isupper() or first_text[:1].isdigit():
        starts_clean = min(1.0, starts_clean + 0.25)
    ends_clean = 1.0 if _SENTENCE_END.search(last_text) else 0.3
    question_start = 1.0 if first_tokens and first_tokens[0] in _QUESTION_WORDS else 0.0
    has_question = 1.0 if any("?" in unit.text for unit in window) else 0.0
    boundary = 100.0 * (
        0.45 * starts_clean + 0.35 * ends_clean + 0.10 * question_start + 0.10 * has_question
    )

    # --- hook: does the opening line give a stranger a reason to stay? -----
    opening = tokens[:6]
    hook_hits = sum(1 for token in opening if token in _HOOK_WORDS)
    hook_hits += sum(1 for token in opening if _is_number_token(token))
    if "?" in first_text:
        hook_hits += 1
    hook = _clamp(hook_hits * 22.0, 0.0, 100.0)

    # --- emphasis and contrast: rate per 100 words, capped -----------------
    emphasis_hits = sum(1 for token in tokens if token in _EMPHASIS)
    contrast_hits = sum(1 for token in tokens if token in _CONTRAST)
    per_hundred = 100.0 / max(1, words)
    emphasis = _clamp(emphasis_hits * per_hundred * 12.0, 0.0, 100.0)
    contrast = _clamp(contrast_hits * per_hundred * 15.0, 0.0, 100.0)

    # --- conclusion: payoff language, weighted toward the back ------------
    tail_start = start_index + int(len(window) * 0.6)
    tail_text = " ".join(unit.text for unit in units[tail_start : end_index + 1]).lower()
    conclusion_hits = sum(1 for phrase in _CONCLUSION_PHRASES if phrase in tail_text)
    conclusion = _clamp(conclusion_hits * 35.0, 0.0, 100.0)

    # --- self-containment: can a cold viewer follow the opening? ----------
    self_contained = 100.0
    if first_tokens and first_tokens[0] in _WEAK_OPENERS:
        self_contained -= 45.0
    if first_tokens and first_tokens[0] in _CONTINUATIONS:
        self_contained -= 35.0
    lead_tokens = tokens[:12]
    # A capitalised word that is not the sentence-initial word is a decent
    # proxy for a named person, place, or product. "I" is excluded because it
    # is capitalised everywhere.
    lead_words = text.split()[:14]
    named = any(
        word[:1].isupper() and word not in {"I", "I'm", "I've", "I'll", "I'd"}
        for word in lead_words[1:]
    )
    numbered = any(_is_number_token(token) for token in lead_tokens)
    if not named and not numbered:
        self_contained -= 20.0
    if words < 40:
        self_contained -= 15.0
    self_contained = _clamp(self_contained, 0.0, 100.0)

    components = {
        "speech_density": round(speech_density, 2),
        "boundary": round(boundary, 2),
        "hook": round(hook, 2),
        "emphasis": round(emphasis, 2),
        "contrast": round(contrast, 2),
        "conclusion": round(conclusion, 2),
        "self_contained": round(self_contained, 2),
    }
    score = sum(_WEIGHTS[key] * components[key] for key in _WEIGHTS)
    return round(score, 2), components


def _describe(components: dict[str, float]) -> str:
    """Short, human-readable reason built from the strongest signals."""
    labels = {
        "hook": "a strong opening",
        "emphasis": "emphatic language",
        "contrast": "contrast or correction",
        "conclusion": "a conclusion or payoff",
        "self_contained": "a self-contained setup",
        "speech_density": "dense continuous speech",
        "boundary": "clean sentence boundaries",
    }
    ranked = sorted(
        ((name, value) for name, value in components.items() if name in labels),
        key=lambda item: -item[1],
    )
    highlights = [labels[name] for name, value in ranked[:2] if value >= 45.0]
    if not highlights:
        highlights = [labels[ranked[0][0]]] if ranked else ["a usable spoken passage"]
    return "Strong " + " and ".join(highlights) + "."


def _overlap(left: CandidateRegion, right: CandidateRegion) -> float:
    return max(0.0, min(left.end, right.end) - max(left.start, right.start))


def _iou(left: CandidateRegion, right: CandidateRegion) -> float:
    intersection = _overlap(left, right)
    if intersection <= 0:
        return 0.0
    union = left.duration + right.duration - intersection
    return intersection / union if union > 0 else 0.0


def _containment(left: CandidateRegion, right: CandidateRegion) -> float:
    intersection = _overlap(left, right)
    shorter = min(left.duration, right.duration)
    return intersection / shorter if shorter > 0 else 0.0


def _gap(left: CandidateRegion, right: CandidateRegion) -> float:
    return max(0.0, max(left.start, right.start) - min(left.end, right.end))


def target_candidate_count(duration_seconds: float, settings: Settings) -> int:
    """Scale the shortlist with video length instead of using a fixed count."""
    by_length = int(round(max(0.0, duration_seconds) / 25.0))
    return max(3, min(settings.clip_max_candidates, by_length))


def generate_candidate_regions(
    segments: Sequence[TranscriptSegment],
    duration_seconds: float,
    settings: Settings,
    *,
    max_candidates: int | None = None,
    timing: dict[str, float] | None = None,
) -> list[CandidateRegion]:
    """Return deterministic, de-duplicated, chronologically ordered regions.

    Every returned region starts and ends on a whole transcript unit, fits the
    configured duration range, and carries its own score and explanation.

    When ``timing`` is supplied, separate second-level durations for unit
    building, span scoring, and shortlist selection are written into it. The
    caller uses these for instrumentation; nothing is logged here.
    """
    started = time.perf_counter()
    if timing is not None:
        timing.setdefault("unit_seconds", 0.0)
        timing.setdefault("scoring_seconds", 0.0)
        timing.setdefault("selection_seconds", 0.0)

    duration = max(0.0, float(duration_seconds))
    units = build_units(segments)
    if timing is not None:
        timing["unit_seconds"] = time.perf_counter() - started
    if not units:
        return []

    if duration <= 0:
        duration = units[-1].end

    target = max_candidates or target_candidate_count(duration, settings)
    target = max(1, min(target, settings.clip_max_candidates))

    min_duration = settings.clip_min_duration
    max_duration = max(min_duration + 1.0, settings.clip_max_duration)
    max_chars = settings.clip_candidate_max_chars

    # Prefix sums keep each span's internal silence O(1).
    gap_before = [0.0]
    for index in range(1, len(units)):
        gap_before.append(max(0.0, units[index].start - units[index - 1].end))
    prefix_gaps = [0.0]
    for value in gap_before:
        prefix_gaps.append(prefix_gaps[-1] + value)

    spans: list[CandidateRegion] = []
    for start_index in range(len(units)):
        text_chars = 0
        for end_index in range(start_index, len(units)):
            span_start = units[start_index].start
            span_end = min(units[end_index].end, duration)
            span_duration = span_end - span_start
            if span_duration > max_duration:
                break

            text_chars += len(units[end_index].text) + 1
            if end_index > start_index and text_chars > max_chars:
                break
            if span_duration < min_duration:
                continue

            internal_gaps = prefix_gaps[end_index] - prefix_gaps[start_index]
            score, components = _score_span(
                units, start_index, end_index, internal_gaps
            )
            spans.append(
                CandidateRegion(
                    start=round(span_start, 3),
                    end=round(span_end, 3),
                    text=_unit_text(units[start_index : end_index + 1]),
                    score=score,
                    reason=_describe(components),
                    component_scores=components,
                    unit_spans=tuple(
                        (unit.start, unit.end) for unit in units[start_index : end_index + 1]
                    ),
                )
            )

    if timing is not None:
        timing["scoring_seconds"] = time.perf_counter() - started - timing["unit_seconds"]
    if not spans:
        return []

    selection_started = time.perf_counter()

    # Selection has two phases:
    #
    # 1. Coverage. Split the video into equal time buckets and keep the best
    #    non-overlapping span from each one. This deliberately reserves a slot
    #    for the quiet part of a video, so a calm but coherent statement is not
    #    crowded out by a cluster of louder spans elsewhere.
    # 2. Fill. Spend any remaining slots on the strongest spans with spacing,
    #    then relax the spacing only if there is not enough distinct material.
    #
    # The bucket count scales with the video length through ``target``; there
    # is no fixed number of windows.
    ordered = sorted(spans, key=lambda span: (-span.score, span.start, span.end))
    kept: list[CandidateRegion] = []
    kept_keys: set[tuple[float, float]] = set()
    min_gap = max(4.0, min_duration * 0.5)

    def take(span: CandidateRegion) -> None:
        kept.append(span)
        kept_keys.add((span.start, span.end))

    def distinct(span: CandidateRegion, *, iou: float = 0.35, containment: float = 0.5) -> bool:
        return not any(
            _iou(span, existing) >= iou or _containment(span, existing) >= containment
            for existing in kept
        )

    bucket_width = max(1.0, duration / target)
    by_bucket: dict[int, list[CandidateRegion]] = {}
    for span in ordered:
        midpoint = (span.start + span.end) / 2.0
        bucket = min(target - 1, max(0, int(midpoint / bucket_width)))
        by_bucket.setdefault(bucket, []).append(span)

    for bucket in sorted(by_bucket):
        for span in by_bucket[bucket]:
            if distinct(span):
                take(span)
                break
        if len(kept) >= target:
            break

    if len(kept) < target:
        for span in ordered:
            if (span.start, span.end) in kept_keys:
                continue
            if not distinct(span):
                continue
            if any(_gap(span, existing) < min_gap for existing in kept):
                continue
            take(span)
            if len(kept) >= target:
                break

    if len(kept) < target:
        for span in ordered:
            if (span.start, span.end) in kept_keys:
                continue
            if not distinct(span, iou=0.5, containment=0.65):
                continue
            take(span)
            if len(kept) >= target:
                break

    kept.sort(key=lambda span: (span.start, span.end))
    if timing is not None:
        timing["selection_seconds"] = time.perf_counter() - selection_started
    return kept
