"""
ai/capabilities/types.py
========================
Strongly-typed metadata structures and enums for the Capability Registry (S27.2).

Invariants:
- All capabilities are provider-neutral domain concepts.
- No free-form dict[str, Any] in contract bindings.
- Fully typed execution, privacy, caching, and cost metadata.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional
from pydantic import Field, field_validator

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.common import CapabilityType, CapabilityTypeEnum, ExecutionClass, ExecutionClassEnum


class CachePolicy(str, Enum):
    """Caching policy governing invocation results for a capability."""
    NEVER = "NEVER"
    DETERMINISTIC = "DETERMINISTIC"
    CONTENT_HASH = "CONTENT_HASH"
    PROVIDER_DEPENDENT = "PROVIDER_DEPENDENT"


class CapabilityPrivacyClass(str, Enum):
    """Inherent privacy and data sensitivity classification for a capability."""
    PUBLIC_SAFE = "PUBLIC_SAFE"              # Safe for public multi-tenant cloud APIs
    SENSITIVE_ALLOWED = "SENSITIVE_ALLOWED"  # May handle user biometrics/voice under enterprise zero-retention
    LOCAL_ONLY = "LOCAL_ONLY"                # Must execute exclusively on local/on-prem hardware
    RESTRICTED = "RESTRICTED"                # Strictly gated or compliance-restricted workload


class CostUnit(str, Enum):
    """Canonical metering unit for capability billing calculations."""
    TOKENS = "TOKENS"
    CHARACTERS = "CHARACTERS"
    AUDIO_SECONDS = "AUDIO_SECONDS"
    VIDEO_SECONDS = "VIDEO_SECONDS"
    IMAGES = "IMAGES"
    REQUESTS = "REQUESTS"
    FRAMES = "FRAMES"


CachePolicyEnum = strict_enum(CachePolicy)
CapabilityPrivacyClassEnum = strict_enum(CapabilityPrivacyClass)
CostUnitEnum = strict_enum(CostUnit)


class ContractBindingRef(AIContractModel):
    """
    Explicit, versioned reference to an input/output contract schema.
    Prevents untyped dict[str, Any] escapes while allowing schema decoupling.
    """
    contract_id: str = Field(min_length=3, description="Canonical contract identifier URI or dotted path")
    version: str = Field(default="1.0.0", description="SemVer version of the contract definition")
    schema_ref: Optional[str] = Field(default=None, description="Optional relative or absolute schema identifier")

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Contract version must be valid SemVer (e.g. 1.0.0), got: {v}")
        return v


class CapabilityDefinition(AIContractModel):
    """
    Authoritative, typed definition for a domain capability in S27.
    """
    id: CapabilityTypeEnum = Field(description="Canonical provider-neutral capability identifier")
    version: str = Field(default="1.0.0", description="SemVer version of this capability definition")
    description: str = Field(min_length=5, description="Domain-level description of capability purpose")
    input_contract: ContractBindingRef = Field(description="Typed binding for request payload")
    output_contract: ContractBindingRef = Field(description="Typed binding for result payload")
    supports_batch: bool = Field(default=False, description="Whether capability supports batch execution")
    supports_streaming: bool = Field(default=False, description="Whether capability supports streaming execution")
    cache_policy: CachePolicyEnum = Field(description="Contract-level caching policy")
    privacy_class: CapabilityPrivacyClassEnum = Field(description="Privacy and data isolation classification")
    cost_unit: CostUnitEnum = Field(description="Canonical resource metering unit")
    media_types: List[str] = Field(min_length=1, description="Associated media modalities (e.g., text, audio, image, video)")
    execution_tier: ExecutionClassEnum = Field(description="Default latency and scheduling tier")

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Capability version must be valid SemVer (e.g. 1.0.0), got: {v}")
        return v
