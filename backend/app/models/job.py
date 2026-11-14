"""Job model and state definitions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.utils.time import utc_now

if TYPE_CHECKING:
    from app.models.clip import Clip


class JobState(str, Enum):
    queued = "queued"
    inspecting = "inspecting"
    transcribing = "transcribing"
    selecting_clips = "selecting_clips"
    tracking_speakers = "tracking_speakers"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in TERMINAL_JOB_STATES

    @property
    def is_active(self) -> bool:
        return self in ACTIVE_JOB_STATES


TERMINAL_JOB_STATES = frozenset(
    {JobState.completed, JobState.failed, JobState.cancelled}
)

ACTIVE_JOB_STATES = frozenset(
    {
        JobState.inspecting,
        JobState.transcribing,
        JobState.selecting_clips,
        JobState.tracking_speakers,
        JobState.rendering,
    }
)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_queue", "state", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=JobState.queued.value
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage_message: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Queued"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rotation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    video_codec: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_codec: Mapped[str | None] = mapped_column(String(64), nullable=True)
    has_audio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    container_format: Mapped[str | None] = mapped_column(String(128), nullable=True)
    frame_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    transcript_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    transcript_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transcript_segment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_speech: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    clip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clip_selection_model: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    speaker_tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clips: Mapped[list["Clip"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    @property
    def state_enum(self) -> JobState:
        return JobState(self.state)

    @property
    def has_transcript(self) -> bool:
        return self.transcript_path is not None

    @property
    def has_clips(self) -> bool:
        return self.clip_count > 0
