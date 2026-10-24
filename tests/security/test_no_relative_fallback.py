"""
tests/security/test_no_relative_fallback.py
===========================================
Regression tests verifying that when resolve_project_dir raises an error,
no component falls back to constructing an unconfined relative Path("projects").

Covers the three write paths:
1. StateStore.export_disk_cache (.pipeline_state.json)
2. CanonicalDocumentRepository.commit_candidate (05_blueprint.json)
3. CreativeService.apply_proposal (master_plan.md)

Acceptance Criteria:
- resolve_project_dir failure prevents any file writes under tmp_path/projects.
- commit_candidate and apply_proposal fail BEFORE any database mutation.
- Idempotency record is marked FAILED on path resolution failure.
- Database state remains unchanged.
"""

from datetime import datetime, timezone
import hashlib
import json
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
from scripts.core.canonical_document_repository import CanonicalDocumentRepository
from scripts.security.path_security import TenantSecurityError


@pytest.fixture
def test_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Hermetic test environment for relative fallback elimination checks."""
    db_file = tmp_path / "test_no_relative_fallback.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    auth_secret = "test-no-relative-fallback-secret-32bytes!"
    monkeypatch.setenv("AUTH_SECRET_KEY", auth_secret)

    engine = DatabaseEngine(db_url=db_url)
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)
    run_suffix = uuid.uuid4().hex[:8]
    ws_id = f"ws_fallback_{run_suffix}"
    prj_id = f"prj_fallback_{run_suffix}"

    user = repo.create_user(f"usr_{run_suffix}", "user@fallback.com")
    repo.create_workspace(ws_id, "Fallback Test Workspace", created_by=user.id)
    repo.add_member(ws_id, user.id, Role.EDITOR)
    repo.create_project(prj_id, ws_id, "Fallback Test Project", created_by=user.id)

    # Initial blueprint and project state at revision 1
    init_doc = {
        "blueprint_version": "2.0.0",
        "project_id": prj_id,
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {
                "scene_id": "scene_01",
                "template": "HeadlineTemplate",
                "startFrame": 0,
                "durationFrames": 150,
                "content": {"text": "Initial Text"},
            }
        ],
    }
    raw_bytes = json.dumps(init_doc).encode("utf-8")
    init_storage_key = f"workspaces/{ws_id}/projects/{prj_id}/blueprints/rev_1_init/blueprint.json"
    storage.put(init_storage_key, raw_bytes, content_type="application/json")
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()

    with engine.transaction() as conn:
        conn.execute(
            """
            INSERT INTO project_artifact_versions (
                id, workspace_id, project_id, artifact_kind, revision, content_hash, storage_key, created_by, created_at
            ) VALUES (?, ?, ?, 'blueprint', 1, ?, ?, ?, ?)
            """,
            (
                f"art_init_{prj_id}_rev1",
                ws_id,
                prj_id,
                content_hash,
                init_storage_key,
                user.id,
                now_iso,
            ),
        )

    client = TestClient(app)
    token = create_signed_token(
        Principal(principal_id=user.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
        secret=auth_secret,
    )

    yield {
        "engine": engine,
        "storage": storage,
        "client": client,
        "token": token,
        "ws_id": ws_id,
        "prj_id": prj_id,
        "user_id": user.id,
        "init_doc": init_doc,
        "tmp_path": tmp_path,
    }

    set_database_engine(None)
    set_storage_service(None)


def test_state_store_export_disk_cache_no_relative_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    1. scripts/core/state_store.py: export_disk_cache
    When resolve_project_dir raises, must return None and write NO file under tmp_path/projects.
    """
    # 1. Switch working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    # 2. Pre-create the directory that relative fallback would target: Path("projects") / ws_id / prj_id
    relative_target_dir = tmp_path / "projects" / "ws_state_test" / "prj_state_test"
    relative_target_dir.mkdir(parents=True, exist_ok=True)

    # 3. Monkeypatch resolve_project_dir to raise TenantSecurityError
    def mock_resolve(*args, **kwargs):
        raise TenantSecurityError("Simulated path traversal / security rejection in resolve_project_dir")

    monkeypatch.setattr("scripts.core.security.path_policy.resolve_project_dir", mock_resolve)
    monkeypatch.setattr("scripts.security.path_security.resolve_project_dir", mock_resolve)

    # 4. Attempt export_disk_cache
    state = ProjectState(
        project_id="prj_state_test",
        workspace_id="ws_state_test",
        revision=1,
        lifecycle_state=LifecycleState.DRAFT.value,
    )
    res = StateStore.export_disk_cache(state)

    # Contract: export_disk_cache is non-throwing, returns None on failure
    assert res is None, f"Expected None on path resolution failure, got {res}"

    # Verify NO files were created under tmp_path/projects
    written_files = [str(p.relative_to(tmp_path)) for p in (tmp_path / "projects").glob("**/*") if p.is_file()]
    assert written_files == [], f"Unexpected files written to projects directory via fallback: {written_files}"


