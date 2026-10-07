"""
tests/ai/contracts/test_provider_neutrality.py
==============================================
Enforces the Provider Neutrality Invariant (ADR-004 DEC-06.3):
- Canonical contracts in `ai/contracts/` must never declare vendor-specific fields
  (e.g., openai_*, anthropic_*, gemini_*, elevenlabs_*, fal_*, replicate_*, whisper_*).
- CapabilityType enum values must represent pure domain capabilities, not vendor brands.
- AIRequest input_data and metadata reject provider-specific keys.
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest
from pydantic import ValidationError

from ai.contracts import AIRequest, CapabilityType
from tests.ai.contracts.fixtures import get_valid_fixtures

CONTRACTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ai" / "contracts"

FORBIDDEN_VENDOR_PATTERNS = [
    "openai",
    "anthropic",
    "gemini",
    "elevenlabs",
    "replicate",
    "whisper",
    "chatgpt",
    "claude",
]


class TestProviderNeutrality:

    def test_no_vendor_names_in_capability_type(self):
        """CapabilityType must not embed vendor names in enum values."""
        for member in CapabilityType:
            val_lower = member.value.lower()
            name_lower = member.name.lower()
            for vendor in FORBIDDEN_VENDOR_PATTERNS:
                assert vendor not in val_lower, f"Vendor string '{vendor}' found in CapabilityType.{member.name}"
                assert vendor not in name_lower, f"Vendor string '{vendor}' found in CapabilityType.{member.name}"

    def test_no_vendor_fields_in_contract_ast(self):
        """Scans all AST nodes in ai/contracts/*.py for vendor-prefixed field declarations."""
        py_files = list(CONTRACTS_DIR.glob("*.py"))
        assert len(py_files) >= 10, "Expected at least 10 contract modules in ai/contracts/"

        violations = []
        for py_file in py_files:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                # Check class attribute definitions (field annotations)
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    field_name = node.target.id.lower()
                    for vendor in FORBIDDEN_VENDOR_PATTERNS:
                        if field_name.startswith(f"{vendor}_") or field_name == vendor:
                            violations.append((py_file.name, node.lineno, field_name))

        assert not violations, f"Vendor-specific fields declared in canonical contracts: {violations}"

    @pytest.mark.parametrize(
        "vendor_field",
        [
            "openai_model",
            "anthropic_version",
            "gemini_config",
            "elevenlabs_voice_settings",
            "fal_seedance_params",
            "replicate_version",
            "whisper_temperature",
        ],
    )
    def test_ai_request_rejects_vendor_input_data(self, vendor_field: str):
        """AIRequest input_data validator actively rejects vendor-specific parameters."""
        f = get_valid_fixtures()["AIRequest_minimal"].copy()
        f["input_data"] = {vendor_field: "some_value"}
        with pytest.raises(ValidationError) as exc_info:
            AIRequest.model_validate(f)
        assert "violates provider neutrality" in str(exc_info.value)

    @pytest.mark.parametrize(
        "vendor_field",
        ["openai_key", "anthropic_max_tokens", "gemini_tier"],
    )
    def test_ai_request_rejects_vendor_metadata(self, vendor_field: str):
        """AIRequest metadata validator actively rejects vendor-specific metadata."""
        f = get_valid_fixtures()["AIRequest_minimal"].copy()
        f["metadata"] = {vendor_field: "meta_val"}
        with pytest.raises(ValidationError) as exc_info:
            AIRequest.model_validate(f)
        assert "violates provider neutrality" in str(exc_info.value)
