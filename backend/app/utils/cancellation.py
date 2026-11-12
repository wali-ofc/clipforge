"""Cooperative cancellation primitives for background jobs.

Cancellation is explicit rather than relying on killing the worker thread.
Long-running stages poll a :class:`CancelToken` at safe boundaries (between
clips, between progress callbacks, and inside subprocess waits). When a token
is cancelled, the pipeline raises :class:`JobCancelled`, records the cancelled
state, and removes temporary files.
"""

from __future__ import annotations

import threading


class JobCancelled(Exception):
    """Raised when a job is cancelled between pipeline stages."""

    def __init__(self, message: str = "The job was cancelled.") -> None:
        self.message = message
        super().__init__(message)


class CancelToken:
    """Thread-safe cancellation flag plus a completion event.

    ``done`` is set by the worker when it has stopped touching the job's
    files, so a delete request can wait for in-flight work to unwind before
    removing directories.
    """

    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._done = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def done(self) -> threading.Event:
        return self._done

    def cancel(self) -> None:
        self._cancelled.set()

    def finish(self) -> None:
        self._done.set()

    def should_cancel(self) -> bool:
        """Return True when cancellation has been requested."""
        return self._cancelled.is_set()

    def raise_if_cancelled(self) -> None:
        if self._cancelled.is_set():
            raise JobCancelled()
