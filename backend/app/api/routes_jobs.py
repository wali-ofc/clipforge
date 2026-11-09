"""Job status, transcript, and clip listing endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.errors import api_error
from app.models.clip import Clip
from app.models.job import Job
from app.schemas.clip import ClipRead
from app.schemas.job import JobRead
from app.schemas.transcript import Transcript
from app.services.transcription import load_transcript
from app.utils.paths import resolve_stored_path

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
