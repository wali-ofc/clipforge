"""Job file deletion and startup orphan-directory cleanup.

Every managed artifact lives under ``DATA_DIR`` in a directory named after the
job UUID. Deletion therefore only ever targets a validated UUID child of
``uploads/``, ``work/``, or ``clips/``; it never accepts a user-supplied path.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models.job import Job
from app.utils.paths import job_clips_dir, job_upload_dir, job_work_dir

logger = logging.getLogger(__name__)


def is_job_uuid(value: str) -> bool:
    """Return True when ``value`` is a canonical UUID string."""
    try:
        return str(UUID(str(value))) == str(value)
    except (ValueError, AttributeError, TypeError):
        return False


def _safe_child(base: Path, job_id: str) -> Path:
    """Resolve ``base / job_id`` and refuse anything outside ``base``."""
    resolved_base = base.resolve()
    candidate = (resolved_base / job_id).resolve()
    if candidate.parent != resolved_base:
        raise ValueError("Job directory escapes its managed base directory.")
    return candidate


def job_directories(settings: Settings, job_id: str) -> tuple[Path, Path, Path]:
    """Return the upload, work, and clip directories for a job."""
    if not is_job_uuid(job_id):
        raise ValueError("Job directory names must be UUIDs.")
    return (
        _safe_child(settings.uploads_dir, job_id),
        _safe_child(settings.work_dir, job_id),
        _safe_child(settings.clips_dir, job_id),
    )


def delete_job_files(settings: Settings, job_id: str) -> int:
    """Delete every managed directory for a job. Returns the count removed."""
    try:
        directories = job_directories(settings, job_id)
    except ValueError:
        logger.error("Refusing to delete files for a non-UUID job id: %r", job_id)
        return 0

    removed = 0
    for directory in directories:
        if not directory.exists():
            continue
        try:
            shutil.rmtree(directory)
        except OSError as exc:
            logger.warning(
                "Could not fully remove job directory %s: %s", directory, exc
            )
        else:
            removed += 1
    if removed:
        logger.info("Deleted %d file director(ies) for job %s", removed, job_id)
    return removed


def cleanup_orphan_job_dirs(
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> int:
    """Remove UUID job directories that have no matching database row.

    This recovers disk space after a crash between deleting a row and deleting
    its files. Non-UUID entries (for example a manually placed ``models``
    folder) are never touched.
    """
    with session_factory() as session:
        known_jobs = set(session.execute(select(Job.id)).scalars().all())

    removed = 0
    for base in (settings.uploads_dir, settings.work_dir, settings.clips_dir):
        if not base.is_dir():
            continue
        for entry in base.iterdir():
            if not entry.is_dir():
                continue
            job_id = entry.name
            if not is_job_uuid(job_id) or job_id in known_jobs:
                continue
            try:
                shutil.rmtree(entry)
            except OSError as exc:
                logger.warning("Could not remove orphan directory %s: %s", entry, exc)
            else:
                removed += 1
                logger.warning("Removed orphan job directory %s", entry)

    if removed:
        logger.warning("Removed %d orphan job director(ies) at startup", removed)
    return removed
