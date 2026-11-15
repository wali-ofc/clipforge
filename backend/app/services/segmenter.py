"""Timestamp parsing and segment rendering for the Segmenter tool.

Groups are separated by new lines or semicolons. Within a group, comma-
separated ranges are cut and joined into a single output clip in order.
Each group produces one downloadable clip.

Supported timestamp forms: SS, MM:SS, HH:MM:SS (fractional seconds allowed).
"""

from __future__ import annotations

import logging
import math
import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from app.config import Settings
from app.models.clip import Clip
from app.services.media_probe import MediaProbeError, probe_media
from app.utils.cancellation import JobCancelled
from app.utils.paths import job_clips_dir, job_work_dir, relative_to_data_dir
from app.utils.subprocesses import (
    CommandCancelled,
    CommandError,
    CommandNotFoundError,
    run_command,
)
from app.utils.time import utc_now

logger = logging.getLogger(__name__)

_RANGE_SPLIT = re.compile(r"\s*(?:-|–|—|to)\s*", re.IGNORECASE)


class SegmentSpecError(ValueError):
    """User-correctable timestamp/spec error."""


@dataclass(frozen=True)
class SegmentRange:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(frozen=True)
class SegmentGroup:
    index: int
    ranges: list[SegmentRange]
    joined: bool

    @property
    def start(self) -> float:
        return self.ranges[0].start

    @property
    def end(self) -> float:
        return self.ranges[-1].end

    @property
    def duration(self) -> float:
        return sum(r.duration for r in self.ranges)


def parse_timestamp(value: str) -> float:
    raw = (value or "").strip()
    if not raw:
        raise SegmentSpecError("Empty timestamp.")
    # Allow plain seconds (int/float)
    if re.fullmatch(r"\d+(?:\.\d+)?", raw):
        seconds = float(raw)
    else:
        parts = raw.split(":")
        if len(parts) not in {2, 3} or not all(p.strip() != "" for p in parts):
            raise SegmentSpecError(f"Invalid timestamp '{value.strip()}'.")
        try:
            nums = [float(p.strip()) for p in parts]
        except ValueError as exc:
            raise SegmentSpecError(f"Invalid timestamp '{value.strip()}'.") from exc
        if any(n < 0 for n in nums):
            raise SegmentSpecError(f"Timestamps must be non-negative: '{value.strip()}'.")
        if len(parts) == 3:
            h, m, s = nums
            seconds = h * 3600 + m * 60 + s
        else:
            m, s = nums
            seconds = m * 60 + s
    if not math.isfinite(seconds) or seconds < 0:
        raise SegmentSpecError(f"Invalid timestamp '{value.strip()}'.")
    return seconds


def _format_ts(seconds: float) -> str:
    total_ms = int(round(max(0.0, seconds) * 1000))
    s, ms = divmod(total_ms, 1000)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        base = f"{h}:{m:02d}:{sec:02d}"
    else:
        base = f"{m}:{sec:02d}"
    if ms:
        return f"{base}.{ms:03d}".rstrip("0").rstrip(".")
    return base


