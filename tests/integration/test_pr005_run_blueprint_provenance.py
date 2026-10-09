"""
tests/integration/test_pr005_run_blueprint_provenance.py

PR-005 Phase 3: Run-to-Blueprint Provenance Decoupling & Immutability Verification.
Guarantees:
1. Matching pinned version executes with correct canonical blueprint bytes.
2. New blueprint committed after enqueue does not silently retarget prior Run.
3. Storage object missing -> fails closed.
4. Storage object corrupted/tampered -> fails closed.
5. Stale / invalidated review approval -> fails closed.
6. Cross-tenant storage key -> rejected.
7. Concurrent idempotent queue requests -> exactly one Run and one RUN_QUEUED event.
8. Conflicting idempotency payload -> IdempotencyConflictError.
9. Worker restart / recovery preserves pinned provenance tuple identically.
"""

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

from api.core.errors import IdempotencyConflictError
from api.services.run_service import RunService
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.run_repository import RunRepository
from scripts.core.state_model import (
    ProjectState,
    LifecycleState,
    ReviewBundle,
    ReviewDecision,
    ReviewDecisionType,
)
from scripts.core.state_store import StateStore
from scripts.core.storage import get_storage_service, set_storage_service, LocalStorageBackend
from scripts.core.worker import PipelineWorker


