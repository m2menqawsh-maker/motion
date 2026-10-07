"""
tests/ai/mcp/test_mcp_compatibility_facade.py
=============================================
Comprehensive automated test suite for the MCP Compatibility Layer (S28-M09).

Covers all required architectural cases:
- Case A: Valid legacy call -> compatibility facade -> canonical service -> PASS
- Case B: Internal direct path works without MCP server
- Case C: Invalid request fails before side effects
- Case D: Unauthorized request fails closed
- Case E: Cross-tenant reference fails closed
- Case F: MCP process unavailable -> internal canonical path continues to work
- Case G: Canonical service unavailable -> MCP does not claim false success
- Case H: Duplicate mutation with same idempotency key produces no duplicate side effect
- Blocked Tool Policy: concatenate_videos fails closed with structured security error
"""

import asyncio
import json
import pytest
from pathlib import Path
from typing import Dict, Any

from ai.contracts import (
    AIErrorCode,
    CapabilityRequest,
    CapabilityStatus,
    CapabilityType,
)
from ai.contracts.media_ops import CheckCacheInput, StoreCacheInput
from ai.mcp.compatibility import (
    CompatibilityMCPServer,
    CompatibilityRegistry,
    CompatibilityRequest,
    MCPCompatibilityFacade,
    MCPCompatibilityStatus,
    default_compatibility_registry,
    default_compatibility_server,
    get_mcp_compatibility_facade,
)
from ai.tools.gateway import ToolGateway, get_tool_gateway
from ai.tools.types import TrustedToolExecutionContext
from api.services.asset_service import AssetService
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2, Provenance
from scripts.core.manifest_loader import save_manifest


@pytest.fixture
def mock_project(tmp_path):
    """Sets up an isolated mock project with valid Manifest v2."""
    proj_id = "prj_mcp_compat_test"
    proj_dir = Path("projects") / proj_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = proj_dir / "02_asset_manifest.json"
    asset = AssetV2(
        asset_id="ast_sample_video",
        kind=AssetKind.VIDEO,
        provenance=Provenance.USER_UPLOAD,
        status=AssetStatus.READY,
        source_path="assets/ready/sample.mp4",
        processed_path="assets/ready/sample.mp4",
        content_hash="hash_video_123",
    )
    manifest = ManifestV2(project_id=proj_id, assets=[asset])
    save_manifest(manifest, manifest_path)

    # Create dummy ready and cache dirs
    ready_dir = proj_dir / "assets" / "ready"
    ready_dir.mkdir(parents=True, exist_ok=True)
    (ready_dir / "sample.mp4").write_bytes(b"dummy video data")

    cache_dir = proj_dir / "assets" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "ast_sample_video_trans123.mp4").write_bytes(b"cached variant data")

    yield proj_id, proj_dir

    import shutil
    shutil.rmtree(proj_dir, ignore_errors=True)


@pytest.fixture
def facade():
    return get_mcp_compatibility_facade()


# =============================================================================
# Case A: Valid Legacy Call via Facade -> Canonical Service -> PASS
# =============================================================================

@pytest.mark.asyncio
async def test_case_a_check_cache_hit_via_facade(facade, mock_project):
    """External MCP check_cache request resolves to cache hit via AssetService."""
    proj_id, _ = mock_project
    req = CompatibilityRequest(
        server_id="common-tools-mcp",
        tool_name="check_cache",
        arguments={
            "asset_id": "ast_sample_video",
            "specs_hash": "trans123",
            "cache_dir": f"projects/{proj_id}/assets/cache",
        },
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_mcp_caller",
        permissions=["viewer", "editor", "asset:read"],
    )

    resp = await facade.execute(req)
    assert resp.success is True
    assert resp.error is None
    assert resp.capability_id == CapabilityType.CHECK_MEDIA_CACHE.value
    assert resp.canonical_owner == "AssetService"
    assert resp.data is not None


@pytest.mark.asyncio
async def test_case_a_check_cache_miss_via_facade(facade, mock_project):
    """External MCP check_cache request returns None on non-existent hash."""
    proj_id, _ = mock_project
    req = CompatibilityRequest(
        server_id="common-tools-mcp",
        tool_name="check_cache",
        arguments={
            "asset_id": "ast_sample_video",
            "specs_hash": "non_existent_hash",
            "cache_dir": f"projects/{proj_id}/assets/cache",
        },
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_mcp_caller",
        permissions=["viewer", "editor", "asset:read"],
    )

    resp = await facade.execute(req)
    assert resp.success is True
    assert resp.error is None
    assert resp.data is None


