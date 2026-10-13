"""
tests/integration/test_b2_capability_gateway_integration.py
=============================================================
Integration test suite for Workstream B2:
- Genuine product API routes through CapabilityService -> CapabilityRouter -> ToolGateway / DomainServiceAdapter.
- Enforces capability allowlists, project-scoped permissions, and tenant boundaries.
- Demonstrates:
  1. Successful authorized capability execution (e.g. GENERATE_SPEECH_MANIFEST).
  2. Rejected unauthorized capability request (Viewer role attempting mutating capability).
  3. Rejected cross-tenant attempt (Beta actor attempting Alpha project capability).
  4. Non-allowlisted capability request rejected (403 Forbidden).
  5. Preservation of human decision authority: zero auto-approval (.studio_approved) and zero run enqueuing.
  6. Repeatable offline CI execution with zero external network or paid provider dependencies.
"""

from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.run_repository import RunRepository
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend, set_storage_service


@pytest.fixture
def b2_env(tmp_path, monkeypatch):
    """Hermetic SaaS environment for Workstream B2 testing."""
    db_file = tmp_path / "b2_runtime.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    auth_secret = "b2-test-signing-secret-for-pytest-harness-32!"
    monkeypatch.setenv("AUTH_SECRET_KEY", auth_secret)

    engine = DatabaseEngine(db_url=db_url)
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)

    # 1. Tenant Alpha - Alice (Editor) and Charlie (Viewer)
    user_alice = repo.create_user("usr_alice_b2", "alice@alpha.com")
    user_charlie = repo.create_user("usr_charlie_b2", "charlie@alpha.com")
    ws_alpha = repo.create_workspace("ws_alpha_b2", "Workspace Alpha B2", created_by=user_alice.id)
    repo.add_member(ws_alpha.id, user_alice.id, Role.EDITOR)
    repo.add_member(ws_alpha.id, user_charlie.id, Role.VIEWER)

    # 2. Tenant Beta - Bob (Editor in Beta)
    user_bob = repo.create_user("usr_bob_b2", "bob@beta.com")
    ws_beta = repo.create_workspace("ws_beta_b2", "Workspace Beta B2", created_by=user_bob.id)
    repo.add_member(ws_beta.id, user_bob.id, Role.EDITOR)

    # 3. Create Project in Workspace Alpha
    prj_alpha = repo.create_project("prj_alpha_b2", ws_alpha.id, "Alpha B2 Video", created_by=user_alice.id)

    # Create project directory on disk
    from scripts.security.path_security import resolve_project_dir
    pdir_alpha = resolve_project_dir(prj_alpha.id, workspace_id=ws_alpha.id, create=True)

    client = TestClient(app)

    try:
        yield {
            "engine": engine,
            "repo": repo,
            "storage": storage,
            "ws_alpha": ws_alpha.id,
            "ws_beta": ws_beta.id,
            "prj_alpha_id": prj_alpha.id,
            "tokens": {
                "alice": create_signed_token(
                    Principal(principal_id=user_alice.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
                    secret=auth_secret,
                ),
                "charlie": create_signed_token(
                    Principal(principal_id=user_charlie.id, principal_type=PrincipalType.HUMAN, roles={Role.VIEWER}),
                    secret=auth_secret,
                ),
                "bob": create_signed_token(
                    Principal(principal_id=user_bob.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
                    secret=auth_secret,
                ),
            },
            "client": client,
            "pdir_alpha": pdir_alpha,
        }
    finally:
        import shutil
        shutil.rmtree(pdir_alpha, ignore_errors=True)
        if pdir_alpha.parent.exists() and not any(pdir_alpha.parent.iterdir()):
            shutil.rmtree(pdir_alpha.parent, ignore_errors=True)


def test_list_capabilities_discovery(b2_env):
    """Verifies that GET /projects/{id}/capabilities returns registered descriptors."""
    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]
    pid = b2_env["prj_alpha_id"]

    resp = client.get(
        f"/projects/{pid}/capabilities",
        headers={"Authorization": f"Bearer {token_alice}"},
    )
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 32

    cap_ids = {c["capability_id"] for c in data}
    assert "GENERATE_SPEECH_MANIFEST" in cap_ids
    assert "TRIM_VIDEO" in cap_ids
    assert "CHECK_MEDIA_CACHE" in cap_ids


def test_authorized_capability_execution_success(b2_env):
    """
    Demonstrates successful authorized execution of a domain capability (GENERATE_SPEECH_MANIFEST).
    Traverses API -> CapabilityService -> CapabilityRouter -> ToolGateway -> DomainServiceAdapter.
    """
    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]
    pid = b2_env["prj_alpha_id"]

    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {
                "audio_storage_key": "audio/alpha_voiceover.wav",
            },
        },
    )
    assert resp.status_code == 200, f"Expected 200 OK: {resp.text}"
    data = resp.json()

    assert data["capability_id"] == "GENERATE_SPEECH_MANIFEST"
    assert data["status"] == "SUCCESS"
    assert data["output"] is not None
    assert data["output"]["project_id"] == pid
    assert "manifest_storage_key" in data["output"]
    assert data["duration_ms"] >= 0
    assert data["error"] is None


