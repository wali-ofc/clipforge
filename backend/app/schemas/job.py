"""API response schemas for jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.job import JobKind, JobState


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str | None = None
    original_filename: str
    content_type: str | None = None
    size_bytes: int

    kind: JobKind = JobKind.ai_clipper
    state: JobState
    progress: int = Field(ge=0, le=100)
    stage_message: str
    error: str | None = None

    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    rotation: int = 0
    video_codec: str | None = None
    audio_codec: str | None = None
    has_audio: bool = False
    container_format: str | None = None
    frame_rate: float | None = None

    has_transcript: bool = False
    transcript_language: str | None = None
    transcript_segment_count: int | None = None
    has_speech: bool | None = None
    source_has_transcript: bool = False
    source_transcript_status: str | None = None

    clip_count: int = 0
    clip_selection_model: str | None = None
    speaker_tracking_enabled: bool = True

    segment_spec: str | None = None
    segment_output_frame: str | None = None
    segment_options: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @field_serializer(
        "created_at", "updated_at", "started_at", "completed_at", when_used="json"
    )
    def _serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):  # type: ignore[override]
        model = super().model_validate(obj, *args, **kwargs)
        # If transcript is provided by the source, surface its metadata.
        if not model.has_transcript:
            source = getattr(obj, "source", None)
            if source is not None and getattr(source, "transcript_path", None):
                model.has_transcript = True
                model.transcript_language = model.transcript_language or getattr(source, "transcript_language", None)
                model.transcript_segment_count = model.transcript_segment_count or getattr(source, "transcript_segment_count", None)
                if model.has_speech is None:
                    model.has_speech = getattr(source, "has_speech", None)
        source = getattr(obj, "source", None)
        if source is not None:
            model.source_has_transcript = bool(getattr(source, "transcript_path", None))
            model.source_transcript_status = getattr(source, "transcript_status", None)
        return model
