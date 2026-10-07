"""
tests/ai/planning/test_planning_architecture_guards.py
======================================================
Architecture Boundary & Authority Guards for S28-05 (Section 48, 49, 50, 51, 77).

Guarantees:
1. CreativePlanner cannot mutate lifecycle state (.pipeline_state.json).
2. CreativePlanner cannot override QC or forge render approvals.
3. CreativePlanner cannot write or mutate the canonical Template Registry.
4. Provider neutrality: zero direct imports of vendor SDKs (openai, anthropic, google.generativeai).
5. BlueprintCompiler cannot mutate lifecycle state or grant QC acceptance.
6. BlueprintCompiler cannot promote templates or mutate canonical Template Registry.
7. BlueprintCompiler does not make Tier decisions (REUSE/COMPOSE/CREATE runtime).
8. BlueprintCompiler does not execute novel candidate creation (CREATE engine).
"""

import ast
from pathlib import Path
import pytest

PLANNING_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "ai" / "planning"


def test_guard_zero_vendor_sdk_imports_in_planning():
    """Provider Neutrality: no direct imports of openai, anthropic, or google.generativeai."""
    forbidden_modules = {"openai", "anthropic", "google.generativeai", "elevenlabs", "heygen", "fal"}
    violations = []

    for py_file in PLANNING_ROOT.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden_modules:
                        violations.append(f"{py_file.name}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in forbidden_modules:
                    violations.append(f"{py_file.name}:{node.lineno}: from {node.module} import ...")

    assert len(violations) == 0, f"Vendor SDK imports detected in ai/planning/:\n" + "\n".join(violations)


def test_guard_zero_raw_filesystem_writes_in_planning():
    """No raw file writes in production ai/planning/."""
    violations = []

    for py_file in PLANNING_ROOT.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    for arg in node.args[1:]:
                        if isinstance(arg, ast.Constant) and any(m in str(arg.value) for m in ["w", "a"]):
                            violations.append(f"{py_file.name}:{node.lineno}: Raw open mode '{arg.value}'")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in ("write_text", "write_bytes"):
                    violations.append(f"{py_file.name}:{node.lineno}: Raw Path.{node.func.attr}() call")

    assert len(violations) == 0, f"Filesystem write violations in ai/planning/:\n" + "\n".join(violations)


def test_guard_no_lifecycle_or_qc_mutation_in_planning():
    """Neither CreativePlanner nor BlueprintCompiler may touch lifecycle or QC services."""
    forbidden_tokens = [
        "transition_to",
        "update_state",
        ".pipeline_state.json",
        ".studio_approved",
        "ReviewDecision",
        "LifecycleService",
        "ReviewService",
        "StateStore",
    ]
    violations = []

    for py_file in PLANNING_ROOT.glob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{py_file.name}: contains forbidden lifecycle/QC token '{token}'")

    assert len(violations) == 0, f"Lifecycle/QC authority violations in ai/planning/:\n" + "\n".join(violations)


def test_guard_no_template_registry_mutations_in_compiler():
    """BlueprintCompiler must treat Template Registry as strictly read-only."""
    forbidden_methods = ["register_template", "promote_candidate", "write_registry", "save_contract"]
    violations = []

    for py_file in PLANNING_ROOT.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden_methods:
                    violations.append(f"{py_file.name}:{node.lineno}: Method call '{node.func.attr}'")

    assert len(violations) == 0, f"Template registry write violations in ai/planning/:\n" + "\n".join(violations)


def test_guard_no_premature_candidate_or_promotion_runtime_in_s28_06():
    """Verify that S28-07 candidate generation, promotion, and approval engines are NOT in S28-06."""
    forbidden_classes = [
        "CreateEngine",
        "TemplateCandidateGenerator",
        "CandidateValidator",
        "CandidatePromoter",
        "PromotionService",
        "PromotionEngine",
        "CandidateWorkspace",
        "ApprovalEngine",
    ]
    violations = []

    for py_file in PLANNING_ROOT.glob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for cls in forbidden_classes:
            if f"class {cls}" in text:
                violations.append(f"{py_file.name}: Defines premature S28-07 class '{cls}'")

    assert len(violations) == 0, f"Premature S28-07 candidate/promotion engine violations:\n" + "\n".join(violations)


def test_guard_no_code_generation_in_compose_engine():
    """COMPOSE Engine must never generate or write code files (.tsx, .jsx, .ts, .js)."""
    forbidden_terms = [
        ".write_text(",
        ".write_bytes(",
        "export const ",
        "export default ",
        "function CustomTemplate",
        "const CustomTemplate",
    ]
    compose_file = PLANNING_ROOT / "compose_engine.py"
    text = compose_file.read_text(encoding="utf-8")
    violations = [t for t in forbidden_terms if t in text]
    assert len(violations) == 0, f"Code generation violations in compose_engine.py:\n" + "\n".join(violations)


def test_guard_tier_policy_and_engines_read_only_on_registry():
    """REUSE, COMPOSE, and TierPolicy must never mutate or write to Template Registry."""
    forbidden_mutations = [
        "register_template",
        "unregister_template",
        "promote_template",
        "write_registry",
        "update_registry",
        "delete_template",
    ]
    for filename in ("reuse_engine.py", "compose_engine.py", "tier_policy.py"):
        path = PLANNING_ROOT / filename
        text = path.read_text(encoding="utf-8")
        for m in forbidden_mutations:
            assert m not in text, f"Registry mutation '{m}' found in {filename}"
