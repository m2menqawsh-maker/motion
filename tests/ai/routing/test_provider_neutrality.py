"""
tests/ai/routing/test_provider_neutrality.py
===========================================
Architecture and Provider Neutrality Guards for Model Router (S27.4).

Invariants:
- Router logic must NEVER branch on vendor brand names for business routing.
- Router logic must NEVER invoke LLMs, provider execution adapters, or network APIs.
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest

ROUTING_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ai" / "routing"

FORBIDDEN_BRAND_STRINGS = [
    "openai",
    "anthropic",
    "gemini",
    "elevenlabs",
    "replicate",
    "whisper",
    "fal",
]

FORBIDDEN_NETWORK_MODULES = [
    "requests",
    "urllib",
    "urllib3",
    "httpx",
    "aiohttp",
    "socket",
]


class TestRoutingProviderNeutrality:

    def test_no_vendor_specific_business_logic_in_router(self):
        """Scans ai/routing/*.py to ensure no if provider == 'openai' or similar branching exists."""
        py_files = list(ROUTING_DIR.glob("*.py"))
        assert len(py_files) >= 5, "Expected ai/routing to contain core modules"

        violations = []
        for f in py_files:
            content = f.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(f))

            for node in ast.walk(tree):
                # Inspect equality comparisons (e.g. x == "openai")
                if isinstance(node, ast.Compare):
                    for comparator in node.comparators:
                        if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                            val_lower = comparator.value.lower()
                            if val_lower in FORBIDDEN_BRAND_STRINGS:
                                violations.append((f.name, node.lineno, comparator.value))

        assert not violations, f"Hardcoded vendor branching found in router: {violations}"

    def test_no_network_or_llm_execution_in_router(self):
        """Router is pure offline logic and must not import network or execution libraries."""
        py_files = list(ROUTING_DIR.glob("*.py"))

        violations = []
        for f in py_files:
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root_mod = alias.name.split(".")[0]
                        if root_mod in FORBIDDEN_NETWORK_MODULES:
                            violations.append((f.name, node.lineno, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    mod = (node.module or "").split(".")[0]
                    if mod in FORBIDDEN_NETWORK_MODULES:
                        violations.append((f.name, node.lineno, node.module))

        assert not violations, f"Forbidden network imports in router: {violations}"
