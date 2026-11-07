"""Health and shared API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    available: bool
    version: str | None = None
    detail: str | None = None


class HealthLimits(BaseModel):
    max_upload_bytes: int = Field(gt=0)
    allowed_formats: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    version: str
    environment: str
    checks: dict[str, HealthCheck]
    limits: HealthLimits
