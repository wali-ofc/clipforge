"""Safe subprocess helpers.

Commands are always passed as argument arrays. Callers must never use
``shell=True`` or interpolate user input into a command string.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Sequence

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# How often a cancellable subprocess checks for a cancellation request.
_CANCEL_POLL_SECONDS = 0.2


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


class CommandCancelled(CommandError):
    """A running command was stopped because the job was cancelled."""

    def __init__(self, command: Sequence[str]) -> None:
        super().__init__(command, -1, "cancelled")


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


def _terminate(process: subprocess.Popen[str]) -> None:
    """Stop a subprocess and wait briefly for it to exit."""
    if process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive
        pass


def _run_cancellable(
    args: Sequence[str],
    *,
    timeout: float,
    cwd: Path | None,
    cancel_check: Callable[[], bool],
) -> subprocess.CompletedProcess[str]:
    try:
        process = subprocess.Popen(
            list(args),
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise CommandNotFoundError(args) from exc

    started = time.monotonic()
    while True:
        if cancel_check():
            _terminate(process)
            raise CommandCancelled(args)

        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            _terminate(process)
            raise CommandError(args, -1, "", timed_out=True)

        try:
            stdout, stderr = process.communicate(
                timeout=min(_CANCEL_POLL_SECONDS, remaining)
            )
        except subprocess.TimeoutExpired:
            continue
        break

    completed = subprocess.CompletedProcess(
        args=list(args),
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
    )
    if completed.returncode != 0:
        raise CommandError(args, completed.returncode, completed.stderr or "")
    return completed


def run_command(
    args: Sequence[str],
    *,
    timeout: float,
    cwd: Path | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing output as text, and raise on failure.

    When ``cancel_check`` is supplied the command is polled so a cancelled job
    can stop FFmpeg promptly instead of waiting for the full timeout.
    """
    if not args:
        raise ValueError("run_command requires at least one argument")

    if cancel_check is not None:
        return _run_cancellable(
            args,
            timeout=timeout,
            cwd=cwd,
            cancel_check=cancel_check,
        )

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
