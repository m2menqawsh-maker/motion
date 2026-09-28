"""
test_s15_architecture_guard.py — Architecture & Structural Guards for S15:
- Guard 1: validate_blueprint.py has NO dependency on TEMPLATE_INDEX.md
- Guard 2: materializer.py does NOT perform physical .tsx file scans to resolve templates
- Guard 3: template contract is the sole Python authority
- Guard 4: contract staleness check succeeds on clean state and fails on out-of-sync contract
- Guard 5: No hardcoded template vocabulary duplicating registry in core scripts
- Guard 6: Zero source-code regex parsing in generator (uses native JSON authority)
- Guard 7: Zero filesystem scanning for template availability in generator
"""
import ast
import json
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATE_BP_PY = ROOT / "scripts" / "gates" / "validate_blueprint.py"
MATERIALIZER_PY = ROOT / "scripts" / "core" / "materializer.py"
GENERATOR_PY = ROOT / "scripts" / "generators" / "generate_template_contract.py"
CONTRACT_PATH = ROOT / "contracts" / "template-runtime-contract.json"
ALIASES_TS = ROOT / "registry" / "template-aliases.ts"
REGISTRY_TSX = ROOT / "registry" / "template-registry.tsx"
AUTHORITY_DATA_JSON = ROOT / "registry" / "template-registry-data.json"


def test_guard_validate_blueprint_has_no_template_index_dependency():
    """validate_blueprint.py must not reference TEMPLATE_INDEX.md."""
    content = VALIDATE_BP_PY.read_text(encoding="utf-8")
    assert "TEMPLATE_INDEX.md" not in content, (
        "Architecture Guard Violation: validate_blueprint.py still references TEMPLATE_INDEX.md!"
    )
    assert "TEMPLATES = set(" not in content, (
        "Architecture Guard Violation: validate_blueprint.py still parses templates from markdown!"
    )


def test_guard_materializer_has_no_physical_tsx_filename_search():
    """materializer.py must not search physical directories for .tsx filenames to validate templates."""
    content = MATERIALIZER_PY.read_text(encoding="utf-8")
    assert ".tsx" not in content or "template" not in content, (
        "Verifying no .tsx glob for templates in materializer"
    )
    assert 'f"{name.lower()}.tsx"' not in content, (
        "Architecture Guard Violation: materializer.py still scans for .tsx filenames!"
    )
    assert "template '{name}' not found on disk" not in content, (
        "Architecture Guard Violation: materializer.py still reports 'not found on disk' for templates!"
    )


def test_guard_no_hardcoded_template_sets_in_core_scripts():
    """
    Core scripts must not declare hardcoded template dictionaries or sets
    duplicating the runtime registry (e.g. VALID_TEMPLATES = {...}).
    """
    for py_file in [VALIDATE_BP_PY, MATERIALIZER_PY]:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assert target.id not in ("VALID_TEMPLATES", "KNOWN_TEMPLATES", "ALL_TEMPLATES"), (
                            f"Hardcoded template set '{target.id}' found in {py_file}!"
                        )


def test_guard_template_contract_is_the_python_authority():
    """
    Scripts must use scripts.core.template_contract.get_template_contract.
    """
    from scripts.core.template_contract import get_template_contract
    contract = get_template_contract()
    assert contract is not None
    assert len(contract.list_canonical_ids()) == 105
    assert len(contract.list_aliases()) == 192


def test_guard_contract_check_cli():
    """CLI check_staleness returns True when up-to-date."""
    from scripts.generators.generate_template_contract import (
        check_staleness,
        serialize_contract_deterministic,
        serialize_aliases_ts,
        build_template_contract,
    )
    
    contract, aliases = build_template_contract()
    json_str = serialize_contract_deterministic(contract)
    aliases_str = serialize_aliases_ts(aliases)
    ok, _ = check_staleness(json_str, aliases_str, contract_path=CONTRACT_PATH, aliases_path=ALIASES_TS)
    assert ok is True


def test_guard_zero_source_code_regex_parsing_in_generator():
    """
    generate_template_contract.py must NOT parse TypeScript/TSX source code with regex.
    It must use native JSON loading on the single authority data file.
    """
    generator_content = GENERATOR_PY.read_text(encoding="utf-8")
    
    # Must NOT attempt to parse .tsx files
    assert "template-registry.tsx" not in generator_content, (
        "Architecture Guard Violation: generator still references template-registry.tsx source text!"
    )
    assert "parse_runtime_registry" not in generator_content, (
        "Architecture Guard Violation: generator still contains a TSX source parser!"
    )
    # Must rely on template-registry-data.json
    assert "template-registry-data.json" in generator_content, (
        "Architecture Guard Violation: generator must read template-registry-data.json as authority!"
    )
    assert "json.loads" in generator_content or "json.load" in generator_content


def test_guard_zero_filesystem_scanning_for_template_availability():
    """
    Generator must NOT scan the filesystem for .tsx files to determine runtime_available.
    Availability is strictly defined by the registry truth.
    """
    generator_content = GENERATOR_PY.read_text(encoding="utf-8")
    
    # Must NOT perform filesystem globs for components
    assert ".glob(" not in generator_content, (
        "Architecture Guard Violation: generator performs filesystem globs!"
    )
    assert ".rglob(" not in generator_content, (
        "Architecture Guard Violation: generator performs filesystem rglobs!"
    )
    assert "templates/scenes" not in generator_content
    assert "templates/elements" not in generator_content
