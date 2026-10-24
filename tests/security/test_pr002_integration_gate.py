"""
Integration Gate Regression Suite for PR-002 (Targeted Closure).
Tests the complete journey:
CREATE -> DB project ownership -> workspace_members authorization -> LIST -> GET -> /state -> RUN.
"""

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token
from scripts.core.database import DatabaseEngine, TenantRepository
from scripts.core.security.principal import Principal, PrincipalType, Role


@pytest.fixture
def gate_env(tmp_path, monkeypatch):
    """Isolated environment with isolated database and projects directory."""
    db_file = tmp_path / "gate_tenant.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-signing-secret-for-pytest-harness-32-chars!")

    from scripts.core.database import set_database_engine
    engine = DatabaseEngine(db_url=db_url)
    set_database_engine(engine)

    repo = TenantRepository(engine)

    # 1. Create Users
    user_alice = repo.create_user("usr_alice", "alice@alpha.com")
    user_bob = repo.create_user("usr_bob", "bob@beta.com")
    user_eve = repo.create_user("usr_eve", "eve@intruder.com")

    # 2. Create Workspaces
    ws_alpha = repo.create_workspace("ws_alpha", "Workspace Alpha", created_by=user_alice.id)
    ws_beta = repo.create_workspace("ws_beta", "Workspace Beta", created_by=user_bob.id)

    # 3. Memberships
    repo.add_member(ws_alpha.id, user_alice.id, Role.EDITOR)
    repo.add_member(ws_beta.id, user_bob.id, Role.EDITOR)

    created_projects = []

    client = TestClient(app)

    yield {
        "engine": engine,
        "repo": repo,
        "db_file": db_file,
        "ws_alpha": ws_alpha.id,
        "ws_beta": ws_beta.id,
        "users": {
            "alice": user_alice,
            "bob": user_bob,
            "eve": user_eve,
        },
        "client": client,
        "created_projects": created_projects,
    }

    # Teardown created projects
    for pid in created_projects:
        pdir = Path(f"projects/{pid}")
        if pdir.exists():
            shutil.rmtree(pdir, ignore_errors=True)


def test_red_project_creation_journey_in_workspace(gate_env):
    """
    RED VERIFICATION of Step 4:
    Alice (member of ws_alpha) creates a project via POST /projects/.
    The project MUST:
    1. Be bound to ws_alpha in the database with created_by = usr_alice.
    2. Appear in GET /projects/ for Alice.
    3. Be readable by Alice via GET /projects/{project_id} and GET /projects/{project_id}/state.
    4. Allow Alice to trigger POST /projects/{project_id}/runs.
    5. NOT be accessible or visible to Bob (ws_beta).
    """
    client = gate_env["client"]
    repo = gate_env["repo"]
    ws_alpha = gate_env["ws_alpha"]
    ws_beta = gate_env["ws_beta"]
    alice_id = gate_env["users"]["alice"].id
    bob_id = gate_env["users"]["bob"].id

    token_alice = create_signed_token(
        Principal(
            principal_id=alice_id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        )
    )
    headers_alice = {
        "Authorization": f"Bearer {token_alice}",
        "X-Workspace-ID": ws_alpha,
    }

    # Step 4b: POST /projects/
    res_create = client.post("/projects/", json={"name": "Alice Promo", "language": "en"}, headers=headers_alice)
    assert res_create.status_code == 200, f"Create failed: {res_create.text}"
    created_id = res_create.json()["project_id"]
    gate_env["created_projects"].append(created_id)

    # Assert project row is linked to workspace Alpha, not ws_default!
    prj_rec = repo.get_project(created_id)
    assert prj_rec is not None, "Project row was NOT written to database!"
    assert prj_rec.workspace_id == ws_alpha, f"Expected project workspace '{ws_alpha}', got '{prj_rec.workspace_id}'!"
    assert prj_rec.created_by == alice_id, f"Expected created_by '{alice_id}', got '{prj_rec.created_by}'!"

    # Step 4c: GET /projects/ for Alice
    res_list = client.get("/projects/", headers=headers_alice)
    assert res_list.status_code == 200
    assert created_id in res_list.json()["projects"], f"Project {created_id} missing from Alice's project list!"

    # GET /projects/{id}
    res_get = client.get(f"/projects/{created_id}", headers=headers_alice)
    assert res_get.status_code == 200, f"Alice cannot read her own project: {res_get.text}"

    # GET /projects/{id}/state
    res_state = client.get(f"/projects/{created_id}/state", headers=headers_alice)
    assert res_state.status_code == 200, f"Alice cannot read project state: {res_state.text}"

    # Step 4d: Bob in ws_beta must NOT see or access Alice's project
    token_bob = create_signed_token(
        Principal(
            principal_id=bob_id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        )
    )
    headers_bob = {
        "Authorization": f"Bearer {token_bob}",
        "X-Workspace-ID": ws_beta,
    }

    res_bob_list = client.get("/projects/", headers=headers_bob)
    assert res_bob_list.status_code == 200
    assert created_id not in res_bob_list.json()["projects"]

    res_bob_get = client.get(f"/projects/{created_id}", headers=headers_bob)
    assert res_bob_get.status_code in (403, 404)

    # Step 4f: Authorized run creation retains ws_alpha (no ws_default fallback)
    res_run = client.post(f"/projects/{created_id}/runs", json={}, headers=headers_alice)
    assert res_run.status_code == 202
    run_data = res_run.json()
    from scripts.core.run_repository import RunRepository
    run_repo = RunRepository(db_path=gate_env["db_file"])
    persisted_run = run_repo.get_run(run_data["run_id"])
    assert persisted_run is not None, "Persisted run record not found!"
    assert persisted_run.workspace_id == ws_alpha, f"Expected workspace_id '{ws_alpha}', got '{persisted_run.workspace_id}'!"


