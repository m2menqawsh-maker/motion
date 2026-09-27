import pytest
import json
import os
import stat
from pathlib import Path

from scripts.core.state_model import (
    LifecycleState,
    ValidationLevel,
    ArtifactRecord,
    ProjectState,
)
from scripts.core.state_store import (
    StateStore,
    StateStoreError,
    StateNotFoundError,
)


def test_red_1_corrupted_json_is_not_missing_state(tmp_path):
    """
    Test 1 (S07 Red Reproduction):
    A corrupted .pipeline_state.json file must NOT be silently swallowed by StateStore.load()
    returning None (which causes pipeline to treat it as non-existent and reset to DRAFT).
    It must raise a specific StateCorruptedError.
    """
    from scripts.core.state_store import StateCorruptedError

    project_dir = tmp_path / "prj_corrupt_json"
    project_dir.mkdir(parents=True)
    state_file = project_dir / ".pipeline_state.json"
    state_file.write_text('{"project_id": "test", "lifecycle_state": "FINAL_QC_PASSED", INVALID_SYNTAX', encoding="utf-8")

    assert state_file.exists()

    with pytest.raises(StateCorruptedError) as exc_info:
        StateStore.load(project_dir)

    assert "Corrupted" in exc_info.type.__name__ or "corrupt" in str(exc_info.value).lower()


def test_red_2_schema_invalid_state_is_not_draft(tmp_path):
    """
    Test 2 (S07 Red Reproduction):
    A syntactically valid JSON file that violates the ProjectState schema (e.g. missing project_id,
    invalid lifecycle enum, forbidden fields) must raise StateCorruptedError, not return None.
    """
    from scripts.core.state_store import StateCorruptedError

    project_dir = tmp_path / "prj_schema_invalid"
    project_dir.mkdir(parents=True)
    state_file = project_dir / ".pipeline_state.json"
    # Valid JSON, but invalid schema: missing project_id and invalid lifecycle enum
    state_file.write_text(json.dumps({
        "schema_version": 1,
        "revision": 5,
        "lifecycle_state": "BOGUS_STATE_NEVER_EXISTED",
    }), encoding="utf-8")

    with pytest.raises(StateCorruptedError):
        StateStore.load(project_dir)


def test_red_3_io_failure_is_distinct(tmp_path):
    """
    Test 3 (S07 Red Reproduction):
    Permission or OS I/O failure when reading .pipeline_state.json must raise StateIOError,
    distinct from StateNotFoundError and StateCorruptedError.
    """
    from scripts.core.state_store import StateIOError

    project_dir = tmp_path / "prj_io_failure"
    project_dir.mkdir(parents=True)
    state_file = project_dir / ".pipeline_state.json"
    state_file.write_text(json.dumps({
        "project_id": "prj_io_failure",
        "lifecycle_state": "DRAFT",
    }), encoding="utf-8")

    # Make file unreadable
    try:
        os.chmod(state_file, 000)
        # Verify read error
        with pytest.raises(StateIOError):
            StateStore.load(project_dir)
    finally:
        os.chmod(state_file, stat.S_IRUSR | stat.S_IWUSR)


