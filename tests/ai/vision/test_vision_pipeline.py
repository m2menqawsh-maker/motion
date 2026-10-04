"""
tests/ai/vision/test_vision_pipeline.py
=======================================
End-to-end tests for VisionPipeline, cache hit/miss, tenant isolation, and progressive hierarchy (S27.15 / AI-13).
"""

import pytest
from ai.cache.service import AICacheService
from ai.contracts.vision import VisualIntelligence
from ai.vision.pipeline import VisionPipeline
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "storage_root")


@pytest.fixture
def cache(storage, tmp_path):
    engine = DatabaseEngine(f"sqlite:///{tmp_path}/vision_cache.db")
    repo = SQLAICacheRepository(engine=engine)
    return AICacheService(repository=repo, storage_service=storage)


@pytest.fixture
def pipeline(storage, cache):
    return VisionPipeline(storage_service=storage, cache_service=cache)


@pytest.mark.asyncio
async def test_vision_pipeline_progressive_execution(pipeline):
    video_bytes = b"MP4_SYNTHETIC_VIDEO_BYTES_VERSION_A"
    simulated_ocr = [{"text": "Hello World", "confidence": 0.99}]
    simulated_objects = [{"label": "coffee_mug", "confidence": 0.95}]

    report = await pipeline.analyze_video(
        workspace_id="ws_video_client",
        asset_id="ast_demo_01",
        media_bytes=video_bytes,
        simulated_shots=[2.0, 5.0],
        simulated_ocr_blocks=simulated_ocr,
        simulated_objects=simulated_objects,
        request_premium_multimodal=False,
    )

    assert isinstance(report, VisualIntelligence)
    assert report.status == "READY"
    assert report.has_visual_analysis is True
    assert len(report.shots) == 3
    assert len(report.keyframes) >= 3
    assert len(report.ocr) >= 1
    assert report.ocr[0].text == "Hello World"
    assert len(report.objects) >= 1
    assert report.objects[0].label == "coffee_mug"
    # Premium multimodal model was NOT called
    assert pipeline.premium_model_invocations == 0


@pytest.mark.asyncio
async def test_vision_pipeline_premium_multimodal_invocation(pipeline):
    video_bytes = b"MP4_PREMIUM_MULTIMODAL_VIDEO"

    report = await pipeline.analyze_video(
        workspace_id="ws_video_client",
        asset_id="ast_premium_01",
        media_bytes=video_bytes,
        request_premium_multimodal=True,
    )

    assert pipeline.premium_model_invocations == 1
    assert len(report.observations) == 1
    assert report.observations[0].category == "narrative_summary"
    assert report.observations[0].provenance.model == "gemini-1.5-pro"


@pytest.mark.asyncio
async def test_vision_cache_hit_and_miss(pipeline):
    """
    Mandatory Test (Rule 9, 30):
    same frame/video + same analysis -> HIT
    byte/content change -> MISS
    """
    video_v1 = b"IDENTICAL_CONTENT_HASH_VIDEO_STREAM"
    video_v2 = b"ALTERED_CONTENT_HASH_VIDEO_STREAM_NEW_BYTE"

    # Call 1: MISS (initial run)
    report_1 = await pipeline.analyze_video(
        workspace_id="ws_video_client",
        asset_id="ast_cached_01",
        media_bytes=video_v1,
        simulated_shots=[3.0],
    )
    assert report_1.status == "READY"

    # Call 2: HIT (same video bytes, same settings)
    report_2 = await pipeline.analyze_video(
        workspace_id="ws_video_client",
        asset_id="ast_cached_01",
        media_bytes=video_v1,
        simulated_shots=[3.0],
    )
    assert report_2.status == "READY"
    assert len(report_2.shots) == len(report_1.shots)

    # Call 3: MISS (content byte changed)
    report_3 = await pipeline.analyze_video(
        workspace_id="ws_video_client",
        asset_id="ast_cached_01",
        media_bytes=video_v2,
        simulated_shots=[3.0],
    )
    assert report_3.status == "READY"
    # Provenance timestamp differs on re-run
    assert report_3.provenance.timestamp >= report_1.provenance.timestamp


@pytest.mark.asyncio
async def test_vision_tenant_isolation(storage, cache):
    """
    Mandatory Test (Rule 25):
    Workspace A cannot read Workspace B cached vision analysis or keyframes.
    """
    pipeline = VisionPipeline(storage_service=storage, cache_service=cache)
    video_bytes = b"SHARED_SECRET_CONTENT_VIDEO"

    # Execute for Tenant A
    await pipeline.analyze_video(
        workspace_id="tenant_a",
        asset_id="ast_secret_01",
        media_bytes=video_bytes,
    )

    # Tenant B tries to query cache with its own workspace ID
    # Cache must miss for Tenant B because cache key includes workspace scope
    report_b = await pipeline.analyze_video(
        workspace_id="tenant_b",
        asset_id="ast_secret_01",
        media_bytes=video_bytes,
    )

    assert report_b.keyframes[0].storage_key.startswith("workspaces/tenant_b/")
    assert not report_b.keyframes[0].storage_key.startswith("workspaces/tenant_a/")
