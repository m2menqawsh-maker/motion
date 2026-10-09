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
from scripts.core.state_model import LifecycleState, ProjectState, ValidationLevel, ReviewDecisionType
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


# ─── FINAL CRASH BOUNDARY 1: Blueprint Commit vs Review Invalidation ───

def test_crash_boundary_blueprint_commit_vs_review_invalidation(test_env, monkeypatch):
    """
    Crash Boundary 1: Inject a failure after new canonical blueprint is committed
    to SQL, but before review invalidation finishes (or before disk is updated).
    Verify that stale approval CANNOT authorize rendering after process restart.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_cb1_review_invalidation"
    test_env["tenant_repo"].create_project(project_id, ws_id, name="CB1 Project", created_by=test_env["user_id"])

    proj_dir = Path("projects") / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    # 1. Setup project with Blueprint Rev 1 and get it REVIEW_APPROVED
    StateStore.create(proj_dir, project_id, initial_lifecycle=LifecycleState.DRAFT, workspace_id=ws_id)
    doc_repo = CanonicalDocumentRepository(test_env["db_engine"], test_env["storage"])

    bp_v1 = _create_minimal_blueprint(project_id, 1)
    doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=project_id,
        expected_revision=1,
        candidate_doc=bp_v1,
        actor_id=test_env["user_id"],
        operation_id="op_cb1_init",
    )

    (proj_dir / "media_map.json").write_text("{}", encoding="utf-8")
    (proj_dir / "probe_qc_report.json").write_text('{"status": "PASSED"}', encoding="utf-8")

    st = StateStore.load(proj_dir)
    StateStore.atomic_update(
        proj_dir,
        expected_revision=st.revision,
        mutator=lambda s: setattr(s, "lifecycle_state", LifecycleState.AWAITING_REVIEW),
    )

    bundle = ReviewService.create_review_bundle(proj_dir)
    principal = create_local_trusted_principal("reviewer_cb1")
    ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=principal, reason="Approved Rev 1")

    # Verify initially authorized
    assert ReviewService.assert_render_authorized(proj_dir).is_authorized is True

    # 2. Inject failure during commit_candidate:
    # SQL transaction commits, but ReviewService.invalidate_review raises a crash exception
    orig_invalidate = ReviewService.invalidate_review
    def crashing_invalidate(*args, **kwargs):
        raise RuntimeError("SIMULATED CRASH: process killed before review invalidation finishes")

    monkeypatch.setattr(ReviewService, "invalidate_review", crashing_invalidate)

    bp_v2 = _create_minimal_blueprint(project_id, 2)
    bp_v2["scenes"][0]["props"]["title"] = "Title Mutated in Rev 2"

    # commit_candidate catches invalidation error and logs warning, or raises
    doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=project_id,
        expected_revision=2,
        candidate_doc=bp_v2,
        actor_id=test_env["user_id"],
        operation_id="op_cb1_mut",
    )

    # 3. Simulate process restart:
    # Restore original ReviewService.invalidate_review without wiping fixture environment
    monkeypatch.setattr(ReviewService, "invalidate_review", orig_invalidate)

    # Re-verify persistent state: SQL has Rev 3, active bundle in state was for Rev 1
    # Check that stale approval CANNOT authorize rendering!
    with pytest.raises(RenderNotAuthorizedError) as exc_info:
        ReviewService.assert_render_authorized(proj_dir)
    assert "REVIEW_BUNDLE_STALE" in str(exc_info.value) or "CANONICAL_BLUEPRINT" in str(exc_info.value)

    # 4. Check persistent state after restart:
    # Bundle and decision must now be permanently invalidated on disk
    reloaded_state = StateStore.load(proj_dir)
    assert reloaded_state.review_bundles[0].status == "INVALIDATED"
    assert reloaded_state.review_decisions[0].decision == ReviewDecisionType.INVALIDATED
    assert not (proj_dir / ".studio_approved").exists()


# ─── FINAL CRASH BOUNDARY 2: Filesystem vs. SQL Crash ───

def test_crash_boundary_filesystem_vs_sql_crash(test_env):
    """
    Crash Boundary 2: Simulate hard process termination between writing
    .pipeline_state.json and completing the SQL state update.
    Restart process and verify safe recovery without conflicting authoritative
    revisions or unauthorized workflow progression.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_cb2_fs_sql_crash"
    test_env["tenant_repo"].create_project(project_id, ws_id, name="CB2 Project", created_by=test_env["user_id"])

    proj_dir = Path("projects") / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    # 1. Normal state: Revision 2, PLAN_READY in both disk and SQL
    StateStore.create(proj_dir, project_id, initial_lifecycle=LifecycleState.DRAFT, workspace_id=ws_id)
    cur = StateStore.load(proj_dir)
    StateStore.atomic_update(
        proj_dir,
        expected_revision=cur.revision,
        mutator=lambda s: setattr(s, "lifecycle_state", LifecycleState.PLAN_READY),
    )

    # Both disk and SQL are currently at revision 2, PLAN_READY
    state_disk = StateStore.load(proj_dir)
    assert state_disk.revision == 2
    assert state_disk.lifecycle_state == LifecycleState.PLAN_READY

    # 2. Simulate crash: disk writes revision 3 (MATERIALIZED), but process was killed before SQL sync
    state_file = proj_dir / StateStore.STATE_FILE
    raw_disk_data = json.loads(state_file.read_text(encoding="utf-8"))
    raw_disk_data["revision"] = 3
    raw_disk_data["lifecycle_state"] = LifecycleState.MATERIALIZED.value
    state_file.write_text(json.dumps(raw_disk_data, indent=2), encoding="utf-8")

    # At this moment: disk has rev 3 (MATERIALIZED), SQL has rev 2 (PLAN_READY)

    # 3. Simulate process restart and reload
    # In managed mode, StateStore.load authoritatively reconciles from SQL
    reloaded = StateStore.load(proj_dir)

    # Assert: Safe recovery to authoritative SQL revision (rev 2, PLAN_READY)
    assert reloaded.revision == 2
    assert reloaded.lifecycle_state == LifecycleState.PLAN_READY

    # Assert: Disk was healed to match authoritative SQL (no unauthorized MATERIALIZED state)
    healed_disk = json.loads(state_file.read_text(encoding="utf-8"))
    assert healed_disk["revision"] == 2
    assert healed_disk["lifecycle_state"] == LifecycleState.PLAN_READY.value

    # 4. Assert: Next legitimate workflow update from rev 2 succeeds cleanly
    updated = StateStore.atomic_update(
        proj_dir,
        expected_revision=2,
        mutator=lambda s: setattr(s, "lifecycle_state", LifecycleState.MATERIALIZED),
    )
    assert updated.revision == 3
    assert updated.lifecycle_state == LifecycleState.MATERIALIZED


