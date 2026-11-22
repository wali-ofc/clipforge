"""Source projects: upload once, then cut as many timestamp batches as needed."""

from __future__ import annotations

import errno
import logging
import os
import shutil
import time
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_session
from app.api.errors import api_error
from app.config import Settings
from app.models.clip import Clip
from app.models.job import Job, JobKind, JobState
from app.models.source import Source
from app.schemas.job import JobRead
from app.schemas.source import SourceRead
from app.services.cleanup import delete_job_files, delete_source_files
from app.services.media_probe import MediaProbeError, probe_media
from app.services.segmenter import SegmentSpecError, parse_segment_spec
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
router = APIRouter(prefix="/api", tags=["sources"])


def _source_read(source: Source, job_count: int) -> SourceRead:
    return SourceRead.model_validate(source).model_copy(update={"job_count": job_count})


def _get_source_or_404(session: Session, source_id: UUID) -> Source:
    source = session.get(Source, str(source_id))
    if source is None:
        raise api_error(404, "source_not_found", "No source project exists with that ID.")
    return source


def _job_count(session: Session, source_id: str) -> int:
    return int(
        session.execute(
            select(func.count(Job.id)).where(Job.source_id == source_id)
        ).scalar_one()
    )


def _check_upload_preconditions(request: Request, settings: Settings) -> None:
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
                f"{human_size(settings.min_free_disk_bytes)} must be free on the "
                f"data drive; {human_size(free_bytes)} is available.",
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