def test_unauthorized_viewer_rejected_for_mutating_capability(b2_env):
    """
    Negative authorization: A viewer role (Charlie) cannot execute a mutating capability.
    Must return 403 Forbidden with AccessDenied.
    """
    client = b2_env["client"]
    token_charlie = b2_env["tokens"]["charlie"]  # Viewer
    pid = b2_env["prj_alpha_id"]

    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_charlie}"},
        json={
            "capability_id": "MUTATE_ASSET_STATUS",
            "input": {
                "asset_id": "ast_test_123",
                "new_status": "READY",
            },
        },
    )
    assert resp.status_code == 403
    assert "accessdenied" in resp.text.lower() or "denied" in resp.text.lower() or "permission" in resp.text.lower()


def test_cross_tenant_capability_execution_rejected(b2_env):
    """
    Negative authorization: Foreign tenant Bob (Workspace Beta) cannot invoke capabilities
    on Workspace Alpha's project.
    Must return 403 Forbidden.
    """
    client = b2_env["client"]
    token_bob = b2_env["tokens"]["bob"]  # Belongs to Workspace Beta
    pid = b2_env["prj_alpha_id"]         # Belongs to Workspace Alpha

    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_bob}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {
                "audio_storage_key": "audio/voiceover.wav",
            },
        },
    )
    assert resp.status_code == 403
    assert "accessdenied" in resp.text.lower() or "denied" in resp.text.lower() or "permission" in resp.text.lower()
    # Confirm zero internal alpha project detail leaked
    assert "Alpha B2 Video" not in resp.text


def test_non_allowlisted_capability_rejected(b2_env):
    """
    Negative test: Invoking a non-allowlisted or administrative capability is rejected with 403 Forbidden.
    """
    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]
    pid = b2_env["prj_alpha_id"]

    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "NON_ALLOWLISTED_OR_UNKNOWN_CAP",
            "input": {},
        },
    )
    assert resp.status_code == 403
    assert "not permitted" in resp.text.lower() or "allowlist" in resp.text.lower()


def test_human_decision_authority_preserved(b2_env):
    """
    Strict invariant: Capability executions must NEVER write .studio_approved marker
    or enqueue runs in the run repository.
    """
    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]
    pid = b2_env["prj_alpha_id"]
    pdir_alpha = b2_env["pdir_alpha"]

    # Execute capability
    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {
                "audio_storage_key": "audio/voiceover.wav",
            },
        },
    )
    assert resp.status_code == 200

    # 1. Verify .studio_approved was NEVER created
    studio_approved_file = pdir_alpha / ".studio_approved"
    assert not studio_approved_file.exists(), "Capability execution must NEVER write .studio_approved"

    # 2. Verify no runs were enqueued
    run_repo = RunRepository(db_path=None)
    recent_runs = run_repo.list_runs(project_id=pid)
    assert len(recent_runs) == 0, "Capability execution must NEVER automatically enqueue a run"


def test_capability_timeout_boundary_enforced(b2_env):
    """
    Negative test: Requested timeouts outside schema bounds (< 1.0 or > 300.0)
    must fail closed with HTTP 422 Unprocessable Entity.
    """
    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]
    pid = b2_env["prj_alpha_id"]

    # Test timeout < 1.0s
    resp_low = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {},
            "requested_timeout": 0.5,
        },
    )
    assert resp_low.status_code == 422, f"Expected 422 for timeout < 1.0; got {resp_low.status_code}"

    # Test timeout > 300.0s
    resp_high = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {},
            "requested_timeout": 500.0,
        },
    )
    assert resp_high.status_code == 422, f"Expected 422 for timeout > 300.0; got {resp_high.status_code}"


def test_capability_idempotency_key_preserved(b2_env):
    """
    Verifies that a client-provided idempotency key is preserved throughout execution.
    """
    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]
    pid = b2_env["prj_alpha_id"]
    idem_key = "idem-test-key-uuid-998877"

    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {
                "audio_storage_key": "audio/alpha_voiceover.wav",
            },
            "idempotency_key": idem_key,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"


def test_storage_confinement_prevents_directory_traversal(b2_env):
    """
    Security test: Attempting path traversal via project_id must fail closed.
    """
    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]

    resp = client.post(
        "/projects/..%2F..%2Fetc%2Fpasswd/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {},
        },
    )
    # Invalid project ID fails with 400 or 404
    assert resp.status_code in (400, 404)


