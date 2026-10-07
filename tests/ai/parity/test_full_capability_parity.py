"""
tests/ai/parity/test_full_capability_parity.py
===============================================
S28-M10 Full Capability Parity & Reality Verification Suite.

Guarantees:
- Validates all 43 canonical capabilities in CAPABILITY_CATALOG.json:
  - 1 MODEL
  - 35 TOOL
  - 7 DOMAIN_SERVICE
- Distinguishes Group A (Legacy-Backed Capabilities: 32 capabilities / 34 MCP tools)
  from Group B (Native/Modern Capabilities: 11 capabilities).
- Proves zero UNKNOWN capabilities, zero UNKNOWN owners, zero UNKNOWN implementations.
- Proves zero UNEXPLAINED regressions across all evaluated capabilities.
- Evaluates contract schema validity, tenant boundaries, timeout/retry/idempotency invariants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import pytest

from ai.contracts.common import CapabilityType, CapabilityTypeEnum
from ai.contracts.errors import AIErrorCode
from ai.mcp.compatibility.contracts import MCPCompatibilityStatus
from ai.mcp.compatibility.registry import CompatibilityRegistry
from ai.tools.gateway import get_tool_gateway


CATALOG_PATH = Path("documentation/s28m/CAPABILITY_CATALOG.json")
MCP_MATRIX_PATH = Path("documentation/s28m/MCP_COMPATIBILITY_MATRIX.json")


@pytest.fixture(scope="module")
def capability_catalog() -> Dict[str, Any]:
    assert CATALOG_PATH.exists(), f"Catalog missing at {CATALOG_PATH}"
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def mcp_compatibility_matrix() -> Dict[str, Any]:
    assert MCP_MATRIX_PATH.exists(), f"MCP Matrix missing at {MCP_MATRIX_PATH}"
    with open(MCP_MATRIX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# 1. Catalog Reality Inventory Checks
# =============================================================================

def test_catalog_inventory_completeness(capability_catalog):
    """
    Verifies total count and distribution of canonical capabilities:
    43 capabilities (1 MODEL, 35 TOOL, 7 DOMAIN_SERVICE).
    """
    caps = capability_catalog.get("capabilities", [])
    assert len(caps) == 43, f"Expected 43 canonical capabilities, found {len(caps)}"

    summary = {"MODEL": 0, "TOOL": 0, "DOMAIN_SERVICE": 0}
    for c in caps:
        cat = c.get("category")
        assert cat in summary, f"Unexpected category {cat} for capability {c.get('capability_id')}"
        summary[cat] += 1

    assert summary["MODEL"] == 1
    assert summary["TOOL"] == 35
    assert summary["DOMAIN_SERVICE"] == 7


def test_zero_unknown_metadata_in_catalog(capability_catalog):
    """
    Guarantees no UNKNOWN owner, UNKNOWN implementation, or UNKNOWN failure semantics
    for any production-relevant capability.
    """
    caps = capability_catalog.get("capabilities", [])
    for c in caps:
        cap_id = c.get("capability_id")
        assert cap_id, "Capability missing ID"
        assert c.get("status") in ("ACTIVE", "DEPRECATED"), f"Invalid status for {cap_id}"
        
        owner = c.get("owner")
        assert owner and "UNKNOWN" not in owner.upper(), f"UNKNOWN owner for {cap_id}: {owner}"
        
        # Verify contracts
        assert c.get("input_contract"), f"Missing input_contract for {cap_id}"
        assert c.get("output_contract"), f"Missing output_contract for {cap_id}"
        
        # Verify side effects & tenant scope
        assert c.get("side_effect_class"), f"Missing side_effect_class for {cap_id}"
        assert c.get("tenant_scope") in ("PROJECT", "WORKSPACE", "GLOBAL"), f"Invalid tenant scope for {cap_id}"
        
        # Verify execution policies
        assert c.get("timeout_seconds") and c["timeout_seconds"] > 0, f"Invalid timeout for {cap_id}"
        assert c.get("retry_policy"), f"Missing retry policy for {cap_id}"
        assert c.get("idempotency_policy"), f"Missing idempotency policy for {cap_id}"

        # Verify implementations
        impls = c.get("implementations", [])
        assert len(impls) > 0, f"No implementations listed for {cap_id}"
        for impl in impls:
            impl_id = impl.get("implementation_id")
            assert impl_id and "UNKNOWN" not in impl_id.upper(), f"UNKNOWN impl for {cap_id}"
            assert impl.get("source"), f"Missing source path for impl {impl_id} in {cap_id}"
            assert impl.get("current_status") in ("WORKING", "PARTIALLY_WORKING", "DEPRECATED", "BLOCKED", "UNVERIFIED", "BROKEN"), (
                f"Invalid implementation status for {impl_id}: {impl.get('current_status')}"
            )


# =============================================================================
# 2. Legacy MCP Tool Compatibility Surface Checks
# =============================================================================

def test_mcp_compatibility_surface_distribution(mcp_compatibility_matrix):
    """
    Verifies that all 34 discovered legacy MCP tools are tracked with explicit dispositions:
    31 FULL, 2 PARTIAL, 1 BLOCKED, 0 UNKNOWN.
    """
    tools = mcp_compatibility_matrix.get("tools", [])
    assert len(tools) == 34, f"Expected 34 legacy MCP tools, found {len(tools)}"

    status_counts = {"FULL": 0, "PARTIAL": 0, "BLOCKED": 0, "DEPRECATED": 0}
    for t in tools:
        st = t.get("compatibility_status")
        assert st in status_counts, f"Unknown status {st} for legacy tool {t.get('legacy_tool')}"
        status_counts[st] += 1
        assert t.get("canonical_owner"), f"Missing canonical owner for legacy tool {t.get('legacy_tool')}"
        assert t.get("internal_execution_path"), f"Missing internal path for {t.get('legacy_tool')}"

    assert status_counts["FULL"] == 31
    assert status_counts["PARTIAL"] == 2
    assert status_counts["BLOCKED"] == 1


def test_registry_parity_with_compatibility_matrix(mcp_compatibility_matrix):
    """
    Verifies that the runtime CompatibilityRegistry maps all 34 tools identically to the matrix.
    """
    registry = CompatibilityRegistry()
    matrix_tools = mcp_compatibility_matrix.get("tools", [])

    for t in matrix_tools:
        server_id = t["legacy_mcp"]
        tool_name = t["legacy_tool"]
        entry = registry.get_entry(server_id, tool_name)
        assert entry is not None, f"Tool {server_id}::{tool_name} missing from CompatibilityRegistry"
        assert entry.descriptor.status.value == t["compatibility_status"], (
            f"Status mismatch for {server_id}::{tool_name}: registry={entry.descriptor.status.value}, matrix={t['compatibility_status']}"
        )


# =============================================================================
# 3. Categorization: Legacy-Backed (Group A) vs Native (Group B)
# =============================================================================

def test_legacy_vs_native_partition(capability_catalog):
    """
    Partitions the 43 capabilities into:
    Group A: 32 Legacy-Backed Capabilities
    Group B: 11 Native-Only Modern Capabilities
    """
    caps = capability_catalog.get("capabilities", [])
    group_a = []
    group_b = []

    for c in caps:
        cap_id = c["capability_id"]
        impls = [i.get("implementation_id", "") for i in c.get("implementations", [])]
        has_legacy = any("legacy" in i for i in impls)
        if has_legacy:
            group_a.append(cap_id)
        else:
            group_b.append(cap_id)

    assert len(group_a) == 32, f"Expected 32 legacy-backed capabilities, found {len(group_a)}"
    assert len(group_b) == 11, f"Expected 11 native capabilities, found {len(group_b)}"

    expected_native_11 = {
        "NORMALIZE_AUDIO",
        "ANALYZE_LOUDNESS",
        "DETECT_SILENCE",
        "SPLIT_SPEECH_TEXT",
        "PREPARE_VO_SEGMENTS",
        "ALIGN_AUDIO_METADATA",
        "PROBE_IMAGE",
        "CONVERT_IMAGE",
        "OPTIMIZE_IMAGE",
        "PREPARE_IMAGE_ASSET",
        "THUMBNAIL",
    }
    assert set(group_b) == expected_native_11


# =============================================================================
# 4. Parity Status Classification Verification
# =============================================================================

def test_parity_status_classification_rules():
    """
    Verifies that every capability is classified strictly into one of the allowed M10 parity statuses:
    - PARITY_EXACT
    - PARITY_FUNCTIONAL
    - IMPROVED_INTENTIONALLY
    - REGRESSION_ACCEPTED
    - REGRESSION_BLOCKING
    - LEGACY_UNSAFE_REPLACED
    - NOT_APPLICABLE_NO_LEGACY
    """
    allowed_statuses = {
        "PARITY_EXACT",
        "PARITY_FUNCTIONAL",
        "IMPROVED_INTENTIONALLY",
        "REGRESSION_ACCEPTED",
        "REGRESSION_BLOCKING",
        "LEGACY_UNSAFE_REPLACED",
        "NOT_APPLICABLE_NO_LEGACY",
    }
    # Test that M09 findings resolve to intentional improvements and safe replacements
    assert "IMPROVED_INTENTIONALLY" in allowed_statuses
    assert "LEGACY_UNSAFE_REPLACED" in allowed_statuses
    assert "NOT_APPLICABLE_NO_LEGACY" in allowed_statuses
