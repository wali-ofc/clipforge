"""Upload and job lifecycle tests."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from app.config import Settings
from app.main import create_app
from app.models.job import Job


def _upload(client, path: Path, *, filename: str | None = None):
    with path.open("rb") as handle:
        return client.post(
            "/api/jobs",
            files={
                "file": (
                    filename or path.name,
                    handle,
                    "video/mp4",
                )
            },
        )


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/api/jobs",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_file_type"


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/jobs",
        files={"file": ("empty.mp4", b"", "video/mp4")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "empty_file"


def test_upload_rejects_corrupt_file(client):
    response = client.post(
        "/api/jobs",
        files={"file": ("broken.mp4", b"not actually a video" * 20, "video/mp4")},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unreadable_media"

    data_dir = client.app.state.settings.data_dir
    assert not any((data_dir / "uploads").glob("*"))


def test_upload_rejects_file_without_video_stream(client, audio_only_file):
    response = _upload(client, audio_only_file)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "no_video_stream"


def test_upload_rejects_oversized_file(settings: Settings):
    limited = settings.model_copy(update={"max_upload_bytes": 64})
    app = create_app(limited)
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            files={"file": ("large.mp4", b"x" * 1024, "video/mp4")},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "file_too_large"
    assert not any((limited.data_dir / "uploads").glob("*"))


def test_valid_upload_creates_queued_job_and_worker_completes(client, sample_video):
    response = _upload(client, sample_video, filename="../../my talk.mp4")
    assert response.status_code == 202

    payload = response.json()
    job_id = payload["id"]
    UUID(job_id)
    assert payload["state"] == "queued"
    assert payload["progress"] == 0
    assert payload["original_filename"] == "my talk.mp4"
    assert payload["duration_seconds"] > 0

    settings = client.app.state.settings
    stored_files = list((settings.uploads_dir / job_id).glob("*"))
    assert len(stored_files) == 1
    assert stored_files[0].name == "source.mp4"
    assert stored_files[0].read_bytes() == sample_video.read_bytes()

    with client.app.state.session_factory() as session:
        stored_job = session.get(Job, job_id)
        assert stored_job is not None
        assert stored_job.stored_path == f"uploads/{job_id}/source.mp4"
        assert stored_job.state == "queued"

    worker = client.app.state.worker
    assert worker.run_once() is True
    assert worker.run_once() is False

    detail = client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    completed = detail.json()
    assert completed["state"] == "completed"
    assert completed["progress"] == 100
    assert completed["width"] == 320
    assert completed["height"] == 240
    assert completed["video_codec"] == "h264"
    assert completed["has_audio"] is True
    assert "not enabled" in completed["stage_message"]
    assert completed["completed_at"] is not None


def test_job_record_survives_app_restart(settings: Settings, sample_video):
    from fastapi.testclient import TestClient

    first_app = create_app(settings)
    with TestClient(first_app) as client:
        response = _upload(client, sample_video)
        assert response.status_code == 202
        job_id = response.json()["id"]

    second_app = create_app(settings)
    with TestClient(second_app) as client:
        detail = client.get(f"/api/jobs/{job_id}")
        assert detail.status_code == 200
        assert detail.json()["state"] == "queued"
        assert detail.json()["original_filename"] == "sample.mp4"


def test_clip_list_is_empty_in_phase_one(client, sample_video):
    response = _upload(client, sample_video)
    job_id = response.json()["id"]

    clips = client.get(f"/api/jobs/{job_id}/clips")
    assert clips.status_code == 200
    assert clips.json() == []


def test_unknown_job_returns_clear_404(client):
    response = client.get(f"/api/jobs/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "job_not_found",
        "message": "No job exists with that ID.",
    }


def test_clip_list_for_unknown_job_returns_404(client):
    response = client.get(f"/api/jobs/{uuid4()}/clips")
    assert response.status_code == 404
