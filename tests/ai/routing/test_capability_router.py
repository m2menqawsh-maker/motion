"""
tests/ai/routing/test_capability_router.py
==========================================
Comprehensive tests for CapabilityRouter (S28-M03):
- Resolution across all 32 canonical capabilities.
- MODEL category branching to ModelRouterSeam.
- TOOL category branching to ToolGateway.
- DOMAIN_SERVICE category branching to ToolGateway -> DomainServiceAdapter.
- Rejection of unknown capabilities.
- Rejection of caller-controlled MCP server / tool names.
- Rejection of caller-controlled provider names.
- Rejection of caller-controlled shell commands or filesystem paths.
"""

import pytest

from ai.contracts import (
    AIErrorCode,
    CapabilityCategory,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
)
from ai.routing.capability_router import CapabilityRouter, ModelRouterSeam, get_capability_router
from ai.tools.gateway import ToolGateway
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def trusted_context() -> TrustedToolExecutionContext:
    return TrustedToolExecutionContext(
        workspace_id="ws_test_alpha",
        actor_id="user_editor_1",
        roles=["editor"],
        permissions=["viewer", "editor"],
        is_admin=False,
        accessible_projects=["prj_alpha_1"],
    )


@pytest.fixture
def router() -> CapabilityRouter:
    return get_capability_router()


class TestCapabilityRouterResolution:
    """Verifies that all 32 capabilities are recognized and dispatched correctly by category."""

    def test_all_32_capabilities_known_to_router(self, router: CapabilityRouter):
        catalog = router.catalog
        assert catalog.total_count == 32

        categories = {
            CapabilityCategory.MODEL.value: 0,
            CapabilityCategory.TOOL.value: 0,
            CapabilityCategory.DOMAIN_SERVICE.value: 0,
        }
        for cap in catalog.list_all():
            cat = cap.category.value if hasattr(cap.category, "value") else str(cap.category)
            categories[cat] += 1

        assert categories[CapabilityCategory.MODEL.value] == 1
        assert categories[CapabilityCategory.TOOL.value] == 24
        assert categories[CapabilityCategory.DOMAIN_SERVICE.value] == 7

    @pytest.mark.asyncio
    async def test_known_model_capability_routes_to_model_seam(
        self,
        router: CapabilityRouter,
        trusted_context: TrustedToolExecutionContext,
    ):
        request = CapabilityRequest(
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "audio/voiceover.wav",
                "language": "ar",
            },
        )
        result = await router.route_and_execute(request, context=trusted_context)

        assert result.status == CapabilityStatus.SUCCESS
        assert result.capability_id == CapabilityType.SPEECH_TO_TEXT
        assert result.execution_metadata.get("router_branch") == "MODEL"
        assert result.execution_metadata.get("seam") == "ModelRouterSeam"
        assert result.output is not None
        assert result.output.get("language") == "ar"

    @pytest.mark.asyncio
    async def test_known_tool_capability_routes_to_tool_gateway(
        self,
        router: CapabilityRouter,
        trusted_context: TrustedToolExecutionContext,
    ):
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 1.0,
                "duration_seconds": 3.0,
            },
        )
        result = await router.route_and_execute(request, context=trusted_context)

        assert result.status == CapabilityStatus.SUCCESS
        assert result.capability_id == CapabilityType.TRIM_VIDEO
        assert result.execution_metadata.get("adapter_kind") == "COMPATIBILITY_MCP"
        assert result.output is not None
        assert result.output.get("project_id") == "prj_alpha_1"
        assert result.output.get("duration_seconds") == 3.0

    @pytest.mark.asyncio
    async def test_known_domain_service_capability_routes_to_domain_service_adapter(
        self,
        router: CapabilityRouter,
        trusted_context: TrustedToolExecutionContext,
    ):
        request = CapabilityRequest(
            capability_id=CapabilityType.CHECK_MEDIA_CACHE,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "asset_id": "ast_video_1",
                "transformation_hash": "hash_spec_abcdef123",
            },
        )
        result = await router.route_and_execute(request, context=trusted_context)

        assert result.status == CapabilityStatus.SUCCESS
        assert result.capability_id == CapabilityType.CHECK_MEDIA_CACHE
        assert result.execution_metadata.get("adapter_kind") == "DOMAIN_SERVICE"
        assert result.output is not None
        assert result.output.get("project_id") == "prj_alpha_1"
        assert result.output.get("transformation_hash") == "hash_spec_abcdef123"

    @pytest.mark.asyncio
    async def test_unknown_capability_rejected_with_structured_error(
        self,
        router: CapabilityRouter,
        trusted_context: TrustedToolExecutionContext,
    ):
        # Request with unregistered capability
        with pytest.raises(Exception):
            # CapabilityType enum validation rejects unknown capability tokens
            CapabilityRequest(
                capability_id="ARBITRARY_UNKNOWN_TOOL",  # type: ignore
                workspace_id="ws_test_alpha",
            )


class TestArchitecturalDecouplingAndGuards:
    """Verifies that callers cannot pass raw MCP, provider, shell, or filesystem selectors."""

    def test_caller_cannot_supply_adapter_name(self):
        with pytest.raises(ValueError) as exc_info:
            CapabilityRequest(
                capability_id=CapabilityType.TRIM_VIDEO,
                workspace_id="ws_test_alpha",
                input={
                    "project_id": "prj_alpha_1",
                    "video_storage_key": "video/raw.mp4",
                    "adapter_name": "MCPToolAdapter",
                },
            )
        assert "Architectural guard violation" in str(exc_info.value)
        assert "adapter_name" in str(exc_info.value)

    def test_caller_cannot_supply_mcp_server(self):
        with pytest.raises(ValueError) as exc_info:
            CapabilityRequest(
                capability_id=CapabilityType.TRIM_VIDEO,
                workspace_id="ws_test_alpha",
                input={
                    "project_id": "prj_alpha_1",
                    "video_storage_key": "video/raw.mp4",
                    "mcp_server": "video-tools-mcp",
                },
            )
        assert "Architectural guard violation" in str(exc_info.value)
        assert "mcp_server" in str(exc_info.value)

    def test_caller_cannot_supply_provider_name(self):
        with pytest.raises(ValueError) as exc_info:
            CapabilityRequest(
                capability_id=CapabilityType.SEARCH_STOCK_IMAGES,
                workspace_id="ws_test_alpha",
                metadata={"provider_name": "pexels"},
                input={"query": "technology"},
            )
        assert "Architectural guard violation" in str(exc_info.value)
        assert "provider_name" in str(exc_info.value)

    def test_caller_cannot_supply_shell_command(self):
        with pytest.raises(ValueError) as exc_info:
            CapabilityRequest(
                capability_id=CapabilityType.TRIM_VIDEO,
                workspace_id="ws_test_alpha",
                input={
                    "project_id": "prj_alpha_1",
                    "video_storage_key": "video/raw.mp4",
                    "shell_command": "ffmpeg -i raw.mp4 out.mp4",
                },
            )
        assert "Architectural guard violation" in str(exc_info.value)
        assert "shell_command" in str(exc_info.value)

    def test_caller_cannot_supply_filesystem_path(self):
        with pytest.raises(ValueError) as exc_info:
            CapabilityRequest(
                capability_id=CapabilityType.TRIM_VIDEO,
                workspace_id="ws_test_alpha",
                input={
                    "project_id": "prj_alpha_1",
                    "video_storage_key": "video/raw.mp4",
                    "filesystem_path": "/var/data/raw.mp4",
                },
            )
        assert "Architectural guard violation" in str(exc_info.value)
        assert "filesystem_path" in str(exc_info.value)