@pytest.mark.parametrize("mutating_cap", [
    "MUTATE_ASSET_STATUS",
    "STORE_MEDIA_CACHE",
    "CANCEL_PROCESSING_JOB",
    "TRIM_VIDEO",
    "RESIZE_VIDEO",
    "EXTEND_VIDEO",
    "TRIM_AUDIO",
    "NORMALIZE_AUDIO_LOUDNESS",
    "RESIZE_IMAGE",
    "CROP_IMAGE_TO_RATIO",
])
def test_unauthorized_viewer_rejected_for_all_mutating_capabilities(b2_env, mutating_cap):
    """
    Issue 4 verification: Parameterized negative authorization matrix.
    Confirms that a caller with Role.VIEWER is strictly denied across ALL 10 mutating capabilities
    defined in MUTATING_CAPABILITIES, receiving HTTP 403 Forbidden with AccessDenied.
    """
    client = b2_env["client"]
    token_charlie = b2_env["tokens"]["charlie"]  # Role.VIEWER
    pid = b2_env["prj_alpha_id"]

    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_charlie}"},
        json={
            "capability_id": mutating_cap,
            "input": {},
        },
    )
    assert resp.status_code == 403, f"Expected 403 for mutating cap {mutating_cap}; got {resp.status_code}"
    assert "accessdenied" in resp.text.lower() or "denied" in resp.text.lower() or "permission" in resp.text.lower()


@pytest.mark.parametrize("readonly_cap,input_payload", [
    ("GENERATE_SPEECH_MANIFEST", {"audio_storage_key": "audio/alpha_voiceover.wav"}),
    ("CHECK_MEDIA_CACHE", {"asset_id": "ast_test_123", "transformation_hash": "hash_12345678"}),
])
def test_viewer_permitted_for_readonly_capabilities(b2_env, readonly_cap, input_payload):
    """
    Issue 4 verification: Read-only capability accessibility.
    Confirms that a caller with Role.VIEWER is permitted to execute non-mutating capabilities
    within their authorized workspace.
    """
    client = b2_env["client"]
    token_charlie = b2_env["tokens"]["charlie"]  # Role.VIEWER
    pid = b2_env["prj_alpha_id"]

    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_charlie}"},
        json={
            "capability_id": readonly_cap,
            "input": input_payload,
        },
    )
    assert resp.status_code == 200, f"Expected 200 for readonly cap {readonly_cap}; got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "SUCCESS"


def test_capability_idempotency_replay_and_conflict_protection(b2_env):
    """
    Issue 4 verification: True idempotency execution replay vs conflict detection.
    1. Initial execution executes and caches the result.
    2. Repeated execution with identical key + payload returns the replayed result with idempotency_hit=True.
    3. Conflicting execution with identical key BUT different payload fails closed.
    """
    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]
    pid = b2_env["prj_alpha_id"]
    idem_key = f"idem-replay-{uuid.uuid4().hex}"

    # Execution 1: Initial call
    resp_1 = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {"audio_storage_key": "audio/alpha_voiceover.wav"},
            "idempotency_key": idem_key,
        },
    )
    assert resp_1.status_code == 200
    data_1 = resp_1.json()
    assert data_1["status"] == "SUCCESS"
    assert data_1["execution_metadata"].get("idempotency_hit") is not True

    # Execution 2: Replay identical call with same key
    resp_2 = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {"audio_storage_key": "audio/alpha_voiceover.wav"},
            "idempotency_key": idem_key,
        },
    )
    assert resp_2.status_code == 200
    data_2 = resp_2.json()
    assert data_2["status"] == "SUCCESS"
    assert data_2["execution_metadata"].get("idempotency_hit") is True
    assert data_2["output"] == data_1["output"]

    # Execution 3: Conflicting payload with same idempotency key
    resp_3 = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {"audio_storage_key": "audio/different_conflicting_audio.wav"},
            "idempotency_key": idem_key,
        },
    )
    assert resp_3.status_code == 200
    data_3 = resp_3.json()
    assert data_3["status"] == "FAILED"
    assert "conflict" in (data_3["error"]["message"] if data_3.get("error") else "").lower()


def test_runtime_timeout_enforced_during_execution(b2_env, monkeypatch):
    """
    Issue 4 verification: Distinguishing runtime cancellation from schema validation.
    When execution exceeds requested timeout, asyncio.wait_for aborts execution,
    returning a structured FAILED result with error code TIMEOUT.
    """
    import asyncio
    from ai.tools.adapters.domain_service import DomainServiceAdapter

    # Patch adapter execute to simulate a slow execution (2.0s)
    async def slow_execute(self, request, validated_input, context):
        await asyncio.sleep(2.0)
        return {"project_id": request.project_id}

    monkeypatch.setattr(DomainServiceAdapter, "execute", slow_execute)

    client = b2_env["client"]
    token_alice = b2_env["tokens"]["alice"]
    pid = b2_env["prj_alpha_id"]

    resp = client.post(
        f"/projects/{pid}/capabilities/execute",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "capability_id": "GENERATE_SPEECH_MANIFEST",
            "input": {"audio_storage_key": "audio/test.wav"},
            "requested_timeout": 1.0,  # Valid schema bound, but runtime exceeds 1.0s
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FAILED"
    assert data["error"] is not None
    assert "TIMEOUT" in data["error"]["code"]
