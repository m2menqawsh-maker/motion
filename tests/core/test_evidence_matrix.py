import pytest
import json
from pathlib import Path

from scripts.core.state_model import (
    LifecycleState,
    ValidationLevel,
    ArtifactRecord,
    ProjectState,
)
from scripts.core.state_store import StateStore
from scripts.core.lifecycle_service import LifecycleService, LifecyclePreconditionFailedError
from scripts.core.recovery_engine import RecoveryEngine


def test_red_1_complete_without_required_output_evidence(tmp_path):
    """
    Test 1 (S06 Red Reproduction):
    A project in COMPLETE state MUST NOT be considered valid or resumable
    if its mandatory final output (out.mp4) is missing on disk or missing from evidence records.
    Current defect on HEAD: RecoveryEngine loops only over state.artifact_records.
    If valid predecessor records exist, but out.mp4 is missing, it returns can_resume=True!
    """
    project_dir = tmp_path / "prj_complete_no_output"
    project_dir.mkdir(parents=True)

    # Required predecessor files exist on disk
    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")

    plan_record = StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256)
    bp_record = StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256)

    # State claims COMPLETE, but out.mp4 is missing on disk and not in records
    state = ProjectState(
        project_id="prj_complete_no_output",
        lifecycle_state=LifecycleState.COMPLETE,
        artifact_records=[plan_record, bp_record],
    )
    StateStore.save(project_dir, state)

    assert not (project_dir / "out.mp4").exists()

    decision = RecoveryEngine.evaluate(project_dir)
    assert not decision.can_resume, (
        f"DEFECT (Test 1): RecoveryEngine accepted COMPLETE state without required output artifact! "
        f"Reason: {decision.reason}"
    )


def test_red_2_missing_required_evidence_despite_empty_record_list(tmp_path):
    """
    Test 2 (S06 Red Reproduction):
    An empty artifact_records list must NOT be treated as 'no errors found'.
    RecoveryEngine must check against the Required Evidence Policy for the state.
    Current defect on HEAD: loops 0 times and returns can_resume=True.
    """
    project_dir = tmp_path / "prj_empty_records"
    project_dir.mkdir(parents=True)

    # State is at PLAN_READY, but artifact_records is empty
    state = ProjectState(
        project_id="prj_empty_records",
        lifecycle_state=LifecycleState.PLAN_READY,
        artifact_records=[],
    )
    StateStore.save(project_dir, state)

    decision = RecoveryEngine.evaluate(project_dir)
    assert not decision.can_resume, (
        f"DEFECT (Test 2): RecoveryEngine trusted empty artifact_records on PLAN_READY state! "
        f"Reason: {decision.reason}"
    )