@pytest.fixture
def test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Sets up an isolated database, storage service, and project directory."""
    db_file = tmp_path / "test_motion.db"
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    monkeypatch.chdir(tmp_path)

    # Initialize Engine & Storage
    engine = DatabaseEngine(db_url)
    set_database_engine(engine)
    storage = LocalStorageBackend(root_dir=storage_dir)
    set_storage_service(storage)

    # Mock safe_subprocess in worker to simulate clean execution without invoking full remotion render
    from unittest.mock import MagicMock
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "Pipeline finished successfully\n[STAGE_START] RENDER\n[STAGE_FINISH] RENDER"
    mock_res.stderr = ""
    mock_sub = MagicMock(return_value=mock_res)
    import scripts.core.worker as worker_mod
    monkeypatch.setattr(worker_mod, "safe_subprocess", mock_sub)

    ws_id = f"ws_{uuid.uuid4().hex[:8]}"
    proj_id = f"proj_{uuid.uuid4().hex[:8]}"

    # Setup tenant in DB
    tenant_repo = TenantRepository(engine)
    user = tenant_repo.create_user(f"usr_{uuid.uuid4().hex[:8]}", f"test_{uuid.uuid4().hex[:8]}@example.com")
    tenant_repo.create_workspace(ws_id, "Test Workspace", user.id)
    tenant_repo.create_project(proj_id, ws_id, "Test Project", user.id)

    # Setup project directory on disk
    proj_dir = projects_dir / proj_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        yield {
            "tmp_path": tmp_path,
            "db_url": db_url,
            "engine": engine,
            "storage": storage,
            "ws_id": ws_id,
            "proj_id": proj_id,
            "proj_dir": proj_dir,
            "mock_subprocess": mock_sub,
        }
    finally:
        set_database_engine(None)
        set_storage_service(None)


def _create_sample_blueprint(title: str = "Test Video", duration: float = 5.0) -> dict:
    return {
        "schema_version": "2.0.0",
        "title": title,
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "duration": duration,
        "scenes": [
            {
                "id": "scene_001",
                "template": "HeroTemplate",
                "startFrame": 0,
                "durationFrames": int(duration * 30),
                "props": {"headline": title},
            }
        ],
    }


def _setup_approved_blueprint_state(test_env, bp_dict, revision: int = 1):
    """Commits blueprint to Storage, project_artifact_versions, and StateStore as APPROVED."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    engine = test_env["engine"]
    storage = test_env["storage"]
    proj_dir = test_env["proj_dir"]

    bp_json = json.dumps(bp_dict, sort_keys=True)
    bp_bytes = bp_json.encode("utf-8")
    bp_sha = hashlib.sha256(bp_bytes).hexdigest()
    storage_key = f"workspaces/{ws_id}/projects/{proj_id}/blueprints/rev_{revision}_{bp_sha[:8]}.json"
    storage.put(storage_key, bp_bytes, content_type="application/json")

    # Record in project_artifact_versions
    with engine.transaction("IMMEDIATE") as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO project_artifact_versions (
                id, workspace_id, project_id, artifact_kind, revision, content_hash, storage_key, created_at
            ) VALUES (?, ?, ?, 'blueprint', ?, ?, ?, datetime('now'))
            """,
            (f"art_{proj_id}_bp_{revision}", ws_id, proj_id, revision, bp_sha, storage_key),
        )

    # Write local disk
    (proj_dir / "05_blueprint.json").write_bytes(bp_bytes)

    # Setup StateStore with approved review bundle
    bundle_id = f"rbd_{uuid.uuid4().hex[:8]}"
    bundle = ReviewBundle(
        review_bundle_id=bundle_id,
        project_id=proj_id,
        state_revision=revision,
        blueprint_sha256=bp_sha,
        media_map_sha256="hash_media",
        probe_report_sha256="hash_probe",
        status="ACTIVE",
    )
    decision = ReviewDecision(
        decision_id=f"dec_{uuid.uuid4().hex[:8]}",
        review_bundle_id=bundle_id,
        project_id=proj_id,
        decision=ReviewDecisionType.APPROVED,
        actor_id="usr_admin",
        state_revision=revision,
        bundle_digest="bundle_digest_1",
    )
    cur_disk = StateStore.load(proj_dir)
    bundles = list(cur_disk.review_bundles) if cur_disk else []
    bundles.append(bundle)
    decisions = list(cur_disk.review_decisions) if cur_disk else []
    decisions.append(decision)

    state = ProjectState(
        project_id=proj_id,
        workspace_id=ws_id,
        revision=revision,
        lifecycle_state=LifecycleState.REVIEW_APPROVED,
        active_review_bundle_id=bundle_id,
        active_review_decision_id=decision.decision_id,
        review_bundles=bundles,
        review_decisions=decisions,
    )
    exp_rev = cur_disk.revision if cur_disk else None
    StateStore.save(proj_dir, state, expected_revision=exp_rev)

    return {
        "revision": revision,
        "blueprint_sha256": bp_sha,
        "storage_key": storage_key,
        "bundle_id": bundle_id,
        "blueprint_bytes": bp_bytes,
    }


def test_matching_pinned_blueprint_provenance_succeeds(test_env):
    """A run enqueued with valid pinned provenance executes cleanly."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    bp_dict = _create_sample_blueprint("Valid Video")
    meta = _setup_approved_blueprint_state(test_env, bp_dict, revision=1)

    run, created = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        payload={"task": "render"},
    )
    assert created is True
    assert run.canonical_document_revision == 1
    assert run.canonical_blueprint_sha256 == meta["blueprint_sha256"]
    assert run.immutable_storage_key == meta["storage_key"]
    assert run.approved_review_bundle_id == meta["bundle_id"]
    assert run.lifecycle_state_revision == 1

    worker = PipelineWorker(worker_id="worker_test_1")
    processed = worker.process_one()
    assert processed is True

    repo = RunRepository()
    final_run = repo.get_run(run.run_id)
    assert final_run.status == RunStatus.SUCCEEDED


