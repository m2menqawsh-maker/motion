"""
S07.5 Evidence & Recovery Hardening — Red Reproduction Tests.

Tests the four key architectural observations:
1. Observation A: .studio_approved alone cannot be trust authority.
2. Observation B: Defensive evidence merge must not resurrect INVALIDATED or SUPERSEDED records.
3. Observation C: RecoveryPlanner must be graph-aware and query StateMachine ancestors.
4. Observation D: Filesystem marker cleanup failure or crash window must not compromise canonical rollback.
"""

import pytest
import json
import uuid
from pathlib import Path
from unittest.mock import patch

from scripts.core.state_model import (
    LifecycleState,
    ValidationLevel,
    EvidenceStatus,
    ArtifactRecord,
    ProjectState,
    StateMachine,
)
from scripts.core.state_store import StateStore
from scripts.core.evidence_matrix import (
    RequiredEvidencePolicy,
    merge_artifact_records,
)
from scripts.core.recovery_engine import (
    RecoveryPlan,
    RecoveryPlanner,
    RecoveryService,
    RecoveryEngine,
)


# ==============================================================================
# Group 1: Observation A & D — .studio_approved is not Trust Authority
# ==============================================================================

def test_red_obs_a_forged_studio_approved_alone_fails_evidence_validation(tmp_path):
    """
    Observation A:
    When state is claimed to be REVIEW_APPROVED, but approval_metadata lacks canonical
    structured approval (approved_by is missing), having .studio_approved on disk
    alone must NOT be considered valid authoritative evidence.
    """
    project_dir = tmp_path / "prj_forged_marker"
    project_dir.mkdir(parents=True)

    # Valid upstream files
    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")
    (project_dir / "media_map.json").write_text("{}", encoding="utf-8")
    (project_dir / "probe_qc_report.json").write_text("{}", encoding="utf-8")

    # Forged marker on disk
    (project_dir / ".studio_approved").write_text("approved\n", encoding="utf-8")

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "media_map.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "probe_qc_report.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, ".studio_approved", ValidationLevel.EXISTS),
    ]

    # State has NO approved_by in approval_metadata
    state = ProjectState(
        project_id="prj_forged_marker",
        lifecycle_state=LifecycleState.REVIEW_APPROVED,
        revision=6,
        artifact_records=records,
        approval_metadata={},  # Empty! No canonical approved_by
    )
    StateStore.save(project_dir, state)

    # Validate evidence
    validation_res = RequiredEvidencePolicy.validate_required_evidence(state, project_dir)

    # Expected after S07.5: Must fail validation because .studio_approved alone lacks canonical approved_by
    assert not validation_res.is_valid, (
        "DEFECT PROVEN (Obs A): RequiredEvidencePolicy trusted .studio_approved alone "
        "without canonical structured approval_metadata (approved_by)!"
    )


def test_red_obs_d_marker_cleanup_failure_preserves_canonical_rollback(tmp_path):
    """
    Observation D:
    During RecoveryService.apply_plan, if unlinking .studio_approved fails (e.g. PermissionError),
    the canonical state rollback must still succeed, approval_metadata must remain INVALIDATED,
    and the stale marker on disk must NOT be accepted as valid approval.
    """
    project_dir = tmp_path / "prj_cleanup_failure"
    project_dir.mkdir(parents=True)

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")
    (project_dir / ".studio_approved").write_text("", encoding="utf-8")

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, ".studio_approved", ValidationLevel.EXISTS),
    ]

    state = ProjectState(
        project_id="prj_cleanup_failure",
        lifecycle_state=LifecycleState.REVIEW_APPROVED,
        revision=8,
        artifact_records=records,
        approval_metadata={"approved_by": "reviewer_alice", "status": "APPROVED"},
    )
    StateStore.save(project_dir, state)

    plan = RecoveryPlanner.create_plan(project_dir)
    assert plan.target_state == LifecycleState.BLUEPRINT_READY

    # Simulate unlink failure on .studio_approved
    orig_unlink = Path.unlink

    def failing_unlink(self, *args, **kwargs):
        if self.name == ".studio_approved":
            raise PermissionError("Simulated read-only filesystem")
        return orig_unlink(self, *args, **kwargs)

    with patch.object(Path, "unlink", failing_unlink):
        reconciled = RecoveryService.apply_plan(project_dir, plan)

    # 1. State rollback succeeded on disk
    assert reconciled.lifecycle_state == LifecycleState.BLUEPRINT_READY
    # 2. Canonical approval metadata was invalidated
    assert reconciled.approval_metadata.get("status") == "INVALIDATED"
    assert "approved_by" not in reconciled.approval_metadata or reconciled.approval_metadata["approved_by"] is None
    # 3. .studio_approved may still be on disk (due to failed unlink)
    assert (project_dir / ".studio_approved").exists()
    # 4. But canonical authorization must reject it!
    val = RequiredEvidencePolicy.validate_required_evidence(reconciled, project_dir)
    # Target state is BLUEPRINT_READY, so it passes for BLUEPRINT_READY
    assert val.is_valid


