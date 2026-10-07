"""
tests/ai/specialized/test_durability_and_cache.py
=================================================
Durability and Caching policy tests for Specialized Media AI (S27.17 / AI-13 Rules 20 & 21).

Invariants verified:
- Durable activity registration with idempotency key.
- Never cache IMAGE_GENERATION or VIDEO_GENERATION per capability cache policy.
- Deterministic operations (PERSON_SEGMENTATION, UPSCALE, AUDIO_DENOISE) use AI-11 cache.
- Repeated identical deterministic call produces Cache HIT without re-invoking provider.
"""

import pytest

from ai.cache.service import AICacheService
from ai.contracts.common import CapabilityType
from ai.contracts.specialized import (
    AudioDenoiseRequest,
    ImageGenerationRequest,
    PersonSegmentationRequest,
    VideoGenerationRequest,
)
from ai.specialized.adapters import FakeSpecializedMediaAdapterA
from ai.specialized.service import SpecializedMediaService
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "dur_cache_storage")


@pytest.fixture
def cache(tmp_path, storage):
    db_file = tmp_path / "spec_cache.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAICacheRepository(engine=engine)
    return AICacheService(repository=repo, storage_service=storage)


@pytest.fixture
def run_repo(tmp_path):
    db_file = tmp_path / "spec_run.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    return SQLAIRunRepository(engine=engine)


@pytest.mark.asyncio
async def test_image_and_video_generation_are_never_cached(storage, cache):
    """
    Mandatory Test (Rule 21):
    IMAGE_GENERATION and VIDEO_GENERATION must NEVER be cached,
    executing fresh every single time.
    """
    adapter = FakeSpecializedMediaAdapterA(storage_service=storage)
    svc = SpecializedMediaService(storage_service=storage, cache_service=cache)
    svc.register_provider_adapter("fake-specialized-a", adapter)

    ws = "ws_gen_nocache"

    # 1. Image Generation (2 identical calls)
    img_req = ImageGenerationRequest(prompt="A mystical forest at dawn", width=512, height=512)
    res_img1 = await svc.generate_image(ws, img_req, provider_id_override="fake-specialized-a")
    res_img2 = await svc.generate_image(ws, img_req, provider_id_override="fake-specialized-a")

    # Both must invoke provider (invocation count == 2)
    assert adapter.invocation_count == 2

    # 2. Video Generation (2 identical calls)
    vid_req = VideoGenerationRequest(prompt="Water droplets in slow motion", duration_seconds=3.0)
    res_vid1 = await svc.generate_video(ws, vid_req, provider_id_override="fake-specialized-a")
    res_vid2 = await svc.generate_video(ws, vid_req, provider_id_override="fake-specialized-a")

    # Invocations increment to 4
    assert adapter.invocation_count == 4


@pytest.mark.asyncio
async def test_deterministic_transform_cache_hit(storage, cache):
    """
    Mandatory Test (Rule 21):
    Deterministic operations (e.g. PERSON_SEGMENTATION) should cache,
    producing a Cache HIT on repeated requests.
    """
    adapter = FakeSpecializedMediaAdapterA(storage_service=storage)
    svc = SpecializedMediaService(storage_service=storage, cache_service=cache)
    svc.register_provider_adapter("fake-specialized-a", adapter)

    ws = "ws_det_cache"
    seg_req = PersonSegmentationRequest(
        image_storage_key=f"workspaces/{ws}/inputs/person_cache.png",
        content_hash="hash_person_cache_001",
    )

    # Call 1: MISS (adapter invoked)
    res1 = await svc.segment_person(ws, seg_req, provider_id_override="fake-specialized-a")
    assert adapter.invocation_count == 1
    assert res1.mask_storage_key is not None

    # Call 2: HIT (adapter not invoked!)
    res2 = await svc.segment_person(ws, seg_req, provider_id_override="fake-specialized-a")
    assert adapter.invocation_count == 1  # Still 1! Zero extra provider execution.
    assert res2.mask_storage_key == res1.mask_storage_key


@pytest.mark.asyncio
async def test_durable_activity_recording(storage, run_repo):
    """
    Mandatory Test (Rule 20):
    Execution creates durable activity record with idempotency semantics.
    """
    adapter = FakeSpecializedMediaAdapterA(storage_service=storage)
    svc = SpecializedMediaService(storage_service=storage, run_repository=run_repo)
    svc.register_provider_adapter("fake-specialized-a", adapter)

    ws = "ws_durable_client"
    req = AudioDenoiseRequest(
        audio_storage_key=f"workspaces/{ws}/inputs/noisy_sample.wav",
        content_hash="hash_durable_audio_01",
    )

    await svc.denoise_audio(ws, req, provider_id_override="fake-specialized-a")

    # Verify run repository recorded the activity with idempotency key
    expected_idemp_key = f"idemp_{req.content_hash}_{CapabilityType.AUDIO_DENOISE.value}"
    act = run_repo.get_activity_by_idempotency_key(
        workspace_id=ws,
        idempotency_key=expected_idemp_key,
    )
    assert act is not None
    assert act.provider == "fake-specialized-a"
    assert act.idempotency_key == expected_idemp_key
