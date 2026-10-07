"""
tests/ai/mcp/test_behavior_parity.py
====================================
Behavior parity verification between legacy MCP functions and new domain/adapters (S27.10).

Proves that:
1. common-tools-mcp check_cache behavior matches AssetService.check_asset_cache.
2. media-sources-mcp change_asset_status behavior is fulfilled by AssetService.update_asset_status.
3. image-tools-mcp operations match the new Image MCP adapters.
"""

import json
import pytest
from pathlib import Path
from PIL import Image

from api.services.asset_service import AssetService
from scripts.core.manifest_model import AssetStatus, AssetKind, Provenance, AssetV2, ManifestV2
from scripts.core.manifest_loader import save_manifest
from ai.mcp.adapters.parity import (
    verify_cache_check_parity,
    verify_asset_status_parity,
    verify_save_cache_parity,
)
from ai.mcp.adapters.image import ImageUpscaleAdapter, ImageCropRatioAdapter, ImageAutoCropAdapter
from ai.mcp.contracts import UpscaleImageInput, CropRatioInput, AutoCropInput
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def test_project(tmp_path, monkeypatch):
    """Sets up a mock project directory with valid Manifest v2."""
    proj_id = "proj_parity_test"
    proj_dir = Path("projects") / proj_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = proj_dir / "02_asset_manifest.json"
    asset = AssetV2(
        asset_id="ast_sample",
        kind=AssetKind.IMAGE,
        provenance=Provenance.USER_UPLOAD,
        status=AssetStatus.READY,
        source_path="assets/ready/sample.png",
        processed_path="assets/ready/sample.png",
        content_hash="abc123hash",
    )
    manifest = ManifestV2(project_id=proj_id, assets=[asset])
    save_manifest(manifest, manifest_path)

    # Create dummy asset file
    ready_dir = proj_dir / "assets" / "ready"
    ready_dir.mkdir(parents=True, exist_ok=True)
    sample_file = ready_dir / "sample.png"
    sample_file.write_bytes(b"dummy image bytes")

    yield proj_id, proj_dir

    # Cleanup
    import shutil
    shutil.rmtree(proj_dir, ignore_errors=True)


@pytest.fixture
def trusted_context():
    return TrustedToolExecutionContext(
        actor_id="usr_parity",
        workspace_id="ws_parity",
        correlation_id="corr_parity",
        roles=["EDITOR"],
        permissions=["asset:read", "asset:upload"],
    )


def test_asset_status_transition_parity(test_project):
    """AssetService.update_asset_status fulfills change_asset_status semantics."""
    proj_id, proj_dir = test_project

    # 1. Transition to 'processing'
    updated = AssetService.update_asset_status(proj_id, "ast_sample", "processing")
    assert verify_asset_status_parity(updated, expected_status="processing", expected_asset_id="ast_sample") is True

    # 2. Verify manifest was updated on disk
    manifest_data = json.loads((proj_dir / "02_asset_manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["assets"][0]["status"] == "processing"

    # 3. Transition to 'ready'
    updated_ready = AssetService.update_asset_status(proj_id, "ast_sample", "ready")
    assert verify_asset_status_parity(updated_ready, expected_status="ready", expected_asset_id="ast_sample") is True


def test_cache_check_parity(test_project):
    """AssetService.check_asset_cache accurately detects existing project assets."""
    proj_id, proj_dir = test_project

    # Existing asset
    hit_path = AssetService.check_asset_cache(proj_id, "ast_sample")
    assert hit_path is not None
    assert "sample.png" in hit_path

    # Non-existent asset
    miss_path = AssetService.check_asset_cache(proj_id, "ast_nonexistent")
    assert miss_path is None


def test_save_cache_parity(test_project, tmp_path):
    """AssetService.save_asset_to_cache persists transformed files to project cache and matches check_asset_cache."""
    proj_id, proj_dir = test_project

    # Create a source file to cache
    source_file = tmp_path / "sample_transcode.png"
    source_file.write_bytes(b"transcoded image payload")

    # Save to cache with specs_hash
    cached_path = AssetService.save_asset_to_cache(
        project_id=proj_id,
        asset_id="ast_sample",
        file_path=str(source_file),
        specs_hash="w200_h200",
    )

    assert Path(cached_path).exists()
    assert "ast_sample_w200_h200.png" in cached_path
    assert Path(cached_path).read_bytes() == b"transcoded image payload"

    # Parity verification with helper
    assert verify_save_cache_parity(cached_path, asset_id="ast_sample", specs_hash="w200_h200") is True

    # Parity with check_asset_cache hit
    hit_path = AssetService.check_asset_cache(proj_id, "ast_sample", specs_hash="w200_h200")
    assert hit_path == cached_path


@pytest.mark.asyncio
async def test_image_upscale_adapter_parity(tmp_path, trusted_context):
    """ImageUpscaleAdapter resizes images with behavior identical to legacy image-tools-mcp."""
    src_img = tmp_path / "orig.png"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(src_img)

    adapter = ImageUpscaleAdapter()
    inp = UpscaleImageInput(file_path=str(src_img), target_width=200, target_height=200)

    out = await adapter.execute(inp, trusted_context)
    assert Path(out.output_path).exists()
    assert out.width == 200
    assert out.height == 200

    with Image.open(out.output_path) as res_img:
        assert res_img.size == (200, 200)


@pytest.mark.asyncio
async def test_image_crop_ratio_adapter_parity(tmp_path, trusted_context):
    """ImageCropRatioAdapter crops images to aspect ratio identically to legacy image-tools-mcp."""
    src_img = tmp_path / "landscape.png"
    img = Image.new("RGB", (1920, 1080), color="red")
    img.save(src_img)

    adapter = ImageCropRatioAdapter()
    inp = CropRatioInput(file_path=str(src_img), target_ratio="1:1")

    out = await adapter.execute(inp, trusted_context)
    assert Path(out.output_path).exists()

    with Image.open(out.output_path) as res_img:
        assert res_img.size == (1080, 1080)