def test_red_4_advanced_lifecycle_missing_evidence_produces_rollback_plan(tmp_path):
    """
    Test 4 (S07 Red Reproduction):
    When state is advanced (COMPLETE) but downstream evidence is missing (media_map, out.mp4 missing),
    RecoveryPlanner must produce a structured RecoveryPlan identifying the last_valid_state (BLUEPRINT_READY)
    and stages needing replay, rather than just returning can_resume=False.
    """
    from scripts.core.recovery_engine import RecoveryPlanner, RecoveryPlan

    project_dir = tmp_path / "prj_plan_rollback"
    project_dir.mkdir(parents=True)

    # Valid upstream files exist on disk
    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")

    # Downstream files (media_map.json, probe_qc_report.json, out.mp4) do NOT exist on disk

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        ArtifactRecord(path="media_map.json", validation=ValidationLevel.EXISTS),
        ArtifactRecord(path="probe_qc_report.json", validation=ValidationLevel.EXISTS),
        ArtifactRecord(path="out.mp4", validation=ValidationLevel.SIZE, size_bytes=5000),
    ]

    state = ProjectState(
        project_id="prj_plan_rollback",
        lifecycle_state=LifecycleState.COMPLETE,
        revision=10,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    plan = RecoveryPlanner.create_plan(project_dir)
    assert isinstance(plan, RecoveryPlan)
    assert plan.current_state == LifecycleState.COMPLETE
    assert plan.last_valid_state == LifecycleState.BLUEPRINT_READY
    assert plan.target_state == LifecycleState.BLUEPRINT_READY
    assert "media_map.json" in plan.invalidated_evidence_paths
    assert "out.mp4" in plan.invalidated_evidence_paths
    assert len(plan.stages_to_replay) > 0


def test_red_5_persisted_state_is_reconciled_before_replay(tmp_path):
    """
    Test 5 (S07 Red Reproduction):
    Executing RecoveryService.apply_plan(plan) must reconcile the on-disk state:
    persisted lifecycle_state becomes target_state (BLUEPRINT_READY) and revision increments monotonically.
    """
    from scripts.core.recovery_engine import RecoveryPlanner, RecoveryService

    project_dir = tmp_path / "prj_apply_reconcile"
    project_dir.mkdir(parents=True)

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        ArtifactRecord(path="out.mp4", validation=ValidationLevel.SIZE, size_bytes=1000),
    ]

    state = ProjectState(
        project_id="prj_apply_reconcile",
        lifecycle_state=LifecycleState.COMPLETE,
        revision=15,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    plan = RecoveryPlanner.create_plan(project_dir)
    assert plan.target_state == LifecycleState.BLUEPRINT_READY

    # Apply reconciliation
    reconciled_state = RecoveryService.apply_plan(project_dir, plan)

    assert reconciled_state.lifecycle_state == LifecycleState.BLUEPRINT_READY
    assert reconciled_state.revision == plan.expected_revision + 1
    assert reconciled_state.revision > 15

    # Verify persisted state on disk
    persisted = StateStore.load(project_dir)
    assert persisted.lifecycle_state == LifecycleState.BLUEPRINT_READY
    assert persisted.revision == reconciled_state.revision


def test_red_6_recovery_preserves_valid_upstream_evidence(tmp_path):
    """
    Test 6 (S07 Red Reproduction):
    Recovery rollback to BLUEPRINT_READY must preserve valid upstream evidence records
    (02_asset_manifest.json, master_plan.md, 05_blueprint.json) with VALID status.
    """
    from scripts.core.recovery_engine import RecoveryPlanner, RecoveryService

    project_dir = tmp_path / "prj_preserve_upstream"
    project_dir.mkdir(parents=True)

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        ArtifactRecord(path="out.mp4", validation=ValidationLevel.SIZE, size_bytes=500),
    ]

    state = ProjectState(
        project_id="prj_preserve_upstream",
        lifecycle_state=LifecycleState.COMPLETE,
        revision=5,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    plan = RecoveryPlanner.create_plan(project_dir)
    reconciled = RecoveryService.apply_plan(project_dir, plan)

    # Check upstream records still valid
    manifest_rec = reconciled.get_artifact_record("02_asset_manifest.json")
    plan_rec = reconciled.get_artifact_record("master_plan.md")
    bp_rec = reconciled.get_artifact_record("05_blueprint.json")

    assert manifest_rec is not None and getattr(manifest_rec, "status", "VALID") == "VALID"
    assert plan_rec is not None and getattr(plan_rec, "status", "VALID") == "VALID"
    assert bp_rec is not None and getattr(bp_rec, "status", "VALID") == "VALID"


def test_red_7_invalid_downstream_evidence_becomes_explicitly_invalidated(tmp_path):
    """
    Test 7 (S07 Red Reproduction):
    Downstream evidence from rolled-back stages (out.mp4) must not be silently deleted,
    but explicitly invalidated with status="INVALIDATED" and an invalidation reason.
    """
    from scripts.core.recovery_engine import RecoveryPlanner, RecoveryService

    project_dir = tmp_path / "prj_explicit_invalidation"
    project_dir.mkdir(parents=True)

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        ArtifactRecord(path="out.mp4", validation=ValidationLevel.SIZE, size_bytes=500),
    ]

    state = ProjectState(
        project_id="prj_explicit_invalidation",
        lifecycle_state=LifecycleState.COMPLETE,
        revision=7,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    plan = RecoveryPlanner.create_plan(project_dir)
    reconciled = RecoveryService.apply_plan(project_dir, plan)

    out_rec = reconciled.get_artifact_record("out.mp4")
    assert out_rec is not None, "Evidence history must be retained for auditability"
    assert getattr(out_rec, "status", None) == "INVALIDATED"
    assert getattr(out_rec, "invalidated_reason", None) is not None
    assert getattr(out_rec, "invalidated_at", None) is not None
