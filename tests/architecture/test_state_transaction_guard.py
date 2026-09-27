"""
Architecture Guard: Transactional State / CAS / Cross-Process Locking (S05).

Invariants enforced:
1. No production file uses hardcoded shared '.pipeline_state.json.tmp'.
2. No production file directly writes '.pipeline_state.json' outside StateStore.
3. No production file outside scripts/core/state_store.py assigns or increments .revision.
4. LifecycleService delegates state updates exclusively to StateStore.atomic_update.
5. StateStore.atomic_update strictly requires integer expected_revision (no None bypass).
"""

import ast
import os
from pathlib import Path
import pytest

from scripts.core.state_store import StateStore

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def get_production_python_files():
    """Returns all active production Python files under api/ and scripts/ (excluding archive)."""
    prod_files = []
    for search_dir in ["api", "scripts"]:
        dir_path = WORKSPACE_ROOT / search_dir
        if not dir_path.exists():
            continue
        for root, dirs, files in os.walk(dir_path):
            if "archive" in root or "tests" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    prod_files.append(Path(root) / f)
    return prod_files


def test_no_hardcoded_shared_tmp_state_file():
    """
    Architecture Invariant:
    No production code may use hardcoded shared '.pipeline_state.json.tmp'.
    Every commit must generate a unique temp file.
    """
    prod_files = get_production_python_files()
    violations = []

    for file_path in prod_files:
        content = file_path.read_text(encoding="utf-8")
        if ".pipeline_state.json.tmp" in content:
            violations.append(str(file_path.relative_to(WORKSPACE_ROOT)))

    assert not violations, (
        f"Architecture Violation (S05 / CONC-001): Found hardcoded '.pipeline_state.json.tmp' in:\n"
        + "\n".join(violations)
    )


def test_no_direct_state_file_writes_outside_state_store():
    """
    Architecture Invariant:
    No production file outside scripts/core/state_store.py may directly write or replace
    '.pipeline_state.json'.
    """
    prod_files = get_production_python_files()
    authorized_files = {"scripts/core/state_store.py"}
    violations = []

    for file_path in prod_files:
        rel_path = file_path.relative_to(WORKSPACE_ROOT).as_posix()
        if rel_path in authorized_files:
            continue

        lines = file_path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if ".pipeline_state.json" in stripped and any(w in stripped for w in ["write_text", "write_bytes", "open("]):
                violations.append(f"{rel_path}:{idx} -> {stripped}")

    assert not violations, (
        f"Architecture Violation (S05): Found unauthorized direct state file writing outside StateStore:\n"
        + "\n".join(violations)
    )


def test_no_scattered_production_revision_mutation():
    """
    Architecture Invariant:
    Production mutation of .revision is centralized within StateStore storage transaction.
    No domain service or script may manually increment or assign to .revision.
    """
    prod_files = get_production_python_files()
    authorized_writers = {
        "scripts/core/state_store.py",
        "scripts/core/state_model.py",
    }
    violations = []

    for file_path in prod_files:
        rel_path = file_path.relative_to(WORKSPACE_ROOT).as_posix()
        if rel_path in authorized_writers:
            continue

        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Attribute) and target.attr == "revision":
                        violations.append(f"{rel_path}:{node.lineno} (direct assign/augassign to .revision)")

    assert not violations, (
        f"Architecture Violation (S05): Found unauthorized mutation of .revision outside StateStore:\n"
        + "\n".join(violations)
    )


def test_lifecycle_service_uses_atomic_update():
    """
    Architecture Invariant:
    LifecycleService.transition must delegate state progression to StateStore.atomic_update.
    """
    service_file = WORKSPACE_ROOT / "scripts" / "core" / "lifecycle_service.py"
    assert service_file.exists()

    tree = ast.parse(service_file.read_text(encoding="utf-8"))
    atomic_update_called = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "atomic_update":
                atomic_update_called = True

    assert atomic_update_called, (
        "Architecture Violation (S05 / STATE-002): LifecycleService does not call StateStore.atomic_update!"
    )


def test_atomic_update_strictly_requires_integer_revision():
    """
    Contract Invariant:
    StateStore.atomic_update rejects None as expected_revision (no wildcard bypass).
    """
    with pytest.raises(ValueError, match="expected_revision must be an integer"):
        StateStore.atomic_update(WORKSPACE_ROOT / "tmp_bogus", expected_revision=None, mutator=lambda s: None)
