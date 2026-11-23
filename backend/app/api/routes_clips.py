"""Clip metadata and rendered-file endpoints."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.errors import api_error
from app.models.clip import Clip
from app.models.job import Job
from app.models.source import Source
from app.schemas.clip import ClipRead
from app.services.captioning import CAPTION_DEFAULTS, captions_for_range, captions_to_plain_text
from app.services.transcription import load_transcript
from app.utils.files import sanitize_display_filename
from app.utils.paths import resolve_stored_path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["clips"])


def _get_clip_or_404(session: Session, clip_id: UUID) -> Clip:
    clip = session.get(Clip, str(clip_id))
    if clip is None:
        raise api_error(404, "clip_not_found", "No clip exists with that ID.")
    return clip


def _cue_payload(cue) -> dict:
    return {
        "start": cue.start,
        "end": cue.end,
        "text": cue.text,
        "display_text": cue.display_text or cue.text,
    }


@router.get("/clips/{clip_id}", response_model=ClipRead)
def get_clip(
    clip_id: UUID,
    session: Session = Depends(get_session),
) -> Clip:
    return _get_clip_or_404(session, clip_id)


@router.get("/clips/{clip_id}/file")
def get_clip_file(
    clip_id: UUID,
    request: Request,
    download: bool = False,
    session: Session = Depends(get_session),
) -> FileResponse:
    """Stream or download a rendered 9:16 portrait MP4 clip file.

    The browser never receives a filesystem path. Files are resolved from the
    clip's stored relative path, which is checked against ``DATA_DIR`` before
    use. ``download=true`` switches the response to an attachment with a safe
    name derived from the clip title.
    """
    clip = _get_clip_or_404(session, clip_id)
    if clip.render_status != "completed" or not clip.output_filename:
        raise api_error(
            404,
            "clip_not_rendered",
            "This clip has been proposed but not rendered yet.",
        )

    settings = request.app.state.settings
    try:
        path = resolve_stored_path(settings, clip.output_filename)
    except ValueError as exc:
        logger.error("Clip %s has an unsafe output path", clip.id)
        raise api_error(
            500,
            "clip_unreadable",
            "The stored clip path is invalid.",
        ) from exc

    if not path.is_file():
        raise api_error(
            404,
            "clip_not_rendered",
            "The rendered clip file is missing.",
        )

    safe_name = (
        sanitize_display_filename(f"{clip.title}.mp4")
        if clip.title
        else Path(clip.output_filename).name
    )

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=safe_name,
        content_disposition_type="attachment" if download else "inline",
    )


def _resolve_transcript_for_clip(session: Session, clip: Clip, settings):
    job = session.get(Job, clip.job_id)
    if job is None:
        raise api_error(404, "job_not_found", "The owning job for this clip was not found.")
    transcript_path = job.transcript_path
    if not transcript_path and job.source_id:
        source = session.get(Source, job.source_id)
        if source and source.transcript_path:
            transcript_path = source.transcript_path
    if not transcript_path:
        raise api_error(404, "transcript_not_found", "No transcript is available for this clip yet.")
    try:
        path = resolve_stored_path(settings, transcript_path)
    except ValueError as exc:
        raise api_error(500, "transcript_unreadable", "The stored transcript path is invalid.") from exc
    if not path.is_file():
        raise api_error(404, "transcript_not_found", "The stored transcript file is missing.")
    try:
        return load_transcript(path)
    except Exception as exc:  # noqa: BLE001
        raise api_error(500, "transcript_unreadable", "The stored transcript could not be read.") from exc


@router.get("/clips/{clip_id}/captions")
def get_clip_captions(
    clip_id: UUID,
    request: Request,
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    clip_relative: bool = Query(True),
    session: Session = Depends(get_session),
) -> dict:
    clip = _get_clip_or_404(session, clip_id)
    transcript = _resolve_transcript_for_clip(session, clip, request.app.state.settings)
    cues = captions_for_range(
        transcript,
        float(clip.start_seconds),
        float(clip.end_seconds),
        language=language,
        max_words=max_words,
        clip_relative=clip_relative,
    )
    return {
        "clip_id": clip.id,
        "job_id": clip.job_id,
        "start": float(clip.start_seconds),
        "end": float(clip.end_seconds),
        "clip_relative": clip_relative,
        "language": (language or "roman").lower(),
        "source_language": transcript.language,
        "max_words": max_words,
        "defaults": CAPTION_DEFAULTS,
        "count": len(cues),
        "plain_text": captions_to_plain_text(cues, timestamped=False),
        "timestamped_text": captions_to_plain_text(cues, timestamped=True),
        "cues": [_cue_payload(cue) for cue in cues],
    }
