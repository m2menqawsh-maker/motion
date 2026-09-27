"""
S09 Test Suite: ReviewService, Review Bundles & Canonical Render Authorization.

Validates:
1. Forged identity rejection (actor strictly from server-verified Principal).
2. Approval without AWAITING_REVIEW rejected.
3. Approval without valid ReviewBundle rejected.
4. Blueprint changes after approval invalidates approval and blocks render.
5. Probe QC changes after approval blocks render.
6. Media map changes after approval blocks render.
7. Stale revision approval fails with CAS conflict.
8. Rejection is real: recorded, blocks render, preserves history.
9. New review bundle after change succeeds.
10. Restart persistence: bundles & decisions survive reload.
11. .studio_approved marker alone is non-authoritative.
12. Recovery rollback invalidates review while preserving history.
13. Safe retry cannot use invalidated review.
14. Canonical assert_render_authorized unified across pipeline and render.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from scripts.core.state_model import LifecycleState, ProjectState, ValidationLevel
from scripts.core.state_store import StateStore, StateConflictError
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.failure_model import FailureCode

# Domain authority to be implemented
from scripts.core.review_service import (
    ReviewService,
    ReviewBundle,
    ReviewDecision,
    ReviewDecisionType,
    ReviewError,
    ReviewIdentityInvalidError,
    ReviewNotAllowedError,
    ReviewBundleMissingError,
    ReviewBundleStaleError,
    RenderNotAuthorizedError,
    assert_render_authorized,
)


@pytest.fixture
def review_env(tmp_path):
    """Sets up a complete project fixture ready for review testing."""
    proj_dir = tmp_path / "projects" / "test_rev_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    project_id = "test_rev_proj"

    # Setup standard required files
    (proj_dir / "02_asset_manifest.json").write_text(
        json.dumps({"assets": ["audio.mp3", "video.mp4"]}, indent=2), encoding="utf-8"
    )
    (proj_dir / "master_plan.md").write_text("# Master Plan\nTest plan content\n", encoding="utf-8")
    (proj_dir / "05_blueprint.json").write_text(
        json.dumps({"version": 1, "scenes": [{"id": "scene_1"}]}, indent=2), encoding="utf-8"
    )
    (proj_dir / "media_map.json").write_text(
        json.dumps({"scene_1": {"bg": "assets/bg.jpg"}}, indent=2), encoding="utf-8"
    )
    (proj_dir / "probe_qc_report.json").write_text(
        json.dumps({"status": "pass", "probes": [{"frame": 0, "status": "pass"}]}, indent=2), encoding="utf-8"
    )
    (proj_dir / "contact_sheet.png").write_bytes(b"\x89PNG\r\n\x1a\nfake_image_bytes")

    # Initialize state at AWAITING_REVIEW
    state = StateStore.create(proj_dir, project_id)
    state.lifecycle_state = LifecycleState.AWAITING_REVIEW
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "02_asset_manifest.json", ValidationLevel.SHA256))
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "master_plan.md", ValidationLevel.SHA256))
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "05_blueprint.json", ValidationLevel.SHA256))
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "media_map.json", ValidationLevel.EXISTS))
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "probe_qc_report.json", ValidationLevel.EXISTS))
    StateStore.save(proj_dir, state)

    trusted_reviewer = Principal(
        principal_id="reviewer_alice",
        principal_type=PrincipalType.HUMAN,
        roles={Role.REVIEWER},
        project_scopes={"test_rev_proj": {Role.REVIEWER}},
        auth_method="SESSION"
    )

    non_reviewer = Principal(
        principal_id="viewer_bob",
        principal_type=PrincipalType.HUMAN,
        roles={Role.VIEWER},
        project_scopes={"test_rev_proj": {Role.VIEWER}},
        auth_method="SESSION"
    )

    return {
        "proj_dir": proj_dir,
        "project_id": project_id,
        "trusted_reviewer": trusted_reviewer,
        "non_reviewer": non_reviewer,
    }


def test_red_01_forged_identity_rejected(review_env):
    """User-supplied approved_by string must NOT be accepted as authority; principal is required."""
    proj_dir = review_env["proj_dir"]

    # 1. Unauthenticated / anonymous principal must be rejected
    anon = Principal(
        principal_id="anonymous",
        principal_type=PrincipalType.ANONYMOUS,
        roles=set(),
        project_scopes={},
        auth_method="NONE"
    )
    bundle = ReviewService.create_review_bundle(proj_dir)

    with pytest.raises(ReviewIdentityInvalidError):
        ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=anon)

    # 2. Non-reviewer principal must be rejected even if attempting to pass approved_by="admin"
    with pytest.raises(ReviewIdentityInvalidError):
        ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=review_env["non_reviewer"])


def test_red_02_approval_without_awaiting_review_rejected(review_env):
    """Approval attempted when project is not in AWAITING_REVIEW must be rejected."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle = ReviewService.create_review_bundle(proj_dir)

    state = StateStore.load(proj_dir)
    state.lifecycle_state = LifecycleState.BLUEPRINT_READY
    StateStore.save(proj_dir, state)

    with pytest.raises(ReviewNotAllowedError):
        ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=reviewer)


