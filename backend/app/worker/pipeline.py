"""Phase 1 pipeline: validate a persisted upload and persist media metadata."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.job import Job, JobState
from app.services.media_probe import MediaProbeError, probe_media
from app.utils.paths import resolve_stored_path
from app.utils.time import utc_now

logger = logging.getLogger(__name__)


def apply_progress(
    job: Job,
    progress: int,
    stage_message: str,
    state: JobState | None = None,
) -> None:
    """Advance progress monotonically and update the human-readable stage."""
    bounded = max(0, min(100, int(progress)))
    job.progress = max(job.progress, bounded)
    job.stage_message = stage_message[:255]
    if state is not None:
        job.state = state.value
    job.updated_at = utc_now()


def claim_next_queued_job(session: Session) -> Job | None:
    """Claim the oldest queued job for this single worker."""
    from sqlalchemy import select

    job = session.execute(
        select(Job)
        .where(Job.state == JobState.queued.value)
        .order_by(Job.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()

    if job is None:
        return None

    job.started_at = utc_now()
    apply_progress(job, 5, "Inspecting source video", JobState.inspecting)
    session.commit()
    session.refresh(job)
    return job


def process_job(session: Session, job: Job, settings: Settings) -> None:
    """Run the Phase 1 inspection pipeline for a claimed job.

    Later phases will continue from this point with transcription, selection,
    tracking, and rendering.
    """
    job_id = job.id

    try:
        source_path = resolve_stored_path(settings, job.stored_path)
        info = probe_media(source_path, settings)

        job.duration_seconds = info.duration_seconds
        job.width = info.width
        job.height = info.height
        job.rotation = info.rotation
        job.video_codec = info.video_codec
        job.audio_codec = info.audio_codec
        job.has_audio = info.has_audio
        job.container_format = info.container_format
        job.frame_rate = info.frame_rate
        job.error = None

        apply_progress(
            job,
            100,
            "Source validated. Automatic clip generation is not enabled in this build phase.",
            JobState.completed,
        )
        job.completed_at = utc_now()
        session.commit()
        logger.info("Job %s inspected and validated", job_id)
    except MediaProbeError as exc:
        _mark_failed(session, job_id, exc.message, stage="Inspection failed")
        logger.warning("Job %s failed inspection: %s", job_id, exc.message)
    except Exception as exc:  # noqa: BLE001 - worker must not crash on one job
        logger.exception("Unexpected error while processing job %s", job_id)
        _mark_failed(
            session,
            job_id,
            f"Unexpected error while inspecting the source: {type(exc).__name__}",
            stage="Inspection failed",
        )


def _mark_failed(session: Session, job_id: str, message: str, *, stage: str) -> None:
    session.rollback()
    current = session.get(Job, job_id)
    if current is None:
        return
    current.state = JobState.failed.value
    current.error = message
    current.stage_message = stage
    current.completed_at = utc_now()
    current.updated_at = utc_now()
    session.commit()
