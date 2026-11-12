"""Job status, transcript, and clip listing endpoints."""

from __future__ import annotations

import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.errors import api_error
from app.models.clip import Clip
from app.models.job import Job, JobState
from app.schemas.clip import ClipRead
from app.schemas.job import JobRead
from app.schemas.transcript import Transcript
from app.services.cleanup import delete_job_files
from app.services.transcription import load_transcript
from app.utils.paths import resolve_stored_path
from app.utils.time import utc_now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["jobs"])


def _get_job_or_404(session: Session, job_id: UUID) -> Job:
    job = session.get(Job, str(job_id))
    if job is None:
        raise api_error(404, "job_not_found", "No job exists with that ID.")
    return job


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(
    job_id: UUID,
    session: Session = Depends(get_session),
) -> Job:
    return _get_job_or_404(session, job_id)


@router.get("/jobs/{job_id}/clips", response_model=list[ClipRead])
def list_job_clips(
    job_id: UUID,
    session: Session = Depends(get_session),
) -> list[Clip]:
    _get_job_or_404(session, job_id)
    result = session.execute(
        select(Clip)
        .where(Clip.job_id == str(job_id))
        .order_by(Clip.start_seconds.asc())
    )
    return list(result.scalars().all())


@router.get("/jobs/{job_id}/transcript", response_model=Transcript)
def get_job_transcript(
    job_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
) -> Transcript:
    """Return the stored timestamped transcript for a job.

    This is internal pipeline data, not a subtitle file. Captions are never
    burned into output videos.
    """
    job = _get_job_or_404(session, job_id)
    if not job.transcript_path:
        raise api_error(
            404,
            "transcript_not_found",
            "No transcript is available for this job yet.",
        )

    settings = request.app.state.settings
    try:
        path = resolve_stored_path(settings, job.transcript_path)
    except ValueError as exc:
        logger.error("Job %s has an unsafe transcript path", job.id)
        raise api_error(
            500,
            "transcript_unreadable",
            "The stored transcript path is invalid.",
        ) from exc

    if not path.is_file():
        raise api_error(
            404,
            "transcript_not_found",
            "The stored transcript file is missing.",
        )

    try:
        return load_transcript(path)
    except Exception as exc:  # noqa: BLE001 - corrupt JSON is a server error
        logger.exception("Could not read transcript for job %s", job.id)
        raise api_error(
            500,
            "transcript_unreadable",
            "The stored transcript could not be read.",
        ) from exc


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(
    job_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
) -> Response:
    """Cancel an active job if needed, then delete its record and media.

    Cancellation is cooperative: the job is marked ``cancelled``, the worker's
    cancel token is set, and the request waits briefly for the pipeline to stop
    touching its files. If the job is already terminal, only the record and
    directories are removed.
    """
    job = _get_job_or_404(session, job_id)
    settings = request.app.state.settings
    worker = getattr(request.app.state, "worker", None)
    job_key = str(job_id)
    state = JobState(job.state)

    processing = bool(worker is not None and worker.is_processing(job_key))
    if not state.is_terminal or processing:
        deadline = time.monotonic() + max(
            0.0, settings.delete_cancel_wait_seconds
        )
        while True:
            current = session.get(Job, job_key)
            if current is None:
                break
            current.state = JobState.cancelled.value
            current.stage_message = "Cancelled by user"
            current.error = None
            current.completed_at = current.completed_at or utc_now()
            current.updated_at = utc_now()
            session.commit()

            if worker is not None:
                worker.request_cancel(job_key)
                remaining = max(0.0, deadline - time.monotonic())
                stopped = worker.wait_for_job(job_key, remaining)
                if not stopped:
                    logger.warning(
                        "Job %s did not stop within %.1f s; deleting its files anyway",
                        job_key,
                        settings.delete_cancel_wait_seconds,
                    )
            break

    session.expire_all()
    session.execute(delete(Clip).where(Clip.job_id == job_key))
    session.execute(delete(Job).where(Job.id == job_key))
    session.commit()

    delete_job_files(settings, job_key)
    logger.info("Deleted job %s and its media", job_key)
    return Response(status_code=204)
