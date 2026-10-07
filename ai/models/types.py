"""
ai/models/types.py
==================
Strongly-typed metadata definitions and pricing structures for Model Registry (S27.3).

Invariants:
- All monetary pricing strictly uses `Decimal` (never float).
- Pricing schedules must have SemVer/timestamp versioning and timezone-aware timestamps.
- Model capabilities are validated against the canonical Capability Registry.
- Model vs Deployment distinction is supported via optional `deployment_id` and `region`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import Field, field_validator

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.common import (
    CapabilityTypeEnum,
    QualityTarget,
    QualityTargetEnum,
)
from ai.contracts.model import (
    CostTier,
    CostTierEnum,
    LatencyTier,
    LatencyTierEnum,
    ModelPricing,
)
from ai.capabilities.types import CapabilityPrivacyClass, CapabilityPrivacyClassEnum


class ModelDefinition(AIContractModel):
    """
    Authoritative metadata definition for a specific model deployment or offering.
    """
    model_id: str = Field(min_length=1, description="Canonical model identifier")
    provider_id: str = Field(min_length=1, description="Identifier of the provider supplying this model")
    display_name: str = Field(min_length=1, description="Human-readable model name")
    capabilities: List[CapabilityTypeEnum] = Field(min_length=1, description="List of domain capabilities this model supports")
    quality_profile: QualityTargetEnum = Field(description="Quality tier target")
    cost_profile: CostTierEnum = Field(description="Relative cost tier")
    latency_profile: LatencyTierEnum = Field(description="Relative latency tier")
    reliability: float = Field(ge=0.0, le=1.0, description="Historical SLA reliability score (0.0 to 1.0)")
    languages: List[str] = Field(default_factory=lambda: ["*"], description="Supported language codes")
    supports_structured_output: bool = Field(default=False, description="Whether model supports constrained JSON/grammar output")
    supports_tools: bool = Field(default=False, description="Whether model supports function calling / tool use")
    supports_audio: bool = Field(default=False, description="Whether model natively supports audio modality")
    supports_video: bool = Field(default=False, description="Whether model natively supports video modality")
    supports_batch: bool = Field(default=False, description="Whether model supports asynchronous batch queue")
    supports_cache: bool = Field(default=False, description="Whether provider supports prompt caching for this model")
    supports_streaming: bool = Field(default=False, description="Whether provider supports streaming output")
    context_limit: Optional[int] = Field(default=None, ge=1, description="Maximum context window tokens if applicable")
    privacy_class: CapabilityPrivacyClassEnum = Field(default=CapabilityPrivacyClass.PUBLIC_SAFE, description="Data privacy rating")
    region: Optional[str] = Field(default=None, description="Optional deployment region (e.g. us-east-1, eu-west-1)")
    deployment_id: Optional[str] = Field(default=None, description="Optional deployment identifier for multi-deployment topologies")
    enabled: bool = Field(default=True, description="Whether this model is active in the registry")
    pricing: Optional[ModelPricing] = Field(default=None, description="Current versioned pricing schedule")
