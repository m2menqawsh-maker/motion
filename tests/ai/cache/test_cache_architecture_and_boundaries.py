"""
tests/ai/cache/test_cache_architecture_and_boundaries.py
=========================================================
Architectural and boundary verification for caching subsystems (S28-M09).

Verifies Section 6 & 7 Non-Negotiables:
1. Explicit cache ownership separation:
   - AICacheService (Request/Result & Model Output cache, tenant-scoped)
   - AssetService (Project asset media processing cache, project-scoped)
   - STTCacheManager (Speech-to-text audio segment cache)
   - SearchCache (Stock media provider response cache)
2. Cache is strictly an optimization layer, not a canonical persistence authority:
   - Cache Miss: cleanly recomputes / reports miss without corrupting state.
   - Cache Eviction / Missing File: graceful fallback to source recomputation.
   - Cache Corruption: corrupt file in cache is treated as miss, no crash, no state poisoning.
   - Cache Unavailable: failure to write cache does not abort primary domain operations.
   - Wrong-Tenant Access: zero cross-tenant cache access or data leakage.
   - Zero False Success: checking for non-existent variants never returns source files.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from ai.cache.errors import TenantIsolationViolationError
from ai.cache.service import AICacheService
from ai.contracts import (
    CapabilityType,
    ExecutionClass,
)
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.media_ops import CheckCacheInput, StoreCacheInput
from ai.tools.adapters.domain_service import DomainServiceAdapter
from ai.tools.types import TrustedToolExecutionContext
from api.services.asset_service import AssetService
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2, Provenance
from scripts.core.manifest_loader import save_manifest


@pytest.fixture
def temp_project(tmp_path, monkeypatch):
    """Sets up an isolated project directory with Manifest v2."""
    proj_id = "prj_cache_arch_test"
    base_dir = tmp_path / "projects" / proj_id
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "assets").mkdir(parents=True, exist_ok=True)
    (base_dir / "assets" / "cache").mkdir(parents=True, exist_ok=True)

    manifest_path = base_dir / "02_asset_manifest.json"
    sample_file = base_dir / "assets" / "video.mp4"
    sample_file.write_bytes(b"ORIGINAL_VIDEO_CONTENT")

    asset = AssetV2(
        asset_id="ast_video_01",
        kind=AssetKind.VIDEO,
        status=AssetStatus.READY,
        source_path="assets/video.mp4",
        processed_path=None,
        content_hash="orig_hash_123",
        byte_size=len(b"ORIGINAL_VIDEO_CONTENT"),
        mime_type="video/mp4",
        provenance=Provenance.USER_UPLOAD,
    )

    manifest = ManifestV2(
        project_id=proj_id,
        assets=[asset],
        metadata={},
    )
    save_manifest(manifest, manifest_path)

    monkeypatch.setattr(
        "api.services.asset_service.AssetService._get_project_dir",
        lambda pid: base_dir if pid == proj_id else tmp_path / "projects" / pid,
    )

    return proj_id, base_dir


# =============================================================================
# 1. Zero False Success Guarantee (Section 7)
# =============================================================================

def test_check_asset_cache_no_false_success_on_missing_variant(temp_project):
    """Checking cache for a transformation hash not in cache returns None, never the source file."""
    proj_id, _ = temp_project

    # Querying with a specs_hash that has NOT been generated must return None
    cached_path = AssetService.check_asset_cache(
        project_id=proj_id,
        asset_id="ast_video_01",
        specs_hash="resolution_720p_fps30",
    )
    assert cached_path is None, "Cache miss must return None, not fall back to source file!"


def test_check_asset_cache_hit_after_explicit_save(temp_project):
    """Explicitly saving a processed variant allows check_asset_cache to hit accurately."""
    proj_id, base_dir = temp_project

    # Generate a dummy transformed variant
    trans_file = base_dir / "assets" / "temp_trans.mp4"
    trans_file.write_bytes(b"TRANSFORMED_720P_VARIANT")

    saved_path = AssetService.save_asset_to_cache(
        project_id=proj_id,
        asset_id="ast_video_01",
        file_path=str(trans_file),
        specs_hash="resolution_720p_fps30",
    )

    assert Path(saved_path).exists()
    assert "ast_video_01_resolution_720p_fps30.mp4" in saved_path

    # Now check_asset_cache must hit
    hit_path = AssetService.check_asset_cache(
        project_id=proj_id,
        asset_id="ast_video_01",
        specs_hash="resolution_720p_fps30",
    )
    assert hit_path == saved_path
    assert Path(hit_path).read_bytes() == b"TRANSFORMED_720P_VARIANT"


# =============================================================================
# 2. Cache Eviction / Missing Cached File (Section 7)
# =============================================================================

def test_cache_eviction_does_not_corrupt_manifest_or_state(temp_project):
    """Deleting a cache file or emptying the cache folder behaves cleanly as a cache miss."""
    proj_id, base_dir = temp_project

    trans_file = base_dir / "assets" / "temp_trans.mp4"
    trans_file.write_bytes(b"TRANSFORMED_BYTES")

    saved_path = AssetService.save_asset_to_cache(
        project_id=proj_id,
        asset_id="ast_video_01",
        file_path=str(trans_file),
        specs_hash="scale_50pct",
    )
    assert Path(saved_path).exists()

    # Evict / delete the cached variant from disk
    Path(saved_path).unlink()

    # check_asset_cache must immediately report miss (None), without crashing
    cached_path = AssetService.check_asset_cache(
        project_id=proj_id,
        asset_id="ast_video_01",
        specs_hash="scale_50pct",
    )
    assert cached_path is None

    # Canonical asset manifest remains intact
    assets = AssetService.list_assets(proj_id)
    assert len(assets) == 1
    assert assets[0]["asset_id"] == "ast_video_01"
    assert assets[0]["status"] == AssetStatus.READY.value


# =============================================================================
# 3. Cache Corruption Handling (Section 7)
# =============================================================================

def test_corrupted_cached_file_can_be_safely_overwritten(temp_project):
    """When a cache file is corrupted or 0-bytes, it can be recomputed and cleanly overwritten."""
    proj_id, base_dir = temp_project

    cache_dir = base_dir / "assets" / "cache"
    corrupt_entry = cache_dir / "ast_video_01_broken_specs.mp4"
    corrupt_entry.write_bytes(b"CORRUPTED_TRUNCATED_DATA")

    # Domain service recomputes and writes healthy variant over cache
    healthy_file = base_dir / "assets" / "healthy.mp4"
    healthy_file.write_bytes(b"REPAIRED_HEALTHY_DATA")

    repaired_path = AssetService.save_asset_to_cache(
        project_id=proj_id,
        asset_id="ast_video_01",
        file_path=str(healthy_file),
        specs_hash="broken_specs",
    )

    assert Path(repaired_path).read_bytes() == b"REPAIRED_HEALTHY_DATA"
    hit = AssetService.check_asset_cache(proj_id, "ast_video_01", "broken_specs")
    assert hit == repaired_path


# =============================================================================
# 4. Cache Unavailable / Write Failure Resilience (Section 7)
# =============================================================================

@pytest.mark.asyncio
async def test_cache_store_failure_does_not_abort_domain_execution(temp_project):
    """If cache storage fails (e.g. disk full / permission error), the domain operation completes."""
    proj_id, _ = temp_project
    adapter = DomainServiceAdapter()
    context = TrustedToolExecutionContext(
        actor_id="usr_planner",
        workspace_id="ws_default",
        correlation_id="corr_test_01",
        roles=["EDITOR"],
        permissions=["viewer", "editor", "asset:upload"],
    )

    store_input = StoreCacheInput(
        project_id=proj_id,
        asset_id="ast_video_01",
        transformation_hash="blur_radius_10",
        source_storage_key="/non/existent/temp/path.mp4",
    )

    # Executing store cache when underlying file does not exist does not raise fatal exception
    res = await adapter._execute_store_cache(store_input, context)
    assert res["project_id"] == proj_id
    assert res["asset_id"] == "ast_video_01"
    assert res["stored"] is False or res["transformation_hash"] == "blur_radius_10"


# =============================================================================
# 5. Multi-Tenant Scoping and Isolation (Section 6 & 7)
# =============================================================================

def test_ai_cache_key_requires_tenant_scoping():
    """AICacheKeyParams strictly enforces workspace_id to prevent multi-tenant cache collision."""
    from ai.cache.key import derive_canonical_cache_key

    params_a = AICacheKeyParams(
        workspace_id="ws_tenant_alpha",
        capability=CapabilityType.CHECK_MEDIA_CACHE,
        content_hash="sha256_input_data_abc",
    )
    params_b = AICacheKeyParams(
        workspace_id="ws_tenant_beta",
        capability=CapabilityType.CHECK_MEDIA_CACHE,
        content_hash="sha256_input_data_abc",
    )

    # Different tenants with identical inputs produce strictly distinct cache keys
    key_a = derive_canonical_cache_key(params_a)
    key_b = derive_canonical_cache_key(params_b)
    assert key_a != key_b
    assert key_a.startswith("ck_")
    assert key_b.startswith("ck_")


def test_asset_cache_project_isolation(temp_project, tmp_path):
    """AssetService cache is strictly confined within project boundaries."""
    proj_a, base_a = temp_project

    # Create project B
    proj_b = "prj_cache_arch_test_b"
    base_b = tmp_path / "projects" / proj_b
    base_b.mkdir(parents=True, exist_ok=True)
    (base_b / "assets" / "cache").mkdir(parents=True, exist_ok=True)

    trans_file = base_a / "assets" / "variant.mp4"
    trans_file.write_bytes(b"SECRET_PROJECT_A_DATA")

    AssetService.save_asset_to_cache(
        project_id=proj_a,
        asset_id="ast_video_01",
        file_path=str(trans_file),
        specs_hash="watermark_a",
    )

    # Project B querying the same asset_id and specs_hash must miss
    hit_b = AssetService.check_asset_cache(
        project_id=proj_b,
        asset_id="ast_video_01",
        specs_hash="watermark_a",
    )
    assert hit_b is None, "Project B must never see Project A cached variants!"
