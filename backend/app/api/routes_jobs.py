"""Job status and clip listing endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.errors import api_error
from app.models.clip import Clip
from app.models.job import Job
from app.schemas.clip import ClipRead
from app.schemas.job import JobRead

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
