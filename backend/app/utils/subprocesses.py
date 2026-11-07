"""Safe subprocess helpers.

Commands are always passed as argument arrays. Callers must never use
``shell=True`` or interpolate user input into a command string.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class CommandError(RuntimeError):
    """A subprocess exited with a non-zero status."""

    def __init__(
        self,
        command: Sequence[str],
        returncode: int,
        stderr: str,
        *,
        timed_out: bool = False,
    ) -> None:
        self.command = list(command)
        self.returncode = returncode
        self.stderr = stderr
        self.timed_out = timed_out
        super().__init__(self._message())

    def _message(self) -> str:
        executable = Path(self.command[0]).name if self.command else "command"
        if self.timed_out:
            return f"{executable} timed out."
        detail = self.stderr.strip().splitlines()
        tail = detail[-1] if detail else "no error output"
        return f"{executable} exited with code {self.returncode}: {tail}"


class CommandNotFoundError(RuntimeError):
    """The executable could not be found."""

    def __init__(self, command: Sequence[str]) -> None:
        self.command = list(command)
        super().__init__(f"Executable not found: {self.command[0] if self.command else ''}")


def command_exists(command: str) -> bool:
    """Return True when a configured command can be found."""
    if not command.strip():
        return False

    expanded = os.path.expanduser(command)
    if Path(expanded).is_absolute() or "/" in expanded or "\\" in expanded:
        return Path(expanded).is_file()

    return shutil.which(expanded) is not None


def run_command(
    args: Sequence[str],
    *,
    timeout: float,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing output as text, and raise on failure."""
    if not args:
        raise ValueError("run_command requires at least one argument")

    try:
        completed = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            creationflags=_CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise CommandNotFoundError(args) from exc
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        raise CommandError(args, -1, stderr, timed_out=True) from exc

    if completed.returncode != 0:
        raise CommandError(args, completed.returncode, completed.stderr or "")

    return completed
