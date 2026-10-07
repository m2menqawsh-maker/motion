"""
tests/ai/media_processing/test_architecture_guards.py
=====================================================
Architectural guards enforcing subsystem boundaries, safe execution,
and tenant isolation in ai/media_processing/ (S28-M06).
"""

import ast
from pathlib import Path
import pytest

MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "ai" / "media_processing"


def test_zero_shell_true_in_media_processing():
    """Ensures no subprocess call in ai/media_processing uses shell=True."""
    violations = []
    for py_file in MEDIA_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                        if keyword.value.value is True:
                            violations.append(f"{py_file.name}:{node.lineno}: shell=True forbidden")

    assert len(violations) == 0, f"Found shell=True calls:\n" + "\n".join(violations)


def test_no_lifecycle_or_db_mutations_in_media_processing():
    """
    Ensures MediaProcessingService does not import or mutate lifecycle / DB state directly.
    Lifecycle and asset records belong to Domain Services.
    """
    forbidden_imports = {
        "scripts.pipeline",
        "scripts.generators",
        "scripts.gates",
        "scripts.render_project",
    }
    violations = []

    for py_file in MEDIA_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(f) for f in forbidden_imports):
                        violations.append(f"{py_file.name}:{node.lineno}: forbidden import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(node.module.startswith(f) for f in forbidden_imports):
                    violations.append(f"{py_file.name}:{node.lineno}: forbidden import {node.module}")

    assert len(violations) == 0, f"Found forbidden architectural imports:\n" + "\n".join(violations)


def test_all_contract_models_are_ai_contract_models():
    """Verifies that all request/result classes inherit from AIContractModel."""
    from ai.contracts.base import AIContractModel
    import ai.media_processing.contracts as contracts

    for attr_name in dir(contracts):
        attr = getattr(contracts, attr_name)
        if isinstance(attr, type) and (attr_name.endswith("Request") or attr_name.endswith("Result")):
            assert issubclass(attr, AIContractModel), f"{attr_name} must inherit from AIContractModel"
