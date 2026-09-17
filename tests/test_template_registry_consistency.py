# -*- coding: utf-8 -*-
"""test_template_registry_consistency.py — Permanent consistency test for CRD-019.

Enforces:
1. Ground truth enumeration of ALL active production templates.
2. Physical existence of implementation files on disk.
3. Upstream validator acceptance (validate_blueprint TEMPLATES).
4. Deterministic sync between template_catalog.json and registry/template-aliases.ts.
5. Zero unknown template classifications.
"""
import json
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "ground-truth" / "template_catalog.json"
TI_PATH = ROOT / "ground-truth" / "TEMPLATE_INDEX.md"
ALIASES_PATH = ROOT / "registry" / "template-aliases.ts"


@pytest.fixture(scope="module")
def ground_truth_data():
    assert CATALOG_PATH.exists(), f"Missing {CATALOG_PATH}"
    assert TI_PATH.exists(), f"Missing {TI_PATH}"

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    ti_text = TI_PATH.read_text(encoding="utf-8")
    ti_templates = set(re.findall(r"\| `([\w-]+)` \|", ti_text))

    active_templates = [
        c for c in catalog
        if c.get("path", "").startswith("templates/")
        and c.get("path") != "templates/brand-resolver.ts"
        and not c.get("path", "").endswith(".d.ts")
    ]

    return {
        "catalog": catalog,
        "ti_templates": ti_templates,
        "active_templates": active_templates
    }


def test_active_templates_count(ground_truth_data):
    """Assert exactly 105 active production template components exist."""
    active = ground_truth_data["active_templates"]
    assert len(active) == 105, f"Expected 105 active templates, got {len(active)}"


def test_every_active_template_has_disk_implementation(ground_truth_data):
    """Every active template must physically exist on disk."""
    active = ground_truth_data["active_templates"]
    missing = []
    for item in active:
        path = ROOT / item["path"]
        if not path.exists():
            missing.append(f"{item['name']}: {item['path']}")

    assert not missing, f"Active templates missing on disk: {missing}"


def test_every_active_template_accepted_by_validator(ground_truth_data):
    """Every active template's ground-truth name must be accepted by validate_blueprint.py."""
    active = ground_truth_data["active_templates"]
    ti_templates = ground_truth_data["ti_templates"]

    unaccepted = []
    for item in active:
        name = item["name"]
        if name not in ti_templates:
            unaccepted.append(name)

    assert not unaccepted, f"Active templates not accepted by validate_blueprint TEMPLATES: {unaccepted}"


def test_clean_room_failed_templates_in_active_set(ground_truth_data):
    """Target templates from the failed Clean-Room run must be in active production set."""
    target_names = {
        "Herodeviceassemblewrapper",
        "Splitscreenwrapper",
        "Landingcodeshowcasewrapper",
        "Datastorywrapper",
        "Creatorreelwrapper"
    }
    active_names = {item["name"] for item in ground_truth_data["active_templates"]}
    missing = target_names - active_names
    assert not missing, f"Target Clean-Room templates missing from active set: {missing}"


def test_template_aliases_file_in_sync_with_ground_truth():
    """Ensure registry/template-aliases.ts matches generator output with zero drift."""
    from scripts.generate_template_aliases import generate_aliases

    content, active_count, alias_count = generate_aliases()
    assert ALIASES_PATH.exists(), f"Missing {ALIASES_PATH}"
    current = ALIASES_PATH.read_text(encoding="utf-8")

    assert current.strip() == content.strip(), (
        "registry/template-aliases.ts is out of sync with ground truth. "
        "Run `python scripts/generate_template_aliases.py` to regenerate."
    )
    assert active_count == 105
    assert alias_count == 210