def test_red_3_evidence_survives_lifecycle_progression(tmp_path):
    """
    Test 3 (S06 Red Reproduction):
    Evidence from earlier stages (e.g. 02_asset_manifest.json from ASSETS_READY)
    must survive subsequent stage transitions (e.g. PLAN_READY, BLUEPRINT_READY).
    Current defect on HEAD: LifecycleService replaces working_copy.artifact_records = new_records.
    """
    project_dir = tmp_path / "prj_cumulative_evidence"
    StateStore.create(project_dir, "prj_cumulative_evidence")

    # 1. DRAFT -> ASSETS_READY
    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    s1 = LifecycleService.transition(
        project_dir=project_dir,
        target_state=LifecycleState.ASSETS_READY,
        artifacts=[("02_asset_manifest.json", ValidationLevel.EXISTS)],
    )
    paths_s1 = [r.path for r in s1.artifact_records]
    assert "02_asset_manifest.json" in paths_s1

    # 2. ASSETS_READY -> PLAN_READY
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    s2 = LifecycleService.transition(
        project_dir=project_dir,
        target_state=LifecycleState.PLAN_READY,
        artifacts=[("master_plan.md", ValidationLevel.SHA256)],
    )
    paths_s2 = [r.path for r in s2.artifact_records]
    assert "02_asset_manifest.json" in paths_s2, (
        f"DEFECT (Test 3): Transition to PLAN_READY erased 02_asset_manifest.json! Found: {paths_s2}"
    )
    assert "master_plan.md" in paths_s2

    # 3. PLAN_READY -> BLUEPRINT_READY
    (project_dir / "05_blueprint.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
    s3 = LifecycleService.transition(
        project_dir=project_dir,
        target_state=LifecycleState.BLUEPRINT_READY,
        artifacts=[("05_blueprint.json", ValidationLevel.SHA256)],
    )
    paths_s3 = [r.path for r in s3.artifact_records]
    assert "02_asset_manifest.json" in paths_s3, (
        f"DEFECT (Test 3): Transition to BLUEPRINT_READY erased 02_asset_manifest.json! Found: {paths_s3}"
    )
    assert "master_plan.md" in paths_s3, (
        f"DEFECT (Test 3): Transition to BLUEPRINT_READY erased master_plan.md! Found: {paths_s3}"
    )
    assert "05_blueprint.json" in paths_s3


def test_red_4_awaiting_review_does_not_erase_probe_evidence(tmp_path):
    """
    Test 4 (S06 Red Reproduction):
    Probe evidence generated before review must remain persisted in state
    when transitioning to AWAITING_REVIEW.
    """
    project_dir = tmp_path / "prj_probe_review"
    StateStore.create(project_dir, "prj_probe_review")

    # Setup prerequisites
    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
    (project_dir / "media_map.json").write_text("{}", encoding="utf-8")
    (project_dir / "probe_qc_report.json").write_text(json.dumps({"status": "passed"}), encoding="utf-8")

    # Fast forward through transitions
    LifecycleService.transition(project_dir, LifecycleState.ASSETS_READY, [("02_asset_manifest.json", ValidationLevel.EXISTS)])
    LifecycleService.transition(project_dir, LifecycleState.PLAN_READY, [("master_plan.md", ValidationLevel.SHA256)])
    LifecycleService.transition(project_dir, LifecycleState.BLUEPRINT_READY, [("05_blueprint.json", ValidationLevel.SHA256)])
    LifecycleService.transition(project_dir, LifecycleState.MATERIALIZED, [("media_map.json", ValidationLevel.EXISTS)])
    LifecycleService.transition(project_dir, LifecycleState.PROBE_PASSED, [("probe_qc_report.json", ValidationLevel.EXISTS)])

    # Transition to AWAITING_REVIEW
    LifecycleService.transition(project_dir, LifecycleState.AWAITING_REVIEW, artifacts=[])

    # Re-read authoritative state from disk
    loaded = StateStore.load(project_dir)
    assert loaded is not None
    loaded_paths = [r.path for r in loaded.artifact_records]

    assert "probe_qc_report.json" in loaded_paths, (
        f"DEFECT (Test 4): probe_qc_report.json was erased upon transitioning to AWAITING_REVIEW! "
        f"Persisted paths: {loaded_paths}"
    )
    assert "02_asset_manifest.json" in loaded_paths, (
        f"DEFECT (Test 4): Prior evidence 02_asset_manifest.json was erased upon reaching AWAITING_REVIEW! "
        f"Persisted paths: {loaded_paths}"
    )
    assert "master_plan.md" in loaded_paths, (
        f"DEFECT (Test 4): Prior evidence master_plan.md was erased upon reaching AWAITING_REVIEW! "
        f"Persisted paths: {loaded_paths}"
    )


def test_red_5_existing_evidence_update_is_deterministic(tmp_path):
    """
    Test 5 (S06 Red Reproduction):
    Updating an artifact record for the same logical path replaces the record
    in-place with updated fields (e.g. newer hash) without producing duplicates.
    """
    project_dir = tmp_path / "prj_deterministic_update"
    project_dir.mkdir(parents=True)

    (project_dir / "master_plan.md").write_text("# Initial Plan", encoding="utf-8")

    state = ProjectState(
        project_id="prj_deterministic_update",
        lifecycle_state=LifecycleState.PLAN_READY,
    )
    rec1 = StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256)
    initial_hash = rec1.sha256

    # Record first version
    if hasattr(state, "record_evidence"):
        state.record_evidence(rec1)
    else:
        state.artifact_records.append(rec1)
    StateStore.save(project_dir, state)

    # Update file content and record second version
    (project_dir / "master_plan.md").write_text("# Updated Plan Content", encoding="utf-8")
    rec2 = StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256)
    updated_hash = rec2.sha256
    assert initial_hash != updated_hash

    loaded = StateStore.load(project_dir)
    if hasattr(loaded, "record_evidence"):
        loaded.record_evidence(rec2)
    else:
        loaded.artifact_records.append(rec2)
    StateStore.save(project_dir, loaded)

    final_state = StateStore.load(project_dir)
    plan_records = [r for r in final_state.artifact_records if r.path == "master_plan.md"]

    assert len(plan_records) == 1, (
        f"DEFECT (Test 5): Duplicate artifact records found for 'master_plan.md': {plan_records}"
    )
    assert plan_records[0].sha256 == updated_hash