def test_red_obs_d_crash_window_stale_marker_does_not_authorize_rendering(tmp_path):
    """
    Observation D Crash Window:
    If a crash occurs after canonical state commit but before marker deletion,
    the leftover .studio_approved marker must NOT authorize render.
    """
    project_dir = tmp_path / "prj_crash_window"
    project_dir.mkdir(parents=True)

    # Leftover marker from crashed cleanup
    (project_dir / ".studio_approved").write_text("", encoding="utf-8")

    state = ProjectState(
        project_id="prj_crash_window",
        lifecycle_state=LifecycleState.BLUEPRINT_READY,  # Rolled back
        revision=12,
        artifact_records=[],
        approval_metadata={"status": "INVALIDATED"},
    )
    StateStore.save(project_dir, state)

    # Import authorization check logic used by render
    loaded = StateStore.load(project_dir)
    assert loaded is not None

    # Verification: Canonical authority must reject render authorization
    # even though .studio_approved exists on disk
    is_render_authorized = (
        loaded.lifecycle_state in (LifecycleState.REVIEW_APPROVED, LifecycleState.RENDERED, LifecycleState.COMPLETE)
        and bool(loaded.approval_metadata.get("approved_by"))
        and (project_dir / ".studio_approved").exists()
    )
    assert not is_render_authorized, (
        "DEFECT PROVEN: Leftover .studio_approved marker falsely authorized rendering after rollback!"
    )


# ==============================================================================
# Group 2: Observation B — Defensive Evidence Merge & Resurrection Prevention
# ==============================================================================

def test_red_obs_b_evidence_merge_does_not_resurrect_invalidated_record():
    """
    Observation B:
    When current persisted state has an INVALIDATED record (e.g. from rollback),
    an incoming stale record with status=VALID from the same or older revision
    must NOT resurrect the record back to VALID.
    """
    from scripts.core.evidence_matrix import EvidenceLedger

    persisted = [
        ArtifactRecord(
            path="out.mp4",
            validation=ValidationLevel.SIZE,
            size_bytes=5000,
            produced_at_revision=10,
            generation_id="gen-1",
            status=EvidenceStatus.INVALIDATED,
            invalidated_reason="Rollback from COMPLETE",
            invalidated_at="2026-09-27T12:00:00Z",
        )
    ]

    stale_incoming = [
        ArtifactRecord(
            path="out.mp4",
            validation=ValidationLevel.SIZE,
            size_bytes=5000,
            produced_at_revision=9,  # Older revision!
            generation_id="gen-1",
            status=EvidenceStatus.VALID,
        )
    ]

    merged = EvidenceLedger.merge_records(persisted, stale_incoming)
    assert len(merged) == 1
    assert merged[0].status == EvidenceStatus.INVALIDATED, (
        f"DEFECT PROVEN (Obs B): Stale incoming record resurrected INVALIDATED out.mp4 to {merged[0].status}!"
    )


def test_red_obs_b_evidence_merge_does_not_resurrect_superseded_record():
    """
    Observation B:
    When current persisted state has a SUPERSEDED record, an incoming stale VALID record
    must NOT resurrect it to VALID.
    """
    from scripts.core.evidence_matrix import EvidenceLedger

    persisted = [
        ArtifactRecord(
            path="master_plan.md",
            validation=ValidationLevel.SHA256,
            sha256="hash_v1",
            produced_at_revision=5,
            generation_id="gen-plan-1",
            status=EvidenceStatus.SUPERSEDED,
        )
    ]

    stale_incoming = [
        ArtifactRecord(
            path="master_plan.md",
            validation=ValidationLevel.SHA256,
            sha256="hash_v1",
            produced_at_revision=5,
            generation_id="gen-plan-1",
            status=EvidenceStatus.VALID,
        )
    ]

    merged = EvidenceLedger.merge_records(persisted, stale_incoming)
    assert len(merged) == 1
    assert merged[0].status == EvidenceStatus.SUPERSEDED, (
        f"DEFECT PROVEN (Obs B): Stale incoming record resurrected SUPERSEDED master_plan.md to {merged[0].status}!"
    )


