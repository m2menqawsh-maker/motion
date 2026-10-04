"""
tests/ai/routing/test_determinism.py
====================================
Verification suite for Determinism and Order Invariance in Model Router (S27.4).

Invariants:
- Same input + Same registry state + Same policy == 100% Identical Selection.
- Registry insertion order or dictionary shuffling has ZERO impact on decision.
"""

from __future__ import annotations

import random
from decimal import Decimal
import pytest

from ai.contracts.common import CapabilityType, QualityTarget
from ai.contracts.model import ModelRequirement
from ai.models import (
    CANONICAL_MODELS_LIST,
    CostTier,
    LatencyTier,
    ModelDefinition,
    ModelRegistry,
    create_empty_model_registry,
    get_model_registry,
)
from ai.providers import get_provider_registry
from ai.routing import ModelRouter, WorkloadEstimate


class TestDeterminism:

    def test_routing_reproducibility(self):
        """Repeated routing invocations under identical state produce identical results."""
        router = ModelRouter()
        req = ModelRequirement(
            capability=CapabilityType.REASONING,
            quality_target=QualityTarget.HIGH,
        )
        workload = WorkloadEstimate(input_tokens=500, output_tokens=200)

        baseline = router.route(req, workload=workload)

        for _ in range(50):
            result = router.route(req, workload=workload)
            assert result.primary_model == baseline.primary_model
            assert result.fallback_candidates == baseline.fallback_candidates
            assert result.reason_code == baseline.reason_code
            assert result.estimated_cost.estimated_cost == baseline.estimated_cost.estimated_cost

    def test_registry_insertion_order_invariance(self):
        """
        Shuffling the order of models registered in ModelRegistry
        must NEVER alter the primary model or fallback ordering.
        """
        models_sample = [
            ModelDefinition(
                model_id="model-1",
                provider_id="openai",
                display_name="Model 1",
                capabilities=[CapabilityType.TEXT_GENERATION],
                quality_profile=QualityTarget.STANDARD,
                cost_profile=CostTier.LOW,
                latency_profile=LatencyTier.FAST,
                reliability=0.99,
                enabled=True,
            ),
            ModelDefinition(
                model_id="model-2",
                provider_id="gemini",
                display_name="Model 2",
                capabilities=[CapabilityType.TEXT_GENERATION],
                quality_profile=QualityTarget.STANDARD,
                cost_profile=CostTier.LOW,
                latency_profile=LatencyTier.FAST,
                reliability=0.99,
                enabled=True,
            ),
            ModelDefinition(
                model_id="model-3",
                provider_id="anthropic",
                display_name="Model 3",
                capabilities=[CapabilityType.TEXT_GENERATION],
                quality_profile=QualityTarget.HIGH,
                cost_profile=CostTier.MEDIUM,
                latency_profile=LatencyTier.FAST,
                reliability=0.99,
                enabled=True,
            ),
        ]

        req = ModelRequirement(capability=CapabilityType.TEXT_GENERATION)

        # Build baseline registry
        reg_baseline = create_empty_model_registry()
        for m in models_sample:
            reg_baseline.register(m)
        router_baseline = ModelRouter(model_registry=reg_baseline)
        baseline_sel = router_baseline.route(req)

        # Run multiple shuffled permutations
        rng = random.Random(42)
        for _ in range(10):
            shuffled = list(models_sample)
            rng.shuffle(shuffled)

            reg_shuffled = create_empty_model_registry()
            for m in shuffled:
                reg_shuffled.register(m)

            router_shuffled = ModelRouter(model_registry=reg_shuffled)
            shuffled_sel = router_shuffled.route(req)

            assert shuffled_sel.primary_model == baseline_sel.primary_model
            assert shuffled_sel.fallback_candidates == baseline_sel.fallback_candidates
            assert shuffled_sel.reason_code == baseline_sel.reason_code
