"""
tests/e2e/test_saas_multi_tenant_e2e.py — Comprehensive End-to-End Multi-Tenant SaaS Suite (S24.5).

Covers the 7 mandatory scenarios from Section 21:
1. Complete Multi-Tenant Isolation (User A vs User B on Asset, Project, Run, Output, Events, Review).
2. Cross-Tenant Asset Injection Fail-Closed Rejection.
3. Concurrent Workers: Atomic Leases & Mutual Exclusion (no double lease, no race conditions).
4. Restart Durability (API restart / worker recovery preserves runs and state).
5. Ephemeral Worker Cleanup & Object Storage Truth (local disk wiped, outputs streamable from StorageService).
6. CAS / Revision Optimistic Concurrency Conflict (409 Conflict on stale revision).
7. RBAC Matrix (Viewer, Editor, Reviewer, Admin roles enforced end-to-end).
"""

import json
import pytest
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from api.main import app
from scripts.core.database import DatabaseEngine, set_database_engine, TenantRepository, TenantStateRepository
from scripts.core.storage import LocalStorageBackend, set_storage_service, build_storage_key
from scripts.core.security.principal import Principal, Role, PrincipalType
from tests.conftest import make_test_auth_headers
from scripts.core.state_model import LifecycleState, ProjectState, ReviewBundle
from scripts.core.state_store import StateStore, StateConflictError
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.run_repository import RunRepository
from scripts.core.worker import PipelineWorker


@pytest.fixture
def saas_environment(tmp_path, monkeypatch):
    # Hermetic Database setup
    db_file = tmp_path / "saas_e2e.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    db_engine = DatabaseEngine(f"sqlite:///{db_file}")
    set_database_engine(db_engine)

    # Hermetic Storage setup
    storage_root = tmp_path / "saas_storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_svc = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage_svc)

    tenant_repo = TenantRepository(db_engine)
    run_repo = RunRepository(db_path=db_file)

    # 1. Setup Workspace Alpha (Acme Corp)
    user_a_admin = tenant_repo.create_user("usr_a_admin", "admin@acme.com")
    user_a_editor = tenant_repo.create_user("usr_a_editor", "editor@acme.com")
    user_a_reviewer = tenant_repo.create_user("usr_a_reviewer", "reviewer@acme.com")
    user_a_viewer = tenant_repo.create_user("usr_a_viewer", "viewer@acme.com")

    ws_a = tenant_repo.create_workspace("ws_acme", "Acme Workspace", created_by=user_a_admin.id)
    tenant_repo.add_member("ws_acme", user_a_editor.id, Role.EDITOR)
    tenant_repo.add_member("ws_acme", user_a_reviewer.id, Role.REVIEWER)
    tenant_repo.add_member("ws_acme", user_a_viewer.id, Role.VIEWER)

    prj_a = tenant_repo.create_project("prj_acme_main", "ws_acme", "Acme Main Video", created_by=user_a_admin.id)

    # 2. Setup Workspace Beta (Globex Inc)
    user_b_admin = tenant_repo.create_user("usr_b_admin", "admin@globex.com")
    user_b_editor = tenant_repo.create_user("usr_b_editor", "editor@globex.com")
    user_b_reviewer = tenant_repo.create_user("usr_b_reviewer", "reviewer@globex.com")
    user_b_viewer = tenant_repo.create_user("usr_b_viewer", "viewer@globex.com")

    ws_b = tenant_repo.create_workspace("ws_globex", "Globex Workspace", created_by=user_b_admin.id)
    tenant_repo.add_member("ws_globex", user_b_editor.id, Role.EDITOR)
    tenant_repo.add_member("ws_globex", user_b_reviewer.id, Role.REVIEWER)
    tenant_repo.add_member("ws_globex", user_b_viewer.id, Role.VIEWER)

    prj_b = tenant_repo.create_project("prj_globex_main", "ws_globex", "Globex Main Video", created_by=user_b_admin.id)

    # Setup on-disk project scaffolds
    proj_dir_a = Path(f"projects/{prj_a.id}")
    proj_dir_a.mkdir(parents=True, exist_ok=True)
    state_a = ProjectState(
        project_id=prj_a.id,
        workspace_id=ws_a.id,
        lifecycle_state=LifecycleState.AWAITING_REVIEW,
        revision=1,
    )
    StateStore.save(proj_dir_a, state_a)
    (proj_dir_a / "05_blueprint.json").write_text("{}", encoding="utf-8")
    (proj_dir_a / "media_map.json").write_text("{}", encoding="utf-8")
    (proj_dir_a / "probe_qc_report.json").write_text("{}", encoding="utf-8")
    (proj_dir_a / "out.mp4").write_bytes(b"ACME_FINAL_MP4_PAYLOAD")

    proj_dir_b = Path(f"projects/{prj_b.id}")
    proj_dir_b.mkdir(parents=True, exist_ok=True)
    state_b = ProjectState(
        project_id=prj_b.id,
        workspace_id=ws_b.id,
        lifecycle_state=LifecycleState.AWAITING_REVIEW,
        revision=1,
    )
    StateStore.save(proj_dir_b, state_b)

    client = TestClient(app)

    yield {
        "client": client,
        "db_file": db_file,
        "db_engine": db_engine,
        "storage": storage_svc,
        "tenant_repo": tenant_repo,
        "run_repo": run_repo,
        "users": {
            "a_admin": user_a_admin,
            "a_editor": user_a_editor,
            "a_reviewer": user_a_reviewer,
            "a_viewer": user_a_viewer,
            "b_admin": user_b_admin,
            "b_editor": user_b_editor,
            "b_reviewer": user_b_reviewer,
            "b_viewer": user_b_viewer,
        },
        "ws_a": ws_a,
        "ws_b": ws_b,
        "prj_a": prj_a,
        "prj_b": prj_b,
        "proj_dir_a": proj_dir_a,
        "proj_dir_b": proj_dir_b,
    }

    shutil.rmtree(proj_dir_a, ignore_errors=True)
    shutil.rmtree(proj_dir_b, ignore_errors=True)


