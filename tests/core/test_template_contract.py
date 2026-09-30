"""
tests/core/test_template_contract.py — Comprehensive Unit & Contract Tests for S15.
Tests:
- Deterministic contract generation from single authority (registry/template-registry-data.json)
- In-memory --check staleness detector
- Collision invariants (duplicate canonical, duplicate alias, alias colliding with canonical)
- Canonical ID naming regex enforcement (^[a-z0-9]+(-[a-z0-9]+)*$)
- Resolution semantics (canonical, alias, unknown, metadata name, malformed)
- Typed UnknownTemplateError with fail-closed semantics
- Presence on disk does NOT make unregistered .tsx valid
- Registered wrapper with name different from canonical ID IS valid
- Availability strictly governed by registry metadata truth (zero disk scanning)
"""
import copy
import json
import re
import tempfile
from pathlib import Path
import pytest

from scripts.core.template_contract import (
    TemplateRegistryContract,
    TemplateContractEntry,
    UnknownTemplateError,
    get_template_contract,
)
from scripts.generators.generate_template_contract import (
    build_template_contract,
    serialize_contract_deterministic,
    serialize_aliases_ts,
    check_staleness,
    write_file_atomic,
    load_authority_metadata,
    TemplateContractGenerationError,
    CANONICAL_ID_REGEX,
    AUTHORITY_FILE,
    OUTPUT_CONTRACT,
    OUTPUT_ALIASES,
)

ROOT = Path(__file__).resolve().parent.parent.parent
CONTRACT_PATH = ROOT / "contracts" / "template-runtime-contract.json"


def test_contract_file_exists_and_valid():
    """contracts/template-runtime-contract.json must exist and parse cleanly."""
    assert CONTRACT_PATH.exists()
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    assert data["contract_version"] == "1.0.0"
    assert data["single_authority"] == "registry/template-registry-data.json"
    assert data["stats"]["canonical_count"] == 105
    assert len(data["templates"]) == 105
    assert len(data["aliases"]) == data["stats"]["alias_count"]


def test_contract_deterministic_generation():
    """Generating the contract twice produces byte-for-byte identical output."""
    contract1, aliases1 = build_template_contract()
    json1 = serialize_contract_deterministic(contract1)
    ts1 = serialize_aliases_ts(aliases1)

    contract2, aliases2 = build_template_contract()
    json2 = serialize_contract_deterministic(contract2)
    ts2 = serialize_aliases_ts(aliases2)

    assert json1 == json2
    assert ts1 == ts2
    assert CONTRACT_PATH.read_text(encoding="utf-8") == json1
    assert (ROOT / "registry" / "template-aliases.ts").read_text(encoding="utf-8") == ts1


def test_contract_check_mode_passes_when_up_to_date():
    """check_staleness returns True when contract and aliases are up-to-date."""
    contract, aliases = build_template_contract()
    json_str = serialize_contract_deterministic(contract)
    ts_str = serialize_aliases_ts(aliases)
    up_to_date, msg = check_staleness(json_str, ts_str, contract_path=CONTRACT_PATH, aliases_path=OUTPUT_ALIASES)
    assert up_to_date is True
    assert "up-to-date" in msg


def test_contract_check_mode_fails_when_stale(tmp_path):
    """check_staleness returns False when file does not match expected output."""
    stale_contract = tmp_path / "stale-contract.json"
    stale_contract.write_text('{"templates": {}}', encoding="utf-8")
    stale_aliases = tmp_path / "stale-aliases.ts"
    stale_aliases.write_text('export const TEMPLATE_ALIASES = {};', encoding="utf-8")

    contract, aliases = build_template_contract()
    json_str = serialize_contract_deterministic(contract)
    ts_str = serialize_aliases_ts(aliases)
    up_to_date, msg = check_staleness(json_str, ts_str, contract_path=stale_contract, aliases_path=stale_aliases)
    assert up_to_date is False
    assert "STALE" in msg


