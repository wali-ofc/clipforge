"""Deterministic pre-scoring and candidate generation tests."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.schemas.transcript import TranscriptSegment
from app.services.clip_prescore import (
    build_units,
    generate_candidate_regions,
    target_candidate_count,
)


def _segment(start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def _speech(
    duration: float,
    sentence: str,
    *,
    sentence_seconds: float = 8.0,
    gap: float = 0.2,
) -> list[TranscriptSegment]:
    """Fill ``duration`` seconds with a repeated sentence, one per segment."""
    segments: list[TranscriptSegment] = []
    cursor = 0.0
    while cursor + sentence_seconds <= duration + 1e-6:
        segments.append(
            _segment(cursor, cursor + sentence_seconds - gap, sentence)
        )
        cursor += sentence_seconds
    return segments


def _iou(left, right) -> float:
    intersection = max(0.0, min(left.end, right.end) - max(left.start, right.start))
    if intersection <= 0:
        return 0.0
    union = (left.end - left.start) + (right.end - right.start) - intersection
    return intersection / union if union > 0 else 0.0


def _containment(left, right) -> float:
    intersection = max(0.0, min(left.end, right.end) - max(left.start, right.start))
    shorter = min(left.end - left.start, right.end - right.start)
    return intersection / shorter if shorter > 0 else 0.0


# --------------------------------------------------------------------------
# Unit building
# --------------------------------------------------------------------------


def test_tiny_fragments_are_merged_into_a_sentence():
    segments = [
        _segment(0.0, 0.4, "Yes."),
        _segment(0.5, 7.0, "The meeting starts at nine in the morning."),
        _segment(7.2, 14.0, "There are twenty chairs in the room."),
    ]

    units = build_units(segments)

    assert units
    # A one-word fragment must not become its own unit: it would look like a
    # mid-sentence cut to the model.
    assert all(len(unit.text.split()) >= 4 for unit in units)


def test_units_do_not_merge_across_a_long_pause():
    segments = [
        _segment(0.0, 6.0, "This is the first complete thought."),
        _segment(30.0, 36.0, "This is a separate thought later."),
    ]

    units = build_units(segments)

    assert len(units) == 2


# --------------------------------------------------------------------------
# Candidate generation
# --------------------------------------------------------------------------


def test_empty_transcript_produces_no_candidates(settings: Settings):
    assert generate_candidate_regions([], 120.0, settings) == []


def test_candidates_stay_inside_the_source_and_duration_bounds(settings: Settings):
    segments = _speech(360.0, "This is a normal sentence about the topic.")
    duration = 360.0

    regions = generate_candidate_regions(segments, duration, settings)

    assert regions
    for region in regions:
        assert 0.0 <= region.start < region.end <= duration
        assert region.duration >= settings.clip_min_duration - 1e-6
        assert region.duration <= settings.clip_max_duration + 1e-6


def test_candidate_count_scales_with_video_length(settings: Settings):
    short = generate_candidate_regions(
        _speech(60.0, "A short video with one repeated sentence here."), 60.0, settings
    )
    long = generate_candidate_regions(
        _speech(1800.0, "A long video with one repeated sentence here."),
        1800.0,
        settings,
    )

    assert len(short) <= 3
    assert len(long) <= settings.clip_max_candidates
    assert len(long) > len(short)


@pytest.mark.parametrize("duration", [45.0, 300.0, 1800.0, 3600.0])
def test_no_hardcoded_window_count(settings: Settings, duration: float):
    segments = _speech(duration, "The same plain sentence is repeated here.")
    regions = generate_candidate_regions(segments, duration, settings)

    assert 1 <= len(regions) <= settings.clip_max_candidates
    assert len(regions) <= target_candidate_count(duration, settings)


def test_regions_do_not_overlap_heavily(settings: Settings):
    segments = _speech(600.0, "Each sentence should stand on its own here.")
    regions = generate_candidate_regions(segments, 600.0, settings)

    for index, left in enumerate(regions):
        for right in regions[index + 1 :]:
            assert _iou(left, right) < 0.5
            assert _containment(left, right) < 0.65


def test_regions_start_and_end_on_unit_boundaries(settings: Settings):
    segments = _speech(300.0, "This sentence is complete and self contained.")
    units = build_units(segments)
    unit_starts = {round(unit.start, 3) for unit in units}
    unit_ends = {round(unit.end, 3) for unit in units}

    regions = generate_candidate_regions(segments, 300.0, settings)

    for region in regions:
        assert round(region.start, 3) in unit_starts
        assert round(region.end, 3) in unit_ends


def test_generation_reports_separate_stage_timings(settings: Settings):
    timing: dict[str, float] = {}

    generate_candidate_regions(
        _speech(180.0, "This sentence is used to measure stage timings."),
        180.0,
        settings,
        timing=timing,
    )

    assert set(timing) == {"unit_seconds", "scoring_seconds", "selection_seconds"}
    assert all(value >= 0.0 for value in timing.values())


def test_output_is_deterministic(settings: Settings):
    segments = _speech(420.0, "A deterministic sentence for the same input.")

    first = generate_candidate_regions(segments, 420.0, settings)
    second = generate_candidate_regions(segments, 420.0, settings)

    assert [(r.start, r.end, r.score) for r in first] == [
        (r.start, r.end, r.score) for r in second
    ]


def test_regions_carry_a_reason_and_component_scores(settings: Settings):
    segments = _speech(180.0, "This sentence carries a short explanation.")
    regions = generate_candidate_regions(segments, 180.0, settings)

    for region in regions:
        assert region.reason.strip()
        assert region.component_scores
        assert 0.0 <= region.score <= 100.0


# --------------------------------------------------------------------------
# Signal quality
# --------------------------------------------------------------------------


def test_question_answer_region_outranks_plain_filler(settings: Settings):
    plain = _speech(120.0, "The room has chairs and a table in the corner.")
    qa_start = 120.0
    qa = [
        _segment(
            qa_start,
            qa_start + 9.0,
            "Why does everyone fail at this every single time?",
        ),
        _segment(
            qa_start + 9.2,
            qa_start + 20.0,
            "Because they never change the one habit that actually matters.",
        ),
        _segment(
            qa_start + 20.2,
            qa_start + 34.0,
            "But the rule is simple, and that is why it works for anyone.",
        ),
    ]

    regions = generate_candidate_regions(plain + qa, 154.0, settings)
    qa_regions = [r for r in regions if r.start >= qa_start - 1e-6]
    plain_regions = [r for r in regions if r.end <= qa_start + 1e-6]

    assert qa_regions
    assert plain_regions
    assert max(r.score for r in qa_regions) > max(r.score for r in plain_regions)


def test_quiet_statement_is_not_dropped_in_a_loud_video(settings: Settings):
    loud = "This is the biggest mistake and it is absolutely insane."
    quiet = [
        _segment(220.0, 229.0, "The meeting starts at nine in the morning."),
        _segment(229.2, 238.0, "The room is on the second floor of the building."),
        _segment(238.2, 248.0, "There are twenty chairs and one long table."),
        _segment(248.2, 259.0, "The agenda covers the budget and the schedule."),
    ]
    segments = (
        _speech(212.0, loud)
        + quiet
        + [
            _segment(260.0 + index * 8.0, 267.0 + index * 8.0, loud)
            for index in range(5)
        ]
    )

    regions = generate_candidate_regions(segments, 300.0, settings)

    covered = sum(
        max(0.0, min(region.end, 259.0) - max(region.start, 220.0)) for region in regions
    )
    assert covered >= 20.0, "the quiet passage was dropped from the shortlist"


def test_continuation_openers_score_below_clean_openers(settings: Settings):
    clean = [
        _segment(0.0, 10.0, "Raj Shamani explains the ten minute rule clearly."),
        _segment(10.2, 22.0, "The rule works because it removes one decision."),
    ]
    continuation = [
        _segment(40.0, 50.0, "And that is the thing about the rule itself."),
        _segment(50.2, 62.0, "It works because it removes one decision."),
    ]

    regions = generate_candidate_regions(clean + continuation, 62.0, settings)
    clean_regions = [r for r in regions if r.end <= 23.0]
    continuation_regions = [r for r in regions if r.start >= 39.0]

    assert clean_regions and continuation_regions
    assert max(r.score for r in clean_regions) > max(
        r.score for r in continuation_regions
    )


def test_candidate_text_budget_is_respected(settings: Settings):
    long_sentence = " ".join(["word"] * 200) + "."
    segments = _speech(300.0, long_sentence, sentence_seconds=12.0)

    regions = generate_candidate_regions(segments, 300.0, settings)

    for region in regions:
        assert len(region.text) <= settings.clip_candidate_max_chars + len(long_sentence)