def test_canonical_document_repository_commit_candidate_no_relative_fallback(
    test_setup, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """
    2. scripts/core/canonical_document_repository.py: commit_candidate
    When resolve_project_dir raises, must fail BEFORE database write and write NO file under tmp_path/projects.
    """
    env = test_setup
    engine = env["engine"]
    storage = env["storage"]
    ws_id = env["ws_id"]
    prj_id = env["prj_id"]
    user_id = env["user_id"]
    init_doc = env["init_doc"]

    doc_repo = CanonicalDocumentRepository(engine, storage)

    # 1. Switch working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    # 2. Pre-create the directory that relative fallback would target
    relative_target_dir = tmp_path / "projects" / ws_id / prj_id
    relative_target_dir.mkdir(parents=True, exist_ok=True)

    # 3. Monkeypatch resolve_project_dir to raise TenantSecurityError
    def mock_resolve(*args, **kwargs):
        raise TenantSecurityError("Simulated path traversal in resolve_project_dir")

    monkeypatch.setattr("scripts.core.security.path_policy.resolve_project_dir", mock_resolve)
    monkeypatch.setattr("scripts.security.path_security.resolve_project_dir", mock_resolve)

    # 4. Attempt commit_candidate
    candidate_doc = json.loads(json.dumps(init_doc))
    candidate_doc["scenes"][0]["content"]["text"] = "Attempted Revision 2"

    with pytest.raises(TenantSecurityError):
        doc_repo.commit_candidate(
            workspace_id=ws_id,
            project_id=prj_id,
            expected_revision=1,
            candidate_doc=candidate_doc,
            actor_id=user_id,
            operation_id=f"op_{uuid.uuid4().hex[:8]}",
        )

    # 5. Verify NO files were written under tmp_path/projects
    written_files = [str(p.relative_to(tmp_path)) for p in (tmp_path / "projects").glob("**/*") if p.is_file()]
    assert written_files == [], f"Unexpected files written via fallback: {written_files}"

    # 6. Verify database state was NOT modified (revision remained 1)
    with engine.transaction() as conn:
        row = conn.execute(
            "SELECT MAX(revision) FROM project_artifact_versions WHERE workspace_id = ? AND project_id = ? AND artifact_kind = 'blueprint'",
            (ws_id, prj_id),
        ).fetchone()
        max_rev = row[0] if row else None
        assert max_rev == 1, f"Database was modified despite path resolution failure! Max revision is {max_rev}"


def test_creative_service_apply_proposal_no_relative_fallback(
    test_setup, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """
    3. api/services/creative_service.py: apply_proposal
    When resolve_project_dir raises, must fail with 400, mark idempotency record FAILED,
    leave database unchanged, and write NO file under tmp_path/projects.
    """
    env = test_setup
    engine = env["engine"]
    client = env["client"]
    token = env["token"]
    ws_id = env["ws_id"]
    prj_id = env["prj_id"]

    # 1. Propose valid creative proposal
    prop_resp = client.post(
        f"/projects/{prj_id}/creative/proposals",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "SaaS Showcase Video", "audio_mode": "VO_MUSIC"},
    )
    assert prop_resp.status_code == 200
    prop_data = prop_resp.json()

    # 2. Switch working directory to tmp_path
    monkeypatch.chdir(tmp_path)

    # 3. Pre-create the directory that relative fallback would target
    relative_target_dir = tmp_path / "projects" / ws_id / prj_id
    relative_target_dir.mkdir(parents=True, exist_ok=True)

    # 4. Monkeypatch resolve_project_dir to raise TenantSecurityError
    def mock_resolve(*args, **kwargs):
        raise TenantSecurityError("Simulated path traversal in resolve_project_dir")

    monkeypatch.setattr("scripts.core.security.path_policy.resolve_project_dir", mock_resolve)
    monkeypatch.setattr("scripts.security.path_security.resolve_project_dir", mock_resolve)

    # 5. Call apply
    op_id = f"op_fallback_test_{uuid.uuid4().hex[:8]}"
    apply_resp = client.post(
        f"/projects/{prj_id}/creative/apply",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "proposal_id": prop_data["proposal_id"],
            "base_revision": prop_data["base_revision"],
            "blueprint": prop_data["candidate_blueprint"],
            "master_plan": prop_data["master_plan"],
            "operation_id": op_id,
        },
    )

    # Must fail with 400 Bad Request
    assert apply_resp.status_code == 400, f"Expected 400 Bad Request, got {apply_resp.status_code}: {apply_resp.text}"
    assert "PATH_RESOLUTION_FAILED" in apply_resp.text or "path" in apply_resp.text.lower()

    # 6. Verify idempotency record is marked FAILED
    with engine.transaction() as conn:
        row = conn.execute(
            "SELECT status, error_json FROM authoring_idempotency_records WHERE operation_id = ?",
            (op_id,),
        ).fetchone()
        assert row is not None, "Idempotency record was not found"
        assert row[0] == "FAILED", f"Idempotency record status is {row[0]}, expected FAILED"

    # 7. Verify database was NOT modified (revision remains 1)
    with engine.transaction() as conn:
        row = conn.execute(
            "SELECT MAX(revision) FROM project_artifact_versions WHERE workspace_id = ? AND project_id = ? AND artifact_kind = 'blueprint'",
            (ws_id, prj_id),
        ).fetchone()
        max_rev = row[0] if row else None
        assert max_rev == 1, f"Database was modified despite path resolution failure! Max revision is {max_rev}"

    # 8. Verify NO files were written under tmp_path/projects
    written_files = [str(p.relative_to(tmp_path)) for p in (tmp_path / "projects").glob("**/*") if p.is_file()]
    assert written_files == [], f"Unexpected files written via fallback: {written_files}"
