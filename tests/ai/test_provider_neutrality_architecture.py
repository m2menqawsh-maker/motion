"""
tests/ai/test_provider_neutrality_architecture.py
=================================================
Architecture Guard for Provider Neutrality (ADR-004 DEC-06.3 / S27.3).

Invariants:
- Domain services and scripts outside `ai/providers/` must never import concrete provider adapter classes.
- Direct vendor-branded classes (e.g. OpenAIProvider, GeminiProvider, ElevenLabsProvider)
  must never appear in domain logic.
- Vendor wire libraries (openai, anthropic, google.generativeai, elevenlabs) are restricted to adapter layers.
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
AI_DIR = WORKSPACE_ROOT / "ai"
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"

FORBIDDEN_VENDOR_CLASSES = {
    "OpenAIProvider",
    "GeminiProvider",
    "AnthropicProvider",
    "ElevenLabsProvider",
    "FalProvider",
    "ReplicateProvider",
    "OpenRouterProvider",
}

FORBIDDEN_RAW_VENDOR_IMPORTS = {
    "openai",
    "anthropic",
    "google.generativeai",
    "elevenlabs",
    "replicate",
    "fal_client",
}


class TestProviderNeutralityArchitecture:

    def test_domain_services_do_not_import_concrete_providers(self):
        """Scans ai/ (excluding ai/providers/) and scripts/core/ for direct vendor provider imports."""
        target_dirs = [
            AI_DIR / "contracts",
            AI_DIR / "capabilities",
            AI_DIR / "models",
            AI_DIR / "routing",
            SCRIPTS_DIR / "core",
        ]

        violations = []
        for target_dir in target_dirs:
            if not target_dir.exists():
                continue
            for py_file in target_dir.rglob("*.py"):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    # Check 'from ... import ...'
                    if isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if alias.name in FORBIDDEN_VENDOR_CLASSES:
                                violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))
                    # Check 'import ...'
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            root_pkg = alias.name.split(".")[0]
                            if root_pkg in FORBIDDEN_RAW_VENDOR_IMPORTS:
                                violations.append((str(py_file.relative_to(WORKSPACE_ROOT)), node.lineno, alias.name))

        assert not violations, f"Provider neutrality violations detected: {violations}"
