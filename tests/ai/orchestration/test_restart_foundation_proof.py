"""
tests/ai/orchestration/test_restart_foundation_proof.py
========================================================
Integration test proving durable crash and restart recovery without shared memory (S27.11).

Invariants verified:
- Instance A creates a durable run and steps in the physical database and executes step 1.
- Instance A is completely discarded and garbage collected (no shared memory objects).
- Instance B (a brand new DatabaseEngine, SQLAIRunRepository, and AIRunService instance)
  loads the persistent state from disk.
- Execution seamlessly resumes from disk persistence: Instance B claims step 2 and completes the run.
"""

from datetime import datetime, timezone
import pytest
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIRunStatus, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.service import AIRunService
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine


def test_restart_resumes_workflow_without_shared_memory(tmp_path):
    db_path = tmp_path / "restart_proof.db"
    db_url = f"sqlite:///{db_path}"

    # =========================================================================
    # Phase 1: Instance A creates run and executes first step
    # =========================================================================
    engine_a = DatabaseEngine(db_url)
    repo_a = SQLAIRunRepository(engine=engine_a)
    service_a = AIRunService(repository=repo_a)

    dag_spec = DAGSpecification(
        workflow_ref="recipe_restart_proof",
        steps=[
            StepDefinition(step_id="step1", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="step2", capability=CapabilityTypeEnum.VOICE_ANALYSIS, dependencies=["step1"]),
        ],
    )

    run_a = service_a.create_run(
        workspace_id="ws_restart",
        capability=CapabilityTypeEnum.PLANNING,
        dag_spec=dag_spec,
    )
    run_id = run_a.run_id

    # Instance A claims step 1 and completes it
    claimed_step1 = service_a.claim_next_runnable_step(worker_id="worker_A", workspace_id="ws_restart")
    assert claimed_step1 is not None
    assert claimed_step1.step_id.endswith("_step1")

    service_a.complete_step(
        step_id=claimed_step1.step_id,
        worker_id="worker_A",
        lease_token=claimed_step1.lease_token,
        output_ref="storage://step1_plan.json",
        usage=UsageRecord(input_tokens=100, output_tokens=50, total_tokens=150),
        cost=CostEstimate(estimated_cost="0.00", actual_cost="0.01"),
    )

    # Verify step 2 is now PENDING in Instance A
    steps_a = service_a.get_run_steps(run_id, workspace_id="ws_restart")
    step2_a = next(s for s in steps_a if s.step_id.endswith("_step2"))
    assert step2_a.status == AIStepStatus.PENDING

    # =========================================================================
    # Phase 2: Complete death of Instance A (zero in-memory state shared)
    # =========================================================================
    del service_a
    del repo_a
    del engine_a

    # =========================================================================
    # Phase 3: Fresh Instance B boots up from persistent database file
    # =========================================================================
    engine_b = DatabaseEngine(db_url)
    repo_b = SQLAIRunRepository(engine=engine_b)
    service_b = AIRunService(repository=repo_b)

    # 1. Instance B inspects persistent run
    recovered_run = service_b.get_run(run_id, workspace_id="ws_restart")
    assert recovered_run is not None
    assert recovered_run.run_id == run_id
    assert recovered_run.status == AIRunStatus.RUNNING

    # 2. Instance B inspects persistent steps
    recovered_steps = service_b.get_run_steps(run_id, workspace_id="ws_restart")
    rec_step1 = next(s for s in recovered_steps if s.step_id.endswith("_step1"))
    rec_step2 = next(s for s in recovered_steps if s.step_id.endswith("_step2"))

    assert rec_step1.status == AIStepStatus.SUCCEEDED
    assert rec_step1.output_ref == "storage://step1_plan.json"
    assert rec_step2.status == AIStepStatus.PENDING

    # 3. Instance B's worker claims step 2 and completes it
    claimed_step2 = service_b.claim_next_runnable_step(worker_id="worker_B", workspace_id="ws_restart")
    assert claimed_step2 is not None
    assert claimed_step2.step_id == rec_step2.step_id

    service_b.complete_step(
        step_id=claimed_step2.step_id,
        worker_id="worker_B",
        lease_token=claimed_step2.lease_token,
        output_ref="storage://step2_audio.mp3",
        usage=UsageRecord(input_tokens=200, output_tokens=100, total_tokens=300),
        cost=CostEstimate(estimated_cost="0.00", actual_cost="0.02"),
    )

    # 4. Final verification: Run is SUCCEEDED across independent processes
    final_run = service_b.get_run(run_id, workspace_id="ws_restart")
    assert final_run.status == AIRunStatus.SUCCEEDED
    assert final_run.completed_at is not None
    assert final_run.usage.total_tokens == 450
    assert float(final_run.cost.actual_cost) == pytest.approx(0.03, abs=1e-3)
