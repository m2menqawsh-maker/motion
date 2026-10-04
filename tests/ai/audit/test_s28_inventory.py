"""
tests/ai/audit/test_s28_inventory.py
======================================
Validates the integrity, completeness, and governance of the S28 Legacy Creative Inventory.

Guarantees:
1. Zero unclassified critical creative artifacts.
2. Every record contains all required fields:
   - legacy_id
   - source_path
   - current_purpose
   - current_consumer
   - current_authority
   - target_subsystem
   - migration_status
3. Every migration_status is one of KEEP, MIGRATE, WRAP, DEPRECATE, DELETE_AFTER_PARITY.
4. Every source_path points to an existing file on disk.
5. Key legacy domains (references/, recipes/, .agents/) have complete coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
INVENTORY_JSON = WORKSPACE_ROOT / "documentation" / "audits" / "s28_legacy_creative_inventory.json"
INVENTORY_MD = WORKSPACE_ROOT / "documentation" / "audits" / "s28_legacy_creative_inventory.md"

REQUIRED_FIELDS = {
    "legacy_id",
    "source_path",
    "current_purpose",
    "current_consumer",
    "current_authority",
    "target_subsystem",
    "migration_status",
}

VALID_STATUSES = {
    "KEEP",
    "MIGRATE",
    "WRAP",
    "DEPRECATE",
    "DELETE_AFTER_PARITY",
}


def test_inventory_files_exist():
    assert INVENTORY_JSON.exists(), f"Missing {INVENTORY_JSON}"
    assert INVENTORY_MD.exists(), f"Missing {INVENTORY_MD}"


def test_inventory_structure_and_completeness():
    data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 80, f"Expected comprehensive audit with >= 80 items, got {len(data)}"

    seen_ids = set()
    for item in data:
        # Check required fields
        for field in REQUIRED_FIELDS:
            assert field in item, f"Item {item.get('legacy_id', 'unknown')} missing required field '{field}'"
            assert isinstance(item[field], str) and len(item[field].strip()) > 0, (
                f"Field '{field}' in {item.get('legacy_id')} cannot be empty"
            )

        # Check legacy_id uniqueness
        lid = item["legacy_id"]
        assert lid not in seen_ids, f"Duplicate legacy_id: {lid}"
        seen_ids.add(lid)

        # Check migration_status validity
        assert item["migration_status"] in VALID_STATUSES, (
            f"Invalid migration_status '{item['migration_status']}' for {lid}"
        )

        # Check physical existence of source_path
        src = WORKSPACE_ROOT / item["source_path"]
        assert src.exists(), f"Source path does not exist on disk: {item['source_path']}"


def test_zero_unclassified_critical_artifacts():
    data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    for item in data:
        status = item["migration_status"]
        assert status in VALID_STATUSES, f"Found unclassified artifact: {item['legacy_id']}"


def test_critical_creative_coverage():
    """Verifies that all 18 production recipes and all 10 taste documents are cataloged."""
    data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    source_paths = {item["source_path"] for item in data}

    # 1. Taste documents
    expected_taste_docs = [
        "references/4_taste_engine/choreography.md",
        "references/4_taste_engine/context-adaptation.md",
        "references/4_taste_engine/core-philosophy.md",
        "references/4_taste_engine/decision-framework.md",
        "references/4_taste_engine/disney-principles.md",
        "references/4_taste_engine/emotion-mapping.md",
        "references/4_taste_engine/motion-personality.md",
        "references/4_taste_engine/narrative-structure.md",
        "references/4_taste_engine/sfx_binding_matrix.md",
        "references/4_taste_engine/user-signature-style.md",
    ]
    for td in expected_taste_docs:
        assert td in source_paths, f"Taste document {td} is missing from inventory"

    # 2. Recipe definitions
    recipe_files = list(WORKSPACE_ROOT.glob("recipes/*.json"))
    for rf in recipe_files:
        rel = rf.relative_to(WORKSPACE_ROOT).as_posix()
        assert rel in source_paths, f"Recipe file {rel} is missing from inventory"

    # 3. Router and Protocol
    assert "references/ROUTER.md" in source_paths
    assert ".agents/rules/video-production-protocol.md" in source_paths
    assert "scripts/gates/taste_gate.py" in source_paths
    assert "scripts/gates/plan_gate.py" in source_paths
    assert "scripts/maintenance/promote_template.py" in source_paths
