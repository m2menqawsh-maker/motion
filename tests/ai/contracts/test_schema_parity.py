"""
tests/ai/contracts/test_schema_parity.py
========================================
Cross-Language Parity Gate:
Verifies that payloads accepted by Python Pydantic models are also accepted by the
generated JSON Schemas (Draft 2020-12), and invalid payloads are rejected consistently.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

from tests.ai.contracts.fixtures import get_valid_fixtures

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCHEMA_DIR = ROOT / "schemas" / "ai"


def load_schema(schema_name: str) -> dict:
    path = SCHEMA_DIR / f"{schema_name}.schema.json"
    assert path.exists(), f"Schema file missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


class TestSchemaParity:

    @pytest.mark.parametrize(
        "fixture_key,schema_name",
        [
            ("UsageRecord_full", "usage_record"),
            ("CostEstimate_full", "cost_estimate"),
            ("AIError_full", "ai_error"),
            ("ModelRequirement_full", "model_requirement"),
            ("ModelSelection_valid", "model_selection"),
            ("CapabilityRequest_valid", "capability_request"),
            ("CapabilityResult_success", "capability_result"),
            ("ToolCall_valid", "tool_call"),
            ("ToolResult_success", "tool_result"),
            ("MemoryQuery_valid", "memory_query"),
            ("MemoryResult_valid", "memory_result"),
            ("MediaIntelligenceRef_valid", "media_intelligence_ref"),
            ("AIRequest_full", "ai_request"),
            ("AIResponse_success", "ai_response"),
            ("AIRun_valid", "ai_run"),
            ("AIStep_valid", "ai_step"),
        ],
    )
    def test_valid_fixtures_pass_json_schema(self, fixture_key: str, schema_name: str):
        """All canonical valid fixtures must validate cleanly against their generated JSON Schemas."""
        fixtures = get_valid_fixtures()
        assert fixture_key in fixtures, f"Fixture {fixture_key} not found"
        payload = fixtures[fixture_key]

        schema = load_schema(schema_name)
        validator = Draft202012Validator(schema)

        errors = list(validator.iter_errors(payload))
        assert not errors, f"JSON Schema validation failed for {fixture_key} against {schema_name}:\n" + "\n".join(
            f"  • {e.json_path}: {e.message}" for e in errors
        )

    def test_json_schema_rejects_extra_fields(self):
        """JSON Schema enforces additionalProperties: false (matching Pydantic extra='forbid')."""
        payload = get_valid_fixtures()["AIRequest_minimal"].copy()
        payload["unauthorized_injected_key"] = "test"

        schema = load_schema("ai_request")
        validator = Draft202012Validator(schema)

        errors = list(validator.iter_errors(payload))
        assert len(errors) >= 1
        assert any("unauthorized_injected_key" in e.message for e in errors)

    def test_json_schema_rejects_missing_required_field(self):
        """JSON Schema enforces required properties."""
        payload = get_valid_fixtures()["AIRequest_minimal"].copy()
        del payload["request_id"]

        schema = load_schema("ai_request")
        validator = Draft202012Validator(schema)

        errors = list(validator.iter_errors(payload))
        assert len(errors) >= 1
        assert any("request_id" in e.message for e in errors)

    def test_json_schema_rejects_unknown_enum(self):
        """JSON Schema enforces enum membership."""
        payload = get_valid_fixtures()["AIRequest_minimal"].copy()
        payload["capability"] = "NOT_A_REAL_CAPABILITY"

        schema = load_schema("ai_request")
        validator = Draft202012Validator(schema)

        errors = list(validator.iter_errors(payload))
        assert len(errors) >= 1
