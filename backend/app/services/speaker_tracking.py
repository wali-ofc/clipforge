"""Speaker tracking and crop planning.

The tracker is intentionally split into pure, testable pieces:

1. Build face tracks by associating detections across sampled frames.
2. Estimate the likely active speaker from face size, centrality, speech
   timing, lightweight mouth motion, and temporal continuity.
3. Choose a stable fallback face when active-speaker confidence is low.
4. Produce a time-indexed crop-centre plan in source pixels, smoothed with an
   EMA, a dead zone, and a speed limit.

No lip-sync or diarization model is used. Speech timing comes from the
transcript (audio-derived), while mouth motion is a small visual cue. This is
why confidence and fallback status are persisted with every clip: the UI can
say when tracking is uncertain instead of pretending a static centre crop is
speaker tracking.
"""

from __future__ import annotations

import bisect
import logging
import math
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

import numpy as np

from app.config import Settings
from app.schemas.transcript import Transcript, TranscriptSegment
from app.services.face_detection import (
    FaceBox,
    FaceDetectionError,
    FaceDetector,
    create_face_detector,
)
from app.services.frame_sampling import SampledFrame, sample_clip_frames

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float], None]

CROP_PLAN_VERSION = 1

FALLBACK_BEHAVIOR = (
    "Low active-speaker confidence keeps a stable largest/central face instead "
    "of switching rapidly. Missing detections hold the last stable crop for a "
    "short period, then fall back to a centred crop."
)

LIMITATIONS = (
    "No lip-sync or speaker-diarization model is used. Active-speaker "
    "confidence blends face size, centrality, mouth motion, transcript speech "
    "timing, and temporal continuity."
)


