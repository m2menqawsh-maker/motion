"""
ai/contracts/activity.py
=========================
Contracts for durable external activities (providers, MCPs, side-effecting tools) (S27.11).

Invariants:
- Typed contracts representing discrete durable activities executed outside local DB transaction.
- Explicit idempotency semantics (AT_MOST_ONCE, AT_LEAST_ONCE, EFFECTIVELY_ONCE).
- Persistent state tracking remote operation references and cost settlement.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from typing_extensions import Self
from pydantic import Field, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.errors import AIError
from ai.contracts.usage import CostEstimate, UsageRecord


class ActivityStatus(str, Enum):
    """Lifecycle status of a durable activity."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ActivityStatusEnum = strict_enum(ActivityStatus)


class IdempotencySemantics(str, Enum):
    """Authoritative execution semantics for external activities."""
    AT_MOST_ONCE = "AT_MOST_ONCE"
    AT_LEAST_ONCE = "AT_LEAST_ONCE"
    EFFECTIVELY_ONCE = "EFFECTIVELY_ONCE"


IdempotencySemanticsEnum = strict_enum(IdempotencySemantics)


class AIActivityRecord(AIContractModel):
    """
    Durable record representing an external operation (provider generation, MCP call, tool side-effect).
    """
    activity_id: str = Field(min_length=1, description="Unique identifier for the activity execution")
    run_id: str = Field(min_length=1, description="Associated AIRun identifier")
    step_id: str = Field(min_length=1, description="Associated AIStep identifier")
    idempotency_key: str = Field(min_length=1, description="Stable logical deduplication key")
    status: ActivityStatusEnum = Field(description="Current execution lifecycle status")
    semantics: IdempotencySemanticsEnum = Field(
        default=IdempotencySemantics.EFFECTIVELY_ONCE,
        description="Execution idempotency guarantee classification",
    )
    started_at: Optional[TzAwareDatetime] = Field(default=None, description="Activity start timestamp")
    completed_at: Optional[TzAwareDatetime] = Field(default=None, description="Activity completion timestamp")
    provider: Optional[str] = Field(default=None, description="Resolved provider adapter identifier")
    model: Optional[str] = Field(default=None, description="Resolved model identifier")
    remote_operation_ref: Optional[str] = Field(default=None, description="Remote provider request ID or reference")
    output_ref: Optional[str] = Field(default=None, description="Persistent output artifact or storage reference")
    error: Optional[AIError] = Field(default=None, description="Error details if activity failed")
    cost: Optional[CostEstimate] = Field(default=None, description="Estimated/actual cost of activity")
    usage: Optional[UsageRecord] = Field(default=None, description="Resource consumption of activity")
    cost_settled: bool = Field(default=False, description="Whether cost has been permanently settled in ledger")
    reservation_id: Optional[str] = Field(default=None, description="Associated budget reservation identifier")
    created_at: TzAwareDatetime = Field(description="Creation timestamp of activity record")

    @model_validator(mode="after")
    def validate_invariants(self) -> Self:
        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError(f"started_at ({self.started_at.isoformat()}) cannot precede created_at ({self.created_at.isoformat()})")
        if self.completed_at is not None and self.started_at is not None and self.completed_at < self.started_at:
            raise ValueError(f"completed_at ({self.completed_at.isoformat()}) cannot precede started_at ({self.started_at.isoformat()})")
        if self.status == ActivityStatus.SUCCEEDED and self.error is not None:
            raise ValueError("AIActivityRecord with status SUCCEEDED cannot hold an error")
        if self.status == ActivityStatus.FAILED and self.error is None:
            raise ValueError("AIActivityRecord with status FAILED must provide a structured error")
        return self
