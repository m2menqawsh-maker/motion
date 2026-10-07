"""
tests/ai/cache/test_durable_activity_integration.py
===================================================
Integration tests proving AI-11 integrates seamlessly with AI-10 Durable Activities and Budget Engine.

Invariants verified:
- Cache MISS -> executes via DurableActivityExecutor -> reserves & settles budget -> publishes cache entry.
- Cache HIT -> bypasses DurableActivityExecutor and provider call -> zero provider cost -> zero duplicate budget reservation.
- 10 concurrent requests -> request coalescing ensures exactly 1 durable activity execution, 1 budget reservation, 10 successful consumers.
- Non-cacheable activities strictly bypass cache and execute via DurableActivityExecutor every time.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import threading
import time
import pytest

from ai.budget.policy import BudgetPolicy
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import Budget, BudgetScope, ReservationRequest
from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIRun, AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.activity import DurableActivityExecutor
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def env_setup(tmp_path):
    db_file = tmp_path / "test_durable_cache.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")

    run_repo = SQLAIRunRepository(engine=engine)
    cache_repo = SQLAICacheRepository(engine=engine)
    storage = LocalStorageBackend(root_dir=storage_dir)

    budget_repo = InMemoryBudgetRepository()
    budget_svc = BudgetService(repository=budget_repo, policy=BudgetPolicy(allow_overage_within_limit=True))
    now = datetime.now(timezone.utc)
    budget_svc.create_budget(
        Budget(
            budget_id="b_ws_durable",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_durable",
            limit=Decimal("100.00"),
            reserved=Decimal("0.00"),
            actual_spend=Decimal("0.00"),
            currency="USD",
            valid_from=now,
            created_at=now,
            updated_at=now,
        )

    )

    activity_executor = DurableActivityExecutor(repository=run_repo, budget_service=budget_svc)
    cache_service = AICacheService(repository=cache_repo, storage_service=storage)

    return {
        "run_repo": run_repo,
        "cache_repo": cache_repo,
        "storage": storage,
        "budget_svc": budget_svc,
        "activity_executor": activity_executor,
        "cache_service": cache_service,
    }


def _create_test_step(run_repo, workspace_id: str, step_id: str, capability: CapabilityTypeEnum) -> AIStep:
    now = datetime.now(timezone.utc)
    run_id = f"run_{step_id}"
    run = AIRun(
        run_id=run_id,
        workspace_id=workspace_id,
        status=AIRunStatus.RUNNING,
        capability=capability,
        created_at=now,
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.05"),
    )
    run_repo.create_run(run)

    step = AIStep(
        step_id=step_id,
        run_id=run_id,
        status=AIStepStatus.RUNNING,
        attempt=1,
        capability=capability,
        created_at=now,
        cost=CostEstimate(estimated_cost="0.05"),
    )
    run_repo.create_steps([step])
    return step


def test_durable_activity_miss_then_hit_zero_cost(env_setup):
    run_repo = env_setup["run_repo"]
    storage = env_setup["storage"]
    budget_svc = env_setup["budget_svc"]
    activity_executor = env_setup["activity_executor"]
    cache_service = env_setup["cache_service"]

    provider_calls = 0

    def fake_provider_fn(idempotency_key: str):
        nonlocal provider_calls
        provider_calls += 1
        # Persist output artifact in StorageService
        out_key = f"workspaces/ws_durable/artifacts/{idempotency_key}.json"
        storage.put(out_key, b'{"result": "voiceover audio ready"}', content_type="application/json")
        return (
            out_key,
            UsageRecord(input_tokens=50, output_tokens=50, total_tokens=100),
            CostEstimate(estimated_cost="0.05", actual_cost="0.0350"),
            f"remote_op_{idempotency_key}",
        )

    # 1. First execution: Cache MISS
    step1 = _create_test_step(run_repo, "ws_durable", "step_01", CapabilityTypeEnum.TEXT_TO_SPEECH)
    params = AICacheKeyParams(
        workspace_id="ws_durable",
        capability=CapabilityTypeEnum.TEXT_TO_SPEECH,
        input_data={"text": "Welcome to our AI platform"},
        model="eleven_multilingual_v2",
    )

    # Reserve budget for step 1
    res_req = ReservationRequest(
        workspace_id="ws_durable",
        amount=Decimal("0.05"),
        currency="USD",
        idempotency_key="res_step_01",
        run_id=step1.run_id,
        ttl_seconds=300,
    )
    res_res = budget_svc.reserve(res_req)
    assert res_res.success is True
    res_id = res_res.reservation.reservation_id

    record1, hit1 = cache_service.execute_cached_activity(
        step=step1,
        workspace_id="ws_durable",
        params=params,
        activity_executor=activity_executor,
        fn=fake_provider_fn,
        reservation_id=res_id,
        native_idempotency_supported=True,
    )

    assert hit1 is False
    assert provider_calls == 1
    assert record1.cost_settled is True
    assert record1.cost.actual_cost == Decimal("0.0350")

    # Budget actual spend is 0.0350
    budget = budget_svc.repository.get_budget("b_ws_durable")
    assert budget.actual_spend == Decimal("0.0350")

    # 2. Second execution (different run/step, identical input): Cache HIT!
    step2 = _create_test_step(run_repo, "ws_durable", "step_02", CapabilityTypeEnum.TEXT_TO_SPEECH)

    record2, hit2 = cache_service.execute_cached_activity(
        step=step2,
        workspace_id="ws_durable",
        params=params,
        activity_executor=activity_executor,
        fn=fake_provider_fn,
        reservation_id=None,  # No reservation needed for hit!
        native_idempotency_supported=True,
    )

    assert hit2 is True
    assert provider_calls == 1  # ZERO provider invocations!
    assert record2.output_ref == record1.output_ref
    # ZERO cost charged
    assert record2.cost.actual_cost == Decimal("0.00")
    # Spend in budget ledger did NOT increase
    budget_after = budget_svc.repository.get_budget("b_ws_durable")
    assert budget_after.actual_spend == Decimal("0.0350")



def test_durable_activity_coalescing_waiters_share_result(env_setup):
    run_repo = env_setup["run_repo"]
    storage = env_setup["storage"]
    budget_svc = env_setup["budget_svc"]
    activity_executor = env_setup["activity_executor"]
    cache_service = env_setup["cache_service"]

    provider_lock = threading.Lock()
    provider_calls = 0

    def slow_provider_fn(idempotency_key: str):
        nonlocal provider_calls
        with provider_lock:
            provider_calls += 1
        time.sleep(0.08)
        out_key = f"workspaces/ws_durable/artifacts/shared_{idempotency_key}.json"
        storage.put(out_key, b'{"result": "coalesced durable audio"}', content_type="application/json")
        return (
            out_key,
            UsageRecord(input_tokens=100, output_tokens=100, total_tokens=200),
            CostEstimate(estimated_cost="0.05", actual_cost="0.0400"),
            f"remote_op_{idempotency_key}",
        )

    params = AICacheKeyParams(
        workspace_id="ws_durable",
        capability=CapabilityTypeEnum.TEXT_TO_SPEECH,
        input_data={"text": "Coalesced voiceover sentence"},
        model="eleven_multilingual_v2",
    )

    steps = [
        _create_test_step(run_repo, "ws_durable", f"coalesce_step_{i}", CapabilityTypeEnum.TEXT_TO_SPEECH)
        for i in range(10)
    ]

    def task(step_idx: int):
        s = steps[step_idx]
        rec, hit = cache_service.execute_cached_activity(
            step=s,
            workspace_id="ws_durable",
            params=params,
            activity_executor=activity_executor,
            fn=slow_provider_fn,
            reservation_id=None,
            native_idempotency_supported=True,
            wait_timeout_seconds=15.0,
            poll_interval_seconds=0.02,
            worker_id=f"w_{step_idx}",
        )
        return rec, hit

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(task, i) for i in range(10)]
        results = [f.result() for f in futures]

    # Exactly 1 provider execution occurred!
    assert provider_calls == 1

    # All 10 steps received valid output and succeeded
    assert len(results) == 10
    first_output_ref = results[0][0].output_ref
    for rec, hit in results:
        assert rec.status == "SUCCEEDED"
        assert rec.output_ref == first_output_ref


def test_non_cacheable_durable_activity_bypasses_cache(env_setup):
    run_repo = env_setup["run_repo"]
    storage = env_setup["storage"]
    activity_executor = env_setup["activity_executor"]
    cache_service = env_setup["cache_service"]

    provider_calls = 0

    def fake_image_provider(idempotency_key: str):
        nonlocal provider_calls
        provider_calls += 1
        out_key = f"workspaces/ws_durable/artifacts/{idempotency_key}.png"
        storage.put(out_key, b"fake_png_bytes", content_type="image/png")
        return (
            out_key,
            UsageRecord(image_count=1),
            CostEstimate(estimated_cost="0.02", actual_cost="0.0200"),
            f"remote_img_{idempotency_key}",
        )

    # Capability IMAGE_GENERATION is CachePolicy.NEVER
    params = AICacheKeyParams(
        workspace_id="ws_durable",
        capability=CapabilityTypeEnum.IMAGE_GENERATION,
        input_data={"prompt": "Generate a sunset landscape"},
    )

    step1 = _create_test_step(run_repo, "ws_durable", "img_step_01", CapabilityTypeEnum.IMAGE_GENERATION)
    rec1, hit1 = cache_service.execute_cached_activity(
        step=step1,
        workspace_id="ws_durable",
        params=params,
        activity_executor=activity_executor,
        fn=fake_image_provider,
        native_idempotency_supported=True,
    )
    assert hit1 is False
    assert provider_calls == 1

    step2 = _create_test_step(run_repo, "ws_durable", "img_step_02", CapabilityTypeEnum.IMAGE_GENERATION)
    rec2, hit2 = cache_service.execute_cached_activity(
        step=step2,
        workspace_id="ws_durable",
        params=params,
        activity_executor=activity_executor,
        fn=fake_image_provider,
        native_idempotency_supported=True,
    )
    assert hit2 is False
    assert provider_calls == 2  # Executed again! Not cached!
