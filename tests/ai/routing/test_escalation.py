"""
tests/ai/routing/test_escalation.py
===================================
Verification suite for Quality Escalation in Model Router (S27.4).

Invariants:
- Insufficient quality triggers quality escalation (conceptually distinct from provider failure).
- Escalation steps only to candidates of strictly higher quality tier.
- Hard constraints (privacy, budget, capability) are NEVER violated during escalation.
- Escalation is bounded by policy.max_escalations.
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from ai.contracts.common import CapabilityType, PrivacyRequirement, QualityTarget
from ai.contracts.model import ModelRequirement
from ai.contracts.usage import CostEstimate
from ai.capabilities.types import CapabilityPrivacyClass
from ai.models.types import CostTier, LatencyTier, ModelDefinition
from ai.routing.escalation import resolve_quality_escalation
from ai.routing.policy import STANDARD_POLICY, RoutingPolicy
from ai.routing.types import QualityEvaluation, QualityStatus


def make_quality_model(mid: str, quality: QualityTarget, cost: Decimal) -> Tuple[ModelDefinition, Decimal, Optional[Decimal]]:
    m = ModelDefinition(
        model_id=mid,
        provider_id="prov-a",
        display_name=mid,
        capabilities=[CapabilityType.TEXT_TO_SPEECH],
        quality_profile=quality,
        cost_profile=CostTier.MEDIUM,
        latency_profile=LatencyTier.FAST,
        reliability=0.99,
        enabled=True,
    )
    return (m, Decimal("1.0"), cost)


class TestQualityEscalation:

    def test_quality_pass_does_not_escalate(self):
        """Passing quality evaluation produces no escalation."""
        c_standard = make_quality_model("m-std", QualityTarget.STANDARD, Decimal("0.01"))
        c_high = make_quality_model("m-high", QualityTarget.HIGH, Decimal("0.05"))

        req = ModelRequirement(capability=CapabilityType.TEXT_TO_SPEECH)
        eval_pass = QualityEvaluation(status=QualityStatus.PASS)

        escalated = resolve_quality_escalation(
            current_model=c_standard[0],
            requirement=req,
            evaluation=eval_pass,
            attempted_models=["m-std"],
            eligible_candidates=[c_standard, c_high],
            policy=STANDARD_POLICY,
        )
        assert escalated is None

    def test_quality_fail_escalates_to_higher_tier(self):
        """Failing quality evaluation escalates from STANDARD to HIGH or ULTRA."""
        c_standard = make_quality_model("m-std", QualityTarget.STANDARD, Decimal("0.01"))
        c_high = make_quality_model("m-high", QualityTarget.HIGH, Decimal("0.05"))
        c_ultra = make_quality_model("m-ultra", QualityTarget.ULTRA, Decimal("0.15"))

        req = ModelRequirement(capability=CapabilityType.TEXT_TO_SPEECH)
        eval_fail = QualityEvaluation(status=QualityStatus.FAIL, reason="Unnatural cadence in synthesized speech")

        escalated = resolve_quality_escalation(
            current_model=c_standard[0],
            requirement=req,
            evaluation=eval_fail,
            attempted_models=["m-std"],
            eligible_candidates=[c_standard, c_high, c_ultra],
            policy=STANDARD_POLICY,
        )
        assert escalated is not None
        assert escalated[0].model_id == "m-high"
        assert escalated[0].quality_profile == QualityTarget.HIGH

    def test_escalation_bounded_by_max_escalations(self):
        """Exceeding max_escalations blocks further escalation."""
        c_std = make_quality_model("m-std", QualityTarget.STANDARD, Decimal("0.01"))
        c_high = make_quality_model("m-high", QualityTarget.HIGH, Decimal("0.05"))
        c_ultra = make_quality_model("m-ultra", QualityTarget.ULTRA, Decimal("0.15"))

        policy = RoutingPolicy(policy_id="test", max_escalations=1)
        req = ModelRequirement(capability=CapabilityType.TEXT_TO_SPEECH)
        eval_fail = QualityEvaluation(status=QualityStatus.FAIL)

        # Attempted m-std, then m-high (1 escalation already done)
        escalated = resolve_quality_escalation(
            current_model=c_high[0],
            requirement=req,
            evaluation=eval_fail,
            attempted_models=["m-std", "m-high"],
            eligible_candidates=[c_std, c_high, c_ultra],
            policy=policy,
        )
        assert escalated is None

    def test_escalation_stops_at_top_tier(self):
        """When already at top tier (ULTRA), quality failure cannot escalate further."""
        c_ultra = make_quality_model("m-ultra", QualityTarget.ULTRA, Decimal("0.15"))
        req = ModelRequirement(capability=CapabilityType.TEXT_TO_SPEECH)
        eval_fail = QualityEvaluation(status=QualityStatus.FAIL)

        escalated = resolve_quality_escalation(
            current_model=c_ultra[0],
            requirement=req,
            evaluation=eval_fail,
            attempted_models=["m-ultra"],
            eligible_candidates=[c_ultra],
            policy=STANDARD_POLICY,
        )
        assert escalated is None
