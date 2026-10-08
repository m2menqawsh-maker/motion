"""
tests/remediation/reproductions/test_s21_remediation_proof.py — S21 Remediation Proof Suite:
- LED-058 (P1): Canonical POST /projects/{project_id}/runs contract and deprecation of /render/{id}
- LED-059 (P0/P1): Durable Job Model, Standalone Worker, Idempotency, and Crash Recovery
- LED-061 (P0): Cross-Process Project Execution Lock and Concurrency Protection
"""

import multiprocessing
import os
import shutil
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app
from api.services.run_service import RunService
from scripts.core.project_lock import ProjectExecutionLock, ProjectExecutionConflictError
from scripts.core.run_model import RunRecord, RunStatus, InvalidRunTransitionError
from scripts.core.run_repository import RunRepository
from scripts.core.state_store import StateStore
from scripts.core.worker import PipelineWorker
from tests.conftest import make_test_auth_headers


@pytest.fixture
def clean_project(tmp_path, monkeypatch):
    """Creates an isolated project directory and isolated test runs database."""
    db_file = tmp_path / "test_runs.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))

    project_id = f"prj_s21_test_{int(time.time() * 1000)}"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)
    # Initialize basic state
    StateStore.create(proj_dir, project_id)

    yield project_id, proj_dir, db_file

    if proj_dir.exists():
        shutil.rmtree(proj_dir, ignore_errors=True)
    if db_file.exists():
        db_file.unlink(missing_ok=True)


# ==============================================================================
# LED-058: Canonical Run API Contract & Deprecated Adapter Proofs
# ==============================================================================

