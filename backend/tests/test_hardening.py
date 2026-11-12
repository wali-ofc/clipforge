"""Cancellation, deletion, disk-space, and path-safety tests (Phase 7)."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.main import create_app
from app.models.clip import Clip
from app.models.job import Job, JobState
from app.services.cleanup import cleanup_orphan_job_dirs, delete_job_files
from app.utils.cancellation import CancelToken, JobCancelled
from app.utils.subprocesses import CommandCancelled, run_command
from app.utils.time import utc_now
from app.worker.pipeline import process_job


def _upload(client, path: Path, *, filename: str | None = None):
    with path.open("rb") as handle:
        return client.post(
            "/api/jobs",
            files={"file": (filename or path.name, handle, "video/mp4")},
        )


def _job_row(job_id: str, **overrides) -> Job:
    values = {
        "id": job_id,
        "original_filename": "test.mp4",
        "stored_path": f"uploads/{job_id}/source.mp4",
        "content_type": "video/mp4",
        "size_bytes": 10,
        "state": JobState.completed.value,
        "progress": 100,
        "stage_message": "Completed",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    values.update(overrides)
    return Job(**values)


def _clip_row(clip_id: str, job_id: str, **overrides) -> Clip:
    values = {
        "id": clip_id,
        "job_id": job_id,
        "start_seconds": 0.0,
        "end_seconds": 5.0,
        "duration_seconds": 5.0,
        "title": "Test clip",
        "component_scores": {},
        "crop_plan": {},
        "tracking_details": {},
        "render_status": "completed",
        "output_filename": f"clips/{job_id}/{clip_id}.mp4",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    values.update(overrides)
    return Clip(**values)


def _job_dirs(settings: Settings, job_id: str) -> tuple[Path, Path, Path]:
    return (
        settings.uploads_dir / job_id,
        settings.work_dir / job_id,
        settings.clips_dir / job_id,
    )


class BlockingTranscriber:
    """Stops inside transcription until the cancel token is set."""

    def __init__(self) -> None:
        self.started = threading.Event()

    def transcribe(
        self,
        source_path,
        duration_seconds,
        work_dir,
        on_progress=None,
        cancel_check=None,
    ):
        self.started.set()
        while True:
            if cancel_check is not None and cancel_check():
                raise JobCancelled()
            time.sleep(0.02)


def test_delete_completed_job_removes_record_clips_and_media(
    client, long_sample_video
):
    response = _upload(client, long_sample_video)
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert client.app.state.worker.run_once() is True

    settings = client.app.state.settings
    assert all(directory.is_dir() for directory in _job_dirs(settings, job_id))

    with client.app.state.session_factory() as session:
        assert session.get(Job, job_id) is not None
        clip_ids = list(
            session.execute(
                select(Clip.id).where(Clip.job_id == job_id)
            ).scalars()
        )
    assert clip_ids

    delete_response = client.delete(f"/api/jobs/{job_id}")
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    assert client.get(f"/api/jobs/{job_id}").status_code == 404
    assert client.get(f"/api/jobs/{job_id}/clips").status_code == 404
    assert not any(directory.exists() for directory in _job_dirs(settings, job_id))

    with client.app.state.session_factory() as session:
        assert session.get(Job, job_id) is None
        remaining = session.execute(
            select(Clip.id).where(Clip.job_id == job_id)
        ).scalars().all()
        assert remaining == []


def test_delete_queued_job_removes_upload_without_worker(client, sample_video):
    response = _upload(client, sample_video)
    assert response.status_code == 202
    job_id = response.json()["id"]
    settings = client.app.state.settings
    assert (settings.uploads_dir / job_id / "source.mp4").is_file()

    assert client.delete(f"/api/jobs/{job_id}").status_code == 204
    assert client.get(f"/api/jobs/{job_id}").status_code == 404
    assert not any(directory.exists() for directory in _job_dirs(settings, job_id))
    assert client.app.state.worker.run_once() is False


def test_delete_active_job_cancels_worker_and_removes_media(
    settings: Settings, sample_video
):
    transcriber = BlockingTranscriber()
    app = create_app(settings, transcriber=transcriber)

    with TestClient(app) as client:
        response = _upload(client, sample_video)
        assert response.status_code == 202
        job_id = response.json()["id"]

        worker = client.app.state.worker
        thread = threading.Thread(target=worker.run_once, daemon=True)
        thread.start()
        assert transcriber.started.wait(10), "worker never started transcription"
        assert worker.is_processing(job_id) is True

        delete_response = client.delete(f"/api/jobs/{job_id}")
        assert delete_response.status_code == 204

        thread.join(10)
        assert not thread.is_alive(), "worker did not stop after cancellation"
        assert worker.is_processing(job_id) is False

        assert client.get(f"/api/jobs/{job_id}").status_code == 404
        assert not any(
            directory.exists() for directory in _job_dirs(settings, job_id)
        )


def test_process_job_marks_preexisting_cancellation(client, sample_video):
    response = _upload(client, sample_video)
    job_id = response.json()["id"]

    token = CancelToken()
    token.cancel()

    with client.app.state.session_factory() as session:
        job = session.get(Job, job_id)
        process_job(session, job, client.app.state.settings, cancel_token=token)

    detail = client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["state"] == "cancelled"
    assert payload["stage_message"] == "Cancelled by user"
    assert payload["error"] is None
    assert payload["completed_at"] is not None

    # A cancelled job is terminal; the worker must not pick it up again.
    assert client.app.state.worker.run_once() is False


def test_delete_unknown_or_repeated_job_returns_404(client, sample_video):
    unknown = client.delete(f"/api/jobs/{uuid4()}")
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "job_not_found"

    response = _upload(client, sample_video)
    job_id = response.json()["id"]
    assert client.delete(f"/api/jobs/{job_id}").status_code == 204
    again = client.delete(f"/api/jobs/{job_id}")
    assert again.status_code == 404
    assert again.json()["detail"]["code"] == "job_not_found"


def test_cleanup_orphan_job_dirs_removes_only_unknown_uuid_dirs(
    client, sample_video
):
    settings = client.app.state.settings
    session_factory = client.app.state.session_factory

    response = _upload(client, sample_video)
    known_id = response.json()["id"]

    orphan_id = str(uuid4())
    for base in (settings.uploads_dir, settings.work_dir, settings.clips_dir):
        orphan_dir = base / orphan_id
        orphan_dir.mkdir(parents=True, exist_ok=True)
        (orphan_dir / "junk.bin").write_bytes(b"junk")

    # A known job keeps all of its directories, even empty ones.
    for base in (settings.work_dir, settings.clips_dir):
        (base / known_id).mkdir(parents=True, exist_ok=True)

    non_uuid_dir = settings.uploads_dir / "not-a-job"
    non_uuid_dir.mkdir(parents=True, exist_ok=True)

    removed = cleanup_orphan_job_dirs(settings, session_factory)
    assert removed == 3

    for base in (settings.uploads_dir, settings.work_dir, settings.clips_dir):
        assert not (base / orphan_id).exists()
    assert (settings.uploads_dir / known_id).is_dir()
    assert non_uuid_dir.is_dir()


def test_delete_job_files_refuses_non_uuid_ids(settings: Settings):
    outside = settings.data_dir.parent / "outside-job"
    outside.mkdir(parents=True, exist_ok=True)

    assert delete_job_files(settings, "../outside-job") == 0
    assert outside.is_dir()


def test_upload_rejects_when_free_disk_is_below_minimum(
    settings: Settings, sample_video
):
    limited = settings.model_copy(update={"min_free_disk_bytes": 10**18})
    app = create_app(limited)

    with TestClient(app) as client:
        response = _upload(client, sample_video)

    assert response.status_code == 507
    assert response.json()["detail"]["code"] == "insufficient_disk_space"
    assert not any(limited.uploads_dir.glob("*"))


def test_transcript_endpoint_rejects_unsafe_stored_path(client):
    job_id = str(uuid4())
    with client.app.state.session_factory() as session:
        session.add(_job_row(job_id, transcript_path="../outside.json"))
        session.commit()

    response = client.get(f"/api/jobs/{job_id}/transcript")
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "transcript_unreadable"


def test_clip_file_endpoint_rejects_unsafe_stored_path(client):
    job_id = str(uuid4())
    clip_id = str(uuid4())
    with client.app.state.session_factory() as session:
        session.add(_job_row(job_id))
        session.add(_clip_row(clip_id, job_id, output_filename="../outside.mp4"))
        session.commit()

    response = client.get(f"/api/clips/{clip_id}/file")
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "clip_unreadable"


def test_run_command_stops_promptly_when_cancelled():
    token = CancelToken()

    def cancel_after_delay() -> bool:
        if not token.cancelled:
            threading.Timer(0.2, token.cancel).start()
        return token.cancelled

    started = time.monotonic()
    with pytest.raises(CommandCancelled):
        run_command(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout=60,
            cancel_check=cancel_after_delay,
        )
    assert time.monotonic() - started < 10


def test_job_state_cancelled_is_terminal():
    assert JobState.cancelled.is_terminal is True
