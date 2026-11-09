"""Shared pytest fixtures."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.services.clip_selection import (
    ClipSelectionError,
    build_chunks,
    candidates_from_payload,
    deduplicate_candidates,
)
from app.services.transcription import TranscriptionError, build_transcript
from app.utils.subprocesses import command_exists


class StubTranscriber:
    """Deterministic transcriber used by tests; never loads a model."""

    def __init__(self, *, has_speech: bool = True, fail: bool = False) -> None:
        self.has_speech = has_speech
        self.fail = fail

    def transcribe(self, source_path, duration_seconds, work_dir, on_progress=None):
        if on_progress:
            on_progress(0.1)
            on_progress(0.6)

        if self.fail:
            raise TranscriptionError(
                "transcription_failed",
                "Simulated transcription failure.",
            )

        if not self.has_speech:
            return build_transcript(
                [],
                duration_seconds,
                language=None,
                model="stub",
            )

        end = max(0.2, float(duration_seconds))
        midpoint = end / 2
        raw_segments = [
            SimpleNamespace(
                start=0.0,
                end=midpoint,
                text="Hello from the stub transcript.",
                words=[
                    SimpleNamespace(start=0.0, end=midpoint / 2, word="Hello"),
                    SimpleNamespace(
                        start=midpoint / 2,
                        end=midpoint,
                        word="transcript",
                    ),
                ],
            ),
            SimpleNamespace(
                start=midpoint,
                end=end,
                text="Second segment.",
                words=[
                    SimpleNamespace(
                        start=midpoint,
                        end=end,
                        word="Second",
                    )
                ],
            ),
        ]
        return build_transcript(
            raw_segments,
            duration_seconds,
            language="en",
            language_probability=0.99,
            model="stub",
        )


class StubSelector:
    """Deterministic clip selector used by tests; never calls Ollama."""

    def __init__(self, settings: Settings, *, fail: bool = False) -> None:
        self.settings = settings
        self.model_name = "stub-selector"
        self.fail = fail

    def select(self, transcript, duration_seconds, on_progress=None):
        if self.fail:
            raise ClipSelectionError(
                "selection_failed",
                "Simulated clip selection failure.",
            )

        if on_progress:
            on_progress(0.5)
            on_progress(1.0)

        if not transcript.segments:
            return []

        chunks = build_chunks(
            transcript.segments,
            self.settings.clip_window_seconds,
            self.settings.clip_window_overlap_seconds,
        )
        candidates = []
        for chunk in chunks:
            payload = {
                "clips": [
                    {
                        "start": chunk.start,
                        "end": chunk.end,
                        "title": "Stub moment",
                        "hook": "A deterministic stub hook",
                        "reason": "A deterministic stub reason.",
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
            candidates.extend(
                candidates_from_payload(
                    payload,
                    chunk,
                    duration_seconds,
                    self.settings,
                )
            )
        return deduplicate_candidates(candidates, self.settings.max_clips)


def _ffmpeg_command(settings: Settings, args: list[str]) -> list[str]:
    return [
        settings.ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        *args,
    ]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    base = get_settings()
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{(tmp_path / 'clipforge-test.db').as_posix()}",
        worker_autostart=False,
        max_upload_bytes=5 * 1024 * 1024,
        ffmpeg_bin=base.ffmpeg_bin,
        ffprobe_bin=base.ffprobe_bin,
        # Use a closed port so health checks never touch a real Ollama.
        ollama_base_url="http://127.0.0.1:9",
        log_level="WARNING",
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(
        settings,
        transcriber=StubTranscriber(),
        selector=StubSelector(settings),
    )


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def no_speech_client(settings: Settings):
    app = create_app(
        settings,
        transcriber=StubTranscriber(has_speech=False),
        selector=StubSelector(settings),
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def failing_client(settings: Settings):
    app = create_app(
        settings,
        transcriber=StubTranscriber(fail=True),
        selector=StubSelector(settings),
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def failing_selector_client(settings: Settings):
    app = create_app(
        settings,
        transcriber=StubTranscriber(),
        selector=StubSelector(settings, fail=True),
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_video(tmp_path: Path, settings: Settings) -> Path:
    if not command_exists(settings.ffmpeg_bin):
        pytest.skip("ffmpeg is not available")
    path = tmp_path / "sample.mp4"
    subprocess.run(
        _ffmpeg_command(
            settings,
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=24:duration=1",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(path),
            ],
        ),
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def long_sample_video(tmp_path: Path, settings: Settings) -> Path:
    if not command_exists(settings.ffmpeg_bin):
        pytest.skip("ffmpeg is not available")
    path = tmp_path / "long-sample.mp4"
    subprocess.run(
        _ffmpeg_command(
            settings,
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=24:duration=30",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=30",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(path),
            ],
        ),
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def video_without_audio(tmp_path: Path, settings: Settings) -> Path:
    if not command_exists(settings.ffmpeg_bin):
        pytest.skip("ffmpeg is not available")
    path = tmp_path / "video-only.mp4"
    subprocess.run(
        _ffmpeg_command(
            settings,
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=24:duration=1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(path),
            ],
        ),
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def audio_only_file(tmp_path: Path, settings: Settings) -> Path:
    if not command_exists(settings.ffmpeg_bin):
        pytest.skip("ffmpeg is not available")
    path = tmp_path / "audio-only.mp4"
    subprocess.run(
        _ffmpeg_command(
            settings,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=1",
                "-c:a",
                "aac",
                "-vn",
                str(path),
            ],
        ),
        check=True,
        capture_output=True,
    )
    return path
