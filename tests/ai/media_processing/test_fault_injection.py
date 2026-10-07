"""
tests/ai/media_processing/test_fault_injection.py
==================================================
Fault injection and resiliency tests for S28-M06 MediaProcessing subsystem.
Validates fail-closed behavior, error mapping, and workspace cleanup on failure.
"""

from unittest.mock import MagicMock
from pathlib import Path
import pytest

from ai.media_processing.contracts import TranscodeVideoRequest, TrimVideoRequest
from ai.media_processing.errors import (
    InvalidMediaFileError,
    MediaProcessingError,
    MediaSourceNotFoundError,
    ProcessExecutionFailedError,
    StoragePublishFailedError,
)
from ai.media_processing.service import MediaProcessingService
from scripts.core.storage.storage_service import StorageService


@pytest.mark.asyncio
async def test_missing_source_asset_fails_closed(
    media_service: MediaProcessingService,
):
    req = TrimVideoRequest(
        project_id="prj_test_m06",
        source_storage_key="video/does_not_exist.mp4",
        start_time_seconds=0.0,
        duration_seconds=2.0,
    )
    with pytest.raises(MediaSourceNotFoundError, match="not found in project storage"):
        await media_service.trim_video(req)


@pytest.mark.asyncio
async def test_corrupt_media_input_fails_closed(
    media_service: MediaProcessingService,
    storage_service: StorageService,
):
    from scripts.core.storage.storage_service import build_storage_key
    corrupt_key = build_storage_key("ws_default", "prj_test_m06", "video", "corrupt_1", "corrupt.mp4")
    storage_service.put(corrupt_key, b"not_a_valid_video_header_data")

    req = TranscodeVideoRequest(
        project_id="prj_test_m06",
        source_storage_key=corrupt_key,
        target_container="mp4",
        video_codec="libx264",
    )
    with pytest.raises((ProcessExecutionFailedError, InvalidMediaFileError)):
        await media_service.transcode_video(req)

    # Workspace directory must be cleaned up even on failure
    subdirs = list(media_service.base_scratch_dir.glob("job_*"))
    assert len(subdirs) == 0


@pytest.mark.asyncio
async def test_storage_publish_failure_fails_closed(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    # Mock storage_service.put to raise an error
    storage_service.put = MagicMock(side_effect=IOError("Disk quota exceeded"))

    req = TrimVideoRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        start_time_seconds=0.0,
        duration_seconds=1.0,
    )

    with pytest.raises(StoragePublishFailedError, match="Failed to publish output artifact"):
        await media_service.trim_video(req)

    # Cleanup must occur
    subdirs = list(media_service.base_scratch_dir.glob("job_*"))
    assert len(subdirs) == 0
