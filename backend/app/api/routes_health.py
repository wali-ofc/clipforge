"""Health endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.config import Settings
from app.schemas.health import HealthCheck, HealthLimits, HealthResponse
from app.services.tooling import check_media_tools, check_whisper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    checks: dict[str, HealthCheck] = {}

    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = HealthCheck(available=True, detail="SQLite reachable")
    except Exception as exc:  # noqa: BLE001 - surface a degraded health state
        logger.warning("Database health check failed: %s", exc)
        checks["database"] = HealthCheck(
            available=False,
            detail="The SQLite database could not be reached.",
        )

    tools = getattr(request.app.state, "media_tools", None)
    if tools is None:
        tools = check_media_tools(settings)
        request.app.state.media_tools = tools

    for name, check in tools.items():
        checks[name] = HealthCheck(
            available=check.available,
            version=check.version,
            detail=check.detail,
        )

    whisper = getattr(request.app.state, "whisper_check", None)
    if whisper is None:
        whisper = check_whisper(settings)
        request.app.state.whisper_check = whisper
    checks["whisper"] = HealthCheck(
        available=whisper.available,
        version=whisper.version,
        detail=whisper.detail,
    )

    healthy = all(check.available for check in checks.values())
    return HealthResponse(
        status="ok" if healthy else "degraded",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        checks=checks,
        limits=HealthLimits(
            max_upload_bytes=settings.max_upload_bytes,
            allowed_formats=[
                f".{extension}" for extension in settings.allowed_video_extensions
            ],
        ),
    )