def parse_segment_spec(spec: str, source_duration: float | None = None) -> list[SegmentGroup]:
    text = (spec or "").replace("\r\n", "\n").replace("\r", "\n")
    # Groups: new lines or semicolons
    raw_groups = [g.strip() for g in re.split(r"[;\n]+", text) if g.strip()]
    if not raw_groups:
        raise SegmentSpecError(
            "No timestamps provided. Enter one range per line for separate clips, or comma-separated ranges in a line to join them."
        )

    groups: list[SegmentGroup] = []
    for idx, raw_group in enumerate(raw_groups, start=1):
        raw_ranges = [r.strip() for r in raw_group.split(",") if r.strip()]
        if not raw_ranges:
            continue
        ranges: list[SegmentRange] = []
        for raw_range in raw_ranges:
            parts = _RANGE_SPLIT.split(raw_range, maxsplit=1)
            if len(parts) != 2:
                raise SegmentSpecError(
                    f"Group {idx}: '{raw_range}' is not a valid range. Use start-end (e.g. 1:23-2:23)."
                )
            start = parse_timestamp(parts[0])
            end = parse_timestamp(parts[1])
            if end <= start:
                raise SegmentSpecError(
                    f"Group {idx}: range '{raw_range}' must have an end after its start."
                )
            if source_duration is not None and source_duration > 0:
                if start >= source_duration - 0.001:
                    raise SegmentSpecError(
                        f"Group {idx}: start {_format_ts(start)} is at/after the video end ({_format_ts(source_duration)})."
                    )
                if end > source_duration:
                    # clamp small overruns, but keep meaningful; be strict if way over? clamp to duration
                    end = min(end, source_duration)
                if end - start < 0.05:
                    raise SegmentSpecError(
                        f"Group {idx}: range '{raw_range}' is too short after fitting to the video duration."
                    )
            ranges.append(SegmentRange(start=start, end=end))
        if not ranges:
            continue
        groups.append(SegmentGroup(index=idx, ranges=ranges, joined=len(ranges) > 1))

    if not groups:
        raise SegmentSpecError("No valid timestamp ranges found.")
    return groups


