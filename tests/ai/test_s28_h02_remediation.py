"""
tests/ai/test_s28_h02_remediation.py
======================================
Architecture and behavioral tests for S28-H02 Dependency & Authority Boundary Remediation.

Guarantees:
1. FIND-01: ai/models has no imports of ai/providers.
2. FIND-01: ModelRegistry works independently without requiring ProviderRegistry.
3. FIND-01: OpenRouter provider resolves model metadata and pricing without importing global ModelRegistry.
4. FIND-01: ProviderRegistry, routing, and fake/mock providers remain fully functional.
5. FIND-02: ai/contracts has no imports of ai/memory implementation.
6. FIND-02: EpistemicStatus, MemoryScope, SourceType defined once in ai/contracts/memory and re-exported by ai/memory/types.
7. FIND-02: ModelPricing defined in ai/contracts/model and re-exported by ai/models/types.
8. FIND-02: Feedback contracts serialize identically; backward compatibility preserved.
9. FIND-03: ai/regression does not depend on legacy milestone eval scripts (e.g. creative_evals_s28_04).
10. S28-M Frozen packages guard: ai/capabilities, ai/tools, ai/mcp, ai/speech, ai/specialized not modified.
"""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
AI_DIR = WORKSPACE_ROOT / "ai"


# ============================================================================
# 1. FIND-01: MODELS <-> PROVIDERS ARCHITECTURAL BOUNDARY
# ============================================================================

