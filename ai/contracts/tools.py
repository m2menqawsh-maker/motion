"""
ai/contracts/tools.py
=====================
Contracts for controlled tool invocation and execution results.

Critical Security Boundary:
- ToolCall parameters originating from LLM completions CANNOT supply or override
  authoritative tenant identities, user roles, or permissions (ADR-004 DEC-06.6).
- Trusted execution context is injected server-side by ToolDispatcher.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Set
from typing_extensions import Self
from pydantic import Field, JsonValue, field_validator, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.errors import AIError

# Authoritative identity fields that an untrusted AI model is strictly forbidden from supplying
FORBIDDEN_TOOL_IDENTITY_FIELDS: Set[str] = {
    "workspace_id",
    "actor_id",
    "user_id",
    "approved_by",
    "permission",
    "role",
    "tenant_id",
}


class ToolCallStatus(str, Enum):
    """Outcome status of an executed tool call."""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


ToolCallStatusEnum = strict_enum(ToolCallStatus)


class ToolCall(AIContractModel):
    """
    Contract representing a request to invoke an authorized tool.
    Originates from model completion and is subject to strict parameter policy enforcement.
    """
    call_id: str = Field(
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Unique identifier for matching tool execution results",
    )
    tool_name: str = Field(
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Canonical identifier of the requested tool",
    )
    parameters: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Tool input arguments validated against the tool schema",
    )
    untrusted_metadata: Optional[Dict[str, JsonValue]] = Field(
        default=None,
        description="Non-authoritative contextual metadata emitted by the model",
    )

    @field_validator("parameters")
    @classmethod
    def validate_identity_isolation(cls, params: Dict[str, JsonValue]) -> Dict[str, JsonValue]:
        violating = FORBIDDEN_TOOL_IDENTITY_FIELDS.intersection(params.keys())
        if violating:
            raise ValueError(
                f"Security violation: ToolCall parameters cannot specify authoritative identity "
                f"or permission fields: {sorted(violating)}. These must be injected by server-side runtime."
            )
        return params


class ToolResult(AIContractModel):
    """
    Contract representing the completed execution of an authorized tool.
    Returned to the orchestration loop.
    """
    call_id: str = Field(
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Identifier matching the originating ToolCall",
    )
    status: ToolCallStatusEnum = Field(description="Execution outcome status")
    output: Optional[Dict[str, JsonValue]] = Field(
        default=None,
        description="Structured return payload from successful tool execution",
    )
    error: Optional[AIError] = Field(
        default=None,
        description="Structured error details if tool execution failed",
    )
    started_at: TzAwareDatetime = Field(description="Timezone-aware start timestamp")
    completed_at: TzAwareDatetime = Field(description="Timezone-aware completion timestamp")
    duration_ms: int = Field(ge=0, description="Measured execution duration in milliseconds")

    @model_validator(mode="after")
    def validate_invariants(self) -> Self:
        if self.completed_at < self.started_at:
            raise ValueError(
                f"completed_at ({self.completed_at.isoformat()}) must not precede started_at ({self.started_at.isoformat()})"
            )
        if self.status == ToolCallStatus.SUCCESS:
            if self.error is not None:
                raise ValueError("ToolResult with status SUCCESS cannot contain an error")
        elif self.status == ToolCallStatus.ERROR:
            if self.error is None:
                raise ValueError("ToolResult with status ERROR must provide a structured error")
        return self
