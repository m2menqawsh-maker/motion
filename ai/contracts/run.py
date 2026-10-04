"""
ai/contracts/run.py
===================
Contracts for durable AI workflow execution (runs and steps).

Invariants:
- Contract models only; orchestrator/worker execution logic deferred to S27.10.
- Strict timestamp ordering: completed_at >= started_at >= created_at.
- Status coherence: SUCCEEDED cannot hold an error; FAILED must provide an error.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from typing_extensions import Self
from pydantic import Field, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import CapabilityType, CapabilityTypeEnum, ExecutionClass, ExecutionClassEnum
from ai.contracts.errors import AIError
from ai.contracts.usage import CostEstimate, UsageRecord



class AIRunStatus(str, Enum):
    """Lifecycle status of a multi-step AI run DAG."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


AIRunStatusEnum = strict_enum(AIRunStatus)


class AIStepStatus(str, Enum):
    """Lifecycle status of an individual step within an AI run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


AIStepStatusEnum = strict_enum(AIStepStatus)


class AIRun(AIContractModel):
    """
    Contract representing an asynchronous or multi-step AI execution pipeline.
    Tracks state, aggregated usage, costs, and failure diagnostics.
    """
    run_id: str = Field(min_length=1, description="Unique run identifier")
    workspace_id: str = Field(min_length=1, description="Mandatory tenant workspace identifier")
    project_id: Optional[str] = Field(default=None, description="Optional associated project identifier")
    session_id: Optional[str] = Field(default=None, description="Optional interactive session identifier")
    status: AIRunStatusEnum = Field(description="Current execution lifecycle status")
    capability: CapabilityTypeEnum = Field(description="Primary capability or workflow goal")
    workflow_ref: Optional[str] = Field(default=None, description="Workflow recipe or DAG definition reference")
    created_at: TzAwareDatetime = Field(description="Timezone-aware creation timestamp")
    started_at: Optional[TzAwareDatetime] = Field(default=None, description="Execution start timestamp")
    completed_at: Optional[TzAwareDatetime] = Field(default=None, description="Completion timestamp")
    usage: UsageRecord = Field(default_factory=UsageRecord, description="Aggregated resource usage")
    cost: CostEstimate = Field(description="Aggregated monetary cost")
    error: Optional[AIError] = Field(default=None, description="Terminal error if status is FAILED")
    contract_version: str = Field(default="1.0.0", description="SemVer version of this contract")
    execution_class: ExecutionClassEnum = Field(default=ExecutionClass.INTERACTIVE, description="Execution latency and scheduling tier")
    prompt_id: Optional[str] = Field(default=None, description="Canonical prompt identifier")
    prompt_version: Optional[str] = Field(default=None, description="Approved version of canonical prompt")
    prompt_hash: Optional[str] = Field(default=None, description="Deterministic content hash of canonical prompt")

    @model_validator(mode="after")
    def validate_invariants(self) -> Self:
        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError(f"started_at ({self.started_at.isoformat()}) cannot precede created_at ({self.created_at.isoformat()})")
        if self.completed_at is not None and self.started_at is not None and self.completed_at < self.started_at:
            raise ValueError(f"completed_at ({self.completed_at.isoformat()}) cannot precede started_at ({self.started_at.isoformat()})")
        if self.status == AIRunStatus.SUCCEEDED and self.error is not None:
            raise ValueError("AIRun with status SUCCEEDED cannot hold an error")
        if self.status == AIRunStatus.FAILED and self.error is None:
            raise ValueError("AIRun with status FAILED must provide a structured error")
        return self


class AIStep(AIContractModel):
    """
    Contract representing an individual discrete unit of work within an AIRun.
    Tracks step attempt, leased execution, and invocation inputs/outputs.
    """
    step_id: str = Field(min_length=1, description="Unique step identifier within the run")
    run_id: str = Field(min_length=1, description="Parent AIRun identifier")
    status: AIStepStatusEnum = Field(description="Step lifecycle status")
    attempt: int = Field(default=1, ge=1, description="Execution attempt counter (1-indexed)")
    capability: CapabilityTypeEnum = Field(description="Capability executed in this step")
    input_ref: Optional[str] = Field(default=None, description="Reference to input artifact or storage key")
    output_ref: Optional[str] = Field(default=None, description="Reference to output artifact or storage key")
    provider: Optional[str] = Field(default=None, description="Resolved provider adapter identifier")
    model: Optional[str] = Field(default=None, description="Resolved model identifier")
    usage: UsageRecord = Field(default_factory=UsageRecord, description="Resource consumption for this step")
    cost: CostEstimate = Field(description="Monetary cost for this step")
    error: Optional[AIError] = Field(default=None, description="Step error details if status is FAILED")
    created_at: TzAwareDatetime = Field(description="Timezone-aware step creation timestamp")
    started_at: Optional[TzAwareDatetime] = Field(default=None, description="Step start timestamp")
    completed_at: Optional[TzAwareDatetime] = Field(default=None, description="Step completion timestamp")
    prompt_id: Optional[str] = Field(default=None, description="Canonical prompt identifier for this step")
    prompt_version: Optional[str] = Field(default=None, description="Version of prompt used for this step")
    prompt_hash: Optional[str] = Field(default=None, description="Content hash of prompt used for this step")

    # Durable Execution & Lease Metadata (S27.11)
    worker_id: Optional[str] = Field(default=None, description="Worker identifier holding the lease")
    lease_token: Optional[str] = Field(default=None, description="Fencing lease token generation")
    lease_expires_at: Optional[TzAwareDatetime] = Field(default=None, description="Lease expiration timestamp")
    heartbeat_at: Optional[TzAwareDatetime] = Field(default=None, description="Last recorded heartbeat timestamp")
    input_hash: Optional[str] = Field(default=None, description="Deterministic content hash of inputs")
    idempotency_key: Optional[str] = Field(default=None, description="Logical idempotency deduplication key")
    dependencies: list[str] = Field(default_factory=list, description="IDs of prerequisite steps in DAG")
    max_attempts: int = Field(default=3, ge=1, description="Maximum allowed execution attempts")
    next_retry_at: Optional[TzAwareDatetime] = Field(default=None, description="Scheduled earliest retry timestamp")

    @model_validator(mode="after")
    def validate_invariants(self) -> Self:
        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError(f"started_at ({self.started_at.isoformat()}) cannot precede created_at ({self.created_at.isoformat()})")
        if self.completed_at is not None and self.started_at is not None and self.completed_at < self.started_at:
            raise ValueError(f"completed_at ({self.completed_at.isoformat()}) cannot precede started_at ({self.started_at.isoformat()})")
        if self.status == AIStepStatus.SUCCEEDED and self.error is not None:
            raise ValueError("AIStep with status SUCCEEDED cannot hold an error")
        if self.status == AIStepStatus.FAILED and self.error is None:
            raise ValueError("AIStep with status FAILED must provide a structured error")
        return self