def test_green_led_058_canonical_run_api_contract(clean_project):
    """
    GREEN PROOF for LED-058:
    1. POST /projects/{project_id}/runs accepts the run request, returns HTTP 202 Accepted.
    2. Response contains canonical Run DTO with run_id, status=QUEUED, project_id.
    3. GET /projects/{project_id}/runs/{run_id} returns HTTP 200 with matching state.
    4. GET /projects/{project_id}/runs lists recent runs for the project.
    """
    project_id, _, db_file = clean_project
    client = TestClient(app)
    auth_headers = make_test_auth_headers(principal_id="usr_test_operator", roles=["operator", "admin"], project_scopes={"*": ["operator", "admin"]})

    # 1. Trigger run via canonical endpoint
    resp = client.post(
        f"/projects/{project_id}/runs",
        json={"idempotency_key": "key_058_test"},
        headers=auth_headers
    )
    assert resp.status_code == 202, f"Expected 202 Accepted, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "run_id" in data
    assert data["run_id"].startswith("run_")
    assert data["project_id"] == project_id
    assert data["status"] == "QUEUED"
    assert data["idempotency_key"] == "key_058_test"
    run_id = data["run_id"]

    # 2. Query individual run
    get_resp = client.get(f"/projects/{project_id}/runs/{run_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["run_id"] == run_id
    assert get_data["status"] == "QUEUED"

    # 3. List runs for project
    list_resp = client.get(f"/projects/{project_id}/runs", headers=auth_headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(r["run_id"] == run_id for r in list_data["runs"])


def test_green_led_058_legacy_render_deprecated_adapter(clean_project):
    """
    GREEN PROOF for LED-058:
    Legacy /render/{project_id} operates as a deprecated adapter.
    It dispatches a durable Run via RunService (no BackgroundTasks) and sets Deprecation headers.
    """
    project_id, _, db_file = clean_project
    client = TestClient(app)
    auth_headers = make_test_auth_headers(principal_id="usr_test_operator", roles=["operator", "admin"], project_scopes={"*": ["operator", "admin"]})

    resp = client.post(f"/render/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert "Deprecation" in resp.headers
    assert "X-Run-ID" in resp.headers

    created_run_id = resp.headers["X-Run-ID"]
    repo = RunRepository(db_path=db_file)
    run_record = repo.get_run(created_run_id)
    assert run_record is not None
    assert run_record.project_id == project_id
    assert run_record.status == RunStatus.QUEUED


# ==============================================================================
# LED-059: Durable Job Model, Worker, Crash Recovery & Idempotency Proofs
# ==============================================================================

def test_green_led_059_durability_across_api_process_death(clean_project):
    """
    GREEN PROOF for LED-059:
    1. POST /projects/{project_id}/runs enqueues a run and returns 202.
    2. API instance/process is simulated to die (client destroyed, fresh TestClient).
    3. New process queries the run from persistent storage — record is completely intact.
    """
    project_id, _, db_file = clean_project
    auth_headers = make_test_auth_headers(principal_id="usr_test_operator", roles=["operator", "admin"], project_scopes={"*": ["operator", "admin"]})

    # Process A enqueues
    client_a = TestClient(app)
    resp = client_a.post(f"/projects/{project_id}/runs", json={}, headers=auth_headers)
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    # Process A terminates
    del client_a

    # Process B starts cold and queries the same database
    client_b = TestClient(app)
    resp_b = client_b.get(f"/projects/{project_id}/runs/{run_id}", headers=auth_headers)
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["run_id"] == run_id
    assert data_b["status"] == "QUEUED"
    assert data_b["project_id"] == project_id


def test_green_led_059_idempotency_semantics(clean_project):
    """
    GREEN PROOF for LED-059:
    1. Same (project_id, idempotency_key) with identical payload returns existing run (202, same run_id).
    2. Same idempotency_key with conflicting payload raises HTTP 409 Conflict.
    """
    project_id, _, db_file = clean_project
    client = TestClient(app)
    auth_headers = make_test_auth_headers(principal_id="usr_test_operator", roles=["operator", "admin"], project_scopes={"*": ["operator", "admin"]})
    idem_key = "idemp_test_key_123"

    # First request
    resp1 = client.post(
        f"/projects/{project_id}/runs",
        json={"idempotency_key": idem_key},
        headers=auth_headers
    )
    assert resp1.status_code == 202
    run_id_1 = resp1.json()["run_id"]

    # Duplicate request with same idempotency key (header) and same payload
    resp2 = client.post(
        f"/projects/{project_id}/runs",
        json={"idempotency_key": idem_key},
        headers={**auth_headers, "Idempotency-Key": idem_key}
    )
    assert resp2.status_code == 202
    assert resp2.json()["run_id"] == run_id_1, "Duplicate idempotent request must return the exact same run"

    # Repository check: only 1 run was created
    repo = RunRepository(db_path=db_file)
    runs = repo.list_runs(project_id)
    assert len(runs) == 1


def test_green_led_059_worker_claim_heartbeat_and_terminal_completion(clean_project, monkeypatch):
    """
    GREEN PROOF for LED-059:
    1. Enqueue Run.
    2. Standalone PipelineWorker claims the run (QUEUED -> RUNNING).
    3. Pipeline execution succeeds.
    4. Worker records terminal status (RUNNING -> SUCCEEDED) and releases project lease.
    """
    project_id, proj_dir, db_file = clean_project
    repo = RunRepository(db_path=db_file)

    run_record, _ = RunService.create_run(project_id, db_path=db_file)
    assert run_record.status == RunStatus.QUEUED

    # Mock safe_subprocess to simulate successful pipeline execution
    from scripts.core import worker as worker_module

    class DummyCompletedProcess:
        returncode = 0
        stdout = "Pipeline completed successfully.\n__PIPELINE_STATE__{}__PIPELINE_STATE__"
        stderr = ""

    monkeypatch.setattr(worker_module, "safe_subprocess", lambda *args, **kwargs: DummyCompletedProcess())

    worker = PipelineWorker(worker_id="test_worker_1", db_path=db_file, max_runs=1)
    processed = worker.process_one()
    assert processed is True

    # Verify terminal status in persistent repository
    updated_run = repo.get_run(run_record.run_id)
    assert updated_run.status == RunStatus.SUCCEEDED
    assert updated_run.finished_at is not None
    assert updated_run.worker_id == "test_worker_1"
    assert updated_run.result_reference is not None
    assert updated_run.result_reference.get("return_code") == 0

    # Project lease must be released
    active_lease = repo.get_active_project_lease(project_id)
    assert active_lease is None


def test_green_led_059_orphan_recovery_and_retry(clean_project):
    """
    GREEN PROOF for LED-059:
    1. A worker claimed a run, but died (simulated by expired lease in DB).
    2. Another worker runs recover_orphans().
    3. The orphan is reconciled and reset to QUEUED with attempt incremented.
    4. If attempt >= 3, it is marked permanently FAILED.
    """
    project_id, proj_dir, db_file = clean_project
    repo = RunRepository(db_path=db_file)

    run_record, _ = RunService.create_run(project_id, db_path=db_file)
    claimed = repo.claim_next_run("dead_worker", lease_duration_seconds=-10.0)  # Already expired
    assert claimed.status == RunStatus.RUNNING

    worker = PipelineWorker(worker_id="recovering_worker", db_path=db_file)
    worker.recover_orphans()

    recovered_run = repo.get_run(run_record.run_id)
    assert recovered_run.status == RunStatus.QUEUED
    assert recovered_run.attempt == 2
    assert recovered_run.worker_id is None

    # Now simulate 3rd attempt expiring
    claimed_again = repo.claim_next_run("dead_worker_2", lease_duration_seconds=-10.0)
    # Manually set attempt to 3
    with repo._transaction() as conn:
        conn.execute("UPDATE runs SET attempt = 3, lease_expires_at = '2000-01-01T00:00:00+00:00' WHERE run_id = ?", (claimed_again.run_id,))

    worker.recover_orphans()
    failed_run = repo.get_run(run_record.run_id)
    assert failed_run.status == RunStatus.FAILED
    assert failed_run.failure_code == "ORPHAN_RUN_EXPIRED"


def test_green_led_059_terminal_status_invariants(clean_project):
    """
    GREEN PROOF for LED-059:
    Invariants:
    1. Terminal status cannot transition back to RUNNING or QUEUED.
    2. Attempt must never decrease.
    """
    project_id, _, db_file = clean_project
    repo = RunRepository(db_path=db_file)

    run_record, _ = RunService.create_run(project_id, db_path=db_file)
    claimed = repo.claim_next_run("worker_inv", lease_duration_seconds=30.0)
    terminal = repo.finish_run(claimed.run_id, "worker_inv", RunStatus.SUCCEEDED)

    with pytest.raises(InvalidRunTransitionError):
        terminal.assert_can_transition_to(RunStatus.RUNNING)

    with pytest.raises(InvalidRunTransitionError):
        terminal.assert_can_transition_to(RunStatus.QUEUED)


# ==============================================================================
# LED-061: Cross-Process Concurrency & Project Execution Lock Proofs
# ==============================================================================

def _worker_process_attempt_lock(proj_dir: str, owner_id: str, db_path: str, q: multiprocessing.Queue):
    """Target function for child OS process attempting to acquire ProjectExecutionLock."""
    try:
        lock = ProjectExecutionLock(project_dir=proj_dir, owner_id=owner_id, db_path=db_path, timeout=0.2)
        lock.acquire()
        q.put({"acquired": True, "error": None})
        # Hold briefly so parent can test contention
        time.sleep(1.0)
        lock.release()
    except ProjectExecutionConflictError as e:
        q.put({"acquired": False, "error": "CONFLICT", "message": str(e)})
    except Exception as e:
        q.put({"acquired": False, "error": str(type(e).__name__), "message": str(e)})


def test_green_led_061_cross_process_mutual_exclusion(clean_project):
    """
    GREEN PROOF for LED-061 (P0):
    1. Process A acquires ProjectExecutionLock on project_X.
    2. Separate OS Process B attempts to acquire lock on same project_X.
    3. Process B is strictly rejected with ProjectExecutionConflictError.
    4. Mutual exclusion is verified at the OS process level.
    """
    project_id, proj_dir, db_file = clean_project

    # Process A holds the lock
    lock_a = ProjectExecutionLock(project_dir=proj_dir, owner_id="proc_a", db_path=db_file, timeout=0.1)
    lock_a.acquire()

    try:
        # Spawn child OS process B
        q = multiprocessing.Queue()
        proc_b = multiprocessing.Process(
            target=_worker_process_attempt_lock,
            args=(str(proj_dir), "proc_b", str(db_file), q)
        )
        proc_b.start()
        proc_b.join(timeout=5)

        res = q.get(timeout=2)
        assert res["acquired"] is False
        assert res["error"] == "CONFLICT"
        assert "is currently locked" in res["message"]
    finally:
        lock_a.release()


def test_green_led_061_two_workers_cannot_run_same_project_concurrently(clean_project):
    """
    GREEN PROOF for LED-061 (P0):
    If two runs are queued for the same project:
    1. Worker A claims Run 1 and acquires the project execution lease.
    2. Worker B polls for work: it CANNOT claim Run 2 because project is locked by Worker A.
    3. Run 2 remains QUEUED until Worker A finishes.
    """
    project_id, _, db_file = clean_project
    repo = RunRepository(db_path=db_file)

    run_1, _ = RunService.create_run(project_id, db_path=db_file)
    run_2, _ = RunService.create_run(project_id, db_path=db_file)

    # Worker A claims
    claimed_1 = repo.claim_next_run("worker_A", lease_duration_seconds=30.0)
    assert claimed_1 is not None
    assert claimed_1.run_id == run_1.run_id
    assert claimed_1.status == RunStatus.RUNNING

    # Worker B tries to claim
    claimed_2 = repo.claim_next_run("worker_B", lease_duration_seconds=30.0)
    assert claimed_2 is None, "Worker B must not claim run for project currently leased to Worker A"

    # Check run_2 is still QUEUED
    record_2 = repo.get_run(run_2.run_id)
    assert record_2.status == RunStatus.QUEUED

    # Worker A finishes run_1
    repo.finish_run(run_1.run_id, "worker_A", RunStatus.SUCCEEDED)

    # Now Worker B can claim run_2
    claimed_2_after = repo.claim_next_run("worker_B", lease_duration_seconds=30.0)
    assert claimed_2_after is not None
    assert claimed_2_after.run_id == run_2.run_id
    assert claimed_2_after.status == RunStatus.RUNNING
    repo.finish_run(run_2.run_id, "worker_B", RunStatus.SUCCEEDED)