def test_red_03_approval_without_valid_review_bundle_rejected(review_env):
    """Approving without an existing valid ReviewBundle must be rejected."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    with pytest.raises(ReviewBundleMissingError):
        ReviewService.approve(proj_dir, "non_existent_bundle_id", principal=reviewer)


def test_red_04_blueprint_changes_after_approval_invalidates_and_blocks_render(review_env):
    """Modifying 05_blueprint.json after approval invalidates review and blocks render."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle = ReviewService.create_review_bundle(proj_dir)
    ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=reviewer)

    # Legacy marker on disk must NOT protect against invalidation
    (proj_dir / ".studio_approved").write_text("", encoding="utf-8")

    # Authorize render right now should pass
    auth_result = assert_render_authorized(proj_dir)
    assert auth_result.is_authorized is True

    # Mutate blueprint on disk
    bp_data = json.loads((proj_dir / "05_blueprint.json").read_text(encoding="utf-8"))
    bp_data["scenes"].append({"id": "scene_tampered"})
    (proj_dir / "05_blueprint.json").write_text(json.dumps(bp_data), encoding="utf-8")

    # Render authorization must now fail closed
    with pytest.raises(RenderNotAuthorizedError) as exc_info:
        assert_render_authorized(proj_dir)

    assert exc_info.value.code in (FailureCode.RENDER_NOT_AUTHORIZED, FailureCode.REVIEW_BUNDLE_STALE)


def test_red_05_probe_report_changes_after_approval_blocks_render(review_env):
    """Modifying probe_qc_report.json after approval invalidates review and blocks render."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle = ReviewService.create_review_bundle(proj_dir)
    ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=reviewer)

    # Mutate probe report
    (proj_dir / "probe_qc_report.json").write_text(
        json.dumps({"status": "fail", "tampered": True}), encoding="utf-8"
    )

    with pytest.raises(RenderNotAuthorizedError):
        assert_render_authorized(proj_dir)


def test_red_06_media_map_changes_after_approval_blocks_render(review_env):
    """Modifying media_map.json after approval invalidates review and blocks render."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle = ReviewService.create_review_bundle(proj_dir)
    ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=reviewer)

    # Mutate media map
    (proj_dir / "media_map.json").write_text(
        json.dumps({"scene_1": {"bg": "assets/different_bg.jpg"}}), encoding="utf-8"
    )

    with pytest.raises(RenderNotAuthorizedError):
        assert_render_authorized(proj_dir)


def test_red_07_stale_revision_approval_fails_with_conflict(review_env):
    """Approving a bundle whose revision is stale relative to state revision must fail with CAS conflict."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    # Bundle created at revision N
    bundle = ReviewService.create_review_bundle(proj_dir)

    # State advances to revision N+1 (e.g. editor updated metadata or artifacts)
    StateStore.atomic_update(
        proj_dir,
        expected_revision=StateStore.load(proj_dir).revision,
        mutator=lambda s: s.run_metadata.update({"editor_edit": "true"}),
    )

    # Approve with expected revision N must fail CAS
    with pytest.raises((StateConflictError, ReviewBundleStaleError)):
        ReviewService.approve(
            proj_dir,
            bundle.review_bundle_id,
            principal=reviewer,
            expected_revision=bundle.state_revision,
        )


def test_red_08_rejection_is_real_and_blocks_render(review_env):
    """Rejection records real decision, blocks render, and preserves history."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle = ReviewService.create_review_bundle(proj_dir)
    ReviewService.reject(
        proj_dir,
        bundle.review_bundle_id,
        principal=reviewer,
        reason="Visual defects in scene 1",
    )

    state = StateStore.load(proj_dir)
    assert len(state.review_decisions) == 1
    decision = state.review_decisions[0]
    assert decision.decision == ReviewDecisionType.REJECTED
    assert decision.reason == "Visual defects in scene 1"
    assert decision.actor_id == reviewer.principal_id

    # Render authorization must fail
    with pytest.raises(RenderNotAuthorizedError):
        assert_render_authorized(proj_dir)


