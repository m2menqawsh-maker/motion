"""
tests/ai/media_processing/conftest.py
======================================
Fixtures for S28-M06 MediaProcessingService tests.
Provides isolated storage services, project fixtures, and deterministic media files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Generator
import pytest

from ai.media_processing.adapter import FFmpegAdapter
from ai.media_processing.service import MediaProcessingService
from ai.media_processing.staging import WorkerStagingContext
from scripts.core.storage.storage_service import StorageService, get_storage_service


@pytest.fixture(scope="session")
def test_fixtures_dir(tmp_path_factory) -> Path:
    """Generates deterministic video and audio test fixtures for the session."""
    fix_dir = tmp_path_factory.mktemp("media_fixtures")
    video_path = fix_dir / "sample_video.mp4"
    audio_path = fix_dir / "sample_audio.wav"

    # 1. Generate 3-second 640x360 h264/aac video
    cmd_vid = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=640x360:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        str(video_path),
    ]
    subprocess.run(cmd_vid, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 2. Generate 3-second 48kHz stereo sine wave audio
    cmd_aud = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=3:sample_rate=48000",
        str(audio_path),
    ]
    subprocess.run(cmd_aud, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return fix_dir


from scripts.core.storage.storage_service import (
    LocalStorageBackend,
    StorageService,
    build_storage_key,
)


@pytest.fixture
def storage_service(tmp_path) -> StorageService:
    """Provides a fresh StorageService rooted in a temporary directory."""
    return LocalStorageBackend(root_dir=tmp_path / "storage")


@pytest.fixture
def sample_video_key(storage_service: StorageService, test_fixtures_dir: Path) -> str:
    """Uploads sample_video.mp4 to storage and returns its storage key."""
    vid_data = (test_fixtures_dir / "sample_video.mp4").read_bytes()
    key = build_storage_key("ws_default", "prj_test_m06", "video", "sample_1", "sample.mp4")
    storage_service.put(key, vid_data)
    return key


@pytest.fixture
def sample_audio_key(storage_service: StorageService, test_fixtures_dir: Path) -> str:
    """Uploads sample_audio.wav to storage and returns its storage key."""
    aud_data = (test_fixtures_dir / "sample_audio.wav").read_bytes()
    key = build_storage_key("ws_default", "prj_test_m06", "audio", "sample_1", "sample.wav")
    storage_service.put(key, aud_data)
    return key


@pytest.fixture
def media_service(storage_service: StorageService, tmp_path: Path) -> MediaProcessingService:
    """Initializes MediaProcessingService with isolated storage and scratch dir."""
    adapter = FFmpegAdapter()
    return MediaProcessingService(
        storage_service=storage_service,
        adapter=adapter,
        base_scratch_dir=tmp_path / "worker_scratch",
    )