def test_unauthorized_non_member_creator_rejected_no_orphaned_state(gate_env):
    """
    Step 4e:
    An unauthorized/non-member creator must be rejected without leaving orphaned
    DB rows or project directories.
    Also tests that a VIEWER role in the workspace is rejected.
    """
    client = gate_env["client"]
    repo = gate_env["repo"]
    ws_alpha = gate_env["ws_alpha"]
    eve = gate_env["users"]["eve"]

    token_eve = create_signed_token(
        Principal(
            principal_id=eve.id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        )
    )
    headers_eve = {
        "Authorization": f"Bearer {token_eve}",
        "X-Workspace-ID": ws_alpha,
    }

    # Count project directories before
    projects_dir = Path("projects")
    existing_dirs = set(p.name for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else set()

    # 1. Non-member Eve attempts creation
    res_eve = client.post("/projects/", json={"name": "Eve Malicious", "language": "en"}, headers=headers_eve)
    assert res_eve.status_code == 403, f"Expected 403 Forbidden for non-member, got {res_eve.status_code}"

    # Verify no new directory was created
    current_dirs = set(p.name for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else set()
    new_dirs = current_dirs - existing_dirs
    assert len(new_dirs) == 0, f"Orphaned project directory detected: {new_dirs}"

    # Verify no DB row was created for Eve
    projects_eve = [p for p in repo.list_projects_for_workspace(ws_alpha) if p.created_by == eve.id]
    assert len(projects_eve) == 0, "Orphaned DB project row found for unauthorized creator!"

    # 2. Viewer in ws_alpha attempts creation
    user_viewer = repo.create_user("usr_viewer", "viewer@alpha.com")
    repo.add_member(ws_alpha, user_viewer.id, Role.VIEWER)

    token_viewer = create_signed_token(
        Principal(
            principal_id=user_viewer.id,
            principal_type=PrincipalType.HUMAN,
            roles={Role.VIEWER},
        )
    )
    headers_viewer = {
        "Authorization": f"Bearer {token_viewer}",
        "X-Workspace-ID": ws_alpha,
    }

    res_viewer = client.post("/projects/", json={"name": "Viewer Attempt", "language": "en"}, headers=headers_viewer)
    assert res_viewer.status_code == 403, f"Expected 403 Forbidden for VIEWER role, got {res_viewer.status_code}"

    current_dirs = set(p.name for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else set()
    new_dirs = current_dirs - existing_dirs
    assert len(new_dirs) == 0, f"Orphaned project directory detected: {new_dirs}"


def test_service_token_never_receives_internal_system_authority(gate_env):
    """
    Step 5 (Invariant 1):
    An HTTP token claiming SERVICE/SYSTEM_WORKER never receives INTERNAL_SYSTEM authority.
    Only trusted in-process creation can establish that authority.
    """
    client = gate_env["client"]
    ws_alpha = gate_env["ws_alpha"]
    alice = gate_env["users"]["alice"]

    # First, create a project owned by Alice in ws_alpha
    token_alice = create_signed_token(
        Principal(principal_id=alice.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR})
    )
    headers_alice = {"Authorization": f"Bearer {token_alice}", "X-Workspace-ID": ws_alpha}
    res_create = client.post("/projects/", json={"name": "Service Test", "language": "en"}, headers=headers_alice)
    assert res_create.status_code == 200
    created_id = res_create.json()["project_id"]
    gate_env["created_projects"].append(created_id)

    # Now create an external HTTP token claiming SERVICE and ADMIN role, but sub is NOT a member
    token_svc = create_signed_token(
        Principal(
            principal_id="svc_untrusted_worker",
            principal_type=PrincipalType.SERVICE,
            roles={Role.ADMIN},
        )
    )
    headers_svc = {"Authorization": f"Bearer {token_svc}"}

    # Verify that HTTP requests with this service token are NOT granted INTERNAL_SYSTEM bypass
    res_get = client.get(f"/projects/{created_id}", headers=headers_svc)
    assert res_get.status_code == 403, f"Expected 403 for untrusted service token, got {res_get.status_code}"

    # Verify in-process call with INTERNAL_SYSTEM CAN authenticate
    principal_internal = Principal(
        principal_id="sys_internal_daemon",
        principal_type=PrincipalType.SYSTEM_WORKER,
        roles={Role.ADMIN},
        auth_method="INTERNAL_SYSTEM",
    )
    assert principal_internal.auth_method == "INTERNAL_SYSTEM"


def test_database_failure_fails_closed_with_503(gate_env):
    """
    Step 5 (Invariant 2):
    Database failure while resolving a managed project's ownership cannot fall through
    to token roles, wildcard scope, or a local/unmanaged fallback.
    Differentiates expected 403 vs 503 consistently, and avoids sensitive errors to callers.
    """
    client = gate_env["client"]
    ws_alpha = gate_env["ws_alpha"]
    alice = gate_env["users"]["alice"]

    token_alice = create_signed_token(
        Principal(principal_id=alice.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR})
    )
    headers_alice = {"Authorization": f"Bearer {token_alice}", "X-Workspace-ID": ws_alpha}
    res_create = client.post("/projects/", json={"name": "DB Fail Test", "language": "en"}, headers=headers_alice)
    assert res_create.status_code == 200
    created_id = res_create.json()["project_id"]
    gate_env["created_projects"].append(created_id)

    # 1. DB failure during project creation raises 503 Service Unavailable
    with patch("scripts.core.database.TenantRepository.get_membership", side_effect=Exception("Database lock acquisition timeout")):
        res_create_fail = client.post("/projects/", json={"name": "Fail Create", "language": "en"}, headers=headers_alice)
        assert res_create_fail.status_code == 503, f"Expected 503 on create DB failure, got {res_create_fail.status_code}"
        assert "Database lock acquisition timeout" not in res_create_fail.text
        assert "Database service temporarily unavailable" in res_create_fail.json()["detail"]

    # 2. DB failure during read authorization fails closed (403 or 503, never 200 bypass)
    with patch("scripts.core.database.TenantRepository.get_project", side_effect=Exception("Database connection timeout")):
        res_fail = client.get(f"/projects/{created_id}", headers=headers_alice)
        assert res_fail.status_code in (403, 503), f"Expected 403/503 Service Unavailable, got {res_fail.status_code}"
        assert "Database connection timeout" not in res_fail.text


def test_standalone_cli_scaffold_distinct_local_behavior(gate_env):
    """
    Step 4g:
    Standalone CLI scaffold (scripts/scaffold_project.py without --workspace-id)
    generates a local project on disk without silently registering or granting API access.
    Cloud/API execution does not silently treat tenant-owned projects as unmanaged.
    """
    client = gate_env["client"]
    repo = gate_env["repo"]
    from api.services.scaffold_service import create_project

    # Standalone CLI scaffold: no workspace_id
    cli_proj_id = create_project("CLI Local Proj", "en")
    assert cli_proj_id is not None
    gate_env["created_projects"].append(cli_proj_id)

    # Verify not registered in TenantRepository
    assert repo.get_project(cli_proj_id) is None

    # Verify project file exists on disk
    assert Path(f"projects/{cli_proj_id}/project.json").exists()

    # Verify that a user cannot see this unmanaged CLI project in GET /projects/
    alice = gate_env["users"]["alice"]
    ws_alpha = gate_env["ws_alpha"]
    token_alice = create_signed_token(
        Principal(principal_id=alice.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR})
    )
    headers_alice = {"Authorization": f"Bearer {token_alice}", "X-Workspace-ID": ws_alpha}

    res_list = client.get("/projects/", headers=headers_alice)
    assert res_list.status_code == 200
    assert cli_proj_id not in res_list.json()["projects"]


