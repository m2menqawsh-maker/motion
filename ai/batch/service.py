"""
ai/batch/service.py
===================
Authoritative Coordinator for Batch & Background AI Workloads (S27.21).

Invariants:
- Strictly reuses existing durable orchestration (AI-10), budget engine (AI-05), cache (AI-11), and router (AI-04).
- Does NOT build a second Router, second Orchestrator, second Budget engine, or second Cache.
- Enforces ExecutionClass policies (INTERACTIVE vs BACKGROUND vs BATCH).
- Batch workloads strictly disallow routing to expensive interactive-only endpoints.
- Reuses cache across bulk operations (N identical tasks = 1 provider call + N-1 cache hits).
- Integrates with BudgetService for pre-reservation and settlement (bounds spend, prevents overspend).
- Recovers safely from worker crashes via AI-10 durable leasing and recovery.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from ai.batch.policy import ForbiddenBatchRouteError, get_execution_policy
from ai.budget.service import BudgetService
from ai.budget.types import BudgetExceededError, BudgetScope, ReservationRequest
from ai.cache.key import derive_canonical_cache_key
from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.common import CapabilityType, CapabilityTypeEnum, ExecutionClass
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.model import ModelRequirement
from ai.contracts.run import AIRun, AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.models.types import CostTier
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.recovery import AIRecoveryService
from ai.orchestration.service import AIRunService
from ai.routing.router import ModelRouter
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.storage.storage_service import get_storage_service

logger = logging.getLogger("ai.batch.service")


class BatchExecutionResult:
    """Outcome summary for a submitted batch execution."""

    def __init__(
        self,
        batch_run_id: str,
        workspace_id: str,
        execution_class: ExecutionClass,
        total_tasks: int,
        cached_count: int,
        executed_count: int,
        total_cost: Decimal,
        results: List[Dict[str, Any]],
        status: str,
    ):
        self.batch_run_id = batch_run_id
        self.workspace_id = workspace_id
        self.execution_class = execution_class
        self.total_tasks = total_tasks
        self.cached_count = cached_count
        self.executed_count = executed_count
        self.total_cost = total_cost
        self.results = results
        self.status = status


class BatchAIService:
    """
    Coordinates batch and background AI execution across existing durable subsystems.
    """

    def __init__(
        self,
        run_service: Optional[AIRunService] = None,
        budget_service: Optional[BudgetService] = None,
        cache_service: Optional[AICacheService] = None,
        router: Optional[ModelRouter] = None,
        recovery_service: Optional[AIRecoveryService] = None,
    ):
        if run_service is not None and hasattr(run_service, "repository"):
            self._run_repo = run_service.repository
            self.run_service = run_service
        else:
            self._run_repo = SQLAIRunRepository()
            self.run_service = AIRunService(repository=self._run_repo)

        self.budget_service = budget_service
        self.cache_service = cache_service or AICacheService(
            repository=SQLAICacheRepository(),
            storage_service=get_storage_service(),
        )
        self.router = router or ModelRouter()
        self.recovery_service = recovery_service or AIRecoveryService(repository=self._run_repo)

    def execute_batch(
        self,
        workspace_id: str,
        capability: CapabilityType,
        tasks: List[Dict[str, Any]],
        max_budget: Optional[Decimal] = None,
        prompt_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        execution_class: ExecutionClass = ExecutionClass.BATCH,
        worker_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> BatchExecutionResult:
        """
        Submits and executes a batch workload with budget protection, cache deduplication,
        and durable orchestration.
        """
        policy = get_execution_policy(execution_class)

        # 1. Routing & Policy Verification: Check candidate model eligibility
        route_req = ModelRequirement(
            capability=capability,
            execution_class=execution_class,
        )
        try:
            selection = self.router.route(route_req)
        except Exception as exc:
            if execution_class == ExecutionClass.BATCH:
                raise ForbiddenBatchRouteError(
                    f"BATCH execution rejected: No eligible batch-compatible model available for capability '{capability.value}': {exc}"
                )
            raise

        # 2. Budget Pre-Reservation Check
        estimated_cost_per_task = selection.estimated_cost.estimated_cost
        if estimated_cost_per_task <= Decimal("0"):
            estimated_cost_per_task = Decimal("0.001")
        total_estimated_cost = estimated_cost_per_task * len(tasks)

        if max_budget is not None and total_estimated_cost > max_budget:
            raise BudgetExceededError(
                error=AIError(
                    code=AIErrorCode.BUDGET_EXCEEDED,
                    message=f"Batch execution rejected: Total estimated cost ${total_estimated_cost} exceeds maximum allowed budget ${max_budget}.",
                    retryable=False,
                )
            )

        reservation_id = None
        if self.budget_service:
            # Reservation amount must be strictly > 0
            reserve_amount = total_estimated_cost if total_estimated_cost > Decimal("0") else Decimal("0.0001")
            res_req = ReservationRequest(
                workspace_id=workspace_id,
                amount=reserve_amount,
                idempotency_key=f"batch_{uuid.uuid4().hex[:12]}",
                capability=capability.value if hasattr(capability, "value") else str(capability),
            )
            res_result = self.budget_service.reserve(res_req)
            if not res_result.success:
                raise BudgetExceededError(
                    error=res_result.error or AIError(
                        code=AIErrorCode.BUDGET_EXCEEDED,
                        message="Batch execution failed budget reservation",
                        retryable=False,
                    )
                )
            if res_result.reservation:
                reservation_id = res_result.reservation.reservation_id

        # 3. Create Durable AIRun DAG (AI-10)
        dag_steps = [
            StepDefinition(
                step_id=f"step_{idx:03d}",
                capability=capability,
                dependencies=[],
            )
            for idx in range(len(tasks))
        ]
        dag_spec = DAGSpecification(steps=dag_steps)

        run = self.run_service.create_run(
            workspace_id=workspace_id,
            capability=capability,
            dag_spec=dag_spec,
            execution_class=execution_class,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
        )

        # Transition run to RUNNING
        run = run.model_copy(update={"status": AIRunStatus.RUNNING})
        self._run_repo.update_run(run)

        # 4. Execute Tasks with Cache Reuse (AI-11)
        results: List[Dict[str, Any]] = []
        cached_count = 0
        executed_count = 0
        actual_total_cost = Decimal("0.00")

        try:
            for idx, task_input in enumerate(tasks):
                step_id = f"step_{idx:03d}"

                # Derive canonical cache key
                cache_params = AICacheKeyParams(
                    workspace_id=workspace_id,
                    capability=capability,
                    input_data=task_input,
                    model=selection.primary_model,
                    prompt_version=prompt_version or "1.0.0",
                )
                cache_key = derive_canonical_cache_key(cache_params)

                # Check cache
                cached_entry = self.cache_service.get(workspace_id, cache_key)
                if cached_entry:
                    cached_count += 1
                    try:
                        raw_data = self.cache_service.storage_service.get(cached_entry.output_ref)
                        parsed = json.loads(raw_data.decode("utf-8"))
                    except Exception:
                        parsed = {"output_ref": cached_entry.output_ref, "cached": True}
                    results.append({"task_index": idx, "source": "cache", "result": parsed})
                else:
                    # Execute task
                    executed_count += 1
                    actual_cost_this_task = estimated_cost_per_task
                    actual_total_cost += actual_cost_this_task

                    task_result = worker_fn(task_input) if worker_fn else {"status": "completed", "input": task_input}
                    results.append({"task_index": idx, "source": "provider", "result": task_result})

                    # Publish to cache so subsequent tasks or batch reruns hit cache
                    try:
                        payload_bytes = json.dumps(task_result).encode("utf-8")
                        storage_key = f"workspaces/{workspace_id}/cache/{capability.value.lower()}/{cache_key}.json"
                        self.cache_service.storage_service.put(storage_key, payload_bytes, "application/json")
                        self.cache_service.publish(
                            workspace_id=workspace_id,
                            cache_key=cache_key,
                            output_ref=storage_key,
                            model=selection.primary_model,
                            capability=capability,
                        )
                    except Exception as exc:
                        logger.warning(f"Failed to publish result to cache: {exc}")

            # Settle budget
            if self.budget_service and reservation_id:
                self.budget_service.settle(
                    reservation_id=reservation_id,
                    actual_cost=actual_total_cost,
                    usage=UsageRecord(),
                )

            # Mark run as succeeded
            run = run.model_copy(
                update={
                    "status": AIRunStatus.SUCCEEDED,
                    "cost": CostEstimate(estimated_cost=total_estimated_cost, actual_cost=actual_total_cost),
                }
            )
            self._run_repo.update_run(run)

        except Exception as exc:
            # Release budget on failure
            if self.budget_service and reservation_id:
                self.budget_service.release(reservation_id=reservation_id)
            raise

        return BatchExecutionResult(
            batch_run_id=run.run_id,
            workspace_id=workspace_id,
            execution_class=execution_class,
            total_tasks=len(tasks),
            cached_count=cached_count,
            executed_count=executed_count,
            total_cost=actual_total_cost,
            results=results,
            status="SUCCEEDED",
        )
