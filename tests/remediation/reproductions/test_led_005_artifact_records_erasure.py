import pytest
from pathlib import Path
from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState, ArtifactRecord, ValidationLevel, LifecycleState

def test_led_005_stage_save_erases_previous_artifacts(tmp_path):
    """
    Finding: LED-005
    Owner Package: S06 (Artifact Registry & Retention)
    Expected correct behavior: Artifact records from previous stages (e.g. 02_asset_manifest.json,
    master_plan.md) must be preserved in state across subsequent stage transitions.
    Actual behavior on current main: In scripts/pipeline.py line 208:
        state.artifact_records = refs
    It directly overwrites the entire list with only the current stage's refs, wiping all prior evidence.
    """
    project_dir = tmp_path / "project_art_erase"
    project_dir.mkdir(parents=True)
    
    # 1. State at PLAN_READY with master_plan.md
    plan_record = ArtifactRecord(path="master_plan.md", validation=ValidationLevel.SHA256, sha256="fake_sha")
    state = ProjectState(
        project_id="test_art_erase",
        lifecycle_state=LifecycleState.PLAN_READY,
        artifact_records=[plan_record]
    )
    StateStore.save(project_dir, state)
    
    # 2. Simulate what save_state() in scripts/pipeline.py does when moving to BLUEPRINT_READY:
    # line 208: state.artifact_records = refs (e.g. only new blueprint refs)
    loaded_state = StateStore.load(project_dir)
    assert len(loaded_state.artifact_records) == 1
    assert loaded_state.artifact_records[0].path == "master_plan.md"
    
    # Simulate stage saving only new refs
    blueprint_refs = [ArtifactRecord(path="05_blueprint.json", validation=ValidationLevel.SHA256, sha256="fake_bp_sha")]
    loaded_state.artifact_records = blueprint_refs
    StateStore.save(project_dir, loaded_state)
    
    # Reload and check whether master_plan.md is preserved
    final_state = StateStore.load(project_dir)
    paths_in_state = [rec.path for rec in final_state.artifact_records]
    
    # Assertion proving the defect:
    # Correct behavior: 'master_plan.md' must still be present in artifact_records
    # Current behavior on main: 'master_plan.md' was erased!
    assert "master_plan.md" in paths_in_state, (
        f"DEFECT PROVEN (LED-005): Saving blueprint stage artifacts erased previous stage records! "
        f"Remaining paths: {paths_in_state}"
    )
