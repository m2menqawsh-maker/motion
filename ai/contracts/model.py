"""
ai/contracts/model.py
=====================
Contracts for model selection criteria and routing decisions.

Invariants:
- Provider-neutral: represents capabilities, constraints, and features rather than hardcoded APIs.
- ModelSelection fallbacks must not duplicate the primary selection or each other.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from typing_extensions import Self
from pydantic import Field, field_validator, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import (
    CapabilityType,
    CapabilityTypeEnum,
    ExecutionClass,
    ExecutionClassEnum,
    PrivacyRequirement,
    PrivacyRequirementEnum,
    QualityTarget,
    QualityTargetEnum,
)
from ai.contracts.usage import CostEstimate

# Canonical recognized provider IDs across S27/S28 platform
CANONICAL_PROVIDER_IDS = frozenset({
    "openai",
    "gemini",
    "anthropic",
    "elevenlabs",
    "fal",
    "replicate",
    "local",
    "mcp",
    "openrouter",
    "mock",
})


class CostTier(str, Enum):
    """Relative cost profile tier of a model."""
    FREE = "FREE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class LatencyTier(str, Enum):
    """Expected operational latency profile."""
    REALTIME = "REALTIME"    # < 500ms
    FAST = "FAST"            # 500ms - 2s
    MODERATE = "MODERATE"    # 2s - 10s
    SLOW = "SLOW"            # > 10s (e.g. video rendering)


CostTierEnum = strict_enum(CostTier)
LatencyTierEnum = strict_enum(LatencyTier)


class ModelPricing(AIContractModel):
    """
    Versioned, auditable pricing definition for model execution.
    Strictly Decimal-backed to prevent floating-point rounding errors.
    """
    pricing_version: str = Field(min_length=1, description="Pricing schedule identifier or revision tag")
    valid_from: TzAwareDatetime = Field(description="Timezone-aware activation datetime")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO-4217 currency code")
    input_token_price: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Cost per input token")
    output_token_price: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Cost per output token")
    audio_minute_price: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Cost per audio minute")
    video_minute_price: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Cost per video minute")
    image_price: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Cost per generated image")
    character_price: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Cost per synthesized character")
    request_price: Optional[Decimal] = Field(default=None, ge=Decimal(0), description="Flat invocation fee per request")

    @field_validator(
        "input_token_price",
        "output_token_price",
        "audio_minute_price",
        "video_minute_price",
        "image_price",
        "character_price",
        "request_price",
        mode="before",
    )
    @classmethod
    def reject_float_pricing(cls, v):
        if isinstance(v, float):
            raise ValueError("Float values are strictly forbidden for pricing to prevent rounding errors; use Decimal or string")
        return v

    @field_validator("valid_from")
    @classmethod
    def validate_timezone_awareness(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("valid_from must be a timezone-aware datetime")
        return v


class ModelRequirement(AIContractModel):
    """
    Contract representing caller requirements and constraints for model resolution.
    Used by future capability routers to score and select optimal deployments.
    """
    capability: CapabilityTypeEnum = Field(description="Target capability required for execution")
    quality_target: QualityTargetEnum = Field(
        default=QualityTarget.STANDARD,
        description="Target quality tier",
    )
    budget_constraint: Optional[CostEstimate] = Field(
        default=None,
        description="Upper budget ceiling allowed for this operation",
    )
    max_latency_ms: Optional[int] = Field(
        default=None,
        gt=0,
        description="Maximum acceptable execution latency in milliseconds",
    )
    language: Optional[str] = Field(
        default=None,
        description="ISO 639-1 language code or BCP 47 tag (e.g. 'en', 'ar')",
    )
    privacy_requirement: PrivacyRequirementEnum = Field(
        default=PrivacyRequirement.PUBLIC_ALLOWED,
        description="Data retention and isolation requirement",
    )
    media_type: Optional[str] = Field(
        default=None,
        description="MIME type of primary media input/output (e.g. 'audio/wav', 'image/png')",
    )
    required_features: List[str] = Field(
        default_factory=list,
        description="List of feature tags required from candidate models (e.g. 'streaming', 'vision')",
    )
    execution_class: Optional[ExecutionClassEnum] = Field(
        default=None,
        description="Execution tier requirement (INTERACTIVE, BACKGROUND, BATCH)",
    )


class ModelSelection(AIContractModel):
    """
    Contract representing the outcome of a routing decision.
    Identifies the primary deployment candidate and ranked fallbacks.
    """
    primary_model: str = Field(min_length=1, description="Resolved primary model identifier")
    fallback_candidates: List[str] = Field(
        default_factory=list,
        description="Ranked fallback candidate identifiers",
    )
    reason_code: str = Field(min_length=1, description="Deterministic reason code for this selection")
    estimated_cost: CostEstimate = Field(description="Estimated cost of executing with primary model")

    @model_validator(mode="after")
    def validate_fallbacks(self) -> Self:
        if self.primary_model in self.fallback_candidates:
            raise ValueError(
                f"fallback_candidates must not contain primary_model '{self.primary_model}'"
            )
        if len(self.fallback_candidates) != len(set(self.fallback_candidates)):
            raise ValueError("fallback_candidates contains duplicate candidate entries")
        return self