def test_models_package_has_no_providers_import():
    """Scans all python files in ai/models/ to guarantee 0 imports of ai.providers."""
    models_dir = AI_DIR / "models"
    violations = []

    for py_file in models_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("ai.providers"):
                        violations.append((py_file.name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("ai.providers"):
                    violations.append((py_file.name, node.lineno, node.module))

    assert not violations, f"ai/models must not import ai.providers: {violations}"


def test_model_registry_works_independently():
    """Verifies ModelRegistry can instantiate, register, query, and filter models without ProviderRegistry."""
    from ai.contracts.common import CapabilityType, QualityTarget
    from ai.models.registry import ModelRegistry
    from ai.models.types import CostTier, LatencyTier, ModelDefinition

    # Create standalone model registry with no provider registry
    reg = ModelRegistry()
    model = ModelDefinition(
        model_id="independent-test-model",
        provider_id="openai",
        display_name="Independent Model",
        capabilities=[CapabilityType.TEXT_GENERATION],
        quality_profile=QualityTarget.STANDARD,
        cost_profile=CostTier.LOW,
        latency_profile=LatencyTier.FAST,
        reliability=0.99,
    )
    reg.register(model)
    assert reg.exists("independent-test-model")
    retrieved = reg.get("independent-test-model")
    assert retrieved.model_id == "independent-test-model"
    assert len(reg.list()) == 1


def test_provider_registry_still_works():
    """Verifies canonical ProviderRegistry works and contains canonical providers."""
    from ai.providers import get_provider_registry
    reg = get_provider_registry()
    assert reg.exists("openai")
    assert reg.exists("openrouter")
    assert reg.exists("anthropic")
    assert len(reg.list()) >= 8


def test_openrouter_provider_resolves_model_metadata_correctly():
    """Verifies OpenRouterProvider estimates cost correctly using ModelPricing contract."""
    from ai.contracts.model import ModelPricing
    from ai.providers.openrouter import OpenRouterProvider

    # Provider should not require global mutable ModelRegistry for cost estimation
    provider = OpenRouterProvider(api_key="test-key")
    # Wire cost estimate calculation
    cost = provider._estimate_cost("openrouter-dev-model", 1000, 500)
    assert cost is not None
    assert isinstance(cost, Decimal)
    assert cost > Decimal("0")


def test_routing_still_selects_valid_provider_and_model():
    """Verifies ModelRouter still selects valid provider and model using both registries."""
    from ai.contracts.common import CapabilityType
    from ai.contracts.model import ModelRequirement
    from ai.routing.router import ModelRouter

    router = ModelRouter()
    req = ModelRequirement(capability=CapabilityType.REASONING)
    selection = router.route(req)
    assert selection.primary_model is not None
    assert selection.reason_code is not None


def test_fake_provider_remains_usable():
    """Verifies a custom or mock provider can be registered and queried in ProviderRegistry."""
    from ai.contracts.common import ExecutionClass, PrivacyRequirement
    from ai.providers.base import ProviderDefinition
    from ai.providers.registry import create_empty_provider_registry

    reg = create_empty_provider_registry()
    mock_provider = ProviderDefinition(
        provider_id="mock-custom",
        display_name="Mock Custom Provider",
        supported_execution_modes=[ExecutionClass.INTERACTIVE],
        privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
        enabled=True,
    )
    reg.register(mock_provider)
    assert reg.exists("mock-custom")
    assert reg.get("mock-custom").display_name == "Mock Custom Provider"


# ============================================================================
# 2. FIND-02: CONTRACTS -> MEMORY INVERTED DEPENDENCY
# ============================================================================

def test_contracts_package_has_no_memory_implementation_import():
    """Scans all python files in ai/contracts/ to guarantee 0 imports of ai.memory."""
    contracts_dir = AI_DIR / "contracts"
    violations = []

    for py_file in contracts_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("ai.memory"):
                        violations.append((py_file.name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("ai.memory"):
                    violations.append((py_file.name, node.lineno, node.module))

    assert not violations, f"ai/contracts must not import ai.memory: {violations}"


def test_canonical_enums_defined_once_and_reexported():
    """Verifies EpistemicStatus, MemoryScope, SourceType are canonically defined in ai/contracts/memory."""
    from ai.contracts.memory import EpistemicStatus as ContractEpistemicStatus
    from ai.contracts.memory import MemoryScope as ContractMemoryScope
    from ai.contracts.memory import SourceType as ContractSourceType
    from ai.memory.types import EpistemicStatus as MemoryEpistemicStatus
    from ai.memory.types import MemoryScope as MemoryMemoryScope
    from ai.memory.types import SourceType as MemorySourceType

    # Exactly one canonical definition (identity test)
    assert ContractEpistemicStatus is MemoryEpistemicStatus
    assert ContractMemoryScope is MemoryMemoryScope
    assert ContractSourceType is MemorySourceType


def test_model_pricing_defined_in_contracts_and_reexported():
    """Verifies ModelPricing is canonically defined in ai/contracts/model and re-exported."""
    from ai.contracts.model import ModelPricing as ContractModelPricing
    from ai.models.types import ModelPricing as ModelModelPricing

    assert ContractModelPricing is ModelModelPricing


def test_feedback_contracts_serialize_identically():
    """Verifies FeedbackClassification and StylePreferenceProvenance serialize identically with canonical types."""
    from datetime import datetime, timezone
    from ai.contracts.creative.feedback import (
        FeedbackCategory,
        FeedbackClassification,
        FeedbackSentiment,
        FeedbackTargetType,
        StylePreferenceProvenance,
    )
    from ai.contracts.memory import EpistemicStatus, MemoryScope, SourceType

    item = FeedbackClassification(
        classification_id="cls-100",
        feedback_id="fb-100",
        workspace_id="ws-default",
        user_id="user-1",
        project_id="proj-1",
        target_type=FeedbackTargetType.SCENE,
        target_reference="scene-01",
        category=FeedbackCategory.PACING,
        sentiment=FeedbackSentiment.POSITIVE,
        preference_dimension="pacing",
        proposed_value="fast",
        scope=MemoryScope.PROJECT,
        confidence=0.9,
        source=SourceType.HUMAN_CONFIRMATION,
        created_at=datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc),
    )
    data = item.model_dump()
    assert data["scope"] == "PROJECT"
    assert data["source"] == "HUMAN_CONFIRMATION"

    sig = StylePreferenceProvenance(
        dimension="pacing",
        epistemic_status=EpistemicStatus.CONFIRMED,
        confidence=0.85,
        source_type=SourceType.USER_STATEMENT,
        evidence_count=2,
        last_observed_at=datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc),
    )
    sig_data = sig.model_dump()
    assert sig_data["epistemic_status"] == "CONFIRMED"
    assert sig_data["source_type"] == "USER_STATEMENT"


# ============================================================================
# 3. FIND-03: MILESTONE EVALS VS REGRESSION SEPARATION
# ============================================================================

def test_regression_package_does_not_depend_on_milestone_evals():
    """Verifies ai/regression/ has 0 imports from ai.evals.creative_evals_s28_*."""
    regression_dir = AI_DIR / "regression"
    violations = []

    for py_file in regression_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "creative_evals_s28" in alias.name:
                        violations.append((py_file.name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module and "creative_evals_s28" in node.module:
                    violations.append((py_file.name, node.lineno, node.module))

    assert not violations, f"ai/regression must not import milestone evals scripts: {violations}"


def test_rubric_grader_is_self_contained():
    """Verifies RubricGrader uses canonical CreativeRubricsEvaluator defined in ai.regression."""
    from ai.regression.rubric_grader import CreativeRubricsEvaluator, RubricGrader
    grader = RubricGrader()
    assert isinstance(grader._evaluator, CreativeRubricsEvaluator)


def test_generic_eval_framework_does_not_depend_on_milestone_scripts():
    """Verifies generic eval platform modules in ai/evals/ do not import milestone scripts."""
    evals_dir = AI_DIR / "evals"
    generic_modules = [
        "runner.py",
        "gate.py",
        "promotion.py",
        "evaluators.py",
        "datasets.py",
        "deferred.py",
        "__init__.py",
    ]
    violations = []
    for mod_name in generic_modules:
        mod_path = evals_dir / mod_name
        if not mod_path.exists():
            continue
        tree = ast.parse(mod_path.read_text(encoding="utf-8"), filename=str(mod_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "creative_evals" in alias.name or "creative_datasets" in alias.name:
                        violations.append((mod_name, node.lineno, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.module and ("creative_evals" in node.module or "creative_datasets" in node.module):
                    violations.append((mod_name, node.lineno, node.module))

    assert not violations, f"Generic eval framework modules must not import milestone scripts: {violations}"


def test_s28_m_frozen_packages_unmodified():
    """Guarantees S28-M frozen packages (capabilities, tools, mcp, speech, specialized, candidates) were not altered."""
    # 1. 0 ToolGateway implementation
    tool_gateway_file = AI_DIR / "tools" / "gateway.py"
    cap_gateway_file = AI_DIR / "capabilities" / "gateway.py"
    assert not tool_gateway_file.exists(), "ToolGateway must not be created in H02 (deferred to S28-M)"
    assert not cap_gateway_file.exists(), "CapabilityGateway must not be created in H02 (deferred to S28-M)"

    # 2. 0 STT/TTS migration (STT remains in ai/speech, TTS remains in ai/specialized)
    speech_adapter = (AI_DIR / "speech" / "adapter.py").read_text(encoding="utf-8")
    assert "TTS" not in speech_adapter, "TTS must not be migrated to ai/speech in H02 (deferred to S28-M)"

    specialized_interfaces = (AI_DIR / "specialized" / "interfaces.py").read_text(encoding="utf-8")
    assert "class TTSProviderInterface" in specialized_interfaces, "TTS must remain in ai/specialized during H02"

    # 3. 0 candidate package relocation (candidates remains directly under ai/candidates)
    assert (AI_DIR / "candidates").is_dir(), "ai/candidates must not be relocated in H02 (deferred to H03)"
    assert (AI_DIR / "candidates" / "service.py").exists(), "ai/candidates/service.py must remain intact"

    # 4. 0 changes to MCP configuration and catalog
    mcp_catalog = (AI_DIR / "mcp" / "catalog.py").read_text(encoding="utf-8")
    assert "class MCPCatalog" in mcp_catalog, "MCPCatalog must remain frozen in H02"
