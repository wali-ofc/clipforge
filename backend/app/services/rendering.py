"""Clip extraction, dynamic 9:16 portrait reframing, and MP4 rendering.

The crop plan stores a smoothed crop centre every sampled frame. Rendering
turns that plan into a small FFmpeg ``sendcmd`` command file: the ``crop``
filter's ``x``/``y`` options are updated at a fixed cadence (25 Hz by default)
while FFmpeg streams the source. This keeps memory flat, avoids a huge
piecewise-linear expression on the command line, and lets FFmpeg hold the last
coordinate between updates.

Tradeoffs:

* The crop updates at ``CROP_COMMAND_STEP_SECONDS`` rather than per output
  frame. At 25 Hz the step is finer than a typical 30 fps frame, so motion is
  visually continuous; the coordinate simply holds until the next command.
* A temporary command file is required. It lives under
  ``data/work/{job_id}/render`` and is removed after the clip finishes.
* Crop *size* is fixed per clip (the plan's geometry is constant), so only the
  top-left ``x``/``y`` change over time.

Every output is probed with ffprobe before it is reported as complete:
dimensions, H.264 video, AAC audio when the source has audio, MP4 container,
and duration all have to match.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from app.config import Settings
from app.models.clip import Clip
from app.services.media_probe import MediaInfo, MediaProbeError, probe_media
from app.services.speaker_tracking import (
    CropPlan,
    compute_crop_geometry,
    interpolate_crop,
)
from app.utils.cancellation import JobCancelled
from app.utils.subprocesses import (
    CommandCancelled,
    CommandError,
    CommandNotFoundError,
    run_command,
)

logger = logging.getLogger(__name__)

# How often the dynamic crop position is refreshed in the sendcmd file.
# 25 Hz is finer than a 30 fps output frame and keeps the file small.
CROP_COMMAND_STEP_SECONDS = 0.04

# A rendered clip may differ slightly from the requested range because of
# keyframe boundaries and AAC priming. These tolerances catch real mistakes
# (wrong source range, truncated output) without rejecting normal encodes.
DURATION_TOLERANCE_SECONDS = 0.6
DURATION_TOLERANCE_RATIO = 0.04


class RenderingError(Exception):
    """A rendering failure with a stable code and user-facing message."""

    def __init__(self, code: str, message: str, status_code: int = 500) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class RenderResult:
    output_path: Path
    width: int
    height: int
    duration_seconds: float
    file_size_bytes: int
    video_codec: str = "h264"
    audio_codec: str | None = "aac"
    frame_rate: float | None = None


class ClipRenderer(Protocol):
    """Renders one candidate clip to a portrait MP4."""

    def render_clip(
        self,
        source_path: Path,
        clip: Clip,
        output_path: Path,
        settings: Settings,
        work_dir: Path,
        *,
        has_audio: bool = True,
        source_width: int | None = None,
        source_height: int | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> RenderResult:
        """Render a single candidate clip to portrait MP4 format."""


def format_sendcmd_path(path: Path) -> str:
    """Format a filesystem path for the FFmpeg ``sendcmd`` filter.

    FFmpeg parses ``:`` as an option separator inside filter arguments, so the
    drive colon on Windows has to be escaped. Forward slashes work on both
    Windows and POSIX.
    """
    posix = path.resolve().as_posix()
    return posix.replace(":", r"\:")


def _even(value: int) -> int:
    """Round down to the nearest even positive integer."""
    return max(2, (int(value) // 2) * 2)


def build_crop_commands_file(
    crop_plan: CropPlan | dict[str, Any] | None,
    duration_seconds: float,
    source_width: int,
    source_height: int,
    crop_w: int,
    crop_h: int,
    command_file_path: Path,
    step_interval: float = CROP_COMMAND_STEP_SECONDS,
) -> int:
    """Write timed crop top-left coordinates for the FFmpeg sendcmd filter.

    The crop centre is interpolated from the clip-relative plan at each step,
    converted to a top-left corner, clamped inside the source, and rounded to
    even coordinates for 4:2:0 chroma. Consecutive identical positions are
    skipped to keep the file small.

    Returns the number of timed commands written.
    """
    duration = max(0.1, float(duration_seconds))
    step = max(0.01, float(step_interval))
    num_steps = max(1, int(math.ceil(duration / step)))

    safe_crop_w = max(2, min(int(crop_w), int(source_width)))
    safe_crop_h = max(2, min(int(crop_h), int(source_height)))
    max_x = max(0, int(source_width) - safe_crop_w)
    max_y = max(0, int(source_height) - safe_crop_h)

    commands: list[str] = []
    last_x: int | None = None
    last_y: int | None = None

    plan = crop_plan
    if plan:
        try:
            interpolate_crop(plan, 0.0)
        except Exception:  # noqa: BLE001 - malformed plan falls back to centre
            logger.warning(
                "Crop plan could not be interpolated; using a centred crop."
            )
            plan = None

    for index in range(num_steps + 1):
        time_seconds = min(duration, index * step)
        center_x = float(source_width) / 2.0
        center_y = float(source_height) / 2.0

        if plan:
            center_x, center_y, _, _ = interpolate_crop(plan, time_seconds)

        top_x = int(round(center_x - safe_crop_w / 2.0))
        top_y = int(round(center_y - safe_crop_h / 2.0))
        top_x = max(0, min(max_x, top_x))
        top_y = max(0, min(max_y, top_y))
        top_x = (top_x // 2) * 2
        top_y = (top_y // 2) * 2

        if index == 0 or top_x != last_x or top_y != last_y:
            commands.append(
                f"{time_seconds:.3f} [enter] crop x {top_x}, crop y {top_y};\n"
            )
            last_x = top_x
            last_y = top_y

    command_file_path.parent.mkdir(parents=True, exist_ok=True)
    command_file_path.write_text("".join(commands), encoding="utf-8")
    return len(commands)


def _verify_output(
    output_path: Path,
    settings: Settings,
    *,
    expected_duration: float,
    expect_audio: bool,
) -> MediaInfo:
    """Probe a rendered file and reject it unless it meets the contract."""
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RenderingError(
            "rendered_file_empty",
            "The rendered clip file is missing or empty.",
        )

    try:
        info = probe_media(output_path, settings)
    except MediaProbeError as exc:
        raise RenderingError(
            "output_unreadable",
            f"The rendered clip could not be verified by ffprobe: {exc.message}",
        ) from exc

    if info.width != settings.output_width or info.height != settings.output_height:
        raise RenderingError(
            "invalid_output_dimensions",
            "The rendered clip is "
            f"{info.width}x{info.height}, expected "
            f"{settings.output_width}x{settings.output_height}.",
        )

    if info.video_codec != "h264":
        raise RenderingError(
            "invalid_video_codec",
            f"The rendered clip uses '{info.video_codec}', expected H.264.",
        )

    if "mp4" not in info.container_format:
        raise RenderingError(
            "invalid_container",
            f"The rendered clip container is '{info.container_format}', expected MP4.",
        )

    if expect_audio:
        if not info.has_audio or info.audio_codec != "aac":
            raise RenderingError(
                "missing_output_audio",
                "The rendered clip is missing the expected AAC audio track.",
            )
    elif info.has_audio:
        raise RenderingError(
            "unexpected_output_audio",
            "The rendered clip has an audio track but the source had none.",
        )

    tolerance = max(
        DURATION_TOLERANCE_SECONDS,
        DURATION_TOLERANCE_RATIO * max(0.0, expected_duration),
    )
    if abs(info.duration_seconds - expected_duration) > tolerance:
        raise RenderingError(
            "invalid_output_duration",
            "The rendered clip is "
            f"{info.duration_seconds:.2f}s, expected about "
            f"{expected_duration:.2f}s.",
        )

    expected_fps = float(settings.output_fps)
    if info.frame_rate is not None and abs(info.frame_rate - expected_fps) > 0.5:
        raise RenderingError(
            "invalid_output_frame_rate",
            f"The rendered clip is {info.frame_rate:.2f} fps, expected "
            f"{expected_fps:.2f} fps.",
        )

    return info


class FFmpegClipRenderer:
    """Renders 9:16 portrait clips with FFmpeg and verifies them with ffprobe."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def render_clip(
        self,
        source_path: Path,
        clip: Clip,
        output_path: Path,
        settings: Settings,
        work_dir: Path,
        *,
        has_audio: bool = True,
        source_width: int | None = None,
        source_height: int | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> RenderResult:
        if not source_path.is_file():
            raise RenderingError(
                "source_missing",
                f"Source file not found at {source_path}",
                status_code=404,
            )

        duration = float(clip.duration_seconds)
        if duration <= 0:
            raise RenderingError(
                "invalid_clip_duration",
                f"Clip duration must be positive, got {duration}",
            )

        src_w = source_width
        src_h = source_height
        if src_w is None or src_h is None or src_w <= 0 or src_h <= 0:
            try:
                info = probe_media(source_path, settings)
                src_w = info.width
                src_h = info.height
            except MediaProbeError as exc:
                raise RenderingError(exc.code, exc.message) from exc

        target_aspect = settings.output_width / settings.output_height
        geometry = compute_crop_geometry(src_w, src_h, target_aspect)

        crop_w = _even(int(round(geometry.width)))
        crop_h = _even(int(round(geometry.height)))
        crop_w = min(crop_w, _even(src_w))
        crop_h = min(crop_h, _even(src_h))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_work_dir = work_dir / "render"
        render_work_dir.mkdir(parents=True, exist_ok=True)
        cmd_file = render_work_dir / f"{clip.id}_commands.txt"

        source_aspect = float(src_w) / float(src_h)
        already_exact_aspect = (
            abs(source_aspect - target_aspect) <= 0.005
            and crop_w >= src_w - 2
            and crop_h >= src_h - 2
        )
        fps = f"{float(settings.output_fps):g}"

        try:
            if already_exact_aspect:
                # The source is already portrait 9:16; only scale it.
                filter_str = (
                    f"fps={fps},"
                    f"scale={settings.output_width}:{settings.output_height}:flags=bicubic,"
                    "setsar=1,format=yuv420p"
                )
            else:
                build_crop_commands_file(
                    clip.crop_plan,
                    duration,
                    src_w,
                    src_h,
                    crop_w,
                    crop_h,
                    cmd_file,
                )
                escaped_path = format_sendcmd_path(cmd_file)
                filter_str = (
                    f"fps={fps},"
                    f"sendcmd=filename='{escaped_path}',"
                    f"crop={crop_w}:{crop_h},"
                    f"scale={settings.output_width}:{settings.output_height}:flags=bicubic,"
                    "setsar=1,format=yuv420p"
                )

            args = [
                settings.ffmpeg_bin,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{float(clip.start_seconds):.3f}",
                "-i",
                str(source_path),
                "-t",
                f"{duration:.3f}",
                "-map",
                "0:v:0",
                "-vf",
                filter_str,
                "-c:v",
                "libx264",
                "-crf",
                str(settings.output_crf),
                "-preset",
                settings.output_preset,
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-sn",
                "-dn",
            ]

            if has_audio:
                args.extend(["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k"])
            else:
                args.append("-an")

            args.append(str(output_path))

            try:
                run_command(
                    args,
                    timeout=settings.render_timeout_seconds,
                    cancel_check=cancel_check,
                )
            except CommandCancelled as exc:
                raise JobCancelled() from exc
            except CommandNotFoundError as exc:
                raise RenderingError(
                    "media_tools_unavailable",
                    "FFmpeg is not installed or not on the PATH.",
                    status_code=503,
                ) from exc
            except CommandError as exc:
                logger.error(
                    "FFmpeg rendering failed for clip %s: %s (stderr: %s)",
                    clip.id,
                    str(exc),
                    exc.stderr,
                )
                raise RenderingError(
                    "rendering_failed",
                    f"FFmpeg failed to render the clip: {exc}",
                ) from exc

            try:
                info = _verify_output(
                    output_path,
                    settings,
                    expected_duration=duration,
                    expect_audio=has_audio,
                )
            except RenderingError:
                output_path.unlink(missing_ok=True)
                raise

            return RenderResult(
                output_path=output_path,
                width=info.width,
                height=info.height,
                duration_seconds=info.duration_seconds,
                file_size_bytes=output_path.stat().st_size,
                video_codec=info.video_codec,
                audio_codec=info.audio_codec,
                frame_rate=info.frame_rate,
            )
        except Exception:
            # Never leave a partial or unverified MP4 behind.
            output_path.unlink(missing_ok=True)
            raise
        finally:
            # The command file is a temporary render artifact.
            cmd_file.unlink(missing_ok=True)
