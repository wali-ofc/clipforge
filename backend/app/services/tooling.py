"""Availability checks for required local executables."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as package_version

from app.config import Settings
from app.services.ollama import OllamaClient
from app.utils.subprocesses import (
    CommandError,
    CommandNotFoundError,
    command_exists,
    run_command,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolCheck:
    name: str
    command: str
    available: bool
    version: str | None = None
    detail: str | None = None


def _check_tool(name: str, command: str, install_hint: str) -> ToolCheck:
    if not command_exists(command):
        return ToolCheck(
            name=name,
            command=command,
            available=False,
            detail=install_hint,
        )

    try:
        completed = run_command([command, "-version"], timeout=15)
    except (CommandNotFoundError, CommandError) as exc:
        return ToolCheck(
            name=name,
            command=command,
            available=False,
            detail=f"{install_hint} ({exc})",
        )

    output = (completed.stdout or "").strip().splitlines()
    version = output[0][:200] if output else None
    return ToolCheck(
        name=name,
        command=command,
        available=True,
        version=version,
    )


def check_media_tools(settings: Settings) -> dict[str, ToolCheck]:
    checks = {
        "ffmpeg": _check_tool(
            "ffmpeg",
            settings.ffmpeg_bin,
            "FFmpeg was not found. Install FFmpeg and add it to PATH, or set "
            "FFMPEG_BIN to the full executable path.",
        ),
        "ffprobe": _check_tool(
            "ffprobe",
            settings.ffprobe_bin,
            "ffprobe was not found. Install FFmpeg and add it to PATH, or set "
            "FFPROBE_BIN to the full executable path.",
        ),
    }

    for check in checks.values():
        if not check.available:
            logger.error("%s: %s", check.name, check.detail)

    return checks


def media_tools_available(checks: dict[str, ToolCheck]) -> bool:
    return all(check.available for check in checks.values())


def check_whisper(settings: Settings) -> ToolCheck:
    """Report whether the faster-whisper package is installed.

    The model itself is downloaded lazily on the first transcription, so this
    check intentionally does not load weights.
    """
    try:
        installed = package_version("faster-whisper")
    except PackageNotFoundError:
        return ToolCheck(
            name="whisper",
            command=settings.whisper_model,
            available=False,
            detail=(
                "faster-whisper is not installed. Install backend dependencies "
                "and restart the server."
            ),
        )

    return ToolCheck(
        name="whisper",
        command=settings.whisper_model,
        available=True,
        version=(
            f"faster-whisper {installed} · {settings.whisper_device}/"
            f"{settings.whisper_compute_type} · model {settings.whisper_model}"
        ),
    )


def check_ollama(settings: Settings) -> ToolCheck:
    """Report whether Ollama is reachable and the configured model is present.

    This only calls the lightweight version/tags endpoints; it never loads a
    model. Clip selection is unavailable until this check passes.
    """
    with OllamaClient(settings) as client:
        probe = client.probe()

    if not probe.reachable:
        return ToolCheck(
            name="ollama",
            command=settings.ollama_model,
            available=False,
            detail=probe.detail
            or (
                f"Ollama is not reachable at {settings.ollama_base_url}. "
                "Start it with `ollama serve` and retry."
            ),
        )

    if probe.model_available is False:
        return ToolCheck(
            name="ollama",
            command=settings.ollama_model,
            available=False,
            detail=probe.detail
            or (
                f"Ollama is running but the model '{settings.ollama_model}' is "
                f"not installed. Run `ollama pull {settings.ollama_model}`."
            ),
        )

    version = f"Ollama {probe.version or 'running'} · model {settings.ollama_model}"
    return ToolCheck(
        name="ollama",
        command=settings.ollama_model,
        available=True,
        version=version,
        detail=probe.detail,
    )
