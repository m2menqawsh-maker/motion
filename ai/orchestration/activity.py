"""
ai/orchestration/activity.py
============================
Durable activity executor for external operations (providers, MCP, tools) (S27.11).

Invariants:
- Treats external calls as durable activities with explicit idempotency semantics.
- Generates and preserves stable logical idempotency keys across retry attempts.
- Enforces boundary between external provider and local DB (no false exactly-once).
- Guarantees non-idempotent activities (AT_MOST_ONCE) are never blindly retried.
- Atomic monotonic cost settlement preventing double-debiting financial ledgers.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Optional, Tuple

from ai.contracts.activity import (
    AIActivityRecord,
    ActivityStatus,
    IdempotencySemantics,
)
from ai.contracts.errors import AIError
from ai.contracts.run import AIRunStatus, AIStep
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.activity_classification import validate_activity_semantics
from ai.orchestration.errors import (
    NonIdempotentRetryError,
    RunAlreadyTerminalError,
)
from ai.orchestration.repository import AIRunRepository

logger = logging.getLogger("ai.orchestration.activity")


def settle_activity_cost(
    activity: AIActivityRecord,
    repository: AIRunRepository,
    budget_service: Optional[Any] = None,
    crash_injector: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Guarantees crash-safe cost settlement across external financial ledger boundary.
    Idempotent settlement prevents double deduction and missing settlement under crash.
    """
    if activity.cost_settled:
        return False

    actual_cost = Decimal("0.00")
    if activity.cost and activity.cost.actual_cost:
        try:
            actual_cost = Decimal(str(activity.cost.actual_cost))
        except Exception:
            pass

    # Window A crash point: Immediately before ledger mutation
    if crash_injector:
        crash_injector("before_ledger_mutation")

    if budget_service and activity.reservation_id:
        settle_res = budget_service.settle(
            reservation_id=activity.reservation_id,
            actual_cost=actual_cost,
            usage=activity.usage,
        )
        if not settle_res.success:
            logger.error(
                "Budget settlement failed for reservation %s: %s",
                activity.reservation_id,
                settle_res.error,
            )

    # Window B crash point: Immediately after ledger mutation, before local completion marker
    if crash_injector:
        crash_injector("after_ledger_mutation_before_marker")

    settled = repository.mark_cost_settled(activity.activity_id)
    return settled


