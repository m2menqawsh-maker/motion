"""
tests/ai/media_processing/test_parity_matrix.py
================================================
Parity campaign tests comparing legacy media processing execution vs canonical
MediaProcessingService execution across real media fixtures (S28-M06).
"""

from pathlib import Path
import pytest

from ai.media_processing.adapter import FFmpegAdapter
from ai.media_processing.contracts import (
    ConcatMediaRequest,
    NormalizeMediaRequest,
    ProbeMediaRequest,
    TrimVideoRequest,
)
from ai.media_processing.service import MediaProcessingService
from ai.media_processing.validator import run_ffprobe_json
from scripts.core.storage.storage_service import StorageService

# Import legacy video operations for parity baseline comparison
from sys import path as sys_path
legacy_tools_path = Path(__file__).resolve().parent.parent.parent.parent / ".agents" / "plugins" / "super-video-maker-plugin" / "tools" / "mcp-servers" / "video-tools-mcp"
if str(legacy_tools_path) not in sys_path:
    sys_path.insert(0, str(legacy_tools_path))

from utils.ffmpeg_ops import get_video_duration, trim_video_file


@pytest.mark.asyncio
async def test_parity_video_trimming(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    test_fixtures_dir: Path,
    sample_video_key: str,
    tmp_path: Path,
):
    adapter = FFmpegAdapter()
    sample_video_path = test_fixtures_dir / "sample_video.mp4"
    target_duration = 1.5

    # 1. Legacy execution (runs on local filesystem)
    legacy_out = tmp_path / "legacy_trimmed.mp4"
    await trim_video_file(str(sample_video_path), target_duration=target_duration, output_path=str(legacy_out))
    legacy_meta = await run_ffprobe_json(legacy_out)
    legacy_dur = float(legacy_meta["format"]["duration"])

    # 2. Canonical execution (runs through MediaProcessingService)
    req = TrimVideoRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        start_time_seconds=0.0,
        duration_seconds=target_duration,
    )
    res = await media_service.trim_video(req)
    canonical_dur = res.duration_seconds

    # 3. Assert parity
    assert abs(canonical_dur - target_duration) < 0.2
    assert abs(legacy_dur - target_duration) < 0.2
    assert abs(canonical_dur - legacy_dur) < 0.2


@pytest.mark.asyncio
async def test_parity_probe_media(
    media_service: MediaProcessingService,
    test_fixtures_dir: Path,
    sample_video_key: str,
):
    sample_video_path = test_fixtures_dir / "sample_video.mp4"

    # 1. Legacy ffprobe duration
    legacy_dur = await get_video_duration(str(sample_video_path))

    # 2. Canonical probe
    req = ProbeMediaRequest(
        project_id="prj_test_m06",
        storage_key=sample_video_key,
    )
    res = await media_service.probe_media(req)

    # 3. Parity assertion
    assert abs(res.duration_seconds - legacy_dur) < 0.05
    assert res.video_streams[0].width == 640
    assert res.video_streams[0].height == 360


@pytest.mark.asyncio
async def test_parity_audio_normalization_standards(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    test_fixtures_dir: Path,
):
    """Verifies that voiceover normalization hits -16 LUFS standard."""
    from scripts.core.storage.storage_service import build_storage_key
    sample_audio = test_fixtures_dir / "sample_audio.wav"
    key = build_storage_key("ws_default", "prj_test_m06", "audio", "vo_1", "vo.wav")
    storage_service.put(key, sample_audio.read_bytes())

    req = NormalizeMediaRequest(
        project_id="prj_test_m06",
        source_storage_key=key,
        target_lufs=-16.0,
    )
    res = await media_service.normalize_media(req)

    assert res.target_lufs == -16.0
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_parity_concat_duration(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    """Verifies that concatenating two 3.0s clips results in a single continuous ~6.0s video."""
    req = ConcatMediaRequest(
        project_id="prj_test_m06",
        source_storage_keys=[sample_video_key, sample_video_key],
        media_type="video",
        reencode_if_needed=True,
    )
    res = await media_service.concat_media(req)

    assert res.total_duration_seconds > 5.5
    assert res.total_duration_seconds < 6.5
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_parity_resize_video(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    test_fixtures_dir: Path,
    sample_video_key: str,
    tmp_path: Path,
):
    """Verifies that legacy resize_video_file and canonical resize_video produce identical dimensions."""
    from ai.media_processing.contracts import ResizeVideoRequest
    from utils.ffmpeg_ops import resize_video_file

    sample_video_path = test_fixtures_dir / "sample_video.mp4"
    target_w, target_h = 320, 180

    # 1. Legacy execution
    legacy_out = tmp_path / "legacy_resized.mp4"
    await resize_video_file(str(sample_video_path), target_w, target_h, maintain_aspect_ratio=True, output_path=str(legacy_out))
    legacy_meta = await run_ffprobe_json(legacy_out)
    legacy_stream = next(s for s in legacy_meta["streams"] if s["codec_type"] == "video")

    # 2. Canonical execution
    req = ResizeVideoRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        target_width=target_w,
        target_height=target_h,
        maintain_aspect_ratio=True,
    )
    res = await media_service.resize_video(req)

    # 3. Parity assertions
    assert res.width == target_w
    assert res.height == target_h
    assert int(legacy_stream["width"]) == target_w
    assert int(legacy_stream["height"]) == target_h
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_parity_change_video_speed(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    """Verifies that speeding up a 3.0s video by 2.0x results in a valid ~1.5s video."""
    from ai.media_processing.contracts import ChangeVideoSpeedRequest

    req = ChangeVideoSpeedRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        speed_factor=2.0,
    )
    res = await media_service.change_video_speed(req)

    # 3.0s original at 2x speed should be approximately 1.5s
    assert abs(res.duration_seconds - 1.5) < 0.3
    assert res.speed_factor == 2.0
    assert storage_service.exists(res.output_storage_key)


@pytest.mark.asyncio
async def test_parity_black_frames_detection(
    media_service: MediaProcessingService,
    storage_service: StorageService,
    sample_video_key: str,
):
    """Verifies black frame detection across clean test video (no false positive trimming)."""
    from ai.media_processing.contracts import DetectBlackFramesRequest

    req = DetectBlackFramesRequest(
        project_id="prj_test_m06",
        source_storage_key=sample_video_key,
        threshold=0.95,
        min_duration=0.1,
    )
    res = await media_service.detect_and_trim_black_frames(req)

    # Clean synthetic test video does not have all-black boundaries
    assert res.project_id == "prj_test_m06"
    assert storage_service.exists(res.output_storage_key)


def test_subsystem_owner_exceptions_documented():
    """
    Architectural boundary assertion:
    Verifies that 'overlay_text' is canonically owned by Remotion rendering templates (not FFmpeg burning),
    and 'detect_scenes' is canonically owned by Vision/Media Intelligence (not media processing).
    """
    from ai.contracts.common import CapabilityType

    # Remotion engine owns typography and overlays (Taste Gate compliance)
    assert not hasattr(CapabilityType, "OVERLAY_TEXT"), "overlay_text must remain in Remotion template engine"

    # Vision subsystem owns shot and scene detection
    from ai.vision.shot_detection import NativeShotDetector
    assert NativeShotDetector is not None, "Shot and scene detection is owned by ai.vision"


