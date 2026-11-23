"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_clips, routes_health, routes_jobs, routes_sources, routes_upload
from app.config import Settings, get_settings
from app.db import (
    create_engine_from_settings,
    create_session_factory,
    init_db,
)
from app.services.cleanup import cleanup_orphan_job_dirs
from app.services.clip_selection import ClipSelector
from app.services.rendering import ClipRenderer
from app.services.speaker_tracking import SpeakerTracker
from app.services.tooling import (
    check_face_detection,
    check_media_tools,
    check_ollama,
    check_whisper,
    media_tools_available,
)
from app.services.transcription import Transcriber
from app.utils.files import human_size
from app.utils.paths import ensure_data_dirs
from app.worker.runner import JobWorker, recover_interrupted_jobs

logger = logging.getLogger(__name__)


def _configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def create_app(
    settings: Settings | None = None,
    transcriber: Transcriber | None = None,
    selector: ClipSelector | None = None,
    speaker_tracker: SpeakerTracker | None = None,
    renderer: ClipRenderer | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _configure_logging(resolved_settings)
        logger.info(
            "Starting %s %s in %s mode",
            resolved_settings.app_name,
            resolved_settings.app_version,
            resolved_settings.app_env,
        )

        ensure_data_dirs(resolved_settings)
        engine = create_engine_from_settings(resolved_settings)
        init_db(engine)
        session_factory = create_session_factory(engine)

        app.state.engine = engine
        app.state.session_factory = session_factory
        # Source-level transcription reuses the same configured transcriber as
        # the job worker, so a video is never loaded by a second model instance.
        app.state.transcriber = transcriber

        media_tools = check_media_tools(resolved_settings)
        app.state.media_tools = media_tools
        if not media_tools_available(media_tools):
            logger.error(
                "Media tools are unavailable. Uploads will be rejected until "
                "FFmpeg and ffprobe are configured."
            )

        whisper_check = check_whisper(resolved_settings)
        app.state.whisper_check = whisper_check
        if not whisper_check.available:
            logger.error(
                "Transcription is unavailable: %s", whisper_check.detail
            )

        ollama_check = check_ollama(resolved_settings)
        app.state.ollama_check = ollama_check
        if not ollama_check.available:
            logger.warning(
                "Clip selection is unavailable: %s", ollama_check.detail
            )

        face_detection_check = check_face_detection(resolved_settings)
        app.state.face_detection_check = face_detection_check
        if not face_detection_check.available:
            logger.warning(
                "Speaker tracking will use centred crops: %s",
                face_detection_check.detail,
            )

        recover_interrupted_jobs(session_factory)
        cleanup_orphan_job_dirs(resolved_settings, session_factory)

        worker = JobWorker(
            resolved_settings,
            session_factory,
            transcriber=transcriber,
            selector=selector,
            speaker_tracker=speaker_tracker,
            renderer=renderer,
        )
        app.state.worker = worker
        if resolved_settings.worker_autostart:
            worker.start()

        logger.info("Data directory: %s", resolved_settings.data_dir)

        try:
            yield
        finally:
            worker.stop()
            engine.dispose()
            logger.info("Shutdown complete")

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Local-first video clipping pipeline.",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Service and dependency status."},
            {"name": "jobs", "description": "Upload, queue, and inspect jobs."},
            {"name": "sources", "description": "Reusable source projects and their cut jobs."},
        ],
    )
    app.state.settings = resolved_settings

    @app.middleware("http")
    async def reject_oversized_upload(request, call_next):
        """Reject clearly oversized multipart bodies before they are spooled."""
        if request.method == "POST" and request.url.path in {"/api/jobs", "/api/sources"}:
            raw_length = request.headers.get("content-length")
            if raw_length:
                try:
                    content_length = int(raw_length)
                except ValueError:
                    content_length = 0
                # Allow a small multipart overhead margin on top of the file
                # limit so a file at the limit is not rejected by boundaries.
                if content_length > resolved_settings.max_upload_bytes + 1024 * 1024:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": {
                                "code": "file_too_large",
                                "message": (
                                    "The upload exceeds the maximum size of "
                                    f"{human_size(resolved_settings.max_upload_bytes)}."
                                ),
                            }
                        },
                    )
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router)
    app.include_router(routes_upload.router)
    app.include_router(routes_sources.router)
    app.include_router(routes_jobs.router)
    app.include_router(routes_clips.router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": resolved_settings.app_name,
            "version": resolved_settings.app_version,
            "health": "/api/health",
            "docs": "/docs",
        }

    return app


app = create_app()
