"""Source projects: upload once, then cut as many timestamp batches as needed."""

from __future__ import annotations

import errno
import logging
import os
import shutil
import threading
import time
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
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
from app.schemas.transcript import Transcript
from app.services.captioning import (
    CAPTION_DEFAULTS,
    captions_for_range,
    captions_for_transcript,
    captions_to_plain_text,
    format_srt,
    format_transcript_txt,
)
from app.services.cleanup import delete_job_files, delete_source_files
from app.services.media_probe import MediaProbeError, probe_media
from app.services.segmenter import SegmentSpecError, parse_segment_spec
from app.services.tooling import media_tools_available
from app.services.transcription import FasterWhisperTranscriber, load_transcript, save_transcript
from app.utils.files import (
    EmptyUpload,
    UploadTooLarge,
    file_extension,
    human_size,
    remove_tree,
    sanitize_display_filename,
    stream_upload_to_path,
)
from app.utils.paths import job_upload_dir, job_work_dir, relative_to_data_dir, resolve_stored_path
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


def _load_source_transcript(source: Source, settings) -> Transcript:
    if not source.transcript_path:
        raise api_error(404, "transcript_not_found", "No transcript is available for this source yet.")
    try:
        path = resolve_stored_path(settings, source.transcript_path)
    except ValueError as exc:
        raise api_error(500, "transcript_unreadable", "The stored transcript path is invalid.") from exc
    if not path.is_file():
        raise api_error(404, "transcript_not_found", "The stored transcript file is missing.")
    try:
        return load_transcript(path)
    except Exception as exc:  # noqa: BLE001
        raise api_error(500, "transcript_unreadable", "The stored transcript could not be read.") from exc


def _source_caption_filename(source: Source, suffix: str) -> str:
    stem = sanitize_display_filename(source.original_filename or "video")
    stem = stem.rsplit(".", 1)[0] if "." in stem else stem
    return sanitize_display_filename(f"{stem}{suffix}")


def _cue_payload(cue) -> dict:
    return {
        "start": cue.start,
        "end": cue.end,
        "text": cue.text,
        "display_text": cue.display_text or cue.text,
    }


@router.get("/sources/{source_id}/transcript", response_model=Transcript)
def get_source_transcript(
    source_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
) -> Transcript:
    source = _get_source_or_404(session, source_id)
    return _load_source_transcript(source, request.app.state.settings)


@router.get("/sources/{source_id}/captions")
def get_source_captions(
    source_id: UUID,
    request: Request,
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    session: Session = Depends(get_session),
) -> dict:
    source = _get_source_or_404(session, source_id)
    transcript = _load_source_transcript(source, request.app.state.settings)
    cues = captions_for_transcript(transcript, language=language, max_words=max_words)
    return {
        "source_id": source.id,
        "language": (language or "roman").lower(),
        "source_language": transcript.language,
        "max_words": max_words,
        "defaults": CAPTION_DEFAULTS,
        "count": len(cues),
        "cues": [_cue_payload(cue) for cue in cues],
    }


@router.get("/sources/{source_id}/captions.srt")
def download_source_captions_srt(
    source_id: UUID,
    request: Request,
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    session: Session = Depends(get_session),
) -> Response:
    source = _get_source_or_404(session, source_id)
    transcript = _load_source_transcript(source, request.app.state.settings)
    cues = captions_for_transcript(transcript, language=language, max_words=max_words)
    body = format_srt(cues)
    filename = _source_caption_filename(source, "-roman-urdu.srt" if (language or "roman").lower() == "roman" else ".srt")
    return Response(
        content=body,
        media_type="application/x-subrip; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sources/{source_id}/captions.txt")
def download_source_captions_txt(
    source_id: UUID,
    request: Request,
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    session: Session = Depends(get_session),
) -> Response:
    source = _get_source_or_404(session, source_id)
    transcript = _load_source_transcript(source, request.app.state.settings)
    cues = captions_for_transcript(transcript, language=language, max_words=max_words)
    body = format_transcript_txt(cues, include_timestamps=True)
    filename = _source_caption_filename(source, "-transcript.txt")
    return Response(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sources/{source_id}/captions/range")
def get_source_caption_range(
    source_id: UUID,
    request: Request,
    start: float = Query(..., ge=0),
    end: float = Query(..., gt=0),
    language: str = Query("roman"),
    max_words: int = Query(8, ge=1, le=20),
    clip_relative: bool = Query(True),
    session: Session = Depends(get_session),
) -> dict:
    source = _get_source_or_404(session, source_id)
    transcript = _load_source_transcript(source, request.app.state.settings)
    duration = float(source.duration_seconds or transcript.duration or 0.0)
    if duration and end > duration + 0.25:
        raise api_error(400, "invalid_range", "End time is beyond the video duration.")
    if end <= start:
        raise api_error(400, "invalid_range", "End time must be after start time.")
    cues = captions_for_range(transcript, start, end, language=language, max_words=max_words, clip_relative=clip_relative)
    return {
        "source_id": source.id,
        "start": start,
        "end": end,
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


def _run_source_transcription(app, source_id: str) -> None:
    settings = app.state.settings
    session_factory = app.state.session_factory
    session = session_factory()
    try:
        source = session.get(Source, source_id)
        if source is None:
            return
        if source.transcript_status == "processing":
            return
        source.transcript_status = "processing"
        source.transcript_error = None
        source.updated_at = utc_now()
        session.commit()

        source_path = resolve_stored_path(settings, source.stored_path)
        work_dir = settings.work_dir / "sources" / source_id
        transcriber = getattr(app.state, "transcriber", None)
        if transcriber is None:
            transcriber = FasterWhisperTranscriber(settings)
        transcript = transcriber.transcribe(
            source_path,
            float(source.duration_seconds or 0.0),
            work_dir,
        )
        transcript_path = work_dir / "transcript.json"
        save_transcript(transcript, transcript_path)

        source.transcript_path = relative_to_data_dir(settings, transcript_path)
        source.transcript_language = transcript.language
        source.transcript_segment_count = len(transcript.segments)
        source.has_speech = transcript.has_speech
        source.transcript_status = "completed"
        source.transcript_error = None
        source.updated_at = utc_now()
        session.commit()
        logger.info("Generated transcript for source %s", source_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Source transcription failed for %s", source_id)
        session.rollback()
        source = session.get(Source, source_id)
        if source is not None:
            source.transcript_status = "failed"
            source.transcript_error = str(exc)[:1000]
            source.updated_at = utc_now()
            session.commit()
    finally:
        session.close()


@router.post("/sources/{source_id}/transcribe", response_model=SourceRead, status_code=202)
def transcribe_source(
    source_id: UUID,
    request: Request,
    session: Session = Depends(get_session),
) -> SourceRead:
    source = _get_source_or_404(session, source_id)
    if source.transcript_status == "processing":
        return _source_read(source, _job_count(session, source.id))
    if source.transcript_path and source.transcript_status == "completed":
        return _source_read(source, _job_count(session, source.id))

    source.transcript_status = "queued"
    source.transcript_error = None
    source.updated_at = utc_now()
    session.commit()
    session.refresh(source)

    thread = threading.Thread(
        target=_run_source_transcription,
        args=(request.app, str(source_id)),
        daemon=True,
        name=f"source-transcribe-{source_id}",
    )
    thread.start()
    return _source_read(source, _job_count(session, source.id))
