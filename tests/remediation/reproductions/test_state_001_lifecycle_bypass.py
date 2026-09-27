import pytest
import asyncio
from pathlib import Path
from api.services.pipeline_service import PipelineService
from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState, LifecycleState

@pytest.mark.asyncio
async def test_state_001_api_bypasses_gates_and_validation(tmp_path, monkeypatch):
    """
    Finding: STATE-001 / LED-018
    Owner Package: S03 (Lifecycle State Engine)
    Expected correct behavior: PipelineService.finish_stage("2") MUST NOT transition
    the lifecycle to BLUEPRINT_READY unless blueprint validation succeeds.
    Actual behavior on current main: PipelineService directly mutates state.lifecycle_state
    without invoking validate_blueprint or checking any evidence.
    """
    project_id = "repro-state-001"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock project directory in PipelineService
    monkeypatch.setattr(PipelineService, "_get_project_dir", classmethod(lambda cls, pid: project_dir))
    
    # Initialize initial state as DRAFT
    initial_state = ProjectState(project_id=project_id, lifecycle_state=LifecycleState.DRAFT)
    StateStore.save(project_dir, initial_state)
    
    # Calling finish_stage for stage 2 (blueprint stage) WITHOUT any valid blueprint on disk
    assert not (project_dir / "05_blueprint.json").exists()
    
    result = await PipelineService.finish_stage(project_id, "2")
    
    loaded_state = StateStore.load(project_dir)
    assert loaded_state is not None
    
    # Assertion proving the defect:
    # Correct behavior: Should NOT be BLUEPRINT_READY without validation and evidence.
    # Current behavior on main: loaded_state.lifecycle_state IS BLUEPRINT_READY (Bypass successful).
    assert loaded_state.lifecycle_state != LifecycleState.BLUEPRINT_READY, (
        f"DEFECT PROVEN: PipelineService.finish_stage('2') mutated lifecycle to "
        f"{loaded_state.lifecycle_state} without blueprint validation or evidence."
    )
