"""API response schemas for clips."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    title: str
    hook: str | None = None
    reason: str | None = None
    score: float | None = None
    component_scores: dict[str, Any] = Field(default_factory=dict)
    output_filename: str | None = None
    width: int | None = None
    height: int | None = None
    speaker_tracking_status: str = "pending"
    speaker_tracking_confidence: float | None = None
    render_status: str = "pending"
    error: str | None = None
    created_at: datetime
    updated_at: datetime
