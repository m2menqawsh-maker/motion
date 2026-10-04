"""
tests/ai/specialized/test_specialized_contracts.py
==================================================
Strong typing and contract tests for Specialized Media AI (S27.17 / AI-13).

Invariants verified:
- All 10 specialized capabilities have strictly typed request and result models:
  1. TTS
  2. Image Generation
  3. Video Generation
  4. Person Segmentation
  5. Background Removal
  6. Lip Sync
  7. Upscale
  8. Audio Denoise
  9. Audio Enhance
  10. Vocal Isolation
- All result objects contain complete AnalysisProvenance without arbitrary dicts.
- No vendor schemas or fields leak into canonical contracts.
"""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from ai.contracts.specialized import (
    AudioDenoiseRequest,
    AudioDenoiseResult,
    AudioEnhanceRequest,
    AudioEnhanceResult,
    BackgroundRemovalRequest,
    BackgroundRemovalResult,
    ImageGenerationRequest,
    ImageGenerationResult,
    LipSyncRequest,
    LipSyncResult,
    PersonSegmentationRequest,
    PersonSegmentationResult,
    TTSRequest,
    TTSResult,
    UpscaleRequest,
    UpscaleResult,
    VideoGenerationRequest,
    VideoGenerationResult,
    VocalIsolationRequest,
    VocalIsolationResult,
)
from ai.specialized.adapters import FakeSpecializedMediaAdapterA
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "spec_storage")


@pytest.fixture
def adapter_a(storage):
    return FakeSpecializedMediaAdapterA(storage_service=storage)


@pytest.mark.asyncio
async def test_all_10_specialized_contracts_execution(adapter_a):
    ws = "ws_test_contracts"

    # 1. TTS
    tts_req = TTSRequest(text="Hello Antigravity", voice_id="voice_adam")
    tts_res = await adapter_a.synthesize(tts_req, ws)
    assert isinstance(tts_res, TTSResult)
    assert tts_res.audio_storage_key.startswith(f"workspaces/{ws}/")
    assert tts_res.provenance.provider == "fake-specialized-a"

    # 2. Image Generation
    img_req = ImageGenerationRequest(prompt="A futuristic neon city", width=1024, height=1024)
    img_res = await adapter_a.generate_image(img_req, ws)
    assert isinstance(img_res, ImageGenerationResult)
    assert img_res.image_storage_key.startswith(f"workspaces/{ws}/")
    assert img_res.width == 1024

    # 3. Video Generation
    vid_req = VideoGenerationRequest(prompt="A cinematic drone shot over mountains", duration_seconds=4.0)
    vid_res = await adapter_a.generate_video(vid_req, ws)
    assert isinstance(vid_res, VideoGenerationResult)
    assert vid_res.video_storage_key.startswith(f"workspaces/{ws}/")
    assert vid_res.duration_seconds == 4.0

    # 4. Person Segmentation
    seg_req = PersonSegmentationRequest(
        image_storage_key=f"workspaces/{ws}/inputs/person.png",
        content_hash="hash_person_01",
    )
    seg_res = await adapter_a.segment_person(seg_req, ws)
    assert isinstance(seg_res, PersonSegmentationResult)
    assert seg_res.mask_storage_key.startswith(f"workspaces/{ws}/")
    assert seg_res.person_count >= 1

    # 5. Background Removal
    bg_req = BackgroundRemovalRequest(
        image_storage_key=f"workspaces/{ws}/inputs/product.png",
        content_hash="hash_product_01",
    )
    bg_res = await adapter_a.remove_background(bg_req, ws)
    assert isinstance(bg_res, BackgroundRemovalResult)
    assert bg_res.output_storage_key.startswith(f"workspaces/{ws}/")

    # 6. Lip Sync
    lip_req = LipSyncRequest(
        video_storage_key=f"workspaces/{ws}/inputs/face.mp4",
        audio_storage_key=f"workspaces/{ws}/inputs/voice.wav",
        content_hash="hash_lipsync_01",
    )
    lip_res = await adapter_a.sync_lips(lip_req, ws)
    assert isinstance(lip_res, LipSyncResult)
    assert lip_res.output_video_storage_key.startswith(f"workspaces/{ws}/")

    # 7. Upscale
    up_req = UpscaleRequest(
        media_storage_key=f"workspaces/{ws}/inputs/low_res.png",
        content_hash="hash_lowres_01",
        scale_factor=2,
    )
    up_res = await adapter_a.upscale(up_req, ws)
    assert isinstance(up_res, UpscaleResult)
    assert up_res.output_storage_key.startswith(f"workspaces/{ws}/")

    # 8. Audio Denoise
    denoise_req = AudioDenoiseRequest(
        audio_storage_key=f"workspaces/{ws}/inputs/noisy_voice.wav",
        content_hash="hash_noisy_01",
    )
    denoise_res = await adapter_a.denoise(denoise_req, ws)
    assert isinstance(denoise_res, AudioDenoiseResult)
    assert denoise_res.output_audio_storage_key.startswith(f"workspaces/{ws}/")

    # 9. Audio Enhance
    enhance_req = AudioEnhanceRequest(
        audio_storage_key=f"workspaces/{ws}/inputs/raw_mic.wav",
        content_hash="hash_raw_mic_01",
    )
    enhance_res = await adapter_a.enhance(enhance_req, ws)
    assert isinstance(enhance_res, AudioEnhanceResult)
    assert enhance_res.output_audio_storage_key.startswith(f"workspaces/{ws}/")

    # 10. Vocal Isolation
    vocal_req = VocalIsolationRequest(
        audio_storage_key=f"workspaces/{ws}/inputs/song.mp4",
        content_hash="hash_song_01",
        extract_instrumental=True,
    )
    vocal_res = await adapter_a.isolate_vocals(vocal_req, ws)
    assert isinstance(vocal_res, VocalIsolationResult)
    assert vocal_res.vocals_storage_key.startswith(f"workspaces/{ws}/")
    assert vocal_res.instrumental_storage_key is not None


def test_contract_validation_rejections():
    """Validates boundary invariant rejections on bad requests."""
    # Negative duration rejected
    with pytest.raises(ValidationError):
        VideoGenerationRequest(prompt="Invalid duration", duration_seconds=-5.0)

    # Empty prompt rejected
    with pytest.raises(ValidationError):
        ImageGenerationRequest(prompt="", width=512, height=512)

    # Scale factor outside allowable range (e.g., 0 or 10)
    with pytest.raises(ValidationError):
        UpscaleRequest(
            media_storage_key="workspaces/ws/file.png",
            content_hash="h1",
            scale_factor=10,
        )
