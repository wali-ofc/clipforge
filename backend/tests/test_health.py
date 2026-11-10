"""Health endpoint tests."""

from __future__ import annotations


def test_health_responds_with_dependency_checks(client):
    response = client.get("/api/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert payload["app"] == "ClipForge"
    assert set(payload["checks"]) == {
        "database",
        "ffmpeg",
        "ffprobe",
        "whisper",
        "ollama",
        "face_detection",
    }
    assert payload["checks"]["database"]["available"] is True
    assert payload["checks"]["whisper"]["available"] is True
    assert "faster-whisper" in (payload["checks"]["whisper"]["version"] or "")
    assert payload["checks"]["ollama"]["available"] is False
    assert payload["limits"]["max_upload_bytes"] > 0
    assert payload["limits"]["allowed_formats"] == [".mp4", ".mov", ".mkv"]


def test_root_points_to_health_and_docs(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/api/health"
    assert response.json()["docs"] == "/docs"
