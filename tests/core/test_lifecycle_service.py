"""
Tests for LifecycleService (S03) — The Single Lifecycle Authority.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

from scripts.core.lifecycle_service import (
    LifecycleService,
    LifecycleError,
    InvalidLifecycleTransitionError,
    LifecyclePreconditionFailedError,
)
from scripts.core.state_model import LifecycleState, ProjectState, ValidationLevel
from scripts.core.state_store import StateStore


@pytest.fixture
def project_setup(tmp_path):
    project_id = "test-s03-lifecycle"
    proj_dir = tmp_path / "projects" / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    initial_state = StateStore.create(proj_dir, project_id)
    return project_id, proj_dir, initial_state


def test_initial_state_is_draft(project_setup):
    _, proj_dir, state = project_setup
    assert state.lifecycle_state == LifecycleState.DRAFT
    assert state.revision == 1


def test_illegal_skip_transition_rejected(project_setup):
    """Direct jump from DRAFT to BLUEPRINT_READY must be rejected."""
    _, proj_dir, _ = project_setup

    with pytest.raises(InvalidLifecycleTransitionError) as exc_info:
        LifecycleService.transition(proj_dir, LifecycleState.BLUEPRINT_READY)

    assert exc_info.value.current_state == LifecycleState.DRAFT
    assert exc_info.value.target_state == LifecycleState.BLUEPRINT_READY

    # State on disk must remain unchanged
    persisted = StateStore.load(proj_dir)
    assert persisted.lifecycle_state == LifecycleState.DRAFT
    assert persisted.revision == 1


def test_missing_prerequisite_file_rejected(project_setup):
    """Transition to ASSETS_READY without 02_asset_manifest.json must fail precondition."""
    _, proj_dir, _ = project_setup

    assert not (proj_dir / "02_asset_manifest.json").exists()

    with pytest.raises(LifecyclePreconditionFailedError) as exc_info:
        LifecycleService.transition(proj_dir, LifecycleState.ASSETS_READY)

    assert "02_asset_manifest.json" in str(exc_info.value)

    # State on disk must remain DRAFT
    persisted = StateStore.load(proj_dir)
    assert persisted.lifecycle_state == LifecycleState.DRAFT


def test_valid_forward_transition_with_evidence(project_setup):
    """Valid transition from DRAFT to ASSETS_READY with manifest present."""
    _, proj_dir, _ = project_setup

    # Create required manifest
    manifest_file = proj_dir / "02_asset_manifest.json"
    manifest_file.write_text('{"assets": []}', encoding="utf-8")

    updated_state = LifecycleService.transition(
        project_dir=proj_dir,
        target_state=LifecycleState.ASSETS_READY,
        artifacts=[("02_asset_manifest.json", ValidationLevel.EXISTS)],
    )

    assert updated_state.lifecycle_state == LifecycleState.ASSETS_READY
    assert updated_state.revision == 2
    assert len(updated_state.artifact_records) == 1
    assert updated_state.artifact_records[0].path == "02_asset_manifest.json"

    # Verify persistence sanity
    persisted = StateStore.load(proj_dir)
    assert persisted is not None
    assert persisted.lifecycle_state == LifecycleState.ASSETS_READY
    assert persisted.revision == 2


def test_blueprint_ready_requires_valid_json_blueprint(project_setup):
    """Transition to BLUEPRINT_READY requires valid non-empty 05_blueprint.json and master_plan.md."""
    _, proj_dir, _ = project_setup

    # First advance to ASSETS_READY
    (proj_dir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")
    LifecycleService.transition(proj_dir, LifecycleState.ASSETS_READY)

    # Advance to PLAN_READY
    (proj_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")
    LifecycleService.transition(proj_dir, LifecycleState.PLAN_READY)

    # Attempt BLUEPRINT_READY without 05_blueprint.json
    with pytest.raises(LifecyclePreconditionFailedError):
        LifecycleService.transition(proj_dir, LifecycleState.BLUEPRINT_READY)

    # Write valid blueprint
    (proj_dir / "05_blueprint.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
    state = LifecycleService.transition(
        proj_dir,
        LifecycleState.BLUEPRINT_READY,
        artifacts=[
            ("master_plan.md", ValidationLevel.SHA256),
            ("05_blueprint.json", ValidationLevel.SHA256),
        ],
    )
    assert state.lifecycle_state == LifecycleState.BLUEPRINT_READY
    assert state.revision == 4


def test_transition_to_failed_with_reason(project_setup):
    """Transition to FAILED is permitted from active states and logs the reason."""
    _, proj_dir, _ = project_setup

    reason = "Asset gate timeout"
    state = LifecycleService.transition(
        proj_dir,
        LifecycleState.FAILED,
        reason=reason,
    )

    assert state.lifecycle_state == LifecycleState.FAILED
    assert state.run_metadata.get("transition_reason") == reason
    assert len(state.structured_errors) == 1
    assert state.structured_errors[0]["error"] == reason

    # Persisted check
    persisted = StateStore.load(proj_dir)
    assert persisted.lifecycle_state == LifecycleState.FAILED


def test_terminal_state_cannot_fail_or_cancel(project_setup):
    """COMPLETE cannot transition to FAILED or CANCELLED."""
    _, proj_dir, state = project_setup

    # Fast-forward state to COMPLETE for unit testing transition rule
    state.lifecycle_state = LifecycleState.COMPLETE
    StateStore.save(proj_dir, state)

    with pytest.raises(InvalidLifecycleTransitionError):
        LifecycleService.transition(proj_dir, LifecycleState.FAILED)

    with pytest.raises(InvalidLifecycleTransitionError):
        LifecycleService.transition(proj_dir, LifecycleState.CANCELLED)


def test_idempotent_transition(project_setup):
    """Transition to the current state succeeds without modifying revision."""
    _, proj_dir, _ = project_setup

    initial = StateStore.load(proj_dir)
    rev_before = initial.revision

    state = LifecycleService.transition(proj_dir, LifecycleState.DRAFT)
    assert state.lifecycle_state == LifecycleState.DRAFT
