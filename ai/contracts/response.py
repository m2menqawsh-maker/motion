"""
ai/contracts/response.py
========================
Canonical response contract emitted by the AI subsystem.

Invariants:
- Provider-neutral: represents normalized AI output, usage, and cost.
- Coherence: SUCCEEDED cannot hold an error; FAILED must provide an AIError.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from typing_extensions import Self
from pydantic import Field, JsonValue, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.errors import AIError
from ai.contracts.usage import CostEstimate, UsageRecord


class AIResponseStatus(str, Enum):
    """Canonical completion status of an AI subsystem response."""
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


AIResponseStatusEnum = strict_enum(AIResponseStatus)


class AIResponse(AIContractModel):
    """
    Canonical response contract returned by the AI subsystem.
    Contains structured output, standardized metrics, and optional diagnostic error.
    """
    request_id: str = Field(min_length=1, description="Identifier of the matching AIRequest")
    run_id: Optional[str] = Field(default=None, description="Identifier of the background AIRun if applicable")
    status: AIResponseStatusEnum = Field(description="High-level completion status")
    result: Optional[Dict[str, JsonValue]] = Field(
        default=None,
        description="Structured normalized output payload on success",
    )
    usage: UsageRecord = Field(default_factory=UsageRecord, description="Normalized resource consumption")
    cost: CostEstimate = Field(description="Monetary cost breakdown for this execution")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings or policy advisories")
    error: Optional[AIError] = Field(default=None, description="Structured error details if execution failed")
    created_at: TzAwareDatetime = Field(description="Timezone-aware response emission timestamp")
    contract_version: str = Field(default="1.0.0", description="SemVer version of this contract")

    @model_validator(mode="after")
    def validate_status_error_coherence(self) -> Self:
        if self.status == AIResponseStatus.SUCCEEDED:
            if self.error is not None:
                raise ValueError("AIResponse with status SUCCEEDED cannot contain an error")
        elif self.status == AIResponseStatus.FAILED:
            if self.error is None:
                raise ValueError("AIResponse with status FAILED must provide a structured error")
        return self
