"""
tests/ai/contracts/test_semantic_invariants.py
==============================================
Validates semantic domain invariants across all canonical AI contracts:
- Timestamp chronology (completed_at >= started_at >= created_at)
- State coherence (SUCCEEDED must not have error; FAILED must have error)
- Model routing consistency (primary model cannot duplicate in fallbacks)
- Tool call security isolation (model parameters cannot inject identity tokens)
- Media storage abstraction (storage_key cannot be a raw host path)
- Usage accounting arithmetic (total_tokens == input_tokens + output_tokens)
- Public error sanitization (credential patterns are rejected)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai.contracts import (
    AIError,
    AIErrorCode,
    AIResponse,
    AIRun,
    AIStep,
    CapabilityResult,
    CapabilityStatus,
    CostEstimate,
    MediaIntelligenceRef,
    ModelSelection,
    ToolCall,
    ToolResult,
    UsageRecord,
)
from tests.ai.contracts.fixtures import get_valid_fixtures

PAST_ISO = "2026-09-30T16:00:00Z"
BASE_ISO = "2026-09-30T17:00:00Z"
FUTURE_ISO = "2026-09-30T18:00:00Z"


class TestSemanticInvariants:

    def test_chronology_completed_before_started_rejected(self):
        """completed_at cannot precede started_at."""
        f = get_valid_fixtures()["AIStep_valid"].copy()
        f["started_at"] = FUTURE_ISO
        f["completed_at"] = BASE_ISO  # Earlier than started_at
        with pytest.raises(ValidationError) as exc_info:
            AIStep.model_validate(f)
        assert "cannot precede started_at" in str(exc_info.value)

    def test_chronology_started_before_created_rejected(self):
        """started_at cannot precede created_at."""
        f = get_valid_fixtures()["AIRun_valid"].copy()
        f["created_at"] = BASE_ISO
        f["started_at"] = PAST_ISO  # Earlier than created_at
        with pytest.raises(ValidationError) as exc_info:
            AIRun.model_validate(f)
        assert "cannot precede created_at" in str(exc_info.value)

    def test_tool_result_chronology_rejected(self):
        """ToolResult completed_at must not precede started_at."""
        f = get_valid_fixtures()["ToolResult_success"].copy()
        f["started_at"] = FUTURE_ISO
        f["completed_at"] = BASE_ISO
        with pytest.raises(ValidationError) as exc_info:
            ToolResult.model_validate(f)
        assert "must not precede started_at" in str(exc_info.value)

    def test_response_succeeded_with_error_rejected(self):
        """AIResponse with status SUCCEEDED cannot hold an error."""
        f = get_valid_fixtures()["AIResponse_success"].copy()
        f["error"] = {
            "code": "INTERNAL_ERROR",
            "message": "Contradictory error",
            "retryable": False,
        }
        with pytest.raises(ValidationError) as exc_info:
            AIResponse.model_validate(f)
        assert "cannot contain an error" in str(exc_info.value)

    def test_response_failed_without_error_rejected(self):
        """AIResponse with status FAILED must provide a structured error."""
        f = get_valid_fixtures()["AIResponse_failed"].copy()
        f["error"] = None
        with pytest.raises(ValidationError) as exc_info:
            AIResponse.model_validate(f)
        assert "must provide a structured error" in str(exc_info.value)

    def test_capability_result_status_coherence(self):
        """CapabilityResult SUCCESS must have output and no error; FAILED must have error."""
        # SUCCESS with error
        f_succ = get_valid_fixtures()["CapabilityResult_success"].copy()
        f_succ["error"] = {"code": "INTERNAL_ERROR", "message": "Failed", "retryable": False}
        with pytest.raises(ValidationError) as exc_info:
            CapabilityResult.model_validate(f_succ)
        assert "cannot contain an error" in str(exc_info.value)

        # FAILED without error
        f_fail = get_valid_fixtures()["CapabilityResult_failed"].copy()
        f_fail["error"] = None
        with pytest.raises(ValidationError) as exc_info:
            CapabilityResult.model_validate(f_fail)
        assert "must provide a structured error" in str(exc_info.value)

    def test_model_selection_duplicate_primary_rejected(self):
        """ModelSelection fallbacks cannot contain the primary model."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSelection(
                primary_model="model_alpha",
                fallback_candidates=["model_beta", "model_alpha"],
                reason_code="ROUTING",
                estimated_cost=CostEstimate(estimated_cost="0.01"),
            )
        assert "must not contain primary_model" in str(exc_info.value)

    def test_model_selection_duplicate_fallbacks_rejected(self):
        """ModelSelection fallbacks cannot contain duplicate candidates."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSelection(
                primary_model="model_alpha",
                fallback_candidates=["model_beta", "model_beta"],
                reason_code="ROUTING",
                estimated_cost=CostEstimate(estimated_cost="0.01"),
            )
        assert "duplicate candidate entries" in str(exc_info.value)

    @pytest.mark.parametrize(
        "identity_field",
        ["workspace_id", "actor_id", "user_id", "approved_by", "permission", "role", "tenant_id"],
    )
    def test_tool_call_identity_injection_rejected(self, identity_field: str):
        """Model output in ToolCall parameters CANNOT specify authoritative identity or permissions."""
        f = get_valid_fixtures()["ToolCall_valid"].copy()
        f["parameters"] = {"prompt": "render image", identity_field: "injected_attacker_id"}
        with pytest.raises(ValidationError) as exc_info:
            ToolCall.model_validate(f)
        assert "Security violation" in str(exc_info.value)
        assert identity_field in str(exc_info.value)

    def test_media_ref_rejects_host_path(self):
        """storage_key in MediaIntelligenceRef cannot be an absolute host filesystem path."""
        f = get_valid_fixtures()["MediaIntelligenceRef_valid"].copy()
        f["storage_key"] = "/var/data/analyses/result.json"
        with pytest.raises(ValidationError) as exc_info:
            MediaIntelligenceRef.model_validate(f)
        assert "abstract storage key, not a host absolute path" in str(exc_info.value)

    def test_media_ref_rejects_traversal(self):
        """storage_key cannot contain path traversal components ('..')."""
        f = get_valid_fixtures()["MediaIntelligenceRef_valid"].copy()
        f["storage_key"] = "storage/../../etc/passwd"
        with pytest.raises(ValidationError) as exc_info:
            MediaIntelligenceRef.model_validate(f)
        assert "path traversal" in str(exc_info.value)

    def test_usage_token_arithmetic_mismatch_rejected(self):
        """total_tokens must equal input_tokens + output_tokens if all are provided."""
        with pytest.raises(ValidationError) as exc_info:
            UsageRecord(input_tokens=100, output_tokens=200, total_tokens=999)
        assert "does not match input_tokens" in str(exc_info.value)

    def test_ai_error_rejects_api_key_leakage(self):
        """AIError rejects public error messages leaking API keys or bearer tokens."""
        with pytest.raises(ValidationError) as exc_info:
            AIError(
                code=AIErrorCode.INTERNAL_ERROR,
                message="Provider failed with sk-live-1234567890abcdef123456",
                retryable=False,
            )
        assert "potentially sensitive credential" in str(exc_info.value)

    def test_ai_error_rejects_bearer_leakage_in_details(self):
        """AIError rejects sensitive bearer tokens inside details dictionary."""
        with pytest.raises(ValidationError) as exc_info:
            AIError(
                code=AIErrorCode.PROVIDER_UNAVAILABLE,
                message="Upstream refused connection",
                retryable=False,
                details={"auth_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"},
            )
        assert "potentially sensitive credential" in str(exc_info.value)
