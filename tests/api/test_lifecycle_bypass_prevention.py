"""
Tests proving prevention of API lifecycle bypass (Finding STATE-001 / S03).
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from api.services.pipeline_service import PipelineService
from scripts.core.lifecycle_service import (
    LifecycleError,
    LifecyclePreconditionFailedError,
)
from scripts.core.state_model import LifecycleState, ProjectState
from scripts.core.state_store import StateStore


@pytest.fixture
def api_project(tmp_path, monkeypatch):
    project_id = "test-api-bypass-prev"
    proj_dir = tmp_path / "projects" / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        PipelineService,
        "_get_project_dir",
        classmethod(lambda cls, pid: proj_dir),
    )

    StateStore.create(proj_dir, project_id)
    return project_id, proj_dir


@pytest.mark.asyncio
async def test_pipeline_service_finish_stage_rejected(api_project):
    """PipelineService.finish_stage must raise LifecyclePreconditionFailedError without gate proof."""
    project_id, proj_dir = api_project

    with pytest.raises(LifecyclePreconditionFailedError):
        await PipelineService.finish_stage(project_id, "asset_gate")

    state = StateStore.load(proj_dir)
    assert state.lifecycle_state == LifecycleState.DRAFT
    assert state.lifecycle_state != LifecycleState.ASSETS_READY


def test_api_finish_stage_returns_422_and_does_not_mutate_state(api_project):
    """Calling POST /gates/{project_id}/finish/asset_gate must return 422 and leave state unchanged."""
    project_id, proj_dir = api_project

    client = TestClient(
        app,
        headers={"X-Principal-ID": "editor_user", "X-Principal-Roles": "editor"},
    )

    response = client.post(f"/gates/{project_id}/finish/asset_gate")
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert data["error"] == "LifecyclePreconditionFailedError"

    # Crucial check: lifecycle_state is unchanged
    state = StateStore.load(proj_dir)
    assert state.lifecycle_state == LifecycleState.DRAFT


def test_api_approve_gate_does_not_advance_lifecycle(api_project):
    """Calling POST /gates/{project_id}/approve/asset_gate fails closed with 422 and does NOT advance lifecycle or mutate metadata."""
    project_id, proj_dir = api_project

    client = TestClient(
        app,
        headers={"X-Principal-ID": "rev_user", "X-Principal-Roles": "reviewer"},
    )

    response = client.post(f"/gates/{project_id}/approve/asset_gate")
    assert response.status_code == 422
    assert response.json()["error"] == "UnsupportedGateOperationError"

    state = StateStore.load(proj_dir)
    # Metadata is NOT recorded (S04 Final Closure: zero side effects)
    assert "approved_by" not in state.approval_metadata
    # Lifecycle must NOT have advanced
    assert state.lifecycle_state == LifecycleState.DRAFT

