"""Face tracking, active-speaker, and crop-planning tests."""

from __future__ import annotations

import numpy as np
import pytest

from app.config import Settings
from app.services.face_detection import FaceBox, FaceDetectionError, OpenCVYuNetDetector
from app.services.frame_sampling import SampledFrame
from app.services.speaker_tracking import (
    FrameFace,
    FrameFaces,
    OpenCVSpeakerTracker,
    TrackChoice,
    assign_mouth_motion,
    build_centered_result,
    build_crop_plan,
    build_face_tracks,
    build_speech_intervals,
    choose_active_tracks,
    compute_crop_geometry,
    interpolate_crop,
    summarize_choices,
)
from app.schemas.transcript import TranscriptSegment


def _face(
    x: float,
    y: float = 100.0,
    width: float = 100.0,
    height: float = 100.0,
    *,
    patch: np.ndarray | None = None,
) -> FrameFace:
    return FrameFace(
        box=FaceBox(x=x, y=y, width=width, height=height, confidence=0.95),
        mouth_patch=patch,
    )


def _frame(time: float, *faces: FrameFace) -> FrameFaces:
    return FrameFaces(time=time, faces=tuple(faces))


def test_wide_source_uses_full_height_for_9x16_crop():
    geometry = compute_crop_geometry(1920, 1080, 9 / 16)
    assert geometry.height == pytest.approx(1080)
    assert geometry.width == pytest.approx(607.5)


def test_tall_portrait_source_uses_full_width_and_crops_height():
    geometry = compute_crop_geometry(1080, 2400, 9 / 16)
    assert geometry.width == pytest.approx(1080)
    assert geometry.height == pytest.approx(1920)


def test_exact_portrait_source_is_not_cropped():
    geometry = compute_crop_geometry(1080, 1920, 9 / 16)
    assert geometry.width == pytest.approx(1080)
    assert geometry.height == pytest.approx(1920)


def test_tracks_follow_a_moving_face_across_samples():
    frames = [
        _frame(0.0, _face(100)),
        _frame(0.5, _face(110)),
        _frame(1.0, _face(120)),
    ]

    tracks = build_face_tracks(
        frames,
        iou_threshold=0.2,
        max_gap_seconds=1.0,
        min_observations=2,
    )

    assert len(tracks) == 1
    assert len(tracks[0].observations) == 3


def test_separate_faces_become_separate_tracks():
    frames = [
        _frame(0.0, _face(100), _face(800)),
        _frame(0.5, _face(105), _face(805)),
    ]

    tracks = build_face_tracks(frames, min_observations=2)

    assert len(tracks) == 2
    assert all(len(track.observations) == 2 for track in tracks)


def test_speech_intervals_are_clipped_and_merged():
    segments = [
        TranscriptSegment(start=0.0, end=2.0, text="one"),
        TranscriptSegment(start=1.5, end=4.0, text="two"),
        TranscriptSegment(start=8.0, end=12.0, text="three"),
    ]

    intervals = build_speech_intervals(segments, 1.0, 10.0)

    assert intervals == [(1.0, 4.0), (8.0, 10.0)]


def test_single_face_is_used_while_speech_is_active(settings: Settings):
    frames = [_frame(0.0, _face(200)), _frame(0.5, _face(205))]
    tracks = build_face_tracks(frames, min_observations=1)
    intervals = [(0.0, 1.0)]

    choices = choose_active_tracks(frames, tracks, intervals, 1280, 720, settings)

    assert all(choice.status == "single_face" for choice in choices)
    assert all(choice.track_id == tracks[0].track_id for choice in choices)
    assert all(choice.confidence >= 0.9 for choice in choices)


def test_mouth_motion_selects_the_active_speaker(settings: Settings):
    still = np.zeros((16, 24), dtype=np.float32)
    moving_a = np.zeros((16, 24), dtype=np.float32)
    moving_b = np.full((16, 24), 255.0, dtype=np.float32)
    frames = [
        _frame(0.0, _face(100, patch=still), _face(1080, patch=still)),
        _frame(0.5, _face(105, patch=moving_a), _face(1085, patch=still)),
        _frame(1.0, _face(110, patch=moving_b), _face(1090, patch=still)),
    ]
    tracks = build_face_tracks(frames, min_observations=2)
    assign_mouth_motion(tracks)
    intervals = [(0.0, 2.0)]

    choices = choose_active_tracks(frames, tracks, intervals, 1280, 720, settings)

    speaker_track = tracks[0].track_id
    assert choices[-1].track_id == speaker_track
    assert choices[-1].status == "tracked"


