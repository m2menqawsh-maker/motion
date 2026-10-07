"""
ai/budget/policy.py
===================
Policy profiles, headroom configurations, and settlement constraints for budgeting (S27.5).

Invariants:
- CostProfiles (ECONOMY, STANDARD, PREMIUM, MAXIMUM) guide quality escalation and cost sensitivity,
  never binding to concrete vendor models.
- All monetary arithmetic and multipliers use exact Decimal representation.
- Hard budget limits are strictly enforced across all profiles, including MAXIMUM.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict
from pydantic import Field

from ai.contracts.base import AIContractModel, StrictDecimal
from ai.budget.types import CostProfile, CostProfileEnum


class CostProfileConfig(AIContractModel):
    """
    Configuration parameters governing an operational Cost Profile.
    Directs policy decisions regarding escalation limits and conservative estimation padding.
    """
    profile: CostProfileEnum = Field(description="Associated cost profile")
    max_quality_escalations: int = Field(ge=0, description="Maximum escalation stages permitted")
    target_cost_sensitivity: float = Field(ge=0.0, le=1.0, description="Cost aversion weight (1.0 = highly cost sensitive)")
    allowed_premium_behavior: bool = Field(description="Whether premium quality tiers can be activated")
    headroom_multiplier: StrictDecimal = Field(
        default=Decimal("1.00"),
        ge=Decimal("1.00"),
        le=Decimal("2.00"),
        description="Conservative multiplier applied to estimated cost during reservation",
    )


DEFAULT_COST_PROFILE_CONFIGS: Dict[CostProfile, CostProfileConfig] = {
    CostProfile.ECONOMY: CostProfileConfig(
        profile=CostProfile.ECONOMY,
        max_quality_escalations=0,
        target_cost_sensitivity=1.0,
        allowed_premium_behavior=False,
        headroom_multiplier=Decimal("1.00"),
    ),
    CostProfile.STANDARD: CostProfileConfig(
        profile=CostProfile.STANDARD,
        max_quality_escalations=1,
        target_cost_sensitivity=0.5,
        allowed_premium_behavior=False,
        headroom_multiplier=Decimal("1.05"),
    ),
    CostProfile.PREMIUM: CostProfileConfig(
        profile=CostProfile.PREMIUM,
        max_quality_escalations=2,
        target_cost_sensitivity=0.2,
        allowed_premium_behavior=True,
        headroom_multiplier=Decimal("1.10"),
    ),
    CostProfile.MAXIMUM: CostProfileConfig(
        profile=CostProfile.MAXIMUM,
        max_quality_escalations=3,
        target_cost_sensitivity=0.0,
        allowed_premium_behavior=True,
        headroom_multiplier=Decimal("1.20"),
    ),
}


def get_cost_profile_config(profile: CostProfile | str) -> CostProfileConfig:
    """Retrieves authoritative configuration parameters for a given CostProfile."""
    key = profile if isinstance(profile, CostProfile) else CostProfile(str(profile))
    return DEFAULT_COST_PROFILE_CONFIGS[key]


class BudgetPolicy(AIContractModel):
    """
    Global operational rules for the Budget & Cost Engine.
    """
    default_reservation_ttl_seconds: int = Field(
        default=300,
        gt=0,
        le=86400,
        description="Default TTL for active reservations (5 minutes)",
    )
    max_reservation_ttl_seconds: int = Field(
        default=3600,
        gt=0,
        le=86400,
        description="Maximum allowed reservation lifespan (1 hour)",
    )
    allow_overage_within_limit: bool = Field(
        default=False,
        description="If True, permits actual > reserved only if available balance can absorb delta without exceeding limit. If False, strictly rejects actual > reserved.",
    )
    default_output_token_bound: int = Field(
        default=4096,
        gt=0,
        description="Conservative output token bound when unconstrained",
    )
    supported_currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="Authoritative ISO-4217 currency code",
    )
