"""Filesystem path helpers.

Uploads and generated artifacts are always addressed through a job UUID. The
original filename is retained only as display metadata and is never used to
build a storage path.
"""

from __future__ import annotations

from pathlib import Path

from app.config import Settings


def ensure_data_dirs(settings: Settings) -> None:
    for directory in (settings.uploads_dir, settings.work_dir, settings.clips_dir):
        directory.mkdir(parents=True, exist_ok=True)


def job_upload_dir(settings: Settings, job_id: str) -> Path:
    return settings.uploads_dir / job_id


def job_work_dir(settings: Settings, job_id: str) -> Path:
    return settings.work_dir / job_id


def job_clips_dir(settings: Settings, job_id: str) -> Path:
    return settings.clips_dir / job_id


def relative_to_data_dir(settings: Settings, path: Path) -> str:
    """Return a POSIX-style path relative to the managed data directory."""
    return path.resolve().relative_to(settings.data_dir.resolve()).as_posix()


def resolve_stored_path(settings: Settings, stored_path: str) -> Path:
    """Resolve a stored relative path and refuse anything outside data_dir."""
    candidate = (settings.data_dir / stored_path).resolve()
    try:
        candidate.relative_to(settings.data_dir.resolve())
    except ValueError as exc:
        raise ValueError("Stored path escapes the managed data directory.") from exc
    return candidate
