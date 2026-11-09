"""Shared pytest fixtures."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
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

        end = max(0.2, min(1.0, float(duration_seconds)))
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
        log_level="WARNING",
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings, transcriber=StubTranscriber())


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def no_speech_client(settings: Settings):
    app = create_app(settings, transcriber=StubTranscriber(has_speech=False))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def failing_client(settings: Settings):
    app = create_app(settings, transcriber=StubTranscriber(fail=True))
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
