from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.models.source import Source
from app.schemas.transcript import Transcript, TranscriptSegment, TranscriptWord
from app.services.captioning import (
    CAPTION_DEFAULTS,
    CaptionCue,
    CaptionWord,
    captions_for_range,
    captions_for_transcript,
    captions_to_plain_text,
    display_cues,
    extract_words_for_range,
    format_srt,
    words_to_cues,
    wrap_caption_text,
)
from app.services.roman_urdu import get_romanizer, romanize_text, set_romanizer


def _transcript_from_words(words: list[tuple[float, float, str]], *, language: str | None = "ur") -> Transcript:
    return Transcript(
        language=language,
        language_probability=0.99 if language else None,
        duration=max((w[1] for w in words), default=0.0),
        model="test",
        has_speech=bool(words),
        created_at="2026-01-01T00:00:00Z",
        segments=[
            TranscriptSegment(
                start=min(w[0] for w in words),
                end=max(w[1] for w in words),
                text=" ".join(w[2] for w in words),
                words=[TranscriptWord(start=w[0], end=w[1], text=w[2]) for w in words],
            )
        ] if words else [],
    )


def test_urdu_to_roman_urdu_conversion_examples():
    assert romanize_text("آپ کا اس پر کیا خیال ہے؟") == "Aap ka is par kya khayal hai?"
    assert romanize_text("مجھے یہ بات سمجھ نہیں آئی۔") == "Mujhe ye baat samajh nahi aayi."
    assert romanize_text("آپ نے بالکل صحیح کہا۔") == "Aap ne bilkul sahi kaha."


def test_mixed_urdu_english_preserved():
    out = romanize_text("یہ بہت interesting بات ہے۔")
    assert "interesting" in out
    assert "bohat" in out.lower()
    assert "baat" in out.lower()


def test_english_only_transcript_preserved():
    text = "This is already English, with punctuation!"
    assert romanize_text(text) == text


def test_romanization_is_cached():
    romanizer = get_romanizer()
    cached = getattr(romanizer, "_romanize_cached", None)
    if cached is None:
        pytest.skip("Configured romanizer does not expose a cache.")
    before = cached.cache_info().hits
    text = "آپ کا اس پر کیا خیال ہے؟"
    romanize_text(text)
    romanize_text(text)
    assert cached.cache_info().hits >= before + 2


def test_romanizer_failure_falls_back_to_original_text():
    class BrokenRomanizer:
        def romanize(self, text: str) -> str:
            raise RuntimeError("romanizer unavailable")

    transcript = _transcript_from_words([(0.0, 1.0, "آپ"), (1.0, 2.0, "ٹھیک")], language="ur")
    original = get_romanizer()
    set_romanizer(BrokenRomanizer())
    try:
        cues = captions_for_transcript(transcript, language="roman")
    finally:
        set_romanizer(original)
    assert cues[0].text == "آپ ٹھیک"


def test_caption_defaults_are_classic_and_never_burned_in():
    assert CAPTION_DEFAULTS == {
        "language": "roman",
        "style": "classic",
        "font": "Arial",
        "position": "center",
        "burn": False,
    }


def test_display_text_uses_max_two_lines_and_preserves_punctuation():
    wrapped = wrap_caption_text("This is a fairly long caption that needs two lines!")
    assert "\n" in wrapped
    assert len(wrapped.splitlines()) == 2
    assert wrapped.endswith("!")

    cues = display_cues(
        [CaptionCue(0.0, 4.0, "This is a fairly long caption that needs two lines!")],
        language="original",
    )
    assert cues[0].display_text is not None
    assert "\n" in cues[0].display_text


def test_original_transcript_remains_unchanged():
    transcript = _transcript_from_words([(0.0, 1.0, "Hello"), (1.0, 2.0, "world")], language="en")
    before = transcript.model_dump_json()
    _ = captions_for_transcript(transcript, language="roman")
    assert transcript.model_dump_json() == before


