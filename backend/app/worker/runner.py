"""Single-process background worker.

The queue is the SQLite ``jobs`` table itself. Jobs are claimed in creation
order, one at a time, so a restart never loses records and no work is silently
started without a database row.
"""

from __future__ import annotations

import logging
import threading

from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models.job import ACTIVE_JOB_STATES, Job, JobState
from app.services.clip_selection import ClipSelector
from app.services.rendering import ClipRenderer
from app.services.speaker_tracking import SpeakerTracker
from app.services.transcription import Transcriber
from app.utils.cancellation import CancelToken
from app.utils.time import utc_now
from app.worker.pipeline import claim_next_queued_job, process_job

logger = logging.getLogger(__name__)


def recover_interrupted_jobs(session_factory: sessionmaker[Session]) -> int:
    """Mark jobs left mid-pipeline by a previous process as failed."""
    active_states = [state.value for state in ACTIVE_JOB_STATES]
    values = {
        "state": JobState.failed.value,
        "stage_message": "Interrupted by server restart",
        "completed_at": utc_now(),
        "updated_at": utc_now(),
    }
    with session_factory() as session:
        source_result = session.execute(
            update(Job)
            .where(Job.state.in_(active_states), Job.source_id.is_not(None))
            .values(
                **values,
                error=(
                    "Processing was interrupted by a server restart. "
                    "Reopen the source project and cut the timestamps again."
                ),
            )
        )
        standalone_result = session.execute(
            update(Job)
            .where(Job.state.in_(active_states), Job.source_id.is_(None))
            .values(
                **values,
                error=(
                    "Processing was interrupted by a server restart. "
                    "Upload the video again to retry."
                ),
            )
        )
        session.commit()
        count = (source_result.rowcount or 0) + (standalone_result.rowcount or 0)

    if count:
        logger.warning("Marked %d interrupted job(s) as failed", count)
    return count


class JobWorker:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        transcriber: Transcriber | None = None,
        selector: ClipSelector | None = None,
        speaker_tracker: SpeakerTracker | None = None,
        renderer: ClipRenderer | None = None,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.transcriber = transcriber
        self.selector = selector
        self.speaker_tracker = speaker_tracker
        self.renderer = renderer
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._run_once_guard = threading.Lock()
        # Held while a queued job is claimed and its cancel token registered.
        # Delete requests take the same lock so they cannot miss a job that is
        # just entering the pipeline.
        self._claim_guard = threading.Lock()
        self._cancel_guard = threading.Lock()
        self._cancel_tokens: dict[str, CancelToken] = {}

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def is_processing(self, job_id: str) -> bool:
        """Return True while this worker owns a cancel token for the job."""
        with self._cancel_guard:
            return job_id in self._cancel_tokens

    def request_cancel(self, job_id: str) -> bool:
        """Request cancellation for a running job.

        Returns True when the job was actively processing. Taking the claim
        lock closes the race where a delete request arrives just as the worker
        is claiming the job.
        """
        with self._claim_guard:
            with self._cancel_guard:
                token = self._cancel_tokens.get(job_id)
            if token is None:
                return False
            token.cancel()
            return True

    def wait_for_job(self, job_id: str, timeout: float) -> bool:
        """Wait for a running job to stop touching its files.

        Returns True when the job is not running or stopped before the
        timeout, and False when it is still unwinding.
        """
        with self._cancel_guard:
            token = self._cancel_tokens.get(job_id)
        if token is None:
            return True
        return token.done.wait(max(0.0, timeout))

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="clipforge-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("Background worker started")

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=self.settings.worker_stop_timeout_seconds)
            if thread.is_alive():
                logger.warning("Background worker did not stop before the timeout")
        self._thread = None

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                processed = self.run_once()
            except Exception:  # noqa: BLE001 - keep the worker alive
                logger.exception("Unhandled error in worker loop")
                processed = False

            if not processed:
                self._stop_event.wait(self.settings.worker_poll_interval_seconds)

        logger.info("Background worker stopped")

    def run_once(self) -> bool:
        """Process at most one queued job. Returns True if a job was handled."""
        with self._run_once_guard:
            with self.session_factory() as session:
                with self._claim_guard:
                    job = claim_next_queued_job(session)
                    if job is None:
                        return False
                    token = CancelToken()
                    with self._cancel_guard:
                        self._cancel_tokens[job.id] = token

                logger.info("Worker claimed job %s", job.id)
                try:
                    process_job(
                        session,
                        job,
                        self.settings,
                        self.transcriber,
                        self.selector,
                        self.speaker_tracker,
                        self.renderer,
                        cancel_token=token,
                    )
                finally:
                    token.finish()
                    with self._cancel_guard:
                        self._cancel_tokens.pop(job.id, None)
                return True