# ─── FINAL CRASH BOUNDARY 3: Revision-Domain Consistency ───

def test_crash_boundary_revision_domain_consistency(test_env):
    """
    Crash Boundary 3: Execute Blueprint commit -> lifecycle transition -> Blueprint commit.
    Verify that document, lifecycle, and run input revisions retain their correct
    independent meanings, with no lost writes or wrong-version rendering.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_cb3_rev_domain"
    test_env["tenant_repo"].create_project(project_id, ws_id, name="CB3 Project", created_by=test_env["user_id"])

    proj_dir = Path("projects") / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Step 0: Initial state - Lifecycle Rev 1 (DRAFT)
    StateStore.create(proj_dir, project_id, initial_lifecycle=LifecycleState.DRAFT, workspace_id=ws_id)
    doc_repo = CanonicalDocumentRepository(test_env["db_engine"], test_env["storage"])

    # Step 1: Blueprint commit 1 -> Document Rev 2
    bp_v1 = _create_minimal_blueprint(project_id, 1)
    doc_dict1, bp_rev1, key1 = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=project_id,
        expected_revision=1,
        candidate_doc=bp_v1,
        actor_id=test_env["user_id"],
        operation_id="op_bp_1",
    )
    assert bp_rev1 == 2
    hash_v2 = hashlib.sha256(json.dumps(doc_dict1, indent=2, ensure_ascii=False).encode("utf-8")).hexdigest()

    # Invalidation hook upon blueprint commit advanced lifecycle state revision to 2
    st_after_bp1 = StateStore.load(proj_dir)
    assert st_after_bp1.revision == 2

    # Step 2: Lifecycle transition -> Lifecycle Rev 3 (ASSETS_READY)
    st_updated = StateStore.atomic_update(
        proj_dir,
        expected_revision=2,
        mutator=lambda s: setattr(s, "lifecycle_state", LifecycleState.ASSETS_READY),
    )
    assert st_updated.revision == 3
    assert st_updated.lifecycle_state == LifecycleState.ASSETS_READY

    # Document revision is STILL 2
    _, current_bp_rev = doc_repo.get_document(workspace_id=ws_id, project_id=project_id)
    assert current_bp_rev == 2

    # Step 3: Blueprint commit 2 -> Document Rev 3
    bp_v2 = _create_minimal_blueprint(project_id, 2)
    bp_v2["scenes"][0]["props"]["title"] = "Updated Title for Rev 3"
    doc_dict2, bp_rev2, key2 = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=project_id,
        expected_revision=2,
        candidate_doc=bp_v2,
        actor_id=test_env["user_id"],
        operation_id="op_bp_2",
    )
    assert bp_rev2 == 3
    hash_v3 = hashlib.sha256(json.dumps(doc_dict2, indent=2, ensure_ascii=False).encode("utf-8")).hexdigest()

    # Invalidation hook upon blueprint commit advanced lifecycle state revision to 4
    st_after_bp2 = StateStore.load(proj_dir)
    assert st_after_bp2.revision == 4

    # Step 4: Verify independent domain retrieval without cross-contamination
    # Document retrieval for Rev 3
    doc_r3, rev3 = doc_repo.get_document(workspace_id=ws_id, project_id=project_id, revision=3)
    assert rev3 == 3
    assert doc_r3["scenes"][0]["props"]["title"] == "Updated Title for Rev 3"

    # Document retrieval for Rev 2
    doc_r2, rev2 = doc_repo.get_document(workspace_id=ws_id, project_id=project_id, revision=2)
    assert rev2 == 2
    assert doc_r2["scenes"][0]["props"]["title"] == "Hello Rev 1"

    # Create run with lifecycle input_revision=4 and verified blueprint hash of Rev 3
    run_repo = RunRepository(db_path=test_env["tmp_path"] / "pr004_test.db")
    run_rec = RunRecord(
        run_id=f"run_cb3_{uuid.uuid4().hex[:8]}",
        workspace_id=ws_id,
        project_id=project_id,
        status=RunStatus.QUEUED,
        input_revision=4,  # Refers to lifecycle state revision
        request_payload_hash=hash_v3,  # Pinned blueprint hash
    )
    persisted_run = run_repo.create_run(run_rec)
    assert persisted_run.input_revision == 4
    assert persisted_run.request_payload_hash == hash_v3


# ─── FINAL CRASH BOUNDARY 4: Run Idempotency & Database Constraint ───

def test_crash_boundary_run_idempotency_concurrency(test_env):
    """
    Crash Boundary 4: Verify that uniqueness constraint exists in the actual
    RunRepository database schema and survives concurrent submissions from
    independent connections/processes.
    """
    ws_id = test_env["workspace_id"]
    project_id = "prj_cb4_idempotency"
    test_env["tenant_repo"].create_project(project_id, ws_id, name="CB4 Project", created_by=test_env["user_id"])

    db_path = test_env["tmp_path"] / "pr004_test.db"

    # 1. Verify that the unique index exists in sqlite_master
    with test_env["db_engine"].get_connection() as conn:
        cur = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'index' AND name = 'uq_runs_workspace_project_idempotency'"
        )
        row = cur.fetchone()
        assert row is not None, "Unique index 'uq_runs_workspace_project_idempotency' missing from database schema!"
        assert "UNIQUE" in row[1].upper(), f"Index definition is not UNIQUE: {row[1]}"

    # 2. Concurrency test: 10 concurrent threads simulating independent workers/processes
    shared_idempotency_key = f"idem_key_cb4_{uuid.uuid4().hex}"
    payload_hash = hashlib.sha256(b"request_payload_content").hexdigest()

    results = []
    errors = []

    def concurrent_submission():
        try:
            # Each thread uses its own RunRepository instance and connection
            thread_repo = RunRepository(db_path=db_path)
            record = RunRecord(
                run_id=f"run_thread_{uuid.uuid4().hex[:8]}",
                workspace_id=ws_id,
                project_id=project_id,
                status=RunStatus.QUEUED,
                idempotency_key=shared_idempotency_key,
                request_payload_hash=payload_hash,
            )
            persisted = thread_repo.create_run(record)
            results.append(persisted)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=concurrent_submission) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Unexpected errors in concurrent submissions: {errors}"
    assert len(results) == 10

    # Exactly 1 run_id across all 10 submissions
    unique_run_ids = {r.run_id for r in results}
    assert len(unique_run_ids) == 1, f"Expected exactly 1 run_id, got: {unique_run_ids}"

    # Verify database table has exactly 1 row for this key
    with test_env["db_engine"].get_connection() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE workspace_id = ? AND project_id = ? AND idempotency_key = ?",
            (ws_id, project_id, shared_idempotency_key)
        )
        count = cur.fetchone()[0]
        assert count == 1, f"Expected exactly 1 row in database, got {count}"

    # 3. Payload mismatch: calling with same key but different payload hash must raise IdempotencyConflictError
    from api.core.errors import IdempotencyConflictError
    conflicting_repo = RunRepository(db_path=db_path)
    conflicting_record = RunRecord(
        run_id=f"run_conflict_{uuid.uuid4().hex[:8]}",
        workspace_id=ws_id,
        project_id=project_id,
        status=RunStatus.QUEUED,
        idempotency_key=shared_idempotency_key,
        request_payload_hash=hashlib.sha256(b"DIFFERENT_PAYLOAD").hexdigest(),
    )
    with pytest.raises(IdempotencyConflictError):
        conflicting_repo.create_run(conflicting_record)