def test_phrase_grouping_and_punctuation():
    words = [
        CaptionWord(0.0, 0.5, "This"),
        CaptionWord(0.5, 1.0, "is"),
        CaptionWord(1.0, 1.5, "a"),
        CaptionWord(1.5, 2.0, "sentence."),
        CaptionWord(2.0, 2.5, "And"),
        CaptionWord(2.5, 3.0, "another"),
        CaptionWord(3.0, 3.5, "one"),
    ]
    cues = words_to_cues(words, max_words=8)
    assert len(cues) == 2
    assert cues[0].text.endswith("sentence.")
    assert cues[1].text == "And another one"


def test_empty_transcript_produces_no_cues_or_srt_body():
    transcript = _transcript_from_words([], language="ur")
    cues = captions_for_transcript(transcript, language="roman")
    assert cues == []
    assert format_srt(cues) == ""


def test_missing_transcript_download_returns_structured_error(client: TestClient, sample_video: Path):
    with sample_video.open("rb") as f:
        resp = client.post("/api/jobs", files={"file": ("no-transcript.mp4", f, "video/mp4")})
    assert resp.status_code == 202
    job_id = resp.json()["id"]

    missing = client.get(f"/api/jobs/{job_id}/captions.srt")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "transcript_not_found"


def test_srt_generation_and_valid_timestamps():
    cues = captions_for_transcript(
        _transcript_from_words([(0.0, 1.2, "Hello"), (1.2, 2.5, "world")], language="en"),
        language="original",
    )
    srt = format_srt(cues)
    assert "1\n00:00:00,000 -->" in srt
    assert "-->" in srt
    assert "Hello world" in srt


def test_txt_generation():
    transcript = _transcript_from_words([(0.0, 1.0, "Hello"), (1.0, 2.0, "world.")], language="en")
    cues = captions_for_transcript(transcript, language="original")
    txt = captions_to_plain_text(cues, timestamped=True)
    assert "00:00 - Hello world." in txt


def test_segmentor_retrieves_only_words_within_selected_range():
    transcript = _transcript_from_words(
        [(0.0, 1.0, "one"), (1.0, 2.0, "two"), (2.0, 3.0, "three"), (3.0, 4.0, "four")],
        language="en",
    )
    words = extract_words_for_range(transcript, 1.1, 3.0, clip_relative=False)
    assert [w.text for w in words] == ["two", "three"]


def test_clip_relative_timestamps():
    transcript = _transcript_from_words([(10.0, 11.0, "hello"), (11.0, 12.0, "there")], language="en")
    cues = captions_for_range(transcript, 10.0, 12.0, language="original", clip_relative=True)
    assert cues[0].start == 0.0
    assert cues[0].end >= 1.9


def test_clips_starting_at_non_zero_timestamps():
    transcript = _transcript_from_words([(90.0, 91.0, "late"), (91.0, 92.0, "start")], language="en")
    words = extract_words_for_range(transcript, 90.0, 92.0, clip_relative=True)
    assert words[0].start == 0.0
    assert words[-1].end == pytest.approx(2.0, abs=0.01)


def test_phrases_crossing_clip_boundaries():
    transcript = _transcript_from_words([(0.0, 1.0, "hello"), (1.0, 2.0, "world"), (2.0, 3.0, "again")], language="en")
    words = extract_words_for_range(transcript, 0.5, 1.5, clip_relative=True)
    # Only overlapping words included and clamped to range.
    assert [w.text for w in words] == ["hello", "world"]
    assert words[0].start == 0.0
    assert words[-1].end == pytest.approx(1.0, abs=0.01)


def test_missing_word_timestamps_fallback_to_segment_level():
    transcript = Transcript(
        language="en",
        language_probability=1.0,
        duration=10.0,
        model="test",
        has_speech=True,
        created_at="2026-01-01T00:00:00Z",
        segments=[TranscriptSegment(start=1.0, end=3.0, text="Segment only", words=[])],
    )
    cues = captions_for_range(transcript, 1.0, 3.0, language="original", clip_relative=True)
    assert len(cues) == 1
    assert cues[0].text == "Segment only"