@router.post("/sources", response_model=SourceRead, status_code=201)
async def create_source(
    request: Request,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> Source:
    """Upload and probe a video once. Later cuts reuse the stored file."""
    settings: Settings = request.app.state.settings
    _check_upload_preconditions(request, settings)

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

    source_id = str(uuid.uuid4())
    upload_dir = job_upload_dir(settings, source_id)
    temporary_path = upload_dir / f"upload.{extension}.part"
    final_path = upload_dir / f"source.{extension}"
    source_created = False

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
            raise api_error(400, "empty_file", "The uploaded file is empty.") from exc

        try:
            info = await run_in_threadpool(probe_media, temporary_path, settings)
        except MediaProbeError as exc:
            raise api_error(exc.status_code, exc.code, exc.message) from exc

        os.replace(temporary_path, final_path)

        source = Source(
            id=source_id,
            original_filename=original_filename,
            stored_path=relative_to_data_dir(settings, final_path),
            content_type=file.content_type,
            size_bytes=size_bytes,
            duration_seconds=info.duration_seconds,
            width=info.width,
            height=info.height,
            rotation=info.rotation,
            video_codec=info.video_codec,
            audio_codec=info.audio_codec,
            has_audio=info.has_audio,
            container_format=info.container_format,
            frame_rate=info.frame_rate,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(source)
        session.commit()
        source_created = True
        logger.info(
            "Created source project %s for %s (%s, %.1f s)",
            source_id,
            original_filename,
            human_size(size_bytes),
            info.duration_seconds,
        )
        return source
    except HTTPException:
        session.rollback()
        raise
    except OSError as exc:
        session.rollback()
        if exc.errno == errno.ENOSPC:
            raise api_error(
                507,
                "insufficient_disk_space",
                "The data drive ran out of space while saving the upload. "
                "Free some space and try again.",
            ) from exc
        logger.exception("Unexpected source upload I/O failure for %s", source_id)
        raise api_error(
            500, "upload_failed", "The upload could not be saved."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.exception("Unexpected source upload failure for %s", source_id)
        raise api_error(
            500, "upload_failed", "The upload could not be saved or inspected."
        ) from exc
    finally:
        if not source_created:
            remove_tree(upload_dir)
        await file.close()


@router.get("/sources", response_model=list[SourceRead])
def list_sources(session: Session = Depends(get_session)) -> list[SourceRead]:
    sources = session.execute(
        select(Source).order_by(Source.created_at.desc())
    ).scalars().all()
    return [_source_read(source, _job_count(session, source.id)) for source in sources]


@router.get("/sources/{source_id}", response_model=SourceRead)
def get_source(
    source_id: UUID, session: Session = Depends(get_session)
) -> SourceRead:
    source = _get_source_or_404(session, source_id)
    return _source_read(source, _job_count(session, source.id))


@router.get("/sources/{source_id}/jobs", response_model=list[JobRead])
def list_source_jobs(
    source_id: UUID, session: Session = Depends(get_session)
) -> list[Job]:
    _get_source_or_404(session, source_id)
    return list(
        session.execute(
            select(Job)
            .where(Job.source_id == str(source_id))
            .order_by(Job.created_at.desc())
        ).scalars().all()
    )


@router.post("/sources/{source_id}/segments", response_model=JobRead, status_code=202)
def create_source_segment(
    source_id: UUID,
    segment_spec: str = Form(...),
    segment_output_frame: str = Form("original"),
    session: Session = Depends(get_session),
) -> Job:
    """Queue a new cut job for an already-uploaded source project."""
    source = _get_source_or_404(session, source_id)
    spec = (segment_spec or "").strip()
    if not spec:
        raise api_error(
            400,
            "missing_segment_spec",
            "Provide timestamps to cut (one range per line, or comma-separated ranges in a line to join).",
        )

    frame = (segment_output_frame or "original").strip().lower()
    if frame not in {"original", "portrait_9_16"}:
        raise api_error(
            400,
            "invalid_segment_frame",
            "Segment output frame must be 'original' or 'portrait_9_16'.",
        )

    try:
        groups = parse_segment_spec(spec, source.duration_seconds)
    except SegmentSpecError as exc:
        raise api_error(400, "invalid_segment_spec", str(exc)) from exc

    now = utc_now()
    job = Job(
        id=str(uuid.uuid4()),
        source_id=source.id,
        original_filename=source.original_filename,
        stored_path=source.stored_path,
        content_type=source.content_type,
        size_bytes=source.size_bytes,
        kind=JobKind.segmenter.value,
        state=JobState.queued.value,
        progress=0,
        stage_message="Queued for segmenting",
        duration_seconds=source.duration_seconds,
        width=source.width,
        height=source.height,
        rotation=source.rotation,
        video_codec=source.video_codec,
        audio_codec=source.audio_codec,
        has_audio=source.has_audio,
        container_format=source.container_format,
        frame_rate=source.frame_rate,
        speaker_tracking_enabled=False,
        segment_spec=spec,
        segment_output_frame=frame,
        segment_options={"output_frame": frame, "group_count": len(groups)},
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.commit()
    logger.info(
        "Queued segment job %s from source %s (%d group(s))",
        job.id,
        source.id,
        len(groups),
    )
    return job


@router.delete("/sources/{source_id}", status_code=204)
def delete_source(
    source_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
) -> None:
    """Cancel and delete every cut job for a source, then its upload."""
    source = _get_source_or_404(session, source_id)
    settings: Settings = request.app.state.settings
    worker = getattr(request.app.state, "worker", None)
    source_key = str(source_id)

    jobs = list(
        session.execute(
            select(Job).where(Job.source_id == source_key)
        ).scalars().all()
    )
    job_ids = [job.id for job in jobs]

    active_jobs = [job for job in jobs if JobState(job.state).is_active]
    if active_jobs:
        deadline = time.monotonic() + max(0.0, settings.delete_cancel_wait_seconds)
        for job in active_jobs:
            job.state = JobState.cancelled.value
            job.stage_message = "Cancelled by user"
            job.error = None
            job.completed_at = job.completed_at or utc_now()
            job.updated_at = utc_now()
            session.commit()
            if worker is not None and worker.request_cancel(job.id):
                remaining = max(0.0, deadline - time.monotonic())
                if not worker.wait_for_job(job.id, remaining):
                    logger.warning(
                        "Source %s job %s did not stop before file deletion",
                        source_key,
                        job.id,
                    )

    session.expire_all()
    if job_ids:
        session.execute(delete(Clip).where(Clip.job_id.in_(job_ids)))
        session.execute(delete(Job).where(Job.id.in_(job_ids)))
    session.execute(delete(Source).where(Source.id == source_key))
    session.commit()

    for job_id in job_ids:
        delete_job_files(settings, job_id, include_upload=False)
    delete_source_files(settings, source_key)
    logger.info("Deleted source %s and %d cut job(s)", source_key, len(job_ids))
