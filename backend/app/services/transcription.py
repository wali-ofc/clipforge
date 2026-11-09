"""Faster-Whisper transcription.

Audio is extracted with FFmpeg to a 16 kHz mono WAV in the job work
directory, transcribed on CPU with INT8, and then removed. The resulting
transcript keeps absolute timestamps relative to the source video.

No captions or subtitle files are generated here; the JSON transcript is
internal pipeline data used by later clip-selection phases.
"""

from __future__ import annotations

import gc
import logging
import math
import os
import re
import threading
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

from app.config import Settings
from app.schemas.transcript import Transcript, TranscriptSegment, TranscriptWord
from app.utils.subprocesses import CommandError, CommandNotFoundError, run_command
from app.utils.time import utc_now

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float], None]

# Whisper sometimes emits these markers for silence or non-speech audio.
_NON_SPEECH_MARKERS = re.compile(
    r"\[\s*(?:music|applause|laughter|silence|blank_audio|inaudible|no speech)\s*\]"
    r"|\(\s*(?:music|applause|laughter|silence|inaudible)\s*\)",
    re.IGNORECASE,
)

_MODEL_CACHE: dict[tuple[str, str, str, int, str], Any] = {}
_MODEL_LOCK = threading.Lock()


class TranscriptionError(Exception):
    """A transcription failure with a user-facing message."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class Transcriber(Protocol):
    def transcribe(
        self,
        source_path: Path,
        duration_seconds: float,
        work_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> Transcript:
        """Return a timestamped transcript for the source video."""


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def is_non_speech_text(text: str) -> bool:
    """Return True for blank text or bracketed non-speech markers."""
    if not text.strip():
        return True
    without_markers = _NON_SPEECH_MARKERS.sub(" ", text)
    return not any(character.isalnum() for character in without_markers)


def _sanitize_word(raw: Any, duration: float) -> TranscriptWord | None:
    text = str(getattr(raw, "word", None) or getattr(raw, "text", "") or "").strip()
    if not text:
        return None

    start = _finite_float(getattr(raw, "start", None))
    end = _finite_float(getattr(raw, "end", None))
    if start is None or end is None:
        return None

    start = _clamp(start, 0.0, duration)
    end = _clamp(end, 0.0, duration)
    if end <= start:
        return None

    return TranscriptWord(start=round(start, 3), end=round(end, 3), text=text)


def _sanitize_segment(raw: Any, duration: float) -> TranscriptSegment | None:
    text = str(getattr(raw, "text", "") or "").strip()
    if not text or is_non_speech_text(text):
        return None

    start = _finite_float(getattr(raw, "start", None))
    end = _finite_float(getattr(raw, "end", None))
    if start is None or end is None:
        return None

    start = _clamp(start, 0.0, duration)
    end = _clamp(end, 0.0, duration)
    if end <= start:
        return None

    words: list[TranscriptWord] = []
    for raw_word in getattr(raw, "words", None) or []:
        word = _sanitize_word(raw_word, duration)
        if word is not None:
            words.append(word)
    words.sort(key=lambda word: (word.start, word.end))

    return TranscriptSegment(
        start=round(start, 3),
        end=round(end, 3),
        text=text,
        words=words,
    )


def build_transcript(
    raw_segments: Iterable[Any],
    duration_seconds: float,
    *,
    language: str | None = None,
    language_probability: float | None = None,
    model: str = "unknown",
) -> Transcript:
    """Convert Whisper output objects into the stored transcript schema.

    Timestamps are clamped to the source duration, invalid ranges and
    non-speech markers are dropped, and segments are sorted by start time.
    A transcript with no usable segments is still valid and reports
    ``has_speech=False`` with no language guess.
    """
    duration = max(0.0, _finite_float(duration_seconds) or 0.0)

    segments: list[TranscriptSegment] = []
    for raw in raw_segments:
        segment = _sanitize_segment(raw, duration)
        if segment is not None:
            segments.append(segment)
    segments.sort(key=lambda segment: (segment.start, segment.end))

    if duration <= 0 and segments:
        duration = segments[-1].end

    probability = _finite_float(language_probability)
    if probability is not None:
        probability = _clamp(probability, 0.0, 1.0)

    cleaned_language = (language or "").strip().lower() or None
    if not segments:
        # Language detection on silence is unreliable; report "unknown"
        # rather than a low-confidence guess when there is no speech.
        cleaned_language = None
        probability = None

    return Transcript(
        language=cleaned_language,
        language_probability=probability,
        duration=round(duration, 3),
        model=model,
        has_speech=bool(segments),
        created_at=utc_now(),
        segments=segments,
    )


def save_transcript(transcript: Transcript, path: Path) -> None:
    """Write a transcript atomically so readers never see partial JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    try:
        temporary.write_text(
            transcript.model_dump_json(indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_transcript(path: Path) -> Transcript:
    return Transcript.model_validate_json(path.read_text(encoding="utf-8"))


def extract_audio(
    source_path: Path,
    destination: Path,
    settings: Settings,
    duration_seconds: float,
) -> None:
    """Extract a 16 kHz mono PCM WAV suitable for Whisper."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    args = [
        settings.ffmpeg_bin,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(destination),
    ]
    timeout = max(
        settings.audio_extract_timeout_seconds,
        max(0.0, duration_seconds) * 3,
    )

    try:
        run_command(args, timeout=timeout)
    except CommandNotFoundError as exc:
        raise TranscriptionError(
            "ffmpeg_missing",
            "FFmpeg was not found. Install FFmpeg and add it to PATH, or set "
            "FFMPEG_BIN to the full executable path.",
        ) from exc
    except CommandError as exc:
        logger.warning(
            "Audio extraction failed for %s: %s",
            source_path.name,
            (exc.stderr or "").strip().splitlines()[-1][:300] if exc.stderr else "no output",
        )
        raise TranscriptionError(
            "audio_extraction_failed",
            "Could not extract audio from the source video. The file may be "
            "damaged or use an unsupported audio codec.",
        ) from exc

    if not destination.is_file() or destination.stat().st_size == 0:
        raise TranscriptionError(
            "audio_extraction_failed",
            "FFmpeg produced no audio for this video. It may not contain an "
            "audio stream.",
        )


def _report(callback: ProgressCallback | None, fraction: float) -> None:
    if callback is None:
        return
    callback(_clamp(float(fraction), 0.0, 1.0))


def _load_whisper_model(
    settings: Settings,
    model_factory: Callable[[Settings], Any] | None = None,
) -> Any:
    if model_factory is not None:
        return model_factory(settings)

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise TranscriptionError(
            "whisper_unavailable",
            "Transcription is unavailable because faster-whisper is not "
            "installed. Install backend dependencies and restart the server.",
        ) from exc

    key = (
        settings.whisper_model,
        settings.whisper_device,
        settings.whisper_compute_type,
        settings.whisper_cpu_threads,
        str(settings.whisper_model_dir),
    )

    with _MODEL_LOCK:
        cached = _MODEL_CACHE.get(key)
        if cached is not None:
            return cached

        settings.whisper_model_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Loading Whisper model %s (%s, %s, %d threads)",
            settings.whisper_model,
            settings.whisper_device,
            settings.whisper_compute_type,
            settings.whisper_cpu_threads,
        )
        try:
            model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
                cpu_threads=settings.whisper_cpu_threads,
                download_root=str(settings.whisper_model_dir),
            )
        except Exception as exc:  # noqa: BLE001 - surface an actionable error
            logger.exception("Could not load Whisper model %s", settings.whisper_model)
            detail = str(exc).strip().splitlines()[0][:200] if str(exc).strip() else ""
            suffix = f" ({detail})" if detail else ""
            raise TranscriptionError(
                "whisper_model_unavailable",
                f"Could not load the Whisper model '{settings.whisper_model}'. "
                "The first run downloads the model, so check the internet "
                "connection and free disk space, then retry." + suffix,
            ) from exc

        _MODEL_CACHE[key] = model
        return model


def unload_whisper_models() -> None:
    """Release cached Whisper models (used before loading the LLM)."""
    with _MODEL_LOCK:
        _MODEL_CACHE.clear()
    gc.collect()


class FasterWhisperTranscriber:
    """CPU INT8 transcription through faster-whisper."""

    def __init__(
        self,
        settings: Settings,
        model_factory: Callable[[Settings], Any] | None = None,
    ) -> None:
        self.settings = settings
        self._model_factory = model_factory

    def transcribe(
        self,
        source_path: Path,
        duration_seconds: float,
        work_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> Transcript:
        work_dir.mkdir(parents=True, exist_ok=True)
        audio_path = work_dir / "audio.wav"

        try:
            _report(on_progress, 0.01)
            extract_audio(source_path, audio_path, self.settings, duration_seconds)
            _report(on_progress, 0.04)

            model = _load_whisper_model(self.settings, self._model_factory)

            try:
                segment_iter, info = model.transcribe(
                    str(audio_path),
                    language=self.settings.whisper_language,
                    beam_size=self.settings.whisper_beam_size,
                    vad_filter=self.settings.whisper_vad_filter,
                    word_timestamps=True,
                    # Long local files transcribe more predictably without
                    # carrying context across segments.
                    condition_on_previous_text=False,
                )

                raw_segments: list[Any] = []
                for segment in segment_iter:
                    raw_segments.append(segment)
                    end = _finite_float(getattr(segment, "end", None)) or 0.0
                    if duration_seconds > 0:
                        _report(
                            on_progress,
                            min(0.97, max(0.05, end / duration_seconds)),
                        )
            except TranscriptionError:
                raise
            except Exception as exc:  # noqa: BLE001 - keep worker alive
                logger.exception("Whisper failed for %s", source_path.name)
                raise TranscriptionError(
                    "transcription_failed",
                    "Whisper could not transcribe this video. The audio may be "
                    "damaged or the model may have run out of memory.",
                ) from exc

            _report(on_progress, 1.0)

            return build_transcript(
                raw_segments,
                duration_seconds,
                language=getattr(info, "language", None),
                language_probability=getattr(info, "language_probability", None),
                model=self.settings.whisper_model,
            )
        finally:
            # The WAV is a temporary decoding artifact; later phases can
            # re-extract only the ranges they need.
            audio_path.unlink(missing_ok=True)
