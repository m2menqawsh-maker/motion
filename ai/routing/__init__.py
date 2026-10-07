"""
ai/routing
==========
Centralized, deterministic Model Router subsystem for S27.
"""

from ai.routing.types import (
    CandidateDiagnostic,
    NoEligibleModelError,
    QualityEvaluation,
    QualityStatus,
    RouterError,
    RoutingDecision,
    RoutingReasonCode,
    WorkloadEstimate,
)
from ai.routing.policy import (
    DRAFT_POLICY,
    HIGH_QUALITY_POLICY,
    RoutingPolicy,
    RoutingWeights,
    STANDARD_POLICY,
    ULTRA_QUALITY_POLICY,
    get_policy_for_target,
)
from ai.routing.cost import calculate_estimated_cost
from ai.routing.constraints import evaluate_hard_constraints
from ai.routing.scoring import calculate_utility_score, rank_eligible_candidates
from ai.routing.fallback import build_fallback_chain, resolve_next_fallback
from ai.routing.escalation import resolve_quality_escalation
from ai.routing.router import ModelRouter
from ai.routing.capability_router import (
    CapabilityRouter,
    ModelRouterSeam,
    get_capability_router,
)

__all__ = [
    "CandidateDiagnostic",
    "NoEligibleModelError",
    "QualityEvaluation",
    "QualityStatus",
    "RouterError",
    "RoutingDecision",
    "RoutingReasonCode",
    "WorkloadEstimate",
    "DRAFT_POLICY",
    "HIGH_QUALITY_POLICY",
    "RoutingPolicy",
    "RoutingWeights",
    "STANDARD_POLICY",
    "ULTRA_QUALITY_POLICY",
    "get_policy_for_target",
    "calculate_estimated_cost",
    "evaluate_hard_constraints",
    "calculate_utility_score",
    "rank_eligible_candidates",
    "build_fallback_chain",
    "resolve_next_fallback",
    "resolve_quality_escalation",
    "ModelRouter",
    "CapabilityRouter",
    "ModelRouterSeam",
    "get_capability_router",
]