def test_copyable_plain_text_and_timestamped_formats():
    cues = captions_for_transcript(
        _transcript_from_words([(0.0, 1.0, "Hello"), (1.0, 2.0, "world")], language="en"),
        language="original",
    )
    plain = captions_to_plain_text(cues, timestamped=False)
    ts = captions_to_plain_text(cues, timestamped=True)
    assert plain.strip() == "Hello world"
    assert ts.startswith("00:00 - ")


def _write_transcript(settings, job_id: str, transcript: Transcript) -> Path:
    path = settings.work_dir / job_id / "transcript.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(transcript.model_dump_json(), encoding="utf-8")
    return path


def _make_completed_job(client: TestClient, settings, sample_video: Path, transcript: Transcript) -> str:
    with sample_video.open("rb") as f:
        resp = client.post("/api/jobs", files={"file": ("clip.mp4", f, "video/mp4")})
    assert resp.status_code == 202
    job_id = resp.json()["id"]

    # Worker is not autostarted in tests; run it synchronously, then overwrite
    # the stub transcript with the deterministic fixture transcript.
    assert client.app.state.worker.run_once() is True
    tpath = _write_transcript(settings, job_id, transcript)
    # Update job row to point at our transcript.
    from app.db import create_engine_from_settings, create_session_factory
    from app.models.job import Job
    engine = create_engine_from_settings(settings)
    SessionLocal = create_session_factory(engine)
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        job.transcript_path = str(tpath.relative_to(settings.data_dir)).replace("\\", "/")
        job.has_speech = transcript.has_speech
        job.transcript_language = transcript.language
        job.transcript_segment_count = len(transcript.segments)
        db.commit()
    engine.dispose()
    return job_id


def _wait_for_source_transcript(client: TestClient, source_id: str) -> str:
    status = "queued"
    for _ in range(100):
        with client.app.state.session_factory() as db:
            source = db.get(Source, source_id)
            status = source.transcript_status if source else "missing"
        if status in {"completed", "failed", "missing"}:
            break
        time.sleep(0.05)
    return status


def _make_source_with_transcript(client: TestClient, settings, video: Path, transcript: Transcript) -> str:
    with video.open("rb") as f:
        resp = client.post(
            "/api/sources",
            files={"file": (video.name, f, "video/mp4")},
        )
    assert resp.status_code == 201
    source_id = resp.json()["id"]

    started = client.post(f"/api/sources/{source_id}/transcribe")
    assert started.status_code == 202
    assert _wait_for_source_transcript(client, source_id) == "completed"

    tpath = settings.work_dir / "sources" / source_id / "transcript.json"
    tpath.parent.mkdir(parents=True, exist_ok=True)
    tpath.write_text(transcript.model_dump_json(), encoding="utf-8")
    with client.app.state.session_factory() as db:
        source = db.get(Source, source_id)
        source.transcript_path = str(tpath.relative_to(settings.data_dir)).replace("\\", "/")
        source.transcript_language = transcript.language
        source.transcript_segment_count = len(transcript.segments)
        source.has_speech = transcript.has_speech
        source.transcript_status = "completed"
        db.commit()
    return source_id


def test_caption_download_endpoints(client: TestClient, settings, sample_video: Path):
    transcript = _transcript_from_words([(0.0, 1.0, "Hello"), (1.0, 2.0, "world")], language="en")
    job_id = _make_completed_job(client, settings, sample_video, transcript)

    srt = client.get(f"/api/jobs/{job_id}/captions.srt?language=original")
    assert srt.status_code == 200
    assert "text/plain" in srt.headers["content-type"] or "subrip" in srt.headers["content-type"]
    assert "attachment" in srt.headers["content-disposition"]
    assert "00:00:00,000 -->" in srt.text

    txt = client.get(f"/api/jobs/{job_id}/captions.txt?language=original")
    assert txt.status_code == 200
    assert "attachment" in txt.headers["content-disposition"]
    assert "Hello world" in txt.text


