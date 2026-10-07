"""
tests/ai/image_modernization/test_image_cache.py
================================================
Comprehensive tests for content-addressed cache (S28-M08).

Invariants:
- Cache key is strictly content-addressed: sha256(source_hash + spec + version).
- Deterministic operation normalization.
- Invalidation on processor version change.
- Tenant isolation across workspaces/projects.
- Corrupted or missing backing objects fail closed as cache misses.
"""

from __future__ import annotations

import io
import pytest
from PIL import Image

from ai.image_processing.cache import (
    ImageCacheManager,
    build_cache_key,
    build_cache_storage_key,
    compute_source_hash,
    normalize_operation_spec,
)
from ai.image_processing.contracts import ResizeImageRequest
from ai.image_processing.service import ImageProcessingService


def test_normalized_operation_spec_deterministic():
    spec_a = {"height": 720, "width": 1280, "fit_mode": "contain", "quality": 90}
    spec_b = {"quality": 90, "width": 1280, "fit_mode": "contain", "height": 720}
    assert normalize_operation_spec(spec_a) == normalize_operation_spec(spec_b)


def test_cache_hit_and_miss_lifecycle(mock_storage, sample_png_bytes):
    manager = ImageCacheManager(mock_storage, processor_version="v1.0")
    spec = {"target_width": 100, "target_height": 100, "fit_mode": "contain"}

    # Initial lookup is a miss
    hit = manager.lookup("proj_1", sample_png_bytes, spec, "png")
    assert hit is None

    # Process and store
    out_img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    bio = io.BytesIO()
    out_img.save(bio, format="PNG")
    out_bytes = bio.getvalue()

    stored_key = manager.store("proj_1", sample_png_bytes, spec, out_bytes, "png")
    assert stored_key.startswith("projects/proj_1/assets/cache/")
    assert mock_storage.exists(stored_key)

    # Subsequent lookup with same bytes + same spec + same version is a hit
    hit = manager.lookup("proj_1", sample_png_bytes, spec, "png")
    assert hit is not None
    cached_key, cached_bytes = hit
    assert cached_key == stored_key
    assert cached_bytes == out_bytes


def test_cache_miss_on_different_spec(mock_storage, sample_png_bytes):
    manager = ImageCacheManager(mock_storage, processor_version="v1.0")
    spec_1 = {"target_width": 100, "target_height": 100}
    spec_2 = {"target_width": 200, "target_height": 200}

    out_bytes = sample_png_bytes
    manager.store("proj_1", sample_png_bytes, spec_1, out_bytes, "png")

    assert manager.lookup("proj_1", sample_png_bytes, spec_2, "png") is None


def test_cache_miss_on_different_source_bytes(mock_storage, sample_png_bytes, sample_jpeg_bytes):
    manager = ImageCacheManager(mock_storage, processor_version="v1.0")
    spec = {"target_width": 100}

    manager.store("proj_1", sample_png_bytes, spec, sample_png_bytes, "png")

    # Same spec, but different source bytes -> cache miss
    assert manager.lookup("proj_1", sample_jpeg_bytes, spec, "png") is None


def test_cache_miss_on_processor_version_change(mock_storage, sample_png_bytes):
    manager_v1 = ImageCacheManager(mock_storage, processor_version="v1.0")
    manager_v2 = ImageCacheManager(mock_storage, processor_version="v2.0")
    spec = {"target_width": 150}

    manager_v1.store("proj_1", sample_png_bytes, spec, sample_png_bytes, "png")

    assert manager_v1.lookup("proj_1", sample_png_bytes, spec, "png") is not None
    # Version v2.0 must invalidate / miss
    assert manager_v2.lookup("proj_1", sample_png_bytes, spec, "png") is None


def test_corrupted_cached_payload_fails_closed_as_miss(mock_storage, sample_png_bytes):
    manager = ImageCacheManager(mock_storage, processor_version="v1.0")
    spec = {"target_width": 100}

    stored_key = manager.store("proj_1", sample_png_bytes, spec, sample_png_bytes, "png")

    # Corrupt the storage object
    mock_storage.put(stored_key, b"CORRUPTED_BYTES_NOT_AN_IMAGE")

    # Lookup should detect corrupted output, log warning, and return None (cache miss)
    assert manager.lookup("proj_1", sample_png_bytes, spec, "png") is None


def test_cross_tenant_cache_isolation(mock_storage, sample_png_bytes):
    manager = ImageCacheManager(mock_storage, processor_version="v1.0")
    spec = {"target_width": 100}

    key_p1 = manager.store("proj_tenant_a", sample_png_bytes, spec, sample_png_bytes, "png")
    assert "proj_tenant_a" in key_p1

    # Project B cannot find or access Project A's cache
    hit_p2 = manager.lookup("proj_tenant_b", sample_png_bytes, spec, "png")
    assert hit_p2 is None


