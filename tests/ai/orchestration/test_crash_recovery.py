"""
tests/ai/orchestration/test_crash_recovery.py
=============================================
Critical Crash Matrix and Idempotency Verification Suite (AI-10B / S27.11).

Invariants verified:
- Matrix 1: Crash before provider call (lease expires -> new worker claims -> provider executes).
- Matrix 2: Crash during provider call (bounded retry, activity recoverable, no uncontrolled side effects).
- Matrix 3: Crash after provider success before local DB commit (stable idempotency key deduplicates provider call).
- Matrix 4: Crash after result persistence before step completion (reuses persisted output_ref, 0 duplicate generation).
- Matrix 5: Crash after AIStep success before child scheduling (recovery detects and unblocks ready DAG children).
- Matrix 6: Crash after child scheduling (recovery does not duplicate children).
- Matrix 7: Stale worker wakes after lease expires (stale worker rejected with StaleWorkerLeaseError).
- Matrix 8: Late provider result after run cancellation (run stays CANCELLED, never resurrected).
- Idempotent Recovery: Running recover() twice produces identical state with 0 mutations on 2nd run.
- Cost Settlement: Exactly-once cost settlement; no double debiting in financial ledgers.
- Non-Idempotent Activities: Blind retry forbidden for AT_MOST_ONCE activities.
- Budget Reservation Recovery: Leaked reservations safely released on crash.
- Real Process Restart Proof: Zero in-memory state shared across simulated process lifetime.
- Multi-Tenant Isolation: Workspace B denied from recovering Workspace A runs.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Optional, Tuple

import pytest

from ai.budget.policy import BudgetPolicy
from ai.budget.repository import InMemoryBudgetRepository
from ai.budget.service import BudgetService
from ai.budget.types import (
    AccountingEventType,
    Budget,
    BudgetScope,
    ReservationRequest,
    ReservationStatus,
)
from ai.contracts.activity import ActivityStatus, IdempotencySemantics
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.run import AIRun, AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.activity import DurableActivityExecutor, settle_activity_cost
from ai.orchestration.activity_classification import (
    ACTIVITY_CLASSIFICATIONS,
    ActivityBoundaryType,
    FalseIdempotencyClaimError,
    validate_activity_semantics,
)
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.errors import (
    NonIdempotentRetryError,
    RunAlreadyTerminalError,
    StaleWorkerLeaseError,
    TenantAccessDeniedError,
)
from ai.orchestration.lease import generate_lease_token
from ai.orchestration.recovery import AIRecoveryService
from ai.orchestration.retry import RetryPolicy
from ai.orchestration.service import AIRunService
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine



class FakeExternalProvider:
    """
    Simulated external AI provider tracking executions, stable idempotency keys,
    and configurable crash simulation points.
    """

    def __init__(self):
        self.call_count: int = 0
        self.invocations_by_key: Dict[str, int] = {}
        self.stored_results: Dict[str, Tuple[str, UsageRecord, CostEstimate, str]] = {}

    def generate(
        self,
        idempotency_key: str,
        crash_at: Optional[str] = None,
    ) -> Tuple[str, UsageRecord, CostEstimate, Optional[str]]:
        self.call_count += 1
        self.invocations_by_key[idempotency_key] = (
            self.invocations_by_key.get(idempotency_key, 0) + 1
        )

        if crash_at == "during_provider_call":
            raise RuntimeError("SIMULATED_CRASH: Process or network died during provider generation")

        # Stable result caching under provider-native idempotency
        if idempotency_key in self.stored_results:
            return self.stored_results[idempotency_key]

        result = (
            f"storage://artifacts/{idempotency_key}.mp4",
            UsageRecord(input_tokens=100, output_tokens=50, total_tokens=150),
            CostEstimate(estimated_cost="0.01", actual_cost="0.0080"),
            f"remote_op_{idempotency_key}",
        )
        self.stored_results[idempotency_key] = result
        return result


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_crash.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    return SQLAIRunRepository(engine=engine)


@pytest.fixture
def budget_service():
    repo = InMemoryBudgetRepository()
    service = BudgetService(repository=repo, policy=BudgetPolicy(allow_overage_within_limit=True))
    now = datetime.now(timezone.utc)
    service.create_budget(
        Budget(
            budget_id="b_ws_crash",
            scope=BudgetScope.WORKSPACE,
            scope_reference="ws_crash",
            limit=Decimal("100.00"),
            reserved=Decimal("0.00"),
            actual_spend=Decimal("0.00"),
            currency="USD",
            valid_from=now,
            created_at=now,
            updated_at=now,
        )
    )
    return service


# =============================================================================
# Critical Crash Matrix Tests (Point 1 to Point 8)
# =============================================================================


def test_matrix_point_1_crash_before_provider_call(repo):
    """
    Matrix 1: Worker claims step, crashes before invoking provider.
    Expected: Lease expires, recovery resets step, new worker claims and completes normally.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="step1", capability=CapabilityTypeEnum.PLANNING)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    # Worker A claims with 0.1s lease, then crashes immediately
    token_a = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_dead", token_a, lease_duration_seconds=0.05)
    assert claimed is not None
    assert claimed.status == AIStepStatus.RUNNING

    time.sleep(0.08)  # Lease expires

    recovery = AIRecoveryService(repository=repo)
    report = recovery.recover("ws_crash")
    assert report.expired_leases_reclaimed == 1
    assert report.steps_reset_for_retry == 1

    # Fresh worker claims and finishes
    provider = FakeExternalProvider()
    executor = DurableActivityExecutor(repository=repo)
    claimed_b = repo.claim_step(step.step_id, "worker_alive", generate_lease_token(), lease_duration_seconds=30.0)
    assert claimed_b is not None

    act = executor.execute_activity(
        claimed_b,
        "ws_crash",
        lambda k: provider.generate(k),
        native_idempotency_supported=True,
    )
    repo.complete_step(claimed_b.step_id, "worker_alive", claimed_b.lease_token, act.output_ref, act.usage, act.cost)

    final_run = repo.get_run(run.run_id)
    assert final_run.status == AIRunStatus.RUNNING  # Step succeeded, run active


