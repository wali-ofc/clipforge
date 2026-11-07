"""FFprobe media inspection tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.services.media_probe import MediaProbeError, probe_media


def test_probe_reads_valid_sample(settings: Settings, sample_video: Path):
    info = probe_media(sample_video, settings)
    assert 0.8 <= info.duration_seconds <= 1.5
    assert (info.width, info.height) == (320, 240)
    assert info.video_codec == "h264"
    assert info.has_audio is True
    assert info.audio_codec == "aac"
    assert info.frame_rate is not None
    assert info.rotation == 0


def test_probe_rejects_corrupt_file(settings: Settings, tmp_path: Path):
    path = tmp_path / "corrupt.mp4"
    path.write_bytes(b"definitely not a video" * 10)
    with pytest.raises(MediaProbeError) as exc_info:
        probe_media(path, settings)
    assert exc_info.value.code == "unreadable_media"


def test_probe_reports_missing_file(settings: Settings, tmp_path: Path):
    with pytest.raises(MediaProbeError) as exc_info:
        probe_media(tmp_path / "missing.mp4", settings)
    assert exc_info.value.code == "file_missing"


def test_probe_rejects_audio_only_file(
    settings: Settings, audio_only_file: Path
):
    with pytest.raises(MediaProbeError) as exc_info:
        probe_media(audio_only_file, settings)
    assert exc_info.value.code == "no_video_stream"
