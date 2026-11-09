"""Processing pipeline.

Phase 1 validates the uploaded source. Phase 2 extracts audio and produces
a timestamped transcript in the job's work directory. Later phases will
continue from the stored transcript.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.job import Job, JobState
from app.schemas.transcript import Transcript
from app.services.media_probe import MediaProbeError, probe_media
from app.services.transcription import (
    FasterWhisperTranscriber,
    Transcriber,
    TranscriptionError,
    build_transcript,
    save_transcript,
)
from app.utils.paths import (
    job_work_dir,
    relative_to_data_dir,
    resolve_stored_path,
)
from app.utils.time import utc_now

logger = logging.getLogger(__name__)


def apply_progress(
    job: Job,
    progress: int,
    stage_message: str,
    state: JobState | None = None,
) -> None:
    """Advance progress monotonically and update the human-readable stage."""
    bounded = max(0, min(100, int(progress)))
    job.progress = max(job.progress, bounded)
    job.stage_message = stage_message[:255]
    if state is not None:
        job.state = state.value
    job.updated_at = utc_now()


def claim_next_queued_job(session: Session) -> Job | None:
    """Claim the oldest queued job for this single worker."""
    from sqlalchemy import select

    job = session.execute(
        select(Job)
        .where(Job.state == JobState.queued.value)
        .order_by(Job.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()

    if job is None:
        return None

    job.started_at = utc_now()
    apply_progress(job, 5, "Inspecting source video", JobState.inspecting)
    session.commit()
    session.refresh(job)
    return job


def process_job(
    session: Session,
    job: Job,
    settings: Settings,
    transcriber: Transcriber | None = None,
) -> None:
    """Run the Phase 2 inspection + transcription pipeline for a job."""
    job_id = job.id

    try:
        source_path = resolve_stored_path(settings, job.stored_path)
        info = probe_media(source_path, settings)

        job.duration_seconds = info.duration_seconds
        job.width = info.width
        job.height = info.height
        job.rotation = info.rotation
        job.video_codec = info.video_codec
        job.audio_codec = info.audio_codec
        job.has_audio = info.has_audio
        job.container_format = info.container_format
        job.frame_rate = info.frame_rate
        job.error = None

        apply_progress(
            job,
            15,
            "Preparing audio for transcription"
            if info.has_audio
            else "No audio stream; skipping speech transcription",
            JobState.transcribing,
        )
        session.commit()

        work_dir = job_work_dir(settings, job_id)

        if info.has_audio:
            active_transcriber = transcriber or FasterWhisperTranscriber(settings)
            transcript = _transcribe_with_progress(
                session,
                job,
                active_transcriber,
                source_path,
                info.duration_seconds,
                work_dir,
            )
        else:
            transcript = build_transcript(
                [],
                info.duration_seconds,
                model=settings.whisper_model,
            )

        apply_progress(job, 98, "Saving transcript", JobState.transcribing)
        session.commit()

        transcript_path = work_dir / "transcript.json"
        save_transcript(transcript, transcript_path)

        job.transcript_path = relative_to_data_dir(settings, transcript_path)
        job.transcript_language = transcript.language
        job.transcript_segment_count = len(transcript.segments)
        job.has_speech = transcript.has_speech
        job.error = None

        if transcript.has_speech:
            language = transcript.language or "unknown language"
            message = (
                f"Transcription complete: {len(transcript.segments)} segments "
                f"in {language}."
            )
        else:
            message = (
                "No useful speech detected. Transcript saved with no segments; "
                "clip selection will need a non-speech fallback."
            )

        apply_progress(job, 100, message, JobState.completed)
        job.completed_at = utc_now()
        session.commit()
        logger.info(
            "Job %s transcribed: %d segments, language=%s, speech=%s",
            job_id,
            len(transcript.segments),
            transcript.language,
            transcript.has_speech,
        )
    except MediaProbeError as exc:
        _mark_failed(session, job_id, exc.message, stage="Inspection failed")
        logger.warning("Job %s failed inspection: %s", job_id, exc.message)
    except TranscriptionError as exc:
        _mark_failed(session, job_id, exc.message, stage="Transcription failed")
        logger.warning("Job %s failed transcription: %s", job_id, exc.message)
    except Exception as exc:  # noqa: BLE001 - worker must not crash on one job
        logger.exception("Unexpected error while processing job %s", job_id)
        _mark_failed(
            session,
            job_id,
            f"Unexpected error while processing the source: {type(exc).__name__}",
            stage="Processing failed",
        )


def _transcribe_with_progress(
    session: Session,
    job: Job,
    transcriber: Transcriber,
    source_path: Path,
    duration_seconds: float,
    work_dir: Path,
) -> Transcript:
    """Run transcription, persisting throttled, monotonic progress updates."""
    last_commit = 0.0
    last_progress = job.progress

    def on_progress(fraction: float) -> None:
        nonlocal last_commit, last_progress

        bounded = max(0.0, min(1.0, float(fraction)))
        progress = 20 + int(round(75 * bounded))
        if progress <= last_progress:
            return

        now = time.monotonic()
        if progress < 95 and now - last_commit < 1.0:
            return

        apply_progress(
            job,
            progress,
            f"Transcribing audio ({progress}%)",
            JobState.transcribing,
        )
        session.commit()
        last_commit = now
        last_progress = progress

    return transcriber.transcribe(
        source_path,
        duration_seconds,
        work_dir,
        on_progress=on_progress,
    )


def _mark_failed(session: Session, job_id: str, message: str, *, stage: str) -> None:
    session.rollback()
    current = session.get(Job, job_id)
    if current is None:
        return
    current.state = JobState.failed.value
    current.error = message
    current.stage_message = stage
    current.completed_at = utc_now()
    current.updated_at = utc_now()
    session.commit()