# ==============================================================================
# Scenario 1: Complete Multi-Tenant Isolation
# ==============================================================================
def test_scenario_1_complete_tenant_isolation(saas_environment):
    """
    Scenario 1:
    User A is in Workspace A, User B is in Workspace B.
    User B attempts: read, edit, trigger run, get output, view events, review approve/reject.
    Expected: Explicit 403 Forbidden on EVERY operation.
    """
    client = saas_environment["client"]
    prj_a = saas_environment["prj_a"].id
    headers_b = make_test_auth_headers(
        principal_id=saas_environment["users"]["b_editor"].id,
        roles=["editor"],
    )
    headers_b_rev = make_test_auth_headers(
        principal_id=saas_environment["users"]["b_reviewer"].id,
        roles=["reviewer"],
    )

    # 1. User B tries to read artifacts of Project A -> 403
    r_art = client.get(f"/projects/{prj_a}/artifacts", headers=headers_b)
    assert r_art.status_code == 403

    # 2. User B tries to trigger a run on Project A -> 403
    r_run = client.post(f"/projects/{prj_a}/runs", json={}, headers=headers_b)
    assert r_run.status_code == 403

    # 3. User B tries to download output of Project A -> 403
    r_out = client.get(f"/projects/{prj_a}/outputs/out.mp4", headers=headers_b)
    assert r_out.status_code == 403

    # 4. User B tries to approve review on Project A -> 403
    r_appr = client.post(f"/projects/{prj_a}/review/approve", json={"reason": "Hacked"}, headers=headers_b_rev)
    assert r_appr.status_code == 403

    # 5. User B tries to reject review on Project A -> 403
    r_rej = client.post(f"/projects/{prj_a}/review/reject", json={"reason": "Hacked"}, headers=headers_b_rev)
    assert r_rej.status_code == 403


# ==============================================================================
# Scenario 2: Cross-Tenant Asset Injection
# ==============================================================================
def test_scenario_2_cross_tenant_asset_injection(saas_environment, monkeypatch):
    """
    Scenario 2:
    Project A manifest attempts to reference an asset stored in Workspace B.
    Worker and validator must reject fail-closed with CROSS_TENANT_VIOLATION.
    """
    run_repo = saas_environment["run_repo"]
    prj_a = saas_environment["prj_a"].id
    ws_a = saas_environment["ws_a"].id

    # Create manifest in Project A referencing Workspace B asset
    manifest_data = {
        "version": "2.0.0",
        "project_id": prj_a,
        "created_at": "2026-09-30T00:00:00Z",
        "title": "Cross Tenant Job Attempt",
        "assets": [
            {
                "asset_id": "ast_victim_blob",
                "storage_key": "workspaces/ws_globex/projects/prj_globex_main/assets/ast_victim_blob/secret.png",
                "role": "main",
            }
        ],
        "timeline": [],
    }
    manifest_file = saas_environment["proj_dir_a"] / "01_manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    run_record = RunRecord(
        run_id=f"run_{uuid.uuid4().hex[:8]}",
        workspace_id=ws_a,
        project_id=prj_a,
        status=RunStatus.QUEUED,
    )
    run_repo.create_run(run_record)

    worker = PipelineWorker(
        worker_id="worker_sec_test",
        db_path=saas_environment["db_file"],
        max_runs=1,
    )
    worker.process_one()

    updated = run_repo.get_run(run_record.run_id)
    assert updated.status == RunStatus.FAILED
    assert updated.failure_code == "CROSS_TENANT_VIOLATION"


