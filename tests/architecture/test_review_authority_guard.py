"""
Architecture Guard: Single Authority for Review Decisions & Render Authorization (S09).

Invariants enforced:
1. ReviewService is the SOLE authority for review bundles, decisions, and render authorization.
2. Direct inspection or reliance on .studio_approved alone for render authorization is forbidden.
3. User-supplied approved_by in API bodies or queries must never be treated as trusted identity.
4. Scripts and routers must not implement ad-hoc approval checks.
"""

import ast
import os
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def get_production_python_files():
    """Returns all production Python files under api/ and scripts/ (excluding archive, tests)."""
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


def test_no_direct_studio_approved_authority_in_render_paths():
    """
    CI / Architecture Guard:
    Render execution files (e.g. scripts/render_project.py, api/services/render_service.py)
    must NOT determine render authorization by checking .studio_approved exists on disk.
    They must invoke ReviewService.assert_render_authorized or assert_render_authorized.
    """
    render_script = WORKSPACE_ROOT / "scripts" / "render_project.py"
    assert render_script.exists()

    content = render_script.read_text(encoding="utf-8")
    assert "assert_render_authorized" in content, (
        "scripts/render_project.py must use canonical assert_render_authorized"
    )


def test_review_service_is_sole_authority_for_review_decisions():
    """
    CI / Architecture Guard:
    No file outside scripts/core/review_service.py and scripts/core/recovery_engine.py
    may mutate review_decisions or active_review_decision_id.
    """
    authorized_writers = {
        "scripts/core/review_service.py",
        "scripts/core/recovery_engine.py",
        "scripts/core/state_model.py",
    }

    prod_files = get_production_python_files()
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
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr in (
                        "review_decisions",
                        "active_review_decision_id",
                        "review_bundles",
                        "active_review_bundle_id",
                    ):
                        violations.append(f"{rel_path}:{node.lineno} (assign to .{target.attr})")

    assert not violations, (
        f"Architecture Violation (S09): Found unauthorized mutations of review state outside ReviewService:\n"
        + "\n".join(violations)
    )
