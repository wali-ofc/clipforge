"""Job status, transcript, and clip listing endpoints."""

from __future__ import annotations

import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.errors import api_error
from app.models.clip import Clip
from app.models.job import Job, JobState
from app.models.source import Source
from app.schemas.clip import ClipRead
from app.schemas.job import JobRead
from app.schemas.transcript import Transcript
from app.services.captioning import (
    CAPTION_DEFAULTS,
    captions_for_range,
    captions_for_transcript,
    captions_to_plain_text,
    format_srt,
    format_transcript_txt,
)
from app.services.cleanup import delete_job_files
from app.services.transcription import load_transcript
from app.utils.files import sanitize_display_filename
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

    The original transcript is preserved; caption/romanization layers are derived
    separately and never overwrite this data.
    """
    job = _get_job_or_404(session, job_id)
    return _resolve_job_transcript(session, job, request.app.state.settings)


def _resolve_job_transcript(session: Session, job: Job, settings) -> Transcript:
    transcript_path = job.transcript_path
    if not transcript_path and job.source_id:
        source = session.get(Source, job.source_id)
        if source and source.transcript_path:
            transcript_path = source.transcript_path
    if not transcript_path:
        raise api_error(
            404,
            "transcript_not_found",
            "No transcript is available for this video yet.",
        )
    return _load_transcript_path(transcript_path, settings, job_id=job.id)


def _load_transcript_path(transcript_path: str, settings, *, job_id: str) -> Transcript:
    try:
        path = resolve_stored_path(settings, transcript_path)
    except ValueError as exc:
        logger.error("Job %s has an unsafe transcript path", job_id)
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
    except Exception as exc:  # noqa: BLE001
        logger.exception("Could not read transcript for job %s", job_id)
        raise api_error(
            500,
            "transcript_unreadable",
            "The stored transcript could not be read.",
        ) from exc


def _caption_filename(job: Job, suffix: str) -> str:
    stem = sanitize_display_filename(job.original_filename or "video")
    stem = stem.rsplit(".", 1)[0] if "." in stem else stem
    return sanitize_display_filename(f"{stem}{suffix}")


def _cue_payload(cue) -> dict:
    return {
        "start": cue.start,
        "end": cue.end,
        "text": cue.text,
        "display_text": cue.display_text or cue.text,
    }


@router.get("/jobs/{job_id}/captions")
def get_job_captions(
    job_id: UUID,
    request: Request,
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    session: Session = Depends(get_session),
) -> dict:
    job = _get_job_or_404(session, job_id)
    transcript = _resolve_job_transcript(session, job, request.app.state.settings)
    cues = captions_for_transcript(transcript, language=language, max_words=max_words)
    return {
        "job_id": job.id,
        "language": (language or "roman").lower(),
        "source_language": transcript.language,
        "max_words": max_words,
        "defaults": CAPTION_DEFAULTS,
        "count": len(cues),
        "cues": [_cue_payload(cue) for cue in cues],
    }


@router.get("/jobs/{job_id}/captions.srt")
def download_job_captions_srt(
    job_id: UUID,
    request: Request,
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    session: Session = Depends(get_session),
) -> Response:
    job = _get_job_or_404(session, job_id)
    transcript = _resolve_job_transcript(session, job, request.app.state.settings)
    cues = captions_for_transcript(transcript, language=language, max_words=max_words)
    body = format_srt(cues)
    filename = _caption_filename(job, "-roman-urdu.srt" if (language or "roman").lower() == "roman" else ".srt")
    return Response(
        content=body,
        media_type="application/x-subrip; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/jobs/{job_id}/captions.txt")
def download_job_captions_txt(
    job_id: UUID,
    request: Request,
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    session: Session = Depends(get_session),
) -> Response:
    job = _get_job_or_404(session, job_id)
    transcript = _resolve_job_transcript(session, job, request.app.state.settings)
    cues = captions_for_transcript(transcript, language=language, max_words=max_words)
    body = format_transcript_txt(cues, include_timestamps=True)
    filename = _caption_filename(job, "-transcript.txt")
    return Response(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/jobs/{job_id}/captions/range")
def get_job_caption_range(
    job_id: UUID,
    request: Request,
    start: float = Query(..., ge=0),
    end: float = Query(..., gt=0),
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    clip_relative: bool = Query(True),
    session: Session = Depends(get_session),
) -> dict:
    job = _get_job_or_404(session, job_id)
    transcript = _resolve_job_transcript(session, job, request.app.state.settings)
    duration = float(job.duration_seconds or transcript.duration or 0.0)
    if duration and end > duration + 0.25:
        raise api_error(400, "invalid_range", "End time is beyond the video duration.")
    if end <= start:
        raise api_error(400, "invalid_range", "End time must be after start time.")
    cues = captions_for_range(
        transcript,
        start,
        end,
        language=language,
        max_words=max_words,
        clip_relative=clip_relative,
    )
    plain = captions_to_plain_text(cues, timestamped=False)
    timestamped = captions_to_plain_text(cues, timestamped=True)
    return {
        "job_id": job.id,
        "start": start,
        "end": end,
        "clip_relative": clip_relative,
        "language": (language or "roman").lower(),
        "source_language": transcript.language,
        "max_words": max_words,
        "defaults": CAPTION_DEFAULTS,
        "count": len(cues),
        "plain_text": plain,
        "timestamped_text": timestamped,
        "cues": [_cue_payload(cue) for cue in cues],
    }


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
    # Source-backed cuts share their upload with the source project, so only
    # standalone jobs own an upload directory. Read this before expire_all().
    include_upload = job.source_id is None

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

    delete_job_files(settings, job_key, include_upload=include_upload)
    logger.info("Deleted job %s and its media", job_key)
    return Response(status_code=204)
