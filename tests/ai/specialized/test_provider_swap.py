"""
tests/ai/specialized/test_provider_swap.py
==========================================
Provider Swap Proof tests for Specialized Media AI (S27.17 / AI-13 Rule 17).

Invariants verified:
- Fake Provider A -> swap configuration / registry -> Fake Provider B.
- Domain code, call signatures, and data contracts remain 100% unchanged.
- Recipes / canonical services remain untouched; only adapter/registry changes.
"""

import pytest

from ai.contracts.specialized import ImageGenerationRequest, TTSRequest, UpscaleRequest
from ai.specialized.adapters import FakeSpecializedMediaAdapterA, FakeSpecializedMediaAdapterB
from ai.specialized.service import SpecializedMediaService
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "swap_storage")


@pytest.fixture
def service(storage):
    adapter_a = FakeSpecializedMediaAdapterA(storage_service=storage)
    adapter_b = FakeSpecializedMediaAdapterB(storage_service=storage)

    svc = SpecializedMediaService(storage_service=storage)
    svc.register_provider_adapter("fake-specialized-a", adapter_a)
    svc.register_provider_adapter("fake-specialized-b", adapter_b)
    return svc


@pytest.mark.asyncio
async def test_provider_swap_speech_synthesis(service):
    """
    Verifies that calling synthesize_speech produces identical domain result
    whether dispatched to Provider A or Provider B, with zero domain changes.
    """
    ws = "ws_swap_client"
    req = TTSRequest(text="Provider swap proof test", voice_id="voice_swappable")

    # 1. Dispatch to Fake Provider A
    result_a = await service.synthesize_speech(ws, req, provider_id_override="fake-specialized-a")
    assert result_a.audio_storage_key.startswith(f"workspaces/{ws}/")
    assert result_a.provenance.provider == "fake-specialized-a"

    # 2. Swap to Fake Provider B via configuration
    result_b = await service.synthesize_speech(ws, req, provider_id_override="fake-specialized-b")
    assert result_b.audio_storage_key.startswith(f"workspaces/{ws}/")
    assert result_b.provenance.provider == "fake-specialized-b"

    # Domain contract invariants hold identically across both
    assert result_a.duration_seconds == result_b.duration_seconds
    assert result_a.sample_rate == result_b.sample_rate == 44100


@pytest.mark.asyncio
async def test_provider_swap_image_generation(service):
    """Verifies image generation provider swap with identical request contract."""
    ws = "ws_swap_client"
    req = ImageGenerationRequest(prompt="A landscape painting", width=1280, height=720)

    # Provider A
    res_a = await service.generate_image(ws, req, provider_id_override="fake-specialized-a")
    assert res_a.provenance.provider == "fake-specialized-a"
    assert res_a.width == 1280

    # Provider B
    res_b = await service.generate_image(ws, req, provider_id_override="fake-specialized-b")
    assert res_b.provenance.provider == "fake-specialized-b"
    assert res_b.width == 1280


@pytest.mark.asyncio
async def test_provider_swap_upscale(service):
    """Verifies upscale transformation provider swap with identical request contract."""
    ws = "ws_swap_client"
    req = UpscaleRequest(
        media_storage_key=f"workspaces/{ws}/inputs/frame_01.png",
        content_hash="hash_swap_upscale",
        scale_factor=4,
    )

    # Provider A
    res_a = await service.upscale(ws, req, provider_id_override="fake-specialized-a")
    assert res_a.provenance.provider == "fake-specialized-a"
    assert res_a.width == 7680

    # Provider B
    res_b = await service.upscale(ws, req, provider_id_override="fake-specialized-b")
    assert res_b.provenance.provider == "fake-specialized-b"
    assert res_b.width == res_a.width