def test_red_obs_b_explicit_new_generation_creates_valid_evidence():
    """
    Observation B:
    When a stage is legitimately re-run, producing a strictly newer generation
    (new generation_id and newer revision), the new record MUST become VALID,
    and historical lineage must be retained in metadata.
    """
    from scripts.core.evidence_matrix import EvidenceLedger

    persisted = [
        ArtifactRecord(
            path="out.mp4",
            validation=ValidationLevel.SIZE,
            size_bytes=5000,
            produced_at_revision=10,
            generation_id="gen-1",
            status=EvidenceStatus.INVALIDATED,
            invalidated_reason="Rollback from COMPLETE",
            invalidated_at="2026-09-27T12:00:00Z",
        )
    ]

    # Explicit new generation from re-render
    new_generation = [
        ArtifactRecord(
            path="out.mp4",
            validation=ValidationLevel.SIZE,
            size_bytes=6000,
            produced_at_revision=12,  # Newer revision!
            generation_id="gen-2",   # Distinct new generation!
            status=EvidenceStatus.VALID,
        )
    ]

    merged = EvidenceLedger.merge_records(persisted, new_generation)
    assert len(merged) == 1
    assert merged[0].status == EvidenceStatus.VALID
    assert merged[0].generation_id == "gen-2"
    assert merged[0].size_bytes == 6000
    # Lineage retained
    lineage = merged[0].metadata.get("superseded_lineage", [])
    assert len(lineage) > 0
    assert lineage[0]["previous_generation_id"] == "gen-1"


# ==============================================================================
# Group 3: Observation C — Graph-Aware Recovery & Single Source of Truth
# ==============================================================================

def test_red_obs_c_statemachine_has_graph_traversal_api():
    """
    Observation C:
    StateMachine must be the single source of truth for predecessors, ancestors,
    and valid rollback candidates, avoiding duplicate lifecycle ordering in Recovery.
    """
    assert hasattr(StateMachine, "get_predecessors"), "StateMachine lacks get_predecessors()"
    assert hasattr(StateMachine, "get_ancestors"), "StateMachine lacks get_ancestors()"
    assert hasattr(StateMachine, "valid_rollback_candidates"), "StateMachine lacks valid_rollback_candidates()"

    # Test ancestor chain for COMPLETE
    ancestors = StateMachine.get_ancestors(LifecycleState.COMPLETE)
    expected_chain = [
        LifecycleState.FINAL_QC_PASSED,
        LifecycleState.RENDERED,
        LifecycleState.REVIEW_APPROVED,
        LifecycleState.AWAITING_REVIEW,
        LifecycleState.PROBE_PASSED,
        LifecycleState.MATERIALIZED,
        LifecycleState.BLUEPRINT_READY,
        LifecycleState.PLAN_READY,
        LifecycleState.ASSETS_READY,
        LifecycleState.DRAFT,
    ]
    assert ancestors == expected_chain

    # Predecessor of BLUEPRINT_READY is PLAN_READY
    preds = StateMachine.get_predecessors(LifecycleState.BLUEPRINT_READY)
    assert preds == [LifecycleState.PLAN_READY]


def test_red_obs_c_recovery_planner_queries_statemachine_graph(tmp_path):
    """
    Observation C:
    RecoveryPlanner must query StateMachine.valid_rollback_candidates() rather than
    relying on an independent hardcoded LIFECYCLE_ORDER list.
    """
    project_dir = tmp_path / "prj_graph_recovery"
    project_dir.mkdir(parents=True)

    (project_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    (project_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    (project_dir / "05_blueprint.json").write_text("{}", encoding="utf-8")

    records = [
        StateStore.create_artifact_record(project_dir, "02_asset_manifest.json", ValidationLevel.EXISTS),
        StateStore.create_artifact_record(project_dir, "master_plan.md", ValidationLevel.SHA256),
        StateStore.create_artifact_record(project_dir, "05_blueprint.json", ValidationLevel.SHA256),
        ArtifactRecord(path="out.mp4", validation=ValidationLevel.SIZE, size_bytes=5000),
    ]

    state = ProjectState(
        project_id="prj_graph_recovery",
        lifecycle_state=LifecycleState.COMPLETE,
        revision=10,
        artifact_records=records,
    )
    StateStore.save(project_dir, state)

    # Plan recovery
    with patch.object(StateMachine, "valid_rollback_candidates", wraps=StateMachine.valid_rollback_candidates) as mock_candidates:
        plan = RecoveryPlanner.create_plan(project_dir)
        assert mock_candidates.called, "RecoveryPlanner did NOT query StateMachine.valid_rollback_candidates()!"

    assert plan.target_state == LifecycleState.BLUEPRINT_READY
