"""Filesystem and filename safety tests."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.config import Settings
from app.utils.files import (
    EmptyUpload,
    UploadTooLarge,
    file_extension,
    human_size,
    sanitize_display_filename,
    stream_upload_to_path,
)
from app.utils.paths import resolve_stored_path


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../evil.mp4", "evil.mp4"),
        ("..\\..\\evil.mp4", "evil.mp4"),
        ("/absolute/path/video.mov", "video.mov"),
        ("  my  talk.mkv  ", "my talk.mkv"),
        ("bad\x00name\x1f.mp4", "badname.mp4"),
        ("...", "upload"),
        ("", "upload"),
    ],
)
def test_sanitize_display_filename(raw: str, expected: str):
    assert sanitize_display_filename(raw) == expected


def test_file_extension_is_lowercase():
    assert file_extension("CLIP.MP4") == "mp4"
    assert file_extension("no-extension") == ""


def test_stream_upload_to_path_writes_file(tmp_path: Path):
    destination = tmp_path / "job" / "source.mp4"
    written = stream_upload_to_path(
        io.BytesIO(b"abcdef"), destination, max_bytes=100, chunk_bytes=2
    )
    assert written == 6
    assert destination.read_bytes() == b"abcdef"


def test_stream_upload_rejects_oversized_and_removes_partial_file(tmp_path: Path):
    destination = tmp_path / "job" / "source.mp4"
    with pytest.raises(UploadTooLarge):
        stream_upload_to_path(
            io.BytesIO(b"abcdef"), destination, max_bytes=4, chunk_bytes=2
        )
    assert not destination.exists()


def test_stream_upload_rejects_empty_and_removes_file(tmp_path: Path):
    destination = tmp_path / "job" / "source.mp4"
    with pytest.raises(EmptyUpload):
        stream_upload_to_path(
            io.BytesIO(b""), destination, max_bytes=100, chunk_bytes=2
        )
    assert not destination.exists()


def test_resolve_stored_path_rejects_traversal(tmp_path: Path):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
    )
    with pytest.raises(ValueError):
        resolve_stored_path(settings, "../outside.mp4")


def test_human_size():
    assert human_size(512) == "512 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(5 * 1024**3) == "5.0 GB"