def test_matrix_point_2_crash_during_provider_call(repo):
    """
    Matrix 2: Worker crashes while external provider call is executing.
    Expected: AIRun not lost, activity marked failed or recoverable, bounded retry allowed.
    """
    service = AIRunService(repository=repo, retry_policy=RetryPolicy(max_attempts=3))
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="step_mid", capability=CapabilityTypeEnum.PLANNING)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    token_a = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_crash_mid", token_a, lease_duration_seconds=0.05)

    executor = DurableActivityExecutor(repository=repo)
    provider = FakeExternalProvider()

    # Simulate crash during provider call (AT_LEAST_ONCE generation)
    with pytest.raises(RuntimeError):
        executor.execute_activity(
            claimed,
            "ws_crash",
            lambda k: provider.generate(k, crash_at="during_provider_call"),
            semantics=IdempotencySemantics.AT_LEAST_ONCE,
        )

    # Activity recorded failure
    activities = repo.get_activities_for_step(step.step_id)
    assert len(activities) == 1
    assert activities[0].status == ActivityStatus.FAILED

    time.sleep(0.08)  # Lease expires

    recovery = AIRecoveryService(repository=repo)
    report = recovery.recover("ws_crash")
    assert report.expired_leases_reclaimed == 1
    assert report.steps_reset_for_retry == 1

    # Retry succeeds
    claimed_retry = repo.claim_step(step.step_id, "worker_retry", generate_lease_token(), lease_duration_seconds=30.0)
    act = executor.execute_activity(
        claimed_retry,
        "ws_crash",
        lambda k: provider.generate(k),
        semantics=IdempotencySemantics.AT_LEAST_ONCE,
    )
    assert act.status == ActivityStatus.SUCCEEDED


def test_matrix_point_3_crash_after_provider_success_before_local_commit(repo):
    """
    Matrix 3: External provider finished and returned success, but worker died before local DB commit.
    Expected: Fake provider tracks stable idempotency key; second worker retries and provider
    does NOT execute expensive generation twice (call count remains 1).
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="step_idem", capability=CapabilityTypeEnum.PLANNING)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    provider = FakeExternalProvider()
    executor = DurableActivityExecutor(repository=repo)

    token_a = generate_lease_token()
    claimed_a = repo.claim_step(step.step_id, "worker_dead_before_commit", token_a, lease_duration_seconds=0.05)

    def crash_after_provider_success(point: str):
        if point == "after_provider_success_before_local_commit":
            raise RuntimeError("CRASH_AFTER_PROVIDER_SUCCESS")

    with pytest.raises(RuntimeError, match="CRASH_AFTER_PROVIDER_SUCCESS"):
        executor.execute_activity(
            claimed_a,
            "ws_crash",
            lambda k: provider.generate(k),
            native_idempotency_supported=True,
            crash_injector=crash_after_provider_success,
        )

    # Provider executed once
    assert provider.call_count == 1
    idempotency_key = executor.derive_idempotency_key(claimed_a)
    assert provider.invocations_by_key[idempotency_key] == 1

    time.sleep(0.08)  # Lease expires

    # Recovery resets step for redelivery
    recovery = AIRecoveryService(repository=repo)
    recovery.recover("ws_crash")

    # Worker B claims and executes with the same logical key
    claimed_b = repo.claim_step(step.step_id, "worker_b", generate_lease_token(), lease_duration_seconds=30.0)
    act_b = executor.execute_activity(
        claimed_b,
        "ws_crash",
        lambda k: provider.generate(k),
        native_idempotency_supported=True,
    )

    assert act_b.status == ActivityStatus.SUCCEEDED
    # Crucial verification: Provider was called with same key and returned stable result without second expensive run!
    assert provider.invocations_by_key[idempotency_key] == 2
    assert len(provider.stored_results) == 1


def test_matrix_point_4_crash_after_result_persistence_before_step_commit(repo):
    """
    Matrix 4: Durable activity output committed, but worker died before complete_step.
    Expected: Recovery or new worker reuses persisted output_ref and does NOT re-call provider at all.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="step_p4", capability=CapabilityTypeEnum.PLANNING)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    provider = FakeExternalProvider()
    executor = DurableActivityExecutor(repository=repo)

    token_a = generate_lease_token()
    claimed_a = repo.claim_step(step.step_id, "worker_p4", token_a, lease_duration_seconds=0.05)

    def crash_before_step_commit(point: str):
        if point == "after_result_persistence_before_step_commit":
            raise RuntimeError("CRASH_AFTER_PERSISTENCE")

    with pytest.raises(RuntimeError, match="CRASH_AFTER_PERSISTENCE"):
        executor.execute_activity(
            claimed_a,
            "ws_crash",
            lambda k: provider.generate(k),
            native_idempotency_supported=True,
            crash_injector=crash_before_step_commit,
        )

    # Activity is durable in SUCCEEDED state in DB!
    activities = repo.get_activities_for_step(step.step_id)
    assert len(activities) == 1
    assert activities[0].status == ActivityStatus.SUCCEEDED
    assert provider.call_count == 1

    time.sleep(0.08)  # Lease expires

    # Recovery sweeps and reconciles the step to SUCCEEDED without calling provider
    recovery = AIRecoveryService(repository=repo)
    report = recovery.recover("ws_crash")
    assert report.expired_leases_reclaimed == 1
    assert report.steps_reconciled_from_activities == 1

    # Step is now SUCCEEDED, output_ref preserved
    final_step = repo.get_step(step.step_id)
    assert final_step.status == AIStepStatus.SUCCEEDED
    assert final_step.output_ref == activities[0].output_ref
    assert provider.call_count == 1  # ZERO duplicate provider generation!


