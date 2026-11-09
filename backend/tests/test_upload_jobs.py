"""Upload and job lifecycle tests."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

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
    assert "No candidate clips" in completed["stage_message"]
    assert completed["completed_at"] is not None
    assert completed["has_transcript"] is True
    assert completed["transcript_language"] == "en"
    assert completed["transcript_segment_count"] == 2
    assert completed["has_speech"] is True
    assert completed["clip_count"] == 0
    assert completed["clip_selection_model"] == "stub-selector"

    transcript_path = settings.work_dir / job_id / "transcript.json"
    assert transcript_path.is_file()
    assert not (settings.work_dir / job_id / "audio.wav").exists()

    transcript_response = client.get(f"/api/jobs/{job_id}/transcript")
    assert transcript_response.status_code == 200
    transcript = transcript_response.json()
    assert transcript["language"] == "en"
    assert transcript["model"] == "stub"
    assert transcript["has_speech"] is True
    assert len(transcript["segments"]) == 2
    for segment in transcript["segments"]:
        assert 0 <= segment["start"] < segment["end"] <= completed["duration_seconds"]
        for word in segment["words"]:
            assert segment["start"] <= word["start"] < word["end"] <= segment["end"]


def test_worker_marks_no_speech_transcript_completed(
    no_speech_client, sample_video
):
    response = _upload(no_speech_client, sample_video)
    assert response.status_code == 202
    job_id = response.json()["id"]

    worker = no_speech_client.app.state.worker
    assert worker.run_once() is True

    detail = no_speech_client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["state"] == "completed"
    assert payload["progress"] == 100
    assert payload["has_transcript"] is True
    assert payload["has_speech"] is False
    assert payload["transcript_segment_count"] == 0
    assert payload["clip_count"] == 0
    assert "No useful speech" in payload["stage_message"]

    transcript = no_speech_client.get(f"/api/jobs/{job_id}/transcript")
    assert transcript.status_code == 200
    body = transcript.json()
    assert body["has_speech"] is False
    assert body["segments"] == []
    assert body["language"] is None


def test_worker_skips_transcription_without_audio_stream(client, video_without_audio):
    response = _upload(client, video_without_audio)
    assert response.status_code == 202
    job_id = response.json()["id"]

    worker = client.app.state.worker
    assert worker.run_once() is True

    detail = client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["state"] == "completed"
    assert payload["progress"] == 100
    assert payload["has_audio"] is False
    assert payload["audio_codec"] is None
    assert payload["has_transcript"] is True
    assert payload["has_speech"] is False
    assert payload["transcript_language"] is None
    assert payload["transcript_segment_count"] == 0
    assert payload["clip_count"] == 0

    transcript = client.get(f"/api/jobs/{job_id}/transcript")
    assert transcript.status_code == 200
    body = transcript.json()
    assert body["has_speech"] is False
    assert body["segments"] == []
    assert body["language"] is None


def test_worker_marks_transcription_failure(failing_client, sample_video):
    response = _upload(failing_client, sample_video)
    assert response.status_code == 202
    job_id = response.json()["id"]

    worker = failing_client.app.state.worker
    assert worker.run_once() is True

    detail = failing_client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["state"] == "failed"
    assert payload["stage_message"] == "Transcription failed"
    assert payload["error"] == "Simulated transcription failure."
    assert payload["has_transcript"] is False

    missing = failing_client.get(f"/api/jobs/{job_id}/transcript")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "transcript_not_found"


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


def test_long_video_produces_candidate_clips(client, long_sample_video):
    response = _upload(client, long_sample_video)
    assert response.status_code == 202
    job_id = response.json()["id"]

    worker = client.app.state.worker
    assert worker.run_once() is True

    detail = client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["state"] == "completed"
    assert payload["clip_count"] >= 1
    assert payload["clip_selection_model"] == "stub-selector"
    assert "Clip selection complete" in payload["stage_message"]

    clips_response = client.get(f"/api/jobs/{job_id}/clips")
    assert clips_response.status_code == 200
    clips = clips_response.json()
    assert len(clips) == payload["clip_count"]

    clip = clips[0]
    assert clip["job_id"] == job_id
    assert 0 <= clip["start_seconds"] < clip["end_seconds"] <= payload["duration_seconds"]
    assert clip["duration_seconds"] == pytest.approx(
        clip["end_seconds"] - clip["start_seconds"], abs=0.01
    )
    assert 15 <= clip["duration_seconds"] <= 90
    assert clip["title"] == "Stub moment"
    assert clip["hook"]
    assert clip["reason"]
    assert clip["score"] is not None
    assert 0 <= clip["score"] <= 100
    assert {
        "hook",
        "clarity",
        "payoff",
        "emotion_or_interest",
        "conciseness",
        "weights",
        "method",
    } <= set(clip["component_scores"])
    assert clip["render_status"] == "pending"
    assert clip["speaker_tracking_status"] == "pending"

    metadata = client.get(f"/api/clips/{clip['id']}")
    assert metadata.status_code == 200
    assert metadata.json()["id"] == clip["id"]

    file_response = client.get(f"/api/clips/{clip['id']}/file")
    assert file_response.status_code == 404
    assert file_response.json()["detail"]["code"] == "clip_not_rendered"


def test_worker_marks_selection_failure(failing_selector_client, long_sample_video):
    response = _upload(failing_selector_client, long_sample_video)
    assert response.status_code == 202
    job_id = response.json()["id"]

    worker = failing_selector_client.app.state.worker
    assert worker.run_once() is True

    detail = failing_selector_client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["state"] == "failed"
    assert payload["stage_message"] == "Clip selection failed"
    assert payload["error"] == "Simulated clip selection failure."
    assert payload["has_transcript"] is True
    assert payload["clip_count"] == 0

    clips = failing_selector_client.get(f"/api/jobs/{job_id}/clips")
    assert clips.status_code == 200
    assert clips.json() == []


def test_unknown_clip_returns_404(client):
    response = client.get(f"/api/clips/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "clip_not_found"
