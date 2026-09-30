"""
Architecture Guard: Single Authority for Project Lifecycle Transitions (S03).

Invariants enforced:
1. No production file outside scripts/core/lifecycle_service.py may assign to .lifecycle_state.
2. Neither API routers nor PipelineService may contain direct lifecycle mutations.
3. scripts/pipeline.py must delegate all state progression and failure marking to LifecycleService.
"""

import ast
import os
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

# Strictly allowed production files for lifecycle_state attribute mutation
AUTHORIZED_LIFECYCLE_WRITERS = {
    "scripts/core/lifecycle_service.py",
}


def get_production_python_files():
    """Returns all production Python files under api/ and scripts/ (excluding archive)."""
    prod_files = []
    for search_dir in ["api", "scripts"]:
        dir_path = WORKSPACE_ROOT / search_dir
        if not dir_path.exists():
            continue
        for root, dirs, files in os.walk(dir_path):
            # Exclude archive, tests, __pycache__
            if "archive" in root or "tests" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    prod_files.append(Path(root) / f)
    return prod_files


def test_no_unauthorized_lifecycle_state_attribute_assignments():
    """
    CI / Architecture Guard:
    Scans all production Python files for AST assignments to target.lifecycle_state.
    Fails if any file outside the single authorized domain service (LifecycleService)
    performs direct lifecycle mutations.
    """
    prod_files = get_production_python_files()
    violations = []

    for file_path in prod_files:
        rel_path = file_path.relative_to(WORKSPACE_ROOT).as_posix()
        if rel_path in AUTHORIZED_LIFECYCLE_WRITERS:
            continue

        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "lifecycle_state":
                        violations.append(f"{rel_path}:{node.lineno} (direct assign to .lifecycle_state)")
            elif isinstance(node, ast.AnnAssign):
                # Annotated assignment: target: Type = value (outside class definitions)
                if isinstance(node.target, ast.Attribute) and node.target.attr == "lifecycle_state":
                    violations.append(f"{rel_path}:{node.lineno} (annotated assign to .lifecycle_state)")
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Attribute) and node.target.attr == "lifecycle_state":
                    violations.append(f"{rel_path}:{node.lineno} (augmented assign to .lifecycle_state)")

    assert not violations, (
        f"Architecture Violation (STATE-001 / S03): Found unauthorized direct assignments "
        f"to .lifecycle_state outside LifecycleService:\n" + "\n".join(violations)
    )


def test_pipeline_service_has_no_lifecycle_mutations():
    """PipelineService in api/services/pipeline_service.py must not contain any lifecycle mutations."""
    pipeline_service_path = WORKSPACE_ROOT / "api" / "services" / "pipeline_service.py"
    assert pipeline_service_path.exists()

    tree = ast.parse(pipeline_service_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "lifecycle_state":
                    pytest.fail(
                        f"PipelineService must not mutate lifecycle_state at line {node.lineno}. "
                        "All transitions must go through LifecycleService."
                    )


def test_api_routers_have_no_lifecycle_mutations():
    """No API router may mutate lifecycle_state directly."""
    routers_dir = WORKSPACE_ROOT / "api" / "routers"
    for r_file in routers_dir.glob("*.py"):
        tree = ast.parse(r_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "lifecycle_state":
                        pytest.fail(
                            f"Router {r_file.name} must not mutate lifecycle_state at line {node.lineno}."
                        )