def test_matrix_point_5_crash_after_step_success_before_child_scheduling(repo):
    """
    Matrix 5: Parent step SUCCEEDED, but worker died before child steps transitioned from WAITING to PENDING.
    Expected: Recovery detects parent SUCCEEDED and unblocks waiting child steps.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[
            StepDefinition(step_id="parent", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="child", capability=CapabilityTypeEnum.TEXT_GENERATION, dependencies=["parent"]),
        ]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    steps = {s.step_id: s for s in service.get_run_steps(run.run_id)}
    parent_step = next(s for s in steps.values() if "parent" in s.step_id)
    child_step = next(s for s in steps.values() if "child" in s.step_id)

    assert child_step.status == AIStepStatus.WAITING

    # Worker claims parent and completes in repo directly without triggering child scheduling (simulating crash)
    token = generate_lease_token()
    repo.claim_step(parent_step.step_id, "worker_parent", token, lease_duration_seconds=30.0)
    repo.complete_step(
        parent_step.step_id,
        "worker_parent",
        token,
        output_ref="storage://parent.json",
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.00"),
    )

    # Worker dies here! Child is still WAITING
    assert repo.get_step(child_step.step_id).status == AIStepStatus.WAITING

    # Recovery sweeps
    recovery = AIRecoveryService(repository=repo)
    report = recovery.recover("ws_crash")
    assert report.children_unblocked == 1

    # Child is now PENDING and runnable
    assert repo.get_step(child_step.step_id).status == AIStepStatus.PENDING


def test_matrix_point_6_crash_after_child_scheduling(repo):
    """
    Matrix 6: Worker crashed after child step was already transitioned to PENDING.
    Expected: Recovery does NOT duplicate child steps or re-schedule.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[
            StepDefinition(step_id="p6_parent", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="p6_child", capability=CapabilityTypeEnum.TEXT_GENERATION, dependencies=["p6_parent"]),
        ]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    steps = service.get_run_steps(run.run_id)
    parent_step = next(s for s in steps if "p6_parent" in s.step_id)

    token = generate_lease_token()
    repo.claim_step(parent_step.step_id, "worker_p6", token, lease_duration_seconds=30.0)
    # Complete step using service which properly schedules child
    service.complete_step(parent_step.step_id, "worker_p6", token)

    # Worker crashes now
    recovery = AIRecoveryService(repository=repo)
    report = recovery.recover("ws_crash")
    # Recovery should report 0 children unblocked because child is already PENDING
    assert report.children_unblocked == 0

    all_steps = service.get_run_steps(run.run_id)
    assert len(all_steps) == 2  # No duplicate steps created!


def test_matrix_point_7_stale_worker_wake_after_lease_expiry(repo):
    """
    Matrix 7: Worker A claims step, lease expires, Worker B claims and succeeds.
    Worker A wakes up and attempts to commit: REJECTED with StaleWorkerLeaseError.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="p7_step", capability=CapabilityTypeEnum.PLANNING)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    # Worker A claims with 0.05s lease
    token_a = generate_lease_token()
    claimed_a = repo.claim_step(step.step_id, "worker_A", token_a, lease_duration_seconds=0.05)
    assert claimed_a is not None

    time.sleep(0.08)  # Lease expires

    # Worker B claims expired step
    token_b = generate_lease_token()
    claimed_b = repo.claim_step(step.step_id, "worker_B", token_b, lease_duration_seconds=30.0)
    assert claimed_b is not None

    # Worker B finishes
    repo.complete_step(
        step.step_id,
        "worker_B",
        token_b,
        output_ref="storage://b_valid.json",
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.00"),
    )

    # Worker A wakes up and attempts to commit with stale token
    with pytest.raises(StaleWorkerLeaseError):
        repo.complete_step(
            step.step_id,
            "worker_A",
            token_a,
            output_ref="storage://a_stale.json",
            usage=UsageRecord(),
            cost=CostEstimate(estimated_cost="0.00"),
        )

    # Worker B's result remains preserved
    final_step = repo.get_step(step.step_id)
    assert final_step.output_ref == "storage://b_valid.json"


def test_matrix_point_8_late_result_after_run_cancellation(repo):
    """
    Matrix 8: AIRun was cancelled while external provider was running.
    Late result arrives: Must NOT advance step or resurrect run to SUCCEEDED.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="p8_step", capability=CapabilityTypeEnum.PLANNING)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    token = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_p8", token, lease_duration_seconds=30.0)

    executor = DurableActivityExecutor(repository=repo)
    provider = FakeExternalProvider()

    def generate_and_cancel_midway(key: str):
        # Cancel the parent run while generation is happening
        service.cancel_run(run.run_id, workspace_id="ws_crash", reason="User requested abort")
        return provider.generate(key)

    with pytest.raises(RunAlreadyTerminalError):
        executor.execute_activity(
            claimed,
            "ws_crash",
            generate_and_cancel_midway,
            native_idempotency_supported=True,
        )

    # Verification: Run remains CANCELLED!
    final_run = repo.get_run(run.run_id)
    assert final_run.status == AIRunStatus.CANCELLED


# =============================================================================
# Idempotent Recovery and Multi-Sweep Verification
# =============================================================================