def _even_floor(value: int) -> int:
    return max(2, (int(value) // 2) * 2)


def _video_filters(
    source_width: int, source_height: int, frame_mode: str, target_fps: float | None
) -> tuple[list[str], int, int]:
    filters: list[str] = []
    if target_fps and target_fps > 0:
        filters.append(f"fps={target_fps:g}")
    out_w, out_h = source_width, source_height
    if frame_mode == "portrait_9_16":
        target_aspect = 9 / 16
        src_aspect = source_width / source_height if source_height else target_aspect
        if src_aspect > target_aspect:
            # wider than 9:16 -> crop width
            crop_h = _even_floor(source_height)
            crop_w = _even_floor(int(round(crop_h * target_aspect)))
            crop_w = min(crop_w, _even_floor(source_width))
        else:
            # taller/narrower -> crop height
            crop_w = _even_floor(source_width)
            crop_h = _even_floor(int(round(crop_w / target_aspect)))
            crop_h = min(crop_h, _even_floor(source_height))
        crop_w = max(2, crop_w)
        crop_h = max(2, crop_h)
        x = max(0, (source_width - crop_w) // 2)
        y = max(0, (source_height - crop_h) // 2)
        x -= x % 2
        y -= y % 2
        filters.append(f"crop={crop_w}:{crop_h}:{x}:{y}")
        out_w, out_h = crop_w, crop_h
    else:
        out_w = _even_floor(source_width)
        out_h = _even_floor(source_height)
        if out_w != source_width or out_h != source_height:
            filters.append(f"scale={out_w}:{out_h}")
    filters.extend(["setsar=1", "format=yuv420p"])
    return filters, out_w, out_h


def _run_ffmpeg(args: list[str], timeout: int, cancel_check: Callable[[], bool] | None) -> None:
    try:
        run_command(args, timeout=timeout, cancel_check=cancel_check)
    except CommandCancelled as exc:
        raise JobCancelled() from exc
    except CommandNotFoundError as exc:
        raise RuntimeError("FFmpeg is not installed or not on PATH.") from exc
    except CommandError as exc:
        detail = (exc.stderr or "").strip().splitlines()
        tail = detail[-1][:300] if detail else str(exc)
        raise RuntimeError(f"FFmpeg failed: {tail}") from exc


def _render_range(
    settings: Settings,
    source_path: Path,
    seg: SegmentRange,
    output_path: Path,
    *,
    has_audio: bool,
    source_width: int,
    source_height: int,
    frame_mode: str,
    target_fps: float | None,
    cancel_check: Callable[[], bool] | None,
) -> tuple[int, int]:
    filters, out_w, out_h = _video_filters(source_width, source_height, frame_mode, target_fps)
    vf = ",".join(filters)
    args = [
        settings.ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{seg.start:.3f}",
        "-i",
        str(source_path),
        "-t",
        f"{seg.duration:.3f}",
        "-map",
        "0:v:0",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-crf",
        str(settings.output_crf),
        "-preset",
        settings.output_preset,
        "-pix_fmt",
        "yuv420p",
        "-sn",
        "-dn",
        "-movflags",
        "+faststart",
    ]
    if has_audio:
        args.extend(["-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k"])
    else:
        args.append("-an")
    args.append(str(output_path))
    render_timeout = int(max(float(settings.render_timeout_seconds), seg.duration * 4.0 + 120.0))
    _run_ffmpeg(args, render_timeout, cancel_check)
    return out_w, out_h


def _concat_parts(
    settings: Settings,
    parts: Sequence[Path],
    output_path: Path,
    *,
    cancel_check: Callable[[], bool] | None,
) -> None:
    list_path = output_path.with_suffix(".concat.txt")
    try:
        def _esc(p: Path) -> str:
            return str(p.resolve()).replace("'", "'\\''")

        content = "\n".join(f"file '{_esc(p)}'" for p in parts)
        list_path.write_text(content, encoding="utf-8")
        args = [
            settings.ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        concat_timeout = int(max(300.0, float(settings.render_timeout_seconds)))
        _run_ffmpeg(args, concat_timeout, cancel_check)
    finally:
        list_path.unlink(missing_ok=True)


def _probe_output(settings: Settings, path: Path) -> tuple[int | None, int | None]:
    try:
        info = probe_media(path, settings)
        return info.width, info.height
    except MediaProbeError:
        return None, None


def _apply_progress(job, progress: int, message: str, state: str) -> None:
    bounded = max(0, min(100, int(progress)))
    job.progress = max(int(getattr(job, "progress", 0) or 0), bounded)
    job.stage_message = (message or "")[:255]
    job.state = state
    job.updated_at = utc_now()


def process_segmenter_job(
    session,
    job,
    settings: Settings,
    *,
    cancel_check: Callable[[], bool] | None = None,
) -> None:
    """Parse spec and render segment groups as Clip outputs."""
    from sqlalchemy import delete

    def _cancelled() -> bool:
        return bool(cancel_check and cancel_check())

    if _cancelled():
        raise JobCancelled()

    source_path = settings.data_dir / job.stored_path
    # resolve safely via relative path stored under data dir
    try:
        source_path = (settings.data_dir / str(job.stored_path)).resolve()
        source_path.relative_to(settings.data_dir.resolve())
    except Exception:
        source_path = Path(str(job.stored_path))

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

    spec = job.segment_spec or ""
    try:
        groups = parse_segment_spec(spec, info.duration_seconds)
    except SegmentSpecError as exc:
        raise ValueError(str(exc)) from exc

    frame_mode = (job.segment_output_frame or "original").strip().lower()
    if frame_mode not in {"original", "portrait_9_16"}:
        frame_mode = "original"

    # Clear previous clips
    session.execute(delete(Clip).where(Clip.job_id == job.id))
    job.clip_count = 0
    job.segment_options = {
        **(job.segment_options or {}),
        "output_frame": frame_mode,
        "group_count": len(groups),
    }
    _apply_progress(job, 20, f"Preparing {len(groups)} segment group(s)", "segmenting")
    session.commit()

    work_dir = job_work_dir(settings, job.id)
    clips_dir = job_clips_dir(settings, job.id)
    seg_work = work_dir / "segment_parts"
    if seg_work.exists():
        shutil.rmtree(seg_work, ignore_errors=True)
    seg_work.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    total = len(groups)
    rendered = 0
    target_fps = info.frame_rate if info.frame_rate and info.frame_rate > 0 else None

    for i, group in enumerate(groups, start=1):
        if _cancelled():
            raise JobCancelled()
        progress = 20 + int(round(75 * (i - 1) / max(1, total)))
        label = f"Segment {i}/{total}"
        if group.joined:
            label += f" (joining {len(group.ranges)} parts)"
        _apply_progress(job, progress, label, "segmenting")
        session.commit()

        clip_id = str(uuid.uuid4())
        final_path = clips_dir / f"{clip_id}.mp4"
        now = utc_now()
        title = f"Segment {group.index}" + (" (joined)" if group.joined else "")
        hook = None
        reason = None
        if group.joined:
            parts_desc = ", ".join(
                f"{_format_ts(r.start)}-{_format_ts(r.end)}" for r in group.ranges
            )
            reason = f"Joined: {parts_desc}"
        else:
            r = group.ranges[0]
            reason = f"{_format_ts(r.start)} - {_format_ts(r.end)}"

        clip = Clip(
            id=clip_id,
            job_id=job.id,
            start_seconds=group.start,
            end_seconds=group.end,
            duration_seconds=round(group.duration, 3),
            title=title[:255],
            hook=hook,
            reason=reason,
            score=None,
            component_scores={
                "segmenter": True,
                "joined": group.joined,
                "parts": [
                    {"start": r.start, "end": r.end, "duration": round(r.duration, 3)}
                    for r in group.ranges
                ],
                "output_frame": frame_mode,
            },
            output_filename=None,
            width=None,
            height=None,
            speaker_tracking_status="n/a",
            speaker_tracking_confidence=None,
            crop_plan={},
            tracking_details={"source": "segmenter", "output_frame": frame_mode},
            render_status="rendering",
            error=None,
            created_at=now,
            updated_at=now,
        )
        session.add(clip)
        session.flush()

        try:
            if len(group.ranges) == 1:
                out_w, out_h = _render_range(
                    settings,
                    source_path,
                    group.ranges[0],
                    final_path,
                    has_audio=info.has_audio,
                    source_width=info.width,
                    source_height=info.height,
                    frame_mode=frame_mode,
                    target_fps=target_fps,
                    cancel_check=cancel_check,
                )
            else:
                part_paths: list[Path] = []
                for pi, seg in enumerate(group.ranges, start=1):
                    if _cancelled():
                        raise JobCancelled()
                    part_path = seg_work / f"{clip_id}_part{pi}.mp4"
                    out_w, out_h = _render_range(
                        settings,
                        source_path,
                        seg,
                        part_path,
                        has_audio=info.has_audio,
                        source_width=info.width,
                        source_height=info.height,
                        frame_mode=frame_mode,
                        target_fps=target_fps,
                        cancel_check=cancel_check,
                    )
                    part_paths.append(part_path)
                _concat_parts(settings, part_paths, final_path, cancel_check=cancel_check)
                for p in part_paths:
                    p.unlink(missing_ok=True)

            if not final_path.is_file() or final_path.stat().st_size == 0:
                raise RuntimeError("Rendered output is missing or empty.")
            pw, ph = _probe_output(settings, final_path)
            if pw and ph:
                out_w, out_h = pw, ph
            clip.output_filename = relative_to_data_dir(settings, final_path)
            clip.width = out_w
            clip.height = out_h
            clip.render_status = "completed"
            clip.error = None
            rendered += 1
        except JobCancelled:
            final_path.unlink(missing_ok=True)
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Segment render failed for job %s group %s", job.id, group.index)
            final_path.unlink(missing_ok=True)
            clip.render_status = "failed"
            clip.error = str(exc)[:1000]
            clip.output_filename = None

        clip.updated_at = utc_now()
        session.commit()

    if seg_work.exists():
        shutil.rmtree(seg_work, ignore_errors=True)

    job.clip_count = total
    if rendered == 0:
        msg = "Segmenting finished, but all outputs failed to render."
    else:
        msg = f"Segmenting complete: {rendered}/{total} clip(s) ready."
    _apply_progress(job, 100, msg, "completed")
    job.completed_at = utc_now()
    session.commit()
