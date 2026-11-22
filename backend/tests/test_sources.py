"""Source project tests: one upload backing many segmenter cut jobs."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.models.clip import Clip
from app.models.job import Job
from app.models.source import Source


def _create_source(client, path: Path, *, filename: str | None = None):
    with path.open("rb") as handle:
        return client.post(
            "/api/sources",
            files={"file": (filename or path.name, handle, "video/mp4")},
        )


def _cut(client, source_id: str, spec: str, frame: str = "original"):
    return client.post(
        f"/api/sources/{source_id}/segments",
        data={"segment_spec": spec, "segment_output_frame": frame},
    )


def test_source_upload_creates_project_without_a_job(client, sample_video):
    response = _create_source(client, sample_video, filename="../talk.mp4")
    assert response.status_code == 201
    payload = response.json()
    source_id = payload["id"]
    assert payload["original_filename"] == "talk.mp4"
    assert payload["job_count"] == 0
    assert payload["duration_seconds"] > 0

    settings = client.app.state.settings
    stored = settings.uploads_dir / source_id / "source.mp4"
    assert stored.is_file()
    assert stored.read_bytes() == sample_video.read_bytes()

    with client.app.state.session_factory() as session:
        assert session.get(Source, source_id) is not None

    assert client.get("/api/sources").json()[0]["id"] == source_id
    assert client.get(f"/api/sources/{source_id}/jobs").json() == []


def test_multiple_cuts_reuse_one_source_and_survive_job_deletion(
    client, long_sample_video
):
    source_response = _create_source(client, long_sample_video)
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    first = _cut(client, source_id, "1 - 2\n3 - 4")
    second = _cut(client, source_id, "5 - 6", frame="portrait_9_16")
    assert first.status_code == 202
    assert second.status_code == 202

    first_id = first.json()["id"]
    second_id = second.json()["id"]
    assert first.json()["source_id"] == source_id
    assert first.json()["state"] == "queued"
    assert first.json()["segment_spec"] == "1 - 2\n3 - 4"
    assert second.json()["segment_output_frame"] == "portrait_9_16"

    jobs = client.get(f"/api/sources/{source_id}/jobs").json()
    assert {job["id"] for job in jobs} == {first_id, second_id}

    worker = client.app.state.worker
    assert worker.run_once() is True
    assert worker.run_once() is True
    assert worker.run_once() is False

    first_clips = client.get(f"/api/jobs/{first_id}/clips").json()
    second_clips = client.get(f"/api/jobs/{second_id}/clips").json()
    assert len(first_clips) == 2
    assert len(second_clips) == 1
    assert all(clip["render_status"] == "completed" for clip in first_clips + second_clips)
    assert client.get(f"/api/jobs/{first_id}").json()["state"] == "completed"

    settings = client.app.state.settings
    upload = settings.uploads_dir / source_id / "source.mp4"
    assert upload.is_file()

    # Deleting one cut keeps the shared source and the other cut intact.
    assert client.delete(f"/api/jobs/{first_id}").status_code == 204
    assert upload.is_file()
    assert client.get(f"/api/jobs/{second_id}").status_code == 200
    assert client.get(f"/api/sources/{source_id}").json()["job_count"] == 1
    with client.app.state.session_factory() as session:
        assert not session.execute(
            select(Clip.id).where(Clip.job_id == first_id)
        ).scalars().all()
        assert session.get(Source, source_id) is not None

    # Deleting the project removes every remaining cut and the upload.
    assert client.delete(f"/api/sources/{source_id}").status_code == 204
    assert not upload.parent.exists()
    assert client.get(f"/api/jobs/{second_id}").status_code == 404
    assert client.get(f"/api/sources/{source_id}").status_code == 404


def test_source_segment_validation(client, sample_video):
    source_id = _create_source(client, sample_video).json()["id"]

    bad_spec = _cut(client, source_id, "not a range")
    assert bad_spec.status_code == 400
    assert bad_spec.json()["detail"]["code"] == "invalid_segment_spec"

    bad_frame = _cut(client, source_id, "0 - 0.5", frame="square")
    assert bad_frame.status_code == 400
    assert bad_frame.json()["detail"]["code"] == "invalid_segment_frame"

    missing = _cut(client, source_id, "   ")
    assert missing.status_code == 400
    assert missing.json()["detail"]["code"] == "missing_segment_spec"

    with client.app.state.session_factory() as session:
        assert session.query(Job).filter(Job.source_id == source_id).count() == 0


def test_unknown_source_returns_404(client):
    missing = uuid4()
    assert client.get(f"/api/sources/{missing}").status_code == 404
    assert client.delete(f"/api/sources/{missing}").status_code == 404
    assert client.get(f"/api/sources/{missing}/jobs").status_code == 404
    assert _cut(client, str(missing), "0 - 0.5").status_code == 404


def test_source_upload_rejects_bad_files(client):
    response = client.post(
        "/api/sources", files={"file": ("notes.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_file_type"
