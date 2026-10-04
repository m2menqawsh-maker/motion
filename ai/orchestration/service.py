"""
ai/orchestration/service.py
============================
High-level domain orchestrator for durable AI workflow execution (S27.11).

Invariants:
- AI has NO direct lifecycle or QC authority.
- Every state mutation is mediated by AIRunRepository with atomic transactions.
- DAG dependency resolution guarantees newly runnable children transition exactly once.
- Terminal failure propagation cascades to all downstream descendants.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from ai.contracts.common import CapabilityTypeEnum, ExecutionClass
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.run import AIRun, AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.dag import DAGSpecification, DAGValidator, StepDefinition
from ai.orchestration.errors import (
    RunNotFoundError,
    StepNotFoundError,
    TenantAccessDeniedError,
)
from ai.orchestration.lease import generate_lease_token
from ai.orchestration.repository import AIRunRepository
from ai.orchestration.retry import RetryPolicy


class AIRunService:
    """
    Authoritative service coordinating durable AI runs, DAG progression,
    worker leasing, and failure cascade propagation.
    """

    def __init__(
        self,
        repository: AIRunRepository,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self.repository = repository
        self.retry_policy = retry_policy or RetryPolicy()

    # -------------------------------------------------------------------------
    # Run Lifecycle Management
    # -------------------------------------------------------------------------

    def create_run(
        self,
        workspace_id: str,
        capability: CapabilityTypeEnum,
        dag_spec: DAGSpecification,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        execution_class: ExecutionClass = ExecutionClass.INTERACTIVE,
        prompt_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        prompt_hash: Optional[str] = None,
    ) -> AIRun:
        """
        Validates the DAG specification and persists a new AIRun with its initial steps.
        Root steps (0 dependencies) start in PENDING.
        Dependent steps start in WAITING.
        """
        if not workspace_id:
            raise TenantAccessDeniedError("Cannot create AIRun without a valid workspace_id.")

        # 1. Structural DAG validation (detects cycles, duplicates, self-deps)
        validator = DAGValidator(dag_spec)
        now_dt = datetime.now(timezone.utc)
        run_id = f"airun_{uuid.uuid4().hex}"

        # 2. Persist parent AIRun
        run = AIRun(
            run_id=run_id,
            workspace_id=workspace_id,
            project_id=project_id,
            session_id=session_id,
            status=AIRunStatus.PENDING,
            capability=capability,
            workflow_ref=dag_spec.workflow_ref,
            created_at=now_dt,
            started_at=None,
            completed_at=None,
            usage=UsageRecord(),
            cost=CostEstimate(estimated_cost="0.00"),
            error=None,
            contract_version="1.0.0",
            execution_class=execution_class,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
        )
        self.repository.create_run(run)

        # 3. Create discrete AIStep records
        steps: List[AIStep] = []
        root_steps = set(validator.get_root_steps())

        for step_def in dag_spec.steps:
            initial_status = (
                AIStepStatus.PENDING if step_def.step_id in root_steps else AIStepStatus.WAITING
            )
            step = AIStep(
                step_id=f"{run_id}_{step_def.step_id}",
                run_id=run_id,
                status=initial_status,
                attempt=1,
                capability=step_def.capability,
                input_ref=step_def.input_ref,
                output_ref=None,
                provider=step_def.provider,
                model=step_def.model,
                usage=UsageRecord(),
                cost=CostEstimate(estimated_cost="0.00"),
                error=None,
                created_at=now_dt,
                started_at=None,
                completed_at=None,
                worker_id=None,
                lease_token=None,
                lease_expires_at=None,
                heartbeat_at=None,
                input_hash=None,
                idempotency_key=step_def.idempotency_key,
                # Store normalized internal step IDs for dependency tracking
                dependencies=[f"{run_id}_{dep}" for dep in step_def.dependencies],
                max_attempts=step_def.max_attempts,
                next_retry_at=None,
                prompt_id=step_def.prompt_id or prompt_id,
                prompt_version=step_def.prompt_version or prompt_version,
                prompt_hash=step_def.prompt_hash or prompt_hash,
            )
            steps.append(step)

        self.repository.create_steps(steps)
        return run

    def get_run(self, run_id: str, workspace_id: Optional[str] = None) -> Optional[AIRun]:
        """Retrieves an AIRun, enforcing tenant boundaries."""
        return self.repository.get_run(run_id, workspace_id=workspace_id)

    def get_step(self, step_id: str, workspace_id: Optional[str] = None) -> Optional[AIStep]:
        """Retrieves an individual step, enforcing tenant boundaries."""
        return self.repository.get_step(step_id, workspace_id=workspace_id)

    def get_run_steps(self, run_id: str, workspace_id: Optional[str] = None) -> List[AIStep]:
        """Retrieves all steps belonging to an AIRun."""
        return self.repository.get_steps_for_run(run_id, workspace_id=workspace_id)

    def list_runnable_steps(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AIStep]:
        """Lists steps currently eligible for worker claims."""
        return self.repository.list_runnable_steps(workspace_id=workspace_id, limit=limit)

    # -------------------------------------------------------------------------
    # Worker Claim and Execution Control
    # -------------------------------------------------------------------------

    def claim_next_runnable_step(
        self,
        worker_id: str,
        workspace_id: Optional[str] = None,
        lease_duration_seconds: float = 30.0,
    ) -> Optional[AIStep]:
        """
        Attempts to claim the next available runnable step atomically.
        Cycles through eligible steps until a claim succeeds or all candidates are exhausted.
        """
        runnable = self.list_runnable_steps(workspace_id=workspace_id, limit=20)
        for candidate in runnable:
            token = generate_lease_token()
            claimed = self.repository.claim_step(
                step_id=candidate.step_id,
                worker_id=worker_id,
                lease_token=token,
                lease_duration_seconds=lease_duration_seconds,
                workspace_id=workspace_id,
            )
            if claimed:
                return claimed
        return None

    def heartbeat_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        lease_duration_seconds: float = 30.0,
    ) -> bool:
        """Extends worker lease validity and records active worker heartbeat."""
        return self.repository.renew_lease(
            step_id=step_id,
            worker_id=worker_id,
            lease_token=lease_token,
            lease_duration_seconds=lease_duration_seconds,
        )

    def complete_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        output_ref: Optional[str] = None,
        usage: Optional[UsageRecord] = None,
        cost: Optional[CostEstimate] = None,
    ) -> AIStep:
        """
        Completes step execution and evaluates DAG progression.
        Transitions newly runnable dependent children from WAITING to PENDING.
        If all steps in the run are SUCCEEDED, marks the AIRun as SUCCEEDED.
        """
        resolved_usage = usage or UsageRecord()
        resolved_cost = cost or CostEstimate(estimated_cost="0.00", actual_cost="0.00")

        # 1. Mark step as SUCCEEDED with stale worker fencing
        step = self.repository.complete_step(
            step_id=step_id,
            worker_id=worker_id,
            lease_token=lease_token,
            output_ref=output_ref,
            usage=resolved_usage,
            cost=resolved_cost,
        )

        # 2. Evaluate DAG progression for the parent run
        all_steps = self.repository.get_steps_for_run(step.run_id)
        step_status_map = {s.step_id: s.status for s in all_steps}

        # Progress dependent children whose prerequisites are now fully satisfied
        for child in all_steps:
            if child.status == AIStepStatus.WAITING:
                all_parents_done = all(
                    step_status_map.get(dep) == AIStepStatus.SUCCEEDED
                    for dep in child.dependencies
                )
                if all_parents_done:
                    # Transition child from WAITING to PENDING (runnable)
                    updated_child = child.model_copy(
                        update={"status": AIStepStatus.PENDING}
                    )
                    self.repository.update_step(updated_child)
                    step_status_map[child.step_id] = AIStepStatus.PENDING

        # 3. Check if all steps in the run have reached SUCCEEDED
        if all(status == AIStepStatus.SUCCEEDED for status in step_status_map.values()):
            parent_run = self.repository.get_run(step.run_id)
            if parent_run and parent_run.status != AIRunStatus.SUCCEEDED:
                # Aggregate total resource usage and cost
                has_in = any(s.usage.input_tokens is not None for s in all_steps)
                has_out = any(s.usage.output_tokens is not None for s in all_steps)
                has_tot = any(s.usage.total_tokens is not None for s in all_steps)

                if has_in or has_out:
                    total_in = sum(s.usage.input_tokens or 0 for s in all_steps)
                    total_out = sum(s.usage.output_tokens or 0 for s in all_steps)
                    total_usage = UsageRecord(
                        input_tokens=total_in,
                        output_tokens=total_out,
                        total_tokens=total_in + total_out,
                    )
                elif has_tot:
                    total_tokens = sum(s.usage.total_tokens or 0 for s in all_steps)
                    total_usage = UsageRecord(total_tokens=total_tokens)
                else:
                    total_usage = UsageRecord()

                total_cost_val = 0.0
                for s in all_steps:
                    if s.cost.actual_cost:
                        try:
                            total_cost_val += float(s.cost.actual_cost)
                        except ValueError:
                            pass

                now_dt = datetime.now(timezone.utc)
                completed_run = parent_run.model_copy(
                    update={
                        "status": AIRunStatus.SUCCEEDED,
                        "completed_at": now_dt,
                        "usage": total_usage,
                        "cost": CostEstimate(
                            estimated_cost=parent_run.cost.estimated_cost,
                            actual_cost=f"{total_cost_val:.4f}",
                        ),
                    }
                )
                self.repository.update_run(completed_run)

        return step

    def fail_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        error: AIError,
    ) -> AIStep:
        """
        Handles step execution failure with typed bounded retry evaluation.
        If retryable and attempt < max_attempts: schedules retry (status -> PENDING).
        If terminal: marks step FAILED, propagates failure to all downstream DAG descendants,
        and marks AIRun FAILED.
        """
        step = self.repository.get_step(step_id)
        if not step:
            raise StepNotFoundError(f"AIStep '{step_id}' not found.")

        # Determine if failure is retryable
        should_retry = self.retry_policy.should_retry(step.attempt, error)

        if should_retry and step.attempt < step.max_attempts:
            next_retry_at = self.retry_policy.compute_next_retry_at(step.attempt)
            return self.repository.fail_step(
                step_id=step_id,
                worker_id=worker_id,
                lease_token=lease_token,
                error=error,
                next_status=AIStepStatus.PENDING,
                next_retry_at=next_retry_at,
            )
        else:
            # Terminal step failure
            failed_step = self.repository.fail_step(
                step_id=step_id,
                worker_id=worker_id,
                lease_token=lease_token,
                error=error,
                next_status=AIStepStatus.FAILED,
                next_retry_at=None,
            )

            # Cascade failure to all downstream descendants in the run
            all_steps = self.repository.get_steps_for_run(step.run_id)
            children_map: dict[str, list[str]] = {s.step_id: [] for s in all_steps}
            for s in all_steps:
                for dep in s.dependencies:
                    if dep in children_map:
                        children_map[dep].append(s.step_id)

            # BFS to find all downstream descendants
            descendants: set[str] = set()
            queue = list(children_map.get(step_id, []))
            while queue:
                curr = queue.pop(0)
                if curr not in descendants:
                    descendants.add(curr)
                    queue.extend(children_map.get(curr, []))

            # Mark all non-terminal descendants as FAILED (DEPENDENCY_FAILED)
            dep_error = AIError.dependency_failed(
                message=f"Step execution aborted because parent prerequisite '{step_id}' failed terminally.",
                details={"failed_parent_step_id": step_id, "parent_error": error.message},
            )
            now_dt = datetime.now(timezone.utc)

            for s in all_steps:
                if s.step_id in descendants and s.status in {
                    AIStepStatus.WAITING,
                    AIStepStatus.PENDING,
                    AIStepStatus.RUNNING,
                }:
                    updated_descendant = s.model_copy(
                        update={
                            "status": AIStepStatus.FAILED,
                            "completed_at": now_dt,
                            "error": dep_error,
                            "worker_id": None,
                            "lease_token": None,
                            "lease_expires_at": None,
                        }
                    )
                    self.repository.update_step(updated_descendant)

            # Mark parent AIRun as FAILED
            parent_run = self.repository.get_run(step.run_id)
            if parent_run and parent_run.status != AIRunStatus.FAILED:
                failed_run = parent_run.model_copy(
                    update={
                        "status": AIRunStatus.FAILED,
                        "completed_at": now_dt,
                        "error": error,
                    }
                )
                self.repository.update_run(failed_run)

            return failed_step

    def cancel_run(
        self,
        run_id: str,
        workspace_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AIRun:
        """Cancels an active or waiting AIRun and all non-terminal steps."""
        return self.repository.cancel_run(
            run_id=run_id,
            workspace_id=workspace_id,
            reason=reason,
        )
