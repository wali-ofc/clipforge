"""Clip metadata and rendered-file endpoints."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.errors import api_error
from app.models.clip import Clip
from app.schemas.clip import ClipRead
from app.utils.files import sanitize_display_filename
from app.utils.paths import resolve_stored_path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["clips"])


def _get_clip_or_404(session: Session, clip_id: UUID) -> Clip:
    clip = session.get(Clip, str(clip_id))
    if clip is None:
        raise api_error(404, "clip_not_found", "No clip exists with that ID.")
    return clip


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
