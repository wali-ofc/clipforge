"""Transcript building, serialization, and audio extraction tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.schemas.transcript import Transcript
from app.services.transcription import (
    FasterWhisperTranscriber,
    build_transcript,
    extract_audio,
    is_non_speech_text,
    load_transcript,
    save_transcript,
)


def _raw_segment(start, end, text, words=None):
    return SimpleNamespace(
        start=start,
        end=end,
        text=text,
        words=[
            SimpleNamespace(start=word_start, end=word_end, word=word)
            for word_start, word_end, word in (words or [])
        ],
    )


def test_build_transcript_keeps_absolute_timestamps_and_words():
    raw = [
        _raw_segment(
            12.4,
            16.8,
            "Most people have no idea.",
            [(12.4, 12.8, "Most"), (12.8, 13.1, "people")],
        ),
        _raw_segment(16.9, 19.0, "Here is why."),
    ]

    transcript = build_transcript(
        raw,
        3600.0,
        language="EN",
        language_probability=0.93,
        model="small",
    )

    assert transcript.language == "en"
    assert transcript.duration == 3600.0
    assert transcript.has_speech is True
    assert transcript.model == "small"
    assert [segment.start for segment in transcript.segments] == [12.4, 16.9]
    assert transcript.segments[0].words[0].text == "Most"
    assert transcript.segments[0].words[0].start == 12.4
    assert transcript.segments[0].end == 16.8


def test_build_transcript_clamps_and_drops_invalid_ranges():
    raw = [
        _raw_segment(-5.0, 2.0, "Negative start", [(-5.0, 2.0, "Negative")]),
        _raw_segment(4.0, 4.0, "Zero length"),
        _raw_segment(5.0, 99.0, "Beyond duration", [(5.0, 99.0, "Beyond")]),
        _raw_segment(6.0, 7.0, "   "),
    ]

    transcript = build_transcript(raw, 10.0, language="en", model="tiny")

    assert len(transcript.segments) == 2
    assert transcript.segments[0].start == 0.0
    assert transcript.segments[0].end == 2.0
    assert transcript.segments[0].words[0].start == 0.0
    assert transcript.segments[0].words[0].end == 2.0
    assert transcript.segments[1].start == 5.0
    assert transcript.segments[1].end == 10.0
    assert transcript.segments[1].words[0].end == 10.0


def test_build_transcript_sorts_segments_by_start():
    raw = [
        _raw_segment(5.0, 6.0, "Second"),
        _raw_segment(1.0, 2.0, "First"),
    ]
    transcript = build_transcript(raw, 10.0, model="tiny")
    assert [segment.text for segment in transcript.segments] == ["First", "Second"]


def test_build_transcript_without_speech_is_valid():
    transcript = build_transcript([], 42.0, language=None, model="small")

    assert transcript.has_speech is False
    assert transcript.segments == []
    assert transcript.duration == 42.0
    assert transcript.language is None


def test_build_transcript_without_speech_discards_language_guess():
    transcript = build_transcript(
        [],
        42.0,
        language="en",
        language_probability=0.31,
        model="small",
    )

    assert transcript.has_speech is False
    assert transcript.language is None
    assert transcript.language_probability is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", True),
        ("   ", True),
        ("[Music]", True),
        ("[Applause] [Music]", True),
        ("(silence)", True),
        ("♪ ♪", True),
        ("...", True),
        ("Hello [Music]", False),
        ("Actual speech.", False),
        ("[Music] then talking", False),
    ],
)
def test_non_speech_detection(text: str, expected: bool):
    assert is_non_speech_text(text) is expected


def test_non_speech_markers_are_removed_from_segments():
    raw = [
        _raw_segment(0.0, 1.0, "[Music]"),
        _raw_segment(1.0, 2.0, "Real words"),
        _raw_segment(2.0, 3.0, "[BLANK_AUDIO]"),
    ]
    transcript = build_transcript(raw, 3.0, model="tiny")
    assert [segment.text for segment in transcript.segments] == ["Real words"]
    assert transcript.has_speech is True


def test_transcript_round_trip_json(tmp_path: Path):
    transcript = build_transcript(
        [
            _raw_segment(
                1.0,
                2.5,
                "Round trip.",
                [(1.0, 1.5, "Round"), (1.5, 2.5, "trip")],
            )
        ],
        3.0,
        language="en",
        language_probability=0.88,
        model="base",
    )
    path = tmp_path / "work" / "job" / "transcript.json"

    save_transcript(transcript, path)
    loaded = load_transcript(path)

    assert loaded.language == "en"
    assert loaded.word_count == 2
    assert loaded.segments[0].words[1].text == "trip"
    assert loaded.created_at == transcript.created_at


def test_transcript_schema_rejects_inverted_ranges():
    with pytest.raises(ValueError):
        Transcript.model_validate(
            {
                "duration": 10.0,
                "model": "tiny",
                "has_speech": True,
                "created_at": "2026-01-01T00:00:00Z",
                "segments": [{"start": 5.0, "end": 4.0, "text": "Bad"}],
            }
        )


def test_extract_audio_creates_pcm_wav(settings: Settings, sample_video: Path, tmp_path: Path):
    destination = tmp_path / "work" / "audio.wav"
    extract_audio(sample_video, destination, settings, 1.0)

    assert destination.is_file()
    assert destination.stat().st_size > 1000


class _FakeModel:
    def __init__(self, segments):
        self.segments = segments
        self.kwargs = None

    def transcribe(self, audio_path, **kwargs):
        assert Path(audio_path).is_file()
        self.kwargs = kwargs
        info = SimpleNamespace(language="en", language_probability=0.95)
        return iter(self.segments), info


def test_faster_whisper_transcriber_uses_model_and_cleans_audio(
    settings: Settings, sample_video: Path, tmp_path: Path
):
    segments = [
        _raw_segment(
            0.0,
            0.5,
            "Generated speech.",
            [(0.0, 0.25, "Generated"), (0.25, 0.5, "speech")],
        )
    ]
    model = _FakeModel(segments)
    transcriber = FasterWhisperTranscriber(
        settings,
        model_factory=lambda _settings: model,
    )
    progress: list[float] = []
    work_dir = tmp_path / "work" / "job"

    transcript = transcriber.transcribe(
        sample_video,
        1.0,
        work_dir,
        on_progress=progress.append,
    )

    assert transcript.has_speech is True
    assert transcript.language == "en"
    assert transcript.segments[0].text == "Generated speech."
    assert model.kwargs is not None
    assert model.kwargs["word_timestamps"] is True
    assert model.kwargs["vad_filter"] is True
    assert model.kwargs["language"] is None
    assert not (work_dir / "audio.wav").exists()
    assert progress == sorted(progress)
    assert progress[-1] == 1.0