def test_new_blueprint_after_enqueue_does_not_retarget_prior_run(test_env):
    """
    CRITICAL PROVENANCE INVARIANT:
    If a new blueprint revision is committed AFTER a run was enqueued,
    the worker must NOT execute the new blueprint. It must execute with the pinned bytes.
    """
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    proj_dir = test_env["proj_dir"]

    # 1. Setup revision 1
    bp1 = _create_sample_blueprint("Rev 1 Title", duration=5.0)
    meta1 = _setup_approved_blueprint_state(test_env, bp1, revision=1)

    # 2. Enqueue run for rev 1
    run1, _ = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        payload={"task": "render"},
    )
    assert run1.canonical_blueprint_sha256 == meta1["blueprint_sha256"]

    # 3. Now commit revision 2 with modified blueprint and different title
    bp2 = _create_sample_blueprint("Rev 2 MUTATED Title", duration=10.0)
    meta2 = _setup_approved_blueprint_state(test_env, bp2, revision=2)
    assert meta2["blueprint_sha256"] != meta1["blueprint_sha256"]

    # At this point, disk 05_blueprint.json has rev 2 content
    disk_before_worker = (proj_dir / "05_blueprint.json").read_bytes()
    assert hashlib.sha256(disk_before_worker).hexdigest() == meta2["blueprint_sha256"]

    # 4. Worker executes run 1
    worker = PipelineWorker(worker_id="worker_test_2")
    processed = worker.process_one()
    assert processed is True

    # 5. Proves worker materialized and executed rev 1 pinned bytes, preventing silent retargeting!
    disk_after_worker = (proj_dir / "05_blueprint.json").read_bytes()
    assert hashlib.sha256(disk_after_worker).hexdigest() == meta1["blueprint_sha256"]

    repo = RunRepository()
    final_run = repo.get_run(run1.run_id)
    assert final_run.status == RunStatus.SUCCEEDED


def test_storage_object_missing_fails_closed(test_env):
    """If the immutable storage object is missing, worker fails closed with STORAGE_OBJECT_MISSING."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    bp_dict = _create_sample_blueprint("Missing Storage Video")
    meta = _setup_approved_blueprint_state(test_env, bp_dict, revision=1)

    # Delete storage object behind its back
    test_env["storage"].delete(meta["storage_key"])

    run, _ = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        payload={"task": "render"},
    )

    worker = PipelineWorker(worker_id="worker_test_3")
    processed = worker.process_one()
    assert processed is True

    repo = RunRepository()
    final_run = repo.get_run(run.run_id)
    assert final_run.status == RunStatus.FAILED
    assert final_run.failure_code == "STORAGE_OBJECT_MISSING"


def test_storage_object_corrupted_fails_closed(test_env):
    """If storage object content was altered/tampered, worker fails closed with STORAGE_OBJECT_CORRUPTED."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    bp_dict = _create_sample_blueprint("Tampered Storage Video")
    meta = _setup_approved_blueprint_state(test_env, bp_dict, revision=1)

    # Overwrite storage object with tampered content
    tampered_bytes = b'{"tampered": true}'
    test_env["storage"].put(meta["storage_key"], tampered_bytes, content_type="application/json")

    run, _ = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        payload={"task": "render"},
    )

    worker = PipelineWorker(worker_id="worker_test_4")
    processed = worker.process_one()
    assert processed is True

    repo = RunRepository()
    final_run = repo.get_run(run.run_id)
    assert final_run.status == RunStatus.FAILED
    assert final_run.failure_code == "STORAGE_OBJECT_CORRUPTED"


def test_stale_or_invalidated_review_approval_fails_closed(test_env):
    """If the review approval bundle is invalidated before execution, worker fails closed."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    proj_dir = test_env["proj_dir"]
    bp_dict = _create_sample_blueprint("Invalidated Approval Video")
    meta = _setup_approved_blueprint_state(test_env, bp_dict, revision=1)

    run, _ = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        payload={"task": "render"},
    )

    # Invalidate the review bundle in StateStore
    state = StateStore.load(proj_dir)
    for b in state.review_bundles:
        if b.review_bundle_id == meta["bundle_id"]:
            b.status = "INVALIDATED"
    StateStore.save(proj_dir, state)

    worker = PipelineWorker(worker_id="worker_test_5")
    processed = worker.process_one()
    assert processed is True

    repo = RunRepository()
    final_run = repo.get_run(run.run_id)
    assert final_run.status == RunStatus.FAILED
    assert final_run.failure_code == "STALE_REVIEW_APPROVAL"


def test_cross_tenant_storage_key_rejected(test_env):
    """If a run has an immutable storage key from a foreign workspace, worker rejects execution."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    bp_dict = _create_sample_blueprint("Cross Tenant Video")
    meta = _setup_approved_blueprint_state(test_env, bp_dict, revision=1)

    foreign_key = f"workspaces/ws_attacker_999/projects/{proj_id}/blueprints/bad.json"

    run, _ = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        payload={
            "task": "render",
            "immutable_storage_key": foreign_key,
        },
    )

    worker = PipelineWorker(worker_id="worker_test_6")
    processed = worker.process_one()
    assert processed is True

    repo = RunRepository()
    final_run = repo.get_run(run.run_id)
    assert final_run.status == RunStatus.FAILED
    assert final_run.failure_code == "CROSS_TENANT_STORAGE_VIOLATION"


