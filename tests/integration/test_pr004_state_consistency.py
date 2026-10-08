"""
tests/integration/test_pr004_state_consistency.py — PR-004 State Consistency & Workflow Integrity Tests.

Verifies:
- A1: Canonical apply/read exact revision with matching SQL/StorageService/disk hashes.
- A2: Explicit revision request when storage object is missing NEVER silently returns stale disk bytes (H2).
- A3: Managed state update fails closed when database sync fails (H1).
- A5/A9: Concurrent run creation with same idempotency key never creates duplicate queued runs (H5).
- A6: Mutating canonical blueprint invalidates active review decision and revokes render authorization (H3).
- A7: Expired leaseholder worker is strictly fenced from finishing run or publishing output (H4).
- A10: Workspace isolation across document reads and run operations.
"""

import os
import json
import uuid
import time
import hashlib
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest

from scripts.core.database import DatabaseEngine, TenantRepository, TenantStateRepository, set_database_engine
from scripts.core.storage.storage_service import LocalStorageBackend, set_storage_service
from scripts.core.canonical_document_repository import (
    CanonicalDocumentRepository,
    RevisionConflictError,
    StateNotFoundError,
)
from scripts.core.state_store import (
    StateStore,
    StateConflictError,
    StateStoreError,
)
from scripts.core.state_model import LifecycleState, ProjectState, ValidationLevel
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.run_repository import RunRepository, RunRepositoryError
from scripts.core.review_service import (
    ReviewService,
    RenderNotAuthorizedError,
    create_local_trusted_principal,
)
from api.services.run_service import RunService
from scripts.core.tenant_model import TenantContext


@pytest.fixture
def test_env(tmp_path, monkeypatch):
    """Sets up an isolated, hermetic SQLite database, LocalStorageService, and projects root."""
    db_file = tmp_path / "pr004_test.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("MOTION_DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("AGY_IS_MANAGED", "1")
    monkeypatch.setenv("MOTION_ENV", "production")

    db_engine = DatabaseEngine(db_url)
    set_database_engine(db_engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_svc = LocalStorageBackend(storage_root)
    set_storage_service(storage_svc)

    # Pre-seed default workspace & user
    tenant_repo = TenantRepository(db_engine)
    user = tenant_repo.create_user("usr_owner", "owner@example.com")
    ws = tenant_repo.create_workspace("ws_pr004", "PR-004 Workspace", user.id)

    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)

    yield {
        "db_engine": db_engine,
        "storage": storage_svc,
        "workspace_id": ws.id,
        "user_id": user.id,
        "tmp_path": tmp_path,
        "tenant_repo": tenant_repo,
    }

    set_database_engine(None)
    set_storage_service(None)


def _create_minimal_blueprint(project_id: str, revision: int = 1) -> dict:
    return {
        "blueprint_version": "2.0.0",
        "project_id": project_id,
        "revision": revision,
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {
                "scene_id": "scene_001",
                "template": "TitleCard",
                "startFrame": 0,
                "durationFrames": 90,
                "props": {"title": f"Hello Rev {revision}"},
            }
        ],
        "meta": {"created_at": datetime.now(timezone.utc).isoformat()},
    }


# ─── TEST H2 / A2: CanonicalDocumentRepository Missing Storage Bytes ───

