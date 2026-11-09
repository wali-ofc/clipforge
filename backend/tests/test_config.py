"""Configuration validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import BACKEND_DIR, Settings


def _valid_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "data_dir": Path("./data"),
        "database_url": "sqlite:///./data/test.db",
    }
    values.update(overrides)
    return Settings(**values)


def test_relative_paths_resolve_against_backend_directory():
    settings = _valid_settings()
    assert settings.data_dir == (BACKEND_DIR / "data").resolve()
    assert settings.database_url == (
        f"sqlite:///{(BACKEND_DIR / 'data' / 'test.db').resolve().as_posix()}"
    )


def test_portrait_output_dimensions_are_accepted():
    settings = _valid_settings(output_width=720, output_height=1280)
    assert settings.output_width == 720


@pytest.mark.parametrize(
    ("width", "height"),
    [(1000, 1000), (1920, 1080), (1080, 1081)],
)
def test_invalid_output_dimensions_are_rejected(width: int, height: int):
    with pytest.raises(ValidationError):
        _valid_settings(output_width=width, output_height=height)


def test_extensions_are_normalized_and_deduplicated():
    settings = _valid_settings(
        allowed_video_extensions=[".MP4", "mov", " mp4 ", ".mkv"]
    )
    assert settings.allowed_video_extensions == ["mp4", "mov", "mkv"]


def test_clip_duration_range_is_validated():
    with pytest.raises(ValidationError):
        _valid_settings(min_clip_seconds=60, max_clip_seconds=20)


def test_upload_limit_must_be_positive():
    with pytest.raises(ValidationError):
        _valid_settings(max_upload_bytes=0)


def test_whisper_model_dir_resolves_against_backend_directory():
    settings = _valid_settings()
    assert settings.whisper_model_dir == (BACKEND_DIR / "data" / "models").resolve()


def test_whisper_language_is_normalized():
    assert _valid_settings(whisper_language=" EN ").whisper_language == "en"
    assert _valid_settings(whisper_language="").whisper_language is None


def test_empty_whisper_model_is_rejected():
    with pytest.raises(ValidationError):
        _valid_settings(whisper_model="   ")
