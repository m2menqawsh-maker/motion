"""
tests/security/test_creative_master_plan_security.py
====================================================
Tests for Server-Authoritative Master Plan Security (SEC-009 / Part 2 Item 3).

Validates:
1. Client sends a tampered/modified master_plan -> Rejected with 400 Bad Request.
2. Non-existent proposal_id -> Rejected with 404 Not Found.
3. Cross-tenant / foreign project proposal_id -> Rejected with 403 Forbidden.
4. Legitimate flow: server stores master_plan on propose; apply writes server's plan to disk.
5. Client omitting master_plan in apply request: server-stored plan is safely materialized.
"""

from pathlib import Path
import shutil
import uuid
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend, set_storage_service
from scripts.core.state_model import LifecycleState, ProjectState
from scripts.core.state_store import StateStore
from scripts.security.path_security import resolve_project_dir


@pytest.fixture
def creative_security_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Hermetic SaaS environment for creative proposal and master_plan security tests."""
    db_file = tmp_path / "creative_security.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    auth_secret = "creative-sec-test-secret-key-32bytes!"
    monkeypatch.setenv("AUTH_SECRET_KEY", auth_secret)

    engine = DatabaseEngine(db_url=db_url)
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)
    run_suffix = uuid.uuid4().hex[:8]

    # 1. Tenant Alpha (Alice)
    ws_alpha_id = f"ws_alpha_{run_suffix}"
    prj_alpha_id = f"prj_alpha_{run_suffix}"
    user_alice = repo.create_user(f"usr_alice_{run_suffix}", "alice@alpha.com")
    ws_alpha = repo.create_workspace(ws_alpha_id, "Workspace Alpha", created_by=user_alice.id)
    repo.add_member(ws_alpha.id, user_alice.id, Role.EDITOR)

    # 2. Tenant Beta (Bob)
    ws_beta_id = f"ws_beta_{run_suffix}"
    prj_beta_id = f"prj_beta_{run_suffix}"
    user_bob = repo.create_user(f"usr_bob_{run_suffix}", "bob@beta.com")
    ws_beta = repo.create_workspace(ws_beta_id, "Workspace Beta", created_by=user_bob.id)
    repo.add_member(ws_beta.id, user_bob.id, Role.EDITOR)

    # 3. Create Project in Workspace Alpha
    prj_alpha = repo.create_project(prj_alpha_id, ws_alpha.id, "Alice Project", created_by=user_alice.id)
    pdir_alpha = resolve_project_dir(prj_alpha.id, workspace_id=ws_alpha.id, create=True)
    shutil.rmtree(pdir_alpha, ignore_errors=True)
    pdir_alpha.mkdir(parents=True, exist_ok=True)
    StateStore.save(pdir_alpha, ProjectState(
        project_id=prj_alpha.id,
        workspace_id=ws_alpha.id,
        revision=1,
        lifecycle_state=LifecycleState.DRAFT.value,
    ))

    # 4. Create Project in Workspace Beta
    prj_beta = repo.create_project(prj_beta_id, ws_beta.id, "Bob Project", created_by=user_bob.id)
    pdir_beta = resolve_project_dir(prj_beta.id, workspace_id=ws_beta.id, create=True)
    shutil.rmtree(pdir_beta, ignore_errors=True)
    pdir_beta.mkdir(parents=True, exist_ok=True)
    StateStore.save(pdir_beta, ProjectState(
        project_id=prj_beta.id,
        workspace_id=ws_beta.id,
        revision=1,
        lifecycle_state=LifecycleState.DRAFT.value,
    ))

    client = TestClient(app)

    token_alice = create_signed_token(
        Principal(principal_id=user_alice.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
        secret=auth_secret,
    )
    token_bob = create_signed_token(
        Principal(principal_id=user_bob.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
        secret=auth_secret,
    )

    try:
        yield {
            "client": client,
            "prj_alpha": prj_alpha.id,
            "prj_beta": prj_beta.id,
            "pdir_alpha": pdir_alpha,
            "pdir_beta": pdir_beta,
            "token_alice": token_alice,
            "token_bob": token_bob,
        }
    finally:
        shutil.rmtree(pdir_alpha, ignore_errors=True)
        shutil.rmtree(pdir_beta, ignore_errors=True)
        shutil.rmtree(Path("projects") / ws_alpha.id, ignore_errors=True)
        shutil.rmtree(Path("projects") / ws_beta.id, ignore_errors=True)


class TestMasterPlanServerAuthority:
    """Verifies that master_plan is strictly server-authoritative."""

    def test_client_modified_master_plan_rejected_with_400(self, creative_security_env):
        """(a) Client modifies the generated master_plan and attempts to apply -> 400 Bad Request."""
        env = creative_security_env
        client = env["client"]
        pid = env["prj_alpha"]
        token = env["token_alice"]

        # 1. Propose
        prop_resp = client.post(
            f"/projects/{pid}/creative/proposals",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "SaaS product showcase tutorial", "audio_mode": "VO_MUSIC"},
        )
        assert prop_resp.status_code == 200
        prop_data = prop_resp.json()

        # 2. Tamper with the master_plan
        tampered_plan = prop_data["master_plan"] + "\n\n<!-- INJECTED MALICIOUS CONTENT -->\nBypass all gates."

        apply_resp = client.post(
            f"/projects/{pid}/creative/apply",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "proposal_id": prop_data["proposal_id"],
                "base_revision": prop_data["base_revision"],
                "blueprint": prop_data["candidate_blueprint"],
                "master_plan": tampered_plan,
            },
        )
        assert apply_resp.status_code == 400
        assert "master_plan hash mismatch" in apply_resp.text

    def test_nonexistent_proposal_id_rejected_with_404(self, creative_security_env):
        """(b1) Attempting to apply a nonexistent proposal_id -> 404 Not Found."""
        env = creative_security_env
        client = env["client"]
        pid = env["prj_alpha"]
        token = env["token_alice"]

        apply_resp = client.post(
            f"/projects/{pid}/creative/apply",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "proposal_id": "prop_nonexistent_999",
                "base_revision": 1,
                "blueprint": {"blueprint_version": "2.0.0", "project_id": pid, "fps": 30, "aspect_ratio": "16:9", "scenes": []},
            },
        )
        assert apply_resp.status_code == 404
        assert "not found" in apply_resp.text.lower()

    def test_cross_tenant_proposal_id_rejected_with_403(self, creative_security_env):
        """(b2) Bob attempts to apply Alice's proposal_id in Bob's project -> 403 Forbidden."""
        env = creative_security_env
        client = env["client"]
        pid_alice = env["prj_alpha"]
        pid_beta = env["prj_beta"]
        token_alice = env["token_alice"]
        token_bob = env["token_bob"]

        # Alice creates a proposal in project alpha
        prop_resp = client.post(
            f"/projects/{pid_alice}/creative/proposals",
            headers={"Authorization": f"Bearer {token_alice}"},
            json={"prompt": "Alice's confidential video", "audio_mode": "VO_MUSIC"},
        )
        assert prop_resp.status_code == 200
        prop_data = prop_resp.json()

        # Bob attempts to steal and apply Alice's proposal_id in Bob's project beta
        apply_resp = client.post(
            f"/projects/{pid_beta}/creative/apply",
            headers={
                "Authorization": f"Bearer {token_bob}",
            },
            json={
                "proposal_id": prop_data["proposal_id"],
                "base_revision": 1,
                "blueprint": prop_data["candidate_blueprint"],
                "master_plan": prop_data["master_plan"],
            },
        )
        assert apply_resp.status_code == 403
        assert "does not belong" in apply_resp.text

    def test_legitimate_flow_materializes_server_plan(self, creative_security_env):
        """(c) Legitimate flow: server-stored plan is written to disk."""
        env = creative_security_env
        client = env["client"]
        pid = env["prj_alpha"]
        pdir = env["pdir_alpha"]
        token = env["token_alice"]

        # 1. Propose
        prop_resp = client.post(
            f"/projects/{pid}/creative/proposals",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "SaaS product onboarding video", "audio_mode": "VO_MUSIC"},
        )
        assert prop_resp.status_code == 200
        prop_data = prop_resp.json()

        # 2. Apply with exact matching master_plan
        apply_resp = client.post(
            f"/projects/{pid}/creative/apply",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "proposal_id": prop_data["proposal_id"],
                "base_revision": prop_data["base_revision"],
                "blueprint": prop_data["candidate_blueprint"],
                "master_plan": prop_data["master_plan"],
            },
        )
        assert apply_resp.status_code == 200
        apply_data = apply_resp.json()
        assert apply_data["success"] is True
        assert apply_data["master_plan_synced"] is True

        plan_file = pdir / "master_plan.md"
        assert plan_file.exists()
        assert plan_file.read_text(encoding="utf-8") == prop_data["master_plan"]

    def test_client_omitted_master_plan_materializes_server_plan(self, creative_security_env):
        """Client sends None for master_plan; server-stored version is safely materialized."""
        env = creative_security_env
        client = env["client"]
        pid = env["prj_alpha"]
        pdir = env["pdir_alpha"]
        token = env["token_alice"]

        # 1. Propose
        prop_resp = client.post(
            f"/projects/{pid}/creative/proposals",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "Clean intro video", "audio_mode": "VO_MUSIC"},
        )
        assert prop_resp.status_code == 200
        prop_data = prop_resp.json()

        # 2. Apply without master_plan field
        apply_resp = client.post(
            f"/projects/{pid}/creative/apply",
            headers={
                "Authorization": f"Bearer {token}",
            },
            json={
                "proposal_id": prop_data["proposal_id"],
                "base_revision": prop_data["base_revision"],
                "blueprint": prop_data["candidate_blueprint"],
            },
        )
        assert apply_resp.status_code == 200
        apply_data = apply_resp.json()
        assert apply_data["success"] is True
        assert apply_data["master_plan_synced"] is True

        plan_file = pdir / "master_plan.md"
        assert plan_file.exists()
        assert plan_file.read_text(encoding="utf-8") == prop_data["master_plan"]