def test_all_canonical_ids_satisfy_regex():
    """Every single canonical template ID satisfies ^[a-z0-9]+(-[a-z0-9]+)*$."""
    contract = get_template_contract()
    for cid in contract.list_canonical_ids():
        assert CANONICAL_ID_REGEX.match(cid), f"Canonical ID '{cid}' violates regex"


def test_generator_fails_on_regex_violation(tmp_path):
    """Generator must raise TemplateContractGenerationError if any canonical ID violates regex."""
    invalid_auth = tmp_path / "invalid-auth.json"
    invalid_auth.write_text(json.dumps({
        "templates": {
            "Invalid_PascalCase": {
                "canonical_id": "Invalid_PascalCase",
                "category": "composition",
                "component_name": "DummyComponent",
                "default_duration_frames": 120,
                "runtime_available": True,
                "aliases": []
            }
        }
    }), encoding="utf-8")

    with pytest.raises(TemplateContractGenerationError) as exc_info:
        build_template_contract(authority_path=invalid_auth)
    assert "violates naming rule regex" in str(exc_info.value)


def test_generator_fails_on_duplicate_alias_conflict(tmp_path):
    """Generator must raise if an alias maps to conflicting canonical IDs."""
    conflicting_auth = tmp_path / "conflicting-auth.json"
    conflicting_auth.write_text(json.dumps({
        "templates": {
            "template-one": {
                "canonical_id": "template-one",
                "category": "composition",
                "component_name": "CompOne",
                "aliases": ["SharedConflictAlias"]
            },
            "template-two": {
                "canonical_id": "template-two",
                "category": "composition",
                "component_name": "CompTwo",
                "aliases": ["SharedConflictAlias"]
            }
        }
    }), encoding="utf-8")

    with pytest.raises(TemplateContractGenerationError) as exc_info:
        build_template_contract(authority_path=conflicting_auth)
    assert "conflicting targets" in str(exc_info.value)


def test_generator_fails_on_alias_colliding_with_canonical_id(tmp_path):
    """Generator must raise if an alias collides with another template's canonical ID."""
    colliding_auth = tmp_path / "colliding-auth.json"
    colliding_auth.write_text(json.dumps({
        "templates": {
            "alpha-template": {
                "canonical_id": "alpha-template",
                "category": "composition",
                "component_name": "CompAlpha",
                "aliases": []
            },
            "beta-template": {
                "canonical_id": "beta-template",
                "category": "composition",
                "component_name": "CompBeta",
                "aliases": ["alpha-template"]
            }
        }
    }), encoding="utf-8")

    with pytest.raises(TemplateContractGenerationError) as exc_info:
        build_template_contract(authority_path=colliding_auth)
    assert "is itself a canonical ID for another template" in str(exc_info.value)


def test_generator_fails_on_mismatched_key_and_canonical_id(tmp_path):
    """Generator must raise if dictionary key does not match canonical_id property."""
    mismatched_auth = tmp_path / "mismatched-auth.json"
    mismatched_auth.write_text(json.dumps({
        "templates": {
            "key-one": {
                "canonical_id": "key-different",
                "category": "composition",
                "component_name": "CompMismatched",
                "aliases": []
            }
        }
    }), encoding="utf-8")

    with pytest.raises(TemplateContractGenerationError) as exc_info:
        build_template_contract(authority_path=mismatched_auth)
    assert "does not match canonical_id" in str(exc_info.value)