def test_service_integration_cache_reuse(image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    mock_storage.put("projects/proj_1/images/input.png", sample_png_bytes)

    req = ResizeImageRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/input.png",
        target_width=100,
        target_height=50,
    )

    # First call: cache miss, processes and stores
    res_1 = image_service.resize_image(req)
    assert res_1.width == 100
    assert res_1.height == 50

    # Second call: cache hit, returns identical output key
    res_2 = image_service.resize_image(req)
    assert res_2.output_storage_key == res_1.output_storage_key
    assert res_2.file_size_bytes == res_1.file_size_bytes


def test_strict_cross_tenant_cache_isolation_and_denial(image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    """
    Explicitly verifies requirement §3:
    - Workspace A + source asset A + op spec X -> cache entry A
    - Workspace B + same source bytes + same normalized op spec -> MUST NOT gain unauthorized access to Workspace A cache object
    - Workspace A caller -> attempts cache/storage key belonging to Workspace B -> DENY
    - No cross-workspace cache leakage.
    """
    from ai.image_processing.errors import ImageTenantConfinementError

    # 1. Setup Workspace A source asset
    mock_storage.put("projects/ws_alpha/images/source.png", sample_png_bytes)
    req_alpha = ResizeImageRequest(
        project_id="ws_alpha",
        image_storage_key="projects/ws_alpha/images/source.png",
        target_width=120,
        target_height=60,
    )
    res_alpha = image_service.resize_image(req_alpha)
    assert res_alpha.output_storage_key.startswith("projects/ws_alpha/assets/cache/")
    assert mock_storage.exists(res_alpha.output_storage_key)

    # 2. Setup Workspace B with identical source bytes and identical normalized spec
    mock_storage.put("projects/ws_beta/images/source.png", sample_png_bytes)
    req_beta = ResizeImageRequest(
        project_id="ws_beta",
        image_storage_key="projects/ws_beta/images/source.png",
        target_width=120,
        target_height=60,
    )

    # Cache lookup directly for Workspace B must be a miss (no leakage from Workspace A)
    spec = req_beta.model_dump()
    cache_mgr = ImageCacheManager(mock_storage, processor_version="v1.0")
    assert cache_mgr.lookup("ws_beta", sample_png_bytes, spec, "png") is None

    # Workspace B processes independently -> its output must be strictly under ws_beta
    res_beta = image_service.resize_image(req_beta)
    assert res_beta.output_storage_key.startswith("projects/ws_beta/assets/cache/")
    assert res_beta.output_storage_key != res_alpha.output_storage_key
    assert "ws_alpha" not in res_beta.output_storage_key

    # 3. Workspace A caller attempts to supply or retrieve Workspace B's cache key -> DENIED
    unauthorized_req_a = ResizeImageRequest(
        project_id="ws_alpha",
        image_storage_key=res_beta.output_storage_key,
        target_width=100,
    )
    with pytest.raises(ImageTenantConfinementError):
        image_service.resize_image(unauthorized_req_a)

    # 4. Workspace B caller attempts to supply or retrieve Workspace A's cache key -> DENIED
    unauthorized_req_b = ResizeImageRequest(
        project_id="ws_beta",
        image_storage_key=res_alpha.output_storage_key,
        target_width=100,
    )
    with pytest.raises(ImageTenantConfinementError):
        image_service.resize_image(unauthorized_req_b)


def test_service_recomputes_and_heals_when_cache_entry_is_corrupted(image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    """
    Explicitly verifies requirement §5:
    - Valid cache key + corrupted cached bytes.
    - Cache hit on corrupted payload is rejected (no canonical success from corrupt bytes).
    - Service automatically falls back to recompute, produces valid output, and heals the cache.
    """
    mock_storage.put("projects/proj_heal/images/input.png", sample_png_bytes)

    req = ResizeImageRequest(
        project_id="proj_heal",
        image_storage_key="projects/proj_heal/images/input.png",
        target_width=140,
        target_height=70,
    )

    # Initial execution creates valid cache
    res_1 = image_service.resize_image(req)
    cache_key = res_1.output_storage_key
    assert mock_storage.exists(cache_key)

    # Inject corruption into the cached payload
    mock_storage.put(cache_key, b"NOT_A_VALID_IMAGE_CORRUPT_PAYLOAD_12345")

    # Second execution: cache manager detects corruption, falls back to fresh processing
    res_2 = image_service.resize_image(req)
    assert res_2.output_storage_key == cache_key
    assert res_2.width == 140
    assert res_2.height == 70

    # Ensure storage is healed and contains valid image bytes (NOT the corrupt payload)
    healed_bytes = mock_storage.get(cache_key)
    assert healed_bytes != b"NOT_A_VALID_IMAGE_CORRUPT_PAYLOAD_12345"
    assert healed_bytes.startswith(b"\x89PNG\r\n\x1a\n")

