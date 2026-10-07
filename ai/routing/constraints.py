"""
ai/routing/constraints.py
=========================
Hard constraint evaluation for the Model Router (S27.4).

Invariants:
- Hard constraints are absolute binary gates (eligible vs ineligible).
- Constraint violations CANNOT be compensated by utility scores.
- Rejection reasons are deterministically captured for auditability.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import List, Optional, Tuple

from ai.contracts.common import ExecutionClass, PrivacyRequirement
from ai.contracts.model import ModelRequirement
from ai.capabilities.types import CapabilityPrivacyClass
from ai.providers.registry import ProviderRegistry
from ai.models.types import CostTier, LatencyTier, ModelDefinition
from ai.routing.cost import calculate_estimated_cost
from ai.routing.policy import RoutingPolicy
from ai.routing.types import WorkloadEstimate

# Conservative baseline latency floor by tier (ms)
LATENCY_TIER_FLOOR_MS = {
    LatencyTier.REALTIME: 100,
    LatencyTier.FAST: 500,
    LatencyTier.MODERATE: 2000,
    LatencyTier.SLOW: 10000,
}


def evaluate_hard_constraints(
    model: ModelDefinition,
    requirement: ModelRequirement,
    provider_registry: ProviderRegistry,
    workload: Optional[WorkloadEstimate] = None,
    policy: Optional[RoutingPolicy] = None,
    target_region: Optional[str] = None,
) -> Tuple[bool, List[str], Optional[Decimal]]:
    """
    Evaluates a candidate model against all non-negotiable hard constraints.
    Returns: (is_eligible, rejection_reasons, estimated_cost)
    """
    reasons: List[str] = []

    # 1. Model enabled check
    if not model.enabled:
        reasons.append("Model is disabled in registry")

    # 2. Provider existence and enabled check
    if not provider_registry.exists(model.provider_id):
        reasons.append(f"Provider '{model.provider_id}' is not registered")
    else:
        provider = provider_registry.get(model.provider_id)
        if not provider.enabled:
            reasons.append(f"Provider '{model.provider_id}' is currently disabled")
        current_env = os.environ.get("MOTION_ENV", "development").strip().lower()
        if current_env in ("production", "prod") and getattr(provider, "environment", "all") == "development":
            reasons.append(f"Provider '{model.provider_id}' is restricted to development environment only")

    # 3. Capability support
    if requirement.capability not in model.capabilities:
        reasons.append(f"Model does not support requested capability '{requirement.capability.value}'")

    # 4. Privacy requirements
    req_privacy = requirement.privacy_requirement
    if req_privacy == PrivacyRequirement.INTERNAL_ONLY:
        if model.privacy_class != CapabilityPrivacyClass.LOCAL_ONLY:
            reasons.append("Requirement is INTERNAL_ONLY but model is not LOCAL_ONLY")
        if provider_registry.exists(model.provider_id):
            prov = provider_registry.get(model.provider_id)
            if prov.privacy_compliance != PrivacyRequirement.INTERNAL_ONLY:
                reasons.append(f"Provider '{prov.provider_id}' does not guarantee INTERNAL_ONLY compliance")

    elif req_privacy == PrivacyRequirement.ZERO_DATA_RETENTION:
        if provider_registry.exists(model.provider_id):
            prov = provider_registry.get(model.provider_id)
            if prov.privacy_compliance not in (PrivacyRequirement.ZERO_DATA_RETENTION, PrivacyRequirement.INTERNAL_ONLY):
                reasons.append(f"Provider '{prov.provider_id}' does not guarantee zero data retention")

    # 5. Language requirements
    if requirement.language:
        req_lang = requirement.language.strip().lower()
        if req_lang != "*":
            supported_langs = [l.strip().lower() for l in model.languages]
            if "*" not in supported_langs and req_lang not in supported_langs:
                reasons.append(f"Model languages {model.languages} do not satisfy required language '{requirement.language}'")

    # 6. Required features
    if requirement.required_features:
        for feat in requirement.required_features:
            f = feat.strip().lower()
            if f in ("structured_output", "structured-output", "json") and not model.supports_structured_output:
                reasons.append("Model does not support structured JSON output")
            elif f in ("tools", "tool_calling", "function_calling") and not model.supports_tools:
                reasons.append("Model does not support tool calling")
            elif f == "streaming" and not model.supports_streaming:
                reasons.append("Model does not support streaming execution")
            elif f == "batch" and not model.supports_batch:
                reasons.append("Model does not support batch execution")
            elif f in ("cache", "prompt_caching") and not model.supports_cache:
                reasons.append("Model does not support prompt caching")
            elif f == "audio" and not model.supports_audio:
                reasons.append("Model does not support audio modality")
            elif f == "video" and not model.supports_video:
                reasons.append("Model does not support video modality")

    # 7. Region / residency constraints
    if target_region:
        if model.region and model.region.lower() != target_region.lower():
            reasons.append(f"Model region '{model.region}' does not match required region '{target_region}'")

    # 8. Latency ceiling check
    if requirement.max_latency_ms is not None:
        floor_latency = LATENCY_TIER_FLOOR_MS.get(model.latency_profile, 1000)
        if floor_latency > requirement.max_latency_ms:
            reasons.append(
                f"Model latency profile '{model.latency_profile.value}' (floor {floor_latency}ms) "
                f"exceeds hard ceiling of {requirement.max_latency_ms}ms"
            )

    # 9. Cost calculation & Hard budget ceiling check
    estimated_cost = calculate_estimated_cost(model.pricing, workload)
    if requirement.budget_constraint is not None:
        budget_limit = requirement.budget_constraint.estimated_cost
        if estimated_cost is not None and estimated_cost > budget_limit:
            reasons.append(
                f"Estimated cost {estimated_cost} exceeds hard budget ceiling of {budget_limit}"
            )
        elif estimated_cost is None and policy and not policy.allow_unknown_cost_models:
            reasons.append("Model pricing is unconfigured and policy forbids unpriced candidates under budget ceiling")

    # 10. Execution Class Policy
    if requirement.execution_class == ExecutionClass.BATCH:
        if provider_registry.exists(model.provider_id):
            prov = provider_registry.get(model.provider_id)
            if ExecutionClass.BATCH not in prov.supported_execution_modes:
                reasons.append(f"Provider '{model.provider_id}' does not support BATCH execution mode")
        if not model.supports_batch and model.cost_profile in (CostTier.HIGH, CostTier.VERY_HIGH):
            reasons.append(
                f"Model '{model.model_id}' is an expensive interactive-only model ({model.cost_profile.value}) "
                "and does not support batch execution. BATCH routing policy forbids blind dispatch."
            )
        elif not model.supports_batch:
            if provider_registry.exists(model.provider_id):
                prov = provider_registry.get(model.provider_id)
                if ExecutionClass.BATCH not in prov.supported_execution_modes:
                    reasons.append(f"Model '{model.model_id}' does not support BATCH execution")
    elif requirement.execution_class == ExecutionClass.INTERACTIVE:
        if provider_registry.exists(model.provider_id):
            prov = provider_registry.get(model.provider_id)
            if ExecutionClass.INTERACTIVE not in prov.supported_execution_modes:
                reasons.append(f"Provider '{model.provider_id}' does not support INTERACTIVE execution mode")

    is_eligible = len(reasons) == 0
    return is_eligible, reasons, estimated_cost

