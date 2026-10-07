"""
tests/ai/media_processing/test_service.py
==========================================
End-to-End tests for MediaProcessingService (S28-M06).
Validates staging isolation, FFmpeg execution, deep validation, and canonical StorageService publishing.
"""

from pathlib import Path
import pytest

from ai.media_processing.contracts import (
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
from ai.media_processing.service import MediaProcessingService
from scripts.core.storage.storage_service import StorageService


@pytest.mark.asyncio
async def test_probe_media(media_service: MediaProcessingService, sample_video_key: str):
    req = ProbeMediaRequest(
        project_id="prj_test_m06",
        storage_key=sample_video_key,
    )
    res = await media_service.probe_media(req)

    assert res.project_id == "prj_test_m06"
    assert res.container is not None
    assert res.duration_seconds > 0.0
    assert len(res.video_streams) == 1
    assert res.video_streams[0].width == 640
    assert res.video_streams[0].height == 360
    assert len(res.audio_streams) == 1


@pytest.mark.asyncio
async def test_transcode_video(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    req = TranscodeVideoRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        target_container="mp4",
        video_codec="libx264",
        preset="ultrafast",
        crf=26,
    )
    res = await media_service.transcode_video(req)

    assert res.project_id == "prj_test_m06"
    assert res.duration_seconds > 0.0

    # Verify published to StorageService
    assert storage_service.exists(res.output_storage_key)
    data = storage_service.get(res.output_storage_key)
    assert len(data) > 0


@pytest.mark.asyncio
async def test_trim_video(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    req = TrimVideoRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        start_time_seconds=0.5,
        duration_seconds=1.5,
    )
    res = await media_service.trim_video(req)

    assert res.project_id == "prj_test_m06"
    assert storage_service.exists(res.output_storage_key)
    assert abs(res.duration_seconds - 1.5) < 0.2


@pytest.mark.asyncio
async def test_extract_audio(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    req = ExtractAudioRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        audio_format="wav",
        sample_rate=48000,
        channels=2,
    )
    res = await media_service.extract_audio(req)

    assert res.project_id == "prj_test_m06"
    assert res.sample_rate == 48000
    assert res.channels == 2
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_extract_frames(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    req = ExtractFramesRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        fps=1.0,
        image_format="png",
    )
    res = await media_service.extract_frames(req)

    assert res.project_id == "prj_test_m06"
    assert res.total_frames >= 2
    assert len(res.frames) == res.total_frames

    # Check each frame key exists in StorageService
    for f in res.frames:
        assert storage_service.exists(f.storage_key)


@pytest.mark.asyncio
async def test_concat_media(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    req = ConcatMediaRequest(
        project_id="prj_test_m06",
        source_storage_keys=[sample_video_key, sample_video_key],
        media_type="video",
        reencode_if_needed=True,
    )
    res = await media_service.concat_media(req)

    assert res.project_id == "prj_test_m06"
    assert storage_service.exists(res.output_storage_key)
    # 3s + 3s = 6s approximately
    assert res.total_duration_seconds > 5.5


@pytest.mark.asyncio
async def test_change_container(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    req = ChangeContainerRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        target_container="mkv",
    )
    res = await media_service.change_container(req)

    assert res.container == "mkv"
    assert res.output_storage_key.endswith(".mkv")
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_normalize_media(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_audio_key: str,
):
    req = NormalizeMediaRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_audio_key,
        target_lufs=-16.0,
    )
    res = await media_service.normalize_media(req)

    assert res.project_id == "prj_test_m06"
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_resize_video(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    req = ResizeVideoRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        target_width=320,
        target_height=180,
    )
    res = await media_service.resize_video(req)

    assert res.width == 320
    assert res.height == 180
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_change_video_speed(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    req = ChangeVideoSpeedRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        speed_factor=2.0,
    )
    res = await media_service.change_video_speed(req)

    # 3.0s / 2.0 = ~1.5s
    assert abs(res.duration_seconds - 1.5) < 0.3
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_staging_workspace_cleaned_up(
    media_service: MediaProcessingService,
    sample_video_key: str,
):
    scratch_dir = media_service.base_scratch_dir

    req = TrimVideoRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        start_time_seconds=0.0,
        duration_seconds=1.0,
    )
    await media_service.trim_video(req)

    # Check that any worker job subdirectory was removed
    subdirs = list(scratch_dir.glob("job_*"))
    assert len(subdirs) == 0, f"Worker staging directories leaked: {subdirs}"