def test_low_confidence_uses_a_stable_fallback(settings: Settings):
    still = np.zeros((16, 24), dtype=np.float32)
    frames = [
        _frame(0.0, _face(100, patch=still), _face(1080, patch=still)),
        _frame(0.5, _face(105, patch=still), _face(1085, patch=still)),
        _frame(1.0, _face(110, patch=still), _face(1090, patch=still)),
    ]
    tracks = build_face_tracks(frames, min_observations=2)
    assign_mouth_motion(tracks)
    intervals = [(0.0, 2.0)]

    choices = choose_active_tracks(frames, tracks, intervals, 1280, 720, settings)

    fallback_ids = {
        choice.track_id for choice in choices if choice.status == "fallback"
    }
    assert fallback_ids
    assert len(fallback_ids) == 1
    assert all(
        choice.track_id in fallback_ids
        for choice in choices
        if choice.status == "fallback"
    )


def test_missing_face_holds_then_centres(settings: Settings):
    adjusted = settings.model_copy(
        update={
            "crop_ema_alpha": 1.0,
            "crop_dead_zone_ratio": 0.0,
            "crop_max_speed_ratio": 100.0,
        }
    )
    choices = [
        TrackChoice(
            time=0.0,
            track_id=1,
            box=FaceBox(x=180, y=280, width=100, height=100, confidence=0.95),
            confidence=0.95,
            status="tracked",
            face_count=1,
        ),
        TrackChoice(
            time=0.5,
            track_id=None,
            box=None,
            confidence=0.0,
            status="none",
            face_count=0,
        ),
        TrackChoice(
            time=1.0,
            track_id=None,
            box=None,
            confidence=0.0,
            status="none",
            face_count=0,
        ),
        TrackChoice(
            time=3.0,
            track_id=None,
            box=None,
            confidence=0.0,
            status="none",
            face_count=0,
        ),
    ]

    plan = build_crop_plan(
        choices,
        1280,
        720,
        9 / 16,
        0.0,
        4.0,
        adjusted,
    )

    assert [sample.status for sample in plan.samples] == [
        "tracked",
        "held",
        "held",
        "centered",
    ]
    assert plan.samples[1].center_x == pytest.approx(plan.samples[0].center_x)
    assert plan.samples[3].center_x == pytest.approx(640.0)
    assert plan.samples[3].center_y == pytest.approx(360.0)


def test_dead_zone_ignores_tiny_movement(settings: Settings):
    adjusted = settings.model_copy(update={"crop_dead_zone_ratio": 0.05})
    choices = [
        TrackChoice(
            time=0.0,
            track_id=1,
            box=FaceBox(x=590, y=310, width=100, height=100, confidence=0.95),
            confidence=0.95,
            status="tracked",
            face_count=1,
        ),
        TrackChoice(
            time=0.5,
            track_id=1,
            box=FaceBox(x=595, y=310, width=100, height=100, confidence=0.95),
            confidence=0.95,
            status="tracked",
            face_count=1,
        ),
    ]

    plan = build_crop_plan(
        choices,
        1280,
        720,
        9 / 16,
        0.0,
        2.0,
        adjusted,
    )

    assert plan.samples[1].center_x == pytest.approx(plan.samples[0].center_x)
    assert plan.samples[1].center_y == pytest.approx(plan.samples[0].center_y)


def test_speed_limit_caps_crop_jumps(settings: Settings):
    choices = [
        TrackChoice(
            time=0.0,
            track_id=1,
            box=FaceBox(x=200, y=300, width=100, height=100, confidence=0.95),
            confidence=0.95,
            status="tracked",
            face_count=1,
        ),
        TrackChoice(
            time=0.5,
            track_id=2,
            box=FaceBox(x=1000, y=300, width=100, height=100, confidence=0.95),
            confidence=0.95,
            status="tracked",
            face_count=1,
        ),
    ]

    plan = build_crop_plan(
        choices,
        1280,
        720,
        9 / 16,
        0.0,
        2.0,
        settings,
    )

    crop_width = plan.crop_width
    max_step = crop_width * settings.crop_max_speed_ratio * 0.5
    delta = abs(plan.samples[1].center_x - plan.samples[0].center_x)
    assert delta <= max_step + 1e-6


