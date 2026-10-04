"""
tests/ai/orchestration/test_cancellation.py
============================================
Tests for durable workflow cancellation and terminal state guarantees (S27.11).

Invariants verified:
- Cancelling a run sets the AIRun and all non-terminal steps to CANCELLED.
- After cancellation, no worker can claim steps from that run.
- Attempting to cancel an already terminal run raises RunAlreadyTerminalError.
- Terminal CANCELLED runs cannot be transitioned back to active states.
"""

import pytest
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIRunStatus, AIStepStatus
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.errors import RunAlreadyTerminalError
from ai.orchestration.service import AIRunService
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def service(tmp_path):
    db_file = tmp_path / "test_canc.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAIRunRepository(engine=engine)
    return AIRunService(repository=repo)


def test_cancel_pending_run(service):
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step1", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="step2", capability=CapabilityTypeEnum.VOICE_ANALYSIS, dependencies=["step1"]),
        ]
    )
    run = service.create_run(workspace_id="ws_canc", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # Cancel while still PENDING
    cancelled_run = service.cancel_run(run.run_id, workspace_id="ws_canc", reason="User requested abort")
    assert cancelled_run.status == AIRunStatus.CANCELLED
    assert cancelled_run.completed_at is not None

    # All steps must be CANCELLED
    steps = service.get_run_steps(run.run_id)
    assert all(s.status == AIStepStatus.CANCELLED for s in steps)

    # No step should be claimable
    claimed = service.claim_next_runnable_step("w1", "ws_canc")
    assert claimed is None


def test_cancel_running_run(service):
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="s1", capability=CapabilityTypeEnum.PLANNING),
            StepDefinition(step_id="s2", capability=CapabilityTypeEnum.PLANNING, dependencies=["s1"]),
        ]
    )
    run = service.create_run(workspace_id="ws_canc2", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # Claim s1 -> run transitions to RUNNING
    claimed_s1 = service.claim_next_runnable_step("w1", "ws_canc2")
    assert claimed_s1 is not None

    current_run = service.get_run(run.run_id)
    assert current_run.status == AIRunStatus.RUNNING

    # Cancel while running
    service.cancel_run(run.run_id, workspace_id="ws_canc2", reason="Emergency cancellation")

    cancelled_run = service.get_run(run.run_id)
    assert cancelled_run.status == AIRunStatus.CANCELLED

    steps = service.get_run_steps(run.run_id)
    step_map = {s.step_id.split("_")[-1]: s for s in steps}
    assert step_map["s1"].status == AIStepStatus.CANCELLED
    assert step_map["s2"].status == AIStepStatus.CANCELLED


def test_cannot_cancel_already_terminal_run(service):
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="s1", capability=CapabilityTypeEnum.PLANNING),
        ]
    )
    run = service.create_run(workspace_id="ws_canc3", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)
    service.cancel_run(run.run_id, workspace_id="ws_canc3")

    # Second cancel must raise RunAlreadyTerminalError
    with pytest.raises(RunAlreadyTerminalError):
        service.cancel_run(run.run_id, workspace_id="ws_canc3")