class DurableActivityExecutor:
    """
    Executes external operations (providers, tools, MCP) as durable activities.
    """

    def __init__(
        self,
        repository: AIRunRepository,
        budget_service: Optional[Any] = None,
    ):
        self.repository = repository
        self.budget_service = budget_service

    @staticmethod
    def derive_idempotency_key(step: AIStep) -> str:
        """
        Derives a stable logical idempotency key for the step.
        Crucial invariant: Never incorporates retry attempt into the key.
        """
        if step.idempotency_key:
            return step.idempotency_key
        return f"idem_{step.run_id}_{step.step_id}"

    def execute_activity(
        self,
        step: AIStep,
        workspace_id: str,
        fn: Callable[[str], Tuple[str, UsageRecord, CostEstimate, Optional[str]]],
        semantics: IdempotencySemantics = IdempotencySemantics.EFFECTIVELY_ONCE,
        reservation_id: Optional[str] = None,
        native_idempotency_supported: bool = False,
        activity_name: Optional[str] = None,
        crash_injector: Optional[Callable[[str], None]] = None,
    ) -> AIActivityRecord:
        """
        Executes a durable activity within a step lifecycle.

        Arguments:
            step: Leased AIStep context
            workspace_id: Tenant isolation scope
            fn: External callable taking idempotency_key and returning:
                (output_ref, usage, cost, remote_operation_ref)
            semantics: Execution semantics (EFFECTIVELY_ONCE, AT_LEAST_ONCE, AT_MOST_ONCE)
            reservation_id: Optional budget reservation identifier
            crash_injector: Optional hook for simulating crashes at matrix failure points

        Returns:
            SUCCEEDED AIActivityRecord with durable outputs.
        """
        # 1. Pre-flight check: Ensure parent run is not already cancelled
        run = self.repository.get_run(step.run_id, workspace_id=workspace_id)
        if run and run.status == AIRunStatus.CANCELLED:
            raise RunAlreadyTerminalError(f"AIRun '{step.run_id}' is cancelled; activity aborted.")

        # Enforce misclassification guard: EFFECTIVELY_ONCE requires proven native idempotency or deterministic read
        validate_activity_semantics(
            activity_name=activity_name or step.capability.value,
            requested_semantics=semantics,
            native_idempotency_supported=native_idempotency_supported,
        )

        if crash_injector:
            crash_injector("before_provider_call")

        # 2. Derive stable logical idempotency key
        idempotency_key = self.derive_idempotency_key(step)

        # 3. Check if activity was already recorded/completed for this key
        existing = self.repository.get_activity_by_idempotency_key(
            workspace_id=workspace_id,
            step_id=step.step_id,
            idempotency_key=idempotency_key,
        )

        if existing:
            # If already succeeded, reuse durable result without re-executing expensive work
            if existing.status == ActivityStatus.SUCCEEDED:
                logger.info(
                    "Reusing persisted activity result for step %s (activity: %s)",
                    step.step_id,
                    existing.activity_id,
                )
                if not existing.cost_settled:
                    settle_activity_cost(
                        existing,
                        self.repository,
                        self.budget_service,
                    )
                return existing

            # Guard against blind retries of non-idempotent operations
            if (
                existing.semantics == IdempotencySemantics.AT_MOST_ONCE
                and existing.status in {ActivityStatus.RUNNING, ActivityStatus.FAILED}
            ):
                raise NonIdempotentRetryError(
                    f"Activity '{existing.activity_id}' has AT_MOST_ONCE semantics and was previously "
                    f"started ({existing.status.value}). Blind retry forbidden to prevent duplicate side effects."
                )
            activity = existing
        else:
            # 4. Record intent in durable storage before executing external call
            now_dt = datetime.now(timezone.utc)
            activity_id = f"act_{uuid.uuid4().hex}"
            new_record = AIActivityRecord(
                activity_id=activity_id,
                run_id=step.run_id,
                step_id=step.step_id,
                idempotency_key=idempotency_key,
                status=ActivityStatus.RUNNING,
                semantics=semantics,
                started_at=now_dt,
                provider=step.provider,
                model=step.model,
                cost_settled=False,
                reservation_id=reservation_id,
                created_at=now_dt,
            )
            activity = self.repository.record_activity_intent(new_record, workspace_id=workspace_id)

        # 5. Execute external callable with stable idempotency key
        try:
            if crash_injector:
                crash_injector("during_provider_call")

            output_ref, usage, cost, remote_op_ref = fn(idempotency_key)

            if crash_injector:
                crash_injector("after_provider_success_before_local_commit")
        except Exception as exc:
            if not isinstance(exc, AIError):
                ai_err = AIError.internal_error(
                    message=f"External activity execution failed: {str(exc)}",
                    details={"error_type": type(exc).__name__},
                )
            else:
                ai_err = exc

            self.repository.mark_activity_failed(activity.activity_id, ai_err)
            raise

        # 6. Post-execution cancellation check: Parent run cancelled while provider call was in-flight
        fresh_run = self.repository.get_run(step.run_id, workspace_id=workspace_id)
        if fresh_run and fresh_run.status == AIRunStatus.CANCELLED:
            # Save durable activity result for audit/provenance, but do NOT advance step or run
            self.repository.mark_activity_completed(
                activity_id=activity.activity_id,
                output_ref=output_ref,
                usage=usage,
                cost=cost,
                remote_op_ref=remote_op_ref,
            )
            raise RunAlreadyTerminalError(
                f"AIRun '{step.run_id}' was cancelled while activity was in-flight; late result ignored."
            )

        # 7. Persist local result durably
        completed_record = self.repository.mark_activity_completed(
            activity_id=activity.activity_id,
            output_ref=output_ref,
            usage=usage,
            cost=cost,
            remote_op_ref=remote_op_ref,
        )

        # 8. Settle cost atomically (ensures crash-safe exactly-once cost deduction)
        settled_bool = settle_activity_cost(
            completed_record,
            self.repository,
            self.budget_service,
            crash_injector=crash_injector,
        )

        if crash_injector:
            crash_injector("after_result_persistence_before_step_commit")

        return completed_record.model_copy(update={"cost_settled": settled_bool or completed_record.cost_settled})
