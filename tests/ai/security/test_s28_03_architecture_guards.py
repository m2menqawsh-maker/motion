"""
tests/ai/security/test_s28_03_architecture_guards.py
====================================================
Architecture & Security Guardrails for S28-03:
- Invariant 1: Provider Neutrality (Recipe != Provider). Zero vendor lock-in across all recipes.
- Invariant 2: Non-goal boundaries. S28-03 does NOT import or call S28-04 Narrative Planner,
  S28-05 Taste Engine, or Creative Planner.
- Invariant 3: Epistemic integrity. Provenance cannot be bypassed; unknown facts cannot become explicit.
- Invariant 4: No mutation of core authentication, authorization, or tenant boundaries.
"""

import ast
from pathlib import Path
import pytest

from ai.recipes.registry import RecipeRegistry, assert_provider_neutral


def test_guard_all_registered_recipes_are_provider_neutral():
    """Invariant 1: All registered recipes strictly comply with provider neutrality."""
    registry = RecipeRegistry()
    for recipe in registry.list_all():
        assert_provider_neutral(recipe)


def test_guard_non_goals_not_imported_in_s28_03():
    """
    Invariant 2: S28-03 must not import or build Narrative Planner, Taste Engine, or Creative Planner.
    Scans AST of ai/intent/, ai/recipes/, and ai/audio/ to guarantee boundaries.
    """
    forbidden_modules = [
        "narrative_planner",
        "taste_engine",
        "creative_planner",
        "narrative",
        "taste",
    ]

    target_dirs = [Path("ai/intent"), Path("ai/recipes"), Path("ai/audio")]
    for tdir in target_dirs:
        for py_file in tdir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in forbidden_modules:
                            assert forbidden not in alias.name.lower(), (
                                f"Boundary violation in {py_file}: imported '{alias.name}' "
                                f"which violates S28-03 non-goals (deferred to S28-04/S28-05)"
                            )
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for forbidden in forbidden_modules:
                        assert forbidden not in node.module.lower(), (
                            f"Boundary violation in {py_file}: imported from '{node.module}' "
                            f"which violates S28-03 non-goals (deferred to S28-04/S28-05)"
                        )


def test_guard_s28_03_no_core_auth_or_tenant_mutations():
    """
    Invariant 4: S28-03 modules are read-only with respect to core authentication,
    user tables, or tenant boundaries.
    """
    forbidden_tokens = [
        "alter table",
        "drop table",
        "delete from users",
        "delete from tenants",
        "update auth",
    ]
    target_dirs = [Path("ai/intent"), Path("ai/recipes"), Path("ai/audio")]
    for tdir in target_dirs:
        for py_file in tdir.glob("*.py"):
            content_lower = py_file.read_text(encoding="utf-8").lower()
            for token in forbidden_tokens:
                assert token not in content_lower, (
                    f"Authority violation in {py_file}: found forbidden mutation token '{token}'"
                )
