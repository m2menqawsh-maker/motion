import pytest
import os
import json
from pathlib import Path
from scripts.checkpoint_model import CheckpointStage, ValidationLevel, CheckpointRecord, ArtifactRecord
from scripts.checkpoint_store import CheckpointStore
from scripts.recovery_engine import RecoveryEngine

@pytest.fixture
def temp_project(tmp_path):
    proj_dir = tmp_path / "projects" / "test_proj"
    proj_dir.mkdir(parents=True)
    return proj_dir

def test_recovery_from_assets_ready(temp_project):
    # Crash after assets -> resume at next stage (Plan)
    record = CheckpointRecord(
        project_id="test_proj",
        run_id="run1",
        checkpoint=CheckpointStage.ASSETS_READY,
        timestamp=0.0
    )
    CheckpointStore.save(temp_project, record)
    
    decision = RecoveryEngine.evaluate(temp_project)
    
    assert decision.can_resume is True
    assert decision.next_stage == CheckpointStage.ASSETS_READY

def test_recovery_from_render_missing_artifacts(temp_project):
    # Crash after render -> resume at Render, but artifact missing -> FAIL
    
    # Create the dummy file so we can generate the record
    dummy_file = temp_project / "out.mp4"
    dummy_file.write_bytes(b"dummy")
    
    refs = [
        CheckpointStore.create_artifact_record(temp_project, "out.mp4", ValidationLevel.EXISTS)
    ]
    
    # Delete it to simulate it being missing
    dummy_file.unlink()
    
    record = CheckpointRecord(
        project_id="test_proj",
        run_id="run-1",
        checkpoint=CheckpointStage.RENDERED,
        timestamp=0.0,
        artifact_references=refs
    )
    CheckpointStore.save(temp_project, record)

    decision = RecoveryEngine.evaluate(temp_project)
    
    assert decision.can_resume is False
    assert decision.next_stage is None
    assert "missing" in decision.reason

def test_recovery_from_render_with_artifacts(temp_project):
    # Crash after render -> resume at QC
    # Create artifacts
    (temp_project / "master_plan.md").write_text("plan")
    (temp_project / "05_blueprint.json").write_text("blueprint")
    (temp_project / "out.mp4").write_text("video")
    
    refs = [
        CheckpointStore.create_artifact_record(temp_project, "master_plan.md", ValidationLevel.SHA256),
        CheckpointStore.create_artifact_record(temp_project, "05_blueprint.json", ValidationLevel.SHA256),
        CheckpointStore.create_artifact_record(temp_project, "out.mp4", ValidationLevel.SIZE)
    ]
    
    record = CheckpointRecord(
        project_id="test_proj",
        run_id="run1",
        checkpoint=CheckpointStage.RENDERED,
        timestamp=0.0,
        artifact_references=refs
    )
    CheckpointStore.save(temp_project, record)
    
    decision = RecoveryEngine.evaluate(temp_project)
    
    assert decision.can_resume is True
    assert decision.next_stage == CheckpointStage.RENDERED

def test_recovery_rejected_unsupported_schema(temp_project):
    # Checkpoint valid but schema unsupported
    record = CheckpointRecord(
        project_id="test_proj",
        run_id="run1",
        checkpoint=CheckpointStage.ASSETS_READY,
        timestamp=0.0,
        checkpoint_schema_version="0.1" # Old schema
    )
    CheckpointStore.save(temp_project, record)
    
    decision = RecoveryEngine.evaluate(temp_project)
    
    assert decision.can_resume is False
    assert decision.recommended_action == "restart_from_scratch"

def test_recovery_rejected_missing_artifact(temp_project):
    # Artifact missing -> checkpoint invalid
    refs = [ArtifactRecord(path="out.mp4", validation=ValidationLevel.SIZE, size_bytes=100)]
    record = CheckpointRecord(
        project_id="test_proj",
        run_id="run1",
        checkpoint=CheckpointStage.RENDERED,
        timestamp=0.0,
        artifact_references=refs
    )
    CheckpointStore.save(temp_project, record)
    
    decision = RecoveryEngine.evaluate(temp_project)
    
    assert decision.can_resume is False
    assert "missing" in decision.reason
    assert decision.recommended_action == "restart_from_stage_creating_out.mp4"

def test_recovery_rejected_size_mismatch(temp_project):
    # Artifact exists but size mismatch
    out_file = temp_project / "out.mp4"
    out_file.write_text("12345") # size 5
    
    refs = [ArtifactRecord(path="out.mp4", validation=ValidationLevel.SIZE, size_bytes=100)] # expected 100
    record = CheckpointRecord(
        project_id="test_proj",
        run_id="run1",
        checkpoint=CheckpointStage.RENDERED,
        timestamp=0.0,
        artifact_references=refs
    )
    CheckpointStore.save(temp_project, record)
    
    decision = RecoveryEngine.evaluate(temp_project)
    
    assert decision.can_resume is False
    assert "size mismatch" in decision.reason
    assert decision.recommended_action == "restart_from_stage_creating_out.mp4"
    
def test_recovery_rejected_hash_mismatch(temp_project):
    # Artifact exists but hash mismatch
    plan_file = temp_project / "master_plan.md"
    plan_file.write_text("plan_changed")
    
    refs = [ArtifactRecord(path="master_plan.md", validation=ValidationLevel.SHA256, sha256="old_hash", size_bytes=12)]
    record = CheckpointRecord(
        project_id="test_proj",
        run_id="run1",
        checkpoint=CheckpointStage.PLAN_READY,
        timestamp=0.0,
        artifact_references=refs
    )
    CheckpointStore.save(temp_project, record)
    
    decision = RecoveryEngine.evaluate(temp_project)
    
    assert decision.can_resume is False
    assert "hash mismatch" in decision.reason
    assert decision.recommended_action == "restart_from_stage_creating_master_plan.md"