class SpeakerTrackingError(Exception):
    """A speaker-tracking failure with a user-facing message."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class FrameFace:
    """One face detection plus an optional mouth-region patch."""

    box: FaceBox
    mouth_patch: np.ndarray | None = field(
        default=None, repr=False, compare=False
    )


@dataclass(frozen=True)
class FrameFaces:
    """All faces detected in one sampled frame."""

    time: float
    faces: tuple[FrameFace, ...]


@dataclass
class TrackObservation:
    time: float
    box: FaceBox
    mouth_motion: float | None = None
    mouth_patch: np.ndarray | None = field(
        default=None, repr=False, compare=False
    )


@dataclass
class FaceTrack:
    track_id: int
    observations: list[TrackObservation] = field(default_factory=list)

    @property
    def first_time(self) -> float:
        return self.observations[0].time

    @property
    def last_time(self) -> float:
        return self.observations[-1].time

    @property
    def duration(self) -> float:
        return max(0.0, self.last_time - self.first_time)

    @property
    def last_observation(self) -> TrackObservation:
        return self.observations[-1]


@dataclass(frozen=True)
class TrackStats:
    track_id: int
    size_ratio: float
    centrality: float
    speech_motion: float
    coverage: float


@dataclass(frozen=True)
class TrackChoice:
    """The selected crop target at one sampled timestamp."""

    time: float
    track_id: int | None
    box: FaceBox | None
    confidence: float
    status: str
    face_count: int


@dataclass(frozen=True)
class CropGeometry:
    width: float
    height: float


@dataclass(frozen=True)
class CropSample:
    time: float
    center_x: float
    center_y: float
    crop_width: float
    crop_height: float
    confidence: float
    status: str
    face_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": round(self.time, 3),
            "x": round(self.center_x, 2),
            "y": round(self.center_y, 2),
            "crop_width": round(self.crop_width, 2),
            "crop_height": round(self.crop_height, 2),
            "confidence": round(self.confidence, 3),
            "status": self.status,
            "face_count": self.face_count,
        }


@dataclass(frozen=True)
class CropPlan:
    source_width: int
    source_height: int
    crop_width: float
    crop_height: float
    target_aspect: float
    samples: tuple[CropSample, ...]
    method: str = "ema+dead-zone+speed-limit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": CROP_PLAN_VERSION,
            "coordinate_space": "source_pixels",
            "time_space": "clip_relative_seconds",
            "method": self.method,
            "target_aspect": round(self.target_aspect, 6),
            "source": {
                "width": int(self.source_width),
                "height": int(self.source_height),
            },
            "crop": {
                "width": round(self.crop_width, 2),
                "height": round(self.crop_height, 2),
            },
            "samples": [sample.to_dict() for sample in self.samples],
        }


@dataclass(frozen=True)
class SpeakerTrackingResult:
    status: str
    confidence: float
    crop_plan: dict[str, Any]
    details: dict[str, Any]


class SpeakerTracker(Protocol):
    """Plans speaker-aware crops for one candidate clip."""

    name: str

    def track(
        self,
        source_path: Path,
        start_seconds: float,
        end_seconds: float,
        frame_width: int,
        frame_height: int,
        transcript: Transcript | None,
        work_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> SpeakerTrackingResult:
        """Return tracking status, confidence, and a crop plan."""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _centrality(box: FaceBox, frame_width: float, frame_height: float) -> float:
    if frame_width <= 0 or frame_height <= 0:
        return 0.0
    distance = math.hypot(
        box.center_x - frame_width / 2.0,
        box.center_y - frame_height / 2.0,
    )
    half_diagonal = math.hypot(frame_width / 2.0, frame_height / 2.0)
    if half_diagonal <= 0:
        return 0.0
    return _clamp(1.0 - distance / half_diagonal, 0.0, 1.0)


def _association_score(
    previous: FaceBox,
    current: FaceBox,
    iou_threshold: float,
) -> float | None:
    """Return a match score, or None when the boxes are too far apart."""
    iou = previous.iou(current)
    if iou >= iou_threshold:
        return 1.0 + iou

    distance = math.hypot(
        previous.center_x - current.center_x,
        previous.center_y - current.center_y,
    )
    scale = max(
        previous.width,
        previous.height,
        current.width,
        current.height,
        1.0,
    )
    if distance <= 0.75 * scale:
        return 0.5 + (1.0 - distance / (0.75 * scale)) * 0.4
    return None


def build_face_tracks(
    frames: Sequence[FrameFaces],
    *,
    iou_threshold: float = 0.2,
    max_gap_seconds: float = 1.0,
    min_observations: int = 2,
) -> list[FaceTrack]:
    """Associate detections across adjacent sampled frames.

    Matching prefers IoU and falls back to centre distance so short gaps and
    small movements do not split one face into many tracks. Greedy matching is
    sufficient at 2 fps and keeps the tracker dependency-free.
    """
    ordered = sorted(frames, key=lambda frame: frame.time)
    all_tracks: list[FaceTrack] = []
    active: list[FaceTrack] = []
    next_id = 1

    for frame in ordered:
        active = [
            track
            for track in active
            if frame.time - track.last_time <= max_gap_seconds
        ]

        pairs: list[tuple[float, int, int]] = []
        for track_index, track in enumerate(active):
            previous = track.last_observation.box
            for face_index, face in enumerate(frame.faces):
                score = _association_score(
                    previous, face.box, iou_threshold
                )
                if score is not None:
                    pairs.append((score, track_index, face_index))

        pairs.sort(reverse=True)
        used_tracks: set[int] = set()
        used_faces: set[int] = set()

        for _score, track_index, face_index in pairs:
            if track_index in used_tracks or face_index in used_faces:
                continue
            track = active[track_index]
            face = frame.faces[face_index]
            track.observations.append(
                TrackObservation(
                    time=frame.time,
                    box=face.box,
                    mouth_patch=face.mouth_patch,
                )
            )
            used_tracks.add(track_index)
            used_faces.add(face_index)

        for face_index, face in enumerate(frame.faces):
            if face_index in used_faces:
                continue
            track = FaceTrack(track_id=next_id)
            track.observations.append(
                TrackObservation(
                    time=frame.time,
                    box=face.box,
                    mouth_patch=face.mouth_patch,
                )
            )
            next_id += 1
            all_tracks.append(track)
            active.append(track)

    filtered = [
        track
        for track in all_tracks
        if len(track.observations) >= min_observations
    ]
    if not filtered and all_tracks:
        # A very short clip may only contain one sample. Keep the longest
        # track rather than discarding all evidence.
        filtered = [max(all_tracks, key=lambda track: len(track.observations))]

    return sorted(filtered, key=lambda track: (track.first_time, track.track_id))


def assign_mouth_motion(
    tracks: Sequence[FaceTrack],
    *,
    max_gap_seconds: float = 1.0,
) -> None:
    """Estimate mouth-region motion from consecutive samples of one track.

    The value is the mean absolute difference between resized lower-face
    patches, normalized to 0-1. It is a cheap visual activity cue, not a
    lip-sync classifier.
    """
    for track in tracks:
        previous: TrackObservation | None = None
        for observation in track.observations:
            if (
                previous is not None
                and previous.mouth_patch is not None
                and observation.mouth_patch is not None
                and observation.time - previous.time <= max_gap_seconds
            ):
                first = previous.mouth_patch
                second = observation.mouth_patch
                if first.shape == second.shape:
                    difference = float(
                        np.mean(np.abs(first.astype(np.float32) - second))
                    )
                    observation.mouth_motion = _clamp(difference / 255.0, 0.0, 1.0)
            previous = observation


def build_speech_intervals(
    segments: Sequence[TranscriptSegment],
    start_seconds: float,
    end_seconds: float,
) -> list[tuple[float, float]]:
    """Clip and merge transcript speech intervals to the candidate range."""
    intervals: list[tuple[float, float]] = []
    for segment in segments:
        start = max(float(start_seconds), float(segment.start))
        end = min(float(end_seconds), float(segment.end))
        if end > start:
            intervals.append((start, end))

    intervals.sort()
    merged: list[tuple[float, float]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + 0.01:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def is_speech_active(
    intervals: Sequence[tuple[float, float]],
    time_seconds: float,
) -> bool:
    for start, end in intervals:
        if start <= time_seconds <= end:
            return True
        if time_seconds < start:
            return False
    return False


def _track_stats(
    tracks: Sequence[FaceTrack],
    frame_count: int,
    frame_width: int,
    frame_height: int,
    speech_intervals: Sequence[tuple[float, float]],
) -> dict[int, TrackStats]:
    frame_area = max(1.0, float(frame_width) * float(frame_height))
    stats: dict[int, TrackStats] = {}
    for track in tracks:
        sizes = [observation.box.area / frame_area for observation in track.observations]
        centralities = [
            _centrality(observation.box, frame_width, frame_height)
            for observation in track.observations
        ]
        speech_motions = [
            observation.mouth_motion
            for observation in track.observations
            if observation.mouth_motion is not None
            and is_speech_active(speech_intervals, observation.time)
        ]
        stats[track.track_id] = TrackStats(
            track_id=track.track_id,
            size_ratio=_median(sizes),
            centrality=_median(centralities),
            speech_motion=(
                sum(speech_motions) / len(speech_motions)
                if speech_motions
                else 0.0
            ),
            coverage=(
                len(track.observations) / frame_count if frame_count > 0 else 0.0
            ),
        )
    return stats


def choose_active_tracks(
    frames: Sequence[FrameFaces],
    tracks: Sequence[FaceTrack],
    speech_intervals: Sequence[tuple[float, float]],
    frame_width: int,
    frame_height: int,
    settings: Settings,
) -> list[TrackChoice]:
    """Choose one crop target per sampled frame.

    A single visible face is used directly. With multiple faces the tracker
    scores size, centrality, continuity, speech activity, and mouth motion. A
    low margin between the top two faces triggers the stable fallback instead
    of a rapid switch.
    """
    stats = _track_stats(
        tracks, len(frames), frame_width, frame_height, speech_intervals
    )
    max_size = max((item.size_ratio for item in stats.values()), default=0.0)
    max_size = max(max_size, 1e-9)

    by_time: dict[float, dict[int, TrackObservation]] = {}
    for track in tracks:
        for observation in track.observations:
            by_time.setdefault(round(observation.time, 6), {})[
                track.track_id
            ] = observation

    previous_track_id: int | None = None
    fallback_track_id: int | None = None
    choices: list[TrackChoice] = []

    for frame in sorted(frames, key=lambda item: item.time):
        observations = by_time.get(round(frame.time, 6), {})
        candidates = [
            (track, observations[track.track_id])
            for track in tracks
            if track.track_id in observations
        ]
        face_count = len(frame.faces)

        if not candidates:
            choices.append(
                TrackChoice(
                    time=frame.time,
                    track_id=None,
                    box=None,
                    confidence=0.0,
                    status="none",
                    face_count=face_count,
                )
            )
            continue

        if len(candidates) == 1:
            track, observation = candidates[0]
            confidence = _clamp(0.7 + 0.3 * observation.box.confidence, 0.0, 1.0)
            previous_track_id = track.track_id
            fallback_track_id = track.track_id
            choices.append(
                TrackChoice(
                    time=frame.time,
                    track_id=track.track_id,
                    box=observation.box,
                    confidence=confidence,
                    status="single_face",
                    face_count=face_count,
                )
            )
            continue

        speech_active = is_speech_active(speech_intervals, frame.time)
        max_motion = max(
            (observation.mouth_motion or 0.0 for _, observation in candidates),
            default=0.0,
        )

        scored: list[tuple[float, float, FaceTrack, TrackObservation]] = []
        for track, observation in candidates:
            track_stats = stats[track.track_id]
            size_score = _clamp(track_stats.size_ratio / max_size, 0.0, 1.0)
            central_score = track_stats.centrality
            continuity = 1.0 if track.track_id == previous_track_id else 0.0
            motion_score = 0.0
            if speech_active and max_motion > 1e-6:
                motion_score = _clamp(
                    (observation.mouth_motion or 0.0) / max_motion, 0.0, 1.0
                )
            speech_score = 1.0 if speech_active else 0.0
            score = (
                0.34 * size_score
                + 0.18 * central_score
                + 0.18 * continuity
                + 0.10 * speech_score
                + 0.15 * motion_score
                + 0.05 * observation.box.confidence
            )
            fallback_score = 0.6 * size_score + 0.4 * central_score
            scored.append((score, fallback_score, track, observation))

        scored.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                item[2].track_id,
            )
        )
        top_score, _top_fallback, top_track, top_observation = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        margin = max(0.0, top_score - second_score)
        confidence = _clamp(
            0.5
            + 1.8 * margin
            + 0.08 * (top_observation.box.confidence - 0.5),
            0.0,
            1.0,
        )

        # Stable largest/central fallback with hysteresis. A different face
        # must beat the current fallback by a margin before it takes over.
        best_fallback = max(
            scored,
            key=lambda item: (item[1], -item[2].track_id),
        )
        current_fallback = next(
            (
                item
                for item in scored
                if item[2].track_id == fallback_track_id
            ),
            None,
        )
        if current_fallback is None or (
            best_fallback[2].track_id != fallback_track_id
            and best_fallback[1] - current_fallback[1]
            >= settings.speaker_switch_margin
        ):
            fallback_track_id = best_fallback[2].track_id

        if confidence >= settings.speaker_confidence_threshold:
            chosen_track = top_track
            chosen_observation = top_observation
            status = "tracked"
        else:
            chosen = next(
                item
                for item in scored
                if item[2].track_id == fallback_track_id
            )
            chosen_track = chosen[2]
            chosen_observation = chosen[3]
            status = "fallback"

        previous_track_id = chosen_track.track_id
        choices.append(
            TrackChoice(
                time=frame.time,
                track_id=chosen_track.track_id,
                box=chosen_observation.box,
                confidence=confidence,
                status=status,
                face_count=face_count,
            )
        )

    return choices


def compute_crop_geometry(
    source_width: int,
    source_height: int,
    target_aspect: float,
) -> CropGeometry:
    """Return the largest target-aspect crop that fits the source.

    Wide sources use full height, so a 9:16 crop is
    ``source_height * 9 / 16`` wide. Sources already narrower than the target
    use full width and crop only the height. This avoids unnecessary cropping
    of portrait footage.
    """
    width = max(0.0, float(source_width))
    height = max(0.0, float(source_height))
    if width <= 0 or height <= 0 or target_aspect <= 0:
        return CropGeometry(width=0.0, height=0.0)

    source_aspect = width / height
    if source_aspect >= target_aspect:
        crop_height = height
        crop_width = height * target_aspect
    else:
        crop_width = width
        crop_height = width / target_aspect

    crop_width = min(crop_width, width)
    crop_height = min(crop_height, height)
    return CropGeometry(width=crop_width, height=crop_height)


def _clamp_center(
    center_x: float,
    center_y: float,
    source_width: float,
    source_height: float,
    crop_width: float,
    crop_height: float,
) -> tuple[float, float]:
    if crop_width >= source_width:
        x = source_width / 2.0
    else:
        x = _clamp(center_x, crop_width / 2.0, source_width - crop_width / 2.0)
    if crop_height >= source_height:
        y = source_height / 2.0
    else:
        y = _clamp(center_y, crop_height / 2.0, source_height - crop_height / 2.0)
    return x, y


def build_crop_plan(
    choices: Sequence[TrackChoice],
    source_width: int,
    source_height: int,
    target_aspect: float,
    clip_start_seconds: float,
    clip_duration_seconds: float,
    settings: Settings,
) -> CropPlan:
    """Create a smoothed, time-indexed crop-centre plan in source pixels."""
    geometry = compute_crop_geometry(source_width, source_height, target_aspect)
    crop_width = geometry.width
    crop_height = geometry.height
    duration = max(0.0, float(clip_duration_seconds))
    center_x = float(source_width) / 2.0
    center_y = float(source_height) / 2.0

    ordered = sorted(choices, key=lambda choice: choice.time)
    if not ordered:
        sample = CropSample(
            time=0.0,
            center_x=center_x,
            center_y=center_y,
            crop_width=crop_width,
            crop_height=crop_height,
            confidence=0.0,
            status="centered",
            face_count=0,
        )
        end_sample = CropSample(
            time=duration,
            center_x=center_x,
            center_y=center_y,
            crop_width=crop_width,
            crop_height=crop_height,
            confidence=0.0,
            status="centered",
            face_count=0,
        )
        return CropPlan(
            source_width=int(source_width),
            source_height=int(source_height),
            crop_width=crop_width,
            crop_height=crop_height,
            target_aspect=target_aspect,
            samples=(sample, end_sample),
        )

    dead_zone = max(0.0, crop_width * settings.crop_dead_zone_ratio)
    max_speed = max(0.0, crop_width * settings.crop_max_speed_ratio)
    alpha = settings.crop_ema_alpha
    hold_seconds = settings.crop_hold_seconds

    previous_x = center_x
    previous_y = center_y
    previous_time: float | None = None
    last_face_x: float | None = None
    last_face_y: float | None = None
    last_face_time: float | None = None
    samples: list[CropSample] = []

    for choice in ordered:
        if choice.box is not None:
            raw_x, raw_y = _clamp_center(
                choice.box.center_x,
                choice.box.center_y,
                float(source_width),
                float(source_height),
                crop_width,
                crop_height,
            )
            last_face_x, last_face_y = raw_x, raw_y
            last_face_time = choice.time
            status = choice.status
        elif (
            last_face_x is not None
            and last_face_y is not None
            and last_face_time is not None
            and choice.time - last_face_time <= hold_seconds
        ):
            # Freeze the smoothed position rather than the raw face centre,
            # so a short detection gap cannot cause a small drift.
            raw_x, raw_y = previous_x, previous_y
            status = "held"
        else:
            raw_x, raw_y = center_x, center_y
            status = "centered"

        dt = (
            choice.time - previous_time
            if previous_time is not None
            else 1.0 / settings.face_sample_fps
        )
        dt = max(1e-3, dt)

        delta_x = raw_x - previous_x
        delta_y = raw_y - previous_y
        if math.hypot(delta_x, delta_y) <= dead_zone:
            smoothed_x, smoothed_y = previous_x, previous_y
        else:
            target_x = alpha * raw_x + (1.0 - alpha) * previous_x
            target_y = alpha * raw_y + (1.0 - alpha) * previous_y
            step_x = target_x - previous_x
            step_y = target_y - previous_y
            max_step = max_speed * dt
            step_length = math.hypot(step_x, step_y)
            if step_length > max_step and step_length > 0:
                scale = max_step / step_length
                step_x *= scale
                step_y *= scale
            smoothed_x = previous_x + step_x
            smoothed_y = previous_y + step_y

        smoothed_x, smoothed_y = _clamp_center(
            smoothed_x,
            smoothed_y,
            float(source_width),
            float(source_height),
            crop_width,
            crop_height,
        )
        relative_time = _clamp(choice.time - clip_start_seconds, 0.0, duration)
        samples.append(
            CropSample(
                time=relative_time,
                center_x=smoothed_x,
                center_y=smoothed_y,
                crop_width=crop_width,
                crop_height=crop_height,
                confidence=choice.confidence,
                status=status,
                face_count=choice.face_count,
            )
        )
        previous_x, previous_y = smoothed_x, smoothed_y
        previous_time = choice.time

    return CropPlan(
        source_width=int(source_width),
        source_height=int(source_height),
        crop_width=crop_width,
        crop_height=crop_height,
        target_aspect=target_aspect,
        samples=tuple(samples),
    )


def summarize_choices(
    choices: Sequence[TrackChoice],
) -> tuple[str, float]:
    """Return the clip-level tracking status and mean confidence."""
    if not choices:
        return "no_frames", 0.0

    face_choices = [choice for choice in choices if choice.box is not None]
    if not face_choices:
        return "no_faces", 0.0

    tracked = sum(
        1
        for choice in choices
        if choice.status in {"tracked", "single_face"}
    )
    fallback = sum(1 for choice in choices if choice.status == "fallback")
    confidence = sum(choice.confidence for choice in face_choices) / len(
        face_choices
    )

    if tracked > 0:
        return "tracked", round(_clamp(confidence, 0.0, 1.0), 3)
    if fallback > 0:
        return "fallback", round(_clamp(confidence, 0.0, 1.0), 3)
    return "no_faces", 0.0


def _target_aspect(settings: Settings) -> float:
    if settings.output_height <= 0:
        return 9.0 / 16.0
    return settings.output_width / settings.output_height


def _centered_plan(
    source_width: int,
    source_height: int,
    clip_duration_seconds: float,
    settings: Settings,
) -> CropPlan:
    return build_crop_plan(
        [],
        source_width,
        source_height,
        _target_aspect(settings),
        0.0,
        clip_duration_seconds,
        settings,
    )


def build_centered_result(
    start_seconds: float,
    end_seconds: float,
    frame_width: int,
    frame_height: int,
    settings: Settings,
    *,
    status: str,
    detail: str | None = None,
    error_code: str | None = None,
) -> SpeakerTrackingResult:
    """Explicit, stable fallback used when tracking cannot run."""
    duration = max(0.0, float(end_seconds) - float(start_seconds))
    plan = _centered_plan(frame_width, frame_height, duration, settings)
    details: dict[str, Any] = {
        "method": "centered-fallback",
        "detector": "opencv-yunet",
        "sample_fps": settings.face_sample_fps,
        "status_reason": detail or "Speaker tracking did not produce face data.",
        "fallback_behavior": FALLBACK_BEHAVIOR,
        "limitations": LIMITATIONS,
        "crop_plan_method": plan.method,
    }
    if error_code:
        details["error_code"] = error_code
    return SpeakerTrackingResult(
        status=status,
        confidence=0.0,
        crop_plan=plan.to_dict(),
        details=details,
    )


def interpolate_crop(
    plan: CropPlan | dict[str, Any],
    time_seconds: float,
) -> tuple[float, float, float, float]:
    """Linearly interpolate a crop plan at a clip-relative timestamp.

    Phase 5 uses this to move between sampled positions on every rendered
    frame instead of stepping at the sampling rate.
    """
    if isinstance(plan, CropPlan):
        samples = list(plan.samples)
    else:
        raw_samples = plan.get("samples") or []
        samples = [
            CropSample(
                time=float(item.get("time", 0.0)),
                center_x=float(item.get("x", 0.0)),
                center_y=float(item.get("y", 0.0)),
                crop_width=float(item.get("crop_width", 0.0)),
                crop_height=float(item.get("crop_height", 0.0)),
                confidence=float(item.get("confidence", 0.0)),
                status=str(item.get("status", "centered")),
                face_count=int(item.get("face_count", 0)),
            )
            for item in raw_samples
            if isinstance(item, dict)
        ]

    if not samples:
        raise SpeakerTrackingError(
            "crop_plan_empty",
            "The crop plan contains no samples.",
        )

    times = [sample.time for sample in samples]
    if time_seconds <= times[0]:
        sample = samples[0]
    elif time_seconds >= times[-1]:
        sample = samples[-1]
    else:
        index = bisect.bisect_right(times, time_seconds)
        left = samples[index - 1]
        right = samples[index]
        span = right.time - left.time
        fraction = 0.0 if span <= 0 else (time_seconds - left.time) / span
        return (
            left.center_x + (right.center_x - left.center_x) * fraction,
            left.center_y + (right.center_y - left.center_y) * fraction,
            left.crop_width + (right.crop_width - left.crop_width) * fraction,
            left.crop_height + (right.crop_height - left.crop_height) * fraction,
        )

    return (
        sample.center_x,
        sample.center_y,
        sample.crop_width,
        sample.crop_height,
    )


def _extract_mouth_patch(
    grayscale: np.ndarray,
    box: FaceBox,
) -> np.ndarray | None:
    """Crop the lower-face region into a tiny grayscale patch."""
    if grayscale.ndim < 2:
        return None
    height, width = grayscale.shape[:2]
    left = int(max(0, box.x + box.width * 0.15))
    right = int(min(width, box.x + box.width * 0.85))
    top = int(max(0, box.y + box.height * 0.55))
    bottom = int(min(height, box.y + box.height))
    if right <= left or bottom <= top:
        return None

    patch = grayscale[top:bottom, left:right]
    if patch.size == 0:
        return None

    try:
        import cv2  # type: ignore[import-not-found]

        resized = cv2.resize(patch, (24, 16), interpolation=cv2.INTER_AREA)
    except Exception:  # noqa: BLE001 - motion is optional
        return None
    return resized.astype(np.float32)


def _report(callback: ProgressCallback | None, fraction: float) -> None:
    if callback is None:
        return
    callback(_clamp(float(fraction), 0.0, 1.0))


class OpenCVSpeakerTracker:
    """Face detection plus heuristic active-speaker crop planning."""

    name = "opencv-yunet"

    def __init__(
        self,
        settings: Settings,
        *,
        detector_factory: Callable[[Settings], FaceDetector] | None = None,
        frame_loader: Callable[[Path], np.ndarray | None] | None = None,
    ) -> None:
        self.settings = settings
        self._detector_factory = detector_factory or create_face_detector
        self._frame_loader = frame_loader or _load_frame

    def track(
        self,
        source_path: Path,
        start_seconds: float,
        end_seconds: float,
        frame_width: int,
        frame_height: int,
        transcript: Transcript | None,
        work_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> SpeakerTrackingResult:
        if end_seconds <= start_seconds:
            return build_centered_result(
                start_seconds,
                end_seconds,
                frame_width,
                frame_height,
                self.settings,
                status="unavailable",
                detail="The candidate range is empty, so no frames were sampled.",
                error_code="empty_range",
            )
        if frame_width <= 0 or frame_height <= 0:
            return build_centered_result(
                start_seconds,
                end_seconds,
                frame_width,
                frame_height,
                self.settings,
                status="unavailable",
                detail="The source dimensions are unknown.",
                error_code="invalid_dimensions",
            )

        detector: FaceDetector | None = None
        frames_dir = work_dir / "frames"
        try:
            detector = self._detector_factory(self.settings)
            _report(on_progress, 0.02)

            sampled = sample_clip_frames(
                source_path,
                start_seconds,
                end_seconds,
                frames_dir,
                self.settings,
            )
            _report(on_progress, 0.08)

            if not sampled:
                return build_centered_result(
                    start_seconds,
                    end_seconds,
                    frame_width,
                    frame_height,
                    self.settings,
                    status="no_frames",
                    detail="FFmpeg produced no frames for this candidate range.",
                    error_code="no_frames",
                )

            frame_faces: list[FrameFaces] = []
            for index, sampled_frame in enumerate(sampled):
                image = self._frame_loader(sampled_frame.path)
                if image is None:
                    continue
                grayscale = _to_grayscale(image)
                if grayscale is None:
                    continue
                detections = detector.detect(image)
                faces = tuple(
                    FrameFace(
                        box=box,
                        mouth_patch=_extract_mouth_patch(grayscale, box),
                    )
                    for box in detections
                )
                frame_faces.append(
                    FrameFaces(time=sampled_frame.time_seconds, faces=faces)
                )
                _report(
                    on_progress,
                    0.08 + 0.72 * (index + 1) / len(sampled),
                )

            if not frame_faces:
                return build_centered_result(
                    start_seconds,
                    end_seconds,
                    frame_width,
                    frame_height,
                    self.settings,
                    status="no_frames",
                    detail="Sampled frames could not be decoded.",
                    error_code="decode_failed",
                )

            tracks = build_face_tracks(
                frame_faces,
                iou_threshold=self.settings.face_track_iou_threshold,
                max_gap_seconds=self.settings.face_track_max_gap_seconds,
                min_observations=self.settings.face_track_min_observations,
            )
            assign_mouth_motion(
                tracks,
                max_gap_seconds=self.settings.face_track_max_gap_seconds,
            )
            _report(on_progress, 0.86)

            speech_intervals = build_speech_intervals(
                transcript.segments if transcript is not None else [],
                start_seconds,
                end_seconds,
            )
            choices = choose_active_tracks(
                frame_faces,
                tracks,
                speech_intervals,
                frame_width,
                frame_height,
                self.settings,
            )
            _report(on_progress, 0.93)

            plan = build_crop_plan(
                choices,
                frame_width,
                frame_height,
                _target_aspect(self.settings),
                start_seconds,
                end_seconds - start_seconds,
                self.settings,
            )
            status, confidence = summarize_choices(choices)
            face_frames = sum(1 for frame in frame_faces if frame.faces)
            details = {
                "method": "heuristic-active-speaker",
                "detector": detector.name,
                "sample_fps": self.settings.face_sample_fps,
                "sampled_frames": len(frame_faces),
                "face_frames": face_frames,
                "face_detection_ratio": round(
                    face_frames / len(frame_faces), 3
                ),
                "face_tracks": len(tracks),
                "speech_intervals": len(speech_intervals),
                "crop_plan_method": plan.method,
                "fallback_behavior": FALLBACK_BEHAVIOR,
                "limitations": LIMITATIONS,
            }
            if status in {"fallback", "no_faces"}:
                details["status_reason"] = (
                    "Active-speaker confidence was low or faces were missing, "
                    "so the planner used a stable fallback crop."
                )
            _report(on_progress, 1.0)
            return SpeakerTrackingResult(
                status=status,
                confidence=confidence,
                crop_plan=plan.to_dict(),
                details=details,
            )
        except FaceDetectionError as exc:
            logger.warning(
                "Speaker tracking unavailable for %.2f-%.2f: %s",
                start_seconds,
                end_seconds,
                exc.message,
            )
            status = (
                "unavailable"
                if exc.code
                in {
                    "face_detection_unavailable",
                    "face_model_missing",
                    "face_model_unreadable",
                    "ffmpeg_missing",
                }
                else "failed"
            )
            return build_centered_result(
                start_seconds,
                end_seconds,
                frame_width,
                frame_height,
                self.settings,
                status=status,
                detail=exc.message,
                error_code=exc.code,
            )
        except Exception as exc:  # noqa: BLE001 - one clip must not fail the job
            logger.exception(
                "Unexpected speaker-tracking error for %.2f-%.2f",
                start_seconds,
                end_seconds,
            )
            return build_centered_result(
                start_seconds,
                end_seconds,
                frame_width,
                frame_height,
                self.settings,
                status="failed",
                detail=f"Speaker tracking failed: {type(exc).__name__}.",
                error_code="tracking_failed",
            )
        finally:
            if detector is not None:
                detector.close()
            shutil.rmtree(frames_dir, ignore_errors=True)


def _load_frame(path: Path) -> np.ndarray | None:
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise FaceDetectionError(
            "face_detection_unavailable",
            "Face detection is unavailable because OpenCV is not installed.",
        ) from exc

    image = cv2.imread(str(path))
    if image is None:
        logger.warning("Could not decode sampled frame %s", path)
    return image


def _to_grayscale(image: np.ndarray) -> np.ndarray | None:
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError:  # pragma: no cover - environment dependent
        return None

    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
