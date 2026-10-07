"""
ai/orchestration/repository.py
===============================
Abstract repository boundary for AIRun and AIStep persistence (S27.11).

Invariants:
- Abstract interface only; never imports raw DB drivers or executes SQL in ai/* (ADR-004 DEC-01).
- Concrete implementations in scripts/core/ handle SQL transactions, row locking, and atomic CAS.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from ai.contracts.activity import AIActivityRecord
from ai.contracts.errors import AIError
from ai.contracts.run import AIRun, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord


class AIRunRepository(ABC):
    """Authoritative storage boundary for durable AI workflows and discrete steps."""

    @abstractmethod
    def create_run(self, run: AIRun) -> AIRun:
        """Persists a new AIRun record."""
        raise NotImplementedError

    @abstractmethod
    def get_run(self, run_id: str, workspace_id: Optional[str] = None) -> Optional[AIRun]:
        """Retrieves an AIRun by ID, enforcing tenant isolation if workspace_id is provided."""
        raise NotImplementedError

    @abstractmethod
    def update_run(self, run: AIRun) -> AIRun:
        """Updates an existing AIRun record."""
        raise NotImplementedError

    @abstractmethod
    def create_steps(self, steps: List[AIStep]) -> List[AIStep]:
        """Persists a batch of AIStep records."""
        raise NotImplementedError

    @abstractmethod
    def get_step(self, step_id: str, workspace_id: Optional[str] = None) -> Optional[AIStep]:
        """Retrieves an AIStep by ID, scoped to workspace_id if provided."""
        raise NotImplementedError

    @abstractmethod
    def get_steps_for_run(self, run_id: str, workspace_id: Optional[str] = None) -> List[AIStep]:
        """Retrieves all steps belonging to an AIRun."""
        raise NotImplementedError

    @abstractmethod
    def update_step(self, step: AIStep) -> AIStep:
        """Updates an existing AIStep."""
        raise NotImplementedError

    @abstractmethod
    def claim_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        lease_duration_seconds: float,
        workspace_id: Optional[str] = None,
    ) -> Optional[AIStep]:
        """
        Atomically attempts to claim a step using CAS:
        Eligible if status == PENDING or (status == RUNNING and lease_expires_at < now).
        Returns the claimed AIStep with status RUNNING if successful, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def renew_lease(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        lease_duration_seconds: float,
    ) -> bool:
        """
        Renews an active lease for a step.
        Returns True if heartbeat/lease renewed successfully, False if lease is stale/superseded.
        """
        raise NotImplementedError

    @abstractmethod
    def complete_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        output_ref: Optional[str],
        usage: UsageRecord,
        cost: CostEstimate,
    ) -> AIStep:
        """
        Marks an AIStep as SUCCEEDED, fencing against stale worker commits.
        Raises StaleWorkerLeaseError if worker_id or lease_token does not match or lease expired.
        """
        raise NotImplementedError

    @abstractmethod
    def fail_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        error: AIError,
        next_status: AIStepStatus,
        next_retry_at: Optional[datetime] = None,
    ) -> AIStep:
        """
        Marks an AIStep as FAILED or PENDING (for retry), fencing against stale workers.
        Raises StaleWorkerLeaseError if worker lease is invalid.
        """
        raise NotImplementedError

    @abstractmethod
    def list_runnable_steps(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AIStep]:
        """
        Lists steps with status PENDING ready for execution (and where next_retry_at is in the past).
        """
        raise NotImplementedError

    @abstractmethod
    def list_expired_steps(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[AIStep]:
        """
        Lists steps with status RUNNING whose lease has expired.
        """
        raise NotImplementedError

    @abstractmethod
    def list_active_runs(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[AIRun]:
        """
        Lists runs that are in non-terminal states (PENDING, RUNNING).
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_run(
        self,
        run_id: str,
        workspace_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AIRun:
        """
        Atomically cancels an AIRun and all its non-terminal steps.
        """
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # Durable Activity Boundary (S27.11 / AI-10B)
    # -------------------------------------------------------------------------

    @abstractmethod
    def record_activity_intent(
        self,
        activity: AIActivityRecord,
        workspace_id: str,
    ) -> AIActivityRecord:
        """
        Atomically records intent to execute an external activity.
        If an activity already exists for (workspace_id, step_id, idempotency_key),
        returns the existing record (idempotent intent registration).
        """
        raise NotImplementedError

    @abstractmethod
    def get_activity(
        self,
        activity_id: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[AIActivityRecord]:
        """Retrieves an activity by ID, scoped to workspace_id if provided."""
        raise NotImplementedError

    @abstractmethod
    def get_activity_by_idempotency_key(
        self,
        workspace_id: str,
        step_id_or_idem: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        step_id: Optional[str] = None,
    ) -> Optional[AIActivityRecord]:
        """
        Retrieves an activity record by stable logical idempotency key.
        Checks step-specific activity first if step_id is provided, otherwise
        resolves across workspace scope.
        """
        raise NotImplementedError

    @abstractmethod
    def get_activities_for_step(
        self,
        step_id: str,
        workspace_id: Optional[str] = None,
    ) -> List[AIActivityRecord]:
        """Retrieves all activity records recorded for a step."""
        raise NotImplementedError

    @abstractmethod
    def update_activity(
        self,
        activity: AIActivityRecord,
        workspace_id: Optional[str] = None,
    ) -> AIActivityRecord:
        """Updates an existing activity record."""
        raise NotImplementedError

    @abstractmethod
    def mark_activity_completed(
        self,
        activity_id: str,
        output_ref: str,
        usage: UsageRecord,
        cost: CostEstimate,
        remote_op_ref: Optional[str] = None,
    ) -> AIActivityRecord:
        """Atomically transitions an activity to SUCCEEDED with durable results."""
        raise NotImplementedError

    @abstractmethod
    def mark_activity_failed(
        self,
        activity_id: str,
        error: AIError,
    ) -> AIActivityRecord:
        """Atomically transitions an activity to FAILED with structured error."""
        raise NotImplementedError

    @abstractmethod
    def mark_cost_settled(self, activity_id: str) -> bool:
        """
        Atomically marks activity cost as permanently settled.
        Returns True if this invocation performed the settlement, False if already settled.
        """
        raise NotImplementedError

