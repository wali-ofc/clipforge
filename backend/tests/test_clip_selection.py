"""Clip selection chunking, validation, scoring, and Ollama client tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.schemas.clip_selection import LLMClip, LLMClipScores
from app.schemas.transcript import Transcript, TranscriptSegment, TranscriptWord
from app.services.clip_selection import (
    ClipCandidate,
    ClipSelectionError,
    OllamaClipSelector,
    TranscriptChunk,
    build_candidate,
    build_chunks,
    build_response_schema,
    candidates_from_payload,
    deduplicate_candidates,
    load_prompt_template,
    render_prompt,
    score_candidate,
)
from app.services.ollama import OllamaError, OllamaMalformedResponse
from app.utils.time import utc_now


def _segment(start: float, end: float, text: str = "Spoken sentence.") -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def _word_segment(
    start: float,
    end: float,
    words: list[tuple[float, float, str]],
    text: str = "Spoken sentence.",
) -> TranscriptSegment:
    return TranscriptSegment(
        start=start,
        end=end,
        text=text,
        words=[
            TranscriptWord(start=word_start, end=word_end, text=word_text)
            for word_start, word_end, word_text in words
        ],
    )


def _transcript(segments: list[TranscriptSegment], duration: float) -> Transcript:
    return Transcript(
        language="en",
        language_probability=0.99,
        duration=duration,
        model="stub",
        has_speech=bool(segments),
        created_at=utc_now(),
        segments=segments,
    )


def _payload(start: float, end: float, *, title: str = "A moment") -> dict:
    return {
        "clips": [
            {
                "start": start,
                "end": end,
                "title": title,
                "hook": "A hook",
                "reason": "A reason",
                "scores": {
                    "hook": 8,
                    "clarity": 9,
                    "standalone": 9,
                    "emotion_or_interest": 7,
                    "payoff": 8,
                },
            }
        ]
    }


class FakeOllamaClient:
    def __init__(self, responses, *, ready_error: Exception | None = None) -> None:
        self.responses = list(responses)
        self.ready_error = ready_error
        self.calls = 0
        self.closed = False

    def ensure_ready(self):
        if self.ready_error is not None:
            raise self.ready_error

    def chat_json(self, *, system: str, user: str, schema: dict):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self) -> None:
        self.closed = True


def test_chunks_use_overlapping_absolute_windows():
    segments = [_segment(index * 30, index * 30 + 30) for index in range(8)]
    chunks = build_chunks(segments, window_seconds=180, overlap_seconds=30)

    assert len(chunks) >= 2
    assert chunks[0].start == 0
    assert chunks[0].end == 180
    assert chunks[1].start == 150
    assert chunks[1].segments[0].start == 150

    for chunk in chunks:
        assert chunk.start < chunk.end
        for segment in chunk.segments:
            assert 0 <= segment.start < segment.end
            assert chunk.start <= segment.start < chunk.end
        # Absolute source timestamps are preserved, never re-based.
        assert chunk.segments[-1].end <= 240


def test_prompt_contains_absolute_timestamps_and_limits(settings: Settings):
    chunk = TranscriptChunk(
        start=120.0,
        end=180.0,
        segments=(_segment(120.0, 150.0, "Hello there."),),
    )
    prompt = render_prompt(
        load_prompt_template(),
        chunk,
        3600.0,
        settings,
        max_candidates=4,
    )

    assert "[120.00 - 150.00] Hello there." in prompt
    assert "120.0 to 180.0" in prompt
    assert "20 to 60" in prompt
    assert "15 to 90" in prompt
    assert "at most 4 clips" in prompt


def test_prompt_placeholder_error_is_actionable(tmp_path: Path):
    with pytest.raises(ClipSelectionError) as error:
        load_prompt_template(tmp_path / "missing.txt")
    assert error.value.code == "clip_prompt_missing"

    with pytest.raises(ClipSelectionError) as error:
        render_prompt("{unknown}", TranscriptChunk(0, 1, ()), 1, _settings(), 1)
    assert error.value.code == "clip_prompt_invalid"


def test_response_schema_requires_clip_fields():
    schema = build_response_schema(3)
    item = schema["properties"]["clips"]["items"]
    assert schema["properties"]["clips"]["maxItems"] == 3
    assert set(item["required"]) == {
        "start",
        "end",
        "title",
        "hook",
        "reason",
        "scores",
    }
    assert set(item["properties"]["scores"]["required"]) == {
        "hook",
        "clarity",
        "standalone",
        "emotion_or_interest",
        "payoff",
    }


def test_boundaries_snap_to_whole_segments(settings: Settings):
    chunk = TranscriptChunk(
        start=0,
        end=60,
        segments=(
            _word_segment(
                0,
                30,
                [(0, 10, "First"), (10, 20, "middle"), (20, 30, "sentence.")],
            ),
            _word_segment(
                30,
                60,
                [(30, 40, "Second"), (40, 50, "middle"), (50, 60, "sentence.")],
            ),
        ),
    )
    raw = LLMClip(start=10, end=20, title="Middle", scores=LLMClipScores())

    candidate = build_candidate(raw, chunk, 60, settings)

    assert candidate is not None
    # The proposal was inside one sentence; the clip expands to that whole
    # transcript segment rather than starting or ending mid-sentence.
    assert candidate.start == 0
    assert candidate.end == 30


def test_boundaries_expand_across_segments(settings: Settings):
    chunk = TranscriptChunk(
        start=0,
        end=60,
        segments=(_segment(0, 30), _segment(30, 60)),
    )
    raw = LLMClip(start=5, end=55, title="Across", scores=LLMClipScores())

    candidate = build_candidate(raw, chunk, 60, settings)

    assert candidate is not None
    assert candidate.start == 0
    assert candidate.end == 60


def test_too_short_clip_is_rejected(settings: Settings):
    chunk = TranscriptChunk(start=0, end=10, segments=(_segment(0, 10),))
    raw = LLMClip(start=0, end=10, title="Tiny", scores=LLMClipScores())

    assert build_candidate(raw, chunk, 10, settings) is None


def test_out_of_bounds_proposal_is_clamped(settings: Settings):
    chunk = TranscriptChunk(start=0, end=60, segments=(_segment(0, 30), _segment(30, 60)))
    raw = LLMClip(start=-100, end=1000, title="Wide", scores=LLMClipScores())

    candidate = build_candidate(raw, chunk, 60, settings)

    assert candidate is not None
    assert candidate.start == 0
    assert candidate.end == 60


def test_reversed_proposal_is_rejected(settings: Settings):
    chunk = TranscriptChunk(start=0, end=60, segments=(_segment(0, 30), _segment(30, 60)))
    raw = LLMClip(start=50, end=50, title="Reversed", scores=LLMClipScores())

    assert build_candidate(raw, chunk, 60, settings) is None


def test_score_is_deterministic_and_weighted(settings: Settings):
    perfect = LLMClipScores(
        hook=10,
        clarity=10,
        standalone=10,
        emotion_or_interest=10,
        payoff=10,
    )
    score, components = score_candidate(duration=30, scores=perfect, settings=settings)

    assert score == pytest.approx(100.0)
    assert components["conciseness"] == 100.0
    assert components["method"] == "deterministic weighted clip potential"
    assert components["weights"] == {
        "hook": 0.25,
        "clarity": 0.25,
        "payoff": 0.2,
        "emotion_or_interest": 0.2,
        "conciseness": 0.1,
    }

    edge_score, edge_components = score_candidate(
        duration=90, scores=perfect, settings=settings
    )
    assert edge_components["conciseness"] == 60.0
    assert edge_score == pytest.approx(96.0)


def test_deduplication_keeps_highest_score_and_limits_count(settings: Settings):
    def candidate(start: float, end: float, score: float) -> ClipCandidate:
        return ClipCandidate(
            start=start,
            end=end,
            title="T",
            hook="H",
            reason="R",
            score=score,
        )

    duplicate_low = candidate(0, 30, 60)
    duplicate_high = candidate(1, 30, 90)
    separate = candidate(40, 70, 70)

    kept = deduplicate_candidates([duplicate_low, duplicate_high, separate], 8)
    assert [item.score for item in kept] == [90, 70]

    limited = deduplicate_candidates([duplicate_low, separate], 1)
    assert len(limited) == 1
    assert limited[0].score == 70


def test_deduplication_removes_nested_clips():
    def candidate(start: float, end: float, score: float) -> ClipCandidate:
        return ClipCandidate(
            start=start,
            end=end,
            title="T",
            hook="H",
            reason="R",
            score=score,
        )

    # The short clip is fully inside the long one; IoU is low but it is a
    # duplicate of the same moment.
    long_clip = candidate(0, 55, 80)
    nested = candidate(4, 25, 80)
    separate = candidate(60, 85, 70)

    kept = deduplicate_candidates([long_clip, nested, separate], 8)
    assert len(kept) == 2
    assert [(item.start, item.end) for item in kept] == [(4, 25), (60, 85)]


def test_deduplication_prefers_shorter_clip_on_score_tie():
    def candidate(start: float, end: float) -> ClipCandidate:
        return ClipCandidate(
            start=start,
            end=end,
            title="T",
            hook="H",
            reason="R",
            score=80,
        )

    kept = deduplicate_candidates([candidate(0, 55), candidate(4, 25)], 8)
    assert len(kept) == 1
    assert (kept[0].start, kept[0].end) == (4, 25)


def test_malformed_payload_is_skipped(settings: Settings):
    chunk = TranscriptChunk(start=0, end=60, segments=(_segment(0, 30), _segment(30, 60)))

    assert candidates_from_payload({"clips": "nope"}, chunk, 60, settings) == []
    assert (
        candidates_from_payload(
            {"clips": [{"start": "not a number", "end": 20}]},
            chunk,
            60,
            settings,
        )
        == []
    )

    mixed = _payload(0, 60)
    mixed["clips"].append({"start": "bad", "end": 20})
    candidates = candidates_from_payload(mixed, chunk, 60, settings)
    assert len(candidates) == 1


def _two_chunk_transcript() -> Transcript:
    segments = [_segment(index * 30, index * 30 + 30) for index in range(8)]
    return _transcript(segments, 240)


def test_selector_skips_malformed_chunk_and_keeps_valid_one(settings: Settings):
    client = FakeOllamaClient(
        [
            OllamaMalformedResponse(
                "ollama_malformed_response", "Model returned prose."
            ),
            _payload(150, 240),
        ]
    )
    selector = OllamaClipSelector(settings, client_factory=lambda: client)

    candidates = selector.select(_two_chunk_transcript(), 240)

    assert client.calls == 2
    assert client.closed is True
    assert len(candidates) == 1
    assert candidates[0].start == 150
    assert candidates[0].end == 210


def test_selector_returns_empty_when_every_chunk_is_malformed(settings: Settings):
    client = FakeOllamaClient(
        [
            OllamaMalformedResponse("ollama_malformed_response", "bad one"),
            OllamaMalformedResponse("ollama_malformed_response", "bad two"),
        ]
    )
    selector = OllamaClipSelector(settings, client_factory=lambda: client)

    assert selector.select(_two_chunk_transcript(), 240) == []
    assert client.closed is True


def test_selector_reports_unavailable_ollama(settings: Settings):
    client = FakeOllamaClient(
        [],
        ready_error=OllamaError(
            "ollama_unavailable", "Ollama is not reachable. Start it with `ollama serve`."
        ),
    )
    selector = OllamaClipSelector(settings, client_factory=lambda: client)

    with pytest.raises(ClipSelectionError) as error:
        selector.select(_two_chunk_transcript(), 240)

    assert error.value.code == "ollama_unavailable"
    assert "ollama serve" in error.value.message
    assert client.closed is True


def test_selector_reports_model_missing(settings: Settings):
    client = FakeOllamaClient(
        [],
        ready_error=OllamaError(
            "ollama_model_missing",
            "The Ollama model is not installed. Run `ollama pull qwen2.5:3b`.",
        ),
    )
    selector = OllamaClipSelector(settings, client_factory=lambda: client)

    with pytest.raises(ClipSelectionError) as error:
        selector.select(_two_chunk_transcript(), 240)

    assert error.value.code == "ollama_model_missing"
    assert "ollama pull" in error.value.message


def test_selector_treats_timeout_as_fatal(settings: Settings):
    client = FakeOllamaClient(
        [OllamaError("ollama_timeout", "Ollama timed out while selecting clips.")]
    )
    selector = OllamaClipSelector(settings, client_factory=lambda: client)

    with pytest.raises(ClipSelectionError) as error:
        selector.select(_two_chunk_transcript(), 240)

    assert error.value.code == "ollama_timeout"
    assert client.closed is True


def test_selector_skips_no_speech_without_calling_ollama(settings: Settings):
    called = False

    def factory():
        nonlocal called
        called = True
        return FakeOllamaClient([])

    selector = OllamaClipSelector(settings, client_factory=factory)

    assert selector.select(_transcript([], 60), 60) == []
    assert called is False


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        data_dir=Path("./data"),
        database_url="sqlite:///./data/test.db",
    )
