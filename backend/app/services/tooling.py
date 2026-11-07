"""Availability checks for required local executables."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings
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