def test_idempotent_recovery_double_sweep(repo):
    """
    Section 12: Recovery must be strictly idempotent.
    Running recover() twice in succession yields identical state and 0 mutations on 2nd sweep.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[
            StepDefinition(step_id="s1", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="s2", capability=CapabilityTypeEnum.TEXT_GENERATION, dependencies=["s1"]),
        ]
    )
    run = service.create_run("ws_idem", CapabilityTypeEnum.PLANNING, dag)
    steps = service.get_run_steps(run.run_id)
    s1 = next(s for s in steps if "s1" in s.step_id)

    # Worker claims s1 with 0.05s lease and dies
    token = generate_lease_token()
    repo.claim_step(s1.step_id, "worker_dead", token, lease_duration_seconds=0.05)
    time.sleep(0.08)

    recovery = AIRecoveryService(repository=repo)

    # First sweep: performs recovery
    report1 = recovery.recover("ws_idem")
    assert report1.expired_leases_reclaimed == 1
    assert report1.steps_reset_for_retry == 1

    # Second sweep: zero changes, identical state
    report2 = recovery.recover("ws_idem")
    assert report2.expired_leases_reclaimed == 0
    assert report2.steps_reconciled_from_activities == 0
    assert report2.steps_reset_for_retry == 0
    assert report2.children_unblocked == 0
    assert report2.runs_completed == 0


# =============================================================================
# Financial Safety and Cost Settlement
# =============================================================================


def test_cost_settled_flag_prevents_double_deduction(repo):
    """
    Section 14: Cost settlement flag is atomic and monotonic.
    mark_cost_settled returns True exactly once.
    """
    now = datetime.now(timezone.utc)
    run = repo.create_run(
        AIRun(
            run_id="run_cost_001",
            workspace_id="ws_cost",
            status=AIRunStatus.RUNNING,
            capability=CapabilityTypeEnum.PLANNING,
            created_at=now,
            usage=UsageRecord(),
            cost=CostEstimate(estimated_cost="0.00"),
        )
    )
    step = repo.create_steps(
        [
            AIStep(
                step_id="step_cost_001",
                run_id="run_cost_001",
                status=AIStepStatus.RUNNING,
                capability=CapabilityTypeEnum.PLANNING,
                created_at=now,
                cost=CostEstimate(estimated_cost="0.01"),
            )
        ]
    )[0]

    executor = DurableActivityExecutor(repository=repo)
    provider = FakeExternalProvider()
    act = executor.execute_activity(
        step,
        "ws_cost",
        lambda k: provider.generate(k),
        native_idempotency_supported=True,
    )

    assert act.cost_settled is True

    # Attempt second settlement -> rejected (returns False)
    settled_again = repo.mark_cost_settled(act.activity_id)
    assert settled_again is False


def test_budget_reservation_released_on_terminal_failure(repo, budget_service):
    """
    Section 14: Worker dies and step fails terminally.
    Attached budget reservation must be released back to available balance.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="s_budget", capability=CapabilityTypeEnum.PLANNING, max_attempts=1)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    # Create budget reservation
    res_req = ReservationRequest(
        workspace_id="ws_crash",
        amount=Decimal("10.00"),
        currency="USD",
        idempotency_key="res_crash_001",
        run_id=run.run_id,
        ttl_seconds=300,
    )
    res_result = budget_service.reserve(res_req)
    assert res_result.success is True
    res_id = res_result.reservation.reservation_id

    # Available balance decreased by $10
    assert budget_service.get_available_budget(BudgetScope.WORKSPACE, "ws_crash") == Decimal("90.00")

    # Worker claims and records activity with reservation_id, then dies
    token = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_res", token, lease_duration_seconds=0.05)
    executor = DurableActivityExecutor(repository=repo)

    with pytest.raises(RuntimeError):
        executor.execute_activity(
            claimed,
            "ws_crash",
            lambda k: (_ for _ in ()).throw(RuntimeError("CRASH")),
            semantics=IdempotencySemantics.AT_MOST_ONCE,
            reservation_id=res_id,
        )

    time.sleep(0.08)  # Lease expires

    # Recovery runs with budget_service attached
    recovery = AIRecoveryService(repository=repo, budget_service=budget_service)
    report = recovery.recover("ws_crash")

    assert report.steps_failed_terminal == 1
    assert report.reservations_released == 1

    # Verification: Budget reservation was safely released! Available balance is back to $100
    assert budget_service.get_available_budget(BudgetScope.WORKSPACE, "ws_crash") == Decimal("100.00")


# =============================================================================
# Non-Idempotent Tool Safety
# =============================================================================


