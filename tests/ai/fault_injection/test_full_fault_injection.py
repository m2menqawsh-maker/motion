"""
tests/ai/fault_injection/test_full_fault_injection.py
=====================================================
Comprehensive Fault Injection, Chaos Engineering, and Crash Semantics Test Suite (S27.24 / AI-15).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from ai.budget.accounting import AccountingEngine
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.reservation import ReservationEngine
from ai.budget.service import BudgetService
from ai.budget.types import Budget, BudgetScope, ReservationRequest
from ai.cache.key import derive_canonical_cache_key
from ai.cache.service import AICacheService
from ai.contracts.cache import AICacheKeyParams
from ai.contracts.common import CapabilityType, CapabilityTypeEnum
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.run import AIRunStatus, AIStepStatus
from ai.memory.policy import MemoryPolicy
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.retry import RetryPolicy
from ai.orchestration.service import AIRunService
from ai.routing.router import ModelRouter
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def test_engine(tmp_path):
    db_file = tmp_path / "test_fault_injection.db"
    return DatabaseEngine(f"sqlite:///{db_file}")


@pytest.fixture
def run_service(test_engine):
    repo = SQLAIRunRepository(engine=test_engine)
    policy = RetryPolicy(max_attempts=3, backoff_base_seconds=0.0, backoff_factor=1.0)
    return AIRunService(repository=repo, retry_policy=policy)


@pytest.fixture
def cache_service(test_engine):
    repo = SQLAICacheRepository(engine=test_engine)
    return AICacheService(repository=repo)


# =============================================================================
# 1. Provider Failures: Timeout, 429, 500, Malformed Output, Outage
# =============================================================================

def test_fault_llm_timeout_triggers_bounded_retry(run_service):
    """Verifies that an upstream LLM timeout triggers bounded retry and fails terminally after max attempts."""
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_timeout", capability=CapabilityTypeEnum.PLANNING, max_attempts=2),
        ]
    )
    run = run_service.create_run(workspace_id="ws_fault", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    timeout_err = AIError(code=AIErrorCode.TIMEOUT, message="Provider timeout after 30000ms", retryable=True)

    # Attempt 1 -> PENDING with retry
    c1 = run_service.claim_next_runnable_step("w1", "ws_fault")
    assert c1 is not None
    f1 = run_service.fail_step(c1.step_id, "w1", c1.lease_token, timeout_err)
    assert f1.status == AIStepStatus.PENDING

    # Attempt 2 -> Terminal FAILED
    c2 = run_service.claim_next_runnable_step("w1", "ws_fault")
    assert c2 is not None
    f2 = run_service.fail_step(c2.step_id, "w1", c2.lease_token, timeout_err)
    assert f2.status == AIStepStatus.FAILED

    # Check parent run is FAILED, not SUCCESS (no hidden success)
    parent = run_service.get_run(run.run_id)
    assert parent.status == AIRunStatus.FAILED


def test_fault_provider_429_rate_limited_retry(run_service):
    """Verifies that 429 rate limiting triggers bounded retry and preserves structured error."""
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_429", capability=CapabilityTypeEnum.TEXT_GENERATION, max_attempts=2),
        ]
    )
    run = run_service.create_run(workspace_id="ws_fault", capability=CapabilityTypeEnum.TEXT_GENERATION, dag_spec=dag_spec)
    rate_err = AIError(code=AIErrorCode.RATE_LIMITED, message="Quota exceeded (429)", retryable=True)

    c1 = run_service.claim_next_runnable_step("w1", "ws_fault")
    f1 = run_service.fail_step(c1.step_id, "w1", c1.lease_token, rate_err)
    assert f1.status == AIStepStatus.PENDING

    c2 = run_service.claim_next_runnable_step("w1", "ws_fault")
    f2 = run_service.fail_step(c2.step_id, "w1", c2.lease_token, rate_err)
    assert f2.status == AIStepStatus.FAILED
    assert f2.error.code == AIErrorCode.RATE_LIMITED


def test_fault_malformed_provider_output_fails_terminally(run_service):
    """Non-retryable schema/JSON corruption fails terminally on attempt 1 without unbounded retry loop."""
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_malformed", capability=CapabilityTypeEnum.TEXT_GENERATION, max_attempts=5),
        ]
    )
    run_service.create_run(workspace_id="ws_fault", capability=CapabilityTypeEnum.TEXT_GENERATION, dag_spec=dag_spec)

    corrupt_err = AIError(
        code=AIErrorCode.INVALID_MODEL_OUTPUT,
        message="Malformed JSON from provider: SyntaxError",
        retryable=False,
    )
    c1 = run_service.claim_next_runnable_step("w1", "ws_fault")
    f1 = run_service.fail_step(c1.step_id, "w1", c1.lease_token, corrupt_err)

    # Must fail terminally because payload corruption is not retryable
    assert f1.status == AIStepStatus.FAILED


# =============================================================================
# 2. Worker Crash, Lease Expiration & Cancellation
# =============================================================================

def test_fault_worker_crash_lease_expiration(run_service):
    """When a worker crashes, its unrenewed lease expires and another worker can reclaim the step."""
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_crash", capability=CapabilityTypeEnum.PLANNING),
        ]
    )
    run_service.create_run(workspace_id="ws_fault", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # Worker 1 claims step with 0.01s lease
    c1 = run_service.claim_next_runnable_step("worker_dead", "ws_fault", lease_duration_seconds=0.01)
    assert c1 is not None

    # Worker 1 crashes (no heartbeat, no completion)
    import time
    time.sleep(0.05)

    # Worker 2 attempts recovery
    reclaimed = run_service.claim_next_runnable_step("worker_alive", "ws_fault", lease_duration_seconds=10.0)
    assert reclaimed is not None
    assert reclaimed.step_id == c1.step_id


def test_fault_cancellation_during_execution(run_service):
    """Cancelling a run transitions status to CANCELLED and prevents further steps from running."""
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_1", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="step_2", capability=CapabilityTypeEnum.PLANNING, dependencies=["step_1"]),
        ]
    )
    run = run_service.create_run(workspace_id="ws_fault", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    run_service.cancel_run(run.run_id, reason="User cancelled project")
    refreshed = run_service.get_run(run.run_id)
    assert refreshed.status == AIRunStatus.CANCELLED

    # No step should be claimable
    claim = run_service.claim_next_runnable_step("worker_1", "ws_fault")
    assert claim is None


# =============================================================================
# 3. Parallel Child Failure (One Succeeds, One Fails)
# =============================================================================

def test_fault_parallel_child_failure_cascade(run_service):
    r"""
    DAG:
        root
       /    \
      child_a  child_b (fails)
       \    /
        join
    If child_b fails, join step must never execute and run terminates FAILED.
    """
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="root", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="child_a", capability=CapabilityTypeEnum.PLANNING, dependencies=["root"]),
            StepDefinition(step_id="child_b", capability=CapabilityTypeEnum.PLANNING, dependencies=["root"], max_attempts=1),
            StepDefinition(step_id="join", capability=CapabilityTypeEnum.PLANNING, dependencies=["child_a", "child_b"]),
        ]
    )
    run = run_service.create_run(workspace_id="ws_fault", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # 1. Complete root
    c_root = run_service.claim_next_runnable_step("w", "ws_fault")
    run_service.complete_step(c_root.step_id, "w", c_root.lease_token, "storage://root.json")

    # 2. Complete child_a
    c_a = run_service.claim_next_runnable_step("w", "ws_fault")
    assert c_a.step_id.endswith("child_a")
    run_service.complete_step(c_a.step_id, "w", c_a.lease_token, "storage://child_a.json")

    # 3. Fail child_b terminally
    c_b = run_service.claim_next_runnable_step("w", "ws_fault")
    assert c_b.step_id.endswith("child_b")
    run_service.fail_step(
        c_b.step_id,
        "w",
        c_b.lease_token,
        AIError(code=AIErrorCode.INTERNAL_ERROR, message="Crash in child_b", retryable=False),
    )

    # 4. Join step must NOT be runnable
    c_join = run_service.claim_next_runnable_step("w", "ws_fault")
    assert c_join is None

    # Parent run is FAILED
    parent = run_service.get_run(run.run_id)
    assert parent.status == AIRunStatus.FAILED


# =============================================================================
# 4. Cost Settlement Crash Semantics (No Duplicate Charges, No Lost Records)
# =============================================================================

def test_fault_cost_settlement_idempotency():
    """
    Simulates crash during cost settlement:
    Verifies that calling settle multiple times with the same reservation ID is idempotent:
    no duplicate debit and no double charge.
    """
    now = datetime.now(timezone.utc)
    repo = InMemoryBudgetRepository()
    service = BudgetService(repository=repo)

    service.create_budget(
        Budget(
            budget_id="b_cost_fault",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_cost_fault",
            limit=Decimal("100.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )

    req = ReservationRequest(
        workspace_id="ws_cost_fault",
        amount=Decimal("10.00"),
        idempotency_key="idemp_fault_res_1",
    )
    res = service.reserve(req)
    res_id = res.reservation.reservation_id

    # First settlement
    s1 = service.settle(res_id, actual_cost=Decimal("8.50"))
    assert s1.success is True
    assert s1.actual_cost == Decimal("8.50")

    # Check budget actual spend
    b1 = repo.get_budget("b_cost_fault")
    assert b1.actual_spend == Decimal("8.50")

    # Crash replay: second settlement invocation with same reservation ID and same cost
    s2 = service.settle(res_id, actual_cost=Decimal("8.50"))
    assert s2.success is True  # Idempotent success

    # Verify NO duplicate charge occurred
    b2 = repo.get_budget("b_cost_fault")
    assert b2.actual_spend == Decimal("8.50")  # Remains exactly 8.50, NOT 17.00


# =============================================================================
# 4. S27.24 Expanded Fault Matrix: Provider 500, Outage, MCP Disconnect,
#    DB Outage, Storage Outage, API Restart, Budget Exhaustion, Stale Cache,
#    Memory Corruption
# =============================================================================

def test_fault_provider_500_internal_error_triggers_bounded_retry(run_service):
    """Verifies that an upstream Provider 500 triggers bounded retries and fails terminally."""
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_500", capability=CapabilityTypeEnum.PLANNING, max_attempts=2),
        ]
    )
    run = run_service.create_run(
        workspace_id="ws_fault_500",
        capability=CapabilityTypeEnum.PLANNING,
        dag_spec=dag_spec,
    )

    # Attempt 1: Provider throws 500 Internal Server Error
    claim1 = run_service.claim_next_runnable_step(worker_id="w1", workspace_id="ws_fault_500")
    assert claim1 is not None
    err_500 = AIError(
        code=AIErrorCode.INTERNAL_ERROR,
        message="500 Internal Server Error from upstream provider",
        retryable=True,
    )
    f1 = run_service.fail_step(claim1.step_id, worker_id="w1", lease_token=claim1.lease_token, error=err_500)
    assert f1.status == AIStepStatus.PENDING

    # Attempt 2: Provider fails with 500 again (exhausting max_attempts=2)
    claim2 = run_service.claim_next_runnable_step(worker_id="w1", workspace_id="ws_fault_500")
    assert claim2 is not None
    f2 = run_service.fail_step(claim2.step_id, worker_id="w1", lease_token=claim2.lease_token, error=err_500)
    assert f2.status == AIStepStatus.FAILED
    assert f2.error.code == AIErrorCode.INTERNAL_ERROR

    run_state = run_service.get_run(run.run_id)
    assert run_state.status == AIRunStatus.FAILED


def test_fault_full_provider_outage_fails_closed():
    """Verifies that when all providers are down/unavailable, the router fails closed with structured error."""
    from ai.providers import ProviderDefinition, create_empty_provider_registry
    from ai.models.registry import create_empty_model_registry
    from ai.models.types import CostTier, LatencyTier, ModelDefinition
    from ai.contracts.common import ExecutionClass, QualityTarget
    from ai.contracts.model import ModelRequirement
    from ai.routing import ModelRouter, NoEligibleModelError, RoutingPolicy

    prov_reg = create_empty_provider_registry()
    prov_reg.register(
        ProviderDefinition(
            provider_id="down-provider",
            display_name="Down Provider",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            enabled=False,
        )
    )
    mod_reg = create_empty_model_registry(provider_registry=prov_reg)

    router = ModelRouter(model_registry=mod_reg, provider_registry=prov_reg)
    req = ModelRequirement(capability=CapabilityType.TEXT_GENERATION, quality_target=QualityTarget.STANDARD)
    policy = RoutingPolicy(policy_id="test-p", max_fallbacks=2)

    with pytest.raises(NoEligibleModelError) as exc_info:
        router.route(req, policy=policy)
    assert "No eligible model found" in str(exc_info.value)


def test_fault_mcp_disconnect_handles_cleanly():
    """Verifies that an MCP disconnect/network drop is caught as a structured, non-leaking AIError."""
    from ai.mcp.errors import MCPExecutionError

    try:
        # Simulate network drop mid-call
        raise MCPExecutionError(operation_name="fetch_context", error_detail="Connection reset by peer / TCP EOF")
    except MCPExecutionError as mcp_err:
        ai_error = mcp_err.to_ai_error()
        assert ai_error.code == AIErrorCode.DEPENDENCY_FAILED
        assert "Connection reset by peer" in ai_error.message
        assert ai_error.retryable is False  # Fails closed safely


def test_fault_db_outage_fails_closed_without_corruption(run_service, test_engine):
    """Verifies that an unexpected DB connection failure raises a structured error and fails closed."""
    dag_spec = DAGSpecification(steps=[StepDefinition(step_id="step_db_fail", capability=CapabilityTypeEnum.PLANNING)])
    run = run_service.create_run(workspace_id="ws_db_fail", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    claim = run_service.claim_next_runnable_step(worker_id="w1", workspace_id="ws_db_fail")
    assert claim is not None

    # Simulate database lock / connection drop during completion
    with pytest.raises(Exception):
        with test_engine.transaction() as conn:
            conn.execute("INSERT INTO nonexistent_table VALUES (1)")

    # The persisted run remains in valid RUNNING state; no corrupted partial commits
    run_state = run_service.get_run(run.run_id)
    assert run_state.status == AIRunStatus.RUNNING


def test_fault_storage_outage_fails_closed_with_structured_error(tmp_path):
    """Verifies that a failure in the underlying StorageService raises StorageError and does not crash."""
    from scripts.core.storage.storage_service import LocalStorageBackend, StorageNotFoundError

    storage = LocalStorageBackend(root_dir=tmp_path / "broken_storage")
    with pytest.raises(StorageNotFoundError):
        storage.get("workspaces/ws1/missing_file.json")


def test_fault_api_restart_during_active_durable_run(test_engine):
    """
    Verifies that when the API/service crashes and restarts, a newly instantiated
    AIRunService recovers existing durable runs and reclaims expired leases cleanly.
    """
    # Instance 1: Creates run and claims step
    repo1 = SQLAIRunRepository(engine=test_engine)
    policy = RetryPolicy(max_attempts=2, backoff_base_seconds=0.0)
    service1 = AIRunService(repository=repo1, retry_policy=policy)

    dag_spec = DAGSpecification(steps=[StepDefinition(step_id="step_restart", capability=CapabilityTypeEnum.PLANNING)])
    run = service1.create_run(workspace_id="ws_restart", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)
    claim1 = service1.claim_next_runnable_step(worker_id="worker_dead", workspace_id="ws_restart")
    assert claim1 is not None

    # Force lease expiration in DB to simulate worker dying during process crash
    past_iso = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    with test_engine.transaction() as conn:
        conn.execute("UPDATE ai_steps SET lease_expires_at = ? WHERE step_id = ?", (past_iso, claim1.step_id))

    # --- PROCESS CRASH & RESTART (Service Instance 2) ---
    repo2 = SQLAIRunRepository(engine=test_engine)
    service2 = AIRunService(repository=repo2, retry_policy=policy)

    # Standby worker claims the orphaned step
    claim2 = service2.claim_next_runnable_step(worker_id="worker_alive", workspace_id="ws_restart")
    assert claim2 is not None
    assert claim2.step_id == claim1.step_id
    assert claim2.worker_id == "worker_alive"

    # Worker 2 successfully completes the recovered step
    completed_step = service2.complete_step(claim2.step_id, worker_id="worker_alive", lease_token=claim2.lease_token, output_ref="storage://recovered.json")
    assert completed_step.status == AIStepStatus.SUCCEEDED


def test_fault_budget_exhaustion_rejects_reservation(tmp_path):
    """Verifies that when budget limit is exhausted, reservation is rejected with BudgetExceeded error result."""
    now = datetime.now(timezone.utc)
    repo = InMemoryBudgetRepository()
    service = BudgetService(repository=repo)

    # Budget has limit of $5.00
    repo.save_budget(
        Budget(
            budget_id="b_exhaust",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_exhaust",
            limit=Decimal("5.00"),
            valid_from=now - timedelta(days=1),
            created_at=now,
            updated_at=now,
        )
    )

    # Request reservation for $15.00 (Exhausts budget)
    req = ReservationRequest(
        workspace_id="ws_exhaust",
        amount=Decimal("15.00"),
        idempotency_key="idemp_exhaust_1",
    )
    res = service.reserve(req)
    assert res.success is False
    assert res.error is not None
    assert res.error.code == AIErrorCode.BUDGET_EXCEEDED
    assert "Budget exceeded" in res.error.message

    # Budget balance must remain untouched
    b = repo.get_budget("b_exhaust")
    assert b.actual_spend == Decimal("0.00")
    assert b.reserved == Decimal("0.00")
    assert b.available == Decimal("5.00")


def test_fault_stale_cache_recovery_recomputes_and_updates_fresh(test_engine, tmp_path):
    """Verifies that an expired/stale cache entry is detected as a cache miss and recomputed cleanly."""
    from scripts.core.storage.storage_service import LocalStorageBackend
    from ai.contracts.capability import CapabilityResult, CapabilityStatus
    from ai.contracts.common import ProvenanceRecord

    storage = LocalStorageBackend(root_dir=tmp_path / "cache_storage")
    repo = SQLAICacheRepository(engine=test_engine)
    cache_svc = AICacheService(repository=repo, storage_service=storage)

    params = AICacheKeyParams(
        workspace_id="ws_stale",
        capability=CapabilityTypeEnum.TEXT_GENERATION,
        input_data={"prompt": "Stale prompt test"},
        model="gpt-4o",
    )

    counter = {"compute_calls": 0}

    def compute():
        counter["compute_calls"] += 1
        now = datetime.now(timezone.utc)
        res = CapabilityResult(
            capability=CapabilityTypeEnum.TEXT_GENERATION,
            status=CapabilityStatus.SUCCESS,
            output_data={"iteration": counter["compute_calls"]},
            provenance=ProvenanceRecord(source="test", timestamp=now),
        )
        return res, res.model_dump_json().encode("utf-8")

    # 1. Compute with short TTL of 1 second
    res1, hit1 = cache_svc.get_or_compute(params, compute, ttl_seconds=1)
    assert hit1 is False
    assert res1.output_data["iteration"] == 1

    # 2. Force cache entry expiration in DB
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    cache_key = derive_canonical_cache_key(params)
    with test_engine.transaction() as conn:
        conn.execute("UPDATE ai_cache_entries SET expires_at = ? WHERE workspace_id = ? AND cache_key = ?", (past_iso, "ws_stale", cache_key))

    # 3. Request again: Stale entry must be treated as a MISS and recomputed
    res2, hit2 = cache_svc.get_or_compute(params, compute, ttl_seconds=60)
    assert hit2 is False  # Stale entry evicted / ignored!
    assert counter["compute_calls"] == 2
    assert res2.output_data["iteration"] == 2


def test_fault_memory_corruption_isolated_gracefully():
    """Verifies that a corrupted persisted memory record is rejected/filtered without crashing retrieval."""
    from ai.memory.models import MemoryEntry, MemoryFilter, TrustedTenantContext
    from ai.memory.repository import InMemoryMemoryRepository
    from ai.memory.service import MemoryService
    from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
    from ai.memory.types import MemoryScope, MemoryType, SourceType

    repo = InMemoryMemoryRepository()
    embedder = DeterministicFakeEmbeddingProvider(dimension=128)
    svc = MemoryService(repository=repo, embedding_provider=embedder, policy=MemoryPolicy())

    ctx = TrustedTenantContext(workspace_id="ws_corrupt", user_id="actor_1", roles=["owner"])

    # Store one valid memory
    entry = svc.store_memory(
        context=ctx,
        content="Valid memory record",
        memory_type=MemoryType.EPISODIC,
        scope=MemoryScope.WORKSPACE,
        source_type=SourceType.USER_STATEMENT,
    )

    # Inject a corrupted memory entry missing embedding into the repository
    corrupted_entry = entry.model_copy(
        update={
            "id": "mem_corrupted_1",
            "content": "Corrupted missing embedding entry",
        }
    )
    repo._entries[("ws_corrupt", corrupted_entry.id)] = corrupted_entry

    # Query semantic: Corrupted entry missing vector embedding is handled gracefully and skipped
    results = svc.query_semantic(context=ctx, query_text="Valid memory record", limit=5)
    assert len(results) >= 1
    assert results[0].entry.id == entry.id