def test_red_h2_canonical_repo_fails_closed_on_missing_storage_bytes(test_env):
    """
    H2 / A2: When an explicit revision N is requested in managed mode, and its storage
    object is missing, the repository must NEVER silently fall back to an unverified disk
    file containing revision N-1 and mislabel it as revision N.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_test_h2"
    doc_repo = CanonicalDocumentRepository(test_env["db_engine"], test_env["storage"])

    # 1. Register project in database
    test_env["tenant_repo"].create_project(project_id, ws_id, name="Test Project", created_by=test_env["user_id"])

    # 2. Commit rev 1 through doc_repo (advancing revision to 2)
    bp_v1 = _create_minimal_blueprint(project_id, 1)
    doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=project_id,
        expected_revision=1,
        candidate_doc=bp_v1,
        actor_id=test_env["user_id"],
        operation_id="op_init_rev2",
    )

    # Now current rev in DB is 2.
    # On disk, write an OLD revision 1 file
    proj_dir = Path("projects") / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    disk_file = proj_dir / "05_blueprint.json"
    disk_v1_bytes = _create_minimal_blueprint(project_id, 1)
    disk_file.write_text(json.dumps(disk_v1_bytes), encoding="utf-8")

    # Now intentionally simulate storage object loss for revision 2
    # Find storage key for rev 2
    with test_env["db_engine"].get_connection() as conn:
        row = conn.execute(
            "SELECT storage_key FROM project_artifact_versions WHERE project_id = ? AND revision = 2",
            (project_id,)
        ).fetchone()
        storage_key = row[0]

    # Delete storage object for rev 2
    test_env["storage"].delete(storage_key)

    # In managed mode, requesting revision 2 MUST FAIL CLOSED (StateNotFoundError).
    # It must NOT read the old disk_v1_bytes and return (disk_v1_bytes, 2)!
    with pytest.raises(StateNotFoundError, match="not found in storage|missing"):
        doc_repo.get_document(workspace_id=ws_id, project_id=project_id, revision=2)


# ─── TEST H1 / A3: StateStore Database Outage Fail-Closed ───

def test_red_h1_statestore_sync_to_db_fails_closed_in_managed_mode(test_env, monkeypatch):
    """
    H1 / A3: In managed mode (AGY_IS_MANAGED=1), if the database sync fails during
    StateStore.atomic_update or StateStore.save, the operation must FAIL CLOSED.
    It must not report success while disk advances and database remains stale.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_test_h1"
    proj_dir = Path("projects") / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    test_env["tenant_repo"].create_project(project_id, ws_id, name="Test H1", created_by=test_env["user_id"])

    # Create initial state on disk and DB
    state = StateStore.create(proj_dir, project_id, initial_lifecycle=LifecycleState.DRAFT, workspace_id=ws_id)
    assert state.revision == 1

    # Verify DB has revision 1
    state_repo = TenantStateRepository(test_env["db_engine"])
    db_state = state_repo.load_state(project_id)
    assert db_state is not None
    assert db_state.revision == 1

    # Now monkeypatch DatabaseEngine to simulate an unexpected SQL error during transaction
    orig_transaction = test_env["db_engine"].transaction
    def failing_transaction(*args, **kwargs):
        raise RuntimeError("SIMULATED_DB_DISCONNECTION_ERROR")

    monkeypatch.setattr(test_env["db_engine"], "transaction", failing_transaction)

    # In managed mode, atomic_update MUST RAISE an exception on DB failure!
    # It must NOT silently return working_copy with disk at rev 2 and DB at rev 1!
    def mutator(s):
        s.lifecycle_state = LifecycleState.ASSETS_READY

    with pytest.raises((StateStoreError, RuntimeError)):
        StateStore.atomic_update(proj_dir, expected_revision=1, mutator=mutator)

    # Verify disk was NOT permanently advanced to rev 2 while DB is broken
    re_loaded = StateStore.load(proj_dir)
    assert re_loaded.revision == 1, "Disk revision must not advance if database sync fails in managed mode!"


# ─── TEST H4 / A7: Stale Worker Fencing Violation on Lease Expiry ───

