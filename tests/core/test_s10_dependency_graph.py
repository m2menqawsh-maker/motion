"""
Core Tests for S10: Artifact Dependency Graph, InvalidationPlan & ArtifactService.
Tests:
- Test 4: Blueprint change invalidates downstream review
- Test 5: Blueprint change invalidates render/QC evidence
- Test 6: Manifest change produces correct downstream invalidation plan
- Test 7: Unrelated artifact change does not invalidate everything (no over-invalidation)
- Test 8: Invalidation survives restart
- Test 9: Recovery uses same dependency truth
- Test 10: ReviewService uses/integrates canonical dependency invalidation
- Test 31: Transitive invalidation exact set
- Test 32: No over-invalidation
- Test 33: Idempotent invalidation
- Test 34: Concurrency (stale revision rejected with CAS conflict / StateConflictError)
- Graph validation tests (DAG, acyclic, deterministic, no orphan nodes)
- Integration with RequiredEvidence & RetryContext
"""
import pytest
import json
from pathlib import Path
from scripts.core.state_model import (
    ProjectState,
    LifecycleState,
    ArtifactRecord,
    ValidationLevel,
    EvidenceStatus,
    ReviewBundle,
    ReviewDecision,
    ReviewDecisionType,
)
from scripts.core.state_store import StateStore, StateConflictError
from scripts.core.dependency_graph import (
    ArtifactDependencyGraph,
    ArtifactKind,
    DependencyEdgeType,
    InvalidationPlan,
)
from scripts.core.artifact_service import ArtifactService
from scripts.core.evidence_matrix import RequiredEvidencePolicy
from scripts.core.review_service import ReviewService, RenderNotAuthorizedError


