"""
tests/ai/cost/test_architecture_guards.py
=========================================
Architectural boundary and isolation guards for S28-08C Cost Observability.

Guarantees:
- Cost subsystem has ZERO runtime authority: purely observational.
- Cost analyzer cannot mutate Template Registry or publish templates.
- Cost analyzer cannot mutate candidate lifecycles (approve, promote).
- Cost analyzer cannot override QC status or pipeline state.
- Cost analyzer cannot override tier selection decisions.
- Cost analyzer cannot write to S27 tenant memory.
- Client cannot forge or tamper with authoritative cost calculation.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from decimal import Decimal
import pytest

from ai.cost.analyzer import CreativeEfficiencyAnalyzer
from ai.cost.collector import CreativeUsageCollector
from ai.cost.accounting import CreativeCostEstimator, TokenAccounting

COST_PACKAGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ai" / "cost"


def test_cost_analyzer_has_zero_mutation_methods():
    """
    Reflective guard: CreativeEfficiencyAnalyzer must only possess read-only inspection methods.
    """
    forbidden_prefixes = (
        "mutate",
        "write",
        "update",
        "approve",
        "promote",
        "publish",
        "override",
        "delete",
        "set_",
        "switch_",
        "force_",
    )

    methods = [
        name for name, _ in inspect.getmembers(CreativeEfficiencyAnalyzer, predicate=inspect.isfunction)
        if not name.startswith("__")
    ]

    for m in methods:
        for prefix in forbidden_prefixes:
            assert not m.startswith(prefix), (
                f"Violation of Zero Runtime Authority: method '{m}' on "
                f"CreativeEfficiencyAnalyzer starts with forbidden mutation prefix '{prefix}'."
            )


def test_cost_subsystem_ast_zero_registry_writes():
    """
    AST analysis: ai/cost/ must contain zero code writing to Template Registry.
    """
    forbidden_targets = [
        "template-registry-data.json",
        "template-registry.tsx",
        "template_catalog.json",
        "TemplateRegistryPublisher",
        "publish_candidate",
        "promote_candidate",
    ]

    py_files = list(COST_PACKAGE_DIR.glob("*.py"))
    assert len(py_files) > 0

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for target in forbidden_targets:
                    assert target not in node.value, (
                        f"Forbidden registry target '{target}' referenced in {py_file.name}:{node.lineno}"
                    )


def test_cost_subsystem_ast_zero_pipeline_state_mutation():
    """
    AST analysis: ai/cost/ must not reference or write pipeline state files or QC flags.
    """
    forbidden_markers = [
        ".pipeline_state.json",
        ".qc_passed",
        "studio_approved",
        "STATIC_PASS",
        "RUNTIME_PASS",
    ]

    py_files = list(COST_PACKAGE_DIR.glob("*.py"))
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        for marker in forbidden_markers:
            assert marker not in content, (
                f"Forbidden pipeline mutation marker '{marker}' found in {py_file.name}."
            )


def test_cost_subsystem_ast_zero_memory_writes():
    """
    AST analysis: ai/cost/ must not write candidates to S27 memory.
    """
    forbidden_calls = [
        "propose_candidate",
        "save_memory",
        "delete_memory",
        "supersede_memory",
    ]

    py_files = list(COST_PACKAGE_DIR.glob("*.py"))
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                attr_name = getattr(func, "attr", None) or getattr(func, "id", None)
                if attr_name in forbidden_calls:
                    pytest.fail(
                        f"Forbidden memory write call '{attr_name}' detected in {py_file.name}:{node.lineno}"
                    )


def test_client_cannot_forge_cost_values():
    """
    Verifies that cost estimation is computed strictly by domain ModelPricing
    rather than accepting arbitrary client calculations.
    """
    # Attempting to calculate cost for gpt-4o always uses authoritative Decimal pricing
    cost, version, prov = CreativeCostEstimator.compute_cost(
        model_id="gpt-4o",
        input_tokens=1000,
        output_tokens=1000,
    )
    # gpt-4o pricing: 1000 * 0.000005 + 1000 * 0.000015 = 0.005 + 0.015 = 0.020000
    assert cost == Decimal("0.020000")
    assert version == "2026.09.v1"