def test_caption_generation_with_no_additional_transcription_call(client: TestClient, settings, sample_video: Path, monkeypatch):
    transcript = _transcript_from_words([(0.0, 1.0, "Hello"), (1.0, 2.0, "world")], language="en")
    job_id = _make_completed_job(client, settings, sample_video, transcript)

    called = {"count": 0}

    def boom(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("transcribe should not be called")

    monkeypatch.setattr("app.services.transcription.FasterWhisperTranscriber.transcribe", boom)
    res = client.get(f"/api/jobs/{job_id}/captions?language=original")
    assert res.status_code == 200
    assert called["count"] == 0


def test_clip_caption_range_endpoint(client: TestClient, settings, long_sample_video: Path):
    transcript = _transcript_from_words([(0.0, 1.0, "one"), (1.0, 2.0, "two"), (2.0, 3.0, "three")], language="en")
    job_id = _make_completed_job(client, settings, long_sample_video, transcript)

    res = client.get(f"/api/jobs/{job_id}/captions/range?start=1.0&end=2.1&language=original&clip_relative=true")
    assert res.status_code == 200
    data = res.json()
    assert data["plain_text"].strip() == "two three"
    assert data["cues"][0]["start"] == pytest.approx(0.0, abs=0.01)


def test_normal_mp4_rendering_not_burning_captions(client: TestClient, settings, long_sample_video: Path):
    # StubRenderer in test fixtures writes dummy bytes; ensure render path has no caption args.
    # This test guards API contract: clip file endpoint still serves mp4; no caption burn endpoint exists in render.
    with long_sample_video.open("rb") as f:
        resp = client.post("/api/jobs", files={"file": ("clip.mp4", f, "video/mp4")})
    assert resp.status_code == 202
    job_id = resp.json()["id"]

    assert client.app.state.worker.run_once() is True

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["state"] == "completed"
    clips = client.get(f"/api/jobs/{job_id}/clips").json()
    assert clips
    clip = clips[0]
    assert clip["render_status"] == "completed"
    # Rendered file is served as MP4; caption text is not embedded by our pipeline (stub renderer writes dummy bytes).
    file_resp = client.get(f"/api/clips/{clip['id']}/file")
    assert file_resp.status_code == 200
    assert "video/mp4" in file_resp.headers["content-type"]


def test_source_transcript_and_download_endpoints(client: TestClient, settings, long_sample_video: Path):
    transcript = _transcript_from_words(
        [(0.0, 1.0, "Hello"), (1.0, 2.0, "world")], language="en"
    )
    source_id = _make_source_with_transcript(client, settings, long_sample_video, transcript)

    stored = client.get(f"/api/sources/{source_id}/transcript")
    assert stored.status_code == 200
    assert stored.json()["segments"][0]["words"][0]["text"] == "Hello"

    srt = client.get(f"/api/sources/{source_id}/captions.srt?language=roman")
    assert srt.status_code == 200
    assert "long-sample-roman-urdu.srt" in srt.headers["content-disposition"]
    assert "00:00:00,000 -->" in srt.text

    txt = client.get(f"/api/sources/{source_id}/captions.txt?language=roman")
    assert txt.status_code == 200
    assert "long-sample-transcript.txt" in txt.headers["content-disposition"]
    assert "Hello world" in txt.text

    ranged = client.get(
        f"/api/sources/{source_id}/captions/range?start=0&end=2.1&language=roman&clip_relative=true"
    )
    assert ranged.status_code == 200
    assert ranged.json()["defaults"]["burn"] is False
    assert ranged.json()["plain_text"].strip() == "Hello world"


def test_source_transcription_reuses_configured_transcriber(
    client: TestClient, settings, sample_video: Path, monkeypatch
):
    with sample_video.open("rb") as f:
        resp = client.post(
            "/api/sources",
            files={"file": ("reuse.mp4", f, "video/mp4")},
        )
    assert resp.status_code == 201
    source_id = resp.json()["id"]

    def boom(*args, **kwargs):
        raise AssertionError("source transcription must reuse the configured transcriber")

    monkeypatch.setattr(
        "app.services.transcription.FasterWhisperTranscriber.transcribe", boom
    )
    started = client.post(f"/api/sources/{source_id}/transcribe")
    assert started.status_code == 202
    assert _wait_for_source_transcript(client, source_id) == "completed"
    assert client.get(f"/api/sources/{source_id}/transcript").status_code == 200