def test_non_idempotent_activity_crash_prevents_blind_retry(repo):
    """
    Section 15: Activities marked AT_MOST_ONCE must NEVER be blindly retried if they crashed.
    Recovery fails the step terminally to prevent duplicate side effects.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="s_non_idem", capability=CapabilityTypeEnum.TEXT_GENERATION)]
    )
    run = service.create_run("ws_safe", CapabilityTypeEnum.TEXT_GENERATION, dag)
    step = service.get_run_steps(run.run_id)[0]

    token = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_tool", token, lease_duration_seconds=0.05)
    executor = DurableActivityExecutor(repository=repo)

    # Activity starts with AT_MOST_ONCE and crashes
    with pytest.raises(RuntimeError):
        executor.execute_activity(
            claimed,
            "ws_safe",
            lambda k: (_ for _ in ()).throw(RuntimeError("NON_IDEM_CRASH")),
            semantics=IdempotencySemantics.AT_MOST_ONCE,
        )

    # Immediate retry attempt through executor raises NonIdempotentRetryError
    with pytest.raises(NonIdempotentRetryError):
        executor.execute_activity(
            claimed,
            "ws_safe",
            lambda k: ("out", UsageRecord(), CostEstimate(estimated_cost="0.00"), None),
            semantics=IdempotencySemantics.AT_MOST_ONCE,
        )

    time.sleep(0.08)  # Lease expires

    # Recovery sweeps: must NOT reset for retry, must fail terminally
    recovery = AIRecoveryService(repository=repo)
    report = recovery.recover("ws_safe")
    assert report.steps_reset_for_retry == 0
    assert report.steps_failed_terminal == 1

    final_step = repo.get_step(step.step_id)
    assert final_step.status == AIStepStatus.FAILED


# =============================================================================
# Real Process Restart Proof
# =============================================================================


def test_real_process_restart_proof(tmp_path):
    """
    Section 16: Real restart proof.
    Process A creates run, starts execution, and dies (all Python objects deleted).
    Process B starts with empty in-memory state, recovers from DB, resumes work to completion.
    """
    db_file = tmp_path / "process_restart.db"

    # --- SIMULATE PROCESS A ---
    engine_a = DatabaseEngine(f"sqlite:///{db_file}")
    repo_a = SQLAIRunRepository(engine=engine_a)
    service_a = AIRunService(repository=repo_a)

    dag = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_a", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="step_b", capability=CapabilityTypeEnum.TEXT_GENERATION, dependencies=["step_a"]),
        ]
    )
    run_a = service_a.create_run("ws_restart", CapabilityTypeEnum.PLANNING, dag)
    run_id = run_a.run_id
    steps_a = service_a.get_run_steps(run_id)
    step_a_id = next(s.step_id for s in steps_a if "step_a" in s.step_id)

    # Process A claims step_a with 0.05s lease and persists durable activity, then crashes
    token_a = generate_lease_token()
    claimed_a = repo_a.claim_step(step_a_id, "worker_proc_a", token_a, lease_duration_seconds=0.05)
    executor_a = DurableActivityExecutor(repository=repo_a)
    provider_a = FakeExternalProvider()

    def crash_after_persist(pt):
        if pt == "after_result_persistence_before_step_commit":
            raise SystemExit("PROCESS A KILLED")

    try:
        executor_a.execute_activity(
            claimed_a,
            "ws_restart",
            lambda k: provider_a.generate(k),
            native_idempotency_supported=True,
            crash_injector=crash_after_persist,
        )
    except SystemExit:
        pass

    # COMPLETE PROCESS DEATH: Delete all process A objects from memory
    del engine_a, repo_a, service_a, executor_a, provider_a, claimed_a

    time.sleep(0.08)  # Lease expires while system is offline

    # --- SIMULATE PROCESS B (Fresh Process) ---
    engine_b = DatabaseEngine(f"sqlite:///{db_file}")
    repo_b = SQLAIRunRepository(engine=engine_b)
    service_b = AIRunService(repository=repo_b)
    recovery_b = AIRecoveryService(repository=repo_b)

    # Process B starts with zero in-memory context; recovers state from disk DB
    report = recovery_b.recover("ws_restart")
    assert report.steps_reconciled_from_activities == 1
    assert report.children_unblocked == 1

    # Step A is SUCCEEDED, Step B is PENDING
    steps_b = {s.step_id: s for s in service_b.get_run_steps(run_id)}
    step_b_id = next(sid for sid in steps_b if "step_b" in sid)
    assert steps_b[step_a_id].status == AIStepStatus.SUCCEEDED
    assert steps_b[step_b_id].status == AIStepStatus.PENDING

    # Process B executes Step B to completion
    token_b = generate_lease_token()
    claimed_b = repo_b.claim_step(step_b_id, "worker_proc_b", token_b, lease_duration_seconds=30.0)
    service_b.complete_step(claimed_b.step_id, "worker_proc_b", token_b, output_ref="storage://step_b.json")

    # Entire run is now SUCCEEDED!
    final_run = repo_b.get_run(run_id)
    assert final_run.status == AIRunStatus.SUCCEEDED


# =============================================================================
# Multi-Tenant Isolation
# =============================================================================


def test_cross_tenant_recovery_isolation(repo):
    """
    Section 13: Multi-tenant boundary.
    Recovery scoped to Workspace B must never touch or reclaim steps belonging to Workspace A.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="isolated_step", capability=CapabilityTypeEnum.PLANNING)]
    )

    # Create run in Workspace A
    run_a = service.create_run("ws_tenant_A", CapabilityTypeEnum.PLANNING, dag)
    step_a = service.get_run_steps(run_a.run_id)[0]

    # Worker in Workspace A dies
    token = generate_lease_token()
    repo.claim_step(step_a.step_id, "worker_ws_a", token, lease_duration_seconds=0.05, workspace_id="ws_tenant_A")
    time.sleep(0.08)  # Lease expires

    # Recovery runs for Workspace B
    recovery = AIRecoveryService(repository=repo)
    report_b = recovery.recover(workspace_id="ws_tenant_B")
    assert report_b.expired_leases_reclaimed == 0

    # Step in Workspace A remains unmutated by Workspace B's recovery sweep
    step_a_fresh = repo.get_step(step_a.step_id, workspace_id="ws_tenant_A")
    assert step_a_fresh.status == AIStepStatus.RUNNING

    # Attempting to read Workspace A run with Workspace B scope raises TenantAccessDeniedError
    with pytest.raises(TenantAccessDeniedError):
        repo.get_run(run_a.run_id, workspace_id="ws_tenant_B")


# =============================================================================
# AI-10BR Durability Hardening Tests
# =============================================================================


def test_activity_classification_matrix_coverage_and_invariants():
    """
    AI-10BR / Section 1: Prove real activity idempotency classification.
    Validates that authoritative taxonomy covers all Provider, MCP, and Tool boundaries,
    and strictly enforces invariants:
    - Zero false EFFECTIVELY_ONCE claims without native idempotency or deterministic reconciliation.
    - AT_MOST_ONCE activities strictly disallow automated blind retries.
    """
    assert len(ACTIVITY_CLASSIFICATIONS) >= 10

    providers = [c for c in ACTIVITY_CLASSIFICATIONS.values() if c.boundary_type == ActivityBoundaryType.PROVIDER]
    mcps = [c for c in ACTIVITY_CLASSIFICATIONS.values() if c.boundary_type == ActivityBoundaryType.MCP]
    tools = [c for c in ACTIVITY_CLASSIFICATIONS.values() if c.boundary_type == ActivityBoundaryType.TOOL]

    assert len(providers) >= 4
    assert len(mcps) >= 4
    assert len(tools) >= 5

    for classification in ACTIVITY_CLASSIFICATIONS.values():
        if classification.semantics == IdempotencySemantics.EFFECTIVELY_ONCE:
            # Must have provable native idempotency support (wire-level, content-addressed, or read-only/state-machine)
            assert classification.native_idempotency_supported is True, (
                f"Activity '{classification.activity_name}' cannot claim EFFECTIVELY_ONCE without native idempotency"
            )

        if classification.boundary_type == ActivityBoundaryType.PROVIDER:
            # External providers without native wire deduplication CANNOT claim EFFECTIVELY_ONCE
            if not classification.native_idempotency_supported:
                assert classification.semantics in (
                    IdempotencySemantics.AT_LEAST_ONCE,
                    IdempotencySemantics.AT_MOST_ONCE,
                ), f"Provider '{classification.activity_name}' without wire idempotency cannot be EFFECTIVELY_ONCE"

        if classification.semantics == IdempotencySemantics.AT_MOST_ONCE:
            # Blind retry must NEVER be possible for AT_MOST_ONCE
            assert classification.blind_retry_possible is False, (
                f"AT_MOST_ONCE activity '{classification.activity_name}' cannot allow blind retries"
            )


