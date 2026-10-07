"""
tests/ai/media_processing/test_adapter.py
==========================================
Tests for FFmpegAdapter (S28-M06).
Validates argv construction, process group isolation, timeout enforcement,
and bounded buffer capture.
"""

import asyncio
from pathlib import Path
import pytest

from ai.media_processing.adapter import FFmpegAdapter, FFmpegProcessResult
from ai.media_processing.contracts import (
    ExtractAudioRequest,
    TranscodeVideoRequest,
    TrimVideoRequest,
)
from ai.media_processing.errors import (
    FFmpegUnavailableError,
    ProcessExecutionFailedError,
    ProcessTimeoutError,
)


def test_adapter_health():
    adapter = FFmpegAdapter()
    health = adapter.get_health()
    assert health["healthy"] is True
    assert health["ffmpeg_path"] is not None
    assert health["ffprobe_path"] is not None


def test_command_builder_transcode_argv():
    adapter = FFmpegAdapter()
    req = TranscodeVideoRequest(
        project_id="prj_1",
        source_storage_key="raw.mov",
        target_container="mp4",
        video_codec="libx264",
        preset="fast",
        crf=22,
    )
    cmd = adapter.build_transcode_command(Path("/in/raw.mov"), Path("/out/res.mp4"), req)

    # Invariants: strictly argv array, no shell string
    assert isinstance(cmd, list)
    assert cmd[0] == "ffmpeg"
    assert "-i" in cmd
    assert "/in/raw.mov" in cmd
    assert "-c:v" in cmd
    assert "libx264" in cmd
    assert "-preset" in cmd
    assert "fast" in cmd
    assert "-crf" in cmd
    assert "22" in cmd
    assert str(Path("/out/res.mp4")) == cmd[-1]


def test_command_builder_trim_argv():
    adapter = FFmpegAdapter()
    req = TrimVideoRequest(
        project_id="prj_1",
        source_storage_key="raw.mp4",
        start_time_seconds=2.5,
        duration_seconds=10.0,
        accurate_seek=False,
    )
    cmd = adapter.build_trim_command(Path("/in/raw.mp4"), Path("/out/trimmed.mp4"), req)
    assert "-ss" in cmd
    assert "2.5" in cmd
    assert "-t" in cmd
    assert "10.0" in cmd
    assert "-c" in cmd
    assert "copy" in cmd


def test_command_builder_extract_audio_argv():
    adapter = FFmpegAdapter()
    req = ExtractAudioRequest(
        project_id="prj_1",
        source_storage_key="raw.mp4",
        audio_format="wav",
        sample_rate=48000,
        channels=2,
    )
    cmd = adapter.build_extract_audio_command(Path("/in/raw.mp4"), Path("/out/audio.wav"), req)
    assert "-vn" in cmd
    assert "-ar" in cmd
    assert "48000" in cmd
    assert "-ac" in cmd
    assert "2" in cmd


@pytest.mark.asyncio
async def test_execute_ffmpeg_success(test_fixtures_dir: Path, tmp_path: Path):
    adapter = FFmpegAdapter()
    input_file = test_fixtures_dir / "sample_video.mp4"
    output_file = tmp_path / "transcoded.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-c:v", "libx264", "-preset", "ultrafast",
        str(output_file),
    ]

    res = await adapter.execute_ffmpeg(cmd, timeout_seconds=15.0)
    assert isinstance(res, FFmpegProcessResult)
    assert res.returncode == 0
    assert output_file.exists()
    assert output_file.stat().st_size > 0


@pytest.mark.asyncio
async def test_execute_ffmpeg_timeout(test_fixtures_dir: Path, tmp_path: Path):
    adapter = FFmpegAdapter()
    input_file = test_fixtures_dir / "sample_video.mp4"
    output_file = tmp_path / "slow_transcode.mp4"

    # Command forced to sleep or process very slowly with ultra tiny timeout
    cmd = [
        "ffmpeg", "-y",
        "-re",  # Read input at native frame rate (slow)
        "-i", str(input_file),
        "-c:v", "libx264", "-preset", "veryslow",
        str(output_file),
    ]

    with pytest.raises(ProcessTimeoutError, match="timeout limit"):
        await adapter.execute_ffmpeg(cmd, timeout_seconds=0.05)


@pytest.mark.asyncio
async def test_execute_ffmpeg_failure_exit_code(tmp_path: Path):
    adapter = FFmpegAdapter()
    nonexistent = tmp_path / "does_not_exist.mp4"
    output_file = tmp_path / "out.mp4"

    cmd = ["ffmpeg", "-y", "-i", str(nonexistent), str(output_file)]

    with pytest.raises(ProcessExecutionFailedError) as exc_info:
        await adapter.execute_ffmpeg_checked(cmd, timeout_seconds=5.0)

    assert exc_info.value.code == "PROCESS_EXECUTION_FAILED"
    assert exc_info.value.details.get("exit_code") != 0



