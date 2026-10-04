"""
tests/ai/orchestration/test_worker_claims_and_leases.py
========================================================
Concurrency, atomic worker claims, and stale worker fencing tests (S27.11).

Invariants verified:
- 10 concurrent workers racing to claim 1 step: exactly ONE winner, 9 receive None.
- While a lease is active, other workers cannot claim the step.
- Heartbeats extend lease duration and prevent reclamation.
- Expired leases are atomically reclaimable by fresh workers.
- Stale workers (whose leases expired or were superseded) are strictly fenced from committing results.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import pytest
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIRun, AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.errors import StaleWorkerLeaseError
from ai.orchestration.lease import generate_lease_token
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_claims.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    return SQLAIRunRepository(engine=engine)


def test_atomic_claim_10_worker_race(repo):
    """
    Simulates 10 workers concurrently racing to claim a single PENDING step.
    Exactly ONE worker must win; the remaining 9 must return None.
    """
    now = datetime.now(timezone.utc)
    run = AIRun(
        run_id="run_race_001",
        workspace_id="ws_alpha",
        status=AIRunStatus.PENDING,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.00"),
    )
    repo.create_run(run)

    step = AIStep(
        step_id="step_race_01",
        run_id="run_race_001",
        status=AIStepStatus.PENDING,
        attempt=1,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        cost=CostEstimate(estimated_cost="0.01"),
    )
    repo.create_steps([step])

    worker_ids = [f"worker_{i:02d}" for i in range(10)]
    results = {}

    def try_claim(w_id: str):
        token = generate_lease_token()
        claimed = repo.claim_step(
            step_id="step_race_01",
            worker_id=w_id,
            lease_token=token,
            lease_duration_seconds=30.0,
            workspace_id="ws_alpha",
        )
        return w_id, claimed

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(try_claim, wid) for wid in worker_ids]
        for f in futures:
            w_id, claimed = f.result()
            results[w_id] = claimed

    winners = [w for w, step in results.items() if step is not None]
    losers = [w for w, step in results.items() if step is None]

    # Exactly 1 winner and 9 losers
    assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}: {winners}"
    assert len(losers) == 9

    winning_worker = winners[0]
    final_step = repo.get_step("step_race_01")
    assert final_step.status == AIStepStatus.RUNNING
    assert final_step.worker_id == winning_worker


def test_active_lease_prevents_theft(repo):
    now = datetime.now(timezone.utc)
    run = AIRun(
        run_id="run_steal_001",
        workspace_id="ws_alpha",
        status=AIRunStatus.PENDING,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.00"),
    )
    repo.create_run(run)

    step = AIStep(
        step_id="step_steal_01",
        run_id="run_steal_001",
        status=AIStepStatus.PENDING,
        attempt=1,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        cost=CostEstimate(estimated_cost="0.01"),
    )
    repo.create_steps([step])

    # Worker A claims with 60 second lease
    token_a = generate_lease_token()
    claimed_a = repo.claim_step(
        step_id="step_steal_01",
        worker_id="worker_A",
        lease_token=token_a,
        lease_duration_seconds=60.0,
    )
    assert claimed_a is not None

    # Worker B tries to claim while lease is active
    token_b = generate_lease_token()
    claimed_b = repo.claim_step(
        step_id="step_steal_01",
        worker_id="worker_B",
        lease_token=token_b,
        lease_duration_seconds=60.0,
    )
    assert claimed_b is None, "Worker B should not be able to steal an active lease"


def test_heartbeat_extends_lease(repo):
    now = datetime.now(timezone.utc)
    run = AIRun(
        run_id="run_hb_001",
        workspace_id="ws_alpha",
        status=AIRunStatus.PENDING,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.00"),
    )
    repo.create_run(run)

    step = AIStep(
        step_id="step_hb_01",
        run_id="run_hb_001",
        status=AIStepStatus.PENDING,
        attempt=1,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        cost=CostEstimate(estimated_cost="0.01"),
    )
    repo.create_steps([step])

    token_a = generate_lease_token()
    repo.claim_step("step_hb_01", "worker_A", token_a, lease_duration_seconds=10.0)

    # Renew lease via heartbeat
    renewed = repo.renew_lease("step_hb_01", "worker_A", token_a, lease_duration_seconds=30.0)
    assert renewed is True

    # Attempt heartbeat with wrong token -> fails
    wrong_token = generate_lease_token()
    renewed_wrong = repo.renew_lease("step_hb_01", "worker_A", wrong_token, lease_duration_seconds=30.0)
    assert renewed_wrong is False


def test_stale_worker_fencing(tmp_path):
    """
    Scenario:
    1. Worker A claims with a short 0.1s lease.
    2. Lease expires.
    3. Worker B claims the expired step.
    4. Worker A wakes up and attempts to commit (complete_step).
    Expected: Worker A's commit is REJECTED with StaleWorkerLeaseError!
    """
    import time

    db_file = tmp_path / "fence.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAIRunRepository(engine=engine)
    now = datetime.now(timezone.utc)

    run = AIRun(
        run_id="run_fence_001",
        workspace_id="ws_alpha",
        status=AIRunStatus.PENDING,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.00"),
    )
    repo.create_run(run)

    step = AIStep(
        step_id="step_fence_01",
        run_id="run_fence_001",
        status=AIStepStatus.PENDING,
        attempt=1,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        cost=CostEstimate(estimated_cost="0.01"),
    )
    repo.create_steps([step])

    # 1. Worker A claims with 0.1s lease
    token_a = generate_lease_token()
    claimed_a = repo.claim_step("step_fence_01", "worker_A", token_a, lease_duration_seconds=0.1)
    assert claimed_a is not None

    # 2. Wait for lease to expire
    time.sleep(0.15)

    # 3. Worker B claims the expired step
    token_b = generate_lease_token()
    claimed_b = repo.claim_step("step_fence_01", "worker_B", token_b, lease_duration_seconds=30.0)
    assert claimed_b is not None
    assert claimed_b.worker_id == "worker_B"

    # 4. Worker A wakes up and tries to complete_step
    with pytest.raises(StaleWorkerLeaseError) as exc_info:
        repo.complete_step(
            step_id="step_fence_01",
            worker_id="worker_A",
            lease_token=token_a,
            output_ref="storage://out_a.json",
            usage=UsageRecord(),
            cost=CostEstimate(estimated_cost="0.01"),
        )
    assert "Stale worker commit rejected" in str(exc_info.value)

    # 5. Worker B successfully commits
    completed_b = repo.complete_step(
        step_id="step_fence_01",
        worker_id="worker_B",
        lease_token=token_b,
        output_ref="storage://out_b.json",
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.01"),
    )
    assert completed_b.status == AIStepStatus.SUCCEEDED
    assert completed_b.output_ref == "storage://out_b.json"


def test_ai_durable_worker_e2e_execution(tmp_path):
    from ai.orchestration.dag import DAGSpecification, StepDefinition
    from ai.orchestration.service import AIRunService
    from ai.orchestration.worker import AIDurableWorker

    db_file = tmp_path / "worker_e2e.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAIRunRepository(engine=engine)
    service = AIRunService(repository=repo)

    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="w_step", capability=CapabilityTypeEnum.PLANNING),
        ]
    )
    service.create_run(workspace_id="ws_worker", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    worker = AIDurableWorker(
        worker_id="worker_live_1",
        service=service,
        workspace_id="ws_worker",
        lease_duration_seconds=10.0,
        heartbeat_interval_seconds=0.05,
    )

    def mock_handler(step):
        # Emulate work
        return "storage://worker_result.json", UsageRecord(total_tokens=42), CostEstimate(estimated_cost="0.00", actual_cost="0.005")

    processed = worker.process_one(mock_handler)
    assert processed is not None
    assert processed.status == AIStepStatus.SUCCEEDED
    assert processed.output_ref == "storage://worker_result.json"

    # Next attempt has no runnable steps
    assert worker.process_one(mock_handler) is None

    worker.stop()

