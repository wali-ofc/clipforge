"""Streamed video upload and job creation."""

from __future__ import annotations

import errno
import json
import logging
import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_session
from app.api.errors import api_error
from app.config import Settings
from app.models.job import Job, JobKind, JobState
from app.schemas.job import JobRead
from app.services.media_probe import MediaProbeError, probe_media
from app.services.tooling import media_tools_available
from app.utils.files import (
    EmptyUpload,
    UploadTooLarge,
    file_extension,
    human_size,
    remove_tree,
    sanitize_display_filename,
    stream_upload_to_path,
)
from app.utils.paths import job_upload_dir, relative_to_data_dir
from app.utils.time import utc_now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["jobs"])


@router.post("/jobs", response_model=JobRead, status_code=202)
async def create_job(
    request: Request,
    file: UploadFile = File(...),
    kind: str = Form(JobKind.ai_clipper.value),
    speaker_tracking: bool = Form(True),
    segment_spec: str | None = Form(None),
    segment_output_frame: str = Form("original"),
    session: Session = Depends(get_session),
) -> Job:
    """Accept a streamed upload, validate it with ffprobe, and queue a job."""
    settings: Settings = request.app.state.settings

    if settings.min_free_disk_bytes > 0:
        try:
            free_bytes = shutil.disk_usage(settings.data_dir).free
        except OSError:
            free_bytes = None
        if free_bytes is not None and free_bytes < settings.min_free_disk_bytes:
            raise api_error(
                507,
                "insufficient_disk_space",
                "Not enough free disk space to accept an upload. At least "
                f"{human_size(settings.min_free_disk_bytes)} must be free on "
                f"the data drive; {human_size(free_bytes)} is available.",
            )

    tools = getattr(request.app.state, "media_tools", None)
    if tools is None or not media_tools_available(tools):
        detail = next(
            (
                check.detail
                for check in (tools or {}).values()
                if not check.available and check.detail
            ),
            "FFmpeg and ffprobe are required to inspect uploads.",
        )
        raise api_error(503, "media_tools_unavailable", detail)

    try:
        job_kind = JobKind(kind)
    except Exception:
        await file.close()
        raise api_error(400, "invalid_job_kind", "Unsupported job kind.")

    normalized_segment_spec: str | None = None
    normalized_segment_frame: str | None = None
    segment_options: dict[str, object] = {}
    if job_kind == JobKind.segmenter:
        spec = (segment_spec or "").strip()
        if not spec:
            await file.close()
            raise api_error(
                400,
                "missing_segment_spec",
                "Provide timestamps to segment (one range per line for separate clips, or comma-separated ranges in a line/group to join into one clip).",
            )
        frame = (segment_output_frame or "original").strip().lower()
        if frame not in {"original", "portrait_9_16"}:
            await file.close()
            raise api_error(
                400,
                "invalid_segment_frame",
                "Segment output frame must be 'original' or 'portrait_9_16'.",
            )
        normalized_segment_spec = spec
        normalized_segment_frame = frame
        segment_options = {"output_frame": frame}

    original_filename = sanitize_display_filename(file.filename or "upload")
    extension = file_extension(file.filename or original_filename)
    if extension not in settings.allowed_video_extensions:
        await file.close()
        raise api_error(
            415,
            "unsupported_file_type",
            "Unsupported file type. Upload one of: "
            f"{settings.allowed_video_extensions_display}.",
        )

    job_id = str(uuid.uuid4())
    upload_dir = job_upload_dir(settings, job_id)
    temporary_path = upload_dir / f"upload.{extension}.part"
    final_path = upload_dir / f"source.{extension}"
    job_created = False

    try:
        try:
            size_bytes = await run_in_threadpool(
                stream_upload_to_path,
                file.file,
                temporary_path,
                max_bytes=settings.max_upload_bytes,
                chunk_bytes=settings.upload_chunk_bytes,
            )
        except UploadTooLarge as exc:
            raise api_error(
                413,
                "file_too_large",
                f"The upload exceeds the maximum size of {human_size(exc.max_bytes)}.",
            ) from exc
        except EmptyUpload as exc:
            raise api_error(
                400, "empty_file", "The uploaded file is empty."
            ) from exc

        try:
            media_info = await run_in_threadpool(
                probe_media, temporary_path, settings
            )
        except MediaProbeError as exc:
            raise api_error(exc.status_code, exc.code, exc.message) from exc

        os.replace(temporary_path, final_path)

        stage = (
            "Queued for segmenting"
            if job_kind == JobKind.segmenter
            else "Queued for inspection"
        )
        job = Job(
            id=job_id,
            original_filename=original_filename,
            stored_path=relative_to_data_dir(settings, final_path),
            content_type=file.content_type,
            size_bytes=size_bytes,
            kind=job_kind.value,
            state=JobState.queued.value,
            progress=0,
            stage_message=stage,
            duration_seconds=media_info.duration_seconds,
            width=media_info.width,
            height=media_info.height,
            rotation=media_info.rotation,
            video_codec=media_info.video_codec,
            audio_codec=media_info.audio_codec,
            has_audio=media_info.has_audio,
            container_format=media_info.container_format,
            frame_rate=media_info.frame_rate,
            speaker_tracking_enabled=bool(speaker_tracking)
            if job_kind == JobKind.ai_clipper
            else False,
            segment_spec=normalized_segment_spec,
            segment_output_frame=normalized_segment_frame,
            segment_options=segment_options,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(job)
        session.commit()
        job_created = True
        logger.info(
            "Created %s job %s for %s (%s, %.1f s)",
            job.kind,
            job_id,
            original_filename,
            human_size(size_bytes),
            media_info.duration_seconds,
        )
        return job
    except HTTPException:
        session.rollback()
        raise
    except OSError as exc:
        session.rollback()
        if exc.errno == errno.ENOSPC:
            logger.error("Upload for job %s ran out of disk space", job_id)
            raise api_error(
                507,
                "insufficient_disk_space",
                "The data drive ran out of space while saving the upload. "
                "Free some space and try again.",
            ) from exc
        logger.exception("Unexpected upload I/O failure for job %s", job_id)
        raise api_error(
            500,
            "upload_failed",
            "The upload could not be saved. Check the backend logs and try again.",
        ) from exc
    except Exception as exc:  # noqa: BLE001 - convert unexpected failures to API errors
        session.rollback()
        logger.exception("Unexpected upload failure for job %s", job_id)
        raise api_error(
            500,
            "upload_failed",
            "The upload could not be saved or inspected. Check the backend logs "
            "and try again.",
        ) from exc
    finally:
        if not job_created:
            remove_tree(upload_dir)
        await file.close()
