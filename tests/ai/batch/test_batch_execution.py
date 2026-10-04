"""
tests/ai/batch/test_batch_execution.py
======================================
Tests for Execution Classes and Batch / Background AI (S27.21).

Invariants verified:
1. Execution classes (INTERACTIVE, BACKGROUND, BATCH) policies and constraints.
2. Batch route constraints: forbids expensive interactive-only routes (CostTier.VERY_HIGH).
3. Cache reuse across bulk operations (N identical tasks = 1 execution + N-1 cache hits).
4. Budget bounding: pre-reservation check prevents runaway cost; exceeding budget raises BudgetExceededError.
5. Durable execution: AIRun is persisted with execution_class, allowing recovery via AIRecoveryService.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import pytest

from ai.batch.policy import (
    BATCH_POLICY,
    BACKGROUND_POLICY,
    ForbiddenBatchRouteError,
    INTERACTIVE_POLICY,
    get_execution_policy,
)
from ai.batch.service import BatchAIService
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import Budget, BudgetExceededError, BudgetScope
from ai.cache.service import AICacheService
from ai.contracts.common import CapabilityType, ExecutionClass
from ai.contracts.model import ModelRequirement
from ai.contracts.run import AIRunStatus
from ai.models.types import CostTier, LatencyTier
from ai.orchestration.recovery import AIRecoveryService
from ai.orchestration.service import AIRunService
from ai.routing.router import ModelRouter
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def batch_service(tmp_path):
    db_file = tmp_path / "test_batch.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")

    run_repo = SQLAIRunRepository(engine=engine)
    cache_repo = SQLAICacheRepository(engine=engine)
    storage = LocalStorageBackend(root_dir=storage_dir)

    run_service = AIRunService(repository=run_repo)
    cache_service = AICacheService(repository=cache_repo, storage_service=storage)

    budget_repo = InMemoryBudgetRepository()
    budget_service = BudgetService(repository=budget_repo)

    # Pre-seed a workspace budget of $10.00
    now = datetime.now(timezone.utc)
    budget_service.create_budget(
        Budget(
            budget_id="bgt_ws_batch",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_batch_test",
            limit=Decimal("10.00"),
            valid_from=now,
            created_at=now,
            updated_at=now,
        )
    )

    router = ModelRouter()
    recovery_service = AIRecoveryService(repository=run_repo)

    return BatchAIService(
        run_service=run_service,
        budget_service=budget_service,
        cache_service=cache_service,
        router=router,
        recovery_service=recovery_service,
    )


def test_execution_class_policies():
    interactive = get_execution_policy(ExecutionClass.INTERACTIVE)
    assert interactive.allow_durable_workers is False
    assert LatencyTier.REALTIME in interactive.allowed_latency_tiers
    assert interactive.max_timeout_seconds <= 15.0

    background = get_execution_policy(ExecutionClass.BACKGROUND)
    assert background.allow_durable_workers is True
    assert LatencyTier.SLOW in background.allowed_latency_tiers
    assert background.max_timeout_seconds >= 600.0

    batch = get_execution_policy(ExecutionClass.BATCH)
    assert batch.allow_durable_workers is True
    assert CostTier.VERY_HIGH in batch.disallowed_cost_tiers
    assert batch.max_timeout_seconds >= 3600.0


def test_batch_cache_deduplication(batch_service):
    worker_calls = []

    def mock_worker(task_input: dict) -> dict:
        worker_calls.append(task_input)
        return {"processed": task_input["video_id"], "status": "analyzed"}

    # 4 tasks total: task 0, 1, 2 are IDENTICAL; task 3 is distinct
    tasks = [
        {"video_id": "vid_dup_001"},
        {"video_id": "vid_dup_001"},
        {"video_id": "vid_dup_001"},
        {"video_id": "vid_unique_999"},
    ]

    result = batch_service.execute_batch(
        workspace_id="ws_batch_test",
        capability=CapabilityType.REASONING,
        tasks=tasks,
        execution_class=ExecutionClass.BATCH,
        worker_fn=mock_worker,
    )

    # Total tasks = 4, executed = 2, cached = 2
    assert result.total_tasks == 4
    assert result.executed_count == 2
    assert result.cached_count == 2
    assert len(worker_calls) == 2
    assert result.status == "SUCCEEDED"

    # Confirm run persisted with execution_class = BATCH
    persisted_run = batch_service._run_repo.get_run(result.batch_run_id, "ws_batch_test")
    assert persisted_run.execution_class == ExecutionClass.BATCH
    assert persisted_run.status == AIRunStatus.SUCCEEDED


def test_batch_budget_enforcement(batch_service):
    # Set a tiny max budget of $0.0001
    tasks = [{"data": f"item_{i}"} for i in range(100)]

    with pytest.raises(BudgetExceededError) as exc_info:
        batch_service.execute_batch(
            workspace_id="ws_batch_test",
            capability=CapabilityType.REASONING,
            tasks=tasks,
            max_budget=Decimal("0.0001"),
            execution_class=ExecutionClass.BATCH,
        )
    assert "exceeds maximum allowed budget" in str(exc_info.value)


def test_forbidden_batch_route_on_unavailable_capability(batch_service):
    # If a routing constraint cannot satisfy BATCH rules (e.g. expensive interactive-only model zeroscope-v2-xl),
    # it raises ForbiddenBatchRouteError
    with pytest.raises(ForbiddenBatchRouteError) as exc_info:
        batch_service.execute_batch(
            workspace_id="ws_batch_test",
            capability=CapabilityType.VIDEO_GENERATION,
            tasks=[{"prompt": "generate video scene"}],
            execution_class=ExecutionClass.BATCH,
        )
    assert "BATCH execution rejected" in str(exc_info.value)