def test_crop_plan_interpolates_between_samples(settings: Settings):
    adjusted = settings.model_copy(
        update={
            "crop_ema_alpha": 1.0,
            "crop_dead_zone_ratio": 0.0,
            "crop_max_speed_ratio": 100.0,
        }
    )
    choices = [
        TrackChoice(
            time=0.0,
            track_id=1,
            box=FaceBox(x=250, y=300, width=100, height=100, confidence=0.95),
            confidence=0.95,
            status="tracked",
            face_count=1,
        ),
        TrackChoice(
            time=1.0,
            track_id=1,
            box=FaceBox(x=450, y=300, width=100, height=100, confidence=0.95),
            confidence=0.95,
            status="tracked",
            face_count=1,
        ),
    ]
    plan = build_crop_plan(
        choices,
        1280,
        720,
        9 / 16,
        0.0,
        2.0,
        adjusted,
    )

    center_x, _center_y, crop_width, _crop_height = interpolate_crop(plan, 0.5)
    assert center_x == pytest.approx(400.0)
    assert crop_width == pytest.approx(plan.crop_width)

    from_dict = interpolate_crop(plan.to_dict(), 0.5)
    assert from_dict[0] == pytest.approx(center_x)


def test_centered_result_is_explicit_and_stable(settings: Settings):
    result = build_centered_result(
        10.0,
        20.0,
        1280,
        720,
        settings,
        status="unavailable",
        detail="Model missing.",
        error_code="face_model_missing",
    )

    assert result.status == "unavailable"
    assert result.confidence == 0.0
    assert result.details["error_code"] == "face_model_missing"
    assert result.crop_plan["samples"]
    assert all(
        sample["status"] == "centered"
        for sample in result.crop_plan["samples"]
    )
    assert result.crop_plan["samples"][0]["x"] == pytest.approx(640.0)


def test_summarize_choices_reports_no_faces(settings: Settings):
    choices = [
        TrackChoice(
            time=0.0,
            track_id=None,
            box=None,
            confidence=0.0,
            status="none",
            face_count=0,
        )
    ]

    status, confidence = summarize_choices(choices)

    assert status == "no_faces"
    assert confidence == 0.0


def test_missing_face_model_raises_actionable_error(tmp_path):
    detector = OpenCVYuNetDetector(tmp_path / "missing.onnx")

    with pytest.raises(FaceDetectionError) as excinfo:
        detector.detect(np.zeros((16, 16, 3), dtype=np.uint8))

    assert excinfo.value.code in {
        "face_model_missing",
        "face_detection_unavailable",
    }


class _FakeDetector:
    name = "fake-detector"

    def detect(self, frame):
        return [FaceBox(x=500, y=200, width=120, height=120, confidence=0.9)]

    def close(self):
        pass


def test_tracker_orchestration_builds_a_crop_plan(
    settings: Settings, monkeypatch, tmp_path
):
    from app.services import speaker_tracking

    sampled = [
        SampledFrame(
            index=index,
            time_seconds=float(index),
            path=tmp_path / f"frame_{index}.jpg",
        )
        for index in range(3)
    ]
    monkeypatch.setattr(
        speaker_tracking, "sample_clip_frames", lambda *args, **kwargs: sampled
    )
    monkeypatch.setattr(
        speaker_tracking,
        "_to_grayscale",
        lambda image: np.zeros((720, 1280), dtype=np.uint8),
    )

    progress: list[float] = []
    tracker = OpenCVSpeakerTracker(
        settings,
        detector_factory=lambda _settings: _FakeDetector(),
        frame_loader=lambda _path: np.zeros((720, 1280, 3), dtype=np.uint8),
    )
    result = tracker.track(
        tmp_path / "source.mp4",
        10.0,
        13.0,
        1280,
        720,
        None,
        tmp_path / "work",
        on_progress=progress.append,
    )

    assert result.status == "tracked"
    assert result.confidence > 0.8
    assert result.crop_plan["coordinate_space"] == "source_pixels"
    assert result.crop_plan["time_space"] == "clip_relative_seconds"
    assert len(result.crop_plan["samples"]) == 3
    assert result.crop_plan["samples"][0]["time"] == pytest.approx(0.0)
    assert result.crop_plan["samples"][0]["x"] < 640.0
    assert result.details["detector"] == "fake-detector"
    assert progress[-1] == pytest.approx(1.0)
    assert not (tmp_path / "work" / "frames").exists()


def test_tracker_returns_explicit_centred_result_when_model_is_missing(
    settings: Settings, tmp_path
):
    def factory(_settings):
        raise FaceDetectionError(
            "face_model_missing",
            "The face-detection model was not found.",
        )

    tracker = OpenCVSpeakerTracker(settings, detector_factory=factory)
    result = tracker.track(
        tmp_path / "source.mp4",
        0.0,
        5.0,
        1280,
        720,
        None,
        tmp_path / "work",
    )

    assert result.status == "unavailable"
    assert result.confidence == 0.0
    assert result.details["error_code"] == "face_model_missing"
    assert all(
        sample["status"] == "centered"
        for sample in result.crop_plan["samples"]
    )
