"""
tests/ai/orchestration/test_dag_execution_and_dependencies.py
==============================================================
Integration tests for DAG execution, parallel fan-out/fan-in, and dependency scheduling (S27.11).

Invariants verified:
- Root steps begin in PENDING; dependent steps begin in WAITING.
- Parallel children become runnable concurrently upon parent completion.
- Fan-in step (E depending on B, C, D) transitions to PENDING exactly once only after
  ALL prerequisite parents have reached SUCCEEDED.
- Run automatically transitions to SUCCEEDED when all DAG steps complete.
"""

from concurrent.futures import ThreadPoolExecutor
import pytest
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIRunStatus, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.service import AIRunService
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def service(tmp_path):
    db_file = tmp_path / "test_dag_exec.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAIRunRepository(engine=engine)
    return AIRunService(repository=repo)


def test_diamond_dag_execution_and_aggregation(service):
    r"""
    Workflow:
          A
        / | \
       B  C  D
        \ | /
          E
    """
    dag_spec = DAGSpecification(
        workflow_ref="recipes/video_generation.json",
        steps=[
            StepDefinition(step_id="A", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="B", capability=CapabilityTypeEnum.VOICE_ANALYSIS, dependencies=["A"]),
            StepDefinition(step_id="C", capability=CapabilityTypeEnum.SHOT_DETECTION, dependencies=["A"]),
            StepDefinition(step_id="D", capability=CapabilityTypeEnum.AUDIO_ENHANCE, dependencies=["A"]),
            StepDefinition(
                step_id="E",
                capability=CapabilityTypeEnum.VIDEO_UNDERSTANDING,
                dependencies=["B", "C", "D"],
            ),
        ],
    )

    run = service.create_run(
        workspace_id="ws_dag",
        capability=CapabilityTypeEnum.PLANNING,
        dag_spec=dag_spec,
    )

    steps = service.get_run_steps(run.run_id)
    step_map = {s.step_id.split("_")[-1]: s for s in steps}

    # Verify initial states
    assert step_map["A"].status == AIStepStatus.PENDING
    assert step_map["B"].status == AIStepStatus.WAITING
    assert step_map["C"].status == AIStepStatus.WAITING
    assert step_map["D"].status == AIStepStatus.WAITING
    assert step_map["E"].status == AIStepStatus.WAITING

    # 1. Claim and execute A
    claimed_a = service.claim_next_runnable_step(worker_id="worker_1", workspace_id="ws_dag")
    assert claimed_a is not None
    assert claimed_a.step_id.endswith("_A")

    service.complete_step(
        step_id=claimed_a.step_id,
        worker_id="worker_1",
        lease_token=claimed_a.lease_token,
        output_ref="storage://a.json",
        usage=UsageRecord(input_tokens=100, output_tokens=50, total_tokens=150),
        cost=CostEstimate(estimated_cost="0.00", actual_cost="0.01"),
    )

    # Now B, C, D must have transitioned to PENDING
    steps = service.get_run_steps(run.run_id)
    step_map = {s.step_id.split("_")[-1]: s for s in steps}
    assert step_map["B"].status == AIStepStatus.PENDING
    assert step_map["C"].status == AIStepStatus.PENDING
    assert step_map["D"].status == AIStepStatus.PENDING
    assert step_map["E"].status == AIStepStatus.WAITING

    # 2. Claim and execute B, C
    claimed_b = service.claim_next_runnable_step(worker_id="worker_2", workspace_id="ws_dag")
    service.complete_step(
        step_id=claimed_b.step_id,
        worker_id="worker_2",
        lease_token=claimed_b.lease_token,
        output_ref="storage://b.json",
        usage=UsageRecord(input_tokens=200, total_tokens=200),
        cost=CostEstimate(estimated_cost="0.00", actual_cost="0.02"),
    )

    claimed_c = service.claim_next_runnable_step(worker_id="worker_3", workspace_id="ws_dag")
    service.complete_step(
        step_id=claimed_c.step_id,
        worker_id="worker_3",
        lease_token=claimed_c.lease_token,
        output_ref="storage://c.json",
        usage=UsageRecord(input_tokens=300, total_tokens=300),
        cost=CostEstimate(estimated_cost="0.00", actual_cost="0.03"),
    )

    # E should still be WAITING (waiting for D)
    steps = service.get_run_steps(run.run_id)
    step_map = {s.step_id.split("_")[-1]: s for s in steps}
    assert step_map["E"].status == AIStepStatus.WAITING

    # 3. Claim and execute D
    claimed_d = service.claim_next_runnable_step(worker_id="worker_4", workspace_id="ws_dag")
    service.complete_step(
        step_id=claimed_d.step_id,
        worker_id="worker_4",
        lease_token=claimed_d.lease_token,
        output_ref="storage://d.json",
        usage=UsageRecord(input_tokens=400, total_tokens=400),
        cost=CostEstimate(estimated_cost="0.00", actual_cost="0.04"),
    )

    # Now E must have transitioned to PENDING (exactly once)
    steps = service.get_run_steps(run.run_id)
    step_map = {s.step_id.split("_")[-1]: s for s in steps}
    assert step_map["E"].status == AIStepStatus.PENDING

    # 4. Claim and execute E
    claimed_e = service.claim_next_runnable_step(worker_id="worker_5", workspace_id="ws_dag")
    service.complete_step(
        step_id=claimed_e.step_id,
        worker_id="worker_5",
        lease_token=claimed_e.lease_token,
        output_ref="storage://e.json",
        usage=UsageRecord(input_tokens=500, total_tokens=500),
        cost=CostEstimate(estimated_cost="0.00", actual_cost="0.05"),
    )

    # Parent AIRun must now be SUCCEEDED with aggregated cost and usage
    final_run = service.get_run(run.run_id, workspace_id="ws_dag")
    assert final_run.status == AIRunStatus.SUCCEEDED
    assert final_run.completed_at is not None
    # 150 + 200 + 300 + 400 + 500 = 1550 tokens
    assert final_run.usage.total_tokens == 1550
    # 0.01 + 0.02 + 0.03 + 0.04 + 0.05 = 0.1500
    assert float(final_run.cost.actual_cost) == pytest.approx(0.15, abs=1e-3)


def test_simultaneous_parent_completion(service):
    """
    Tests that when parallel parents complete concurrently, the child E
    transitions to PENDING cleanly without error or duplicate state.
    """
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="P1", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="P2", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="C", capability=CapabilityTypeEnum.VOICE_ANALYSIS, dependencies=["P1", "P2"]),
        ]
    )

    run = service.create_run(workspace_id="ws_simul", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # Claim P1 and P2
    claimed_p1 = service.claim_next_runnable_step("w1", "ws_simul")
    claimed_p2 = service.claim_next_runnable_step("w2", "ws_simul")
    assert claimed_p1 is not None and claimed_p2 is not None

    def finish_p1():
        service.complete_step(claimed_p1.step_id, "w1", claimed_p1.lease_token)

    def finish_p2():
        service.complete_step(claimed_p2.step_id, "w2", claimed_p2.lease_token)

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(finish_p1)
        f2 = executor.submit(finish_p2)
        f1.result()
        f2.result()

    steps = service.get_run_steps(run.run_id)
    step_map = {s.step_id.split("_")[-1]: s for s in steps}
    assert step_map["C"].status == AIStepStatus.PENDING
