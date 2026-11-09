"""API response schemas for jobs."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.job import JobState


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str | None = None
    size_bytes: int

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