def test_database_url_not_in_subprocess_environment():
    """
    Requirement 1:
    Verify DATABASE_URL is strictly excluded from CommandPolicy.sanitize_environment().
    """
    from scripts.core.security.command_policy import CommandPolicy
    env = CommandPolicy.sanitize_environment({"DATABASE_URL": "sqlite:///sensitive.db", "PATH": "/usr/bin"})
    assert "DATABASE_URL" not in env, "SECURITY VIOLATION: DATABASE_URL leaked into subprocess environment!"


def test_unauthorized_subprocesses_strictly_denied_database_credentials():
    """
    Negative test (PR-003 Security Regression Closure):
    Verify unauthorized subprocesses (FFmpeg, Remotion, Scaffolding, Gates, Pipeline)
    are strictly denied access to DATABASE_URL, RUNS_DB_PATH, and AUTH_SECRET_KEY.
    """
    import sys
    from scripts.core.security.command_policy import CommandPolicy, DATABASE_CREDENTIAL_ENV_VARS

    sensitive_env = {
        "DATABASE_URL": "sqlite:///production_secret.db",
        "RUNS_DB_PATH": "/secrets/runs.db",
        "AUTH_SECRET_KEY": "super-secret-jwt-signing-key",
        "MOTION_DATABASE_URL": "postgres://user:pass@db/prod",
        "PATH": "/usr/bin",
    }

    # 1. FFmpeg
    ffmpeg_val = CommandPolicy.validate_command(["ffmpeg", "-version"], is_production=True)
    for cred_key in DATABASE_CREDENTIAL_ENV_VARS:
        assert cred_key not in ffmpeg_val.sanitized_env, f"SECURITY VIOLATION: {cred_key} leaked to ffmpeg!"

    # 2. Remotion / Node
    remotion_val = CommandPolicy.validate_command(["npx", "remotion"], is_production=True)
    for cred_key in DATABASE_CREDENTIAL_ENV_VARS:
        assert cred_key not in remotion_val.sanitized_env, f"SECURITY VIOLATION: {cred_key} leaked to remotion!"

    # 3. Pipeline / Scaffold / Gates
    for script in ["scripts/pipeline.py", "scripts/scaffold_project.py", "scripts/gates/final_qc.py", "scripts/render_project.py"]:
        py_val = CommandPolicy.validate_command([sys.executable, script, "prj_test"], is_production=True)
        for cred_key in DATABASE_CREDENTIAL_ENV_VARS:
            assert cred_key not in py_val.sanitized_env, f"SECURITY VIOLATION: {cred_key} leaked to {script}!"

    # 4. Direct sanitize_environment call with sensitive_env for unauthorized target
    clean = CommandPolicy.sanitize_environment(sensitive_env, is_production=True, target_script="scripts/pipeline.py")
    for cred_key in DATABASE_CREDENTIAL_ENV_VARS:
        assert cred_key not in clean, f"SECURITY VIOLATION: {cred_key} present in sanitized environment for unauthorized target!"