@pytest.fixture
def project_setup(tmp_path):
    proj_dir = tmp_path / "prj_s10_test"
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    (proj_dir / "02_asset_manifest.json").write_text(json.dumps({"assets": []}), encoding="utf-8")
    (proj_dir / "01_plan.md").write_text("# Plan", encoding="utf-8")
    (proj_dir / "04_timings.json").write_text(json.dumps({"timings": []}), encoding="utf-8")
    (proj_dir / "05_blueprint.json").write_text(json.dumps({"scenes": [{"id": "s1"}]}), encoding="utf-8")
    (proj_dir / "media_map.json").write_text(json.dumps({"assets": {}}), encoding="utf-8")
    (proj_dir / "probe_qc_report.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    (proj_dir / "out.mp4").write_text("dummy video content", encoding="utf-8")
    (proj_dir / "08_qc_report.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    (proj_dir / ".studio_approved").write_text("APPROVED by reviewer_1", encoding="utf-8")

    # Initial state
    state = ProjectState(
        project_id="prj_s10_test",
        revision=10,
        lifecycle_state=LifecycleState.REVIEW_APPROVED,
        approval_metadata={"approved_by": "reviewer_1", "status": "APPROVED"},
        artifact_records=[
            ArtifactRecord(
                path="02_asset_manifest.json",
                validation=ValidationLevel.EXISTS,
                status=EvidenceStatus.VALID,
                stage="ASSETS_READY",
            ),
            ArtifactRecord(
                path="01_plan.md",
                validation=ValidationLevel.SHA256,
                sha256=StateStore._compute_sha256(proj_dir / "01_plan.md"),
                status=EvidenceStatus.VALID,
                stage="PLAN_READY",
            ),
            ArtifactRecord(
                path="04_timings.json",
                validation=ValidationLevel.SHA256,
                sha256=StateStore._compute_sha256(proj_dir / "04_timings.json"),
                status=EvidenceStatus.VALID,
                stage="TIMINGS_EXTRACTED",
            ),
            ArtifactRecord(
                path="05_blueprint.json",
                validation=ValidationLevel.SHA256,
                sha256=StateStore._compute_sha256(proj_dir / "05_blueprint.json"),
                status=EvidenceStatus.VALID,
                stage="BLUEPRINT_GENERATED",
            ),
            ArtifactRecord(
                path="media_map.json",
                validation=ValidationLevel.EXISTS,
                status=EvidenceStatus.VALID,
                stage="MEDIA_MATERIALIZED",
            ),
            ArtifactRecord(
                path="probe_qc_report.json",
                validation=ValidationLevel.SHA256,
                sha256=StateStore._compute_sha256(proj_dir / "probe_qc_report.json"),
                status=EvidenceStatus.VALID,
                stage="PROBE_PASSED",
            ),
        ],
    )
    # Create active review bundle and decision
    state.lifecycle_state = LifecycleState.AWAITING_REVIEW
    StateStore.save(proj_dir, state)

    bundle = ReviewService.create_review_bundle(proj_dir)
    from scripts.core.review_service import create_local_trusted_principal
    principal = create_local_trusted_principal("reviewer_1")
    decision = ReviewService.approve(
        project_dir=proj_dir,
        bundle_id=bundle.review_bundle_id,
        principal=principal,
        reason="Approved for testing",
    )

    return proj_dir


def test_graph_structural_validation():
    """Graph validation: DAG, acyclic, all nodes registered, deterministic."""
    graph = ArtifactDependencyGraph()
    graph.validate_graph()

    # Verify key nodes exist
    for kind in [
        ArtifactKind.MANIFEST,
        ArtifactKind.PLAN,
        ArtifactKind.TIMINGS,
        ArtifactKind.BLUEPRINT,
        ArtifactKind.MATERIALIZED_MEDIA,
        ArtifactKind.PROBE_REPORT,
        ArtifactKind.REVIEW_BUNDLE,
        ArtifactKind.REVIEW_DECISION,
        ArtifactKind.RENDER_OUTPUT,
        ArtifactKind.FINAL_QC,
        ArtifactKind.COMPLETE,
    ]:
        assert kind in graph.nodes


def test_transitive_invalidation_exact_set():
    """Test 31: Blueprint changes -> exact expected downstream set."""
    graph = ArtifactDependencyGraph()
    dependents = graph.get_transitive_dependents(ArtifactKind.BLUEPRINT)

    expected = {
        ArtifactKind.MATERIALIZED_MEDIA,
        ArtifactKind.PROBE_REPORT,
        ArtifactKind.REVIEW_BUNDLE,
        ArtifactKind.REVIEW_DECISION,
        ArtifactKind.RENDER_OUTPUT,
        ArtifactKind.FINAL_QC,
        ArtifactKind.COMPLETE,
    }
    assert dependents == expected, f"Expected {expected}, got {dependents}"

    # Upstream must not be in dependents
    assert ArtifactKind.PLAN not in dependents
    assert ArtifactKind.TIMINGS not in dependents
    assert ArtifactKind.MANIFEST not in dependents


def test_manifest_transitive_invalidation_exact_set():
    """Test 6: Manifest changes -> exact expected downstream set."""
    graph = ArtifactDependencyGraph()
    dependents = graph.get_transitive_dependents(ArtifactKind.MANIFEST)

    expected = {
        ArtifactKind.MATERIALIZED_MEDIA,
        ArtifactKind.PROBE_REPORT,
        ArtifactKind.REVIEW_BUNDLE,
        ArtifactKind.REVIEW_DECISION,
        ArtifactKind.RENDER_OUTPUT,
        ArtifactKind.FINAL_QC,
        ArtifactKind.COMPLETE,
    }
    assert dependents == expected, f"Expected {expected}, got {dependents}"
    assert ArtifactKind.PLAN not in dependents
    assert ArtifactKind.TIMINGS not in dependents
    assert ArtifactKind.BLUEPRINT not in dependents


def test_blueprint_change_invalidates_downstream_review(project_setup):
    """Test 4: Mutating blueprint via ArtifactService invalidates review."""
    proj_dir = project_setup
    state_before = StateStore.load(proj_dir)
    assert state_before.get_active_review_decision().decision == ReviewDecisionType.APPROVED

    # Mutate blueprint via canonical ArtifactService
    new_bp_content = json.dumps({"scenes": [{"id": "s1_modified"}]})
    plan = ArtifactService.mutate_artifact(
        project_dir=proj_dir,
        artifact_kind=ArtifactKind.BLUEPRINT,
        new_content=new_bp_content,
        reason="Updated scene 1 layout",
    )

    assert ArtifactKind.BLUEPRINT.value in plan.changed_artifacts
    assert ArtifactKind.REVIEW_BUNDLE.value in plan.invalidated_artifacts or plan.invalidated_review_bundles
    assert ArtifactKind.REVIEW_DECISION.value in plan.invalidated_artifacts or plan.invalidated_decisions

    state_after = StateStore.load(proj_dir)
    active_bundle = state_after.get_active_review_bundle()
    active_decision = state_after.get_active_review_decision()

    assert active_bundle.status == "INVALIDATED"
    assert active_decision.decision == ReviewDecisionType.INVALIDATED
    assert not (proj_dir / ".studio_approved").exists(), "Stale .studio_approved must be removed"

    # ReviewService assert_render_authorized must fail closed
    with pytest.raises(RenderNotAuthorizedError):
        ReviewService.assert_render_authorized(proj_dir)


def test_blueprint_change_invalidates_render_qc_evidence(project_setup):
    """Test 5: Blueprint change invalidates render/QC and probe evidence records."""
    proj_dir = project_setup
    # Add render and final QC evidence to state
    state = StateStore.load(proj_dir)
    state.record_evidence(ArtifactRecord(
        path="out.mp4",
        validation=ValidationLevel.SIZE,
        size_bytes=100,
        status=EvidenceStatus.VALID,
        stage="RENDERED",
    ))
    state.record_evidence(ArtifactRecord(
        path="08_qc_report.json",
        validation=ValidationLevel.SHA256,
        sha256="fake_sha",
        status=EvidenceStatus.VALID,
        stage="FINAL_QC_PASSED",
    ))
    StateStore.save(proj_dir, state)

    # Mutate blueprint
    ArtifactService.mutate_artifact(
        project_dir=proj_dir,
        artifact_kind=ArtifactKind.BLUEPRINT,
        new_content=json.dumps({"scenes": [{"id": "s2"}]}),
        reason="Blueprint scene change",
    )

    state_after = StateStore.load(proj_dir)
    rec_probe = state_after.get_artifact_record("probe_qc_report.json")
    rec_render = state_after.get_artifact_record("out.mp4")
    rec_qc = state_after.get_artifact_record("08_qc_report.json")

    assert rec_probe.status == EvidenceStatus.INVALIDATED
    assert rec_render.status == EvidenceStatus.INVALIDATED
    assert rec_qc.status == EvidenceStatus.INVALIDATED
    assert "Blueprint scene change" in rec_probe.invalidated_reason


def test_manifest_change_produces_correct_downstream_invalidation_plan(project_setup):
    """Test 6: Manifest change produces correct downstream invalidation plan."""
    proj_dir = project_setup
    plan = ArtifactService.mutate_artifact(
        project_dir=proj_dir,
        artifact_kind=ArtifactKind.MANIFEST,
        new_content=json.dumps({"assets": [{"id": "logo", "path": "logo.png"}]}),
        reason="Added logo asset",
    )

    # Plan should invalidate materialized media, probe, review, render, QC
    invalidated_kinds = set(plan.invalidated_artifacts)
    assert ArtifactKind.MATERIALIZED_MEDIA.value in invalidated_kinds
    assert ArtifactKind.PROBE_REPORT.value in invalidated_kinds

    # Blueprint and timings and plan must NOT be invalidated!
    assert ArtifactKind.BLUEPRINT.value not in invalidated_kinds
    assert ArtifactKind.PLAN.value not in invalidated_kinds
    assert ArtifactKind.TIMINGS.value not in invalidated_kinds


def test_unrelated_artifact_change_does_not_invalidate_everything(project_setup):
    """Test 7 & 32: Unrelated artifact change does not cause over-invalidation."""
    proj_dir = project_setup

    # Mutating final QC should NOT invalidate blueprint, timings, plan, probe, or media map!
    plan = ArtifactService.mutate_artifact(
        project_dir=proj_dir,
        artifact_kind=ArtifactKind.FINAL_QC,
        new_content=json.dumps({"status": "PASS", "checks": 10}),
        reason="Updated QC report metrics",
    )

    invalidated_kinds = set(plan.invalidated_artifacts)
    assert ArtifactKind.PLAN.value not in invalidated_kinds
    assert ArtifactKind.TIMINGS.value not in invalidated_kinds
    assert ArtifactKind.BLUEPRINT.value not in invalidated_kinds
    assert ArtifactKind.MATERIALIZED_MEDIA.value not in invalidated_kinds
    assert ArtifactKind.PROBE_REPORT.value not in invalidated_kinds
    assert ArtifactKind.REVIEW_BUNDLE.value not in invalidated_kinds


def test_invalidation_survives_restart(project_setup):
    """Test 8: Invalidation persists across process reload."""
    proj_dir = project_setup

    ArtifactService.mutate_artifact(
        project_dir=proj_dir,
        artifact_kind=ArtifactKind.BLUEPRINT,
        new_content=json.dumps({"scenes": [{"id": "s3"}]}),
        reason="Restart test change",
    )

    # Fresh reload from disk
    reloaded_state = StateStore.load(proj_dir)
    probe_rec = reloaded_state.get_artifact_record("probe_qc_report.json")
    assert probe_rec is not None
    assert probe_rec.status == EvidenceStatus.INVALIDATED
    assert probe_rec.invalidated_reason == "Restart test change"
    assert reloaded_state.get_active_review_bundle().status == "INVALIDATED"


def test_idempotent_invalidation(project_setup):
    """Test 33: Applying invalidation plan repeatedly is safe and idempotent."""
    proj_dir = project_setup

    # Compute plan
    state = StateStore.load(proj_dir)
    graph = ArtifactDependencyGraph()
    plan = graph.compute_invalidation_plan(
        project_state=state,
        changed_nodes=[ArtifactKind.BLUEPRINT],
        reason="Idempotency test",
    )

    # First apply
    ArtifactService.apply_invalidation_plan(proj_dir, plan)
    state1 = StateStore.load(proj_dir)
    rev1 = state1.revision

    # Second apply with updated expected revision
    plan.source_revision = rev1
    ArtifactService.apply_invalidation_plan(proj_dir, plan)
    state2 = StateStore.load(proj_dir)

    # Both runs keep probe invalidated without duplicated records
    probe_records = [r for r in state2.artifact_records if r.path == "probe_qc_report.json"]
    assert len(probe_records) == 1
    assert probe_records[0].status == EvidenceStatus.INVALIDATED


def test_concurrency_stale_invalidation_plan_raises_conflict(project_setup):
    """Test 34: Stale InvalidationPlan on revision N fails if state is already N+1."""
    proj_dir = project_setup
    state = StateStore.load(proj_dir)

    graph = ArtifactDependencyGraph()
    plan = graph.compute_invalidation_plan(
        project_state=state,
        changed_nodes=[ArtifactKind.BLUEPRINT],
        reason="Concurrent writer A",
    )
    assert plan.source_revision == state.revision

    # Concurrent writer B increments revision
    def bump_rev(copy):
        copy.run_metadata["bumped"] = True
    StateStore.atomic_update(proj_dir, expected_revision=state.revision, mutator=bump_rev)

    # Writer A attempts to apply plan with old source_revision
    with pytest.raises(StateConflictError):
        ArtifactService.apply_invalidation_plan(proj_dir, plan)


def test_recovery_uses_same_dependency_truth(project_setup):
    """Test 9: RecoveryPlanner relies on centralized dependency graph / semantic invalidation."""
    from scripts.core.recovery_engine import RecoveryPlanner
    proj_dir = project_setup

    # Corrupt probe on disk
    (proj_dir / "probe_qc_report.json").unlink()

    state = StateStore.load(proj_dir)
    plan = RecoveryPlanner.create_plan(proj_dir, state)

    # Must rollback to a valid predecessor before probe
    assert plan.target_state in (LifecycleState.ASSETS_READY, LifecycleState.PLAN_READY, LifecycleState.BLUEPRINT_READY, LifecycleState.MATERIALIZED)
    assert "probe_qc_report.json" in plan.invalidated_evidence_paths


def test_review_service_integrates_canonical_dependency_invalidation(project_setup):
    """Test 10: ReviewService checks hashes linked to canonical dependency graph nodes."""
    proj_dir = project_setup
    # ReviewService uses graph-governed artifacts
    governed_paths = ArtifactDependencyGraph.get_review_governed_paths()
    assert "05_blueprint.json" in governed_paths
    assert "media_map.json" in governed_paths
    assert "probe_qc_report.json" in governed_paths
    assert "02_asset_manifest.json" in governed_paths


def test_required_evidence_fails_when_downstream_invalidated(project_setup):
    """RequiredEvidencePolicy does not accept INVALIDATED evidence."""
    proj_dir = project_setup
    ArtifactService.mutate_artifact(
        project_dir=proj_dir,
        artifact_kind=ArtifactKind.BLUEPRINT,
        new_content=json.dumps({"scenes": [{"id": "s_new"}]}),
        reason="Required evidence test",
    )

    state = StateStore.load(proj_dir)
    res = RequiredEvidencePolicy.validate_required_evidence(state, proj_dir)
    assert not res.is_valid, "State should be invalid when required evidence is INVALIDATED"


# ==============================================================================
# S10 Hardening Patch Regressions: .studio_approved Legacy Status & Cleanup
# ==============================================================================

def test_studio_approved_removal_does_not_affect_valid_decision(project_setup):
    """
    Regression Test 1: Removing .studio_approved entirely does not alter the validity
    of a canonically approved ReviewDecision. The canonical authority is ReviewService +
    ReviewDecision in ProjectState, NOT the legacy marker on disk.
    """
    proj_dir = project_setup
    # Verify initially authorized
    auth_before = ReviewService.assert_render_authorized(proj_dir)
    assert auth_before.is_authorized is True

    # Remove the legacy marker completely
    marker = proj_dir / ".studio_approved"
    if marker.exists():
        marker.unlink()
    assert not marker.exists(), "Legacy marker must be absent"

    # Authorization must STILL succeed because canonical state is intact
    auth_after = ReviewService.assert_render_authorized(proj_dir)
    assert auth_after.is_authorized is True

    # State decision remains APPROVED
    state = StateStore.load(proj_dir)
    decision = state.get_active_review_decision()
    assert decision is not None
    assert decision.decision == ReviewDecisionType.APPROVED


def test_studio_approved_alone_cannot_create_decision_or_authorize_render(tmp_path):
    """
    Regression Test 2: Presence of .studio_approved alone on disk does NOT create a
    ReviewDecision in ProjectState and does NOT authorize render.
    """
    proj_dir = tmp_path / "prj_marker_only"
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Initial state without any approved review decision
    state = ProjectState(
        project_id="prj_marker_only",
        revision=1,
        lifecycle_state=LifecycleState.AWAITING_REVIEW,
        artifact_records=[],
    )
    StateStore.save(proj_dir, state)

    # Place forged/manual .studio_approved marker on disk
    marker = proj_dir / ".studio_approved"
    marker.write_text(json.dumps({"approved_by": "untrusted_actor"}), encoding="utf-8")
    assert marker.exists()

    # Verify no review decision exists in state
    loaded_state = StateStore.load(proj_dir)
    assert loaded_state.get_active_review_decision() is None

    # ReviewService must fail closed: render is NOT authorized
    with pytest.raises(RenderNotAuthorizedError):
        ReviewService.assert_render_authorized(proj_dir)


def test_artifact_service_invalidation_resilient_to_marker_unlink_oserror(project_setup, caplog):
    """
    Regression Test 3: If unlinking .studio_approved fails with OSError (e.g. read-only disk),
    the atomic CAS state commit remains committed and authoritative:
    - ReviewDecision and ReviewBundle remain INVALIDATED
    - State revision remains incremented
    - Render authorization remains denied
    - Stale marker does NOT resurrect validity
    - A structured warning is logged by ArtifactService
    """
    import logging
    from unittest.mock import patch

    proj_dir = project_setup
    assert (proj_dir / ".studio_approved").exists()
    state_before = StateStore.load(proj_dir)
    rev_before = state_before.revision

    orig_unlink = Path.unlink

    def failing_unlink(self, *args, **kwargs):
        if self.name == ".studio_approved":
            raise OSError("Simulated read-only disk: unlink failed")
        return orig_unlink(self, *args, **kwargs)

    with caplog.at_level(logging.WARNING, logger="clean_video.artifact_service"):
        with patch.object(Path, "unlink", failing_unlink):
            plan = ArtifactService.mutate_artifact(
                project_dir=proj_dir,
                artifact_kind=ArtifactKind.BLUEPRINT,
                new_content=json.dumps({"scenes": [{"id": "s_oserror"}]}),
                reason="Unlink failure resilience test",
            )

    # 1. Mutation succeeded without escaping exception
    assert plan is not None

    # 2. State commit succeeded and revision incremented
    state_after = StateStore.load(proj_dir)
    assert state_after.revision == rev_before + 1

    # 3. Canonical decisions and bundles are INVALIDATED
    assert state_after.get_active_review_bundle().status == "INVALIDATED"
    assert state_after.get_active_review_decision().decision == ReviewDecisionType.INVALIDATED

    # 4. Marker is still on disk because unlink was mocked to fail
    assert (proj_dir / ".studio_approved").exists()

    # 5. Stale marker grants ZERO authority; render must fail closed
    with pytest.raises(RenderNotAuthorizedError):
        ReviewService.assert_render_authorized(proj_dir)

    # 6. Structured warning logged
    assert "Best-effort cleanup failed to unlink legacy marker '.studio_approved'" in caplog.text
    assert "State invalidation remains committed and authoritative." in caplog.text


def test_artifact_service_crash_after_state_commit_leaves_system_secure(project_setup):
    """
    Regression Test 4: Crash window test. If a crash or interruption occurs after state commit
    but before marker cleanup:
    - The committed revision and INVALIDATED status persist on disk
    - The leftover marker does NOT grant authorization
    - Render remains strictly blocked
    """
    proj_dir = project_setup
    assert (proj_dir / ".studio_approved").exists()
    state = StateStore.load(proj_dir)
    rev_before = state.revision

    graph = ArtifactDependencyGraph()
    plan = graph.compute_invalidation_plan(
        project_state=state,
        changed_nodes=[ArtifactKind.BLUEPRINT],
        reason="Crash window simulation",
    )

    # Simulate crash right after StateStore.atomic_update:
    # We apply the state update mutator directly (as atomic_update does), but simulate
    # process termination before the marker cleanup loop can run.
    def mutator(working_copy):
        for b in working_copy.review_bundles:
            if b.status == "ACTIVE":
                b.invalidate("Crash window simulation")
        for d in working_copy.review_decisions:
            if d.decision == ReviewDecisionType.APPROVED:
                d.invalidate("Crash window simulation")
        working_copy.sync_approval_metadata()

    StateStore.atomic_update(
        project_dir=proj_dir,
        expected_revision=state.revision,
        mutator=mutator,
    )

    # System "restarts": reload state
    reloaded_state = StateStore.load(proj_dir)
    assert reloaded_state.revision == rev_before + 1
    assert reloaded_state.get_active_review_bundle().status == "INVALIDATED"
    assert reloaded_state.get_active_review_decision().decision == ReviewDecisionType.INVALIDATED

    # Stale marker was NOT cleaned up due to crash
    assert (proj_dir / ".studio_approved").exists()

    # Authorization must fail closed despite marker existing
    with pytest.raises(RenderNotAuthorizedError):
        ReviewService.assert_render_authorized(proj_dir)

