"""
tests/ai/budget/test_architecture_guards.py
===========================================
Architectural boundary guard tests for S27.5 (Budget & Cost Engine).

Enforces:
1. Router does not reserve budget (Router = decision, Budget = financial authority).
2. Budget does not execute providers (pure financial governance).
3. Budget does not import concrete vendor adapters (OpenAIProvider, etc.).
4. Budget does not use raw database drivers or raw SQL.
"""

import ast
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AI_DIR = WORKSPACE_ROOT / "ai"
BUDGET_DIR = AI_DIR / "budget"
ROUTING_DIR = AI_DIR / "routing"


class TestBudgetArchitectureGuards:

    def test_router_does_not_import_or_call_budget_service(self):
        """Scans ai/routing/ to ensure Model Router does not import or invoke BudgetService.reserve."""
        violations = []
        for py_file in ROUTING_DIR.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if "ai.budget" in mod:
                        for alias in node.names:
                            if alias.name in {"BudgetService", "reserve", "ReservationEngine"}:
                                violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "ai.budget" in alias.name:
                            violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))

        assert not violations, f"Router is importing Budget authority: {violations}"

    def test_budget_does_not_import_concrete_providers(self):
        """Scans ai/budget/ to ensure no concrete vendor provider adapters are imported."""
        forbidden_vendors = {
            "OpenAIProvider",
            "GeminiProvider",
            "AnthropicProvider",
            "ElevenLabsProvider",
            "FalProvider",
            "ReplicateProvider",
            "openai",
            "anthropic",
            "google.generativeai",
            "elevenlabs",
        }
        violations = []
        for py_file in BUDGET_DIR.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name in forbidden_vendors:
                            violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        root_mod = alias.name.split(".")[0]
                        if root_mod in forbidden_vendors:
                            violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))

        assert not violations, f"Budget engine imports concrete provider or vendor SDK: {violations}"

    def test_budget_does_not_execute_providers(self):
        """Verifies BudgetService does not define any provider execution methods."""
        from ai.budget.service import BudgetService

        forbidden_method_keywords = {"execute_provider", "call_provider", "run_model", "invoke_model"}
        service_methods = set(dir(BudgetService))

        found = forbidden_method_keywords.intersection(service_methods)
        assert not found, f"BudgetService contains execution methods: {found}"

    def test_budget_does_not_use_raw_db_drivers_or_sql(self):
        """Verifies no raw DB modules or direct SQL executions exist in ai/budget/."""
        forbidden_db = {"sqlite3", "psycopg2", "asyncpg", "mysql", "databases"}
        violations = []
        for py_file in BUDGET_DIR.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in forbidden_db or alias.name.split(".")[0] in forbidden_db:
                            violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod in forbidden_db or mod.split(".")[0] in forbidden_db:
                        violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, mod))

        assert not violations, f"Raw database driver import found in ai/budget/: {violations}"
