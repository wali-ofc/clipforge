"""File upload and filename helpers."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import BinaryIO

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")
_MAX_DISPLAY_FILENAME = 255


class UploadTooLarge(ValueError):
    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        super().__init__(f"Upload exceeds the configured limit of {human_size(max_bytes)}.")


class EmptyUpload(ValueError):
    def __init__(self) -> None:
        super().__init__("The uploaded file is empty.")


def sanitize_display_filename(filename: str) -> str:
    """Return a safe filename suitable only for display metadata."""
    normalized = (filename or "").replace("\\", "/")
    candidate = normalized.rsplit("/", 1)[-1]
    candidate = _CONTROL_CHARACTERS.sub("", candidate)
    candidate = _WHITESPACE.sub(" ", candidate).strip()
    candidate = candidate.strip(" .")

    if candidate in {"", ".", ".."}:
        return "upload"

    if len(candidate) > _MAX_DISPLAY_FILENAME:
        stem = Path(candidate).stem[: _MAX_DISPLAY_FILENAME - 16]
        suffix = Path(candidate).suffix[:15]
        candidate = f"{stem}{suffix}"

    return candidate


def file_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def stream_upload_to_path(
    source: BinaryIO,
    destination: Path,
    *,
    max_bytes: int,
    chunk_bytes: int,
) -> int:
    """Copy a streamed upload to disk while enforcing a byte limit.

    The destination is removed on any failure so callers never leave a partial
    upload behind.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = 0

    try:
        with destination.open("wb") as output:
            while True:
                chunk = source.read(chunk_bytes)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise UploadTooLarge(max_bytes)
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    if total == 0:
        destination.unlink(missing_ok=True)
        raise EmptyUpload()

    return total


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def human_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
