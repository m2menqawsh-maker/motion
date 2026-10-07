"""
tests/ai/contracts/test_contracts_invalid.py
============================================
Verifies that canonical contracts strictly reject invalid inputs:
- Extra forbidden fields (extra = "forbid")
- Missing mandatory fields
- Type mismatches (strict = True)
- Unknown enum variants
- Naive datetimes lacking timezone offsets
- Negative monetary quantities
"""

from __future__ import annotations

from datetime import datetime
import pytest
from pydantic import ValidationError

from ai.contracts import (
    AIError,
    AIRequest,
    AIResponse,
    AIRun,
    AIStep,
    CapabilityRequest,
    CapabilityResult,
    CostEstimate,
    MediaIntelligenceRef,
    MemoryQuery,
    ModelRequirement,
    ModelSelection,
    ProvenanceRecord,
    ToolCall,
    ToolResult,
    UsageRecord,
)
from tests.ai.contracts.fixtures import get_valid_fixtures


class TestInvalidContracts:

    def test_extra_field_rejected(self):
        """Strict policy: extra fields must fail validation at ingress boundaries."""
        f = get_valid_fixtures()["AIRequest_minimal"].copy()
        f["unexpected_extra_field"] = "malicious_or_hallucinated"
        with pytest.raises(ValidationError) as exc_info:
            AIRequest.model_validate(f)
        assert "extra_forbidden" in str(exc_info.value)

    def test_missing_mandatory_field_rejected(self):
        """Mandatory fields (e.g. request_id, workspace_id) cannot be omitted."""
        f = get_valid_fixtures()["AIRequest_minimal"].copy()
        del f["workspace_id"]
        with pytest.raises(ValidationError) as exc_info:
            AIRequest.model_validate(f)
        assert "Field required" in str(exc_info.value)

    def test_unknown_enum_rejected(self):
        """Unknown enum variants cannot be coerced or accepted."""
        f = get_valid_fixtures()["AIRequest_minimal"].copy()
        f["capability"] = "UNKNOWN_CAPABILITY_XYZ"
        with pytest.raises(ValidationError) as exc_info:
            AIRequest.model_validate(f)
        assert "Input should be" in str(exc_info.value)

    def test_wrong_primitive_type_rejected(self):
        """Strict typing rejects mismatched primitives (e.g. string for integer attempt)."""
        f = get_valid_fixtures()["AIStep_valid"].copy()
        f["attempt"] = "first_attempt"
        with pytest.raises(ValidationError):
            AIStep.model_validate(f)

    def test_naive_datetime_rejected(self):
        """Timestamps without timezone offsets must be rejected."""
        f = get_valid_fixtures()["AIRequest_minimal"].copy()
        f["created_at"] = "2026-09-30T17:00:00"  # Missing Z or UTC offset
        with pytest.raises(ValidationError) as exc_info:
            AIRequest.model_validate(f)
        assert "timezone-aware" in str(exc_info.value)

    def test_naive_datetime_object_rejected(self):
        """Python naive datetime object must be rejected."""
        f = get_valid_fixtures()["ProvenanceRecord_valid"].copy()
        f["timestamp"] = datetime(2026, 9, 30, 17, 0, 0)
        with pytest.raises(ValidationError) as exc_info:
            ProvenanceRecord.model_validate(f)
        assert "timezone-aware" in str(exc_info.value)

    def test_negative_cost_rejected(self):
        """Monetary values cannot be negative."""
        with pytest.raises(ValidationError):
            CostEstimate(estimated_cost="-1.50")

    def test_negative_token_count_rejected(self):
        """Token counts cannot be negative."""
        with pytest.raises(ValidationError):
            UsageRecord(input_tokens=-10)

    def test_negative_attempt_rejected(self):
        """AIStep attempt must be >= 1."""
        f = get_valid_fixtures()["AIStep_valid"].copy()
        f["attempt"] = 0
        with pytest.raises(ValidationError):
            AIStep.model_validate(f)

    def test_negative_latency_rejected(self):
        """Latency in ProvenanceRecord must be >= 0."""
        f = get_valid_fixtures()["ProvenanceRecord_valid"].copy()
        f["latency_ms"] = -5
        with pytest.raises(ValidationError):
            ProvenanceRecord.model_validate(f)

    def test_invalid_currency_code_rejected(self):
        """Currency must match ISO 4217 3-letter code format."""
        with pytest.raises(ValidationError):
            CostEstimate(estimated_cost="1.00", currency="dollar")
