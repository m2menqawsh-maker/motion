"""
ai/budget/estimator.py
======================
Deterministic, conservative cost estimation engine for pre-execution budgeting (S27.5).

Invariants:
- Integrates with S27.4 canonical `calculate_estimated_cost` to prevent logic duplication.
- Conservative reservation: enforces bounded ceilings for unconstrained workloads (no infinite or $0 guesses).
- Strictly Decimal-backed arithmetic (no binary float precision loss).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from ai.contracts.usage import CostEstimate
from ai.models.types import ModelPricing
from ai.routing.cost import calculate_estimated_cost
from ai.routing.types import WorkloadEstimate
from ai.budget.types import CostProfile
from ai.budget.policy import get_cost_profile_config

QUANTIZE_PRECISION = Decimal("0.000001")


class BudgetEstimator:
    """
    Authority on financial workload estimation and conservative reservation ceilings.
    """

    @classmethod
    def estimate_cost(
        cls,
        pricing: Optional[ModelPricing],
        workload: Optional[WorkloadEstimate] = None,
    ) -> Optional[Decimal]:
        """
        Calculates the standard deterministic baseline cost using canonical pricing.
        Returns None if pricing schedule is not configured.
        """
        return calculate_estimated_cost(pricing=pricing, workload=workload)

    @classmethod
    def estimate_conservative_cost(
        cls,
        pricing: Optional[ModelPricing],
        workload: Optional[WorkloadEstimate] = None,
        cost_profile: CostProfile = CostProfile.STANDARD,
        default_output_tokens: int = 4096,
    ) -> CostEstimate:
        """
        Calculates conservative upper-bound cost for budget reservation.
        
        Guarantees:
        - If output tokens are unconstrained, applies bounded ceiling.
        - Applies headroom multiplier derived from CostProfile.
        - Denies execution (raises ValueError) if model pricing is not configured.
        - Strictly forbids $0 reservation for billable invocation.
        """
        if pricing is None:
            raise ValueError("Cannot estimate budget cost: ModelPricing schedule is missing or unconfigured")

        # Create bounded conservative workload copy if necessary
        effective_workload = workload
        if pricing.output_token_price is not None:
            if effective_workload is None:
                effective_workload = WorkloadEstimate(
                    input_tokens=1000,
                    output_tokens=default_output_tokens,
                    request_count=1,
                )
            elif effective_workload.output_tokens is None or effective_workload.output_tokens == 0:
                effective_workload = effective_workload.model_copy(
                    update={"output_tokens": default_output_tokens}
                )

        baseline_cost = cls.estimate_cost(pricing=pricing, workload=effective_workload)
        if baseline_cost is None:
            raise ValueError(f"Failed to calculate baseline cost for pricing schedule '{pricing.pricing_version}'")

        profile_config = get_cost_profile_config(cost_profile)
        headroom = profile_config.headroom_multiplier
        reserved_amount = (baseline_cost * headroom).quantize(QUANTIZE_PRECISION, rounding=ROUND_HALF_UP)

        # Enforce minimum precision ceiling if baseline is zero but price components exist
        if reserved_amount <= Decimal("0") and (
            pricing.input_token_price or pricing.output_token_price or pricing.request_price
        ):
            # Billable pricing exists but workload evaluates to 0; enforce safe bounded minimum
            reserved_amount = Decimal("0.000100")

        return CostEstimate(
            estimated_cost=baseline_cost,
            reserved_cost=reserved_amount,
            currency=pricing.currency,
            pricing_version=pricing.pricing_version,
        )
