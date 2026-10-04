"""
tests/ai/routing/test_scoring.py
================================
Verification suite for candidate ranking, scoring weights, and tie breaking (S27.4).

Invariants:
- High-cost / premium models are NOT chosen by default when cheaper models fulfill criteria.
- Scoring is purely mathematical and parameter-driven.
- Tie-breaking is 100% deterministic and insensitive to input order.
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from ai.contracts.common import CapabilityType, QualityTarget
from ai.contracts.model import ModelRequirement
from ai.models.types import CostTier, LatencyTier, ModelDefinition
from ai.routing.policy import DRAFT_POLICY, HIGH_QUALITY_POLICY, RoutingPolicy, RoutingWeights, STANDARD_POLICY
from ai.routing.scoring import calculate_utility_score, rank_eligible_candidates


class TestCandidateScoring:

    def test_premium_model_not_default_when_standard_suffices(self):
        """
        Critical Taste Gate Invariant:
        When caller requests STANDARD quality, an economical STANDARD model
        MUST defeat an expensive ULTRA model under standard/balanced policy.
        """
        cheap_standard_model = ModelDefinition(
            model_id="cheap-standard",
            provider_id="provider-a",
            display_name="Cheap Standard Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.995,
            enabled=True,
        )
        expensive_ultra_model = ModelDefinition(
            model_id="expensive-ultra",
            provider_id="provider-b",
            display_name="Expensive Frontier Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.ULTRA,
            cost_profile=CostTier.VERY_HIGH,
            latency_profile=LatencyTier.FAST,
            reliability=0.999,
            enabled=True,
        )

        req = ModelRequirement(
            capability=CapabilityType.TEXT_GENERATION,
            quality_target=QualityTarget.STANDARD,
        )

        candidates = [
            (cheap_standard_model, Decimal("0.002")),
            (expensive_ultra_model, Decimal("0.250")),
        ]

        ranked = rank_eligible_candidates(candidates, req, STANDARD_POLICY)
        winner = ranked[0][0]

        assert winner.model_id == "cheap-standard", (
            f"Expected cheap-standard to win for STANDARD quality, but {winner.model_id} won"
        )

    def test_ultra_target_prioritizes_ultra_quality(self):
        """Under high/ultra quality target, ultra model defeats standard model."""
        cheap_standard_model = ModelDefinition(
            model_id="cheap-standard",
            provider_id="provider-a",
            display_name="Cheap Standard Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.995,
            enabled=True,
        )
        expensive_ultra_model = ModelDefinition(
            model_id="expensive-ultra",
            provider_id="provider-b",
            display_name="Expensive Frontier Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.ULTRA,
            cost_profile=CostTier.MEDIUM,
            latency_profile=LatencyTier.FAST,
            reliability=0.999,
            enabled=True,
        )

        req = ModelRequirement(
            capability=CapabilityType.TEXT_GENERATION,
            quality_target=QualityTarget.ULTRA,
        )

        candidates = [
            (cheap_standard_model, Decimal("0.002")),
            (expensive_ultra_model, Decimal("0.010")),
        ]

        ultra_policy = RoutingPolicy(
            policy_id="ultra-test",
            weights=RoutingWeights(
                quality_weight=Decimal("5.0"),
                cost_weight=Decimal("0.5"),
                latency_weight=Decimal("0.2"),
                reliability_weight=Decimal("1.0"),
            ),
        )

        ranked = rank_eligible_candidates(candidates, req, ultra_policy)
        winner = ranked[0][0]
        assert winner.model_id == "expensive-ultra"

    def test_deterministic_tie_breaking(self):
        """When two candidates have identical scores, tie-breaker produces identical ordering."""
        model_a = ModelDefinition(
            model_id="model-alpha",
            provider_id="provider-a",
            display_name="Model Alpha",
            capabilities=[CapabilityType.REASONING],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=True,
        )
        model_b = ModelDefinition(
            model_id="model-beta",
            provider_id="provider-b",
            display_name="Model Beta",
            capabilities=[CapabilityType.REASONING],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=True,
        )

        req = ModelRequirement(capability=CapabilityType.REASONING)

        # Candidate order 1: [A, B]
        ranked1 = rank_eligible_candidates([(model_a, Decimal("0.01")), (model_b, Decimal("0.01"))], req, STANDARD_POLICY)
        # Candidate order 2: [B, A]
        ranked2 = rank_eligible_candidates([(model_b, Decimal("0.01")), (model_a, Decimal("0.01"))], req, STANDARD_POLICY)

        # Ordering must be 100% deterministic (model-alpha alphabetically precedes model-beta)
        assert [m[0].model_id for m in ranked1] == [m[0].model_id for m in ranked2]
        assert ranked1[0][0].model_id == "model-alpha"
        assert ranked1[1][0].model_id == "model-beta"