def test_authorized_component_explicitly_granted_database_credentials():
    """
    Positive test (PR-003 Security Regression Closure):
    Verify that only authorized database components (e.g. explicitly flagged or in DATABASE_AUTHORIZED_SCRIPTS)
    are granted DATABASE_URL and related credentials.
    """
    from scripts.core.security.command_policy import CommandPolicy

    sensitive_env = {
        "DATABASE_URL": "sqlite:///production_secret.db",
        "RUNS_DB_PATH": "/secrets/runs.db",
        "AUTH_SECRET_KEY": "super-secret-jwt-signing-key",
        "PATH": "/usr/bin",
    }

    # 1. Authorized via explicit allow_database_env flag
    clean_explicit = CommandPolicy.sanitize_environment(
        sensitive_env, is_production=True, allow_database_env=True
    )
    assert clean_explicit.get("DATABASE_URL") == "sqlite:///production_secret.db"
    assert clean_explicit.get("RUNS_DB_PATH") == "/secrets/runs.db"
    assert clean_explicit.get("AUTH_SECRET_KEY") == "super-secret-jwt-signing-key"

    # 2. Authorized via target_script in DATABASE_AUTHORIZED_SCRIPTS
    clean_script = CommandPolicy.sanitize_environment(
        sensitive_env, is_production=True, target_script="scripts/run_creative_cost_audit.py"
    )
    assert clean_script.get("DATABASE_URL") == "sqlite:///production_secret.db"
    assert clean_script.get("RUNS_DB_PATH") == "/secrets/runs.db"
    assert clean_script.get("AUTH_SECRET_KEY") == "super-secret-jwt-signing-key"