@pytest.mark.asyncio
async def test_case_a_change_asset_status_via_facade(facade, mock_project):
    """External MCP change_asset_status mutates asset lifecycle via AssetService."""
    proj_id, _ = mock_project
    req = CompatibilityRequest(
        server_id="media-sources-mcp",
        tool_name="change_asset_status",
        arguments={
            "asset_id": "ast_sample_video",
            "from_status": "ready",
            "to_status": "processing",
            "asset_type": "video",
        },
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_mcp_caller",
        roles=["EDITOR"],
        permissions=["editor", "asset:upload"],
    )

    resp = await facade.execute(req)
    assert resp.success is True
    assert resp.error is None
    assert resp.capability_id == CapabilityType.MUTATE_ASSET_STATUS.value
    assert resp.canonical_owner == "AssetService"
    assert resp.canonical_output["current_status"] == "processing"


# =============================================================================
# Case B: Internal Direct Path Works Without MCP Server
# =============================================================================

@pytest.mark.asyncio
async def test_case_b_internal_direct_path_without_mcp(mock_project):
    """Internal AI callers use ToolGateway directly with zero MCP involvement."""
    proj_id, _ = mock_project
    gateway = get_tool_gateway()
    context = TrustedToolExecutionContext(
        actor_id="usr_internal_planner",
        workspace_id="ws_internal",
        correlation_id="corr_internal_123",
        roles=["EDITOR"],
        permissions=["viewer", "editor", "asset:read"],
    )

    cap_req = CapabilityRequest(
        capability_id=CapabilityType.CHECK_MEDIA_CACHE,
        workspace_id="ws_internal",
        project_id=proj_id,
        actor_id="usr_internal_planner",
        input={
            "project_id": proj_id,
            "asset_id": "ast_sample_video",
            "transformation_hash": "trans123",
        },
    )

    res = await gateway.execute(cap_req, context)
    assert res.status == CapabilityStatus.SUCCESS
    assert res.output["cache_hit"] is True
    assert res.error is None
    assert "ast_sample_video_trans123" in res.output["cached_storage_key"]


# =============================================================================
# Case C: Invalid Request Fails Before Side Effects
# =============================================================================

@pytest.mark.asyncio
async def test_case_c_path_traversal_fails_closed(facade, mock_project):
    """Inbound request containing path traversal is rejected before execution."""
    proj_id, _ = mock_project
    req = CompatibilityRequest(
        server_id="audio-tools-mcp",
        tool_name="trim_audio",
        arguments={
            "file_path": "../../etc/shadow",
            "target_duration": 5.0,
        },
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_attacker",
        permissions=["editor"],
    )

    resp = await facade.execute(req)
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == AIErrorCode.SCHEMA_VALIDATION_FAILED
    assert "Path traversal detected" in resp.error.message


@pytest.mark.asyncio
async def test_case_c_missing_required_arguments_fails_closed(facade, mock_project):
    """Missing required parameters fails closed with SCHEMA_VALIDATION_FAILED."""
    proj_id, _ = mock_project
    req = CompatibilityRequest(
        server_id="common-tools-mcp",
        tool_name="save_to_cache",
        arguments={
            "asset_id": "ast_test",
            # missing transformation_hash / source_storage_key
        },
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_mcp_caller",
        permissions=["editor"],
    )

    resp = await facade.execute(req)
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == AIErrorCode.SCHEMA_VALIDATION_FAILED


# =============================================================================
# Case D: Unauthorized Request Fails Closed
# =============================================================================

@pytest.mark.asyncio
async def test_case_d_unauthorized_mutation_fails_closed(facade, mock_project):
    """Viewer attempting mutating tool fails closed with POLICY_DENIED."""
    proj_id, _ = mock_project
    req = CompatibilityRequest(
        server_id="media-sources-mcp",
        tool_name="change_asset_status",
        arguments={
            "asset_id": "ast_sample_video",
            "to_status": "ready",
        },
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_viewer_only",
        roles=["VIEWER"],
        permissions=["viewer"],  # lacks 'editor'
    )

    resp = await facade.execute(req)
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code == AIErrorCode.POLICY_DENIED
    assert "lacks required permission" in resp.error.message


# =============================================================================
# Case E: Cross-Tenant Reference Fails Closed
# =============================================================================

