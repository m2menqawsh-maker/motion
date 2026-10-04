"""
ai/routing/policy.py
====================
Configurable, versioned routing policies and scoring weights for the Model Router (S27.4).

Invariants:
- All weights are explicit, validated Decimals without hidden constants.
- Policies are versioned and deterministic.
"""

from __future__ import annotations

from decimal import Decimal
from pydantic import Field, field_validator

from ai.contracts.base import AIContractModel
from ai.contracts.common import QualityTarget


class RoutingWeights(AIContractModel):
    """
    Normalized contribution weights for candidate utility scoring.
    """
    quality_weight: Decimal = Field(default=Decimal("1.0"), ge=Decimal(0), description="Weight for quality target adherence")
    cost_weight: Decimal = Field(default=Decimal("1.0"), ge=Decimal(0), description="Weight for minimizing estimated cost")
    latency_weight: Decimal = Field(default=Decimal("0.5"), ge=Decimal(0), description="Weight for minimizing operational latency")
    reliability_weight: Decimal = Field(default=Decimal("0.5"), ge=Decimal(0), description="Weight for historical reliability SLA")

    @field_validator(
        "quality_weight",
        "cost_weight",
        "latency_weight",
        "reliability_weight",
        mode="before",
    )
    @classmethod
    def reject_float(cls, v):
        if isinstance(v, float):
            raise ValueError("Routing weights must be Decimal or string representations to prevent floating point drift")
        return v


class RoutingPolicy(AIContractModel):
    """
    Authoritative, versioned policy governing candidate filtering, scoring, and fallback bounds.
    """
    policy_id: str = Field(min_length=1, description="Unique policy identifier")
    version: str = Field(default="1.0.0", description="SemVer version of the policy")
    weights: RoutingWeights = Field(default_factory=RoutingWeights, description="Utility scoring weights")
    max_fallbacks: int = Field(default=3, ge=1, le=10, description="Maximum length of ordered fallback chain")
    max_escalations: int = Field(default=2, ge=0, le=5, description="Maximum sequential quality escalations allowed")
    max_same_model_retries: int = Field(default=1, ge=0, le=3, description="Maximum retries permitted on identical model before fallback")
    max_total_attempts: int = Field(default=4, ge=1, le=10, description="Absolute bounded limit on total attempts across retries and fallbacks")
    allow_cross_provider_fallback: bool = Field(default=True, description="Whether fallback chain may transition across distinct providers")
    prefer_cross_provider_diversity: bool = Field(default=True, description="Whether fallback selection alternates provider origins")
    allow_unknown_cost_models: bool = Field(default=False, description="Whether models with unconfigured pricing can be selected")
    allow_regional_cross_spill: bool = Field(default=False, description="Whether requests can spill to other regions if local is unavailable")


# Pre-configured canonical policy instances for standard quality targets
DRAFT_POLICY = RoutingPolicy(
    policy_id="draft-cost-first",
    version="1.0.0",
    weights=RoutingWeights(
        quality_weight=Decimal("0.5"),
        cost_weight=Decimal("3.0"),
        latency_weight=Decimal("0.8"),
        reliability_weight=Decimal("0.5"),
    ),
    max_fallbacks=2,
)

STANDARD_POLICY = RoutingPolicy(
    policy_id="standard-balanced",
    version="1.0.0",
    weights=RoutingWeights(
        quality_weight=Decimal("1.0"),
        cost_weight=Decimal("1.5"),
        latency_weight=Decimal("0.5"),
        reliability_weight=Decimal("0.7"),
    ),
    max_fallbacks=3,
)

HIGH_QUALITY_POLICY = RoutingPolicy(
    policy_id="high-quality-prioritized",
    version="1.0.0",
    weights=RoutingWeights(
        quality_weight=Decimal("2.5"),
        cost_weight=Decimal("1.0"),
        latency_weight=Decimal("0.4"),
        reliability_weight=Decimal("0.8"),
    ),
    max_fallbacks=3,
)

ULTRA_QUALITY_POLICY = RoutingPolicy(
    policy_id="ultra-fidelity-first",
    version="1.0.0",
    weights=RoutingWeights(
        quality_weight=Decimal("4.0"),
        cost_weight=Decimal("0.3"),
        latency_weight=Decimal("0.3"),
        reliability_weight=Decimal("1.0"),
    ),
    max_fallbacks=4,
)


def get_policy_for_target(quality_target: QualityTarget) -> RoutingPolicy:
    """Returns the canonical default routing policy matched to caller quality target."""
    if quality_target == QualityTarget.DRAFT:
        return DRAFT_POLICY
    if quality_target == QualityTarget.HIGH:
        return HIGH_QUALITY_POLICY
    if quality_target == QualityTarget.ULTRA:
        return ULTRA_QUALITY_POLICY
    return STANDARD_POLICY