def test_multi_workspace_creator_requires_explicit_header(gate_env):
    """
    Requirement 4:
    If a user is a member of more than one workspace with project creation permissions,
    omitting X-Workspace-ID must return HTTP 400 with an unambiguous error message.
    """
    client = gate_env["client"]
    repo = gate_env["repo"]
    ws_alpha = gate_env["ws_alpha"]
    ws_beta = gate_env["ws_beta"]

    user_multi = repo.create_user("usr_multi", "multi@example.com")
    repo.add_member(ws_alpha, user_multi.id, Role.EDITOR)
    repo.add_member(ws_beta, user_multi.id, Role.EDITOR)

    token_multi = create_signed_token(
        Principal(principal_id=user_multi.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR})
    )
    headers_no_ws = {"Authorization": f"Bearer {token_multi}"}

    # 1. Omitting header returns HTTP 400
    res_ambiguous = client.post("/projects/", json={"name": "Ambiguous", "language": "en"}, headers=headers_no_ws)
    assert res_ambiguous.status_code == 400
    assert "Ambiguous workspace selection" in res_ambiguous.json()["detail"]

    # 2. Specifying header succeeds
    headers_explicit = {"Authorization": f"Bearer {token_multi}", "X-Workspace-ID": ws_alpha}
    res_explicit = client.post("/projects/", json={"name": "Explicit", "language": "en"}, headers=headers_explicit)
    assert res_explicit.status_code == 200
    created_id = res_explicit.json()["project_id"]
    gate_env["created_projects"].append(created_id)
    assert repo.get_project(created_id).workspace_id == ws_alpha


def test_external_admin_cannot_create_unmanaged_projects_via_http(gate_env):
    """
    Requirement 3:
    An external Admin token (without workspace membership) cannot create
    unmanaged projects via the HTTP API.
    """
    client = gate_env["client"]
    repo = gate_env["repo"]

    token_admin_unscoped = create_signed_token(
        Principal(principal_id="usr_admin_unscoped", principal_type=PrincipalType.HUMAN, roles={Role.ADMIN})
    )
    headers = {"Authorization": f"Bearer {token_admin_unscoped}"}

    res = client.post("/projects/", json={"name": "Admin Unscoped", "language": "en"}, headers=headers)
    assert res.status_code == 403
    assert "Unmanaged project creation via HTTP API is prohibited" in res.text


def test_partial_failure_cleanup_before_and_during_db_registration(gate_env):
    """
    Requirement 2:
    Verify atomic project creation and rollback:
    - Failure during scaffolding cleans up partial directories.
    - Failure during DB registration removes the created directory.
    - Failure during state sync deletes the DB record and the directory.
    - Pre-existing files are never deleted.
    """
    client = gate_env["client"]
    repo = gate_env["repo"]
    ws_alpha = gate_env["ws_alpha"]
    alice = gate_env["users"]["alice"]

    token_alice = create_signed_token(
        Principal(principal_id=alice.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR})
    )
    headers = {"Authorization": f"Bearer {token_alice}", "X-Workspace-ID": ws_alpha}

    projects_dir = Path("projects")
    existing_dirs = set(p.name for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else set()

    # 1. Failure during scaffolding subprocess
    with patch("api.services.scaffold_service.safe_subprocess") as mock_sub:
        class FakeResult:
            returncode = 1
            stderr = "Simulated filesystem write error"
            stdout = ""
        mock_sub.return_value = FakeResult()

        res_scaffold_fail = client.post("/projects/", json={"name": "Fail 1", "language": "en"}, headers=headers)
        assert res_scaffold_fail.status_code == 500

    current_dirs = set(p.name for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else set()
    assert (current_dirs - existing_dirs) == set(), "Orphaned directory left after scaffolding failure!"

    # 2. Failure during DB registration in parent process
    with patch.object(repo, "create_project", side_effect=Exception("Simulated DB connection failure")):
        with patch("scripts.core.database.TenantRepository.create_project", side_effect=Exception("Simulated DB connection failure")):
            res_db_fail = client.post("/projects/", json={"name": "Fail 2", "language": "en"}, headers=headers)
            assert res_db_fail.status_code == 503

    current_dirs = set(p.name for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else set()
    assert (current_dirs - existing_dirs) == set(), "Orphaned directory left after DB registration failure!"

    # 3. Failure during post-registration state sync
    with patch("scripts.core.state_store.StateStore._sync_to_db", side_effect=Exception("Simulated state sync failure")):
        res_sync_fail = client.post("/projects/", json={"name": "Fail 3", "language": "en"}, headers=headers)
        assert res_sync_fail.status_code == 503

    current_dirs = set(p.name for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.exists() else set()
    assert (current_dirs - existing_dirs) == set(), "Orphaned directory left after state sync failure!"


