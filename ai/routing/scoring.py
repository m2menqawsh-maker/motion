"""
ai/routing/scoring.py
====================
Deterministic candidate scoring, utility computation, and tie-breaking for Model Router (S27.4).

Invariants:
- Utility scoring is purely mathematical, Decimal-backed, and parameter-governed.
- Tie-breaking is 100% deterministic and independent of dictionary insertion order.
- Expensive models do NOT win by default when lower-cost models meet target criteria.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple

from ai.contracts.common import QualityTarget
from ai.contracts.model import ModelRequirement
from ai.models.types import CostTier, LatencyTier, ModelDefinition
from ai.routing.policy import RoutingPolicy, RoutingWeights

QUALITY_NUMERIC_MAP = {
    QualityTarget.DRAFT: Decimal("0.25"),
    QualityTarget.STANDARD: Decimal("0.50"),
    QualityTarget.HIGH: Decimal("0.75"),
    QualityTarget.ULTRA: Decimal("1.00"),
}

COST_TIER_NUMERIC_MAP = {
    CostTier.FREE: Decimal("0.00"),
    CostTier.LOW: Decimal("0.25"),
    CostTier.MEDIUM: Decimal("0.50"),
    CostTier.HIGH: Decimal("0.75"),
    CostTier.VERY_HIGH: Decimal("1.00"),
}

LATENCY_TIER_NUMERIC_MAP = {
    LatencyTier.REALTIME: Decimal("0.10"),
    LatencyTier.FAST: Decimal("0.30"),
    LatencyTier.MODERATE: Decimal("0.60"),
    LatencyTier.SLOW: Decimal("1.00"),
}


def calculate_utility_score(
    model: ModelDefinition,
    requirement: ModelRequirement,
    estimated_cost: Optional[Decimal],
    policy: RoutingPolicy,
) -> Decimal:
    """
    Computes a deterministic utility score for an eligible model candidate.
    
    Formula:
        Utility = (QualityScore * QualityWeight)
                - (CostPenalty * CostWeight)
                - (LatencyPenalty * LatencyWeight)
                + (ReliabilityScore * ReliabilityWeight)
    """
    weights: RoutingWeights = policy.weights

    # 1. Quality contribution
    model_quality_val = QUALITY_NUMERIC_MAP.get(model.quality_profile, Decimal("0.50"))
    target_quality_val = QUALITY_NUMERIC_MAP.get(requirement.quality_target, Decimal("0.50"))

    # If model meets or exceeds target quality, reward proportionally.
    # If target is DRAFT or STANDARD, excess quality gives diminishing returns.
    if model_quality_val >= target_quality_val:
        quality_score = target_quality_val + (model_quality_val - target_quality_val) * Decimal("0.25")
    else:
        # Sub-target penalty
        quality_score = model_quality_val * Decimal("0.50")

    # 2. Cost penalty
    tier_cost = COST_TIER_NUMERIC_MAP.get(model.cost_profile, Decimal("0.50"))
    if estimated_cost is not None and estimated_cost > Decimal("0"):
        # Scale estimated cost into a normalized penalty component
        cost_penalty = (tier_cost + min(Decimal("1.00"), estimated_cost * Decimal("50"))) / Decimal("2")
    else:
        cost_penalty = tier_cost

    # 3. Latency penalty
    latency_penalty = LATENCY_TIER_NUMERIC_MAP.get(model.latency_profile, Decimal("0.50"))

    # 4. Reliability contribution
    reliability_score = Decimal(str(round(model.reliability, 4)))

    # Weighted composite utility
    utility = (
        (quality_score * weights.quality_weight)
        - (cost_penalty * weights.cost_weight)
        - (latency_penalty * weights.latency_weight)
        + (reliability_score * weights.reliability_weight)
    )

    return utility.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def rank_eligible_candidates(
    candidates_with_costs: List[Tuple[ModelDefinition, Optional[Decimal]]],
    requirement: ModelRequirement,
    policy: RoutingPolicy,
) -> List[Tuple[ModelDefinition, Decimal, Optional[Decimal]]]:
    """
    Scores and ranks eligible candidates using deterministic tie-breaking.
    Returns: List of (model, utility_score, estimated_cost) sorted descending by utility.
    """
    scored = []
    for model, est_cost in candidates_with_costs:
        score = calculate_utility_score(model, requirement, est_cost, policy)
        scored.append((model, score, est_cost))

    def tie_break_key(item: Tuple[ModelDefinition, Decimal, Optional[Decimal]]):
        model, score, est_cost = item
        # Deterministic sorting hierarchy:
        # 1. Utility score (highest first)
        # 2. Reliability SLA (highest first)
        # 3. Estimated cost (lowest first)
        # 4. Latency tier penalty (lowest first)
        # 5. Canonical model_id (alphabetical asc)
        # 6. Deployment_id (alphabetical asc)
        # 7. Provider_id (alphabetical asc)
        cost_val = est_cost if est_cost is not None else Decimal("999999")
        lat_val = LATENCY_TIER_NUMERIC_MAP.get(model.latency_profile, Decimal("1.0"))
        
        return (
            -score,
            -Decimal(str(model.reliability)),
            cost_val,
            lat_val,
            model.model_id,
            model.deployment_id or "",
            model.provider_id,
        )

    return sorted(scored, key=tie_break_key)
