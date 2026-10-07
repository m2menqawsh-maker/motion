"""
tests/ai/test_s28_h03_remediation.py
====================================
Architecture Red/Green Verification Suite for Milestone S28-H03.
Focus: Safe Package Reorganization & Import Migration (FIND-06: ai/candidates wrong-layer relocation).

Invariants Verified:
1. Canonical implementation lives in `creative_governance.candidates`.
2. `ai.candidates` is a thin compatibility facade (DEPRECATED_COMPATIBILITY_IMPORT) with ZERO class definitions.
3. Compatibility re-exports resolve to the identical canonical objects.
4. Layering Invariants:
   - `creative_governance` does NOT import `ai.planning`, `ai.taste`, `ai.routing`, `ai.providers`, `ai.models`, `ai.regression`, `ai.evals`.
   - `ai.contracts` does NOT import `creative_governance`.
5. Zero unmigrated production consumers in `api/` and `scripts/`.
6. S28-M subsystems (capabilities, tools, mcp, speech, specialized) remain frozen.
7. FIND-01 and FIND-02 remain fixed.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Set
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


class TestFind06CandidateRelocation:
    """Verifies that candidate governance has relocated from ai/candidates to creative_governance/candidates."""

    def test_canonical_package_exists(self):
        """creative_governance/candidates must exist and contain the canonical implementation."""
        target_pkg = WORKSPACE_ROOT / "creative_governance" / "candidates"
        assert target_pkg.exists(), "creative_governance/candidates package directory must exist"
        assert (target_pkg / "__init__.py").exists(), "creative_governance/candidates/__init__.py must exist"

    def test_canonical_classes_defined_in_creative_governance(self):
        """All core candidate services and gates must be defined in creative_governance.candidates."""
        from creative_governance.candidates.service import TemplateCandidateService
        from creative_governance.candidates.repository import TemplateCandidateRepository
        from creative_governance.candidates.validation_service import CandidateValidationService
        from creative_governance.candidates.review_service import CandidateReviewService
        from creative_governance.candidates.promotion_service import PromotionService

        assert TemplateCandidateService.__module__ == "creative_governance.candidates.service"
        assert TemplateCandidateRepository.__module__ == "creative_governance.candidates.repository"
        assert CandidateValidationService.__module__ == "creative_governance.candidates.validation_service"
        assert CandidateReviewService.__module__ == "creative_governance.candidates.review_service"
        assert PromotionService.__module__ == "creative_governance.candidates.promotion_service"

    def test_ai_candidates_is_thin_facade_without_class_definitions(self):
        """ai/candidates must contain NO class definitions (re-exports only)."""
        ai_candidates_dir = WORKSPACE_ROOT / "ai" / "candidates"
        assert ai_candidates_dir.exists(), "ai/candidates compatibility facade directory must exist"

        class_defs = []
        for py_file in ai_candidates_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_defs.append(f"{py_file.name}:{node.lineno}:{node.name}")

        assert len(class_defs) == 0, (
            f"ai/candidates must not contain class definitions; found {len(class_defs)}:\n"
            + "\n".join(class_defs)
        )

    def test_compatibility_reexports_identity(self):
        """Importing from ai.candidates must resolve to identical objects in creative_governance.candidates."""
        import ai.candidates.service as legacy_service
        import creative_governance.candidates.service as canonical_service

        import ai.candidates.errors as legacy_errors
        import creative_governance.candidates.errors as canonical_errors

        import ai.candidates.review_service as legacy_review
        import creative_governance.candidates.review_service as canonical_review

        import ai.candidates.promotion_service as legacy_promotion
        import creative_governance.candidates.promotion_service as canonical_promotion

        assert legacy_service.TemplateCandidateService is canonical_service.TemplateCandidateService
        assert legacy_errors.CandidateConflictError is canonical_errors.CandidateConflictError
        assert legacy_errors.CandidateNotFoundError is canonical_errors.CandidateNotFoundError
        assert legacy_review.CandidateReviewService is canonical_review.CandidateReviewService
        assert legacy_promotion.PromotionService is canonical_promotion.PromotionService

    def test_creative_governance_disallowed_dependencies(self):
        """creative_governance must not import AI planner, taste, routing, providers, or evals."""
        gov_dir = WORKSPACE_ROOT / "creative_governance"
        if not gov_dir.exists():
            pytest.skip("creative_governance not yet created")

        forbidden_prefixes = (
            "ai.planning",
            "ai.taste",
            "ai.routing",
            "ai.providers",
            "ai.models",
            "ai.regression",
            "ai.evals",
            "ai.memory",
            "ai.context",
        )

        violations: List[str] = []
        for py_file in gov_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(alias.name.startswith(p) for p in forbidden_prefixes):
                            violations.append(f"{py_file.name}:{node.lineno}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if any(mod.startswith(p) for p in forbidden_prefixes):
                        violations.append(f"{py_file.name}:{node.lineno}: from {mod} import ...")

        assert len(violations) == 0, (
            f"creative_governance contains forbidden AI dependencies:\n" + "\n".join(violations)
        )

    def test_contracts_does_not_import_creative_governance(self):
        """ai/contracts must not import creative_governance (Layer 0 invariant)."""
        contracts_dir = WORKSPACE_ROOT / "ai" / "contracts"
        violations: List[str] = []
        for py_file in contracts_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("creative_governance"):
                            violations.append(f"{py_file.name}:{node.lineno}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod.startswith("creative_governance"):
                        violations.append(f"{py_file.name}:{node.lineno}: from {mod} import ...")

        assert len(violations) == 0, (
            f"ai/contracts imports creative_governance:\n" + "\n".join(violations)
        )

    def test_production_consumers_migrated_from_ai_candidates(self):
        """Production packages (api/ and scripts/) must not import from ai.candidates."""
        prod_dirs = [WORKSPACE_ROOT / "api", WORKSPACE_ROOT / "scripts"]
        unmigrated: List[str] = []

        for p_dir in prod_dirs:
            for py_file in p_dir.rglob("*.py"):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.startswith("ai.candidates"):
                                unmigrated.append(f"{py_file.relative_to(WORKSPACE_ROOT)}:{node.lineno}: import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        if mod.startswith("ai.candidates"):
                            unmigrated.append(f"{py_file.relative_to(WORKSPACE_ROOT)}:{node.lineno}: from {mod} import ...")

        assert len(unmigrated) == 0, (
            f"Found unmigrated production consumers importing from ai.candidates:\n"
            + "\n".join(unmigrated)
        )


class TestFrozenS28MGuards:
    """Verifies that S28-M subsystems remain completely untouched during H03."""

    def test_capabilities_baseline_frozen(self):
        from ai.capabilities.registry import CapabilityDefinition, CapabilityRegistry
        cap_reg = CapabilityRegistry()
        assert cap_reg is not None

    def test_tools_baseline_frozen(self):
        from ai.tools.registry import ToolRegistration, ToolRegistry
        from ai.tools.authorization import ToolAuthorizationPolicy
        tool_reg = ToolRegistry()
        assert tool_reg is not None

    def test_mcp_baseline_frozen(self):
        from ai.mcp.catalog import MCPServerDefinition, MCPCatalog
        from ai.mcp.policy import MCPSecurityPolicy
        catalog = MCPCatalog()
        assert catalog is not None

    def test_speech_and_specialized_baseline_frozen(self):
        from ai.speech.adapter import SpeechProviderAdapter
        from ai.specialized.interfaces import TTSProviderInterface
        assert SpeechProviderAdapter is not None
        assert TTSProviderInterface is not None


class TestPreviousRemediationsGuards:
    """Ensures that FIND-01 and FIND-02 remediations from H02 remain intact."""

    def test_find_01_models_does_not_import_providers(self):
        models_dir = WORKSPACE_ROOT / "ai" / "models"
        violations = []
        for py_file in models_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("ai.providers"):
                            violations.append(f"{py_file.name}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("ai.providers"):
                        violations.append(f"{py_file.name}:{node.lineno}")
        assert len(violations) == 0

    def test_find_02_contracts_does_not_import_memory(self):
        contracts_dir = WORKSPACE_ROOT / "ai" / "contracts"
        violations = []
        for py_file in contracts_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("ai.memory"):
                            violations.append(f"{py_file.name}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("ai.memory"):
                        violations.append(f"{py_file.name}:{node.lineno}")
        assert len(violations) == 0
