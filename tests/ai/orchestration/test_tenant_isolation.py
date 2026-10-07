"""
tests/ai/orchestration/test_tenant_isolation.py
================================================
Security tests proving strict multi-tenant isolation across AIRuns and AISteps (S27.11).

Invariants verified:
- Workspace B cannot read, inspect, or retrieve Workspace A runs or steps.
- Workspace B workers cannot claim Workspace A steps.
- Workspace B cannot cancel Workspace A runs.
"""

import pytest
from ai.contracts.common import CapabilityTypeEnum
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.errors import TenantAccessDeniedError
from ai.orchestration.service import AIRunService
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def service(tmp_path):
    db_file = tmp_path / "test_tenant.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLAIRunRepository(engine=engine)
    return AIRunService(repository=repo)


def test_cross_tenant_read_denied(service):
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step1", capability=CapabilityTypeEnum.PLANNING),
        ]
    )
    run_a = service.create_run(workspace_id="ws_alpha", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # Workspace A can read its own run
    assert service.get_run(run_a.run_id, workspace_id="ws_alpha") is not None

    # Workspace B attempt to read run_a is denied
    with pytest.raises(TenantAccessDeniedError) as exc_info:
        service.get_run(run_a.run_id, workspace_id="ws_beta")
    assert "belongs to workspace 'ws_alpha', not 'ws_beta'" in str(exc_info.value)


def test_cross_tenant_step_read_denied(service):
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="s1", capability=CapabilityTypeEnum.PLANNING),
        ]
    )
    run_a = service.create_run(workspace_id="ws_alpha", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)
    step_a_id = f"{run_a.run_id}_s1"

    # Workspace B attempt to read step_a is denied
    with pytest.raises(TenantAccessDeniedError):
        service.get_step(step_a_id, workspace_id="ws_beta")


def test_cross_tenant_claim_blocked(service):
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_a", capability=CapabilityTypeEnum.PLANNING),
        ]
    )
    service.create_run(workspace_id="ws_alpha", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # Worker configured for Workspace B polls for work
    claimed = service.claim_next_runnable_step(worker_id="worker_beta", workspace_id="ws_beta")
    assert claimed is None, "Worker from Workspace B must never be able to claim Workspace A steps"


def test_cross_tenant_cancel_denied(service):
    dag_spec = DAGSpecification(
        steps=[
            StepDefinition(step_id="step_a", capability=CapabilityTypeEnum.PLANNING),
        ]
    )
    run_a = service.create_run(workspace_id="ws_alpha", capability=CapabilityTypeEnum.PLANNING, dag_spec=dag_spec)

    # Workspace B tries to cancel Workspace A's run
    with pytest.raises(TenantAccessDeniedError):
        service.cancel_run(run_a.run_id, workspace_id="ws_beta")
