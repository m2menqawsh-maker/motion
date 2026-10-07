"""
ai/orchestration/recovery.py
============================
Autonomous idempotent recovery service for durable AI runs and steps (S27.11).

Invariants:
- Proves durability under failure (worker death, lease expiry, process crash).
- Idempotent: Consecutive recover() invocations produce identical state and 0 duplicate work.
- Fences against stale workers: Reclaimed steps supersede dead worker leases.
- Prevents blind retries for non-idempotent activities (AT_MOST_ONCE).
- Reconciles unprogressed DAG children and run terminal states.
- Multi-tenant isolation: Scoped strictly to specified workspace when provided.
- Releases leaked budget reservations without double deduction or leakage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional

from ai.contracts.activity import ActivityStatus, IdempotencySemantics
from ai.contracts.errors import AIError
from ai.contracts.run import AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.activity import settle_activity_cost
from ai.orchestration.errors import NonIdempotentRetryError
from ai.orchestration.repository import AIRunRepository
from ai.orchestration.retry import RetryPolicy

logger = logging.getLogger("ai.orchestration.recovery")


@dataclass
class RecoveryReport:
    """Summary report detailing mutations performed during a recovery sweep."""
    workspace_id: Optional[str]
    expired_leases_reclaimed: int = 0
    steps_reconciled_from_activities: int = 0
    steps_reset_for_retry: int = 0
    steps_failed_terminal: int = 0
    children_unblocked: int = 0
    runs_completed: int = 0
    runs_failed: int = 0
    reservations_released: int = 0
    costs_settled: int = 0


class AIRecoveryService:
    """
    Authoritative recovery coordinator reconciling abandoned steps, expired leases,
    persisted activity results, unprogressed DAG children, and leaked reservations.
    """

    def __init__(
        self,
        repository: AIRunRepository,
        retry_policy: Optional[RetryPolicy] = None,
        budget_service: Optional[Any] = None,
    ):
        self.repository = repository
        self.retry_policy = retry_policy or RetryPolicy()
        self.budget_service = budget_service

    def recover(self, workspace_id: Optional[str] = None) -> RecoveryReport:
        """
        Executes a complete, idempotent recovery sweep.

        Guarantees:
        - Running recover() twice in succession yields identical DB state with 0 additional mutations.
        - No lost AIRun.
        - No stale worker overwrite.
        - No duplicate expensive provider calls.
        - True multi-tenant isolation.
        """
        report = RecoveryReport(workspace_id=workspace_id)
        now_dt = datetime.now(timezone.utc)

        # ---------------------------------------------------------------------
        # Phase 1: Reclaim Expired Leased Steps
        # ---------------------------------------------------------------------
        expired_steps = self.repository.list_expired_steps(workspace_id=workspace_id)

        for step in expired_steps:
            report.expired_leases_reclaimed += 1
            activities = self.repository.get_activities_for_step(step.step_id, workspace_id=workspace_id)
            succeeded_activity = next((a for a in activities if a.status == ActivityStatus.SUCCEEDED), None)

            if succeeded_activity:
                # Critical Matrix Point 4: Worker died after durable result commit before step commit.
                # Reconcile step directly to SUCCEEDED using persisted activity outputs without re-running provider.
                if not succeeded_activity.cost_settled:
                    if settle_activity_cost(succeeded_activity, self.repository, self.budget_service):
                        report.costs_settled += 1

                reconciled_step = step.model_copy(
                    update={
                        "status": AIStepStatus.SUCCEEDED,
                        "output_ref": succeeded_activity.output_ref,
                        "usage": succeeded_activity.usage or UsageRecord(),
                        "cost": succeeded_activity.cost or CostEstimate(estimated_cost="0.00", actual_cost="0.00"),
                        "completed_at": succeeded_activity.completed_at or now_dt,
                        "worker_id": None,
                        "lease_token": None,
                        "lease_expires_at": None,
                    }
                )
                self.repository.update_step(reconciled_step)
                report.steps_reconciled_from_activities += 1
                logger.info(
                    "Recovery reconciled step %s to SUCCEEDED from activity %s",
                    step.step_id,
                    succeeded_activity.activity_id,
                )
            else:
                # Check for non-idempotent activity crash (Section 15)
                non_idempotent = next(
                    (a for a in activities if a.semantics == IdempotencySemantics.AT_MOST_ONCE),
                    None,
                )
                if non_idempotent:
                    # Blind retry forbidden! Fail step terminally.
                    non_idem_err = AIError.internal_error(
                        message=(
                            f"Non-idempotent activity '{non_idempotent.activity_id}' crashed or lease expired. "
                            f"Automatic retry disallowed to prevent duplicate side effects."
                        ),
                        details={"activity_id": non_idempotent.activity_id},
                    )
                    self._fail_step_terminal(step, non_idem_err, report, now_dt)
                elif step.attempt < step.max_attempts:
                    # Bounded retry: reset to PENDING for another worker
                    next_retry = self.retry_policy.compute_next_retry_at(step.attempt)
                    reset_step = step.model_copy(
                        update={
                            "status": AIStepStatus.PENDING,
                            "attempt": step.attempt + 1,
                            "next_retry_at": next_retry,
                            "worker_id": None,
                            "lease_token": None,
                            "lease_expires_at": None,
                        }
                    )
                    self.repository.update_step(reset_step)
                    report.steps_reset_for_retry += 1
                else:
                    # Max attempts exceeded
                    timeout_err = AIError.timeout(
                        message=f"AIStep '{step.step_id}' lease expired and max attempts ({step.max_attempts}) reached.",
                    )
                    self._fail_step_terminal(step, timeout_err, report, now_dt)

        # ---------------------------------------------------------------------
        # Phase 2: Progress DAG Dependencies (Matrix Point 5 & 6)
        # ---------------------------------------------------------------------
        active_runs = self.repository.list_active_runs(workspace_id=workspace_id)

        for run in active_runs:
            steps = self.repository.get_steps_for_run(run.run_id, workspace_id=workspace_id)
            step_status_map = {s.step_id: s.status for s in steps}

            for child in steps:
                if child.status == AIStepStatus.WAITING:
                    all_deps_succeeded = (
                        len(child.dependencies) > 0
                        and all(
                            step_status_map.get(dep) == AIStepStatus.SUCCEEDED
                            for dep in child.dependencies
                        )
                    )
                    if all_deps_succeeded:
                        unblocked_child = child.model_copy(
                            update={"status": AIStepStatus.PENDING}
                        )
                        self.repository.update_step(unblocked_child)
                        step_status_map[child.step_id] = AIStepStatus.PENDING
                        report.children_unblocked += 1

            # -----------------------------------------------------------------
            # Phase 3: Reconcile Run Completion & Terminal State
            # -----------------------------------------------------------------
            refreshed_steps = self.repository.get_steps_for_run(run.run_id, workspace_id=workspace_id)
            statuses = {s.status for s in refreshed_steps}

            if statuses and all(s == AIStepStatus.SUCCEEDED for s in statuses):
                # All steps succeeded -> reconcile run to SUCCEEDED
                total_in = sum(s.usage.input_tokens or 0 for s in refreshed_steps)
                total_out = sum(s.usage.output_tokens or 0 for s in refreshed_steps)
                total_tokens = sum(s.usage.total_tokens or 0 for s in refreshed_steps)

                if total_in or total_out:
                    total_usage = UsageRecord(
                        input_tokens=total_in,
                        output_tokens=total_out,
                        total_tokens=total_in + total_out,
                    )
                elif total_tokens:
                    total_usage = UsageRecord(total_tokens=total_tokens)
                else:
                    total_usage = UsageRecord()

                total_cost_val = Decimal("0.00")
                for s in refreshed_steps:
                    if s.cost.actual_cost:
                        try:
                            total_cost_val += Decimal(str(s.cost.actual_cost))
                        except Exception:
                            pass

                completed_run = run.model_copy(
                    update={
                        "status": AIRunStatus.SUCCEEDED,
                        "completed_at": now_dt,
                        "usage": total_usage,
                        "cost": CostEstimate(
                            estimated_cost=run.cost.estimated_cost,
                            actual_cost=f"{total_cost_val:.4f}",
                        ),
                    }
                )
                self.repository.update_run(completed_run)
                report.runs_completed += 1
            elif AIStepStatus.FAILED in statuses:
                # Check if any step is still runnable or running
                has_active = any(s in {AIStepStatus.PENDING, AIStepStatus.RUNNING} for s in statuses)
                if not has_active and run.status != AIRunStatus.FAILED:
                    failed_step = next((s for s in refreshed_steps if s.status == AIStepStatus.FAILED and s.error is not None), None)
                    run_error = failed_step.error if failed_step else AIError.internal_error(
                        message=f"AIRun '{run.run_id}' failed due to one or more step failures.",
                        details={"run_id": run.run_id},
                    )
                    failed_run = run.model_copy(
                        update={
                            "status": AIRunStatus.FAILED,
                            "completed_at": now_dt,
                            "error": run_error,
                        }
                    )
                    self.repository.update_run(failed_run)
                    report.runs_failed += 1

        return report

    def _fail_step_terminal(
        self,
        step: AIStep,
        error: AIError,
        report: RecoveryReport,
        now_dt: datetime,
    ) -> None:
        """Helper marking a step terminally failed, releasing reservations, and cascading failure."""
        failed_step = step.model_copy(
            update={
                "status": AIStepStatus.FAILED,
                "completed_at": now_dt,
                "error": error,
                "worker_id": None,
                "lease_token": None,
                "lease_expires_at": None,
            }
        )
        self.repository.update_step(failed_step)
        report.steps_failed_terminal += 1

        # Release leaked budget reservation if attached (Section 14)
        activities = self.repository.get_activities_for_step(step.step_id)
        for act in activities:
            if act.reservation_id and self.budget_service:
                try:
                    self.budget_service.release(act.reservation_id)
                    report.reservations_released += 1
                except Exception as exc:
                    logger.warning("Failed to release reservation %s: %s", act.reservation_id, exc)

        # Cascade failure to all downstream descendants in DAG
        all_steps = self.repository.get_steps_for_run(step.run_id)
        children_map: dict[str, list[str]] = {s.step_id: [] for s in all_steps}
        for s in all_steps:
            for dep in s.dependencies:
                if dep in children_map:
                    children_map[dep].append(s.step_id)

        descendants: set[str] = set()
        queue = list(children_map.get(step.step_id, []))
        while queue:
            curr = queue.pop(0)
            if curr not in descendants:
                descendants.add(curr)
                queue.extend(children_map.get(curr, []))

        dep_error = AIError.dependency_failed(
            message=f"Cascading abort: parent prerequisite step '{step.step_id}' failed terminally.",
        )
        for s in all_steps:
            if s.step_id in descendants and s.status in {
                AIStepStatus.WAITING,
                AIStepStatus.PENDING,
                AIStepStatus.RUNNING,
            }:
                failed_desc = s.model_copy(
                    update={
                        "status": AIStepStatus.FAILED,
                        "completed_at": now_dt,
                        "error": dep_error,
                        "worker_id": None,
                        "lease_token": None,
                        "lease_expires_at": None,
                    }
                )
                self.repository.update_step(failed_desc)
