"""
tests/ai/audio_modernization/test_tenant_isolation.py
=====================================================
Tenant isolation test suite for S28-M07 audio modernization.
Verifies cross-tenant boundaries, project confinement, and fail-closed denial.
"""

import pytest

from ai.contracts import CapabilityRequest, CapabilityStatus, CapabilityType
from ai.contracts.errors import AIErrorCode
from ai.contracts.media_ops import (
    AnalyzeLoudnessInput,
    DetectSilenceInput,
    NormalizeAudioInput,
)
from ai.media_processing.errors import MediaSourceUnauthorizedError
from ai.media_processing.security import (
    ProtocolSecurityViolationError,
    validate_storage_key_confinement,
)
from ai.tools.gateway import ToolGateway
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def tenant_alpha_ctx():
    return TrustedToolExecutionContext(
        workspace_id="ws_tenant_alpha",
        actor_id="usr_alpha_editor",
        roles=["editor"],
        permissions=["editor", "viewer"],
        accessible_projects=["prj_alpha_1"],
    )


@pytest.fixture
def tenant_beta_ctx():
    return TrustedToolExecutionContext(
        workspace_id="ws_tenant_beta",
        actor_id="usr_beta_editor",
        roles=["editor"],
        permissions=["editor", "viewer"],
        accessible_projects=["prj_beta_1"],
    )


class TestTenantIsolation:
    """Test suite ensuring tenant separation across modernized audio tools."""

    def test_storage_key_confinement_blocks_cross_project(self):
        # Key belonging to prj_beta_1 when project_id is prj_alpha_1
        foreign_key = "workspaces/ws_tenant_beta/projects/prj_beta_1/audio/secret.wav"
        with pytest.raises((MediaSourceUnauthorizedError, ProtocolSecurityViolationError)) as exc_info:
            validate_storage_key_confinement(foreign_key, project_id="prj_alpha_1")
        assert "prj_beta_1" in str(exc_info.value) or "prj_alpha_1" in str(exc_info.value)

    def test_storage_key_confinement_blocks_directory_traversal(self):
        traversal_key = "projects/prj_alpha_1/../../etc/passwd"
        with pytest.raises(ProtocolSecurityViolationError):
            validate_storage_key_confinement(traversal_key, project_id="prj_alpha_1")

    @pytest.mark.asyncio
    async def test_tool_gateway_blocks_cross_project_execution(self, tenant_alpha_ctx):
        gateway = ToolGateway()

        # Actor from Alpha attempts to run NORMALIZE_AUDIO on project prj_beta_1
        request = CapabilityRequest(
            capability_id=CapabilityType.NORMALIZE_AUDIO,
            workspace_id="ws_tenant_alpha",
            project_id="prj_beta_1",  # Not accessible to tenant_alpha_ctx
            input={
                "project_id": "prj_beta_1",
                "audio_storage_key": "storage/prj_beta_1/audio.wav",
                "target_lufs": -16.0,
            },
        )
        result = await gateway.execute(request, context=tenant_alpha_ctx)

        # Must fail-closed on authorization
        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code in (
            AIErrorCode.TENANT_ACCESS_DENIED,
            AIErrorCode.POLICY_DENIED,
            AIErrorCode.SCHEMA_VALIDATION_FAILED,
        )

    @pytest.mark.asyncio
    async def test_analyze_loudness_blocks_unauthorized_tenant(self, tenant_alpha_ctx):
        gateway = ToolGateway()
        request = CapabilityRequest(
            capability_id=CapabilityType.ANALYZE_LOUDNESS,
            workspace_id="ws_tenant_alpha",
            project_id="prj_beta_unauthorized",
            input={
                "project_id": "prj_beta_unauthorized",
                "audio_storage_key": "storage/prj_beta_unauthorized/audio.wav",
            },
        )
        result = await gateway.execute(request, context=tenant_alpha_ctx)
        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
