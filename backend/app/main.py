"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_clips, routes_health, routes_jobs, routes_upload
from app.config import Settings, get_settings
from app.db import (
    create_engine_from_settings,
    create_session_factory,
    init_db,
)
from app.services.clip_selection import ClipSelector
from app.services.tooling import (
    check_media_tools,
    check_ollama,
    check_whisper,
    media_tools_available,
)
from app.services.transcription import Transcriber
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

        recover_interrupted_jobs(session_factory)

        worker = JobWorker(
            resolved_settings,
            session_factory,
            transcriber=transcriber,
            selector=selector,
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
        ],
    )
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router)
    app.include_router(routes_upload.router)
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
