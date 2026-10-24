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
        shutil.rmtree(Path("projects") / ws_alpha.id, ignore_errors=True)


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

        # Call get_lifecycle_dto: must raise TenantSecurityError due to inconsistent tenant ownership
        from scripts.core.database import TenantSecurityError
        with pytest.raises(TenantSecurityError, match="Tenant mismatch"):
            ProjectService.get_lifecycle_dto(pid)
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


def test_project_service_lifecycle_dto_missing_disk_loads_db(b1_env):
    """
    Verifies that when on-disk state is absent, ProjectService.get_lifecycle_dto
    safely falls back to the authoritative database state.
    """
    from api.services.project_service import ProjectService
    from scripts.core.state_store import StateStore
    import json

    pid = b1_env["prj_alpha_id"]
    pdir = b1_env["pdir_alpha"]
    engine = b1_env["engine"]

    # Ensure no disk state exists
    (pdir / StateStore.STATE_FILE).unlink(missing_ok=True)

    # Set DB state with revision = 7 and valid JSON
    state_payload = {
        "project_id": pid,
        "workspace_id": b1_env["ws_alpha"],
        "revision": 7,
        "lifecycle_state": "DRAFT",
    }
    with engine.transaction() as conn:
        conn.execute(
            "UPDATE project_states SET revision = 7, lifecycle_state = 'DRAFT', state_json = ? WHERE project_id = ?",
            (json.dumps(state_payload), pid),
        )

    dto = ProjectService.get_lifecycle_dto(pid)
    assert dto.revision == 7
    assert dto.lifecycle_state == "DRAFT"


def test_project_service_lifecycle_dto_missing_disk_fails_closed_on_corrupt_db(b1_env):
    """
    Verifies that when on-disk state is absent and the database state_json is corrupted,
    ProjectService.get_lifecycle_dto fails closed and raises StateCorruptedError.
    """
    from api.services.project_service import ProjectService
    from scripts.core.state_store import StateStore, StateCorruptedError

    pid = b1_env["prj_alpha_id"]
    pdir = b1_env["pdir_alpha"]
    engine = b1_env["engine"]

    # Ensure no disk state exists
    (pdir / StateStore.STATE_FILE).unlink(missing_ok=True)

    # Set DB state with corrupt JSON
    with engine.transaction() as conn:
        conn.execute(
            "UPDATE project_states SET revision = 9, state_json = '{malformed: true, missing_quotes' WHERE project_id = ?",
            (pid,),
        )

    with pytest.raises(StateCorruptedError, match="corrupted"):
        ProjectService.get_lifecycle_dto(pid)


