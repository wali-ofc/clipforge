"""FFprobe-based media inspection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings
from app.utils.subprocesses import (
    CommandError,
    CommandNotFoundError,
    run_command,
)

logger = logging.getLogger(__name__)

# Codecs FFmpeg can decode reliably in this pipeline. Containers are validated
# separately by extension. Anything outside this set gets a clear error rather
# than failing later during rendering.
SUPPORTED_VIDEO_CODECS = frozenset(
    {
        "av1",
        "dnxhd",
        "h263",
        "h264",
        "hevc",
        "mjpeg",
        "mpeg2video",
        "mpeg4",
        "msmpeg4v3",
        "prores",
        "theora",
        "vp8",
        "vp9",
        "wmv3",
    }
)


class MediaProbeError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class MediaInfo:
    duration_seconds: float
    width: int
    height: int
    rotation: int
    video_codec: str
    audio_codec: str | None
    has_audio: bool
    container_format: str
    frame_rate: float | None


def _parse_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_frame_rate(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    if "/" in value:
        numerator, _, denominator = value.partition("/")
        try:
            top = float(numerator)
            bottom = float(denominator)
        except ValueError:
            return None
        if bottom == 0:
            return None
        rate = top / bottom
    else:
        parsed = _parse_float(value)
        rate = parsed if parsed else 0.0

    return round(rate, 3) if 0 < rate <= 1000 else None


def _extract_rotation(stream: dict[str, Any]) -> int:
    rotation = 0.0
    tags = stream.get("tags") or {}
    if "rotate" in tags:
        parsed = _parse_float(tags.get("rotate"))
        if parsed is not None:
            rotation = parsed

    for side_data in stream.get("side_data_list") or []:
        if "rotation" in side_data:
            parsed = _parse_float(side_data.get("rotation"))
            if parsed is not None:
                rotation = parsed

    normalized = int(round(rotation)) % 360
    if normalized > 180:
        normalized -= 360
    return normalized


def probe_media(path: Path, settings: Settings) -> MediaInfo:
    """Inspect a local video file with ffprobe.

    Raises MediaProbeError with a user-facing message for unreadable files,
    missing video streams, missing duration, or unsupported codecs.
    """
    if not path.is_file():
        raise MediaProbeError(
            "file_missing",
            "The uploaded file could not be found on disk. Please upload it again.",
            500,
        )

    args = [
        settings.ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]

    try:
        completed = run_command(args, timeout=settings.ffprobe_timeout_seconds)
    except CommandNotFoundError as exc:
        raise MediaProbeError(
            "ffprobe_missing",
            "ffprobe was not found. Install FFmpeg and add it to PATH, or set "
            "FFPROBE_BIN to the full executable path.",
            503,
        ) from exc
    except CommandError as exc:
        logger.warning(
            "ffprobe could not read %s: %s",
            path.name,
            exc.stderr.strip().splitlines()[-1][:300] if exc.stderr.strip() else "no output",
        )
        raise MediaProbeError(
            "unreadable_media",
            "FFprobe could not read this file. It may be corrupt or use an "
            "unsupported container.",
        ) from exc

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise MediaProbeError(
            "unreadable_media",
            "FFprobe returned an unreadable response for this file.",
        ) from exc

    streams = payload.get("streams") or []
    if not isinstance(streams, list):
        streams = []

    video_streams = [
        stream
        for stream in streams
        if stream.get("codec_type") == "video"
        and (stream.get("disposition") or {}).get("attached_pic") != 1
    ]
    if not video_streams:
        raise MediaProbeError(
            "no_video_stream",
            "This file has no video stream. Upload an MP4, MOV, or MKV containing video.",
        )

    video = video_streams[0]
    video_codec = str(video.get("codec_name") or "unknown").lower()
    if video_codec not in SUPPORTED_VIDEO_CODECS:
        raise MediaProbeError(
            "unsupported_video_codec",
            f"The video codec '{video_codec}' is not supported. Re-encode the file "
            "as H.264 in an MP4 container and try again.",
        )

    try:
        width = int(video.get("width") or 0)
        height = int(video.get("height") or 0)
    except (TypeError, ValueError) as exc:
        raise MediaProbeError(
            "invalid_dimensions", "Could not determine the video dimensions."
        ) from exc

    if width <= 0 or height <= 0:
        raise MediaProbeError(
            "invalid_dimensions", "Could not determine the video dimensions."
        )

    rotation = _extract_rotation(video)
    if abs(rotation) == 90:
        width, height = height, width

    format_info = payload.get("format") or {}
    duration = _parse_float(format_info.get("duration"))
    if duration is None:
        duration = _parse_float(video.get("duration"))
    if duration is None:
        raise MediaProbeError(
            "duration_unknown",
            "The file duration could not be determined. Re-encode the file and try again.",
        )

    audio_streams = [
        stream for stream in streams if stream.get("codec_type") == "audio"
    ]
    audio_codec = (
        str(audio_streams[0].get("codec_name") or "unknown").lower()
        if audio_streams
        else None
    )

    frame_rate = _parse_frame_rate(
        video.get("avg_frame_rate") or video.get("r_frame_rate")
    )

    return MediaInfo(
        duration_seconds=round(duration, 3),
        width=width,
        height=height,
        rotation=rotation,
        video_codec=video_codec,
        audio_codec=audio_codec,
        has_audio=bool(audio_streams),
        container_format=str(format_info.get("format_name") or "unknown")[:128],
        frame_rate=frame_rate,
    )
