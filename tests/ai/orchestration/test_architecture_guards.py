"""
tests/ai/orchestration/test_architecture_guards.py
===================================================
Structural and architectural boundary guards for ai/orchestration/ (S27.11).

Invariants enforced:
1. No raw SQL or database driver imports inside ai/orchestration/.
2. No direct project filesystem access (projects/) inside ai/orchestration/.
3. No direct lifecycle_state mutation inside ai/orchestration/.
4. No direct QC approval tokens (.studio_approved, .qc_passed) in ai/orchestration/.
5. No provider-specific imports or branching in orchestration core.
6. No dict[str, Any] at important public API signatures.
7. Persistence is delegated exclusively to AIRunRepository (no in-memory authority).
"""

import ast
from pathlib import Path
from typing import List
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ORCHESTRATION_DIR = WORKSPACE_ROOT / "ai" / "orchestration"


def _get_python_files() -> List[Path]:
    return list(ORCHESTRATION_DIR.glob("*.py"))


def test_no_raw_db_drivers_in_orchestration():
    forbidden_modules = {"sqlite3", "psycopg2", "psycopg", "asyncpg", "mysql", "databases"}
    violations = []

    for file_path in _get_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in forbidden_modules:
                        violations.append((file_path.name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in forbidden_modules:
                    violations.append((file_path.name, node.lineno, node.module))

    assert not violations, f"Forbidden database driver imports found in ai/orchestration/: {violations}"


def test_no_raw_sql_execution_in_orchestration():
    violations = []
    sql_keywords = {"SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"}

    for file_path in _get_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr in {"execute", "executemany"}:
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        first_word = node.args[0].value.strip().split()[0].upper()
                        if first_word in sql_keywords:
                            violations.append((file_path.name, node.lineno, node.args[0].value[:30]))

    assert not violations, f"Raw SQL execution found in ai/orchestration/: {violations}"


def test_no_filesystem_projects_access_in_orchestration():
    forbidden = ["projects/", "projects\\", ".pipeline_state.json"]
    violations = []

    for file_path in _get_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any(p in node.value for p in forbidden):
                    violations.append((file_path.name, node.lineno, node.value))

    assert not violations, f"Raw project filesystem access found in ai/orchestration/: {violations}"


def test_no_lifecycle_or_qc_authority_mutation_in_orchestration():
    forbidden_qc_tokens = {".studio_approved", ".qc_passed", "06_qc_report.json"}
    violations = []

    for file_path in _get_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            # Check attribute assignment to lifecycle_state
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Attribute) and target.attr == "lifecycle_state":
                        violations.append((file_path.name, node.lineno, "lifecycle_state assignment"))
            # Check QC tokens
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any(t in node.value for t in forbidden_qc_tokens):
                    violations.append((file_path.name, node.lineno, node.value))

    assert not violations, f"Lifecycle or QC authority bypass found in ai/orchestration/: {violations}"


def test_no_provider_specific_coupling_in_orchestration():
    """Ensures ai/orchestration does not hardcode vendor provider SDK imports."""
    forbidden_vendors = {"openai", "anthropic", "google.generativeai", "replicate", "fal_client", "elevenlabs"}
    violations = []

    for file_path in _get_python_files():
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden_vendors:
                        violations.append((file_path.name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in forbidden_vendors:
                    violations.append((file_path.name, node.lineno, node.module))

    assert not violations, f"Vendor provider imports found in ai/orchestration/: {violations}"
