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
    session: Session = Depends(get_session),
) -> FileResponse:
    """Serve a rendered clip file once Phase 5 has produced it."""
    clip = _get_clip_or_404(session, clip_id)
    if not clip.output_filename:
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

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=Path(clip.output_filename).name,
    )