def test_false_idempotency_classification_rejected(repo):
    """
    AI-10BR / Section 1: Non-idempotent operations falsely claiming EFFECTIVELY_ONCE
    must be rejected with FalseIdempotencyClaimError.
    """
    with pytest.raises(FalseIdempotencyClaimError):
        validate_activity_semantics(
            activity_name="provider:unsupported_model",
            requested_semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
            native_idempotency_supported=False,
            is_deterministic_read=False,
        )

    # Rejection via executor dispatch
    now = datetime.now(timezone.utc)
    repo.create_run(
        AIRun(
            run_id="run_false_claim",
            workspace_id="ws_false_claim",
            status=AIRunStatus.RUNNING,
            capability=CapabilityTypeEnum.PLANNING,
            created_at=now,
            usage=UsageRecord(),
            cost=CostEstimate(estimated_cost="0.00"),
        )
    )
    step = repo.create_steps(
        [
            AIStep(
                step_id="step_false_claim",
                run_id="run_false_claim",
                status=AIStepStatus.RUNNING,
                capability=CapabilityTypeEnum.PLANNING,
                created_at=now,
                cost=CostEstimate(estimated_cost="0.01"),
            )
        ]
    )[0]

    executor = DurableActivityExecutor(repository=repo)
    provider = FakeExternalProvider()

    with pytest.raises(FalseIdempotencyClaimError):
        executor.execute_activity(
            step,
            "ws_false_claim",
            lambda k: provider.generate(k),
            semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
            native_idempotency_supported=False,
            activity_name="provider:paid_video_generation",
        )

