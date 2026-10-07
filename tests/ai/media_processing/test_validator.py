"""
tests/ai/media_processing/test_validator.py
============================================
Tests for deep ffprobe output validation and media stream sanity (S28-M06).
"""

from pathlib import Path
import pytest

from ai.media_processing.errors import OutputValidationError
from ai.media_processing.validator import (
    run_ffprobe_json,
    validate_audio_output,
    validate_concat_output,
    validate_extracted_frames,
    validate_file_sanity,
    validate_video_transcode,
    validate_video_trim,
)


def test_validate_file_sanity_empty(tmp_path: Path):
    empty_file = tmp_path / "zero.mp4"
    empty_file.touch()

    with pytest.raises(OutputValidationError, match="suspiciously small"):
        validate_file_sanity(empty_file, min_bytes=100)


def test_validate_file_sanity_missing(tmp_path: Path):
    missing_file = tmp_path / "ghost.mp4"
    with pytest.raises(OutputValidationError, match="not created"):
        validate_file_sanity(missing_file)


@pytest.mark.asyncio
async def test_run_ffprobe_json_real_file(test_fixtures_dir: Path):
    sample_video = test_fixtures_dir / "sample_video.mp4"

    meta = await run_ffprobe_json(sample_video)
    assert "streams" in meta
    assert "format" in meta

    video_streams = [s for s in meta["streams"] if s.get("codec_type") == "video"]
    assert len(video_streams) == 1
    assert video_streams[0]["width"] == 640
    assert video_streams[0]["height"] == 360
    assert video_streams[0]["codec_name"] == "h264"


@pytest.mark.asyncio
async def test_validate_video_transcode(test_fixtures_dir: Path):
    sample_video = test_fixtures_dir / "sample_video.mp4"

    meta = await validate_video_transcode(
        output_path=sample_video,
        expected_width=640,
        expected_height=360,
    )
    assert meta["width"] == 640
    assert meta["height"] == 360


@pytest.mark.asyncio
async def test_validate_video_duration_deviation(test_fixtures_dir: Path):
    sample_video = test_fixtures_dir / "sample_video.mp4"

    # Expecting 10s video when video is 3s
    with pytest.raises(OutputValidationError, match="deviates from expected"):
        await validate_video_trim(
            output_path=sample_video,
            expected_duration=10.0,
            tolerance_seconds=0.5,
        )


@pytest.mark.asyncio
async def test_validate_audio_output(test_fixtures_dir: Path):
    sample_audio = test_fixtures_dir / "sample_audio.wav"

    meta = await validate_audio_output(
        output_path=sample_audio,
        min_duration=0.5,
    )
    assert meta["sample_rate"] == 48000
    assert meta["channels"] == 1


@pytest.mark.asyncio
async def test_validate_extracted_frames(test_fixtures_dir: Path, tmp_path: Path):
    # Extract 2 real frames using ffmpeg
    sample_video = test_fixtures_dir / "sample_video.mp4"
    f1 = tmp_path / "f1.png"
    f2 = tmp_path / "f2.png"

    import subprocess
    subprocess.run(["ffmpeg", "-y", "-i", str(sample_video), "-vframes", "1", str(f1)], check=True)
    subprocess.run(["ffmpeg", "-y", "-i", str(sample_video), "-ss", "1.0", "-vframes", "1", str(f2)], check=True)

    frames = await validate_extracted_frames(
        frame_paths=[f1, f2],
        expected_min_count=2,
    )
    assert len(frames) == 2
    assert frames[0]["width"] == 640
    assert frames[0]["height"] == 360
