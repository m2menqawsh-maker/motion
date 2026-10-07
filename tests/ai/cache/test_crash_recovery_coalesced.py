"""
tests/ai/cache/test_crash_recovery_coalesced.py
================================================
AI-11R — S27.12 Coalesced Owner Crash Hardening Tests.

Critical Guarantees Verified:
1. Shared durable execution identity (workspace_id + cache_key + generation)
   survives owner / run / step changes across different AIRun / AIStep contexts.
2. Crash after durable activity result persisted, before cache READY commit:
   - New owner takes expired cache lease.
   - New owner reconciles persisted activity.
   - Publishes cache entry as READY.
   - Provider executions = 1 (ZERO duplicate provider invocations).
   - Logical shared activities = 1 (no duplicate AIActivityRecord).
   - Budget settlements = 1 (no duplicate reservation or settlement).
   - Both consumers resolve the result.
3. Crash after provider success before activity commit (EFFECTIVELY_ONCE):
   - Provider physical generations = 1 via shared idempotency key.
   - Cache entry becomes READY.
   - Logical activities = 1.
4. AT_LEAST_ONCE semantics behavior is documented and verified.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import threading
import time
import pytest

from ai.budget.policy import BudgetPolicy
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import Budget, BudgetScope, ReservationRequest
from ai.cache.key import derive_canonical_cache_key
from ai.cache.service import AICacheService
from ai.contracts.activity import ActivityStatus, IdempotencySemantics
from ai.contracts.cache import AICacheKeyParams, CacheEntryStatus
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIRun, AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.activity import DurableActivityExecutor
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def hardened_env(tmp_path):
    db_file = tmp_path / "hardened_crash.db"
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
            budget_id="b_ws_hardened",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_hardened",
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
    cache_service = AICacheService(
        repository=cache_repo,
        storage_service=storage,
        default_lease_duration_seconds=0.2,
    )

    return {
        "engine": engine,
        "run_repo": run_repo,
        "cache_repo": cache_repo,
        "storage": storage,
        "budget_svc": budget_svc,
        "activity_executor": activity_executor,
        "cache_service": cache_service,
    }


def _create_step(run_repo, workspace_id: str, run_id: str, step_id: str, capability: CapabilityTypeEnum) -> AIStep:
    now = datetime.now(timezone.utc)
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


# =============================================================================
# Critical Test 1: Crash after durable activity result persisted, before cache READY commit
# =============================================================================

def test_crash_after_activity_persistence_before_cache_ready(hardened_env):
    """
    Scenario:
    - Request A (Run A, Step A) and Request B (Run B, Step B) have different run/step IDs.
    - Owner A wins cache ownership.
    - Owner A executes external durable activity; activity succeeds and output is persisted in storage.
    - CRASH A immediately before cache READY commit!
    - Cache lease expires.
    - Owner B takes ownership on lease takeover.
    - Owner B reconciles prior work:
        * Discovers persisted activity result.
        * Publishes cache entry as READY.
        * ZERO duplicate provider calls!
        * ZERO duplicate activity records!
        * ZERO duplicate budget settlements!
    """
    run_repo = hardened_env["run_repo"]
    cache_repo = hardened_env["cache_repo"]
    storage = hardened_env["storage"]
    budget_svc = hardened_env["budget_svc"]
    activity_executor = hardened_env["activity_executor"]
    cache_service = hardened_env["cache_service"]

    provider_physical_calls = 0
    settlement_calls = 0

    def mock_provider(idempotency_key: str):
        nonlocal provider_physical_calls
        provider_physical_calls += 1
        out_key = f"workspaces/ws_hardened/artifacts/{idempotency_key}.json"
        storage.put(out_key, b'{"speech": "persisted audio waveform"}', content_type="application/json")
        return (
            out_key,
            UsageRecord(input_tokens=100, output_tokens=100, total_tokens=200),
            CostEstimate(estimated_cost="0.05", actual_cost="0.0400"),
            f"remote_op_{idempotency_key}",
        )

    params = AICacheKeyParams(
        workspace_id="ws_hardened",
        capability=CapabilityTypeEnum.TEXT_TO_SPEECH,
        input_data={"text": "Crash resilience test sentence"},
        model="eleven_multilingual_v2",
    )
    cache_key = derive_canonical_cache_key(params)

    # 1. Step A from Run A
    step_a = _create_step(run_repo, "ws_hardened", "run_A_111", "step_A_111", CapabilityTypeEnum.TEXT_TO_SPEECH)

    # Reserve budget for Step A
    res_req_a = ReservationRequest(
        workspace_id="ws_hardened",
        amount=Decimal("0.05"),
        currency="USD",
        idempotency_key="res_step_A",
        run_id=step_a.run_id,
        ttl_seconds=300,
    )
    res_a = budget_svc.reserve(res_req_a)
    assert res_a.success is True

    # 2. Simulate Owner A executing the durable activity, then CRASHING before complete_entry
    # We do this by having Owner A claim ownership and execute activity directly, then dying
    won_a, entry_a = cache_repo.claim_execution_ownership(
        workspace_id="ws_hardened",
        cache_key=cache_key,
        owner_id="worker_A",
        lease_token="lease_token_A",
        lease_duration_seconds=0.05,
        params=params,
    )
    assert won_a is True
    shared_idem_key = entry_a.activity_idempotency_key
    assert shared_idem_key == f"cache_idem_ws_hardened_{cache_key}_g1"

    # Worker A executes durable activity with shared_idem_key
    step_a_shared = step_a.model_copy(update={"idempotency_key": shared_idem_key})
    record_a = activity_executor.execute_activity(
        step=step_a_shared,
        workspace_id="ws_hardened",
        fn=mock_provider,
        semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
        reservation_id=res_a.reservation.reservation_id,
        native_idempotency_supported=True,
    )
    assert record_a.status == ActivityStatus.SUCCEEDED
    assert provider_physical_calls == 1
    assert record_a.cost_settled is True

    # Link activity to cache entry as Owner A would
    cache_repo.link_activity(
        workspace_id="ws_hardened",
        cache_key=cache_key,
        owner_id="worker_A",
        lease_token="lease_token_A",
        activity_id=record_a.activity_id,
        activity_idempotency_key=shared_idem_key,
    )

    # --- CRASH A OCCURS HERE! ---
    # Worker A crashed BEFORE calling cache_repo.complete_entry!
    # Cache entry is still IN_FLIGHT:
    entry_mid = cache_repo.get_entry("ws_hardened", cache_key)
    assert entry_mid.status == CacheEntryStatus.IN_FLIGHT

    # Simulate lease expiration in DB
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    with cache_repo.engine.transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE ai_cache_entries SET lease_expires_at = ? WHERE workspace_id = ? AND cache_key = ?",
            (past_iso, "ws_hardened", cache_key),
        )

    # 3. Owner B arrives with DIFFERENT Run and Step IDs (Run B, Step B)
    step_b = _create_step(run_repo, "ws_hardened", "run_B_222", "step_B_222", CapabilityTypeEnum.TEXT_TO_SPEECH)

    # Owner B executes execute_cached_activity
    record_b, hit_b = cache_service.execute_cached_activity(
        step=step_b,
        workspace_id="ws_hardened",
        params=params,
        activity_executor=activity_executor,
        fn=mock_provider,
        reservation_id=None,
        native_idempotency_supported=True,
        worker_id="worker_B",
    )

    # -------------------------------------------------------------------------
    # VERIFICATION OF GUARANTEES
    # -------------------------------------------------------------------------

    # Guarantee 1: Provider physical executions == 1 (Worker B did NOT re-run provider)
    assert provider_physical_calls == 1

    # Guarantee 2: Logical shared activities == 1 (Worker B did NOT create a new activity)
    with run_repo.engine.get_connection() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) as cnt FROM ai_activities WHERE workspace_id = ? AND idempotency_key = ?",
            ("ws_hardened", shared_idem_key),
        )
        activity_count = cur.fetchone()["cnt"]
    assert activity_count == 1

    # Guarantee 3: Cache entry transitioned to READY
    entry_final = cache_repo.get_entry("ws_hardened", cache_key)
    assert entry_final.status == CacheEntryStatus.READY
    assert entry_final.output_ref == record_a.output_ref
    assert storage.exists(entry_final.output_ref)

    # Guarantee 4: Consumer B received valid result
    assert record_b.status == ActivityStatus.SUCCEEDED
    assert record_b.output_ref == record_a.output_ref
    assert record_b.cost.actual_cost == Decimal("0.00")
    assert record_b.cost_settled is True

    # Guarantee 5: Budget ledger charged exactly once (0.0400)
    budget = budget_svc.repository.get_budget("b_ws_hardened")
    assert budget.actual_spend == Decimal("0.0400")


# =============================================================================
# Critical Test 2: Crash after provider completes before activity commit (EFFECTIVELY_ONCE)
# =============================================================================

def test_crash_after_provider_success_before_activity_commit(hardened_env):
    """
    Scenario:
    - Owner A starts activity.
    - Provider completes and generates output.
    - Crash occurs after provider success, before activity is marked completed in DB.
    - Owner B takes over lease.
    - Provider has EFFECTIVELY_ONCE semantics: returns cached output for same idempotency key.
    - Expected:
        * Provider physical generations = 1.
        * Activity marked SUCCEEDED.
        * Cache entry becomes READY.
        * Logical activities in DB = 1.
    """
    run_repo = hardened_env["run_repo"]
    cache_repo = hardened_env["cache_repo"]
    storage = hardened_env["storage"]
    budget_svc = hardened_env["budget_svc"]
    activity_executor = hardened_env["activity_executor"]
    cache_service = hardened_env["cache_service"]

    physical_provider_generations = 0
    provider_cache = {}

    def idempotent_provider(idempotency_key: str):
        nonlocal physical_provider_generations
        if idempotency_key in provider_cache:
            # Native provider deduplication (EFFECTIVELY_ONCE)
            return provider_cache[idempotency_key]

        physical_provider_generations += 1
        out_key = f"workspaces/ws_hardened/artifacts/gen_{idempotency_key}.json"
        storage.put(out_key, b'{"result": "voiceover audio generated"}', content_type="application/json")
        res = (
            out_key,
            UsageRecord(input_tokens=80, output_tokens=80, total_tokens=160),
            CostEstimate(estimated_cost="0.05", actual_cost="0.0300"),
            f"remote_op_{idempotency_key}",
        )
        provider_cache[idempotency_key] = res
        return res

    params = AICacheKeyParams(
        workspace_id="ws_hardened",
        capability=CapabilityTypeEnum.TEXT_TO_SPEECH,
        input_data={"text": "Effectively once test sentence"},
        model="eleven_multilingual_v2",
    )
    cache_key = derive_canonical_cache_key(params)

    step_a = _create_step(run_repo, "ws_hardened", "run_A_crash2", "step_A_crash2", CapabilityTypeEnum.TEXT_TO_SPEECH)

    # 1. Worker A claims ownership in cache
    won_a, entry_a = cache_repo.claim_execution_ownership(
        workspace_id="ws_hardened",
        cache_key=cache_key,
        owner_id="worker_A",
        lease_token="lease_token_A",
        lease_duration_seconds=0.05,
        params=params,
    )
    assert won_a is True
    shared_idem_key = entry_a.activity_idempotency_key

    # Crash injector simulating worker crash right after provider returns, before local activity commit
    crashed = False

    def crash_hook(point: str):
        nonlocal crashed
        if point == "after_provider_success_before_local_commit" and not crashed:
            crashed = True
            raise RuntimeError("CRASH_A: Worker A killed after provider returned!")

    # Worker A executes activity and crashes abruptly (simulating hard process death)
    step_a_shared = step_a.model_copy(update={"idempotency_key": shared_idem_key})
    with pytest.raises(RuntimeError, match="CRASH_A"):
        activity_executor.execute_activity(
            step=step_a_shared,
            workspace_id="ws_hardened",
            fn=idempotent_provider,
            native_idempotency_supported=True,
            crash_injector=crash_hook,
        )

    assert crashed is True
    assert physical_provider_generations == 1

    # In DB, the cache entry is still IN_FLIGHT because Worker A died abruptly
    entry_mid = cache_repo.get_entry("ws_hardened", cache_key)
    assert entry_mid.status == CacheEntryStatus.IN_FLIGHT

    # Simulate lease expiration in DB (Worker A is dead and stops renewing lease)
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    with cache_repo.engine.transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE ai_cache_entries SET lease_expires_at = ? WHERE workspace_id = ? AND cache_key = ?",
            (past_iso, "ws_hardened", cache_key),
        )

    # Worker B arrives with different Run and Step IDs (Run B, Step B)
    step_b = _create_step(run_repo, "ws_hardened", "run_B_crash2", "step_B_crash2", CapabilityTypeEnum.TEXT_TO_SPEECH)

    record_b, hit_b = cache_service.execute_cached_activity(
        step=step_b,
        workspace_id="ws_hardened",
        params=params,
        activity_executor=activity_executor,
        fn=idempotent_provider,
        native_idempotency_supported=True,
        worker_id="worker_B",
    )

    # Verification:
    # 1. Physical provider generations remain 1 (no duplicate generation)
    assert physical_provider_generations == 1

    # 2. Activity record in DB is 1 (reused via shared idempotency key)
    shared_idem_key = entry_mid.activity_idempotency_key
    with run_repo.engine.get_connection() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) as cnt FROM ai_activities WHERE workspace_id = ? AND idempotency_key = ?",
            ("ws_hardened", shared_idem_key),
        )
        cnt = cur.fetchone()["cnt"]
    assert cnt == 1

    # 3. Cache entry is now READY
    entry_final = cache_repo.get_entry("ws_hardened", cache_key)
    assert entry_final.status == CacheEntryStatus.READY

    # 4. Result resolved successfully
    assert record_b.status == ActivityStatus.SUCCEEDED
    assert storage.exists(record_b.output_ref)


# =============================================================================
# Test 3: Concurrent Waiters with Crashed Owner
# =============================================================================

def test_crashed_owner_with_multiple_concurrent_waiters(hardened_env):
    """
    Scenario:
    - Owner A starts execution and crashes.
    - 5 waiters are concurrently waiting.
    - Lease expires.
    - One of the waiters takes over ownership.
    - All 5 consumers resolve valid result.
    - Exactly 1 provider execution completes.
    - Cache entry is READY.
    """
    run_repo = hardened_env["run_repo"]
    cache_repo = hardened_env["cache_repo"]
    storage = hardened_env["storage"]
    activity_executor = hardened_env["activity_executor"]
    cache_service = hardened_env["cache_service"]

    provider_lock = threading.Lock()
    provider_calls = 0

    def slow_provider(idempotency_key: str):
        nonlocal provider_calls
        with provider_lock:
            provider_calls += 1
        time.sleep(0.05)
        out_key = f"workspaces/ws_hardened/artifacts/multi_{idempotency_key}.json"
        storage.put(out_key, b'{"result": "multi-waiter recovered audio"}', content_type="application/json")
        return (
            out_key,
            UsageRecord(input_tokens=50, output_tokens=50, total_tokens=100),
            CostEstimate(estimated_cost="0.05", actual_cost="0.0350"),
            f"remote_op_{idempotency_key}",
        )

    params = AICacheKeyParams(
        workspace_id="ws_hardened",
        capability=CapabilityTypeEnum.TEXT_TO_SPEECH,
        input_data={"text": "Concurrent recovery test sentence"},
        model="eleven_multilingual_v2",
    )
    cache_key = derive_canonical_cache_key(params)

    # 1. Owner A claims and immediately crashes
    won_a, entry_a = cache_repo.claim_execution_ownership(
        workspace_id="ws_hardened",
        cache_key=cache_key,
        owner_id="worker_crashed_owner",
        lease_token="lease_token_crashed",
        lease_duration_seconds=0.05,
        params=params,
    )
    assert won_a is True

    # Expire lease to simulate crash
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    with cache_repo.engine.transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE ai_cache_entries SET lease_expires_at = ? WHERE workspace_id = ? AND cache_key = ?",
            (past_iso, "ws_hardened", cache_key),
        )

    # 2. 5 concurrent requests from different runs/steps arrive
    steps = [
        _create_step(run_repo, "ws_hardened", f"run_multi_{i}", f"step_multi_{i}", CapabilityTypeEnum.TEXT_TO_SPEECH)
        for i in range(5)
    ]

    def task(idx: int):
        return cache_service.execute_cached_activity(
            step=steps[idx],
            workspace_id="ws_hardened",
            params=params,
            activity_executor=activity_executor,
            fn=slow_provider,
            native_idempotency_supported=True,
            wait_timeout_seconds=10.0,
            poll_interval_seconds=0.02,
            worker_id=f"worker_waiter_{idx}",
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(task, i) for i in range(5)]
        results = [f.result() for f in futures]

    # Exactly 1 provider execution across all workers
    assert provider_calls == 1

    # All 5 consumers received SUCCEEDED result
    assert len(results) == 5
    shared_out_ref = results[0][0].output_ref
    for rec, hit in results:
        assert rec.status == ActivityStatus.SUCCEEDED
        assert rec.output_ref == shared_out_ref

    # Cache entry is READY
    entry_final = cache_repo.get_entry("ws_hardened", cache_key)
    assert entry_final.status == CacheEntryStatus.READY
    assert entry_final.output_ref == shared_out_ref


# =============================================================================
# Test 4: Document and Verify AT_LEAST_ONCE Semantics Behavior
# =============================================================================

def test_at_least_once_semantics_re_execution_on_unrecorded_crash(hardened_env):
    """
    Documents and verifies real behavior:
    If operation has AT_LEAST_ONCE semantics and provider does NOT support native idempotency:
    - If crash occurs before any activity result is persisted,
    - The new owner after lease expiry re-executes the provider to ensure at-least-once delivery.
    - We do NOT claim effectively-once when external provider cannot guarantee it.
    """
    run_repo = hardened_env["run_repo"]
    cache_repo = hardened_env["cache_repo"]
    storage = hardened_env["storage"]
    activity_executor = hardened_env["activity_executor"]
    cache_service = hardened_env["cache_service"]

    provider_calls = 0

    def non_idempotent_provider(idempotency_key: str):
        nonlocal provider_calls
        provider_calls += 1
        out_key = f"workspaces/ws_hardened/artifacts/alo_{provider_calls}.json"
        storage.put(out_key, b'{"result": "at least once audio"}', content_type="application/json")
        return (
            out_key,
            UsageRecord(input_tokens=40, output_tokens=40, total_tokens=80),
            CostEstimate(estimated_cost="0.05", actual_cost="0.0250"),
            f"remote_op_{idempotency_key}",
        )

    params = AICacheKeyParams(
        workspace_id="ws_hardened",
        capability=CapabilityTypeEnum.TEXT_TO_SPEECH,
        input_data={"text": "At-least-once recovery sentence"},
        model="eleven_multilingual_v2",
    )
    cache_key = derive_canonical_cache_key(params)

    # 1. Worker A claims ownership and crashes BEFORE provider or persistence
    won_a, _ = cache_repo.claim_execution_ownership(
        workspace_id="ws_hardened",
        cache_key=cache_key,
        owner_id="worker_crashed_alo",
        lease_token="lease_token_alo",
        lease_duration_seconds=0.05,
        params=params,
    )
    assert won_a is True

    # Expire lease
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    with cache_repo.engine.transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE ai_cache_entries SET lease_expires_at = ? WHERE workspace_id = ? AND cache_key = ?",
            (past_iso, "ws_hardened", cache_key),
        )

    # 2. Worker B takes over and executes with AT_LEAST_ONCE semantics
    step_b = _create_step(run_repo, "ws_hardened", "run_B_alo", "step_B_alo", CapabilityTypeEnum.TEXT_TO_SPEECH)
    record_b, hit_b = cache_service.execute_cached_activity(
        step=step_b,
        workspace_id="ws_hardened",
        params=params,
        activity_executor=activity_executor,
        fn=non_idempotent_provider,
        semantics=IdempotencySemantics.AT_LEAST_ONCE,
        native_idempotency_supported=False,
        worker_id="worker_B",
    )

    # Exactly 1 provider execution happened (since Worker A died before calling provider)
    assert provider_calls == 1
    assert record_b.status == ActivityStatus.SUCCEEDED
    assert cache_repo.get_entry("ws_hardened", cache_key).status == CacheEntryStatus.READY