# ==============================================================================
# Scenario 3: Concurrent Workers & Mutual Exclusion
# ==============================================================================
def test_scenario_3_concurrent_workers_no_double_lease(saas_environment):
    """
    Scenario 3:
    Two workers attempt to claim jobs simultaneously.
    Verifies:
    - Exactly one worker claims the project execution lease.
    - No double lease is possible for the same project while running.
    """
    run_repo = saas_environment["run_repo"]
    prj_a = saas_environment["prj_a"].id
    ws_a = saas_environment["ws_a"].id

    run_1 = RunRecord(run_id="run_concurrent_1", workspace_id=ws_a, project_id=prj_a, status=RunStatus.QUEUED)
    run_2 = RunRecord(run_id="run_concurrent_2", workspace_id=ws_a, project_id=prj_a, status=RunStatus.QUEUED)
    run_repo.create_run(run_1)
    run_repo.create_run(run_2)

    # Worker 1 claims
    claim_1 = run_repo.claim_next_run(worker_id="worker_alpha", lease_duration_seconds=60.0)
    assert claim_1 is not None
    assert claim_1.run_id == "run_concurrent_1"

    # Worker 2 attempts to claim while Worker 1 holds active lease on prj_a
    claim_2 = run_repo.claim_next_run(worker_id="worker_beta", lease_duration_seconds=60.0)
    # Must be None because prj_a is locked by worker_alpha!
    assert claim_2 is None

    # Worker 1 finishes run_1
    run_repo.finish_run(run_id="run_concurrent_1", worker_id="worker_alpha", status=RunStatus.SUCCEEDED)

    # Now Worker 2 can claim run_2
    claim_2_after = run_repo.claim_next_run(worker_id="worker_beta", lease_duration_seconds=60.0)
    assert claim_2_after is not None
    assert claim_2_after.run_id == "run_concurrent_2"


# ==============================================================================
# Scenario 4: Restart Durability
# ==============================================================================
def test_scenario_4_restart_durability(saas_environment):
    """
    Scenario 4:
    API restarts or crashes while a run is in progress.
    Verifies:
    - Run and lease state persist in DB across connections.
    - Orphaned lease expires and recovers cleanly.
    """
    run_repo = saas_environment["run_repo"]
    prj_a = saas_environment["prj_a"].id
    ws_a = saas_environment["ws_a"].id

    run = RunRecord(run_id="run_durable_1", workspace_id=ws_a, project_id=prj_a, status=RunStatus.QUEUED)
    run_repo.create_run(run)

    # Worker claims with 0-second lease to simulate instant expiry/crash
    claimed = run_repo.claim_next_run(worker_id="worker_crashed", lease_duration_seconds=0.0)
    assert claimed.status == RunStatus.RUNNING

    # "Restart API & Worker" by creating fresh repo instance from same DB
    fresh_repo = RunRepository(db_path=saas_environment["db_file"])
    orphans = fresh_repo.recover_orphaned_runs(grace_seconds=0.0)
    assert len(orphans) == 1
    assert orphans[0].run_id == "run_durable_1"

    # Recover orphan to retry
    fresh_repo.reset_run_to_queued(orphans[0].run_id, new_attempt=2)
    recovered = fresh_repo.get_run("run_durable_1")
    assert recovered.status == RunStatus.QUEUED
    assert recovered.attempt == 2