def test_red_09_new_review_after_change_succeeds(review_env):
    """After changes invalidate bundle A, creating and approving bundle B authorizes render."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle_a = ReviewService.create_review_bundle(proj_dir)
    ReviewService.approve(proj_dir, bundle_a.review_bundle_id, principal=reviewer)

    # Edit blueprint
    (proj_dir / "05_blueprint.json").write_text(
        json.dumps({"version": 2, "scenes": [{"id": "scene_1_fixed"}]}), encoding="utf-8"
    )

    # Render is blocked
    with pytest.raises(RenderNotAuthorizedError):
        assert_render_authorized(proj_dir)

    # Reset to AWAITING_REVIEW for new review
    state = StateStore.load(proj_dir)
    state.lifecycle_state = LifecycleState.AWAITING_REVIEW
    StateStore.save(proj_dir, state)

    # Create bundle B with new hash
    bundle_b = ReviewService.create_review_bundle(proj_dir)
    assert bundle_b.review_bundle_id != bundle_a.review_bundle_id
    assert bundle_b.blueprint_sha256 != bundle_a.blueprint_sha256

    # Approve bundle B
    ReviewService.approve(proj_dir, bundle_b.review_bundle_id, principal=reviewer)

    # Now render is authorized
    auth_result = assert_render_authorized(proj_dir)
    assert auth_result.is_authorized is True
    assert auth_result.bundle_id == bundle_b.review_bundle_id


def test_red_10_restart_persistence(review_env):
    """Review bundles and decisions survive complete reload from disk."""
    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle = ReviewService.create_review_bundle(proj_dir)
    ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=reviewer)

    # Reload fresh from disk
    reloaded = StateStore.load(proj_dir)
    assert len(reloaded.review_bundles) >= 1
    assert len(reloaded.review_decisions) >= 1
    assert reloaded.active_review_bundle_id == bundle.review_bundle_id

    # Verify authorization works from disk state
    auth_result = assert_render_authorized(proj_dir)
    assert auth_result.is_authorized is True


def test_red_11_studio_approved_alone_does_not_authorize_render(review_env):
    """Presence of .studio_approved marker without valid ReviewDecision must fail authorization."""
    proj_dir = review_env["proj_dir"]

    # Touch .studio_approved marker
    (proj_dir / ".studio_approved").write_text("", encoding="utf-8")

    # No approved ReviewDecision exists
    with pytest.raises(RenderNotAuthorizedError):
        assert_render_authorized(proj_dir)


def test_red_12_recovery_rollback_invalidates_review_preserving_history(review_env):
    """Recovery rollback before REVIEW_APPROVED invalidates review decision without deleting history."""
    from scripts.core.recovery_engine import RecoveryService

    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle = ReviewService.create_review_bundle(proj_dir)
    ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=reviewer)

    state_before = StateStore.load(proj_dir)
    assert state_before.lifecycle_state == LifecycleState.REVIEW_APPROVED

    # Trigger recovery rollback to MATERIALIZED
    plan = RecoveryService.create_plan(proj_dir, target_state=LifecycleState.MATERIALIZED, reason="Testing S09 rollback")
    RecoveryService.apply_plan(proj_dir, plan)

    state_after = StateStore.load(proj_dir)
    assert state_after.lifecycle_state == LifecycleState.MATERIALIZED
    assert len(state_after.review_decisions) >= 1
    # Active decision must be marked INVALIDATED
    latest_decision = state_after.review_decisions[-1]
    assert latest_decision.decision == ReviewDecisionType.INVALIDATED

    # Render is blocked
    with pytest.raises(RenderNotAuthorizedError):
        assert_render_authorized(proj_dir)


def test_red_13_safe_retry_cannot_use_invalidated_review(review_env):
    """RetryPolicy rejects render operation retry if review decision is invalidated."""
    from scripts.core.retry_policy import RetryPolicy, RetryContext

    proj_dir = review_env["proj_dir"]
    reviewer = review_env["trusted_reviewer"]

    bundle = ReviewService.create_review_bundle(proj_dir)
    ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=reviewer)

    # Invalidate by tampering blueprint
    (proj_dir / "05_blueprint.json").write_text('{"tampered": true}', encoding="utf-8")

    state = StateStore.load(proj_dir)
    ctx = RetryContext(
        project_id=review_env["project_id"],
        expected_revision=state.revision,
        operation="render_project",
        stage="render",
        attempt=1,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    valid, reason = RetryPolicy.verify_preconditions(proj_dir, ctx)
    assert not valid, f"Expected retry to fail for invalidated review, got valid with reason: {reason}"
    assert "review" in reason.lower() or "authoriz" in reason.lower() or "blueprint" in reason.lower()
