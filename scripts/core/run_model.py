"""
Run Domain Model & Canonical Lifecycle for S21.

Defines the RunRecord, RunStatus state machine, and data invariants.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class RunStatus(str, Enum):
    """Canonical states for a Pipeline Run."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"  # Reserved for S22
    CANCELLED = "CANCELLED"                # Reserved for S22


TERMINAL_STATUSES = {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}


class InvalidRunTransitionError(ValueError):
    """Raised when an illegal run status transition is attempted."""
    pass


class RunRecord(BaseModel):
    """Canonical domain model for a pipeline execution run."""
    run_id: str
    workspace_id: str = "ws_default"
    project_id: str
    status: RunStatus = RunStatus.QUEUED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    attempt: int = 1
    worker_id: Optional[str] = None
    lease_expires_at: Optional[str] = None
    input_revision: Optional[int] = None
    canonical_document_revision: Optional[int] = None
    canonical_blueprint_sha256: Optional[str] = None
    immutable_storage_key: Optional[str] = None
    approved_review_bundle_id: Optional[str] = None
    lifecycle_state_revision: Optional[int] = None
    idempotency_key: Optional[str] = None
    request_payload_hash: Optional[str] = None
    failure_code: Optional[str] = None
    failure_detail: Optional[Dict[str, Any]] = None
    result_reference: Optional[Dict[str, Any]] = None

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def assert_can_transition_to(self, new_status: RunStatus) -> None:
        """Validates that the status transition is strictly legal according to invariants."""
        if self.status == new_status:
            return

        if self.is_terminal:
            raise InvalidRunTransitionError(
                f"Cannot transition terminal run {self.run_id} from {self.status.value} to {new_status.value}."
            )

        allowed = {
            RunStatus.QUEUED: {RunStatus.RUNNING, RunStatus.CANCEL_REQUESTED, RunStatus.CANCELLED},
            RunStatus.RUNNING: {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.QUEUED, RunStatus.CANCEL_REQUESTED, RunStatus.CANCELLED},
            RunStatus.CANCEL_REQUESTED: {RunStatus.CANCELLED, RunStatus.FAILED, RunStatus.SUCCEEDED},
        }

        permitted_targets = allowed.get(self.status, set())
        if new_status not in permitted_targets:
            raise InvalidRunTransitionError(
                f"Illegal run status transition for {self.run_id}: {self.status.value} -> {new_status.value}."
            )


class RunEvent(BaseModel):
    """Canonical domain model for a persistent Run Event (S22 - LED-060)."""
    event_id: str
    workspace_id: str = "ws_default"
    run_id: str
    project_id: str
    sequence: int
    event_type: str
    stage: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any] = Field(default_factory=dict)
