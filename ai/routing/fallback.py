"""
ai/routing/fallback.py
======================
Deterministic fallback chain construction and failure-aware fallback resolution (S27.4).

Invariants:
- Fallback candidates never include the primary candidate.
- Fallback candidates contain no duplicates.
- All fallbacks strictly satisfy all hard constraints.
- Failure-aware resolution routes intelligently away from failure causes.
- Bounded retries prevent infinite loops.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Tuple

from ai.contracts.errors import AIErrorCode
from ai.models.types import ModelDefinition
from ai.routing.policy import RoutingPolicy


def build_fallback_chain(
    ranked_candidates: List[Tuple[ModelDefinition, Decimal, Optional[Decimal]]],
    policy: RoutingPolicy,
) -> List[str]:
    """
    Constructs an ordered, deduplicated, bounded fallback list from ranked eligible candidates.
    Applies cross-provider diversity when configured.
    """
    if len(ranked_candidates) <= 1:
        return []

    primary_model = ranked_candidates[0][0]
    primary_key = primary_model.model_id
    primary_provider = primary_model.provider_id

    eligible_pool = [item[0] for item in ranked_candidates[1:]]
    fallbacks: List[str] = []
    selected_keys = {primary_key}

    if policy.prefer_cross_provider_diversity:
        # Separate candidates into distinct providers vs same provider
        diverse_candidates = [m for m in eligible_pool if m.provider_id != primary_provider]
        same_provider_candidates = [m for m in eligible_pool if m.provider_id == primary_provider]

        # Interleave with priority to diverse providers
        while (diverse_candidates or same_provider_candidates) and len(fallbacks) < policy.max_fallbacks:
            if diverse_candidates:
                candidate = diverse_candidates.pop(0)
                c_key = candidate.model_id
                if c_key not in selected_keys:
                    fallbacks.append(c_key)
                    selected_keys.add(c_key)

            if len(fallbacks) >= policy.max_fallbacks:
                break

            if same_provider_candidates:
                candidate = same_provider_candidates.pop(0)
                c_key = candidate.model_id
                if c_key not in selected_keys:
                    fallbacks.append(c_key)
                    selected_keys.add(c_key)
    else:
        for model in eligible_pool:
            c_key = model.model_id
            if c_key not in selected_keys:
                fallbacks.append(c_key)
                selected_keys.add(c_key)
                if len(fallbacks) >= policy.max_fallbacks:
                    break

    return fallbacks


def resolve_next_fallback(
    current_candidate: str,
    failure_code: AIErrorCode,
    attempted_candidates: List[str],
    ranked_candidates: List[Tuple[ModelDefinition, Decimal, Optional[Decimal]]],
    policy: RoutingPolicy,
) -> Optional[str]:
    """
    Deterministically resolves the next fallback candidate based on failure classification.
    Returns None if terminal or no remaining eligible candidate.
    """
    # 1. Terminal failures: No fallback allowed
    if failure_code in (AIErrorCode.CANCELLED, AIErrorCode.CONTENT_REJECTED, AIErrorCode.BUDGET_EXCEEDED):
        return None

    # 2. Bounded total attempts
    if len(attempted_candidates) >= policy.max_total_attempts:
        return None

    candidate_map = {m[0].model_id: m[0] for m in ranked_candidates}
    current_model = candidate_map.get(current_candidate)
    current_provider = current_model.provider_id if current_model else None

    # 3. Same-model retry check for transient output issues
    same_model_attempts = attempted_candidates.count(current_candidate)
    if failure_code in (AIErrorCode.INVALID_MODEL_OUTPUT, AIErrorCode.TIMEOUT):
        if same_model_attempts <= policy.max_same_model_retries:
            return current_candidate

    # 4. Filter unattempted candidates
    unattempted = [m[0] for m in ranked_candidates if m[0].model_id not in attempted_candidates]
    if not unattempted:
        return None

    # 5. Failure-specific prioritization
    if failure_code in (AIErrorCode.RATE_LIMITED, AIErrorCode.PROVIDER_UNAVAILABLE):
        # Strongly prefer candidates from an alternative provider
        alternative_providers = [m for m in unattempted if m.provider_id != current_provider]
        if alternative_providers:
            return alternative_providers[0].model_id

    elif failure_code == AIErrorCode.SCHEMA_VALIDATION_FAILED:
        # Prefer models with structured output support
        structured_models = [m for m in unattempted if m.supports_structured_output]
        if structured_models:
            return structured_models[0].model_id

    # Default to next highest-ranked unattempted candidate
    return unattempted[0].model_id
