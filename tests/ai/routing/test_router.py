"""
tests/ai/routing/test_router.py
===============================
Verification suite for ModelRouter interface, diagnostics, and multi-deployment (S27.4).
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from ai.contracts.common import CapabilityType, ExecutionClass, QualityTarget
from ai.contracts.model import ModelRequirement
from ai.models.types import CostTier, LatencyTier, ModelDefinition
from ai.models.registry import create_empty_model_registry
from ai.providers import ProviderDefinition, create_empty_provider_registry
from ai.routing import (
    ModelRouter,
    NoEligibleModelError,
    RoutingReasonCode,
    WorkloadEstimate,
)


@pytest.fixture
def deployment_router():
    provider_reg = create_empty_provider_registry()
    provider_reg.register(
        ProviderDefinition(
            provider_id="multi-cloud",
            display_name="Multi Cloud Provider",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            enabled=True,
        )
    )

    model_reg = create_empty_model_registry(provider_registry=provider_reg)
    model_reg.register(
        ModelDefinition(
            model_id="llm-model-core",
            provider_id="multi-cloud",
            display_name="LLM US Cluster",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.999,
            region="us-east-1",
            deployment_id="dep-us-01",
            enabled=True,
        )
    )
    model_reg.register(
        ModelDefinition(
            model_id="llm-model-core-eu",
            provider_id="multi-cloud",
            display_name="LLM EU Cluster",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.999,
            region="eu-west-1",
            deployment_id="dep-eu-01",
            enabled=True,
        )
    )

    return ModelRouter(
        model_registry=model_reg,
        provider_registry=provider_reg,
    )


class TestModelRouterFeatures:

    def test_routing_with_diagnostics(self, deployment_router):
        """Routing with diagnostics returns complete candidate evaluation logs."""
        req = ModelRequirement(capability=CapabilityType.TEXT_GENERATION)
        decision = deployment_router.route_with_diagnostics(req)

        assert decision.selection is not None
        assert decision.evaluated_candidates_count == 2
        assert decision.eligible_candidates_count == 2
        assert len(decision.diagnostics) == 2

        for diag in decision.diagnostics:
            assert diag.eligible is True
            assert diag.utility_score is not None

    def test_region_residency_selection(self, deployment_router):
        """Specifying target_region routes strictly to that deployment."""
        req = ModelRequirement(capability=CapabilityType.TEXT_GENERATION)

        # Route to EU
        decision_eu = deployment_router.route_with_diagnostics(req, target_region="eu-west-1")
        assert decision_eu.selection.primary_model == "llm-model-core-eu"

        # Route to US
        decision_us = deployment_router.route_with_diagnostics(req, target_region="us-east-1")
        assert decision_us.selection.primary_model == "llm-model-core"

    def test_no_eligible_candidates_raises_structured_error(self, deployment_router):
        """When no models support capability, NoEligibleModelError is raised with reasons."""
        req = ModelRequirement(capability=CapabilityType.IMAGE_GENERATION)

        with pytest.raises(NoEligibleModelError) as exc_info:
            deployment_router.route(req)

        err = exc_info.value
        assert err.capability == CapabilityType.IMAGE_GENERATION.value
        assert len(err.reasons) > 0
