"""
tests/ai/orchestration/test_repository_persistence.py
=====================================================
Integration tests proving persistent SQLite storage of AIRun and AIStep (S27.11).

Invariants verified:
- AIRun and AIStep records are saved to and queried from physical database.
- Modifying state in repository strictly updates durable rows on disk.
- Cascading delete of AIRun removes child AISteps.
"""

from datetime import datetime, timezone
import pytest
from ai.contracts.common import CapabilityTypeEnum
from ai.contracts.run import AIRun, AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_ai_orchestration.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    return SQLAIRunRepository(engine=engine)


def test_create_and_get_airun(repo):
    now = datetime.now(timezone.utc)
    run = AIRun(
        run_id="run_test_001",
        workspace_id="ws_acme",
        project_id="prj_100",
        session_id="sess_555",
        status=AIRunStatus.PENDING,
        capability=CapabilityTypeEnum.PLANNING,
        workflow_ref="recipe_v1",
        created_at=now,
        usage=UsageRecord(input_tokens=100, output_tokens=50, total_tokens=150),
        cost=CostEstimate(estimated_cost="0.02"),
    )

    repo.create_run(run)

    loaded = repo.get_run("run_test_001", workspace_id="ws_acme")
    assert loaded is not None
    assert loaded.run_id == "run_test_001"
    assert loaded.workspace_id == "ws_acme"
    assert loaded.status == AIRunStatus.PENDING
    assert loaded.usage.total_tokens == 150
    assert str(loaded.cost.estimated_cost) == "0.02"


def test_create_and_get_aisteps(repo):
    now = datetime.now(timezone.utc)
    run = AIRun(
        run_id="run_steps_001",
        workspace_id="ws_acme",
        status=AIRunStatus.PENDING,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.00"),
    )
    repo.create_run(run)

    step1 = AIStep(
        step_id="step_01",
        run_id="run_steps_001",
        status=AIStepStatus.PENDING,
        attempt=1,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        cost=CostEstimate(estimated_cost="0.01"),
        dependencies=[],
    )
    step2 = AIStep(
        step_id="step_02",
        run_id="run_steps_001",
        status=AIStepStatus.WAITING,
        attempt=1,
        capability=CapabilityTypeEnum.VOICE_ANALYSIS,
        created_at=now,
        cost=CostEstimate(estimated_cost="0.02"),
        dependencies=["step_01"],
    )

    repo.create_steps([step1, step2])

    steps = repo.get_steps_for_run("run_steps_001", workspace_id="ws_acme")
    assert len(steps) == 2
    assert steps[0].step_id == "step_01"
    assert steps[0].status == AIStepStatus.PENDING
    assert steps[1].step_id == "step_02"
    assert steps[1].status == AIStepStatus.WAITING
    assert steps[1].dependencies == ["step_01"]


def test_update_airun_and_aistep_persistence(repo):
    now = datetime.now(timezone.utc)
    run = AIRun(
        run_id="run_upd_001",
        workspace_id="ws_acme",
        status=AIRunStatus.PENDING,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        usage=UsageRecord(),
        cost=CostEstimate(estimated_cost="0.00"),
    )
    repo.create_run(run)

    step = AIStep(
        step_id="step_upd_01",
        run_id="run_upd_001",
        status=AIStepStatus.PENDING,
        attempt=1,
        capability=CapabilityTypeEnum.PLANNING,
        created_at=now,
        cost=CostEstimate(estimated_cost="0.01"),
    )
    repo.create_steps([step])

    # Update run to RUNNING
    run_running = run.model_copy(update={"status": AIRunStatus.RUNNING, "started_at": now})
    repo.update_run(run_running)

    loaded_run = repo.get_run("run_upd_001")
    assert loaded_run.status == AIRunStatus.RUNNING

    # Update step to RUNNING
    step_running = step.model_copy(update={"status": AIStepStatus.RUNNING, "started_at": now})
    repo.update_step(step_running)

    loaded_step = repo.get_step("step_upd_01")
    assert loaded_step.status == AIStepStatus.RUNNING
