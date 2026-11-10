"""Modular face-detection interface.

Phase 4 deliberately keeps the detector behind a small protocol so the rest
of the pipeline does not depend on OpenCV. The default implementation uses
OpenCV's YuNet ONNX detector, which is small, CPU-friendly, and ships as a
single model file.

If the model file or OpenCV is unavailable, callers receive a
``FaceDetectionError`` with an actionable message. The speaker tracker turns
that into an explicit ``unavailable`` status and a stable centre crop instead
of silently claiming that faces were tracked.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from app.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL_FILENAME = "face_detection_yunet_2023mar.onnx"


class FaceDetectionError(Exception):
    """A face-detection failure with a user-facing message."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class FaceBox:
    """A face rectangle in decoded source-frame pixels.

    The coordinates refer to the frame after FFmpeg has applied rotation
    metadata, i.e. the same display orientation reported by ``probe_media``.
    """

    x: float
    y: float
    width: float
    height: float
    confidence: float = 1.0

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)

    def clamped(self, frame_width: int, frame_height: int) -> "FaceBox":
        """Clamp the rectangle to the frame and return a new box."""
        width = min(max(0.0, self.width), float(frame_width))
        height = min(max(0.0, self.height), float(frame_height))
        x = min(max(0.0, self.x), max(0.0, frame_width - width))
        y = min(max(0.0, self.y), max(0.0, frame_height - height))
        return FaceBox(
            x=x,
            y=y,
            width=width,
            height=height,
            confidence=max(0.0, min(1.0, self.confidence)),
        )

    def iou(self, other: "FaceBox") -> float:
        """Intersection over union for track association."""
        left = max(self.x, other.x)
        top = max(self.y, other.y)
        right = min(self.x + self.width, other.x + other.width)
        bottom = min(self.y + self.height, other.y + other.height)
        intersection = max(0.0, right - left) * max(0.0, bottom - top)
        if intersection <= 0:
            return 0.0
        union = self.area + other.area - intersection
        return intersection / union if union > 0 else 0.0


class FaceDetector(Protocol):
    """Detects faces in one decoded frame."""

    name: str

    def detect(self, frame: np.ndarray) -> list[FaceBox]:
        """Return face boxes in frame pixels."""

    def close(self) -> None:
        """Release detector resources."""


class OpenCVYuNetDetector:
    """OpenCV YuNet face detector.

    The model is loaded lazily so importing this module never requires OpenCV
    and a missing model does not prevent the rest of the app from starting.
    """

    name = "opencv-yunet"

    def __init__(
        self,
        model_path: Path,
        *,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
        min_size: int = 32,
    ) -> None:
        self.model_path = Path(model_path)
        self.score_threshold = float(score_threshold)
        self.nms_threshold = float(nms_threshold)
        self.top_k = int(top_k)
        self.min_size = int(min_size)
        self._cv2: Any = None
        self._detector: Any = None

    def _load(self) -> None:
        if self._detector is not None:
            return

        try:
            import cv2  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise FaceDetectionError(
                "face_detection_unavailable",
                "Face detection is unavailable because OpenCV is not installed. "
                "Install backend dependencies and restart the server.",
            ) from exc

        if not self.model_path.is_file():
            raise FaceDetectionError(
                "face_model_missing",
                "The face-detection model was not found at "
                f"{self.model_path}. Download the YuNet ONNX model there or set "
                "FACE_DETECTOR_MODEL_PATH.",
            )

        try:
            detector = cv2.FaceDetectorYN.create(
                str(self.model_path),
                "",
                (320, 320),
                self.score_threshold,
                self.nms_threshold,
                self.top_k,
            )
        except Exception as exc:  # noqa: BLE001 - surface an actionable message
            logger.exception("Could not load the face-detection model")
            raise FaceDetectionError(
                "face_model_unreadable",
                "The face-detection model could not be loaded. Re-download "
                f"{self.model_path.name} and restart the server.",
            ) from exc

        self._cv2 = cv2
        self._detector = detector

    def detect(self, frame: np.ndarray) -> list[FaceBox]:
        self._load()
        if frame is None or frame.ndim < 2:
            return []

        height, width = int(frame.shape[0]), int(frame.shape[1])
        if width <= 0 or height <= 0:
            return []

        try:
            self._detector.setInputSize((width, height))
            _, raw_faces = self._detector.detect(frame)
        except Exception as exc:  # noqa: BLE001 - keep one bad frame non-fatal
            logger.warning("Face detection failed for one frame: %s", exc)
            return []

        if raw_faces is None:
            return []

        faces: list[FaceBox] = []
        for row in raw_faces:
            if len(row) < 5:
                continue
            x, y, box_width, box_height = (float(value) for value in row[:4])
            confidence = float(row[-1])
            if confidence < self.score_threshold:
                continue
            if box_width < self.min_size or box_height < self.min_size:
                continue
            box = FaceBox(
                x=x,
                y=y,
                width=box_width,
                height=box_height,
                confidence=confidence,
            ).clamped(width, height)
            if box.width > 0 and box.height > 0:
                faces.append(box)

        # Larger, more confident faces first makes downstream fallback
        # selection deterministic when scores tie.
        faces.sort(key=lambda box: (-box.area, -box.confidence, box.x, box.y))
        return faces

    def close(self) -> None:
        self._detector = None


def create_face_detector(settings: Settings) -> FaceDetector:
    """Build the configured detector.

    This is the single place that knows the concrete implementation, so a
    different detector can be dropped in without changing the tracker.
    """
    return OpenCVYuNetDetector(
        settings.face_detector_model_path,
        score_threshold=settings.face_detector_score_threshold,
        nms_threshold=settings.face_detector_nms_threshold,
        top_k=settings.face_detector_top_k,
        min_size=settings.face_detector_min_size,
    )
