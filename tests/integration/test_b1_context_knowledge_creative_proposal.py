"""
tests/integration/test_b1_context_knowledge_creative_proposal.py
==================================================================
End-to-end integration test suite verifying Workstream B1:
- Real production API caller invokes ContextBuilder & KnowledgeRouter.
- Deterministic context_hash and context_diagnostics returned.
- Changing authorized project context measurably influences the creative proposal result.
- Strict tenant boundary enforcement prevents cross-tenant access and data leakage.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend, set_storage_service


@pytest.fixture
def b1_env(tmp_path, monkeypatch):
    """Hermetic SaaS environment for Workstream B1 testing."""
    db_file = tmp_path / "b1_runtime.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    auth_secret = "b1-test-signing-secret-for-pytest-harness-32!"
    monkeypatch.setenv("AUTH_SECRET_KEY", auth_secret)

    engine = DatabaseEngine(db_url=db_url)
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)

    # 1. Tenant Alpha
    user_alice = repo.create_user("usr_alice", "alice@alpha.com")
    ws_alpha = repo.create_workspace("ws_alpha", "Workspace Alpha", created_by=user_alice.id)
    repo.add_member(ws_alpha.id, user_alice.id, Role.EDITOR)

    # 2. Tenant Beta (Foreign)
    user_bob = repo.create_user("usr_bob", "bob@beta.com")
    ws_beta = repo.create_workspace("ws_beta", "Workspace Beta", created_by=user_bob.id)
    repo.add_member(ws_beta.id, user_bob.id, Role.EDITOR)

    # 3. Create Project in Workspace Alpha
    prj_alpha = repo.create_project("prj_alpha_b1", ws_alpha.id, "Alpha Context Video", created_by=user_alice.id)

    # Create project directory on disk
    pdir_alpha = Path(f"projects/{prj_alpha.id}")
    pdir_alpha.mkdir(parents=True, exist_ok=True)

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


def test_authenticated_proposal_invokes_context_builder(b1_env):
    """
    Verifies that POST /projects/{pid}/creative/proposals executes ContextBuilder
    and returns a valid context_hash and context_diagnostics in the response.
    """
    client = b1_env["client"]
    token_alice = b1_env["tokens"]["alice"]
    pid = b1_env["prj_alpha_id"]

    resp = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "prompt": "Create a 15-second product launch video for a SaaS tool with voiceover and music",
            "aspect_ratio": "9:16",
        },
    )

    assert resp.status_code == 200, f"Expected 200 OK: {resp.text}"
    data = resp.json()

    assert "context_hash" in data, "Response must include context_hash"
    assert data["context_hash"] is not None
    assert len(data["context_hash"]) == 64, "context_hash must be a valid 64-char SHA256 digest"

    assert "context_diagnostics" in data, "Response must include context_diagnostics"
    diag = data["context_diagnostics"]
    assert diag is not None
    assert diag["total_items_included"] > 0
    assert diag["total_estimated_tokens"] > 0


def test_changing_authorized_project_context_influences_proposal(b1_env):
    """
    Demonstrates that changing authorized project context (e.g. advancing revision or facts)
    measurably changes the assembled context_hash and proposal metadata.
    """
    client = b1_env["client"]
    token_alice = b1_env["tokens"]["alice"]
    pid = b1_env["prj_alpha_id"]
    engine = b1_env["engine"]

    # Request 1: Initial revision 1
    resp1 = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "prompt": "Explainer video about high speed video rendering",
            "aspect_ratio": "16:9",
        },
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    hash1 = data1["context_hash"]
    rev1 = data1["base_revision"]
    assert rev1 == 1

    # Mutate project state in authoritative SQL store to revision 2
    with engine.transaction() as conn:
        conn.execute("UPDATE project_states SET revision = 2 WHERE project_id = ?", (pid,))

    # Request 2: Exactly same prompt, but project state context changed
    resp2 = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "prompt": "Explainer video about high speed video rendering",
            "aspect_ratio": "16:9",
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    hash2 = data2["context_hash"]
    rev2 = data2["base_revision"]
    assert rev2 == 2

    # Assert that changing project context changed the context_hash
    assert hash1 != hash2, "Changing authorized project revision must change context_hash"


def test_cross_tenant_request_rejected_without_leakage(b1_env):
    """
    Negative authorization: Actor from Workspace Beta cannot access Workspace Alpha's project.
    Must return 403 Forbidden with zero project facts leaked.
    """
    client = b1_env["client"]
    token_bob = b1_env["tokens"]["bob"]  # Belongs to ws_beta
    pid = b1_env["prj_alpha_id"]         # Belongs to ws_alpha

    resp = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_bob}"},
        json={
            "prompt": "Attempt cross-tenant access to alpha video",
            "aspect_ratio": "9:16",
        },
    )

    assert resp.status_code == 403
    assert "accessdenied" in resp.text.lower() or "denied" in resp.text.lower()
    # Ensure no internal alpha data was exposed in error details
    assert "Alpha Context Video" not in resp.text


def test_project_service_lifecycle_dto_rejects_cross_tenant_state_pollution(b1_env):
    """
    Security test: If DB contains a project_states entry with a mismatched workspace_id,
    ProjectService.get_lifecycle_dto must NOT adopt the foreign state to pollute disk state.
    """
    from api.services.project_service import ProjectService
    from scripts.core.state_store import StateStore
    from scripts.core.state_model import ProjectState, LifecycleState

    pid = b1_env["prj_alpha_id"]
    pdir = b1_env["pdir_alpha"]
    engine = b1_env["engine"]

    # Initialize disk state with workspace_id = ws_alpha and revision = 5
    disk_state = ProjectState(
        project_id=pid,
        workspace_id=b1_env["ws_alpha"],
        revision=5,
        lifecycle_state=LifecycleState.DRAFT,
    )
    StateStore._persist_atomic(pdir, disk_state)

    try:
        # Inject mismatched DB state with workspace_id = ws_beta (foreign) and revision = 10
        with engine.transaction() as conn:
            conn.execute(
                "UPDATE project_states SET workspace_id = ?, revision = 10 WHERE project_id = ?",
                (b1_env["ws_beta"], pid),
            )

        # Call get_lifecycle_dto: must reject the mismatched foreign DB state and maintain revision 5
        dto = ProjectService.get_lifecycle_dto(pid)
        assert dto.revision == 5, f"Expected disk revision 5 to be preserved; got {dto.revision}"
    finally:
        (pdir / StateStore.STATE_FILE).unlink(missing_ok=True)


def test_project_service_lifecycle_dto_prevents_state_downgrade(b1_env):
    """
    State consistency test: If DB contains a stale lower revision than disk,
    get_lifecycle_dto must NOT downgrade the state revision.
    """
    from api.services.project_service import ProjectService
    from scripts.core.state_store import StateStore
    from scripts.core.state_model import ProjectState, LifecycleState

    pid = b1_env["prj_alpha_id"]
    pdir = b1_env["pdir_alpha"]
    engine = b1_env["engine"]

    # Set disk state at revision 8
    disk_state = ProjectState(
        project_id=pid,
        workspace_id=b1_env["ws_alpha"],
        revision=8,
        lifecycle_state=LifecycleState.DRAFT,
    )
    StateStore._persist_atomic(pdir, disk_state)

    try:
        # Set DB state at stale lower revision 3
        with engine.transaction() as conn:
            conn.execute(
                "UPDATE project_states SET revision = 3 WHERE project_id = ?",
                (pid,),
            )

        # Call get_lifecycle_dto: must preserve disk revision 8 (monotonicity)
        dto = ProjectService.get_lifecycle_dto(pid)
        assert dto.revision == 8, f"Expected higher revision 8 to be preserved; got {dto.revision}"
    finally:
        (pdir / StateStore.STATE_FILE).unlink(missing_ok=True)


def test_sensitive_data_not_leaked_into_context_diagnostics(b1_env):
    """
    Security test: Injected API keys and tokens in prompts must be sanitized
    and must not leak into context diagnostics or error payloads.
    """
    client = b1_env["client"]
    token_alice = b1_env["tokens"]["alice"]
    pid = b1_env["prj_alpha_id"]

    secret_key = "sk-live-super-secret-key-12345"
    resp = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "prompt": f"Create video using API key {secret_key} and token secret",
            "aspect_ratio": "16:9",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    # Diagnostics and response must NOT contain the raw secret key
    assert secret_key not in str(data.get("context_diagnostics", {})), "Secret key leaked in context_diagnostics"
    assert secret_key not in str(data.get("diagnostics", [])), "Secret key leaked in proposal diagnostics"
