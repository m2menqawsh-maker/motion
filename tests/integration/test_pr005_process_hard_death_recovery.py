"""
tests/integration/test_pr005_process_hard_death_recovery.py
===========================================================
Authoritative Integration Verification Suite for PR-005 Phase 2:
Genuine Separate-OS-Process Hard-Death and Durable Recovery.

Verifies:
- Crash Boundary 1: StateStore writes .pipeline_state.json to disk but process
  exits (SIGKILL / os._exit) before SQL commit. Fresh process loads and authoritatively
  heals disk copy back to SQL truth; no lifecycle advance, no review bypass.
- Crash Boundary 2: Canonical Blueprint artifact commits to SQL, but process
  exits before review invalidation or disk mirror update completes. Fresh process
  rejects stale approval by exact authoritative content hash and invalidates bundle fail-closed.
- Crash Boundary 3: Worker process claims Run and receives SIGKILL; fresh worker
  recovers orphaned Run, and stale worker is strictly fenced from publishing output or completing.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional

import pytest

from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.security.principal import Role
from scripts.core.state_model import LifecycleState, ProjectState, ReviewDecisionType
from scripts.core.state_store import StateStore
from scripts.core.review_service import ReviewService, RenderNotAuthorizedError, create_local_trusted_principal
from scripts.core.canonical_document_repository import CanonicalDocumentRepository
from scripts.core.storage import LocalStorageBackend, set_storage_service
from scripts.core.run_repository import RunRepository
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.worker import PipelineWorker


# =============================================================================
# CHILD PROCESS DISPATCHER (Invoked via subprocess with separate PID)
# =============================================================================

def _child_entrypoint():
    """CLI dispatcher for child worker/mutator processes under test."""
    if len(sys.argv) < 2:
        sys.exit(1)

    subcmd = sys.argv[1]

    if subcmd == "statestore_crash":
        # Args: proj_dir, ws_id, project_id, db_url, barrier_file, kill_mode
        proj_dir = Path(sys.argv[2])
        ws_id = sys.argv[3]
        project_id = sys.argv[4]
        db_url = sys.argv[5]
        barrier_file = Path(sys.argv[6])
        kill_mode = sys.argv[7]  # "exit" or "wait_kill"

        os.environ["AGY_IS_MANAGED"] = "1"
        os.environ["DATABASE_URL"] = db_url
        engine = DatabaseEngine(db_url=db_url)
        set_database_engine(engine)

        orig_sync = StateStore._sync_to_db

        def crashing_sync(state, expected_revision=None):
            # Barrier: Disk has been written via _persist_atomic, touch barrier before SQL sync!
            barrier_file.write_text(json.dumps({
                "pid": os.getpid(),
                "stage": "disk_written_before_sql_sync",
                "revision": state.revision,
                "lifecycle_state": state.lifecycle_state.value if hasattr(state.lifecycle_state, "value") else str(state.lifecycle_state),
            }), encoding="utf-8")

            if kill_mode == "exit":
                # Hard exit immediately without running Python atexit or rollback handlers
                os._exit(77)
            else:
                # Wait for parent to send SIGKILL
                while True:
                    time.sleep(0.1)

        StateStore._sync_to_db = crashing_sync

        cur = StateStore.load(proj_dir)
        StateStore.atomic_update(
            proj_dir,
            expected_revision=cur.revision,
            mutator=lambda s: setattr(s, "lifecycle_state", LifecycleState.MATERIALIZED),
        )

    elif subcmd == "blueprint_crash":
        # Args: proj_dir, ws_id, project_id, db_url, storage_dir, barrier_file, kill_mode
        proj_dir = Path(sys.argv[2])
        ws_id = sys.argv[3]
        project_id = sys.argv[4]
        db_url = sys.argv[5]
        storage_dir = Path(sys.argv[6])
        barrier_file = Path(sys.argv[7])
        kill_mode = sys.argv[8]

        os.environ["AGY_IS_MANAGED"] = "1"
        os.environ["DATABASE_URL"] = db_url
        engine = DatabaseEngine(db_url=db_url)
        set_database_engine(engine)
        storage = LocalStorageBackend(root_dir=storage_dir)
        set_storage_service(storage)

        doc_repo = CanonicalDocumentRepository(engine, storage)

        orig_invalidate = ReviewService.invalidate_review

        def crashing_invalidate(*args, **kwargs):
            # Barrier: Blueprint committed in SQL project_artifact_versions, but review not yet invalidated!
            barrier_file.write_text(json.dumps({
                "pid": os.getpid(),
                "stage": "blueprint_sql_committed_before_review_invalidation",
            }), encoding="utf-8")

            if kill_mode == "exit":
                os._exit(88)
            else:
                while True:
                    time.sleep(0.1)

        ReviewService.invalidate_review = crashing_invalidate

        # Mutated blueprint candidate
        bp_data = {
            "schema_version": "2.0.0",
            "project_id": project_id,
            "aspect_ratio": "16:9",
            "fps": 30,
            "width": 1920,
            "height": 1080,
            "scenes": [
                {
                    "scene_id": "sc_01",
                    "template": "animatedtext-element",
                    "durationFrames": 90,
                    "startFrame": 0,
                    "props": {"text": "Mutated in Rev 2"},
                }
            ],
            "totalDurationFrames": 90,
        }

        doc_repo.commit_candidate(
            workspace_id=ws_id,
            project_id=project_id,
            expected_revision=2,
            candidate_doc=bp_data,
            actor_id="usr_tester",
            operation_id="op_bp_crash_test",
        )

    elif subcmd == "worker_claim_and_wait":
        # Args: db_url, worker_id, barrier_file
        db_url = sys.argv[2]
        worker_id = sys.argv[3]
        barrier_file = Path(sys.argv[4])

        db_path = db_url.replace("sqlite:///", "")
        repo = RunRepository(db_path=db_path)

        # Claim next run
        claimed = repo.claim_next_run(worker_id=worker_id, lease_duration_seconds=5.0)
        if claimed:
            barrier_file.write_text(json.dumps({
                "pid": os.getpid(),
                "worker_id": worker_id,
                "run_id": claimed.run_id,
                "attempt": claimed.attempt,
                "status": claimed.status.value,
            }), encoding="utf-8")
            # Loop forever until killed by SIGKILL
            while True:
                time.sleep(0.1)
        else:
            sys.exit(2)

    elif subcmd == "stale_worker_finish":
        # Args: db_url, worker_id, run_id, barrier_file
        db_url = sys.argv[2]
        worker_id = sys.argv[3]
        run_id = sys.argv[4]
        barrier_file = Path(sys.argv[5])

        db_path = db_url.replace("sqlite:///", "")
        repo = RunRepository(db_path=db_path)

        # Attempt to finish run as stale worker
        try:
            repo.finish_run(
                run_id=run_id,
                worker_id=worker_id,
                status=RunStatus.SUCCEEDED,
                result_reference={"stale_publish": True},
            )
            barrier_file.write_text(json.dumps({"success": True}), encoding="utf-8")
        except Exception as e:
            barrier_file.write_text(json.dumps({"success": False, "error": str(e)}), encoding="utf-8")

    sys.exit(0)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def recovery_env(tmp_path, monkeypatch):
    """Hermetic filesystem and SQLite DB environment for OS process crash tests."""
    db_file = tmp_path / "crash_recovery.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("AGY_IS_MANAGED", "1")

    engine = DatabaseEngine(db_url=db_url)
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    tenant_repo = TenantRepository(engine)
    user = tenant_repo.create_user("usr_rec_admin", "rec_admin@motion.local")
    ws = tenant_repo.create_workspace("ws_rec", "Recovery Workspace", created_by=user.id)
    tenant_repo.add_member(ws.id, user.id, Role.ADMIN)

    yield {
        "engine": engine,
        "db_file": db_file,
        "db_url": db_url,
        "storage": storage,
        "storage_dir": storage_root,
        "tenant_repo": tenant_repo,
        "workspace_id": ws.id,
        "user_id": user.id,
        "tmp_path": tmp_path,
    }


# =============================================================================
# CRASH BOUNDARY 1: StateStore Disk Write vs SQL Sync Crash
# =============================================================================

def test_real_process_death_statestore_fs_vs_sql_recovery(recovery_env):
    """
    Genuine OS Process Hard-Death Test (Crash Window 1):
    Child process writes .pipeline_state.json with revision 3 (MATERIALIZED) to disk,
    but is killed via SIGKILL / os._exit before the SQL database transaction commits.

    Verifies:
    1. Child process PID is distinct and terminates abnormally with SIGKILL (or exit code 77).
    2. Persisted pre-restart state has split-brain: disk at rev 3, DB at rev 2.
    3. Fresh post-restart process calls StateStore.load(pdir).
    4. Authoritative SQL state wins: safely recovers to rev 2 (PLAN_READY).
    5. Disk .pipeline_state.json is healed back to rev 2 (no unauthorized MATERIALIZED advance).
    6. Subsequent legitimate workflow update from healed rev 2 succeeds cleanly.
    """
    ws_id = recovery_env["workspace_id"]
    project_id = "prj_cb1_os_crash"
    recovery_env["tenant_repo"].create_project(project_id, ws_id, name="Crash Project 1", created_by=recovery_env["user_id"])

    proj_dir = Path("projects") / project_id
    if proj_dir.exists():
        shutil.rmtree(proj_dir, ignore_errors=True)
    proj_dir.mkdir(parents=True, exist_ok=True)
    barrier_file = recovery_env["tmp_path"] / "cb1_barrier.json"

    # Step 1: Initialize normal state: Rev 2, PLAN_READY in both disk and SQL
    StateStore.create(proj_dir, project_id, initial_lifecycle=LifecycleState.DRAFT, workspace_id=ws_id)
    cur = StateStore.load(proj_dir)
    StateStore.atomic_update(
        proj_dir,
        expected_revision=cur.revision,
        mutator=lambda s: setattr(s, "lifecycle_state", LifecycleState.PLAN_READY),
    )

    state_before = StateStore.load(proj_dir)
    assert state_before.revision == 2
    assert state_before.lifecycle_state == LifecycleState.PLAN_READY

    # Step 2: Spawn child process to perform atomic_update with hard exit before SQL sync
    cmd = [
        sys.executable,
        __file__,
        "statestore_crash",
        str(proj_dir),
        ws_id,
        project_id,
        recovery_env["db_url"],
        str(barrier_file),
        "wait_kill",  # Child will wait for parent SIGKILL
    ]

    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent.parent), AGY_IS_MANAGED="1")
    proc = subprocess.Popen(cmd, env=env)
    child_pid = proc.pid
    assert child_pid != os.getpid(), "Child PID must be distinct from test parent PID"

    try:
        # Bounded wait for child to reach barrier (disk written, before SQL sync)
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if barrier_file.exists():
                break
            time.sleep(0.05)

        assert barrier_file.exists(), "Child process did not reach disk write barrier within timeout"
        barrier_data = json.loads(barrier_file.read_text(encoding="utf-8"))
        assert barrier_data["pid"] == child_pid
        assert barrier_data["stage"] == "disk_written_before_sql_sync"

        # Step 3: Hard kill child process with SIGKILL
        os.kill(child_pid, signal.SIGKILL)
        exit_code = proc.wait(timeout=5.0)

        # On POSIX, exit_code for SIGKILL is -9
        assert exit_code == -signal.SIGKILL or exit_code == -9, f"Expected SIGKILL (-9), got {exit_code}"

        # Step 4: Verify uncommitted pre-restart state
        # Disk has revision 3 (MATERIALIZED)
        disk_raw = json.loads((proj_dir / StateStore.STATE_FILE).read_text(encoding="utf-8"))
        assert disk_raw["revision"] == 3
        assert disk_raw["lifecycle_state"] == LifecycleState.MATERIALIZED.value

        # SQL still has authoritative revision 2 (PLAN_READY)
        with recovery_env["engine"].get_connection() as conn:
            cur_sql = conn.execute("SELECT revision, lifecycle_state FROM project_states WHERE project_id = ?", (project_id,)).fetchone()
            assert cur_sql[0] == 2
            assert cur_sql[1] == LifecycleState.PLAN_READY.value

        # Step 5: Post-restart recovery in fresh process context
        reloaded = StateStore.load(proj_dir)

        # Assert: DB authoritative state restored
        assert reloaded.revision == 2
        assert reloaded.lifecycle_state == LifecycleState.PLAN_READY

        # Assert: Disk was healed back to revision 2
        healed_disk = json.loads((proj_dir / StateStore.STATE_FILE).read_text(encoding="utf-8"))
        assert healed_disk["revision"] == 2
        assert healed_disk["lifecycle_state"] == LifecycleState.PLAN_READY.value

        # Step 6: Verify next legitimate update from healed state succeeds
        next_update = StateStore.atomic_update(
            proj_dir,
            expected_revision=2,
            mutator=lambda s: setattr(s, "lifecycle_state", LifecycleState.MATERIALIZED),
        )
        assert next_update.revision == 3
        assert next_update.lifecycle_state == LifecycleState.MATERIALIZED

    finally:
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
        if proj_dir.exists():
            import shutil
            shutil.rmtree(proj_dir, ignore_errors=True)


# =============================================================================
# CRASH BOUNDARY 2: Blueprint SQL Commit vs Review Invalidation Crash
# =============================================================================

def test_real_process_death_blueprint_commit_vs_review_invalidation(recovery_env):
    """
    Genuine OS Process Hard-Death Test (Crash Window 2):
    Child process commits a new canonical blueprint to SQL (project_artifact_versions),
    but is killed via SIGKILL before downstream review invalidation finishes.

    Verifies:
    1. Child process PID is distinct and terminated via SIGKILL.
    2. SQL has committed Blueprint Rev 2, but on-disk state still has old active ReviewBundle (Rev 1).
    3. Fresh process restarts: ReviewService.assert_render_authorized(proj_dir) fails closed.
    4. Stale approval cannot authorize rendering; bundle is permanently invalidated.
    """
    ws_id = recovery_env["workspace_id"]
    project_id = "prj_cb2_bp_crash"
    recovery_env["tenant_repo"].create_project(project_id, ws_id, name="Crash Project 2", created_by=recovery_env["user_id"])

    proj_dir = Path("projects") / project_id
    if proj_dir.exists():
        shutil.rmtree(proj_dir, ignore_errors=True)
    proj_dir.mkdir(parents=True, exist_ok=True)
    barrier_file = recovery_env["tmp_path"] / "cb2_barrier.json"

    # Step 1: Initialize Project at Rev 1 with Canonical Blueprint and Approval
    StateStore.create(proj_dir, project_id, initial_lifecycle=LifecycleState.DRAFT, workspace_id=ws_id)
    doc_repo = CanonicalDocumentRepository(recovery_env["engine"], recovery_env["storage"])

    bp_v1 = {
        "schema_version": "2.0.0",
        "project_id": project_id,
        "aspect_ratio": "16:9",
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "scenes": [
            {
                "scene_id": "sc_01",
                "template": "animatedtext-element",
                "durationFrames": 90,
                "startFrame": 0,
                "props": {"text": "Original Rev 1"},
            }
        ],
        "totalDurationFrames": 90,
    }
    doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=project_id,
        expected_revision=1,
        candidate_doc=bp_v1,
        actor_id=recovery_env["user_id"],
        operation_id="op_cb2_init",
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
    principal = create_local_trusted_principal("reviewer_cb2")
    ReviewService.approve(proj_dir, bundle.review_bundle_id, principal=principal, reason="Initial Rev 1 Approval")

    # Initial check: render is authorized for Rev 1
    assert ReviewService.assert_render_authorized(proj_dir).is_authorized is True

    # Step 2: Spawn child process to commit Rev 2 and kill at barrier before review invalidation
    cmd = [
        sys.executable,
        __file__,
        "blueprint_crash",
        str(proj_dir),
        ws_id,
        project_id,
        recovery_env["db_url"],
        str(recovery_env["storage_dir"]),
        str(barrier_file),
        "wait_kill",
    ]

    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent.parent), AGY_IS_MANAGED="1")
    proc = subprocess.Popen(cmd, env=env)
    child_pid = proc.pid
    assert child_pid != os.getpid()

    try:
        # Bounded wait for barrier
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if barrier_file.exists():
                break
            time.sleep(0.05)

        assert barrier_file.exists(), "Child process did not reach blueprint commit barrier within timeout"

        # Step 3: Hard kill child process
        os.kill(child_pid, signal.SIGKILL)
        exit_code = proc.wait(timeout=5.0)
        assert exit_code in (-signal.SIGKILL, -9)

        # Step 4: Verify pre-restart state
        # In SQL: project_artifact_versions has revision 2 committed!
        with recovery_env["engine"].get_connection() as conn:
            cur_art = conn.execute(
                "SELECT revision, content_hash FROM project_artifact_versions WHERE project_id = ? AND artifact_kind = 'blueprint' ORDER BY revision DESC LIMIT 1",
                (project_id,)
            ).fetchone()
            assert cur_art is not None
            assert cur_art[0] == 3

        # Step 5: Post-restart recovery check:
        # Fresh execution must detect that DB canonical blueprint is revision 2 whereas active bundle is for revision 1.
        # It MUST raise RenderNotAuthorizedError and permanently invalidate the stale bundle!
        with pytest.raises(RenderNotAuthorizedError) as exc_info:
            ReviewService.assert_render_authorized(proj_dir)

        assert "REVIEW_BUNDLE_STALE" in str(exc_info.value) or "CANONICAL_BLUEPRINT" in str(exc_info.value)

        # Verify disk state after recovery: bundle and decision are permanently INVALIDATED
        reloaded_state = StateStore.load(proj_dir)
        assert reloaded_state.review_bundles[0].status == "INVALIDATED"
        assert reloaded_state.review_decisions[0].decision == ReviewDecisionType.INVALIDATED
        assert not (proj_dir / ".studio_approved").exists()

    finally:
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
        if proj_dir.exists():
            import shutil
            shutil.rmtree(proj_dir, ignore_errors=True)


# =============================================================================
# CRASH BOUNDARY 3: Worker OS SIGKILL, Orphan Recovery & Fencing
# =============================================================================

def test_real_process_death_worker_lease_fencing_and_orphan_recovery(recovery_env):
    """
    Genuine OS Process Hard-Death Test (Crash Window 3):
    Child worker claims Run 1 with lease, receives SIGKILL during execution.
    Fresh worker process recovers the orphaned run and finishes it.
    A stale worker attempting to finish after lease expiry is strictly fenced.

    Verifies:
    1. Child worker PID is killed by SIGKILL while holding active lease.
    2. Run status remains RUNNING until lease expires or orphan recovery intervenes.
    3. Orphan recovery resets run to QUEUED with attempt incremented.
    4. Stale worker attempting to mark SUCCEEDED after lease expiry fails.
    5. Fresh worker claims and finishes run cleanly.
    """
    ws_id = recovery_env["workspace_id"]
    project_id = "prj_cb3_worker_crash"
    recovery_env["tenant_repo"].create_project(project_id, ws_id, name="Crash Project 3", created_by=recovery_env["user_id"])

    run_repo = RunRepository(db_path=recovery_env["db_file"])
    barrier_file = recovery_env["tmp_path"] / "cb3_barrier.json"

    # Step 1: Create a QUEUED run
    run_id = "run_cb3_test_001"
    run_rec = RunRecord(
        run_id=run_id,
        workspace_id=ws_id,
        project_id=project_id,
        status=RunStatus.QUEUED,
        input_revision=1,
    )
    run_repo.create_run(run_rec)

    # Step 2: Spawn child worker process to claim run and wait
    child_worker_id = "worker_child_sigkill_01"
    cmd = [
        sys.executable,
        __file__,
        "worker_claim_and_wait",
        recovery_env["db_url"],
        child_worker_id,
        str(barrier_file),
    ]

    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent.parent))
    proc = subprocess.Popen(cmd, env=env)
    child_pid = proc.pid
    assert child_pid != os.getpid()

    try:
        # Bounded wait for child to claim
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if barrier_file.exists():
                break
            time.sleep(0.05)

        assert barrier_file.exists(), "Child worker did not claim run within timeout"
        barrier_data = json.loads(barrier_file.read_text(encoding="utf-8"))
        assert barrier_data["pid"] == child_pid
        assert barrier_data["run_id"] == run_id
        assert barrier_data["status"] == "RUNNING"

        # Check DB: Run is indeed RUNNING and worker_id is child_worker_id
        claimed_run = run_repo.get_run(run_id)
        assert claimed_run.status == RunStatus.RUNNING
        assert claimed_run.worker_id == child_worker_id
        assert claimed_run.attempt == 1

        # Step 3: Send SIGKILL to child worker process
        os.kill(child_pid, signal.SIGKILL)
        exit_code = proc.wait(timeout=5.0)
        assert exit_code in (-signal.SIGKILL, -9)

        # Step 4: Simulate stale worker attempting to finish after lease expiry
        # Force lease expiry by backdating expiry in SQLite
        with recovery_env["engine"].get_connection() as conn:
            conn.execute(
                "UPDATE project_execution_leases SET expires_at = '2000-01-01T00:00:00Z' WHERE project_id = ?",
                (project_id,)
            )
            conn.execute(
                "UPDATE runs SET lease_expires_at = '2000-01-01T00:00:00Z' WHERE run_id = ?",
                (run_id,)
            )

        # Spawn a separate child process representing the stale worker trying to finish
        stale_barrier = recovery_env["tmp_path"] / "cb3_stale_barrier.json"
        cmd_stale = [
            sys.executable,
            __file__,
            "stale_worker_finish",
            recovery_env["db_url"],
            child_worker_id,
            run_id,
            str(stale_barrier),
        ]
        res_stale = subprocess.run(cmd_stale, env=env, capture_output=True, text=True)
        assert res_stale.returncode == 0
        assert stale_barrier.exists()
        stale_res = json.loads(stale_barrier.read_text(encoding="utf-8"))
        # Fencing: Stale worker finish must fail!
        assert stale_res["success"] is False
        assert "lease" in stale_res.get("error", "").lower() or "fenced" in stale_res.get("error", "").lower()

        # Step 5: Fresh worker performs orphan recovery
        fresh_worker = PipelineWorker(
            worker_id="worker_fresh_02",
            db_path=recovery_env["db_file"],
            max_runs=1,
        )
        fresh_worker.recover_orphans()

        # Run was reset to QUEUED for retry with attempt = 2
        recovered_run = run_repo.get_run(run_id)
        assert recovered_run.status == RunStatus.QUEUED
        assert recovered_run.attempt == 2

        # Step 6: Fresh worker can now claim the run
        fresh_claim = run_repo.claim_next_run(worker_id="worker_fresh_02", lease_duration_seconds=30.0)
        assert fresh_claim is not None
        assert fresh_claim.run_id == run_id
        assert fresh_claim.worker_id == "worker_fresh_02"
        assert fresh_claim.attempt == 2

        # Fresh worker finishes cleanly
        finished = run_repo.finish_run(
            run_id=run_id,
            worker_id="worker_fresh_02",
            status=RunStatus.SUCCEEDED,
            result_reference={"recovered": True},
        )
        assert finished.status == RunStatus.SUCCEEDED

    finally:
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass


if __name__ == "__main__":
    _child_entrypoint()
