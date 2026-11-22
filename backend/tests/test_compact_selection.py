"""Compact clip selection tests.

These cover the deterministic shortlist, the single compact Ollama request, the
containment rules that stop the model inventing timestamps, graceful failure
handling, and the timing instrumentation.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings
from app.schemas.clip_selection import CompactClipProposal
from app.schemas.transcript import Transcript, TranscriptSegment
from app.services.clip_prescore import CandidateRegion, generate_candidate_regions
from app.services.clip_selection import (
    ClipSelectionError,
    OllamaClipSelector,
    create_clip_selector,
)
from app.services.compact_selection import (
    COMPACT_SYSTEM_PROMPT,
    CompactOllamaClipSelector,
    build_compact_candidate,
    build_compact_schema,
    candidates_from_compact_payload,
    find_region,
    fit_within_region,
    load_compact_instructions,
    refine_within_region,
    render_compact_prompt,
)
from app.services.ollama import (
    OllamaChatResult,
    OllamaChatStats,
    OllamaClient,
    OllamaError,
    OllamaMalformedResponse,
)
from app.utils.time import utc_now

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _segment(start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def _speech(
    duration: float,
    sentence: str = "This is a complete sentence about the topic at hand.",
    *,
    sentence_seconds: float = 8.0,
    gap: float = 0.2,
) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    cursor = 0.0
    while cursor + sentence_seconds <= duration + 1e-6:
        segments.append(_segment(cursor, cursor + sentence_seconds - gap, sentence))
        cursor += sentence_seconds
    return segments


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


def _region(
    start: float = 0.0,
    end: float = 30.0,
    *,
    score: float = 50.0,
    unit_spans: tuple[tuple[float, float], ...] | None = None,
) -> CandidateRegion:
    if unit_spans is None:
        # Four ten-second sentences by default.
        unit_spans = tuple(
            (start + index * 10.0, start + (index + 1) * 10.0)
            for index in range(max(1, int(round((end - start) / 10.0))))
        )
    return CandidateRegion(
        start=start,
        end=end,
        text="A transcript sentence for this candidate region.",
        score=score,
        reason="Strong clean sentence boundaries.",
        component_scores={"boundary": 80.0, "speech_density": 70.0},
        unit_spans=unit_spans,
    )


def _clip(start: float, end: float, *, rank: int = 1, score: float = 8.0, hook: str = "a clear insight") -> dict:
    return {
        "rank": rank,
        "start": start,
        "end": end,
        "score": score,
        "category": "insight",
        "hook": hook,
    }


class FakeCompactClient:
    """Stands in for :class:`OllamaClient` and records the request."""

    def __init__(self, responses, *, ready_error: Exception | None = None) -> None:
        self.responses = list(responses)
        self.ready_error = ready_error
        self.calls = 0
        self.prompts: list[str] = []
        self.systems: list[str] = []
        self.schemas: list[dict] = []
        self.num_predicts: list[int | None] = []
        self.closed = False

    def ensure_ready(self):
        if self.ready_error is not None:
            raise self.ready_error

    def chat_json_result(self, *, system, user, schema, num_predict=None):
        self.calls += 1
        self.prompts.append(user)
        self.systems.append(system)
        self.schemas.append(schema)
        self.num_predicts.append(num_predict)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, OllamaChatResult):
            return response
        return OllamaChatResult(
            payload=response,
            stats=OllamaChatStats(
                prompt_eval_count=100,
                prompt_eval_seconds=5.0,
                eval_count=50,
                eval_seconds=2.0,
                total_seconds=7.0,
            ),
        )

    def close(self) -> None:
        self.closed = True


# --------------------------------------------------------------------------
# Schema and prompt shape
# --------------------------------------------------------------------------


def test_compact_schema_contains_only_the_six_required_fields():
    schema = build_compact_schema(5)

    item = schema["properties"]["clips"]["items"]
    assert set(item["properties"]) == {
        "rank",
        "start",
        "end",
        "score",
        "category",
        "hook",
    }
    assert set(item["required"]) == set(item["properties"])
    assert "reason" not in item["properties"]
    assert "scores" not in item["properties"]


def test_compact_prompt_puts_static_instructions_first(settings: Settings):
    instructions = load_compact_instructions()

    first = render_compact_prompt(instructions, [_region(0, 30)], 120.0, settings)
    second = render_compact_prompt(
        instructions, [_region(100, 140, score=70)], 900.0, settings
    )

    static_prefix = instructions.rstrip()
    assert first.startswith(static_prefix)
    assert second.startswith(static_prefix)
    assert first[: len(static_prefix)] == second[: len(static_prefix)]
    # The variable data comes after the static block, not before it.
    assert first.index("Candidate regions:") > len(static_prefix)


# --------------------------------------------------------------------------
# Region matching and containment
# --------------------------------------------------------------------------


def test_proposal_inside_a_region_needs_no_clamp():
    region = _region(0, 30)

    matched, needs_clamp = find_region(5.0, 25.0, [region])

    assert matched is region
    assert needs_clamp is False


def test_proposal_outside_every_region_is_rejected():
    matched, _ = find_region(80.0, 110.0, [_region(0, 30), _region(40, 70)])

    assert matched is None


def test_mostly_overlapping_proposal_is_clamped_into_its_region():
    region = _region(0, 30)

    matched, needs_clamp = find_region(5.0, 35.0, [region])

    assert matched is region
    assert needs_clamp is True


def test_clamped_candidate_never_exceeds_its_region(settings: Settings):
    region = _region(0, 30)
    proposal = CompactClipProposal(**_clip(5.0, 35.0))

    candidate = build_compact_candidate(proposal, [region], 300.0, settings)

    assert candidate is not None
    assert region.start <= candidate.start
    assert candidate.end <= region.end


def test_timestamp_outside_all_regions_produces_no_candidate(settings: Settings):
    region = _region(0, 30)
    proposal = CompactClipProposal(**_clip(40.0, 70.0))

    assert build_compact_candidate(proposal, [region], 300.0, settings) is None


def test_refinement_snaps_to_sentence_edges_inside_the_region():
    region = _region(
        0,
        40,
        unit_spans=((0.0, 10.0), (10.0, 20.0), (20.0, 30.0), (30.0, 40.0)),
    )

    start, end = refine_within_region(12.0, 27.0, region)

    assert (start, end) == (10.0, 30.0)
    assert region.start <= start < end <= region.end


def test_refinement_cannot_leave_the_original_region():
    region = _region(
        50,
        90,
        unit_spans=((50.0, 60.0), (60.0, 70.0), (70.0, 80.0), (80.0, 90.0)),
    )

    start, end = refine_within_region(50.5, 89.5, region)

    assert region.start <= start
    assert end <= region.end


def test_fit_enforces_hard_duration_limits_within_the_region(settings: Settings):
    region = _region(0, 30)

    fitted = fit_within_region(0.0, 5.0, region, settings)

    assert fitted is not None
    start, end = fitted
    assert end - start >= settings.clip_hard_min_seconds
    assert end <= region.end


# --------------------------------------------------------------------------
# Payload parsing
# --------------------------------------------------------------------------


def test_valid_payload_produces_a_candidate_with_compact_metadata(settings: Settings):
    region = _region(0, 30, score=60.0)
    payload = {"clips": [_clip(2.0, 28.0, score=9.0, hook="one clear practical insight")]}

    candidates = candidates_from_compact_payload(payload, [region], 300.0, settings)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert region.start <= candidate.start < candidate.end <= region.end
    assert candidate.hook == "one clear practical insight"
    assert len(candidate.hook.split()) <= 6
    assert candidate.component_scores["category"] == "insight"
    assert candidate.component_scores["model_score"] == 90.0


def test_hook_is_truncated_to_six_words(settings: Settings):
    region = _region(0, 30)
    payload = {
        "clips": [
            _clip(2.0, 28.0, hook="this hook is much longer than six words total")
        ]
    }

    candidates = candidates_from_compact_payload(payload, [region], 300.0, settings)

    assert candidates[0].hook.split() == [
        "this",
        "hook",
        "is",
        "much",
        "longer",
        "than",
    ]


def test_duplicate_selections_are_deduplicated(settings: Settings):
    region = _region(0, 40)
    payload = {
        "clips": [
            _clip(2.0, 30.0, rank=1, score=9.0),
            _clip(4.0, 32.0, rank=2, score=8.0),
        ]
    }

    candidates = candidates_from_compact_payload(payload, [region], 300.0, settings)

    assert len(candidates) == 1


def test_candidates_are_ranked_by_final_score(settings: Settings):
    regions = [_region(0, 40, score=50.0), _region(100, 140, score=50.0)]
    payload = {
        "clips": [
            _clip(2.0, 30.0, rank=1, score=6.0),
            _clip(102.0, 130.0, rank=2, score=9.0),
        ]
    }

    candidates = candidates_from_compact_payload(payload, regions, 300.0, settings)

    assert [candidate.score > 70 for candidate in candidates] == [True, False]
    assert candidates[0].score > candidates[1].score
    # Refinement may snap to sentence edges, but it must not switch regions.
    assert regions[1].start <= candidates[0].start < candidates[0].end <= regions[1].end
    assert regions[0].start <= candidates[1].start < candidates[1].end <= regions[0].end


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"clips": None},
        {"clips": "not-a-list"},
        {"clips": [{"start": "bad", "end": 20}]},
        {"clips": [{"rank": 1, "start": 10}]},
        {"clips": [None]},
    ],
)
def test_malformed_payload_returns_empty_without_raising(settings: Settings, payload):
    assert candidates_from_compact_payload(payload, [_region(0, 30)], 300.0, settings) == []


def test_empty_transcript_returns_no_candidates_and_skips_ollama(settings: Settings):
    called = False

    def factory():
        nonlocal called
        called = True
        return FakeCompactClient([{"clips": []}])

    selector = CompactOllamaClipSelector(settings, client_factory=factory)

    assert selector.select(_transcript([], 60), 60) == []
    assert called is False
    assert selector.last_timings.candidate_count == 0


# --------------------------------------------------------------------------
# Selector behaviour
# --------------------------------------------------------------------------


def _selector_with_regions(settings: Settings, duration: float, response):
    segments = _speech(duration)
    regions = generate_candidate_regions(segments, duration, settings)
    assert regions, "fixture transcript produced no candidate regions"
    client = FakeCompactClient([response])
    selector = CompactOllamaClipSelector(settings, client_factory=lambda: client)
    return selector, client, regions, _transcript(segments, duration)


def test_selector_makes_exactly_one_compact_request(settings: Settings):
    segments = _speech(300.0)
    regions = generate_candidate_regions(segments, 300.0, settings)
    payload = {"clips": [_clip(regions[0].start, regions[0].end)]}
    client = FakeCompactClient([payload])
    selector = CompactOllamaClipSelector(settings, client_factory=lambda: client)

    candidates = selector.select(_transcript(segments, 300.0), 300.0)

    assert client.calls == 1
    assert client.closed is True
    assert len(candidates) == 1
    assert regions[0].start <= candidates[0].start < candidates[0].end <= regions[0].end


def test_selector_sends_the_static_system_prompt(settings: Settings):
    selector, client, _regions, transcript = _selector_with_regions(
        settings, 300.0, {"clips": []}
    )
    selector.select(transcript, 300.0)

    assert client.systems == [COMPACT_SYSTEM_PROMPT]
    assert client.schemas[0] == build_compact_schema(settings.clip_max_output)
    assert client.num_predicts[0] is not None
    assert client.num_predicts[0] > 0


def test_selector_uses_the_same_static_prefix_across_videos(settings: Settings):
    instructions = load_compact_instructions().rstrip()
    client = FakeCompactClient([{"clips": []}, {"clips": []}])
    selector = CompactOllamaClipSelector(settings, client_factory=lambda: client)

    for duration in (120.0, 900.0):
        segments = _speech(duration)
        selector.select(_transcript(segments, duration), duration)

    assert client.calls == 2
    for prompt in client.prompts:
        assert prompt.startswith(instructions)
    assert client.prompts[0][: len(instructions)] == client.prompts[1][: len(instructions)]


def test_selector_records_separate_timings(settings: Settings):
    segments = _speech(300.0)
    regions = generate_candidate_regions(segments, 300.0, settings)
    payload = {"clips": [_clip(regions[0].start, regions[0].end)]}
    client = FakeCompactClient([payload])
    selector = CompactOllamaClipSelector(settings, client_factory=lambda: client)

    selector.select(_transcript(segments, 300.0), 300.0)

    timings = selector.last_timings
    assert timings.mode == "compact"
    assert timings.candidate_count == len(regions)
    assert timings.prompt_chars > 0
    assert timings.prompt_tokens_estimated > 0
    assert timings.prompt_eval_tokens == 100
    assert timings.prompt_eval_seconds == 5.0
    assert timings.generation_tokens == 50
    assert timings.generation_seconds == 2.0
    assert timings.candidate_generation_seconds >= 0.0
    assert timings.total_seconds >= timings.prescore_seconds
    assert timings.total_seconds >= timings.validation_seconds


def test_selector_handles_malformed_ollama_response(settings: Settings):
    client = FakeCompactClient(
        [OllamaMalformedResponse("ollama_malformed_response", "Model returned prose.")]
    )
    selector = CompactOllamaClipSelector(settings, client_factory=lambda: client)

    assert selector.select(_transcript(_speech(300.0), 300.0), 300.0) == []
    assert client.closed is True


def test_selector_reports_unavailable_ollama(settings: Settings):
    client = FakeCompactClient(
        [],
        ready_error=OllamaError("ollama_unavailable", "Ollama is not reachable."),
    )
    selector = CompactOllamaClipSelector(settings, client_factory=lambda: client)

    with pytest.raises(ClipSelectionError) as error:
        selector.select(_transcript(_speech(300.0), 300.0), 300.0)

    assert error.value.code == "ollama_unavailable"
    assert client.closed is True


def test_selector_reports_timeout_as_fatal(settings: Settings):
    client = FakeCompactClient(
        [OllamaError("ollama_timeout", "Ollama timed out while selecting clips.")]
    )
    selector = CompactOllamaClipSelector(settings, client_factory=lambda: client)

    with pytest.raises(ClipSelectionError) as error:
        selector.select(_transcript(_speech(300.0), 300.0), 300.0)

    assert error.value.code == "ollama_timeout"


@pytest.mark.parametrize("duration", [90.0, 420.0, 1500.0])
def test_selector_scales_candidate_count_with_video_length(
    settings: Settings, duration: float
):
    segments = _speech(duration)
    regions = generate_candidate_regions(segments, duration, settings)
    client = FakeCompactClient([{"clips": []}])
    selector = CompactOllamaClipSelector(settings, client_factory=lambda: client)

    selector.select(_transcript(segments, duration), duration)

    assert 1 <= selector.last_timings.candidate_count <= settings.clip_max_candidates
    assert selector.last_timings.candidate_count == len(regions)


# --------------------------------------------------------------------------
# Factory and backwards compatibility
# --------------------------------------------------------------------------


def test_factory_returns_compact_selector_by_default(settings: Settings):
    assert isinstance(create_clip_selector(settings), CompactOllamaClipSelector)


def test_factory_keeps_legacy_selector_behind_config(settings: Settings):
    legacy = settings.model_copy(update={"clip_selection_mode": "legacy"})

    assert isinstance(create_clip_selector(legacy), OllamaClipSelector)


def test_chat_json_still_returns_only_the_payload(settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "message": {"content": json.dumps({"clips": []})},
                "prompt_eval_count": 10,
            },
        )

    client = OllamaClient(settings, transport=httpx.MockTransport(handler))
    try:
        assert client.chat_json(system="s", user="u", schema={"type": "object"}) == {
            "clips": []
        }
    finally:
        client.close()


def test_chat_json_result_parses_server_timings(settings: Settings):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "message": {"content": json.dumps({"clips": []})},
                "prompt_eval_count": 2252,
                "prompt_eval_duration": 192_000_000_000,
                "eval_count": 120,
                "eval_duration": 40_000_000_000,
                "total_duration": 240_000_000_000,
                "load_duration": 1_500_000_000,
            },
        )

    client = OllamaClient(settings, transport=httpx.MockTransport(handler))
    try:
        result = client.chat_json_result(
            system="static", user="variable", schema={"type": "object"}, num_predict=320
        )
    finally:
        client.close()

    assert result.payload == {"clips": []}
    assert result.stats.prompt_eval_count == 2252
    assert result.stats.prompt_eval_seconds == 192.0
    assert result.stats.eval_count == 120
    assert result.stats.eval_seconds == 40.0
    assert result.stats.total_seconds == 240.0
    assert result.stats.load_seconds == 1.5
    assert captured["options"]["num_predict"] == 320
    assert captured["options"]["num_ctx"] == settings.ollama_num_ctx
