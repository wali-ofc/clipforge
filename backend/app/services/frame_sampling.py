"""Sample frames from candidate clip ranges only.

Phase 4 must never scan the whole source video. FFmpeg seeks to the candidate
start, decodes only the candidate duration, and writes evenly spaced JPEGs at
the configured sampling rate. The caller owns the temporary directory and is
responsible for removing it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.services.face_detection import FaceDetectionError
from app.utils.subprocesses import CommandError, CommandNotFoundError, run_command

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SampledFrame:
    """One decoded frame and its absolute source timestamp."""

    index: int
    time_seconds: float
    path: Path


def sample_clip_frames(
    source_path: Path,
    start_seconds: float,
    end_seconds: float,
    output_dir: Path,
    settings: Settings,
) -> list[SampledFrame]:
    """Extract frames between two source timestamps.

    FFmpeg applies rotation metadata while decoding, so the JPEG dimensions
    match the display orientation used by ``probe_media``.
    """
    duration = max(0.0, float(end_seconds) - float(start_seconds))
    if duration <= 0:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "frame_%06d.jpg"

    args = [
        settings.ffmpeg_bin,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{max(0.0, float(start_seconds)):.3f}",
        "-i",
        str(source_path),
        "-t",
        f"{duration:.3f}",
        "-an",
        "-sn",
        "-vf",
        f"fps={settings.face_sample_fps:g}",
        "-q:v",
        "2",
        str(pattern),
    ]

    timeout = max(120.0, duration * 4.0 + 60.0)
    try:
        run_command(args, timeout=timeout)
    except CommandNotFoundError as exc:
        raise FaceDetectionError(
            "ffmpeg_missing",
            "FFmpeg was not found while sampling frames for speaker tracking. "
            "Install FFmpeg and add it to PATH, or set FFMPEG_BIN.",
        ) from exc
    except CommandError as exc:
        logger.warning(
            "Frame sampling failed for %s (%.2f-%.2f): %s",
            source_path.name,
            start_seconds,
            end_seconds,
            (exc.stderr or "").strip().splitlines()[-1][:300]
            if exc.stderr
            else "no output",
        )
        raise FaceDetectionError(
            "frame_sampling_failed",
            "Could not decode frames from the source video for speaker tracking.",
        ) from exc

    paths = sorted(output_dir.glob("frame_*.jpg"))
    frames: list[SampledFrame] = []
    for index, path in enumerate(paths):
        # FFmpeg's fps filter emits the first frame at the start of the
        # candidate range. The timestamp is clamped to the candidate end.
        timestamp = min(
            float(end_seconds),
            max(0.0, float(start_seconds) + index / settings.face_sample_fps),
        )
        frames.append(
            SampledFrame(index=index, time_seconds=timestamp, path=path)
        )
    return frames
