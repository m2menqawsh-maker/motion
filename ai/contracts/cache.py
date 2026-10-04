"""
ai/contracts/cache.py
=====================
Strongly-typed contracts for AI Artifact Cache and request deduplication (S27.12).

Invariants:
- Cache identity is deterministic, provider-neutral, and tenant-isolated.
- Cache entries are strongly typed; no unrestricted dict[str, Any] at boundaries.
- Output references point to authoritative object storage (StorageService).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, Optional
from typing_extensions import Self
from pydantic import Field, JsonValue, field_validator, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import CapabilityType, CapabilityTypeEnum
from ai.contracts.errors import AIError


class CacheEntryStatus(str, Enum):
    """Lifecycle status of an AI cache entry."""
    IN_FLIGHT = "IN_FLIGHT"
    READY = "READY"
    FAILED = "FAILED"


CacheEntryStatusEnum = strict_enum(CacheEntryStatus)


class AICacheKeyParams(AIContractModel):
    """
    Input dimensions required to derive a deterministic canonical cache key.
    Server-side constructed; never directly supplied or manipulated by models.
    """
    workspace_id: str = Field(min_length=1, description="Tenant boundary isolation key")
    capability: CapabilityTypeEnum = Field(description="Target domain capability")
    input_data: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Structured typed input payload for the capability",
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="Deterministic content hash of media assets or raw inputs",
    )
    settings: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Hyperparameters, quality targets, or generation settings affecting the output",
    )
    model: Optional[str] = Field(
        default=None,
        description="Target model identifier if capability result is model-dependent",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Version string of the target model",
    )
    contract_version: str = Field(
        default="1.0.0",
        description="SemVer of the capability contract definition",
    )
    prompt_version: str = Field(
        default="1.0.0",
        description="SemVer or content hash of the prompt template / system prompt",
    )
    analysis_version: str = Field(
        default="1.0.0",
        description="SemVer of the processing / analysis logic",
    )

    @field_validator("contract_version", "prompt_version", "analysis_version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError(f"Version must be valid SemVer (e.g. 1.0.0), got: {v}")
        return v


class AICacheEntry(AIContractModel):
    """
    Authoritative typed record representing a cached AI execution artifact.
    """
    cache_key: str = Field(min_length=8, description="Canonical SHA-256 derived cache identifier")
    workspace_id: str = Field(min_length=1, description="Tenant isolation boundary")
    capability: CapabilityTypeEnum = Field(description="Associated domain capability")
    input_hash: str = Field(min_length=8, description="Canonical SHA-256 of normalized inputs")
    status: CacheEntryStatusEnum = Field(description="Current status of the cache record")
    output_ref: Optional[str] = Field(
        default=None,
        description="Storage key pointing to persisted artifact in StorageService",
    )
    producer: Optional[str] = Field(
        default=None,
        description="Provider or worker that generated the result",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model identifier used for generation",
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Version of model used for generation",
    )
    contract_version: str = Field(default="1.0.0", description="SemVer of the contract")
    prompt_version: str = Field(default="1.0.0", description="SemVer or hash of prompt")
    analysis_version: str = Field(default="1.0.0", description="SemVer of analysis logic")
    created_at: TzAwareDatetime = Field(description="Creation timestamp of cache entry")
    expires_at: Optional[TzAwareDatetime] = Field(default=None, description="Optional TTL expiration timestamp")
    owner_id: Optional[str] = Field(default=None, description="Worker identifier currently leasing in-flight execution")
    lease_token: Optional[str] = Field(default=None, description="Monotonic lease fencing token")
    lease_expires_at: Optional[TzAwareDatetime] = Field(default=None, description="Lease deadline for crash recovery")
    activity_id: Optional[str] = Field(default=None, description="Shared durable activity identifier")
    activity_idempotency_key: Optional[str] = Field(default=None, description="Durable execution identity for shared activity")
    generation: int = Field(default=1, ge=1, description="Logical cache computation generation")
    error: Optional[AIError] = Field(default=None, description="Structured error if execution failed")


    @model_validator(mode="after")
    def validate_coherence(self) -> Self:
        if self.status == CacheEntryStatus.READY:
            if not self.output_ref:
                raise ValueError("Cache entry with status READY must have an output_ref")
            if self.error is not None:
                raise ValueError("Cache entry with status READY cannot hold an error")
        elif self.status == CacheEntryStatus.FAILED:
            if self.error is None:
                raise ValueError("Cache entry with status FAILED must provide a structured error")
        return self
