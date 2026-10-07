"""
tests/ai/mcp/test_mcp_catalog.py
================================
Tests for MCPCatalog, server registration, ownership, and disposition policies (S27.10).
"""

import pytest
from ai.mcp.catalog import MCPCatalog, default_mcp_catalog
from ai.mcp.contracts import (
    MCPDisposition,
    MCPOperationCategory,
    MCPOwnershipClass,
    MCPServerDefinition,
)


def test_catalog_inventory_contains_all_six_servers():
    """Authoritative catalog must contain all 6 repository MCP servers."""
    servers = default_mcp_catalog.list_servers()
    server_ids = [s.server_id for s in servers]
    assert len(server_ids) == 6
    assert "audio-tools-mcp" in server_ids
    assert "video-tools-mcp" in server_ids
    assert "image-tools-mcp" in server_ids
    assert "media-sources-mcp" in server_ids
    assert "common-tools-mcp" in server_ids
    assert "ffmpeg-mcp-server" in server_ids


def test_catalog_deterministic_ordering():
    """list_servers must return entries sorted deterministically by server_id."""
    servers = default_mcp_catalog.list_servers()
    server_ids = [s.server_id for s in servers]
    assert server_ids == sorted(server_ids)


def test_retained_mcp_servers_configuration():
    """Retained MCP servers must be classified as KEEP_AS_MCP and allowed for production."""
    retained_ids = ["audio-tools-mcp", "video-tools-mcp", "image-tools-mcp"]
    for sid in retained_ids:
        srv = default_mcp_catalog.get_server(sid)
        assert srv is not None
        assert srv.disposition == MCPDisposition.KEEP_AS_MCP
        assert srv.ownership_class == MCPOwnershipClass.RUNTIME_CONTROL
        assert srv.allowed_for_production is True
        assert srv.enabled is True
        assert len(srv.operations) > 0


def test_migrated_domain_mcp_servers_configuration():
    """Migrated servers (common-tools-mcp, media-sources-mcp) must NOT be allowed for direct production AI."""
    common_srv = default_mcp_catalog.get_server("common-tools-mcp")
    assert common_srv is not None
    assert common_srv.disposition == MCPDisposition.CONVERT_TO_DOMAIN_SERVICE
    assert common_srv.ownership_class == MCPOwnershipClass.DEV_ONLY
    assert common_srv.allowed_for_production is False

    media_srv = default_mcp_catalog.get_server("media-sources-mcp")
    assert media_srv is not None
    assert media_srv.disposition == MCPDisposition.CONVERT_TO_DOMAIN_SERVICE
    assert media_srv.ownership_class == MCPOwnershipClass.DEV_ONLY
    assert media_srv.allowed_for_production is False


def test_deprecated_mcp_server_configuration():
    """Deprecated legacy node server must be strictly quarantined from production AI."""
    ffmpeg_srv = default_mcp_catalog.get_server("ffmpeg-mcp-server")
    assert ffmpeg_srv is not None
    assert ffmpeg_srv.disposition == MCPDisposition.DEPRECATE
    assert ffmpeg_srv.ownership_class == MCPOwnershipClass.DEV_ONLY
    assert ffmpeg_srv.allowed_for_production is False
    assert ffmpeg_srv.enabled is False


def test_production_filtering():
    """list_servers with production_only=True must strictly return only retained production servers."""
    prod_servers = default_mcp_catalog.list_servers(production_only=True)
    prod_ids = [s.server_id for s in prod_servers]
    assert prod_ids == ["audio-tools-mcp", "image-tools-mcp", "video-tools-mcp"]


def test_is_operation_allowed():
    """is_operation_allowed verifies allowed operations and rejects unapproved/deprecated ones."""
    # Retained operations allowed in production
    assert default_mcp_catalog.is_operation_allowed("audio-tools-mcp", "trim_audio", is_production=True) is True
    assert default_mcp_catalog.is_operation_allowed("video-tools-mcp", "resize_video", is_production=True) is True
    assert default_mcp_catalog.is_operation_allowed("image-tools-mcp", "upscale_image", is_production=True) is True

    # Unknown operation on retained server
    assert default_mcp_catalog.is_operation_allowed("audio-tools-mcp", "delete_hard_drive", is_production=True) is False

    # Operations on servers not allowed for production
    assert default_mcp_catalog.is_operation_allowed("common-tools-mcp", "check_cache", is_production=True) is False
    assert default_mcp_catalog.is_operation_allowed("media-sources-mcp", "change_asset_status", is_production=True) is False
    assert default_mcp_catalog.is_operation_allowed("ffmpeg-mcp-server", "concatenate_videos", is_production=True) is False


def test_get_operation_metadata():
    """get_operation retrieves accurate operation contracts and categories."""
    op = default_mcp_catalog.get_operation("audio-tools-mcp", "normalize_loudness")
    assert op is not None
    assert op.name == "normalize_loudness"
    assert op.category == MCPOperationCategory.AUDIO_PROCESSING
    assert op.timeout_seconds == 30.0
    assert op.allow_shell is False
    assert op.allow_arbitrary_fs is False
    assert op.requires_tenant_scope is True


def test_unknown_server_lookup_returns_none():
    """Querying an unknown server returns None."""
    assert default_mcp_catalog.get_server("nonexistent-mcp-server") is None
    assert default_mcp_catalog.get_operation("nonexistent-mcp-server", "some_tool") is None
