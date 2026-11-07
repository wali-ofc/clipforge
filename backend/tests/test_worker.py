"""Worker queue, recovery, and progress tests."""

from __future__ import annotations

from sqlalchemy import select

from app.models.job import Job, JobState
from app.utils.time import utc_now
from app.worker.pipeline import apply_progress, claim_next_queued_job
from app.worker.runner import recover_interrupted_jobs


def _job(job_id: str, *, state: JobState, progress: int = 0) -> Job:
    return Job(
        id=job_id,
        original_filename="test.mp4",
        stored_path=f"uploads/{job_id}/source.mp4",
        content_type="video/mp4",
        size_bytes=10,
        state=state.value,
        progress=progress,
        stage_message="Test",
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def test_progress_never_moves_backwards():
    job = _job("job-progress", state=JobState.inspecting, progress=40)

    apply_progress(job, 10, "Older update")
    assert job.progress == 40

    apply_progress(job, 75, "Newer update")
    assert job.progress == 75
    assert job.stage_message == "Newer update"


def test_job_state_helpers():
    assert JobState.completed.is_terminal is True
    assert JobState.failed.is_terminal is True
    assert JobState.rendering.is_active is True
    assert JobState.queued.is_terminal is False
    assert JobState.queued.is_active is False


def test_claim_next_queued_job_marks_inspecting(client):
    settings = client.app.state.settings
    job_id = "11111111-1111-1111-1111-111111111111"
    with client.app.state.session_factory() as session:
        session.add(_job(job_id, state=JobState.queued))
        session.commit()

    with client.app.state.session_factory() as session:
        claimed = claim_next_queued_job(session)
        assert claimed is not None
        assert claimed.id == job_id
        assert claimed.state == JobState.inspecting.value
        assert claimed.progress >= 5
        assert claimed.started_at is not None

    with client.app.state.session_factory() as session:
        assert claim_next_queued_job(session) is None


def test_recover_interrupted_jobs_marks_active_jobs_failed(client):
    session_factory = client.app.state.session_factory
    interrupted_id = "22222222-2222-2222-2222-222222222222"
    queued_id = "33333333-3333-3333-3333-333333333333"

    with session_factory() as session:
        session.add(
            _job(interrupted_id, state=JobState.transcribing, progress=55)
        )
        session.add(_job(queued_id, state=JobState.queued, progress=0))
        session.commit()

    assert recover_interrupted_jobs(session_factory) == 1

    with session_factory() as session:
        interrupted = session.get(Job, interrupted_id)
        queued = session.get(Job, queued_id)
        assert interrupted is not None
        assert interrupted.state == JobState.failed.value
        assert interrupted.progress == 55
        assert "interrupted" in (interrupted.error or "").lower()
        assert interrupted.completed_at is not None

        assert queued is not None
        assert queued.state == JobState.queued.value

        states = session.execute(select(Job.state)).scalars().all()
        assert states.count(JobState.failed.value) == 1


def test_worker_returns_false_when_queue_is_empty(client):
    assert client.app.state.worker.run_once() is False