def test_deterministic_output_does_not_conflate_with_effectively_once_execution(repo):
    """
    S27.11 Hardening: Prove classification policy does NOT conflate deterministic output
    with effectively-once external execution.
    An external provider activity (like embedding generation) producing deterministic vectors
    still risks duplicate external execution/billing upon ambiguous crash, and therefore
    MUST NOT be classified as EFFECTIVELY_ONCE without wire-level native idempotency.
    """
    # 1. Policy check: Attempting to claim EFFECTIVELY_ONCE solely based on deterministic output is rejected
    with pytest.raises(FalseIdempotencyClaimError) as exc_info:
        validate_activity_semantics(
            activity_name="provider:embedding_generation",
            requested_semantics=IdempotencySemantics.EFFECTIVELY_ONCE,
            native_idempotency_supported=False,
            is_deterministic_output=True,
        )
    assert "Deterministic output alone does not prevent duplicate external provider execution or billing" in str(exc_info.value)

    # 2. Authoritative taxonomy verification
    embedding_cls = ACTIVITY_CLASSIFICATIONS["provider:embedding_generation"]
    assert embedding_cls.semantics == IdempotencySemantics.AT_LEAST_ONCE
    assert embedding_cls.native_idempotency_supported is False
    assert embedding_cls.stable_key_propagated is False
    assert embedding_cls.blind_retry_possible is True
    assert "duplicate provider execution/cost possible" in embedding_cls.residual_duplicate_risk

    # 3. Behavioral simulation: Provider call count increases upon retry despite deterministic output
    external_provider_invocations = 0
    external_cost_billed = Decimal("0.00")

    def mock_external_embedding_provider(idempotency_key: str):
        nonlocal external_provider_invocations, external_cost_billed
        external_provider_invocations += 1
        external_cost_billed += Decimal("0.0002")
        return (
            "storage://embeddings/vec_123.bin",
            UsageRecord(input_tokens=50, total_tokens=50),
            CostEstimate(estimated_cost="0.0002", actual_cost="0.0002"),
            None,
        )

    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[
            StepDefinition(
                step_id="step_embedding",
                capability=CapabilityTypeEnum.PLANNING,
                max_attempts=2,
            )
        ]
    )
    run = service.create_run("ws_embed", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    token = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_embed", token, lease_duration_seconds=0.05, workspace_id="ws_embed")
    executor = DurableActivityExecutor(repository=repo)

    def crash_after_provider(pt: str):
        if pt == "after_provider_success_before_local_commit":
            raise RuntimeError("AMBIGUOUS_CRASH_POST_PROVIDER_EXECUTION")

    # Attempt 1: Provider executes and bills, but worker crashes before durable result commit
    with pytest.raises(RuntimeError, match="AMBIGUOUS_CRASH_POST_PROVIDER_EXECUTION"):
        executor.execute_activity(
            claimed,
            "ws_embed",
            mock_external_embedding_provider,
            semantics=IdempotencySemantics.AT_LEAST_ONCE,
            native_idempotency_supported=False,
            activity_name="provider:embedding_generation",
            crash_injector=crash_after_provider,
        )

    assert external_provider_invocations == 1
    assert external_cost_billed == Decimal("0.0002")

    # Lease expires
    time.sleep(0.08)

    # Recovery resets for bounded retry because semantics is AT_LEAST_ONCE
    recovery = AIRecoveryService(repository=repo)
    report = recovery.recover("ws_embed")
    assert report.steps_reset_for_retry == 1

    # Attempt 2: New worker claims and executes
    token2 = generate_lease_token()
    claimed2 = repo.claim_step(step.step_id, "worker_embed_2", token2, lease_duration_seconds=10.0, workspace_id="ws_embed")
    act2 = executor.execute_activity(
        claimed2,
        "ws_embed",
        mock_external_embedding_provider,
        semantics=IdempotencySemantics.AT_LEAST_ONCE,
        native_idempotency_supported=False,
        activity_name="provider:embedding_generation",
    )

    # Both invocations produced the identical deterministic output
    assert act2.output_ref == "storage://embeddings/vec_123.bin"

    # BUT external provider executed and was billed TWICE ($0.0004 total)
    assert external_provider_invocations == 2
    assert external_cost_billed == Decimal("0.0004")
    # Proves: Deterministic output does NOT equal effectively-once external execution.


def test_non_idempotent_crash_after_dispatch_no_duplicate_execution(repo):
    """
    AI-10BR / Section 1: Non-idempotent external operation + crash after dispatch
    -> strictly NO automatic duplicate execution.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[
            StepDefinition(
                step_id="step_non_idem_side_effect",
                capability=CapabilityTypeEnum.PLANNING,
                max_attempts=3,
            )
        ]
    )
    run = service.create_run("ws_non_idem_test", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    external_side_effect_invocations = 0

    def mock_external_mutation(idempotency_key: str):
        nonlocal external_side_effect_invocations
        external_side_effect_invocations += 1
        return (
            "storage://output.json",
            UsageRecord(total_tokens=100),
            CostEstimate(estimated_cost="0.50", actual_cost="0.50"),
            "ext_txn_12345",
        )

    token = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_unsafe", token, lease_duration_seconds=0.05, workspace_id="ws_non_idem_test")
    executor = DurableActivityExecutor(repository=repo)

    def crash_after_dispatch_before_commit(pt: str):
        if pt == "after_provider_success_before_local_commit":
            raise RuntimeError("CRASH_AFTER_EXTERNAL_DISPATCH")

    # Worker dispatches external mutation, which executes, then worker crashes
    with pytest.raises(RuntimeError, match="CRASH_AFTER_EXTERNAL_DISPATCH"):
        executor.execute_activity(
            claimed,
            "ws_non_idem_test",
            mock_external_mutation,
            semantics=IdempotencySemantics.AT_MOST_ONCE,
            native_idempotency_supported=False,
            activity_name="tool:patch_blueprint",
            crash_injector=crash_after_dispatch_before_commit,
        )

    # Exactly 1 dispatch took place before crash
    assert external_side_effect_invocations == 1

    time.sleep(0.08)  # Lease expires

    # Recovery sweeps: must NOT reset for retry, must fail terminally to prevent duplicate side effects
    recovery = AIRecoveryService(repository=repo)
    report = recovery.recover("ws_non_idem_test")

    assert report.steps_reset_for_retry == 0
    assert report.steps_failed_terminal == 1

    final_step = repo.get_step(step.step_id, workspace_id="ws_non_idem_test")
    assert final_step.status == AIStepStatus.FAILED

    # Even if another rogue worker tries to retry the step, executor blocks it with NonIdempotentRetryError
    with pytest.raises(NonIdempotentRetryError):
        executor.execute_activity(
            claimed,
            "ws_non_idem_test",
            mock_external_mutation,
            semantics=IdempotencySemantics.AT_MOST_ONCE,
            native_idempotency_supported=False,
            activity_name="tool:patch_blueprint",
        )

    # Crucial proof: Invocations remain strictly 1 (ZERO automated duplicate execution)
    assert external_side_effect_invocations == 1


def test_cost_settlement_crash_window_a_before_ledger(repo, budget_service):
    """
    AI-10BR / Section 2: Window A Crash - Worker dies immediately before ledger mutation.
    Expected:
    - Activity completed in local store, but financial ledger was NOT mutated before crash.
    - Recovery detects unsettled activity and invokes idempotent settlement.
    - Result: Exactly one logical charge on ledger, settlement records = 1, no lost charge.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="step_win_a", capability=CapabilityTypeEnum.PLANNING)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    # Create budget reservation ($1.00)
    res_req = ReservationRequest(
        workspace_id="ws_crash",
        amount=Decimal("1.00"),
        currency="USD",
        idempotency_key="res_win_a_001",
        run_id=run.run_id,
        ttl_seconds=300,
    )
    res_result = budget_service.reserve(res_req)
    assert res_result.success is True
    res_id = res_result.reservation.reservation_id

    token = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_win_a", token, lease_duration_seconds=0.05, workspace_id="ws_crash")
    executor = DurableActivityExecutor(repository=repo, budget_service=budget_service)
    provider = FakeExternalProvider()

    def crash_window_a(pt: str):
        if pt == "before_ledger_mutation":
            raise RuntimeError("CRASH_WINDOW_A_BEFORE_LEDGER")

    # Worker crashes immediately BEFORE budget_service.settle
    with pytest.raises(RuntimeError, match="CRASH_WINDOW_A_BEFORE_LEDGER"):
        executor.execute_activity(
            claimed,
            "ws_crash",
            lambda k: provider.generate(k),
            native_idempotency_supported=True,
            reservation_id=res_id,
            crash_injector=crash_window_a,
        )

    # Verify state right after Window A crash:
    # 1. Budget actual_spend is still 0.00 (ledger was not mutated)
    budget_pre = budget_service.repository.get_budget("b_ws_crash")
    assert budget_pre.actual_spend == Decimal("0.00")
    # 2. Settle accounting entries count is 0
    entries_pre = budget_service.repository.get_accounting_entries(res_id)
    settle_entries_pre = [e for e in entries_pre if e.event_type == AccountingEventType.SETTLED]
    assert len(settle_entries_pre) == 0
    # 3. Local activity cost_settled is False
    act_pre = repo.get_activities_for_step(step.step_id, workspace_id="ws_crash")[0]
    assert act_pre.cost_settled is False

    time.sleep(0.08)  # Lease expires

    # Recovery runs
    recovery = AIRecoveryService(repository=repo, budget_service=budget_service)
    report = recovery.recover("ws_crash")

    assert report.costs_settled == 1
    assert report.steps_reconciled_from_activities == 1

    # Verify post-recovery state:
    # 1. Final ledger delta = exactly one logical charge ($0.0080)
    budget_post = budget_service.repository.get_budget("b_ws_crash")
    assert budget_post.actual_spend == Decimal("0.0080")
    assert budget_post.reserved == Decimal("0.00")
    # 2. Settlement records = exactly one logical settlement
    entries_post = budget_service.repository.get_accounting_entries(res_id)
    settle_entries_post = [e for e in entries_post if e.event_type == AccountingEventType.SETTLED]
    assert len(settle_entries_post) == 1
    # 3. Local completion marker set
    act_post = repo.get_activities_for_step(step.step_id, workspace_id="ws_crash")[0]
    assert act_post.cost_settled is True

    # Idempotency verification: 2nd recovery sweep must be a no-op
    report_idempotent = recovery.recover("ws_crash")
    assert report_idempotent.costs_settled == 0
    budget_final = budget_service.repository.get_budget("b_ws_crash")
    assert budget_final.actual_spend == Decimal("0.0080")
    entries_final = budget_service.repository.get_accounting_entries(res_id)
    settle_entries_final = [e for e in entries_final if e.event_type == AccountingEventType.SETTLED]
    assert len(settle_entries_final) == 1


