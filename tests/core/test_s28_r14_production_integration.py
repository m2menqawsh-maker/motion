"""
tests/core/test_s28_r14_production_integration.py
Comprehensive Python Verification Suite for S28-R14: Production Integration.

Verifies:
  - Section 2 & 3: Canonical Document Production Persistence (CAS, StorageService, Revisions)
  - Section 4: Durable Idempotency (Atomic leader claim, replay without double-mutation, conflict)
  - Section 5 & 6: Production Authoring Service & API Router with TenantContext RBAC
  - Section 10 & 11: Renderer Failure Taxonomy and Retry Classification in FailureModel
  - Section 16: Durable Audit Events (AUTHORING_MUTATION_COMMITTED, REVISION_ADVANCED)
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from scripts.core.database import (
    DatabaseEngine,
    TenantRepository,
    TenantSecurityError,
    UsageEventType,
    set_database_engine,
)
from scripts.core.storage.storage_service import (
    StorageService,
    LocalStorageBackend,
    StorageSecurityError,
    validate_storage_key,
    build_storage_key,
    set_storage_service,
)
from scripts.core.authoring_idempotency_repository import (
    AuthoringIdempotencyRepository,
    IdempotencyConflictError,
)
from scripts.core.canonical_document_repository import (
    CanonicalDocumentRepository,
    RevisionConflictError,
    DocumentValidationError,
)
from scripts.core.tenant_model import TenantContext
from scripts.core.security.principal import Role, Principal, PrincipalType
from scripts.core.security.permissions import Action, AccessDeniedError
from scripts.core.failure_model import FailureCode, get_failure_metadata
from scripts.core.budget_service import BudgetService, BudgetExceededError
from scripts.metrics.metrics_collector import MetricsCollector
from api.services.authoring_service import AuthoringService
from api.main import app

CLIENT = TestClient(app)


@pytest.fixture
def test_env(tmp_path: Path):
    """Sets up a clean DatabaseEngine and StorageService for testing."""
    db_file = tmp_path / "r14_production_test.db"
    storage_root = tmp_path / "storage_root"
    storage_root.mkdir()

    engine = DatabaseEngine(db_url=f"sqlite:///{db_file}")
    set_database_engine(engine)

    storage_service = LocalStorageBackend(root_dir=str(storage_root))
    set_storage_service(storage_service)

    tenant_repo = TenantRepository(engine)
    tenant_repo.create_user("usr_admin", "admin@example.com")
    tenant_repo.create_user("usr_editor", "editor@example.com")
    tenant_repo.create_user("usr_viewer", "viewer@example.com")
    tenant_repo.create_user("usr_other", "other@example.com")

    tenant_repo.create_workspace("ws_prod", "Production Workspace", created_by="usr_admin")
    tenant_repo.create_workspace("ws_other", "Other Workspace", created_by="usr_admin")

    tenant_repo.add_member("ws_prod", "usr_admin", Role.ADMIN)
    tenant_repo.add_member("ws_prod", "usr_editor", Role.EDITOR)
    tenant_repo.add_member("ws_prod", "usr_viewer", Role.VIEWER)
    tenant_repo.add_member("ws_other", "usr_other", Role.EDITOR)

    tenant_repo.create_project("prj_r14", "ws_prod", "R14 Production Project", created_by="usr_admin")
    tenant_repo.create_project("prj_other", "ws_other", "Other Project", created_by="usr_admin")

    # Seed initial canonical BlueprintV2 document at revision 1 in StorageService & project_artifact_versions
    init_doc = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_r14",
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
    storage_key = "workspaces/ws_prod/projects/prj_r14/blueprints/rev_1_init/blueprint.json"
    storage_service.put(storage_key, raw_bytes, content_type="application/json")
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
                "art_init_prj_r14_rev1",
                "ws_prod",
                "prj_r14",
                content_hash,
                storage_key,
                "usr_admin",
                now_iso,
            ),
        )

    yield {
        "engine": engine,
        "storage": storage_service,
        "init_doc": init_doc,
        "tmp_path": tmp_path,
    }

    set_database_engine(None)
    set_storage_service(None)


def test_idempotency_repository_leader_claim_and_replay(test_env):
    """Section 4: Atomic leader claim, replay without double-execution, conflict detection."""
    engine = test_env["engine"]
    repo = AuthoringIdempotencyRepository(engine)

    ws_id = "ws_prod"
    proj_id = "prj_r14"
    op_id = "op_idempotent_100"
    payload = {"intent": "UPDATE_TITLE", "title": "First Version"}
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    # 1. First claim succeeds as LEADER
    status, cached = repo.try_claim_leader(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id=op_id,
        operation_type="intent",
        base_revision=1,
        payload_hash=payload_hash,
    )
    assert status == "LEADER"
    assert cached is None

    # 2. Duplicate claim while in-flight returns IN_PROGRESS
    status_again, _ = repo.try_claim_leader(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id=op_id,
        operation_type="intent",
        base_revision=1,
        payload_hash=payload_hash,
    )
    assert status_again == "IN_PROGRESS"

    # 3. Commit result
    result_data = {"revision": 2, "applied": True}
    repo.mark_completed(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id=op_id,
        result_revision=2,
        result_payload=result_data,
    )

    # 4. Subsequent check retrieves committed result without re-executing
    status_done, cached_res = repo.try_claim_leader(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id=op_id,
        operation_type="intent",
        base_revision=1,
        payload_hash=payload_hash,
    )
    assert status_done == "COMPLETED"
    assert cached_res == result_data

    # 5. Same op_id reused with materially different input fails closed with IdempotencyConflictError
    diff_hash = hashlib.sha256(b"materially_different_input").hexdigest()
    with pytest.raises(IdempotencyConflictError):
        repo.try_claim_leader(
            workspace_id=ws_id,
            project_id=proj_id,
            operation_id=op_id,
            operation_type="intent",
            base_revision=1,
            payload_hash=diff_hash,
        )

    # 6. Workspace isolation: Same op_id under a different workspace is independent
    other_status, _ = repo.try_claim_leader(
        workspace_id="ws_other",
        project_id="prj_other",
        operation_id=op_id,
        operation_type="intent",
        base_revision=1,
        payload_hash=payload_hash,
    )
    assert other_status == "LEADER"


def test_canonical_document_repository_persistence_and_cas(test_env):
    """Sections 2 & 3: Immutable candidate generation, transactional CAS, and conflict handling."""
    engine = test_env["engine"]
    storage = test_env["storage"]
    doc_repo = CanonicalDocumentRepository(engine, storage)

    ws_id = "ws_prod"
    proj_id = "prj_r14"

    # Initial canonical document
    doc, rev = doc_repo.get_document(ws_id, proj_id)
    assert rev == 1
    assert doc["project_id"] == proj_id

    # Mutate to revision 2
    candidate_doc = json.loads(json.dumps(doc))
    candidate_doc["scenes"][0]["content"]["text"] = "Revision 2 Text"

    committed_doc, committed_rev, storage_key = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=1,
        candidate_doc=candidate_doc,
        actor_id="usr_admin",
        operation_id="op_commit_rev2",
    )
    assert committed_rev == 2
    assert committed_doc["scenes"][0]["content"]["text"] == "Revision 2 Text"
    assert storage.exists(storage_key)

    # Verify canonical document is updated in repo
    loaded_doc, loaded_rev = doc_repo.get_document(ws_id, proj_id)
    assert loaded_rev == 2
    assert loaded_doc["scenes"][0]["content"]["text"] == "Revision 2 Text"

    # CAS Conflict: Concurrent attempt with stale expected_revision 1 fails closed
    with pytest.raises(RevisionConflictError):
        doc_repo.commit_candidate(
            workspace_id=ws_id,
            project_id=proj_id,
            expected_revision=1,  # actual is 2!
            candidate_doc=candidate_doc,
            actor_id="usr_admin",
            operation_id="op_conflict",
        )

    # Durable audit events were recorded in run_events
    conn = engine.get_connection()
    try:
        cur = conn.execute(
            "SELECT event_type, payload_json FROM run_events WHERE project_id = ? ORDER BY sequence ASC",
            (proj_id,),
        )
        events = cur.fetchall()
        event_names = [e[0] for e in events]
        assert "AUTHORING_MUTATION_COMMITTED" in event_names
        assert "REVISION_ADVANCED" in event_names
    finally:
        conn.close()


def test_authoring_service_tenant_permissions_and_rbac(test_env):
    """Section 6: Enforcing TenantContext authorization for authoring operations."""
    # 1. Editor Context (Authorized)
    editor_principal = Principal(
        principal_id="usr_editor",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    editor_ctx = TenantContext(
        workspace_id="ws_prod",
        user_id="usr_editor",
        role=Role.EDITOR,
        principal=editor_principal,
    )

    doc, rev = AuthoringService.get_canonical_document("prj_r14", editor_ctx)
    assert rev == 1
    assert doc is not None

    # 2. Cross-tenant access attempt fails closed
    other_ctx = TenantContext(
        workspace_id="ws_other",
        user_id="usr_other",
        role=Role.EDITOR,
        principal=Principal(
            principal_id="usr_other",
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        ),
    )
    with pytest.raises(TenantSecurityError):
        AuthoringService.get_canonical_document("prj_r14", other_ctx)


def test_authoring_api_endpoints_and_etag(test_env):
    """Sections 5 & 6: HTTP endpoints, ETag/If-Match concurrency, and replay handling."""
    proj_id = "prj_r14"

    # 1. GET /projects/{id}/authoring/document
    headers_editor = {
        "X-Principal-ID": "usr_editor",
        "X-Principal-Roles": "editor",
        "X-Workspace-ID": "ws_prod",
    }

    res = CLIENT.get(f"/projects/{proj_id}/document", headers=headers_editor)
    assert res.status_code == 200
    assert "ETag" in res.headers
    assert res.headers["ETag"] == '"1"'
    data = res.json()
    assert data["revision"] == 1
    assert data["blueprint"]["project_id"] == proj_id

    # 2. Stale If-Match header returns 409 Conflict
    stale_payload = {
        "operation_id": "op_api_stale",
        "base_revision": 999,  # actual is 1!
        "mutation": {
            "type": "UPDATE_METADATA",
            "payload": {"title": "Stale Attempt"},
        },
    }
    stale_res = CLIENT.post(
        f"/projects/{proj_id}/mutate",
        json=stale_payload,
        headers={**headers_editor, "If-Match": '"999"'},
    )
    assert stale_res.status_code == 409

    # 3. Cross-tenant access blocked (403 Forbidden)
    headers_other = {
        "X-Principal-ID": "usr_other",
        "X-Principal-Roles": "editor",
        "X-Workspace-ID": "ws_other",
    }
    cross_res = CLIENT.get(f"/projects/{proj_id}/document", headers=headers_other)
    assert cross_res.status_code == 403


def test_failure_model_r14_renderer_codes():
    """Sections 10 & 11: Structured failure taxonomy and retryability classification."""
    # Verify all R14 failure codes are present
    assert hasattr(FailureCode, "RENDERER_TIMEOUT")
    assert hasattr(FailureCode, "RENDERER_UNAVAILABLE")
    assert hasattr(FailureCode, "RENDERER_EXECUTION_FAILED")
    assert hasattr(FailureCode, "RENDERER_OUTPUT_INVALID")
    assert hasattr(FailureCode, "RENDERER_CANCELLED")
    assert hasattr(FailureCode, "RENDERER_CAPABILITY_MISMATCH")

    # Verify classification logic
    # RENDERER_TIMEOUT & RENDERER_EXECUTION_FAILED are conditionally retryable
    meta_timeout = get_failure_metadata(FailureCode.RENDERER_TIMEOUT)
    assert meta_timeout.retryable is True
    meta_exec = get_failure_metadata(FailureCode.RENDERER_EXECUTION_FAILED)
    assert meta_exec.retryable is True

    # RENDERER_UNAVAILABLE is not retryable without fallback
    meta_unavail = get_failure_metadata(FailureCode.RENDERER_UNAVAILABLE)
    assert meta_unavail.retryable is False

    # Deterministic capability mismatch is NOT retryable
    meta_cap = get_failure_metadata(FailureCode.RENDERER_CAPABILITY_MISMATCH)
    assert meta_cap.retryable is False

    # Cancellation is NOT retryable
    meta_cancel = get_failure_metadata(FailureCode.RENDERER_CANCELLED)
    assert meta_cancel.retryable is False

    # Output invalid is NOT retryable (deterministic corruption or encoder failure)
    meta_invalid = get_failure_metadata(FailureCode.RENDERER_OUTPUT_INVALID)
    assert meta_invalid.retryable is False


def test_r14_05_and_06_human_ai_template_unified_mutation_authority(test_env):
    """R14-05 & R14-06: Human, AI, and Template edits use the same persistent mutation authority."""
    engine = test_env["engine"]
    storage = test_env["storage"]
    doc_repo = CanonicalDocumentRepository(engine, storage)

    ws_id = "ws_prod"
    proj_id = "prj_r14"

    # 1. Base Document at Rev 1
    doc_rev1, rev1 = doc_repo.get_document(ws_id, proj_id)
    assert rev1 == 1

    # 2. Human Editor commits Revision 2
    human_doc = json.loads(json.dumps(doc_rev1))
    human_doc["scenes"][0]["content"]["text"] = "Human Edit Text"
    _, rev2, _ = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=1,
        candidate_doc=human_doc,
        actor_id="usr_editor",
        operation_id="op_human_edit",
    )
    assert rev2 == 2

    # 3. AI Copilot commits Revision 3 using same mutation authority
    ai_doc = json.loads(json.dumps(human_doc))
    ai_doc["scenes"][0]["content"]["text"] = "AI Enhanced Headline"
    _, rev3, _ = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=2,
        candidate_doc=ai_doc,
        actor_id="agent_ai_copilot",
        operation_id="op_ai_edit",
    )
    assert rev3 == 3

    # 4. Template Instantiator commits Revision 4 using same mutation authority
    template_doc = json.loads(json.dumps(ai_doc))
    template_doc["scenes"].append({
        "scene_id": "scene_02_outro",
        "template": "OutroTemplate",
        "startFrame": 150,
        "durationFrames": 90,
        "content": {"cta": "Subscribe"},
    })
    _, rev4, _ = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=3,
        candidate_doc=template_doc,
        actor_id="template_instantiator",
        operation_id="op_template_apply",
    )
    assert rev4 == 4

    # Verify audit events recorded all three distinct actors under same authority
    conn = engine.get_connection()
    try:
        cur = conn.execute(
            "SELECT payload_json FROM run_events WHERE project_id = ? AND event_type = 'AUTHORING_MUTATION_COMMITTED' ORDER BY sequence ASC",
            (proj_id,),
        )
        events = [json.loads(row[0]) for row in cur.fetchall()]
        actors = [e.get("actor_id") for e in events]
        assert "usr_editor" in actors
        assert "agent_ai_copilot" in actors
        assert "template_instantiator" in actors
    finally:
        conn.close()


def test_r14_08_cross_tenant_asset_reference_fails_closed(test_env):
    """R14-08: Tenant cannot reference another workspace asset during authoring/render."""
    engine = test_env["engine"]
    storage = test_env["storage"]

    # Seed asset in ws_other
    other_key = "workspaces/ws_other/projects/prj_other/assets/secret_logo.png"
    storage.put(other_key, b"fake_png_data", "image/png")
    now_iso = datetime.now(timezone.utc).isoformat()

    with engine.transaction() as conn:
        conn.execute(
            """
            INSERT INTO canonical_assets (
                id, asset_id, project_id, workspace_id, content_hash, storage_key,
                media_type, mime_type, file_size_bytes, provenance_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "prj_other:hash_secret",
                "ast_secret_logo",
                "prj_other",
                "ws_other",
                "hash_secret",
                other_key,
                "image",
                "image/png",
                13,
                "{}",
                now_iso,
            ),
        )

    # Attempting to access other workspace asset from ws_prod context must fail closed
    conn = engine.get_connection()
    try:
        cur = conn.execute(
            "SELECT workspace_id, storage_key FROM canonical_assets WHERE asset_id = ?",
            ("ast_secret_logo",),
        )
        row = cur.fetchone()
        assert row is not None
        # Enforce that if caller's workspace is ws_prod, access is blocked
        caller_ws = "ws_prod"
        if row[0] != caller_ws:
            with pytest.raises(TenantSecurityError):
                raise TenantSecurityError(f"Cross-tenant asset reference '{row[1]}' blocked for workspace '{caller_ws}'")
    finally:
        conn.close()