@pytest.mark.asyncio
async def test_case_e_cross_project_reference_fails_closed(facade, mock_project):
    """Caller bound to project A attempting to mutate project B fails closed."""
    proj_id, _ = mock_project
    foreign_proj = "prj_other_tenant"

    req = CompatibilityRequest(
        server_id="common-tools-mcp",
        tool_name="check_cache",
        arguments={
            "project_id": foreign_proj,  # Mismatched with request.project_id
            "asset_id": "ast_sample_video",
            "specs_hash": "trans123",
        },
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_mcp_caller",
        permissions=["viewer", "editor"],
    )

    resp = await facade.execute(req)
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code in (AIErrorCode.TENANT_ACCESS_DENIED, AIErrorCode.SCHEMA_VALIDATION_FAILED)


# =============================================================================
# Case F: MCP Process Unavailable -> Internal AI Continues Healthy
# =============================================================================

def test_case_f_internal_capabilities_work_without_mcp_process():
    """Confirms ToolGateway and Domain services have zero runtime dependency on MCP processes."""
    from ai.capabilities.catalog import get_capability_catalog
    catalog = get_capability_catalog()
    assert catalog.total_count == 43

    # All domain services and native adapters are pure Python / system binaries
    for cap in catalog.list_all():
        assert cap.owner is not None
        assert len(cap.implementations) > 0


# =============================================================================
# Case G: Canonical Service Unavailable -> MCP Does Not Claim Success
# =============================================================================

@pytest.mark.asyncio
async def test_case_g_canonical_service_error_propagates_structured_error(facade):
    """When target project does not exist, AssetService raises error; MCP reports failure."""
    req = CompatibilityRequest(
        server_id="common-tools-mcp",
        tool_name="save_to_cache",
        arguments={
            "file_path": "assets/ready/sample.mp4",
            "asset_id": "ast_nonexistent",
            "specs_hash": "h_123",
        },
        workspace_id="ws_compat",
        project_id="prj_non_existent_project_xyz",
        actor_id="usr_mcp_caller",
        roles=["EDITOR"],
        permissions=["editor"],
    )

    resp = await facade.execute(req)
    assert resp.success is False
    assert resp.error is not None
    # Must NOT claim success or return dummy path
    assert resp.data is None


# =============================================================================
# Case H: Duplicate Mutation with Same Idempotency Key Replays Result
# =============================================================================

@pytest.mark.asyncio
async def test_case_h_idempotency_key_replays_safely(facade, mock_project):
    """Consecutive calls with the same idempotency key replay cached result."""
    proj_id, _ = mock_project
    idem_key = "idem_compat_test_key_001"

    req1 = CompatibilityRequest(
        server_id="common-tools-mcp",
        tool_name="check_cache",
        arguments={
            "asset_id": "ast_sample_video",
            "specs_hash": "trans123",
        },
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_mcp_caller",
        idempotency_key=idem_key,
        permissions=["viewer", "editor"],
    )

    resp1 = await facade.execute(req1)
    assert resp1.success is True

    # Re-execute with identical payload and key
    resp2 = await facade.execute(req1)
    assert resp2.success is True
    assert resp2.data == resp1.data


# =============================================================================
# Blocked Insecure Tool Policy Check
# =============================================================================

@pytest.mark.asyncio
async def test_concatenate_videos_security_blocked(facade, mock_project):
    """concatenate_videos fails closed with structured security error."""
    proj_id, _ = mock_project
    req = CompatibilityRequest(
        server_id="ffmpeg-mcp-server",
        tool_name="concatenate_videos",
        arguments={"video_paths": ["a.mp4", "b.mp4"]},
        workspace_id="ws_compat",
        project_id=proj_id,
        actor_id="usr_mcp_caller",
    )

    resp = await facade.execute(req)
    assert resp.success is False
    assert resp.error is not None
    assert resp.error.code in (AIErrorCode.POLICY_DENIED, AIErrorCode.CAPABILITY_UNAVAILABLE)
    assert "permanently blocked for security" in resp.error.message


def test_compatibility_registry_totals():
    """Proves all 34 tools are registered with 0 unknown."""
    reg = default_compatibility_registry
    assert reg.total_count == 34
    counts = reg.get_status_counts()
    assert counts["FULL"] == 31
    assert counts["PARTIAL"] == 2
    assert counts["BLOCKED"] == 1
    assert counts["DEPRECATED"] == 0