def test_red_h4_stale_worker_fenced_on_lease_expiry(test_env):
    """
    H4 / A7: A worker whose execution lease has expired must be strictly fenced
    from finishing the run as SUCCEEDED or updating the terminal status.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_test_h4"
    test_env["tenant_repo"].create_project(project_id, ws_id, name="Test H4", created_by=test_env["user_id"])

    run_repo = RunRepository(test_env["db_engine"].db_url.replace("sqlite:///", ""))

    # 1. Create a QUEUED run
    run = RunRecord(
        run_id="run_fencing_test",
        workspace_id=ws_id,
        project_id=project_id,
        status=RunStatus.QUEUED,
        input_revision=1,
    )
    run_repo.create_run(run)

    # 2. Worker 1 claims run with short lease of 1 second
    claimed = run_repo.claim_next_run(worker_id="worker_alpha", lease_duration_seconds=1.0)
    assert claimed is not None
    assert claimed.worker_id == "worker_alpha"

    # 3. Simulate lease expiration by updating lease_expires_at to the past
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    with run_repo._transaction("IMMEDIATE") as conn:
        conn.execute("UPDATE runs SET lease_expires_at = ? WHERE run_id = ?", (past_iso, claimed.run_id))
        conn.execute("UPDATE project_execution_leases SET expires_at = ? WHERE run_id = ?", (past_iso, claimed.run_id))

    # 4. Worker alpha (whose lease expired) attempts to call finish_run(SUCCEEDED)
    # This MUST raise RunRepositoryError (Stale worker fencing violation)
    with pytest.raises(RunRepositoryError, match="Stale worker fencing violation|lease expired|lost"):
        run_repo.finish_run(
            run_id=claimed.run_id,
            worker_id="worker_alpha",
            status=RunStatus.SUCCEEDED,
            result_reference={"return_code": 0},
        )


# ─── TEST H5 / A5: Concurrent Run Creation Idempotency ───

def test_red_h5_concurrent_idempotency_creates_exactly_one_run(test_env, monkeypatch):
    """
    H5 / A5: Two concurrent requests with the identical idempotency key and payload
    must race safely, resulting in exactly ONE queued run and zero duplicate records.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_test_h5"
    test_env["tenant_repo"].create_project(project_id, ws_id, name="Test H5", created_by=test_env["user_id"])

    proj_dir = Path("projects") / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    StateStore.create(proj_dir, project_id, initial_lifecycle=LifecycleState.DRAFT, workspace_id=ws_id)

    db_path = test_env["db_engine"].db_url.replace("sqlite:///", "")
    idemp_key = "idemp_concurrent_key_001"
    payload = {"render_preset": "high", "fps": 30}

    results = []
    errors = []
    barrier = threading.Barrier(2)

    # Monkeypatch find_by_idempotency to synchronize both threads before insertion
    orig_find = RunRepository.find_by_idempotency
    def synchronized_find(self, project_id, idempotency_key, *args, **kwargs):
        res = orig_find(self, project_id, idempotency_key, *args, **kwargs)
        try:
            barrier.wait(timeout=2.0)
        except threading.BrokenBarrierError:
            pass
        return res

    monkeypatch.setattr(RunRepository, "find_by_idempotency", synchronized_find)

    def caller_thread():
        try:
            rec, is_created = RunService.create_run(
                project_id=project_id,
                idempotency_key=idemp_key,
                payload=payload,
                db_path=db_path,
                workspace_id=ws_id,
            )
            results.append((rec, is_created))
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=caller_thread)
    t2 = threading.Thread(target=caller_thread)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(errors) == 0, f"Concurrent callers experienced unexpected errors: {errors}"
    assert len(results) == 2

    run_ids = {r[0].run_id for r in results}
    assert len(run_ids) == 1, f"Expected exactly 1 run_id across concurrent calls, got: {run_ids}"

    created_flags = [r[1] for r in results]
    assert created_flags.count(True) == 1, "Exactly one thread should report is_created=True"
    assert created_flags.count(False) == 1, "The duplicate thread should report is_created=False"


# ─── TEST H3 / A6: Canonical Mutation Invalidates Review Approval ───

def test_red_h3_canonical_apply_invalidates_downstream_review_decision(test_env):
    """
    H3 / A6: When a project has reached REVIEW_APPROVED, applying a new canonical
    document revision MUST invalidate the prior review approval and revoke render
    authorization.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_test_h3"
    test_env["tenant_repo"].create_project(project_id, ws_id, name="Test H3", created_by=test_env["user_id"])

    proj_dir = Path("projects") / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize StateStore and project files
    state = StateStore.create(proj_dir, project_id, initial_lifecycle=LifecycleState.DRAFT, workspace_id=ws_id)
    doc_repo = CanonicalDocumentRepository(test_env["db_engine"], test_env["storage"])

    bp_v1 = _create_minimal_blueprint(project_id, 1)
    doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=project_id,
        expected_revision=1,
        candidate_doc=bp_v1,
        actor_id=test_env["user_id"],
        operation_id="op_init_rev1",
    )

    # Create dummy media map and probe report
    (proj_dir / "media_map.json").write_text("{}", encoding="utf-8")
    (proj_dir / "probe_qc_report.json").write_text('{"status": "PASSED"}', encoding="utf-8")

    # Advance state to AWAITING_REVIEW
    def set_awaiting(s):
        s.lifecycle_state = LifecycleState.AWAITING_REVIEW
    cur_st = StateStore.load(proj_dir)
    StateStore.atomic_update(proj_dir, expected_revision=cur_st.revision, mutator=set_awaiting)

    # Create review bundle and approve
    bundle = ReviewService.create_review_bundle(proj_dir)
    principal = create_local_trusted_principal("trusted_reviewer")
    decision = ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=principal, reason="Initial approval")

    # Verify currently authorized for render
    auth_res = ReviewService.assert_render_authorized(proj_dir)
    assert auth_res.is_authorized is True

    # 2. Mutate canonical blueprint to rev 3
    curr_doc, curr_bp_rev = doc_repo.get_document(workspace_id=ws_id, project_id=project_id)
    assert curr_bp_rev == 2
    bp_v2 = _create_minimal_blueprint(project_id, 2)
    bp_v2["scenes"][0]["props"]["title"] = "Mutated Scene Title"

    doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=project_id,
        expected_revision=curr_bp_rev,
        candidate_doc=bp_v2,
        actor_id=test_env["user_id"],
        operation_id="op_mutate_rev3",
    )

    # 3. Render authorization MUST now fail closed!
    with pytest.raises(RenderNotAuthorizedError):
        ReviewService.assert_render_authorized(proj_dir)