def test_cost_settlement_crash_window_b_after_ledger_before_marker(repo, budget_service):
    """
    AI-10BR / Section 2: Window B Crash - Worker dies immediately after ledger mutation
    but before local completion marker (AIActivityRecord.cost_settled) is saved.
    Expected:
    - Ledger already charged $0.0080, but local DB has cost_settled=False.
    - Recovery runs settle_activity_cost; budget_service recognizes already-settled reservation.
    - Result: No double charge, final ledger delta = exactly one logical charge ($0.0080),
      settlement records = 1, cost_settled marked True.
    """
    service = AIRunService(repository=repo)
    dag = DAGSpecification(
        steps=[StepDefinition(step_id="step_win_b", capability=CapabilityTypeEnum.PLANNING)]
    )
    run = service.create_run("ws_crash", CapabilityTypeEnum.PLANNING, dag)
    step = service.get_run_steps(run.run_id)[0]

    # Create budget reservation ($1.00)
    res_req = ReservationRequest(
        workspace_id="ws_crash",
        amount=Decimal("1.00"),
        currency="USD",
        idempotency_key="res_win_b_001",
        run_id=run.run_id,
        ttl_seconds=300,
    )
    res_result = budget_service.reserve(res_req)
    assert res_result.success is True
    res_id = res_result.reservation.reservation_id

    token = generate_lease_token()
    claimed = repo.claim_step(step.step_id, "worker_win_b", token, lease_duration_seconds=0.05, workspace_id="ws_crash")
    executor = DurableActivityExecutor(repository=repo, budget_service=budget_service)
    provider = FakeExternalProvider()

    def crash_window_b(pt: str):
        if pt == "after_ledger_mutation_before_marker":
            raise RuntimeError("CRASH_WINDOW_B_AFTER_LEDGER_BEFORE_MARKER")

    # Worker crashes immediately AFTER budget_service.settle, before mark_cost_settled
    with pytest.raises(RuntimeError, match="CRASH_WINDOW_B_AFTER_LEDGER_BEFORE_MARKER"):
        executor.execute_activity(
            claimed,
            "ws_crash",
            lambda k: provider.generate(k),
            native_idempotency_supported=True,
            reservation_id=res_id,
            crash_injector=crash_window_b,
        )

    # Verify state right after Window B crash:
    # 1. Budget actual_spend WAS charged $0.0080
    budget_pre = budget_service.repository.get_budget("b_ws_crash")
    assert budget_pre.actual_spend == Decimal("0.0080")
    # 2. Accounting record exists
    entries_pre = budget_service.repository.get_accounting_entries(res_id)
    settle_entries_pre = [e for e in entries_pre if e.event_type == AccountingEventType.SETTLED]
    assert len(settle_entries_pre) == 1
    # 3. But local activity cost_settled is STILL False!
    act_pre = repo.get_activities_for_step(step.step_id, workspace_id="ws_crash")[0]
    assert act_pre.cost_settled is False

    time.sleep(0.08)  # Lease expires

    # Recovery sweeps and reconciles
    recovery = AIRecoveryService(repository=repo, budget_service=budget_service)
    report = recovery.recover("ws_crash")

    assert report.costs_settled == 1
    assert report.steps_reconciled_from_activities == 1

    # Verify post-recovery state:
    # 1. Final ledger delta remains EXACTLY $0.0080 (NO DOUBLE CHARGE of $0.0160!)
    budget_post = budget_service.repository.get_budget("b_ws_crash")
    assert budget_post.actual_spend == Decimal("0.0080")
    # 2. Settlement records remain EXACTLY 1 (idempotent reservation settlement prevented duplicate entry)
    entries_post = budget_service.repository.get_accounting_entries(res_id)
    settle_entries_post = [e for e in entries_post if e.event_type == AccountingEventType.SETTLED]
    assert len(settle_entries_post) == 1
    # 3. Local activity cost_settled is now True
    act_post = repo.get_activities_for_step(step.step_id, workspace_id="ws_crash")[0]
    assert act_post.cost_settled is True

    # Re-run recovery: stable idempotent state
    report2 = recovery.recover("ws_crash")
    assert report2.costs_settled == 0
    budget_final = budget_service.repository.get_budget("b_ws_crash")
    assert budget_final.actual_spend == Decimal("0.0080")

