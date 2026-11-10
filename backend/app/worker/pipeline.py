"""Processing pipeline.

Phase 1 validates the uploaded source. Phase 2 extracts audio and produces
a timestamped transcript in the job's work directory. Phase 3 asks a local
Ollama model for candidate moments, validates and refines them, and stores
clip proposals. Later phases will continue from those proposals.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.clip import Clip
from app.models.job import Job, JobState
from app.schemas.transcript import Transcript
from app.services.clip_selection import (
    ClipCandidate,
    ClipSelectionError,
    ClipSelector,
    OllamaClipSelector,
)
from app.services.media_probe import MediaProbeError, probe_media
from app.services.speaker_tracking import (
    OpenCVSpeakerTracker,
    SpeakerTracker,
    build_centered_result,
)
from app.services.transcription import (
    FasterWhisperTranscriber,
    Transcriber,
    TranscriptionError,
    build_transcript,
    save_transcript,
    unload_whisper_models,
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
    selector: ClipSelector | None = None,
    speaker_tracker: SpeakerTracker | None = None,
) -> None:
    """Run inspection, transcription, selection, and crop planning for a job."""
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

        apply_progress(job, 82, "Saving transcript", JobState.transcribing)
        session.commit()

        transcript_path = work_dir / "transcript.json"
        save_transcript(transcript, transcript_path)

        job.transcript_path = relative_to_data_dir(settings, transcript_path)
        job.transcript_language = transcript.language
        job.transcript_segment_count = len(transcript.segments)
        job.has_speech = transcript.has_speech
        job.clip_count = 0
        job.clip_selection_model = None
        job.error = None
        session.commit()

        if transcript.has_speech:
            # Whisper and the local LLM should not both hold memory on a
            # 16 GB machine. Release the cached Whisper model first.
            unload_whisper_models()
            candidates, model_name = _select_clips_with_progress(
                session,
                job,
                settings,
                transcript,
                info.duration_seconds,
                selector,
            )
            _replace_clips(session, job, candidates)
            job.clip_selection_model = model_name
            session.commit()

            if candidates:
                _track_clips_with_progress(
                    session,
                    job,
                    settings,
                    transcript,
                    source_path,
                    speaker_tracker,
                )
                message = (
                    f"Clip selection complete: {len(candidates)} candidate "
                    f"clip(s) proposed by {model_name or 'the selector'}. "
                    "Speaker-aware crop plans generated."
                )
            else:
                message = (
                    "No candidate clips were selected. The transcript may be "
                    "too short or may not contain self-contained moments."
                )
        else:
            message = (
                "No useful speech detected. Transcript saved with no segments; "
                "no clips were selected."
            )

        apply_progress(job, 100, message, JobState.completed)
        job.completed_at = utc_now()
        session.commit()
        logger.info(
            "Job %s processed: %d segments, language=%s, speech=%s, clips=%d",
            job_id,
            len(transcript.segments),
            transcript.language,
            transcript.has_speech,
            job.clip_count,
        )
    except MediaProbeError as exc:
        _mark_failed(session, job_id, exc.message, stage="Inspection failed")
        logger.warning("Job %s failed inspection: %s", job_id, exc.message)
    except TranscriptionError as exc:
        _mark_failed(session, job_id, exc.message, stage="Transcription failed")
        logger.warning("Job %s failed transcription: %s", job_id, exc.message)
    except ClipSelectionError as exc:
        _mark_failed(session, job_id, exc.message, stage="Clip selection failed")
        logger.warning("Job %s failed clip selection: %s", job_id, exc.message)
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
        progress = 20 + int(round(60 * bounded))
        if progress <= last_progress:
            return

        now = time.monotonic()
        if progress < 80 and now - last_commit < 1.0:
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


def _select_clips_with_progress(
    session: Session,
    job: Job,
    settings: Settings,
    transcript: Transcript,
    duration_seconds: float,
    selector: ClipSelector | None,
) -> tuple[list[ClipCandidate], str | None]:
    """Run selection with monotonic progress in the 84-97 range."""
    active_selector = selector or OllamaClipSelector(settings)
    model_name = getattr(active_selector, "model_name", None)

    apply_progress(
        job,
        84,
        "Selecting candidate clips",
        JobState.selecting_clips,
    )
    session.commit()

    def on_progress(fraction: float) -> None:
        bounded = max(0.0, min(1.0, float(fraction)))
        progress = 84 + int(round(13 * bounded))
        if progress <= job.progress:
            return
        apply_progress(
            job,
            progress,
            f"Selecting candidate clips ({progress}%)",
            JobState.selecting_clips,
        )
        session.commit()

    candidates = active_selector.select(
        transcript,
        duration_seconds,
        on_progress=on_progress,
    )
    return candidates, model_name


def _track_clips_with_progress(
    session: Session,
    job: Job,
    settings: Settings,
    transcript: Transcript,
    source_path: Path,
    tracker: SpeakerTracker | None,
) -> None:
    """Plan a speaker-aware crop for every candidate clip.

    A tracking failure is recorded on the clip with a stable centred fallback;
    it never fails the whole job. This keeps fallback behaviour explicit
    instead of silently presenting a static centre crop as tracking.
    """
    active_tracker = tracker or OpenCVSpeakerTracker(settings)
    clips = list(
        session.execute(
            select(Clip)
            .where(Clip.job_id == job.id)
            .order_by(Clip.start_seconds.asc())
        )
        .scalars()
        .all()
    )
    if not clips:
        return

    apply_progress(
        job,
        97,
        "Planning speaker-aware crops",
        JobState.tracking_speakers,
    )
    session.commit()

    tracking_root = job_work_dir(settings, job.id) / "tracking"
    total = len(clips)
    for index, clip in enumerate(clips):
        clip_work_dir = tracking_root / clip.id
        try:
            result = active_tracker.track(
                source_path,
                clip.start_seconds,
                clip.end_seconds,
                job.width or 0,
                job.height or 0,
                transcript,
                clip_work_dir,
            )
            clip.speaker_tracking_status = result.status
            clip.speaker_tracking_confidence = result.confidence
            clip.crop_plan = result.crop_plan
            clip.tracking_details = result.details
        except Exception as exc:  # noqa: BLE001 - fallback per clip
            logger.exception(
                "Speaker tracking failed for clip %s", clip.id
            )
            fallback = build_centered_result(
                clip.start_seconds,
                clip.end_seconds,
                job.width or 0,
                job.height or 0,
                settings,
                status="failed",
                detail=f"Speaker tracking failed: {type(exc).__name__}.",
                error_code="tracking_failed",
            )
            clip.speaker_tracking_status = fallback.status
            clip.speaker_tracking_confidence = fallback.confidence
            clip.crop_plan = fallback.crop_plan
            clip.tracking_details = fallback.details

        clip.updated_at = utc_now()
        progress = 97 + int(round(2 * (index + 1) / total))
        apply_progress(
            job,
            progress,
            f"Planning speaker-aware crops ({index + 1}/{total})",
            JobState.tracking_speakers,
        )
        session.commit()


def _replace_clips(
    session: Session,
    job: Job,
    candidates: list[ClipCandidate],
) -> None:
    """Replace any previous proposals for this job with the new selection."""
    session.execute(delete(Clip).where(Clip.job_id == job.id))
    now = utc_now()
    for candidate in candidates:
        session.add(
            Clip(
                id=str(uuid.uuid4()),
                job_id=job.id,
                start_seconds=candidate.start,
                end_seconds=candidate.end,
                duration_seconds=candidate.duration,
                title=candidate.title[:255],
                hook=candidate.hook or None,
                reason=candidate.reason or None,
                score=candidate.score,
                component_scores=candidate.component_scores,
                speaker_tracking_status="pending",
                speaker_tracking_confidence=None,
                crop_plan={},
                tracking_details={},
                render_status="pending",
                created_at=now,
                updated_at=now,
            )
        )
    job.clip_count = len(candidates)
    session.flush()


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
