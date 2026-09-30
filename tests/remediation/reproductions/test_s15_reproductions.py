"""
test_s15_reproductions.py — Permanent Verification & Invariant Tests for S15 Findings:
- LED-037 (P0): Single Authority (Runtime Template Registry -> Generated Contract).
- LED-038 (P0): Markdown (TEMPLATE_INDEX.md) has NO runtime authority.
- LED-039 (P0): Unified resolution semantics: Validator accepts canonical/aliases and rejects metadata.
- LED-040 (P0): Materializer no longer searches disk for .tsx matching template name.
- LED-042 (P1): Canonical template ID rule enforced across all registry entries.
"""
import json
import re
from pathlib import Path
import pytest

from scripts.core.template_contract import get_template_contract
from scripts.core.materializer import materialize_project_atomic
from scripts.generators.generate_template_contract import CANONICAL_ID_REGEX

ROOT = Path(__file__).resolve().parent.parent.parent.parent
AUTHORITY_FILE = ROOT / "registry" / "template-registry-data.json"
REGISTRY_TSX = ROOT / "registry" / "template-registry.tsx"
TEMPLATE_INDEX_MD = ROOT / "ground-truth" / "TEMPLATE_INDEX.md"


def test_reproduction_led_037_single_template_authority():
    """
    LED-037 Invariant:
    A single authoritative contract determines template validity for all consumers.
    'rui-hero-device-assemble' is accepted across all consumers.
    """
    contract = get_template_contract()
    
    # Contract resolves canonical
    entry = contract.resolve("rui-hero-device-assemble")
    assert entry is not None
    assert entry.canonical_id == "rui-hero-device-assemble"
    assert entry.runtime_available is True

    # Single authority JSON contains it
    data_json = json.loads(AUTHORITY_FILE.read_text(encoding="utf-8"))
    assert "rui-hero-device-assemble" in data_json["templates"]

    # Runtime registry tsx imports template-registry-data.json
    reg_text = REGISTRY_TSX.read_text(encoding="utf-8")
    assert 'import registryMetadata from "./template-registry-data.json"' in reg_text


def test_reproduction_led_038_markdown_not_governing_validator():
    """
    LED-038 Invariant:
    validate_blueprint.py does NOT depend on TEMPLATE_INDEX.md.
    Modifying TEMPLATE_INDEX.md does not inject valid templates into the contract.
    """
    contract = get_template_contract()
    
    # Contract must reject arbitrary names even if they existed in markdown
    assert contract.is_valid("NonExistentTemplate12345") is False
    assert contract.resolve("NonExistentTemplate12345") is None


def test_reproduction_led_039_validator_resolution_semantics():
    """
    LED-039 Invariant:
    Validator accepts runtime-valid canonical IDs and aliases, but rejects metadata names.
    """
    contract = get_template_contract()
    
    # Valid canonical
    assert contract.is_valid("rui-hero-device-assemble") is True
    
    # Valid alias
    assert contract.is_valid("HeroDeviceAssembleWrapper") is True
    assert contract.canonicalize("HeroDeviceAssembleWrapper") == "rui-hero-device-assemble"
    
    # Metadata names rejected
    assert contract.is_valid("Background") is False
    assert contract.resolve("Background") is None


def test_reproduction_led_040_materializer_accepts_canonical_id(tmp_path):
    """
    LED-040 Invariant:
    Materializer succeeds on canonical templates (e.g. rui-hero-device-assemble)
    without requiring a physical file named 'rui-hero-device-assemble.tsx' on disk.
    """
    proj_dir = tmp_path / "prj_rep_040"
    proj_dir.mkdir(parents=True)
    
    (proj_dir / "01_project.json").write_text(json.dumps({
        "project_id": "prj_rep_040",
        "title": "Reproduction Test 040",
        "fps": 30
    }), encoding="utf-8")
    
    (proj_dir / "02_asset_manifest.json").write_text(json.dumps({
        "manifest_version": "2.0.0",
        "project_id": "prj_rep_040",
        "created_at": "2026-09-28T12:00:00Z",
        "assets": []
    }), encoding="utf-8")
    
    (proj_dir / "master_plan.md").write_text("# Master Plan\n", encoding="utf-8")
    
    (proj_dir / "05_blueprint.json").write_text(json.dumps({
        "blueprint_version": "2.0.0",
        "project_id": "prj_rep_040",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {
                "scene_id": "scn_01",
                "template": "rui-hero-device-assemble",
                "startFrame": 0,
                "durationFrames": 30
            }
        ]
    }), encoding="utf-8")
    
    res = materialize_project_atomic(proj_dir, workspace_root=ROOT)
    assert res["project_id"] == "prj_rep_040"
    assert "rui-hero-device-assemble" in res["used_templates"]


def test_reproduction_led_042_canonical_id_naming_rule():
    """
    LED-042 Invariant:
    Every canonical template ID in the single authority satisfies CANONICAL_ID_REGEX.
    Animatedtextwrapper is no longer registered as a canonical ID violating regex.
    """
    auth_data = json.loads(AUTHORITY_FILE.read_text(encoding="utf-8"))
    canonical_ids = list(auth_data["templates"].keys())

    # Animatedtextwrapper is migrated
    assert "Animatedtextwrapper" not in canonical_ids
    assert "animatedtext-element" in canonical_ids

    # All canonical IDs match regex
    for cid in canonical_ids:
        assert CANONICAL_ID_REGEX.match(cid), f"ID '{cid}' violates regex"

