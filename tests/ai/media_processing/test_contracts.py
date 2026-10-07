"""
tests/ai/media_processing/test_contracts.py
============================================
Tests for strongly-typed media processing operation contracts (S28-M06).
Validates bounds, allowlists, required fields, and sanitization.
"""

import pytest
from pydantic import ValidationError

from ai.media_processing.contracts import (
    ALLOWED_AUDIO_CODECS,
    ALLOWED_AUDIO_FORMATS,
    ALLOWED_PRESETS,
    ALLOWED_VIDEO_CODECS,
    ALLOWED_VIDEO_CONTAINERS,
    ChangeContainerRequest,
    ChangeVideoSpeedRequest,
    ConcatMediaRequest,
    DetectBlackFramesRequest,
    EnforceKeyframesRequest,
    ExtendAudioRequest,
    ExtendVideoRequest,
    ExtractAudioRequest,
    ExtractFramesRequest,
    NormalizeMediaRequest,
    ProbeMediaRequest,
    ResizeVideoRequest,
    TranscodeVideoRequest,
    TrimAudioRequest,
    TrimSilenceRequest,
    TrimVideoRequest,
)


def test_probe_media_request_valid():
    req = ProbeMediaRequest(project_id="prj_1", storage_key="video/clip.mp4")
    assert req.project_id == "prj_1"
    assert req.storage_key == "video/clip.mp4"


def test_probe_media_request_empty_rejected():
    with pytest.raises(ValidationError):
        ProbeMediaRequest(project_id="", storage_key="")


def test_transcode_video_request_valid():
    req = TranscodeVideoRequest(
        project_id="prj_1",
        source_storage_key="video/raw.mov",
        target_container="mp4",
        video_codec="libx264",
        preset="fast",
        crf=23,
    )
    assert req.target_container == "mp4"
    assert req.video_codec == "libx264"


def test_transcode_video_request_invalid_codec_rejected():
    with pytest.raises(ValidationError, match="not in allowed codecs"):
        TranscodeVideoRequest(
            project_id="prj_1",
            source_storage_key="video/raw.mov",
            video_codec="malicious_codec_shell",
        )


def test_transcode_video_request_invalid_container_rejected():
    with pytest.raises(ValidationError, match="not in allowed containers"):
        TranscodeVideoRequest(
            project_id="prj_1",
            source_storage_key="video/raw.mov",
            target_container="exe",
        )



def test_transcode_video_request_crf_bounds():
    with pytest.raises(ValidationError):
        TranscodeVideoRequest(
            project_id="prj_1",
            source_storage_key="video/raw.mov",
            crf=60,  # Max is 51
        )
    with pytest.raises(ValidationError):
        TranscodeVideoRequest(
            project_id="prj_1",
            source_storage_key="video/raw.mov",
            crf=-1,
        )


def test_trim_video_request_valid_and_bounds():
    req = TrimVideoRequest(
        project_id="prj_1",
        source_storage_key="video/clip.mp4",
        start_time_seconds=1.5,
        duration_seconds=5.0,
    )
    assert req.start_time_seconds == 1.5
    assert req.duration_seconds == 5.0

    # Negative start time
    with pytest.raises(ValidationError):
        TrimVideoRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            start_time_seconds=-0.5,
        )

    # Zero or negative duration
    with pytest.raises(ValidationError):
        TrimVideoRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            duration_seconds=0.0,
        )


def test_extract_audio_request_allowlists():
    req = ExtractAudioRequest(
        project_id="prj_1",
        source_storage_key="video/clip.mp4",
        audio_format="wav",
        sample_rate=48000,
        channels=2,
    )
    assert req.audio_format == "wav"

    with pytest.raises(ValidationError, match="not in allowed formats"):
        ExtractAudioRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            audio_format="raw_sh",
        )

    with pytest.raises(ValidationError):
        ExtractAudioRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            channels=16,  # Valid channels are 1 to 8
        )


def test_extract_frames_request_bounds():
    req = ExtractFramesRequest(
        project_id="prj_1",
        source_storage_key="video/clip.mp4",
        fps=1.0,
        image_format="png",
    )
    assert req.fps == 1.0

    with pytest.raises(ValidationError):
        ExtractFramesRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            max_frames=200,  # Max frames is 100
        )

    with pytest.raises(ValidationError, match="not allowed"):
        ExtractFramesRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            image_format="gif",  # Only png, jpg, jpeg, webp
        )


def test_concat_media_request_validation():
    req = ConcatMediaRequest(
        project_id="prj_1",
        source_storage_keys=["video/part1.mp4", "video/part2.mp4"],
    )
    assert len(req.source_storage_keys) == 2

    # Needs at least 2 files
    with pytest.raises(ValidationError):
        ConcatMediaRequest(
            project_id="prj_1",
            source_storage_keys=["video/part1.mp4"],
        )


def test_resize_video_request_bounds():
    req = ResizeVideoRequest(
        project_id="prj_1",
        source_storage_key="video/clip.mp4",
        target_width=1920,
        target_height=1080,
    )
    assert req.target_width == 1920

    with pytest.raises(ValidationError):
        ResizeVideoRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            target_width=0,
            target_height=1080,
        )

    with pytest.raises(ValidationError):
        ResizeVideoRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            target_width=1920,
            target_height=-10,
        )


def test_speed_and_silence_requests():
    speed_req = ChangeVideoSpeedRequest(
        project_id="prj_1",
        source_storage_key="video/clip.mp4",
        speed_factor=1.5,
    )
    assert speed_req.speed_factor == 1.5

    with pytest.raises(ValidationError):
        ChangeVideoSpeedRequest(
            project_id="prj_1",
            source_storage_key="video/clip.mp4",
            speed_factor=0.0,  # Must be gt 0.0
        )

    silence_req = TrimSilenceRequest(
        project_id="prj_1",
        source_storage_key="audio/track.wav",
        threshold_db=-30.0,
    )
    assert silence_req.threshold_db == -30.0

    with pytest.raises(ValidationError):
        TrimSilenceRequest(
            project_id="prj_1",
            source_storage_key="audio/track.wav",
            threshold_db=10.0,  # Must be <= 0.0
        )


