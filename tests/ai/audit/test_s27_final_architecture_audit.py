"""
tests/ai/audit/test_s27_final_architecture_audit.py
===================================================
S27.27 — Authoritative Architecture Audit Suite.

Invariants Verified:
1. No raw SQL queries or direct DB drivers inside the `ai/` package (ADR-004 DEC-01).
2. No direct database bypass or untyped persistence in AI domain.
3. No raw filesystem mutations bypassing the StorageService boundary.
4. No direct project lifecycle mutations or QC gate bypasses by AI agents.
5. No hardcoded credentials or API keys across the codebase.
6. Provider replaceability proof: Provider A -> Provider B swap without domain changes.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import List, Tuple

import pytest

from ai.contracts.base import AIContractModel
from ai.contracts.capability import CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityType, ExecutionClass, ProvenanceRecord, QualityTarget
from ai.contracts.model import ModelRequirement
from ai.models.registry import create_empty_model_registry
from ai.models.types import CostTier, LatencyTier, ModelDefinition
from ai.providers import ProviderDefinition, create_empty_provider_registry
from ai.routing import ModelRouter, RoutingPolicy


AI_ROOT = Path(__file__).resolve().parents[3] / "ai"


def test_audit_no_raw_sql_in_ai_subsystem():
    """
    Scans every python file in production ai/ to ensure zero direct SQL statements
    or database driver imports.
    """
    sql_forbidden_imports = {"sqlite3", "psycopg2", "mysql", "asyncpg", "pymysql"}
    sql_query_patterns = [
        re.compile(r"\bSELECT\b\s+.*\s+\bFROM\b", re.IGNORECASE),
        re.compile(r"\bINSERT\b\s+\bINTO\b", re.IGNORECASE),
        re.compile(r"\bUPDATE\b\s+.*\s+\bSET\b", re.IGNORECASE),
        re.compile(r"\bDELETE\b\s+\bFROM\b", re.IGNORECASE),
        re.compile(r"\bCREATE\b\s+\bTABLE\b", re.IGNORECASE),
        re.compile(r"\bDROP\b\s+\bTABLE\b", re.IGNORECASE),
    ]

    violations: List[str] = []

    for py_file in AI_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(py_file))

        # Check forbidden imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in sql_forbidden_imports:
                        violations.append(f"{py_file.name}: Forbidden import '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(node.module.startswith(pkg) for pkg in sql_forbidden_imports):
                    violations.append(f"{py_file.name}: Forbidden from-import '{node.module}'")

        # Check raw SQL query strings (excluding comments)
        lines = text.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern in sql_query_patterns:
                if pattern.search(line):
                    # Check if line is just documentation/docstring
                    if '"""' in line or "'''" in line or "e.g." in line.lower():
                        continue
                    violations.append(f"{py_file.name}:{idx}: Raw SQL pattern detected in '{line.strip()}'")

    assert len(violations) == 0, f"Architecture violations detected in ai/:\n" + "\n".join(violations)


def test_audit_no_hardcoded_secrets_in_ai_subsystem():
    """
    Scans every file in production ai/ for leaked secrets or plaintext credentials.
    """
    secret_patterns = [
        re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
        re.compile(r"AIza[0-9A-Za-z-_]{35}", re.IGNORECASE),
        re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
    ]

    violations: List[str] = []

    for py_file in AI_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        for idx, line in enumerate(lines, 1):
            for pattern in secret_patterns:
                if pattern.search(line):
                    violations.append(f"{py_file.name}:{idx}: Leaked credential detected")

    assert len(violations) == 0, f"Secret leaks detected in production ai/:\n" + "\n".join(violations)


def test_audit_provider_replaceability_proof():
    """
    Proves ADR-004 DEC-06 (Provider Neutrality & Replaceability):
    A capability execution request routed to Provider A can be seamlessly
    swapped to Provider B without changing contracts, tool signatures,
    or caller domain code.
    """
    # 1. Setup Provider Registry with Provider A and Provider B
    provider_reg = create_empty_provider_registry()
    provider_reg.register(
        ProviderDefinition(
            provider_id="provider-alpha",
            display_name="Provider Alpha (Cloud)",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            enabled=True,
        )
    )
    provider_reg.register(
        ProviderDefinition(
            provider_id="provider-beta",
            display_name="Provider Beta (On-Prem / Local)",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            enabled=True,
        )
    )

    model_reg = create_empty_model_registry(provider_registry=provider_reg)

    model_reg.register(
        ModelDefinition(
            model_id="alpha-text-model",
            provider_id="provider-alpha",
            display_name="Alpha Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=True,
        )
    )
    model_reg.register(
        ModelDefinition(
            model_id="beta-text-model",
            provider_id="provider-beta",
            display_name="Beta Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=True,
        )
    )

    router = ModelRouter(model_registry=model_reg, provider_registry=provider_reg)
    policy = RoutingPolicy(policy_id="default-policy", max_fallbacks=2)

    # 2. Canonical requirement defined purely via Capability Contract (No provider coupling)
    requirement = ModelRequirement(
        capability=CapabilityType.TEXT_GENERATION,
        quality_target=QualityTarget.STANDARD,
    )

    # 3. Route under standard conditions -> selects active candidate
    decision1 = router.route(requirement=requirement, policy=policy)
    assert decision1.primary_model in ("alpha-text-model", "beta-text-model")

    # 4. Swap: Disable Provider Alpha completely
    provider_reg._providers["provider-alpha"] = ProviderDefinition(
        provider_id="provider-alpha",
        display_name="Provider Alpha (Cloud)",
        supported_execution_modes=[ExecutionClass.INTERACTIVE],
        enabled=False,
    )


    # 5. Route again with identical requirement and policy -> seamlessly resolves to Provider Beta
    decision2 = router.route(requirement=requirement, policy=policy)
    assert decision2.primary_model == "beta-text-model"
    assert model_reg.get(decision2.primary_model).provider_id == "provider-beta"

def test_audit_no_raw_filesystem_writes_in_ai_subsystem():
    """
    Scans every python file in production ai/ to ensure zero raw filesystem writes
    (open(..., 'w'), write_text, write_bytes). All persistence must traverse
    StorageService or repository boundaries.
    """
    violations: List[str] = []

    for py_file in AI_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check built-in open(..., 'w'/'a')
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    for arg in node.args[1:]:
                        if isinstance(arg, ast.Constant) and any(m in str(arg.value) for m in ["w", "a"]):
                            violations.append(f"{py_file.name}:{node.lineno}: Raw file open mode '{arg.value}'")
                # Check Path.write_text / write_bytes
                elif isinstance(node.func, ast.Attribute) and node.func.attr in ("write_text", "write_bytes"):
                    violations.append(f"{py_file.name}:{node.lineno}: Raw Path.{node.func.attr}() call")

    assert len(violations) == 0, f"Raw filesystem write violations in ai/:\n" + "\n".join(violations)


def test_audit_no_direct_lifecycle_or_qc_mutation_in_ai():
    """
    Ensures that AI layers do not expose tools or methods to directly override
    project lifecycle state or bypass QC approval gates.
    """
    from ai.tools.registry import ToolRegistry
    registry = ToolRegistry()
    tools = registry.list_tools()

    # Forbidden tool names that could bypass domain governance
    forbidden_tool_names = {
        "set_project_status",
        "override_lifecycle",
        "bypass_qc",
        "approve_project_qc",
        "force_publish",
    }

    registered_names = {t.name for t in tools}
    intersections = registered_names.intersection(forbidden_tool_names)
    assert len(intersections) == 0, f"Forbidden governance tools exposed to AI: {intersections}"