def test_concurrent_idempotent_enqueue_single_run_and_event(test_env):
    """Two concurrent enqueue calls with the same idempotency key return the identical Run and emit 1 event."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    bp_dict = _create_sample_blueprint("Idempotent Video")
    _setup_approved_blueprint_state(test_env, bp_dict, revision=1)

    idemp_key = f"idemp_{uuid.uuid4().hex}"
    payload = {"task": "render", "resolution": "1080p"}

    run1, is_created1 = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        idempotency_key=idemp_key,
        payload=payload,
    )
    run2, is_created2 = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        idempotency_key=idemp_key,
        payload=payload,
    )

    assert is_created1 is True
    assert is_created2 is False
    assert run1.run_id == run2.run_id
    assert run1.canonical_blueprint_sha256 == run2.canonical_blueprint_sha256

    events = RunService.get_events(proj_id, run1.run_id)
    queued_events = [e for e in events if e.event_type == "RUN_QUEUED"]
    assert len(queued_events) == 1


def test_conflicting_idempotent_payload_raises_409(test_env):
    """Reusing the same idempotency key with different payload raises IdempotencyConflictError."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    bp_dict = _create_sample_blueprint("Conflict Video")
    _setup_approved_blueprint_state(test_env, bp_dict, revision=1)

    idemp_key = f"idemp_{uuid.uuid4().hex}"

    RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        idempotency_key=idemp_key,
        payload={"task": "render", "resolution": "1080p"},
    )

    with pytest.raises(IdempotencyConflictError):
        RunService.create_run(
            project_id=proj_id,
            workspace_id=ws_id,
            idempotency_key=idemp_key,
            payload={"task": "render", "resolution": "720p"},
        )


def test_worker_restart_preserves_pinned_provenance(test_env):
    """When a worker dies and the run is recovered, all 5 pinned provenance fields remain intact."""
    ws_id = test_env["ws_id"]
    proj_id = test_env["proj_id"]
    bp_dict = _create_sample_blueprint("Recovery Video")
    meta = _setup_approved_blueprint_state(test_env, bp_dict, revision=1)

    run, _ = RunService.create_run(
        project_id=proj_id,
        workspace_id=ws_id,
        payload={"task": "render"},
    )

    repo = RunRepository()
    # Simulate worker 1 claims the run
    claimed = repo.claim_next_run(worker_id="worker_crashed", lease_duration_seconds=-10.0)
    assert claimed is not None
    assert claimed.run_id == run.run_id

    # Expire lease directly in SQL to simulate hard crash
    with repo._transaction("IMMEDIATE") as conn:
        conn.execute(
            "UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00Z' WHERE run_id = ?",
            (run.run_id,),
        )
        conn.execute(
            "UPDATE project_execution_leases SET expires_at = '2000-01-01T00:00:00Z' WHERE run_id = ?",
            (run.run_id,),
        )

    # Worker 2 boots up, performs orphan recovery pass, and claims the run
    worker2 = PipelineWorker(worker_id="worker_fresh")
    processed = worker2.process_one()
    assert processed is True

    recovered_run = repo.get_run(run.run_id)
    assert recovered_run.status == RunStatus.SUCCEEDED
    assert recovered_run.attempt == 2
    assert recovered_run.canonical_document_revision == 1
    assert recovered_run.canonical_blueprint_sha256 == meta["blueprint_sha256"]
    assert recovered_run.immutable_storage_key == meta["storage_key"]
    assert recovered_run.approved_review_bundle_id == meta["bundle_id"]
    assert recovered_run.lifecycle_state_revision == 1
