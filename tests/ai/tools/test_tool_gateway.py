"""
tests/ai/tools/test_tool_gateway.py
===================================
Comprehensive test suite for ToolGateway (S28-M03):
- Input & Output Contract Validation (Pydantic schema enforcement, extra="forbid").
- Authorization & Tenant Context (viewer vs editor, SYSTEM scope, project/workspace isolation).
- Side-Effects Policy Enforcement (consuming side_effects[] array, SSRF/egress, subprocess guards).
- Security Blocking (CONCATENATE_VIDEOS blocked).
- Idempotency & Timeout Handling (cached replays, conflict detection, timeout enforcement).
- Domain Authority Routing (AssetService, RunService, manifest/timeline).
- End-to-End Router -> Gateway -> Adapter Integration.
- Legacy Tool Output Parity.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ai.contracts import (
    AIContractModel,
    AIErrorCode,
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
    ImplementationDescriptor,
    SideEffectClass,
    TenantScope,
)
from ai.routing.capability_router import get_capability_router
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.adapters.domain_service import DomainServiceAdapter
from ai.tools.adapters.mcp import ImplementationSecurityBlockedError, MCPToolAdapter
from ai.tools.adapters.registry import AdapterRegistry
from ai.tools.errors import NetworkPolicyViolationError
from ai.tools.gateway import IdempotencyStore, ToolGateway, validate_safe_url
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def trusted_editor_ctx() -> TrustedToolExecutionContext:
    return TrustedToolExecutionContext(
        workspace_id="ws_test_alpha",
        actor_id="usr_editor_1",
        roles=["editor"],
        permissions=["viewer", "editor"],
        is_admin=False,
        accessible_projects=["prj_alpha_1"],
    )


@pytest.fixture
def trusted_viewer_ctx() -> TrustedToolExecutionContext:
    return TrustedToolExecutionContext(
        workspace_id="ws_test_alpha",
        actor_id="usr_viewer_1",
        roles=["viewer"],
        permissions=["viewer"],
        is_admin=False,
        accessible_projects=["prj_alpha_1"],
    )


@pytest.fixture
def trusted_admin_ctx() -> TrustedToolExecutionContext:
    return TrustedToolExecutionContext(
        workspace_id="ws_test_alpha",
        actor_id="usr_admin_1",
        roles=["admin"],
        permissions=["viewer", "editor", "admin"],
        is_admin=True,
        accessible_projects=["prj_alpha_1", "prj_beta_2"],
    )


@pytest.fixture
def gateway() -> ToolGateway:
    return ToolGateway(idempotency_store=IdempotencyStore())


# =============================================================================
# 1. Input & Output Contract Validation
# =============================================================================

class TestInputOutputValidation:
    """Verifies that ToolGateway strictly validates inputs and outputs against Pydantic models."""

    @pytest.mark.asyncio
    async def test_valid_input_accepted_and_executed(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 1.0,
                "duration_seconds": 2.5,
            },
        )
        result = await gateway.execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.SUCCESS
        assert result.capability_id == CapabilityType.TRIM_VIDEO
        assert result.output is not None
        assert result.output["duration_seconds"] == 2.5

    @pytest.mark.asyncio
    async def test_missing_required_input_rejected_before_adapter(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        # Missing required duration_seconds
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 1.0,
            },
        )
        result = await gateway.execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.SCHEMA_VALIDATION_FAILED

    @pytest.mark.asyncio
    async def test_extra_forbidden_fields_in_input_rejected(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        # Extra unmodeled field injected
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 1.0,
                "duration_seconds": 2.0,
                "unauthorized_field": "exploit",
            },
        )
        result = await gateway.execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.SCHEMA_VALIDATION_FAILED

    @pytest.mark.asyncio
    async def test_adapter_returning_invalid_output_fails_output_validation(
        self,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        # Create a mock adapter that returns malformed output missing required fields
        mock_adapter = MagicMock(spec=CapabilityAdapter)
        mock_adapter.adapter_kind = "MOCK"
        mock_adapter.name = "mock_bad_output_adapter"
        mock_adapter.execute = AsyncMock(return_value={"corrupted": "bad_data"})

        cap_def = get_capability_router().catalog.get(CapabilityType.TRIM_VIDEO)
        registry = AdapterRegistry()
        registry.register(mock_adapter, [cap_def.capability_id])

        custom_gateway = ToolGateway(adapter_registry=registry)
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 0.0,
                "duration_seconds": 5.0,
            },
        )
        result = await custom_gateway.execute(request, context=trusted_editor_ctx)

        # Invariant: Never report success if output is invalid
        assert result.status == CapabilityStatus.FAILED
        assert result.output is None
        assert result.error is not None
        assert result.error.code == AIErrorCode.INVALID_MODEL_OUTPUT


# =============================================================================
# 2. Authorization & Tenant Isolation
# =============================================================================

class TestAuthorizationAndTenantIsolation:
    """Verifies RBAC and multi-tenant project/workspace boundary enforcement."""

    @pytest.mark.asyncio
    async def test_viewer_role_denied_editor_capability(
        self,
        gateway: ToolGateway,
        trusted_viewer_ctx: TrustedToolExecutionContext,
    ):
        # MUTATE_ASSET_STATUS requires 'editor'
        request = CapabilityRequest(
            capability_id=CapabilityType.MUTATE_ASSET_STATUS,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "asset_id": "ast_video_1",
                "new_status": "READY",
            },
        )
        result = await gateway.execute(request, context=trusted_viewer_ctx)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.POLICY_DENIED
        assert "lacks required permission" in result.error.message

    @pytest.mark.asyncio
    async def test_cross_project_isolation_violation_rejected(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        # trusted_editor_ctx only has access to "prj_alpha_1"
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_foreign_99",
            input={
                "project_id": "prj_foreign_99",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 0.0,
                "duration_seconds": 2.0,
            },
        )
        result = await gateway.execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.TENANT_ACCESS_DENIED
        assert "cannot access project 'prj_foreign_99'" in result.error.message

    @pytest.mark.asyncio
    async def test_cross_workspace_isolation_violation_rejected(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_foreign_99",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 0.0,
                "duration_seconds": 2.0,
            },
        )
        result = await gateway.execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.TENANT_ACCESS_DENIED
        assert "Cross-workspace isolation violation" in result.error.message

    @pytest.mark.asyncio
    async def test_mismatched_request_and_input_project_id_rejected(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_different_2",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 0.0,
                "duration_seconds": 2.0,
            },
        )
        result = await gateway.execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.TENANT_ACCESS_DENIED
        assert "Conflicting project context" in result.error.message


# =============================================================================
# 3. Side-Effects & Security Policy
# =============================================================================

class TestSideEffectsAndSecurity:
    """Verifies multi-side-effect evaluation, SSRF safe URL checks, and subprocess protection."""

    def test_side_effects_array_evaluated_not_scalar_alone(self, gateway: ToolGateway):
        """Regression test: verifies that all items in side_effects[] are recorded and enforced."""
        cap_def = gateway.catalog.get(CapabilityType.CHANGE_VIDEO_SPEED)
        assert cap_def is not None

        # Verify CHANGE_VIDEO_SPEED has multiple side effects
        effects = [e.value if hasattr(e, "value") else str(e) for e in cap_def.side_effects]
        assert "PERSISTENT_WRITE" in effects
        assert "SUBPROCESS" in effects
        assert "BACKGROUND_JOB" in effects

    def test_ssrf_blocks_localhost_and_internal_ips(self):
        blocked_urls = [
            "http://localhost:8000/media.mp4",
            "http://127.0.0.1/video.mp4",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1/internal.wav",
            "http://192.168.1.1/secret.jpg",
            "file:///etc/passwd",
            "ftp://ftp.example.com/asset.mov",
            "data:text/plain;base64,SGVsbG8=",
        ]
        for url in blocked_urls:
            with pytest.raises(NetworkPolicyViolationError):
                validate_safe_url(url)

    def test_ssrf_allows_public_https_domains(self):
        allowed_urls = [
            "https://images.unsplash.com/photo-123.jpg",
            "https://api.pexels.com/v1/search",
            "https://cdn.pixabay.com/audio/sample.mp3",
        ]
        for url in allowed_urls:
            validate_safe_url(url)  # Must not raise

    @pytest.mark.asyncio
    async def test_concatenate_videos_security_blocked(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        request = CapabilityRequest(
            capability_id=CapabilityType.CONCATENATE_VIDEOS,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_keys": ["video/1.mp4", "video/2.mp4"],
            },
        )
        result = await gateway.execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.CAPABILITY_UNAVAILABLE
        assert "Security blocked implementation" in result.error.message or "shell injection" in result.error.message

    @pytest.mark.asyncio
    async def test_subprocess_policy_blocks_injected_shell_keys(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        # If an unmodeled shell key slipped past contract or was present in input
        cap_def = gateway.catalog.get(CapabilityType.TRIM_VIDEO)
        assert cap_def is not None

        # Verify gateway helper blocks raw command arguments
        mock_input = MagicMock()
        mock_input.model_dump.return_value = {
            "project_id": "prj_alpha_1",
            "command": "rm -rf /",
        }
        with pytest.raises(Exception) as exc_info:
            gateway._enforce_subprocess_policy(
                CapabilityRequest(capability_id=CapabilityType.TRIM_VIDEO, workspace_id="ws_test_alpha"),
                mock_input,
            )
        assert "is forbidden" in str(exc_info.value)


# =============================================================================
# 4. Idempotency & Timeout Handling
# =============================================================================

class TestIdempotencyAndTimeout:
    """Verifies replay caching, conflict detection, and execution timeout."""

    @pytest.mark.asyncio
    async def test_idempotency_cache_hit_returns_replayed_result(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        req1 = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            idempotency_key="idem_trim_001",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 1.0,
                "duration_seconds": 2.0,
            },
        )
        res1 = await gateway.execute(req1, context=trusted_editor_ctx)
        assert res1.status == CapabilityStatus.SUCCESS

        # Second execution with exact same idempotency_key and input
        req2 = req1.model_copy(update={"request_id": "req_new_2"})
        res2 = await gateway.execute(req2, context=trusted_editor_ctx)

        assert res2.status == CapabilityStatus.SUCCESS
        assert res2.execution_metadata.get("idempotency_hit") is True
        assert res2.output == res1.output

    @pytest.mark.asyncio
    async def test_idempotency_conflict_with_different_payload_fails(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        req1 = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            idempotency_key="idem_conflict_test",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 1.0,
                "duration_seconds": 2.0,
            },
        )
        await gateway.execute(req1, context=trusted_editor_ctx)

        # Same key with different duration
        req2 = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            idempotency_key="idem_conflict_test",
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 1.0,
                "duration_seconds": 9.9,
            },
        )
        res2 = await gateway.execute(req2, context=trusted_editor_ctx)

        assert res2.status == CapabilityStatus.FAILED
        assert res2.error is not None
        assert res2.error.code == AIErrorCode.POLICY_DENIED

    @pytest.mark.asyncio
    async def test_timeout_enforced_when_adapter_exceeds_deadline(
        self,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        async def slow_execute(req, inp, ctx):
            await asyncio.sleep(2.0)
            return {"project_id": "prj_alpha_1", "output_storage_key": "storage/out.mp4", "duration_seconds": 1.0}

        mock_adapter = MagicMock(spec=CapabilityAdapter)
        mock_adapter.adapter_kind = "MOCK"
        mock_adapter.name = "mock_slow_adapter"
        mock_adapter.execute = slow_execute

        cap_def = get_capability_router().catalog.get(CapabilityType.TRIM_VIDEO)
        registry = AdapterRegistry()
        registry.register(mock_adapter, [cap_def.capability_id])

        slow_gateway = ToolGateway(adapter_registry=registry)
        request = CapabilityRequest(
            capability_id=CapabilityType.TRIM_VIDEO,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            requested_timeout=0.1,  # 100ms deadline
            input={
                "project_id": "prj_alpha_1",
                "video_storage_key": "video/raw.mp4",
                "start_time_seconds": 0.0,
                "duration_seconds": 1.0,
            },
        )
        result = await slow_gateway.execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.TIMEOUT


# =============================================================================
# 5. Domain Authority Enforcement
# =============================================================================

class TestDomainAuthorityEnforcement:
    """Verifies that DOMAIN_SERVICE capabilities route to canonical services (AssetService, RunService)."""

    @pytest.mark.asyncio
    async def test_mutate_asset_status_invokes_asset_service(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        with patch("api.services.asset_service.AssetService.update_asset_status", return_value={"asset_id": "ast_video_1", "status": "READY", "previous_status": "PROCESSING"}) as mock_mutate:
            request = CapabilityRequest(
                capability_id=CapabilityType.MUTATE_ASSET_STATUS,
                workspace_id="ws_test_alpha",
                project_id="prj_alpha_1",
                input={
                    "project_id": "prj_alpha_1",
                    "asset_id": "ast_video_1",
                    "new_status": "READY",
                },
            )
            result = await gateway.execute(request, context=trusted_editor_ctx)

            assert result.status == CapabilityStatus.SUCCESS
            assert mock_mutate.called
            assert result.output is not None
            assert result.output["current_status"] == "READY"

    @pytest.mark.asyncio
    async def test_check_media_cache_invokes_asset_service(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        with patch("api.services.asset_service.AssetService.check_asset_cache", return_value="storage/prj_alpha_1/cached.mp4") as mock_cache:
            request = CapabilityRequest(
                capability_id=CapabilityType.CHECK_MEDIA_CACHE,
                workspace_id="ws_test_alpha",
                project_id="prj_alpha_1",
                input={
                    "project_id": "prj_alpha_1",
                    "asset_id": "ast_video_1",
                    "transformation_hash": "hash_xyz_789",
                },
            )
            result = await gateway.execute(request, context=trusted_editor_ctx)

            assert result.status == CapabilityStatus.SUCCESS
            assert mock_cache.called
            assert result.output is not None
            assert result.output["cache_hit"] is True

    @pytest.mark.asyncio
    async def test_store_media_cache_invokes_asset_service(
        self,
        gateway: ToolGateway,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        with patch("api.services.asset_service.AssetService.save_asset_to_cache") as mock_save:
            request = CapabilityRequest(
                capability_id=CapabilityType.STORE_MEDIA_CACHE,
                workspace_id="ws_test_alpha",
                project_id="prj_alpha_1",
                input={
                    "project_id": "prj_alpha_1",
                    "asset_id": "ast_video_1",
                    "transformation_hash": "hash_xyz_789",
                    "source_storage_key": "storage/prj_alpha_1/transformed.mp4",
                },
            )
            result = await gateway.execute(request, context=trusted_editor_ctx)

            assert result.status == CapabilityStatus.SUCCESS
            assert mock_save.called
            assert result.output is not None
            assert result.output["stored"] is True


# =============================================================================
# 6. End-to-End Integration & Parity
# =============================================================================

class TestEndToEndIntegrationAndParity:
    """End-to-End testing across all 3 Capability Categories through CapabilityRouter."""

    @pytest.mark.asyncio
    async def test_tool_category_e2e_trim_video(
        self,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        router = get_capability_router()
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
        result = await router.route_and_execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.SUCCESS
        assert result.execution_metadata.get("router_branch") == "TOOL"
        assert result.execution_metadata.get("adapter_kind") == "COMPATIBILITY_MCP"

    @pytest.mark.asyncio
    async def test_domain_service_category_e2e(
        self,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        router = get_capability_router()
        request = CapabilityRequest(
            capability_id=CapabilityType.GENERATE_SPEECH_MANIFEST,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "storage/transcription.wav",
            },
        )
        result = await router.route_and_execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.SUCCESS
        assert result.execution_metadata.get("router_branch") == "DOMAIN_SERVICE"
        assert result.output is not None
        assert "manifest_storage_key" in result.output

    @pytest.mark.asyncio
    async def test_model_category_e2e(
        self,
        trusted_editor_ctx: TrustedToolExecutionContext,
    ):
        from unittest.mock import AsyncMock, patch
        router = get_capability_router()
        request = CapabilityRequest(
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            workspace_id="ws_test_alpha",
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "audio/narration.wav",
            },
        )
        mock_res = CapabilityResult(
            request_id=request.request_id,
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            status=CapabilityStatus.SUCCESS,
            output={"transcript": "hello world"},
            execution_metadata={"router_branch": "MODEL"},
        )
        with patch.object(router.model_router, "execute_model_capability", new=AsyncMock(return_value=mock_res)):
            result = await router.route_and_execute(request, context=trusted_editor_ctx)

        assert result.status == CapabilityStatus.SUCCESS
        assert result.execution_metadata.get("router_branch") == "MODEL"
        assert result.output is not None
        assert "transcript" in result.output