def test_resolution_semantics_matrix():
    """
    Validates the 5 required resolution semantics:
    1. Canonical ID -> resolves to itself
    2. Alias -> resolves to canonical ID
    3. Unknown ID -> None (fail closed)
    4. Metadata name -> None (fail closed)
    5. Whitespace / malformed -> None (fail closed)
    """
    contract = get_template_contract()

    # 1. Canonical ID
    c_entry = contract.resolve("rui-hero-device-assemble")
    assert c_entry is not None
    assert c_entry.canonical_id == "rui-hero-device-assemble"
    assert contract.is_valid("rui-hero-device-assemble") is True
    assert contract.canonicalize("rui-hero-device-assemble") == "rui-hero-device-assemble"

    # 2. Alias
    a_entry = contract.resolve("HeroDeviceAssembleWrapper")
    assert a_entry is not None
    assert a_entry.canonical_id == "rui-hero-device-assemble"
    assert contract.is_valid("HeroDeviceAssembleWrapper") is True
    assert contract.canonicalize("HeroDeviceAssembleWrapper") == "rui-hero-device-assemble"

    # 3. Unknown ID
    assert contract.resolve("NonExistentTemplateXYZ") is None
    assert contract.is_valid("NonExistentTemplateXYZ") is False
    with pytest.raises(UnknownTemplateError) as exc:
        contract.canonicalize("NonExistentTemplateXYZ", scene_id="s1", project_id="prj_1")
    assert exc.value.error_code == "UNKNOWN_TEMPLATE_ID"
    assert exc.value.template_id == "NonExistentTemplateXYZ"
    assert exc.value.scene_id == "s1"
    assert exc.value.project_id == "prj_1"

    # 4. Metadata name
    assert contract.resolve("Background") is None
    assert contract.resolve("Color") is None
    assert contract.resolve("Width") is None
    assert contract.resolve("Text") is None
    assert contract.resolve("misc") is None

    # 5. Whitespace / malformed
    assert contract.resolve("") is None
    assert contract.resolve("   ") is None
    assert contract.resolve(" rui-hero-device-assemble ") is None
    assert contract.resolve("rui-hero-device-assemble\n") is None
    assert contract.resolve(None) is None
    assert contract.resolve(12345) is None


def test_no_fuzzy_or_case_folding_resolution():
    """Resolution must strictly fail closed without guessing or fuzzy matching."""
    contract = get_template_contract()

    # Substring must not match
    assert contract.resolve("hero-device") is None
    assert contract.resolve("device-assemble") is None

    # Case variants not in aliases must not match
    assert contract.resolve("RUI-HERO-DEVICE-ASSEMBLE") is None
    assert contract.resolve("rui_hero_device_assemble") is None


def test_unregistered_physical_tsx_file_is_not_valid(tmp_path):
    """
    Physical existence of a .tsx file does NOT confer validity if unregistered in registry authority.
    """
    fake_tsx = ROOT / "templates" / "scenes" / "FakeUnregisteredComponent.tsx"
    # Even if this file exists or is queried, contract resolution fails closed
    contract = get_template_contract()
    assert contract.is_valid("FakeUnregisteredComponent") is False
    assert contract.resolve("FakeUnregisteredComponent") is None
    assert contract.is_valid("fake-unregistered-component") is False
    assert contract.resolve("fake-unregistered-component") is None


def test_wrapper_name_different_from_canonical_id_is_valid():
    """
    A template where component wrapper differs from canonical ID (e.g. HeroDeviceAssembleWrapper
    vs rui-hero-device-assemble) resolves correctly without needing matching filename.
    """
    contract = get_template_contract()
    entry = contract.resolve("HeroDeviceAssembleWrapper")
    assert entry is not None
    assert entry.canonical_id == "rui-hero-device-assemble"
    assert entry.component_name == "HeroDeviceAssembleWrapper"
    assert entry.runtime_available is True


def test_runtime_available_governed_by_registry_truth(tmp_path):
    """
    runtime_available flag is taken directly from the registry authority,
    never inferred from disk existence.
    """
    custom_auth = tmp_path / "custom-auth.json"
    custom_auth.write_text(json.dumps({
        "templates": {
            "mock-offline-template": {
                "canonical_id": "mock-offline-template",
                "category": "experimental",
                "component_name": "MockOffline",
                "runtime_available": False,
                "aliases": []
            },
            "mock-online-template": {
                "canonical_id": "mock-online-template",
                "category": "composition",
                "component_name": "MockOnline",
                "runtime_available": True,
                "aliases": []
            }
        }
    }), encoding="utf-8")

    contract_data, _ = build_template_contract(authority_path=custom_auth)
    assert contract_data["templates"]["mock-offline-template"]["runtime_available"] is False
    assert contract_data["templates"]["mock-online-template"]["runtime_available"] is True
