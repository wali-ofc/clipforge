"""Unit and integration tests for Phase 5 clip rendering."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.rendering as rendering_module
from app.config import Settings
from app.services.media_probe import MediaInfo, probe_media
from app.services.rendering import (
    FFmpegClipRenderer,
    RenderingError,
    _verify_output,
    build_crop_commands_file,
    format_sendcmd_path,
)
from app.utils.subprocesses import CommandError, command_exists


def _media_info(settings: Settings, **overrides) -> MediaInfo:
    values = {
        "duration_seconds": 2.0,
        "width": settings.output_width,
        "height": settings.output_height,
        "rotation": 0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "has_audio": True,
        "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
        "frame_rate": float(settings.output_fps),
    }
    values.update(overrides)
    return MediaInfo(**values)


def _require_ffmpeg(settings: Settings) -> None:
    if not command_exists(settings.ffmpeg_bin) or not command_exists(
        settings.ffprobe_bin
    ):
        pytest.skip("ffmpeg or ffprobe is not available")


def test_format_sendcmd_path():
    path = Path("D:/py/clipforge/data/work/commands.txt")
    formatted = format_sendcmd_path(path)
    assert "\\:" in formatted
    assert "\\" not in formatted.replace("\\:", "")


def test_build_crop_commands_file(tmp_path: Path):
    cmd_file = tmp_path / "commands.txt"
    crop_plan = {
        "version": 1,
        "samples": [
            {"time": 0.0, "x": 640.0, "y": 360.0, "crop_width": 405.0, "crop_height": 720.0},
            {"time": 2.0, "x": 800.0, "y": 360.0, "crop_width": 405.0, "crop_height": 720.0},
        ],
    }
    count = build_crop_commands_file(
        crop_plan,
        duration_seconds=2.0,
        source_width=1280,
        source_height=720,
        crop_w=404,
        crop_h=720,
        command_file_path=cmd_file,
        step_interval=0.1,
    )
    assert count > 0
    assert cmd_file.is_file()
    lines = cmd_file.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].startswith("0.000 [enter] crop x")
    for line in lines:
        assert "[enter] crop x" in line
        assert "crop y" in line
        parts = line.split("crop x ")[1].split(",")
        x_val = int(parts[0])
        y_val = int(parts[1].split("crop y ")[1].rstrip(";"))
        assert x_val % 2 == 0
        assert y_val % 2 == 0
        assert 0 <= x_val <= 1280 - 404
        assert 0 <= y_val <= 720 - 720


def test_build_crop_commands_centers_without_plan(tmp_path: Path):
    cmd_file = tmp_path / "centered.txt"
    count = build_crop_commands_file(
        {},
        duration_seconds=1.0,
        source_width=1280,
        source_height=720,
        crop_w=404,
        crop_h=720,
        command_file_path=cmd_file,
        step_interval=0.1,
    )
    # All commands are identical, so only the first is written.
    assert count == 1
    assert cmd_file.read_text(encoding="utf-8").startswith("0.000 [enter] crop x 438")


def test_build_crop_commands_handles_malformed_plan(tmp_path: Path):
    cmd_file = tmp_path / "malformed.txt"
    count = build_crop_commands_file(
        {"samples": []},
        duration_seconds=1.0,
        source_width=1280,
        source_height=720,
        crop_w=404,
        crop_h=720,
        command_file_path=cmd_file,
        step_interval=0.1,
    )
    assert count == 1
    assert cmd_file.read_text(encoding="utf-8").startswith(
        "0.000 [enter] crop x 438"
    )


def test_build_crop_commands_clamps_and_dedupes(tmp_path: Path):
    cmd_file = tmp_path / "clamped.txt"
    crop_plan = {
        "samples": [
            {"time": 0.0, "x": -500.0, "y": -500.0},
            {"time": 1.0, "x": 5000.0, "y": 5000.0},
        ]
    }
    count = build_crop_commands_file(
        crop_plan,
        duration_seconds=1.0,
        source_width=640,
        source_height=360,
        crop_w=200,
        crop_h=360,
        command_file_path=cmd_file,
        step_interval=0.25,
    )
    assert count >= 2
    lines = cmd_file.read_text(encoding="utf-8").strip().splitlines()
    for line in lines:
        x_val = int(line.split("crop x ")[1].split(",")[0])
        y_val = int(line.split("crop y ")[1].rstrip(";"))
        assert 0 <= x_val <= 440
        assert y_val == 0


def test_renderer_missing_source(settings: Settings, tmp_path: Path):
    renderer = FFmpegClipRenderer(settings)
    clip = SimpleNamespace(
        id="test-clip",
        start_seconds=0.0,
        end_seconds=5.0,
        duration_seconds=5.0,
        crop_plan={},
    )
    with pytest.raises(RenderingError) as exc_info:
        renderer.render_clip(
            source_path=tmp_path / "nonexistent.mp4",
            clip=clip,
            output_path=tmp_path / "out.mp4",
            settings=settings,
            work_dir=tmp_path / "work",
        )
    assert exc_info.value.code == "source_missing"


def test_verify_output_accepts_valid_metadata(settings: Settings, tmp_path: Path, monkeypatch):
    output = tmp_path / "clip.mp4"
    output.write_bytes(b"\x00" * 64)
    monkeypatch.setattr(
        rendering_module, "probe_media", lambda path, cfg: _media_info(settings)
    )
    info = _verify_output(
        output, settings, expected_duration=2.0, expect_audio=True
    )
    assert info.width == settings.output_width
    assert info.video_codec == "h264"


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"width": 720, "height": 1280}, "invalid_output_dimensions"),
        ({"video_codec": "hevc"}, "invalid_video_codec"),
        ({"container_format": "matroska,webm"}, "invalid_container"),
        ({"has_audio": False, "audio_codec": None}, "missing_output_audio"),
        ({"audio_codec": "mp3"}, "missing_output_audio"),
        ({"duration_seconds": 12.0}, "invalid_output_duration"),
        ({"frame_rate": 60.0}, "invalid_output_frame_rate"),
    ],
)
def test_verify_output_rejects_bad_metadata(
    settings: Settings, tmp_path: Path, monkeypatch, overrides, code
):
    output = tmp_path / "clip.mp4"
    output.write_bytes(b"\x00" * 64)
    monkeypatch.setattr(
        rendering_module,
        "probe_media",
        lambda path, cfg: _media_info(settings, **overrides),
    )
    with pytest.raises(RenderingError) as exc_info:
        _verify_output(
            output, settings, expected_duration=2.0, expect_audio=True
        )
    assert exc_info.value.code == code


def test_verify_output_rejects_unexpected_audio(settings: Settings, tmp_path: Path, monkeypatch):
    output = tmp_path / "clip.mp4"
    output.write_bytes(b"\x00" * 64)
    monkeypatch.setattr(
        rendering_module, "probe_media", lambda path, cfg: _media_info(settings)
    )
    with pytest.raises(RenderingError) as exc_info:
        _verify_output(
            output, settings, expected_duration=2.0, expect_audio=False
        )
    assert exc_info.value.code == "unexpected_output_audio"


def test_verify_output_rejects_empty_file(settings: Settings, tmp_path: Path):
    output = tmp_path / "clip.mp4"
    output.write_bytes(b"")
    with pytest.raises(RenderingError) as exc_info:
        _verify_output(
            output, settings, expected_duration=2.0, expect_audio=True
        )
    assert exc_info.value.code == "rendered_file_empty"


def test_renderer_removes_partial_output_on_ffmpeg_failure(
    settings: Settings, tmp_path: Path, monkeypatch
):
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"not a real video")
    output_path = tmp_path / "partial.mp4"

    def fake_run(args, *, timeout, cwd=None, cancel_check=None):
        output_path.write_bytes(b"partial output")
        raise CommandError(args, 1, "simulated ffmpeg failure")

    monkeypatch.setattr(rendering_module, "run_command", fake_run)

    renderer = FFmpegClipRenderer(settings)
    clip = SimpleNamespace(
        id="clip-failure",
        start_seconds=0.0,
        end_seconds=2.0,
        duration_seconds=2.0,
        crop_plan={},
    )

    with pytest.raises(RenderingError) as exc_info:
        renderer.render_clip(
            source_path=source_path,
            clip=clip,
            output_path=output_path,
            settings=settings,
            work_dir=tmp_path / "work",
            has_audio=False,
            source_width=640,
            source_height=360,
        )

    assert exc_info.value.code == "rendering_failed"
    assert not output_path.exists()
    assert not (
        tmp_path / "work" / "render" / "clip-failure_commands.txt"
    ).exists()


def test_ffmpeg_clip_renderer_integration(settings: Settings, tmp_path: Path):
    _require_ffmpeg(settings)

    source_path = tmp_path / "source.mp4"
    cmd = [
        settings.ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=640x360:rate=25:duration=3",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=3",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        str(source_path),
    ]
    subprocess.run(cmd, check=True)

    renderer = FFmpegClipRenderer(settings)
    clip = SimpleNamespace(
        id="clip-integration-test",
        start_seconds=0.5,
        end_seconds=2.5,
        duration_seconds=2.0,
        crop_plan={
            "version": 1,
            "samples": [
                {"time": 0.0, "x": 320.0, "y": 180.0, "crop_width": 202.0, "crop_height": 360.0},
                {"time": 2.0, "x": 400.0, "y": 180.0, "crop_width": 202.0, "crop_height": 360.0},
            ],
        },
    )

    output_path = tmp_path / "output.mp4"
    work_dir = tmp_path / "work"

    result = renderer.render_clip(
        source_path=source_path,
        clip=clip,
        output_path=output_path,
        settings=settings,
        work_dir=work_dir,
        has_audio=True,
        source_width=640,
        source_height=360,
    )

    assert result.output_path.is_file()
    assert result.file_size_bytes > 0
    assert result.width == settings.output_width
    assert result.height == settings.output_height
    assert result.video_codec == "h264"
    assert result.audio_codec == "aac"
    assert result.frame_rate == pytest.approx(settings.output_fps, abs=0.5)
    assert not (work_dir / "render" / "clip-integration-test_commands.txt").exists()

    info = probe_media(output_path, settings)
    assert info.width == settings.output_width
    assert info.height == settings.output_height
    assert info.video_codec == "h264"
    assert info.has_audio is True
    assert info.audio_codec == "aac"
    assert "mp4" in info.container_format
    assert info.frame_rate == pytest.approx(settings.output_fps, abs=0.5)
    assert info.duration_seconds == pytest.approx(2.0, abs=0.4)


def test_ffmpeg_clip_renderer_without_audio(settings: Settings, tmp_path: Path):
    _require_ffmpeg(settings)

    source_path = tmp_path / "source_no_audio.mp4"
    cmd = [
        settings.ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=25:duration=2",
        "-c:v",
        "libx264",
        str(source_path),
    ]
    subprocess.run(cmd, check=True)

    renderer = FFmpegClipRenderer(settings)
    clip = SimpleNamespace(
        id="clip-no-audio",
        start_seconds=0.0,
        end_seconds=1.5,
        duration_seconds=1.5,
        crop_plan={},
    )

    output_path = tmp_path / "output_no_audio.mp4"
    work_dir = tmp_path / "work"

    result = renderer.render_clip(
        source_path=source_path,
        clip=clip,
        output_path=output_path,
        settings=settings,
        work_dir=work_dir,
        has_audio=False,
        source_width=320,
        source_height=240,
    )

    assert result.output_path.is_file()
    info = probe_media(output_path, settings)
    assert info.has_audio is False
    assert info.width == settings.output_width
    assert info.height == settings.output_height


def test_dynamic_crop_follows_plan(settings: Settings, tmp_path: Path):
    """The rendered crop must actually move, not stay at the first position."""
    _require_ffmpeg(settings)
    cv2 = pytest.importorskip("cv2")

    source_path = tmp_path / "two_color.mp4"
    cmd = [
        settings.ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=red:size=320x240:rate=25:duration=2",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:size=320x240:rate=25:duration=2",
        "-filter_complex",
        "[0:v][1:v]hstack=inputs=2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(source_path),
    ]
    subprocess.run(cmd, check=True)

    renderer = FFmpegClipRenderer(settings)
    clip = SimpleNamespace(
        id="clip-dynamic-crop",
        start_seconds=0.0,
        end_seconds=2.0,
        duration_seconds=2.0,
        crop_plan={
            "samples": [
                {"time": 0.0, "x": 100.0, "y": 120.0},
                {"time": 1.5, "x": 540.0, "y": 120.0},
            ]
        },
    )

    output_path = tmp_path / "dynamic.mp4"
    renderer.render_clip(
        source_path=source_path,
        clip=clip,
        output_path=output_path,
        settings=settings,
        work_dir=tmp_path / "work",
        has_audio=False,
        source_width=640,
        source_height=240,
    )

    capture = cv2.VideoCapture(str(output_path))
    frames: list = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()

    assert len(frames) > 10
    first_blue, _, first_red = frames[0].reshape(-1, 3).mean(axis=0)
    last_blue, _, last_red = frames[-1].reshape(-1, 3).mean(axis=0)

    assert first_red > 150 and first_blue < 100
    assert last_blue > 150 and last_red < 100
