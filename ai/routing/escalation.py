"""
ai/routing/escalation.py
========================
Deterministic quality escalation resolution for the Model Router (S27.4).

Invariants:
- Quality escalation is distinct from provider failure fallback.
- Escalation steps only to candidates of strictly higher quality tier.
- Hard constraints (privacy, budget, capability) are NEVER violated during escalation.
- Escalation paths are bounded by policy.max_escalations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Tuple

from ai.contracts.common import QualityTarget
from ai.contracts.model import ModelRequirement
from ai.models.types import ModelDefinition
from ai.routing.policy import RoutingPolicy
from ai.routing.types import QualityEvaluation, QualityStatus

QUALITY_TIER_RANK = {
    QualityTarget.DRAFT: 1,
    QualityTarget.STANDARD: 2,
    QualityTarget.HIGH: 3,
    QualityTarget.ULTRA: 4,
}


def resolve_quality_escalation(
    current_model: ModelDefinition,
    requirement: ModelRequirement,
    evaluation: QualityEvaluation,
    attempted_models: List[str],
    eligible_candidates: List[Tuple[ModelDefinition, Decimal, Optional[Decimal]]],
    policy: RoutingPolicy,
) -> Optional[Tuple[ModelDefinition, Decimal, Optional[Decimal]]]:
    """
    Selects the next higher-quality model candidate when quality evaluation fails.
    Returns: (escalated_model, utility_score, estimated_cost) or None.
    """
    # 1. Only escalate if evaluation explicitly reported quality failure
    if evaluation.status != QualityStatus.FAIL:
        return None

    # 2. Bounded escalation count
    if len(attempted_models) >= policy.max_escalations + 1:
        return None

    current_rank = QUALITY_TIER_RANK.get(current_model.quality_profile, 1)

    # 3. Filter candidates strictly to higher-quality tiers not yet attempted
    escalation_pool = [
        item for item in eligible_candidates
        if item[0].model_id not in attempted_models
        and QUALITY_TIER_RANK.get(item[0].quality_profile, 1) > current_rank
    ]

    if not escalation_pool:
        return None

    # 4. Sort escalation candidates primarily by incremental quality rank, then by utility score
    def escalation_sort_key(item: Tuple[ModelDefinition, Decimal, Optional[Decimal]]):
        model, score, est_cost = item
        quality_rank = QUALITY_TIER_RANK.get(model.quality_profile, 1)
        cost_val = est_cost if est_cost is not None else Decimal("999999")
        return (quality_rank, -score, cost_val, model.model_id)

    sorted_escalation = sorted(escalation_pool, key=escalation_sort_key)
    return sorted_escalation[0]