def test_different_project_contexts_produce_different_planning_decisions(b1_env):
    """
    Issue 1 verification:
    Proves that two authorized projects with meaningfully different context constraints
    (e.g., excluded templates and brand colors) produce appropriately different creative
    planning and compilation decisions under otherwise identical user prompts.
    """
    import shutil
    from scripts.core.state_store import StateStore
    from scripts.core.state_model import ProjectState, LifecycleState

    client = b1_env["client"]
    token_alice = b1_env["tokens"]["alice"]
    ws_alpha = b1_env["ws_alpha"]
    repo = b1_env["repo"]

    from scripts.security.path_security import resolve_project_dir

    # Project 1: Standard / Default Project
    prj_1 = repo.create_project("prj_diff_default", ws_alpha, "Default Project", created_by="usr_alice")
    pdir_1 = resolve_project_dir(prj_1.id, workspace_id=ws_alpha, create=True)
    state_1 = ProjectState(
        project_id=prj_1.id,
        workspace_id=ws_alpha,
        revision=1,
        lifecycle_state=LifecycleState.DRAFT,
        run_metadata={},
    )
    StateStore._persist_atomic(pdir_1, state_1)

    # Project 2: Constrained Project with excluded "rui-intro" and explicit brand colors
    prj_2 = repo.create_project("prj_diff_constrained", ws_alpha, "Constrained Project", created_by="usr_alice")
    pdir_2 = resolve_project_dir(prj_2.id, workspace_id=ws_alpha, create=True)
    state_2 = ProjectState(
        project_id=prj_2.id,
        workspace_id=ws_alpha,
        revision=1,
        lifecycle_state=LifecycleState.DRAFT,
        run_metadata={
            "excluded_templates": ["rui-intro"],
            "brand_colors": ["#112233", "#445566"],
        },
    )
    StateStore._persist_atomic(pdir_2, state_2)

    prompt = "Create a modern fast-paced technical product showcase video"

    try:
        # Request for Project 1
        resp_1 = client.post(
            f"/projects/{prj_1.id}/creative/proposals",
            headers={"Authorization": f"Bearer {token_alice}"},
            json={"prompt": prompt, "aspect_ratio": "9:16"},
        )
        assert resp_1.status_code == 200, f"Error: {resp_1.text}"
        data_1 = resp_1.json()

        # Request for Project 2 with identical prompt
        resp_2 = client.post(
            f"/projects/{prj_2.id}/creative/proposals",
            headers={"Authorization": f"Bearer {token_alice}"},
            json={"prompt": prompt, "aspect_ratio": "9:16"},
        )
        assert resp_2.status_code == 200, f"Error: {resp_2.text}"
        data_2 = resp_2.json()

        # 1. First scene template selection decision must differ!
        scene_1_template = data_1["candidate_blueprint"]["scenes"][0]["template"]
        scene_2_template = data_2["candidate_blueprint"]["scenes"][0]["template"]

        # Default project should select "rui-intro"
        assert scene_1_template == "rui-intro", f"Expected rui-intro, got {scene_1_template}"
        # Constrained project MUST NOT select "rui-intro" (it is excluded) and should fallback to "rui-title-card"
        assert scene_2_template == "rui-title-card", f"Expected rui-title-card, got {scene_2_template}"
        assert scene_1_template != scene_2_template, "Template decision must differ based on authorized context!"

        # 2. Brief constraints must reflect project context
        assert "rui-intro" in data_2["brief"]["constraints"]["excluded_templates"]
        assert "rui-intro" not in data_1["brief"]["constraints"]["excluded_templates"]
        assert data_2["brief"]["constraints"]["brand_colors"] == ["#112233", "#445566"]

        # 3. Candidate blueprint scene props in Project 2 must include brand colors
        scene_2_props = data_2["candidate_blueprint"]["scenes"][0].get("template_props", {})
        assert scene_2_props.get("brand_colors") == ["#112233", "#445566"]

    finally:
        shutil.rmtree(pdir_1, ignore_errors=True)
        shutil.rmtree(pdir_2, ignore_errors=True)
        shutil.rmtree(Path("projects") / ws_alpha, ignore_errors=True)


def test_startup_to_authenticated_api_retrieves_canonical_knowledge(b1_env):
    """
    Issue 2 verification:
    Proves that canonical knowledge catalog initialized at startup is genuinely
    retrieved and utilized during authenticated creative proposal requests.
    """
    from ai.knowledge.catalog_service import get_knowledge_catalog_service

    # Ensure catalog is initialized as it would be at FastAPI startup
    catalog_svc = get_knowledge_catalog_service()
    indexed_count = catalog_svc.initialize_catalog(verify_hash=True)
    assert indexed_count > 0, "Canonical knowledge catalog must index chunks"

    client = b1_env["client"]
    token_alice = b1_env["tokens"]["alice"]
    pid = b1_env["prj_alpha_id"]

    resp = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "prompt": "Explainer video about video editing with sound effects and motion personality",
            "aspect_ratio": "9:16",
        },
    )

    assert resp.status_code == 200, f"Error: {resp.text}"
    data = resp.json()

    # Verify context_diagnostics contains retrieved knowledge
    assert "context_diagnostics" in data
    retrieved = data["context_diagnostics"].get("retrieved_knowledge", [])
    assert len(retrieved) > 0, "Production request must retrieve canonical knowledge chunks"

    # Verify canonical knowledge documents are retrieved
    doc_ids = {k.get("document_id") for k in retrieved if k.get("document_id")}
    assert any(
        doc in doc_ids
        for doc in ("know_taste_motion_personality", "know_taste_sfx_matrix", "know_playbook_video_copy", "know_playbook_motion_collage")
    ), f"Expected canonical documents in retrieved knowledge; got {doc_ids}"

    # Verify diagnostics also contains KNOWLEDGE_RETRIEVAL record
    diag_types = [d.get("type") for d in data.get("diagnostics", [])]
    assert "KNOWLEDGE_RETRIEVAL" in diag_types
