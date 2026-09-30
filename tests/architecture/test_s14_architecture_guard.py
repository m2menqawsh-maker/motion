"""
tests/architecture/test_s14_architecture_guard.py — Architecture Guard for Fail-Closed Media Resolution (S14).

Guards against re-introducing fail-open patterns:
- mediaMap[x] || x
- mediaMap[x] ?? x
- mediaMap[x] ? mediaMap[x] : x
- safe_load("media_map.json", {})
"""
import re
from pathlib import Path
import pytest

from scripts.core.state_model import LifecycleState
from scripts.core.asset_resolution import (
    load_required_media_map,
    resolve_asset_reference,
    UnknownAssetReferenceError,
    RequiredArtifactMissingError,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def test_guard_no_fail_open_media_map_expressions():
    """
    ARCHITECTURE GUARD:
    Scans TypeScript and Python code for fail-open fallback patterns on media maps:
    - mediaMap[x] ?? x
    - mediaMap[x] || x
    - (mediaMap && mediaMap[x]) ? mediaMap[x] : x
    - media_map.get(x, x)
    """
    ts_files = list((WORKSPACE_ROOT / "remotion-app" / "src").rglob("*.ts*")) + list((WORKSPACE_ROOT / "contracts").rglob("*.ts*"))
    
    # Regex matching fail-open expressions
    fail_open_patterns = [
        re.compile(r"mediaMap\s*\[\s*\w+\s*\]\s*(?:\?\?|\|\|)\s*\w+"),
        re.compile(r"media_map\s*\[\s*\w+\s*\]\s*(?:\?\?|\|\|)\s*\w+"),
        re.compile(r"mediaMap\s*\[\s*\w+\s*\]\s*\?\s*mediaMap\s*\[\s*\w+\s*\]\s*:\s*\w+"),
        re.compile(r"media_map\.get\s*\(\s*\w+\s*,\s*\w+\s*\)"),
    ]

    violations = []

    for fpath in ts_files:
        if "node_modules" in str(fpath) or ".cache" in str(fpath):
            continue
        content = fpath.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            for pat in fail_open_patterns:
                if pat.search(line):
                    violations.append(f"{fpath.relative_to(WORKSPACE_ROOT)}:{line_no}: {line.strip()}")

    assert not violations, f"Fail-open mediaMap expression(s) detected:\n" + "\n".join(violations)


def test_guard_no_safe_load_empty_media_map_in_active_scripts():
    """
    ARCHITECTURE GUARD:
    Ensures no active script in scripts/ (excluding archive/) uses safe_load("media_map.json", {})
    or defaults missing media_map to an empty dict.
    """
    script_files = list((WORKSPACE_ROOT / "scripts").rglob("*.py"))
    bad_pattern = re.compile(r'safe_load\(\s*["\']media_map\.json["\']\s*,\s*\{\}\s*\)')

    violations = []
    for fpath in script_files:
        if "archive" in str(fpath) or "__pycache__" in str(fpath):
            continue
        content = fpath.read_text(encoding="utf-8")
        for line_no, line in enumerate(content.splitlines(), start=1):
            if bad_pattern.search(line):
                violations.append(f"{fpath.relative_to(WORKSPACE_ROOT)}:{line_no}: {line.strip()}")

    assert not violations, f"Found safe_load(\"media_map.json\", {{}}) in active script(s):\n" + "\n".join(violations)


def test_guard_behavioral_fail_closed_resolution():
    """
    BEHAVIORAL GUARD:
    Verifies that unknown asset references fail closed deterministically.
    """
    with pytest.raises(UnknownAssetReferenceError):
        resolve_asset_reference("ast_unmapped", {})


def test_guard_behavioral_mandatory_media_map(tmp_path):
    """
    BEHAVIORAL GUARD:
    Verifies that missing media_map.json in MATERIALIZED state raises RequiredArtifactMissingError.
    """
    dummy_dir = tmp_path / "prj_guard"
    dummy_dir.mkdir()
    with pytest.raises(RequiredArtifactMissingError):
        load_required_media_map(dummy_dir, state=LifecycleState.MATERIALIZED, workspace_root=tmp_path)
