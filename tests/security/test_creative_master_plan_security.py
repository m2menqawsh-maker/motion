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

    def test_proposal_persistence_survives_memory_cache_clear_and_blocks_cross_tenant(self, creative_security_env):
        """
        Fix 1 Test:
        1. Propose creates proposal stored in persistent StorageService.
        2. In-memory proposal cache is completely cleared: CreativeService._proposals_store.clear().
        3. Authorized apply fetches from StorageService and succeeds with 200 OK.
        4. Cross-tenant apply from another tenant (Bob) is rejected with 404 (or 403).
           (We assert 404: In canonical multi-tenant storage layout, proposals are partitioned by
           workspaces/{ws_id}/projects/{prj_id}/proposals/{prop_id}.json. Foreign tenant lookups
           in their own namespace yield 404 Not Found, preventing cross-tenant existence enumeration).
        """
        from api.services.creative_service import CreativeService

        env = creative_security_env
        client = env["client"]
        pid_alice = env["prj_alpha"]
        pid_beta = env["prj_beta"]
        token_alice = env["token_alice"]
        token_bob = env["token_bob"]
        pdir_alice = env["pdir_alpha"]

        # 1. Alice generates proposal
        prop_resp = client.post(
            f"/projects/{pid_alice}/creative/proposals",
            headers={"Authorization": f"Bearer {token_alice}"},
            json={"prompt": "Permanent storage persistence showcase", "audio_mode": "VO_MUSIC"},
        )
        assert prop_resp.status_code == 200
        prop_data = prop_resp.json()
        prop_id = prop_data["proposal_id"]

        # 2. Clear memory cache entirely to simulate server restart / cache eviction
        CreativeService._proposals_store.clear()
        assert prop_id not in CreativeService._proposals_store

        # 3. Foreign tenant (Bob) attempts to apply Alice's proposal after cache clear
        cross_resp = client.post(
            f"/projects/{pid_beta}/creative/apply",
            headers={"Authorization": f"Bearer {token_bob}"},
            json={
                "proposal_id": prop_id,
                "base_revision": 1,
                "blueprint": prop_data["candidate_blueprint"],
            },
        )
        assert cross_resp.status_code in (403, 404)

        # 4. Legitimate tenant (Alice) applies proposal: must fetch from StorageService and succeed
        apply_resp = client.post(
            f"/projects/{pid_alice}/creative/apply",
            headers={"Authorization": f"Bearer {token_alice}"},
            json={
                "proposal_id": prop_id,
                "base_revision": prop_data["base_revision"],
                "blueprint": prop_data["candidate_blueprint"],
            },
        )
        assert apply_resp.status_code == 200
        assert apply_resp.json()["success"] is True
        plan_file = pdir_alice / "master_plan.md"
        assert plan_file.exists()
        assert plan_file.read_text(encoding="utf-8") == prop_data["master_plan"]

    def test_idempotency_conflict_evaluated_before_proposal_lookup(self, creative_security_env):
        """
        Fix 2 Test:
        Verifies that replaying with a conflicting payload under an already-executed operation_id
        is rejected with 409 Conflict, even if the proposal_id in the conflicting payload does not exist.
        Protocol idempotency invariants strictly precede entity/proposal resolution.
        """
        env = creative_security_env
        client = env["client"]
        pid = env["prj_alpha"]
        token = env["token_alice"]

        # 1. Propose
        prop_resp = client.post(
            f"/projects/{pid}/creative/proposals",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": "Idempotency ordering test", "audio_mode": "VO_MUSIC"},
        )
        assert prop_resp.status_code == 200
        prop_data = prop_resp.json()

        op_id = f"op_test_order_{uuid.uuid4().hex[:8]}"
        apply_payload = {
            "proposal_id": prop_data["proposal_id"],
            "base_revision": prop_data["base_revision"],
            "blueprint": prop_data["candidate_blueprint"],
            "operation_id": op_id,
        }

        # 2. First apply succeeds (200)
        resp1 = client.post(
            f"/projects/{pid}/creative/apply",
            headers={"Authorization": f"Bearer {token}"},
            json=apply_payload,
        )
        assert resp1.status_code == 200

        # 3. Conflicting apply: same operation_id, but different / non-existent proposal_id
        conflicting_payload = dict(apply_payload)
        conflicting_payload["proposal_id"] = "prop_nonexistent_conflict_999"

        resp2 = client.post(
            f"/projects/{pid}/creative/apply",
            headers={"Authorization": f"Bearer {token}"},
            json=conflicting_payload,
        )
        # Must return 409 Conflict (idempotency violation), NOT 404 Not Found
        assert resp2.status_code == 409
        assert "idempotency" in resp2.text.lower()

    def test_idempotency_record_marked_failed_on_proposal_errors(self, creative_security_env):
        """
        Note 3 Test:
        Verifies that when apply_proposal fails due to:
        - 404: nonexistent proposal_id
        - 403: cross-tenant proposal_id
        - 400: client-modified master_plan hash mismatch
        the idempotency record is immediately transitioned from IN_PROGRESS to FAILED
        via mark_failed, preventing stuck leader locks.
        """
        env = creative_security_env
        client = env["client"]
        pid_a = env["prj_alpha"]
        pid_b = env["prj_beta"]
        token_a = env["token_alice"]
        token_b = env["token_bob"]

        from scripts.core.database import get_database_engine
        engine = get_database_engine()

        def get_idemp_status(op_id: str):
            with engine.transaction() as conn:
                row = conn.execute(
                    "SELECT status, error_json FROM authoring_idempotency_records WHERE operation_id = ?",
                    (op_id,),
                ).fetchone()
                return (row[0], row[1]) if row else (None, None)

        # 1. Test 404: Nonexistent proposal_id
        op_404 = f"op_test_fail_404_{uuid.uuid4().hex[:6]}"
        resp_404 = client.post(
            f"/projects/{pid_a}/creative/apply",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "proposal_id": "prop_nonexistent_999",
                "base_revision": 1,
                "blueprint": {"blueprint_version": "2.0.0", "project_id": pid_a, "fps": 30, "aspect_ratio": "16:9", "scenes": []},
                "operation_id": op_404,
            },
        )
        assert resp_404.status_code == 404
        status_404, err_404 = get_idemp_status(op_404)
        assert status_404 == "FAILED"
        assert err_404 is not None and "PROPOSAL_NOT_FOUND" in err_404

        # Propose in Alpha to get a valid proposal
        prop_resp = client.post(
            f"/projects/{pid_a}/creative/proposals",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"prompt": "SaaS product showcase tutorial", "audio_mode": "VO_MUSIC"},
        )
        assert prop_resp.status_code == 200
        prop_data = prop_resp.json()
        valid_prop_id = prop_data["proposal_id"]

        # 2. Test 403: Cross-tenant proposal_id
        op_403 = f"op_test_fail_403_{uuid.uuid4().hex[:6]}"
        resp_403 = client.post(
            f"/projects/{pid_b}/creative/apply",
            headers={"Authorization": f"Bearer {token_b}"},
            json={
                "proposal_id": valid_prop_id,
                "base_revision": 1,
                "blueprint": {"blueprint_version": "2.0.0", "project_id": pid_b, "fps": 30, "aspect_ratio": "16:9", "scenes": []},
                "operation_id": op_403,
            },
        )
        assert resp_403.status_code == 403
        status_403, err_403 = get_idemp_status(op_403)
        assert status_403 == "FAILED"
        assert err_403 is not None and "CROSS_TENANT_PROPOSAL" in err_403

        # 3. Test 400: Tampered master_plan
        op_400 = f"op_test_fail_400_{uuid.uuid4().hex[:6]}"
        resp_400 = client.post(
            f"/projects/{pid_a}/creative/apply",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "proposal_id": valid_prop_id,
                "base_revision": prop_data["base_revision"],
                "blueprint": prop_data["candidate_blueprint"],
                "master_plan": "# Tampered Master Plan by Malicious Client",
                "operation_id": op_400,
            },
        )
        assert resp_400.status_code == 400
        status_400, err_400 = get_idemp_status(op_400)
        assert status_400 == "FAILED"
        assert err_400 is not None and "PLAN_HASH_MISMATCH" in err_400