def test_valid_complete_state_with_all_evidence_passes(tmp_path):
    """
    Acceptance Criterion: A COMPLETE state with all required evidence validly
    present on disk and recorded passes validation and evaluates as resumable.
    """
    project_dir = tmp_path / "prj_valid_complete"
    project_dir.mkdir(parents=True)

    # Write required files
    (project_dir / "02_asset_manifest.json").write_text('{"assets": []}', encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Valid Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text('{"scenes": []}', encoding="utf-8")
    (project_dir / "out.mp4").write_bytes(b"\x00" * 1024)  # 1 KB valid mock mp4

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "out.mp4", ValidationLevel.SIZE),
    ]

    state = ProjectState(
        project_id="prj_valid_complete",
        lifecycle_state=LifecycleState.COMPLETE,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    decision = RecoveryEngine.evaluate(project_dir)
    assert decision.can_resume is True
    assert decision.next_state == LifecycleState.COMPLETE
    assert decision.validation_result is not None
    assert decision.validation_result.is_valid is True
    assert decision.validation_result.verified_count == 4


def test_size_mismatch_detected(tmp_path):
    """Verifies that an unexpected modification to artifact size triggers SIZE_MISMATCH."""
    project_dir = tmp_path / "prj_size_mismatch"
    project_dir.mkdir(parents=True)

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")
    (project_dir / "out.mp4").write_bytes(b"\x00" * 500)

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "out.mp4", ValidationLevel.SIZE),
    ]

    state = ProjectState(
        project_id="prj_size_mismatch",
        lifecycle_state=LifecycleState.COMPLETE,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    # Tamper with file size
    (project_dir / "out.mp4").write_bytes(b"\x00" * 1500)

    decision = RecoveryEngine.evaluate(project_dir)
    assert decision.can_resume is False
    assert decision.validation_result is not None
    assert decision.validation_result.is_valid is False
    issue_types = [iss.issue_type.value for iss in decision.validation_result.issues]
    assert "SIZE_MISMATCH" in issue_types


def test_hash_mismatch_detected(tmp_path):
    """Verifies that an altered file with unchanged size triggers HASH_MISMATCH."""
    project_dir = tmp_path / "prj_hash_mismatch"
    project_dir.mkdir(parents=True)

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("AAAABBBBCCCCDDDD", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")
    (project_dir / "out.mp4").write_bytes(b"\x00" * 200)

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "out.mp4", ValidationLevel.SIZE),
    ]

    state = ProjectState(
        project_id="prj_hash_mismatch",
        lifecycle_state=LifecycleState.COMPLETE,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    # Alter content while keeping exact same length
    (project_dir / "master_plan.md").write_text("XXXXYYYYZZZZWWWW", encoding="utf-8")

    decision = RecoveryEngine.evaluate(project_dir)
    assert decision.can_resume is False
    assert decision.validation_result is not None
    assert decision.validation_result.is_valid is False
    issue_types = [iss.issue_type.value for iss in decision.validation_result.issues]
    assert "HASH_MISMATCH" in issue_types


def test_empty_file_rejected(tmp_path):
    """Verifies that a 0-byte required file is caught as EMPTY_FILE."""
    project_dir = tmp_path / "prj_empty_file"
    project_dir.mkdir(parents=True)

    # 0-byte file
    (project_dir / "02_asset_manifest.json").write_text("", encoding="utf-8")

    state = ProjectState(
        project_id="prj_empty_file",
        lifecycle_state=LifecycleState.ASSETS_READY,
        artifact_records=[ArtifactRecord(path="02_asset_manifest.json", validation=ValidationLevel.EXISTS)],
    )
    StateStore.save(project_dir, state)

    decision = RecoveryEngine.evaluate(project_dir)
    assert decision.can_resume is False
    assert decision.validation_result is not None
    issue_types = [iss.issue_type.value for iss in decision.validation_result.issues]
    assert "EMPTY_FILE" in issue_types


def test_state_store_cas_and_concurrency_preserved_with_evidence(tmp_path):
    """
    Verifies that S05 CAS protection, monotonic revision increment,
    and cross-process locking work cleanly alongside S06 cumulative evidence.
    """
    from scripts.core.state_store import StateConflictError

    project_dir = tmp_path / "prj_cas_evidence"
    StateStore.create(project_dir, "prj_cas_evidence")

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    st1 = LifecycleService.transition(
        project_dir,
        LifecycleState.ASSETS_READY,
        artifacts=[("02_asset_manifest.json", ValidationLevel.EXISTS)],
    )
    assert st1.revision == 2

    # Attempting an atomic update with stale revision (1 instead of 2) MUST fail CAS
    with pytest.raises(StateConflictError):
        StateStore.atomic_update(
            project_dir,
            expected_revision=1,
            mutator=lambda s: s.record_evidence(ArtifactRecord(path="dummy.txt", validation=ValidationLevel.EXISTS)),
        )

    # Correct revision (2) succeeds and increments revision to 3
    st2 = StateStore.atomic_update(
        project_dir,
        expected_revision=2,
        mutator=lambda s: s.record_evidence(ArtifactRecord(path="dummy.txt", validation=ValidationLevel.EXISTS)),
    )
    assert st2.revision == 3
    # 02_asset_manifest.json must still be preserved
    paths = [r.path for r in st2.artifact_records]
    assert "02_asset_manifest.json" in paths
    assert "dummy.txt" in paths