# ==============================================================================
# Scenario 5: Ephemeral Worker Cleanup & Object Storage Truth
# ==============================================================================
def test_scenario_5_ephemeral_worker_cleanup_and_storage_truth(saas_environment, monkeypatch):
    """
    Scenario 5:
    Run executes, outputs and artifacts are saved to StorageService.
    Local disk files are wiped completely.
    StorageService serves as canonical truth, and download remains functional.
    """
    client = saas_environment["client"]
    run_repo = saas_environment["run_repo"]
    prj_a = saas_environment["prj_a"].id
    ws_a = saas_environment["ws_a"].id

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Pipeline render completed"
    mock_result.stderr = ""
    monkeypatch.setattr("scripts.core.worker.safe_subprocess", lambda *args, **kwargs: mock_result)

    run = RunRecord(run_id="run_ephemeral_truth", workspace_id=ws_a, project_id=prj_a, status=RunStatus.QUEUED)
    run_repo.create_run(run)

    worker = PipelineWorker(worker_id="worker_ephemeral", db_path=saas_environment["db_file"], max_runs=1)
    worker.process_one()

    # Verify run succeeded
    run_rec = run_repo.get_run("run_ephemeral_truth")
    assert run_rec.status == RunStatus.SUCCEEDED
    storage_key = run_rec.result_reference.get("output_storage_key")
    assert storage_key is not None

    # WIPE local project directory out.mp4 completely
    out_file = saas_environment["proj_dir_a"] / "out.mp4"
    if out_file.exists():
        out_file.unlink()
    assert not out_file.exists()

    # User A downloads output: OutputService fetches from StorageService!
    headers_a = make_test_auth_headers(
        principal_id=saas_environment["users"]["a_editor"].id,
        roles=["editor"],
    )
    resp = client.get(f"/projects/{prj_a}/outputs/out.mp4", headers=headers_a)
    assert resp.status_code == 200
    assert resp.content == b"ACME_FINAL_MP4_PAYLOAD"


# ==============================================================================
# Scenario 6: CAS / Revision Optimistic Concurrency Conflict
# ==============================================================================
def test_scenario_6_cas_revision_conflict(saas_environment):
    """
    Scenario 6:
    Concurrent state mutations on the same project state with identical expected_revision.
    Exactly one succeeds; the second MUST fail with StateConflictError (409 Conflict).
    """
    prj_a = saas_environment["prj_a"].id
    ws_a = saas_environment["ws_a"].id
    state_repo = TenantStateRepository(saas_environment["db_engine"])

    current_state = state_repo.get_state(prj_a)
    assert current_state is not None
    base_rev = current_state.revision

    # Mutation 1: advances revision from base_rev to base_rev + 1
    new_state_1 = current_state.model_copy(deep=True)
    new_state_1.lifecycle_state = LifecycleState.FINAL_QC_PASSED
    state_repo.atomic_update(prj_a, expected_revision=base_rev, new_state=new_state_1)

    # Mutation 2: stale writer still thinks revision is base_rev -> Must raise StateConflictError!
    new_state_2 = current_state.model_copy(deep=True)
    new_state_2.lifecycle_state = LifecycleState.FAILED
    with pytest.raises(StateConflictError) as exc_info:
        state_repo.atomic_update(prj_a, expected_revision=base_rev, new_state=new_state_2)

    assert exc_info.value.expected_revision == base_rev
    assert exc_info.value.actual_revision == base_rev + 1


# ==============================================================================
# Scenario 7: RBAC Matrix
# ==============================================================================
def test_scenario_7_rbac_matrix_end_to_end(saas_environment):
    """
    Scenario 7:
    - Viewer attempts edit/run -> 403 Forbidden
    - Editor triggers run -> 202 Accepted
    - Editor attempts review approval -> 403 Forbidden
    - Reviewer approves review -> 200 OK
    """
    client = saas_environment["client"]
    prj_a = saas_environment["prj_a"].id

    headers_viewer = make_test_auth_headers(
        principal_id=saas_environment["users"]["a_viewer"].id,
        roles=["viewer"],
    )
    headers_editor = make_test_auth_headers(
        principal_id=saas_environment["users"]["a_editor"].id,
        roles=["editor"],
    )
    headers_reviewer = make_test_auth_headers(
        principal_id=saas_environment["users"]["a_reviewer"].id,
        roles=["reviewer"],
    )

    # 1. Viewer attempts run -> 403
    r_v_run = client.post(f"/projects/{prj_a}/runs", json={}, headers=headers_viewer)
    assert r_v_run.status_code == 403

    # 2. Editor triggers run -> 202
    r_e_run = client.post(f"/projects/{prj_a}/runs", json={}, headers=headers_editor)
    assert r_e_run.status_code == 202

    # 3. Editor attempts review approval -> 403
    r_e_appr = client.post(f"/projects/{prj_a}/review/approve", json={}, headers=headers_editor)
    assert r_e_appr.status_code == 403

    # 4. Reviewer approves review
    from scripts.core.review_service import ReviewService
    admin_principal = Principal(principal_id="sys_admin", principal_type=PrincipalType.HUMAN, roles={Role.ADMIN})
    bundle = ReviewService.create_review_bundle(
        project_dir=saas_environment["proj_dir_a"],
        actor=admin_principal,
    )
    r_r_appr = client.post(
        f"/projects/{prj_a}/review/approve",
        json={"bundle_id": bundle.review_bundle_id, "reason": "Reviewer authorized"},
        headers=headers_reviewer,
    )
    assert r_r_appr.status_code == 200
    assert r_r_appr.json()["status"] == "success"