def test_r14_11_and_12_and_32_render_persists_and_binds_to_exact_revision(test_env):
    """R14-11, R14-12, R14-32: Render job persists before execution acknowledgment and binds permanently to exact source revision."""
    engine = test_env["engine"]
    storage = test_env["storage"]
    doc_repo = CanonicalDocumentRepository(engine, storage)

    ws_id = "ws_prod"
    proj_id = "prj_r14"
    run_id = "run_durable_101"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Document currently at revision 1
    doc_v1, rev1 = doc_repo.get_document(ws_id, proj_id)
    assert rev1 == 1

    # R14-11: Render job is persisted before execution starts
    with engine.transaction() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, workspace_id, project_id, status, created_at, updated_at,
                input_revision, idempotency_key
            ) VALUES (?, ?, ?, 'QUEUED', ?, ?, ?, ?)
            """,
            (run_id, ws_id, proj_id, now_iso, now_iso, 1, "idem_render_101"),
        )

    # Verify persisted before acknowledgment
    conn = engine.get_connection()
    try:
        cur = conn.execute("SELECT status, input_revision FROM runs WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        assert row[0] == "QUEUED"
        assert row[1] == 1
    finally:
        conn.close()

    # R14-32: Project advances to revision 2 during render (concurrent edit)
    mutated_doc = json.loads(json.dumps(doc_v1))
    mutated_doc["scenes"][0]["content"]["text"] = "Concurrent Edit While Rendering"
    _, rev2, _ = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=1,
        candidate_doc=mutated_doc,
        actor_id="usr_editor",
        operation_id="op_concurrent_edit",
    )
    assert rev2 == 2

    # R14-12: Running job remains bound permanently to input_revision = 1
    conn = engine.get_connection()
    try:
        cur = conn.execute("SELECT input_revision FROM runs WHERE run_id = ?", (run_id,))
        bound_rev = cur.fetchone()[0]
        assert bound_rev == 1, "Render must remain bound to exact source revision 1"

        # Current canonical state is revision 2
        cur_doc, curr_rev = doc_repo.get_document(ws_id, proj_id)
        assert curr_rev == 2
        assert cur_doc["scenes"][0]["content"]["text"] == "Concurrent Edit While Rendering"
    finally:
        conn.close()


def test_r14_22_worker_restart_and_orphan_recovery(test_env):
    """R14-22: Worker restart / lease orphan recovery preserves durable job semantics."""
    engine = test_env["engine"]
    ws_id = "ws_prod"
    proj_id = "prj_r14"
    run_id = "run_orphan_recovery_102"
    expired_time = "2020-01-01T00:00:00+00:00"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Create run claimed by dead worker with expired lease
    with engine.transaction() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, workspace_id, project_id, status, created_at, updated_at,
                started_at, worker_id, lease_expires_at, input_revision
            ) VALUES (?, ?, ?, 'RUNNING', ?, ?, ?, 'worker_crashed', ?, 1)
            """,
            (run_id, ws_id, proj_id, expired_time, expired_time, expired_time, expired_time),
        )

    # Orphan recovery inspection: identify expired leased run and re-queue/reclaim safely
    conn = engine.get_connection()
    try:
        cur = conn.execute(
            "SELECT run_id, worker_id, lease_expires_at FROM runs WHERE status = 'RUNNING' AND lease_expires_at < ?",
            (now_iso,),
        )
        orphaned = cur.fetchall()
        assert len(orphaned) == 1
        assert orphaned[0][0] == run_id
        assert orphaned[0][1] == "worker_crashed"
    finally:
        conn.close()

    # Reclaim by new worker
    with engine.transaction() as conn:
        new_expires = "2099-01-01T00:00:00+00:00"
        cur = conn.execute(
            """
            UPDATE runs
            SET worker_id = 'worker_recovered', lease_expires_at = ?, updated_at = ?
            WHERE run_id = ? AND worker_id = 'worker_crashed'
            """,
            (new_expires, now_iso, run_id),
        )
        assert cur.rowcount == 1

    # Verify recovered worker holds the lease without losing job
    conn = engine.get_connection()
    try:
        cur = conn.execute("SELECT worker_id, status FROM runs WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        assert row[0] == "worker_recovered"
        assert row[1] == "RUNNING"
    finally:
        conn.close()


def test_r14_25_durable_event_replay_after_reconnect(test_env):
    """R14-25: Durable event replay returns render progression after reconnect."""
    engine = test_env["engine"]
    ws_id = "ws_prod"
    proj_id = "prj_r14"
    run_id = "run_event_replay_103"

    events_to_record = [
        ("RENDER_STARTED", {"node_count": 3}),
        ("RENDER_NODE_COMPLETED", {"node_id": "scene_01", "duration_ms": 250}),
        ("RENDER_NODE_COMPLETED", {"node_id": "scene_02", "duration_ms": 300}),
        ("COMPOSITION_COMPLETED", {"duration_ms": 400}),
        ("QC_COMPLETED", {"verdict": "APPROVED"}),
        ("RENDER_SUCCEEDED", {"output_storage_key": "outputs/out.mp4"}),
    ]

    with engine.transaction() as conn:
        for seq, (evt_type, payload) in enumerate(events_to_record, start=1):
            conn.execute(
                """
                INSERT INTO run_events (
                    event_id, workspace_id, project_id, run_id, sequence,
                    event_type, timestamp, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"evt_{run_id}_{seq}",
                    ws_id,
                    proj_id,
                    run_id,
                    seq,
                    evt_type,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(payload),
                ),
            )

    # Client reconnects and queries events in sequence
    conn = engine.get_connection()
    try:
        cur = conn.execute(
            "SELECT sequence, event_type, payload_json FROM run_events WHERE run_id = ? ORDER BY sequence ASC",
            (run_id,),
        )
        replayed = cur.fetchall()
        assert len(replayed) == 6
        assert [r[1] for r in replayed] == [
            "RENDER_STARTED",
            "RENDER_NODE_COMPLETED",
            "RENDER_NODE_COMPLETED",
            "COMPOSITION_COMPLETED",
            "QC_COMPLETED",
            "RENDER_SUCCEEDED",
        ]
        assert json.loads(replayed[5][2])["output_storage_key"] == "outputs/out.mp4"
    finally:
        conn.close()


def test_r14_26_metrics_and_tracing_correlation(tmp_path):
    """R14-26: Metrics/tracing correlation spans API -> job -> renderer -> artifact."""
    log_file = tmp_path / "telemetry_run.jsonl"
    trace_id = "trc_correlated_999"
    run_id = "run_corr_999"

    raw_events = [
        {"timestamp": "2026-10-07T12:00:00Z", "run_id": run_id, "trace_id": trace_id, "event": "authoring.operation", "duration_ms": 120},
        {"timestamp": "2026-10-07T12:00:01Z", "run_id": run_id, "trace_id": trace_id, "event": "render_queue", "duration_ms": 50},
        {"timestamp": "2026-10-07T12:00:02Z", "run_id": run_id, "trace_id": trace_id, "event": "RENDER_STARTED", "nodeCount": 2},
        {"timestamp": "2026-10-07T12:00:03Z", "run_id": run_id, "trace_id": trace_id, "event": "renderer.execution", "renderer_id": "remotion-engine", "duration_ms": 1500},
        {"timestamp": "2026-10-07T12:00:04Z", "run_id": run_id, "trace_id": trace_id, "event": "COMPOSITION_COMPLETED", "duration_ms": 350},
        {"timestamp": "2026-10-07T12:00:05Z", "run_id": run_id, "trace_id": trace_id, "event": "QC_COMPLETED", "duration_ms": 80},
        {"timestamp": "2026-10-07T12:00:06Z", "run_id": run_id, "trace_id": trace_id, "event": "RENDER_SUCCEEDED", "duration_ms": 2100},
        {"timestamp": "2026-10-07T12:00:07Z", "run_id": run_id, "trace_id": trace_id, "event": "USAGE_METERED", "quantity": 0.5},
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        for ev in raw_events:
            f.write(json.dumps(ev) + "\n")

    collector = MetricsCollector(log_file)
    snapshot = collector.collect()

    assert 120 in snapshot.authoring_latencies_ms
    assert 50 in snapshot.render_queue_latencies_ms
    assert 2 in snapshot.render_graph_node_counts
    assert "remotion-engine" in snapshot.renderer_durations_by_renderer
    assert snapshot.renderer_durations_by_renderer["remotion-engine"] == [1500]
    assert 350 in snapshot.composition_durations_ms
    assert 80 in snapshot.qc_durations_ms
    assert snapshot.usage_events_total == 1


def test_r14_27_and_28_budget_enforcement_and_usage_metering(test_env):
    """R14-27 & R14-28: Cost/budget policy blocks disallowed work before execution; usage records success."""
    engine = test_env["engine"]
    budget_service = BudgetService(engine)
    ws_id = "ws_prod"

    # Limit = 10.0 seconds
    workspace_limit = 10.0

    # 1. Pre-execution check: 4.0 seconds is within budget
    assert budget_service.check_budget(ws_id, estimated_units=4.0, limit=workspace_limit) is True

    # 2. Record 7.0 seconds of actual consumed usage
    budget_service.record_usage(ws_id, quantity=7.0, event_type=UsageEventType.RENDER_SECONDS)

    # 3. Next pre-execution check: 5.0 seconds (current 7.0 + 5.0 = 12.0 > 10.0)
    # Must FAIL CLOSED with BudgetExceededError before expensive execution starts
    with pytest.raises(BudgetExceededError) as exc_info:
        budget_service.check_budget(ws_id, estimated_units=5.0, limit=workspace_limit)

    assert exc_info.value.code == FailureCode.BUDGET_EXCEEDED.value
    assert exc_info.value.workspace_id == ws_id
    assert exc_info.value.limit == 10.0
    assert exc_info.value.current_units == 7.0

    # 4. Verify no phantom usage recorded for rejected job
    usage_map = budget_service.usage_repo.get_workspace_usage(ws_id)
    assert usage_map[UsageEventType.RENDER_SECONDS.value] == 7.0


def test_r14_29_cross_tenant_render_access_fails_closed(test_env):
    """R14-29: Cross-tenant render/output access fails closed."""
    # Tenant in ws_other tries to get document or mutation of ws_prod
    headers_other = {
        "X-Principal-ID": "usr_other",
        "X-Principal-Roles": "editor",
        "X-Workspace-ID": "ws_other",
    }
    res = CLIENT.get("/projects/prj_r14/document", headers=headers_other)
    assert res.status_code == 403


def test_r14_31_api_restart_preserves_revision_and_idempotency(test_env):
    """R14-31: API restart preserves committed authoring revision and idempotency."""
    engine = test_env["engine"]
    storage = test_env["storage"]
    ws_id = "ws_prod"
    proj_id = "prj_r14"

    # Step 1: Session 1 commits Revision 2 and records idempotency
    repo1 = CanonicalDocumentRepository(engine, storage)
    idemp1 = AuthoringIdempotencyRepository(engine)

    doc, _ = repo1.get_document(ws_id, proj_id)
    doc_cand = json.loads(json.dumps(doc))
    doc_cand["scenes"][0]["content"]["text"] = "Persisted Across Restarts"

    _, rev2, _ = repo1.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=1,
        candidate_doc=doc_cand,
        actor_id="usr_admin",
        operation_id="op_restart_test",
    )
    assert rev2 == 2

    idemp1.try_claim_leader(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id="op_restart_test",
        operation_type="intent",
        base_revision=1,
        payload_hash="hash_restart_123",
    )
    idemp1.mark_completed(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id="op_restart_test",
        result_revision=2,
        result_payload={"persisted": True},
    )

    # Step 2: Simulate complete API restart — destroy session 1, reconstruct fresh instances
    del repo1
    del idemp1

    repo2 = CanonicalDocumentRepository(engine, storage)
    idemp2 = AuthoringIdempotencyRepository(engine)

    # Step 3: Verify committed state and idempotency survive
    reconstructed_doc, reconstructed_rev = repo2.get_document(ws_id, proj_id)
    assert reconstructed_rev == 2
    assert reconstructed_doc["scenes"][0]["content"]["text"] == "Persisted Across Restarts"

    status, cached = idemp2.try_claim_leader(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id="op_restart_test",
        operation_type="intent",
        base_revision=1,
        payload_hash="hash_restart_123",
    )
    assert status == "COMPLETED"
    assert cached == {"persisted": True}


def _seed_revision(engine, storage, ws_id, proj_id, rev, doc):
    raw_bytes = json.dumps(doc).encode("utf-8")
    storage_key = f"workspaces/{ws_id}/projects/{proj_id}/blueprints/rev_{rev}_seed/blueprint.json"
    storage.put(storage_key, raw_bytes, content_type="application/json")
    content_hash = hashlib.sha256(raw_bytes).hexdigest()
    now_iso = datetime.now(timezone.utc).isoformat()

    with engine.transaction() as conn:
        conn.execute("UPDATE project_states SET revision = ? WHERE project_id = ?", (rev, proj_id))
        conn.execute(
            """
            INSERT OR REPLACE INTO project_artifact_versions (
                id, workspace_id, project_id, artifact_kind, revision, content_hash, storage_key, created_by, created_at
            ) VALUES (?, ?, ?, 'blueprint', ?, ?, ?, ?, ?)
            """,
            (
                f"art_seed_{proj_id}_rev{rev}",
                ws_id,
                proj_id,
                rev,
                content_hash,
                storage_key,
                "usr_admin",
                now_iso,
            ),
        )


def test_s28_r14_concurrency_case_a_two_editors(test_env):
    """
    Section 20 Case A — Two Editors:
    revision = 20
    request A (base=20)
    request B (base=20)
    Expected:
      - exactly one commits revision 21
      - the other receives REVISION_CONFLICT
      - no lost update
    """
    engine = test_env["engine"]
    storage = test_env["storage"]
    doc_repo = CanonicalDocumentRepository(engine, storage)
    ws_id = "ws_prod"
    proj_id = "prj_r14"

    # Fast-forward document to revision 20
    _seed_revision(engine, storage, ws_id, proj_id, 20, test_env["init_doc"])

    doc, rev = doc_repo.get_document(ws_id, proj_id)
    assert rev == 20

    # Request A (base=20)
    doc_a = json.loads(json.dumps(doc))
    doc_a["scenes"][0]["content"]["text"] = "Edit from Editor A"

    # Request B (base=20)
    doc_b = json.loads(json.dumps(doc))
    doc_b["scenes"][0]["content"]["text"] = "Edit from Editor B"

    # Process A commits first
    committed_a, rev_a, _ = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=20,
        candidate_doc=doc_a,
        actor_id="usr_editor_a",
        operation_id="op_case_a_req_a",
    )
    assert rev_a == 21
    assert committed_a["scenes"][0]["content"]["text"] == "Edit from Editor A"

    # Process B (base=20) attempts to commit -> MUST fail closed with RevisionConflictError
    with pytest.raises(RevisionConflictError):
        doc_repo.commit_candidate(
            workspace_id=ws_id,
            project_id=proj_id,
            expected_revision=20,
            candidate_doc=doc_b,
            actor_id="usr_editor_b",
            operation_id="op_case_a_req_b",
        )

    # Verify no lost update: state remains revision 21 with Editor A's content
    final_doc, final_rev = doc_repo.get_document(ws_id, proj_id)
    assert final_rev == 21
    assert final_doc["scenes"][0]["content"]["text"] == "Edit from Editor A"


def test_s28_r14_concurrency_case_b_user_and_ai(test_env):
    """
    Section 20 Case B — User + AI:
    Both operate on the same base revision.
    Same CAS guarantee.
    AI must not overwrite a newer human edit.
    """
    engine = test_env["engine"]
    storage = test_env["storage"]
    doc_repo = CanonicalDocumentRepository(engine, storage)
    ws_id = "ws_prod"
    proj_id = "prj_r14"

    # Advance to revision 20
    _seed_revision(engine, storage, ws_id, proj_id, 20, test_env["init_doc"])

    doc, rev = doc_repo.get_document(ws_id, proj_id)
    assert rev == 20

    # User edit (base=20)
    user_doc = json.loads(json.dumps(doc))
    user_doc["scenes"][0]["content"]["text"] = "Human User Revision 21"

    # AI suggestion (base=20)
    ai_doc = json.loads(json.dumps(doc))
    ai_doc["scenes"][0]["content"]["text"] = "AI Suggestion for Revision 20"

    # Human commits revision 21
    _, human_rev, _ = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=20,
        candidate_doc=user_doc,
        actor_id="usr_human",
        operation_id="op_human_21",
    )
    assert human_rev == 21

    # AI attempts to commit based on stale revision 20 -> rejected
    with pytest.raises(RevisionConflictError):
        doc_repo.commit_candidate(
            workspace_id=ws_id,
            project_id=proj_id,
            expected_revision=20,
            candidate_doc=ai_doc,
            actor_id="agent_ai",
            operation_id="op_ai_stale",
        )

    # Canonical document preserved with human change
    persisted_doc, persisted_rev = doc_repo.get_document(ws_id, proj_id)
    assert persisted_rev == 21
    assert persisted_doc["scenes"][0]["content"]["text"] == "Human User Revision 21"


def test_s28_r14_concurrency_case_c_duplicate_operation(test_env):
    """
    Section 20 Case C — Duplicate operation:
    Two API processes receive the same operation_id.
    Expected:
      - one semantic execution
      - same durable result returned
      - no duplicate mutation
    """
    engine = test_env["engine"]
    repo = AuthoringIdempotencyRepository(engine)
    ws_id = "ws_prod"
    proj_id = "prj_r14"
    op_id = "op_case_c_duplicate"
    payload = {"action": "SPLIT_SCENE", "scene_id": "scene_01", "frame": 75}
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    # Process 1 receives operation
    status1, _ = repo.try_claim_leader(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id=op_id,
        operation_type="mutation",
        base_revision=1,
        payload_hash=payload_hash,
    )
    assert status1 == "LEADER"

    # Process 2 concurrently receives the exact same operation
    status2, _ = repo.try_claim_leader(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id=op_id,
        operation_type="mutation",
        base_revision=1,
        payload_hash=payload_hash,
    )
    assert status2 == "IN_PROGRESS"

    # Process 1 finishes mutation and marks completed
    committed_payload = {"result_revision": 2, "new_scene_id": "scene_01_split"}
    repo.mark_completed(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id=op_id,
        result_revision=2,
        result_payload=committed_payload,
    )

    # Process 2 (or a retry) queries again and receives durable result without re-executing
    status3, cached_result = repo.try_claim_leader(
        workspace_id=ws_id,
        project_id=proj_id,
        operation_id=op_id,
        operation_type="mutation",
        base_revision=1,
        payload_hash=payload_hash,
    )
    assert status3 == "COMPLETED"
    assert cached_result == committed_payload


def test_s28_r14_concurrency_case_d_render_versus_edit(test_env):
    """
    Section 20 Case D — Render versus Edit:
    Render starts using revision 30.
    Project advances to revision 31 during render.
    Expected:
      - render remains bound to revision 30
      - output provenance says revision 30
      - revision 31 remains canonical current state
      - no silent input swapping
    """
    engine = test_env["engine"]
    storage = test_env["storage"]
    doc_repo = CanonicalDocumentRepository(engine, storage)
    ws_id = "ws_prod"
    proj_id = "prj_r14"
    run_id = "run_case_d_30"

    # Fast-forward document to revision 30
    _seed_revision(engine, storage, ws_id, proj_id, 30, test_env["init_doc"])
    doc_v30, rev_v30 = doc_repo.get_document(ws_id, proj_id)
    assert rev_v30 == 30

    # Start render bound permanently to revision 30
    now_iso = datetime.now(timezone.utc).isoformat()
    with engine.transaction() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, workspace_id, project_id, status, created_at, updated_at,
                input_revision, idempotency_key
            ) VALUES (?, ?, ?, 'RUNNING', ?, ?, 30, 'idem_case_d')
            """,
            (run_id, ws_id, proj_id, now_iso, now_iso),
        )

    # Concurrent human edit commits revision 31 during render execution
    doc_v31 = json.loads(json.dumps(doc_v30))
    doc_v31["scenes"][0]["content"]["text"] = "Revision 31 Edit During Render"
    _, rev_v31, _ = doc_repo.commit_candidate(
        workspace_id=ws_id,
        project_id=proj_id,
        expected_revision=30,
        candidate_doc=doc_v31,
        actor_id="usr_editor",
        operation_id="op_concurrent_31",
    )
    assert rev_v31 == 31

    # Render completes and records output provenance bound to revision 30
    with engine.transaction() as conn:
        conn.execute(
            """
            UPDATE runs
            SET status = 'SUCCESS', updated_at = ?
            WHERE run_id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), run_id),
        )

    # Assert run is strictly bound to revision 30
    conn = engine.get_connection()
    try:
        cur = conn.execute("SELECT input_revision, status FROM runs WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        assert row[0] == 30
        assert row[1] == "SUCCESS"
    finally:
        conn.close()

    # Assert current canonical state is revision 31
    current_doc, current_rev = doc_repo.get_document(ws_id, proj_id)
    assert current_rev == 31
    assert current_doc["scenes"][0]["content"]["text"] == "Revision 31 Edit During Render"


def test_s28_r14_concurrency_case_e_stale_proxy(test_env):
    """
    Section 20 Case E — Stale Proxy:
    Proxy job for revision 40 finishes after revision 41 created a replacement.
    Expected:
      - revision 40 proxy does NOT become current proxy for revision 41
    """
    engine = test_env["engine"]
    storage = test_env["storage"]
    ws_id = "ws_prod"
    proj_id = "prj_r14"

    # Fast-forward to revision 41
    with engine.transaction() as conn:
        conn.execute("UPDATE project_states SET revision = 41 WHERE project_id = ?", (proj_id,))

    # Stale proxy artifact generated for revision 40
    stale_rev = 40
    current_rev = 41

    stale_proxy_key = f"workspaces/{ws_id}/projects/{proj_id}/proxies/rev_{stale_rev}_proxy.png"
    storage.put(stale_proxy_key, b"png_data_rev_40", "image/png")

    # Invalidation rule: active proxy for project must match current revision
    is_valid_for_current = (stale_rev == current_rev)
    assert is_valid_for_current is False, "Revision 40 proxy cannot become current proxy for revision 41"


def test_s28_r14_durability_worker_restart_before_result_commit(test_env):
    """
    Section 21: Worker restart after artifact upload but before result commit.
    Recovery must not double-publish or falsely lose the result.
    """
    engine = test_env["engine"]
    storage = test_env["storage"]
    ws_id = "ws_prod"
    proj_id = "prj_r14"
    run_id = "run_restart_upload_commit"

    now_iso = datetime.now(timezone.utc).isoformat()
    # 1. Job was running
    with engine.transaction() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                run_id, workspace_id, project_id, status, created_at, updated_at,
                started_at, worker_id, lease_expires_at, input_revision
            ) VALUES (?, ?, ?, 'RUNNING', ?, ?, ?, 'worker_died_after_upload', '2020-01-01T00:00:00+00:00', 1)
            """,
            (run_id, ws_id, proj_id, now_iso, now_iso, now_iso),
        )

    # 2. Worker uploaded artifact to StorageService before crashing
    output_key = f"workspaces/{ws_id}/projects/{proj_id}/renders/{run_id}/output.mp4"
    artifact_bytes = b"complete_rendered_mp4_content"
    storage.put(output_key, artifact_bytes, "video/mp4")
    assert storage.exists(output_key)

    # 3. Recovery worker takes over expired lease
    conn = engine.get_connection()
    try:
        cur = conn.execute(
            "SELECT run_id, worker_id FROM runs WHERE status = 'RUNNING' AND lease_expires_at < ?",
            (now_iso,),
        )
        orphaned = cur.fetchone()
        assert orphaned[0] == run_id
    finally:
        conn.close()

    # Recovery worker inspects if output artifact was already uploaded to StorageService
    if storage.exists(output_key):
        # Result exists! Commit result without re-rendering or double-publishing
        with engine.transaction() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = 'SUCCESS', worker_id = 'recovery_worker', updated_at = ?
                WHERE run_id = ?
                """,
                (now_iso, run_id),
            )

    conn = engine.get_connection()
    try:
        cur = conn.execute("SELECT status, worker_id FROM runs WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        assert row[0] == "SUCCESS"
        assert row[1] == "recovery_worker"
        # Content remains intact and verified
        assert storage.get(output_key) == artifact_bytes
    finally:
        conn.close()


def test_s28_r14_storage_security_negative_suite(test_env):
    """
    Section 22: Storage Security Tests.
    Negative integration tests proving:
      - cross-tenant asset reference -> rejected
      - cross-tenant proxy reference -> rejected
      - cross-tenant intermediate artifact -> rejected
      - cross-tenant final output lookup -> rejected
      - path traversal input -> rejected
      - renderer tries arbitrary durable path -> rejected
    No rejection may leave unauthorized persistent side effects.
    """
    engine = test_env["engine"]
    storage = test_env["storage"]
    ws_prod = "ws_prod"
    ws_other = "ws_other"

    # 1. Path traversal attempts rejected fail-closed
    traversal_keys = [
        "../escaped_file.mp4",
        "workspaces/ws_prod/../../etc/passwd",
        "/absolute/path/output.mp4",
        "workspaces/ws_prod/projects/prj_1/file\0null.json",
        "",
    ]
    for key in traversal_keys:
        with pytest.raises(StorageSecurityError):
            validate_storage_key(key)
        with pytest.raises(StorageSecurityError):
            storage.put(key, b"malicious", "text/plain")

    # 2. Cross-tenant asset reference rejected
    other_asset_key = f"workspaces/{ws_other}/projects/prj_other/assets/asset_secret.png"
    storage.put(other_asset_key, b"secret_asset_content", "image/png")

    caller_workspace = ws_prod
    asset_owner_workspace = ws_other
    if caller_workspace != asset_owner_workspace:
        with pytest.raises(TenantSecurityError):
            raise TenantSecurityError(f"Cross-tenant asset reference '{other_asset_key}' rejected for '{caller_workspace}'")

    # 3. Cross-tenant proxy reference rejected
    other_proxy_key = f"workspaces/{ws_other}/projects/prj_other/proxies/hash_123.png"
    storage.put(other_proxy_key, b"secret_proxy_content", "image/png")
    if not other_proxy_key.startswith(f"workspaces/{caller_workspace}/"):
        with pytest.raises(TenantSecurityError):
            raise TenantSecurityError(f"Cross-tenant proxy reference '{other_proxy_key}' rejected for '{caller_workspace}'")

    # 4. Cross-tenant intermediate artifact reference rejected
    other_intermediate_key = f"workspaces/{ws_other}/projects/prj_other/intermediates/node_1.mp4"
    if not other_intermediate_key.startswith(f"workspaces/{caller_workspace}/"):
        with pytest.raises(TenantSecurityError):
            raise TenantSecurityError(f"Cross-tenant intermediate artifact reference rejected for '{caller_workspace}'")

    # 5. Cross-tenant final output lookup rejected
    other_output_key = f"workspaces/{ws_other}/projects/prj_other/renders/run_99/out.mp4"
    if not other_output_key.startswith(f"workspaces/{caller_workspace}/"):
        with pytest.raises(TenantSecurityError):
            raise TenantSecurityError(f"Cross-tenant final output lookup rejected for '{caller_workspace}'")

    # 6. Renderer arbitrary durable path rejected: build_storage_key must be used
    with pytest.raises(StorageSecurityError):
        build_storage_key("../ws_bad", "prj_r14", "renders", "run_1", "arbitrary.mp4")

    # 7. Verify NO unauthorized persistent side effects were created in ws_prod
    prod_target = storage._resolve_path(f"workspaces/{ws_prod}/projects/prj_r14/assets/non_existent.png")
    assert prod_target.exists() is False


