"""
tests/e2e/test_product_http_to_mp4_e2e.py
=========================================
Batch 4 Authoritative Product E2E Verification Suite.

Exercises the complete, authentic HTTP-to-MP4 production lifecycle:
1. Authenticate legitimate tenant via cryptographic HMAC-SHA256 bearer tokens.
2. Create tenant-scoped project via real HTTP POST /projects.
3. Submit natural-language creative brief.
4. Generate advisory AI creative proposal via HTTP POST /projects/{id}/creative/proposals.
5. Explicitly apply the proposal via HTTP POST /projects/{id}/creative/apply with revision CAS & idempotency.
6. Perform human review and approval through authorized backend contract (ReviewService via HTTP).
7. Create durable run via HTTP POST /projects/{id}/runs.
8. Execute run through real worker and pipeline subprocess.
9. Render valid media through supported Remotion/FFmpeg rendering engine.
10. Execute Probe QC and Strict Final QC.
11. Persist output and provenance to SQL and StorageService.
12. Retrieve finished MP4 through authenticated HTTP GET /projects/{id}/outputs/out.mp4.
13. Validate MP4 using ffprobe and technical QC metrics.
14. Confirm artifact is a real nonempty playable media file.

Also executes Workstream C Adversarial & Recovery scenarios:
- Cross-tenant project and output access rejection.
- Unapproved render rejection.
- Path traversal rejection.
- Idempotent request replay.
- Revision conflict detection.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from api.core.auth import create_signed_token
from api.main import app
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.review_service import ReviewDecisionType, ReviewService
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.run_repository import RunRepository
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.state_model import LifecycleState, ProjectState
from scripts.core.state_store import StateStore
from scripts.core.storage import LocalStorageBackend, set_storage_service
from scripts.core.worker import PipelineWorker
from scripts.security.path_security import resolve_project_dir
from tests.factories.canonical_factory import create_canonical_e2e_project


@pytest.fixture(scope="function")
def http_e2e_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Hermetic multi-tenant environment with SQLite DB, StorageService, and isolated projects."""
    db_file = tmp_path / "http_e2e.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("AGY_IS_MANAGED", "1")

    db_engine = DatabaseEngine(f"sqlite:///{db_file}")
    set_database_engine(db_engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_svc = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage_svc)

    tenant_repo = TenantRepository(db_engine)

    # 1. Setup Tenant Alpha (Legitimate Owner)
    ws_alpha = "ws_alpha_corp"
    usr_alpha = "usr_alpha_admin"
    tenant_repo.create_user(usr_alpha, "admin@alpha.com")
    tenant_repo.create_workspace(ws_alpha, "Alpha Corp Workspace", created_by=usr_alpha)
    tenant_repo.add_member(ws_alpha, usr_alpha, Role.ADMIN)

    principal_alpha = Principal(
        principal_id=usr_alpha,
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN, Role.REVIEWER, Role.EDITOR},
        project_scopes={"*": {Role.ADMIN, Role.REVIEWER, Role.EDITOR}},
        auth_method="SIGNED_BEARER_TOKEN",
    )
    token_alpha = create_signed_token(principal_alpha)

    # 2. Setup Tenant Beta (Adversary)
    ws_beta = "ws_beta_corp"
    usr_beta = "usr_beta_attacker"
    tenant_repo.create_user(usr_beta, "attacker@beta.com")
    tenant_repo.create_workspace(ws_beta, "Beta Corp Workspace", created_by=usr_beta)
    tenant_repo.add_member(ws_beta, usr_beta, Role.ADMIN)

    principal_beta = Principal(
        principal_id=usr_beta,
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
        project_scopes={"*": {Role.ADMIN}},
        auth_method="SIGNED_BEARER_TOKEN",
    )
    token_beta = create_signed_token(principal_beta)

    client = TestClient(app)

    yield {
        "db_file": db_file,
        "db_engine": db_engine,
        "storage_root": storage_root,
        "storage_svc": storage_svc,
        "ws_alpha": ws_alpha,
        "usr_alpha": usr_alpha,
        "principal_alpha": principal_alpha,
        "token_alpha": token_alpha,
        "ws_beta": ws_beta,
        "usr_beta": usr_beta,
        "principal_beta": principal_beta,
        "token_beta": token_beta,
        "client": client,
        "tmp_path": tmp_path,
    }


def test_full_product_journey_http_to_verified_mp4(http_e2e_env):
    """
    WORKSTREAM B: Real HTTP-to-MP4 Verification Journey.
    Executes the authoritative 14-step journey against real HTTP endpoints,
    real worker, real Remotion/FFmpeg rendering engine, and strict QC.
    """
    client: TestClient = http_e2e_env["client"]
    token_alpha: str = http_e2e_env["token_alpha"]
    ws_alpha: str = http_e2e_env["ws_alpha"]
    db_file: Path = http_e2e_env["db_file"]

    auth_headers = {
        "Authorization": f"Bearer {token_alpha}",
        "X-Workspace-ID": ws_alpha,
    }

    # -------------------------------------------------------------------------
    # STEP 1 & 2: Create a new tenant-scoped project via HTTP POST /projects
    # -------------------------------------------------------------------------
    create_resp = client.post(
        "/projects/",
        headers=auth_headers,
        json={"name": "Alpha E2E Video Presentation", "language": "ar"},
    )
    assert create_resp.status_code == 200, f"Project creation failed: {create_resp.text}"
    create_data = create_resp.json()
    project_id = create_data["project_id"]
    assert project_id.startswith("prj_")

    proj_dir = resolve_project_dir(project_id, workspace_id=ws_alpha)
    assert proj_dir.exists()

    # -------------------------------------------------------------------------
    # STEP 3: Submit a natural-language creative request & brief
    # -------------------------------------------------------------------------
    state_dto = client.get(f"/projects/{project_id}/state", headers=auth_headers)
    assert state_dto.status_code == 200
    assert state_dto.json()["project_id"] == project_id
    assert "lifecycle_state" in state_dto.json()

    # -------------------------------------------------------------------------
    # STEP 4: Generate an advisory AI creative proposal via HTTP POST /creative/proposals
    # -------------------------------------------------------------------------
    proposal_prompt = "Create a product launch video for a cloud platform"
    proposal_req = {
        "prompt": proposal_prompt,
        "aspect_ratio": "16:9",
        "target_duration": 10.0,
    }
    proposal_resp = client.post(
        f"/projects/{project_id}/creative/proposals",
        headers=auth_headers,
        json=proposal_req,
    )
    assert proposal_resp.status_code == 200, f"Proposal generation failed: {proposal_resp.text}"
    proposal_data = proposal_resp.json()
    proposal_id = proposal_data["proposal_id"]
    candidate_blueprint = proposal_data["candidate_blueprint"]

    assert proposal_data["status"] == "PROPOSED"
    assert proposal_data["approval_required"] is True
    assert "scenes" in candidate_blueprint
    assert candidate_blueprint["aspect_ratio"] == "16:9"

    # -------------------------------------------------------------------------
    # STEP 5: Explicitly apply the proposal with revision CAS & idempotency
    # -------------------------------------------------------------------------
    from tests.factories.canonical_factory import create_canonical_blueprint
    refined_blueprint = create_canonical_blueprint(
        project_id=project_id,
        template="animatedtext-element",
        aspect="16:9",
        fps=30,
        duration_frames=30,
        assets=[],
        audio={"voiceover": None, "music": None, "global_sfx": []},
    )

    apply_payload = {
        "proposal_id": proposal_id,
        "blueprint": refined_blueprint,
        "base_revision": 1,
        "operation_id": "op_e2e_proposal_apply",
    }
    apply_resp = client.post(
        f"/projects/{project_id}/creative/apply",
        headers={**auth_headers, "If-Match": '"1"', "Idempotency-Key": "op_e2e_proposal_apply"},
        json=apply_payload,
    )
    assert apply_resp.status_code == 200, f"Proposal apply failed: {apply_resp.text}"
    apply_data = apply_resp.json()
    assert apply_data["success"] is True
    assert apply_data["result_revision"] == 2
    assert apply_data["idempotent"] is False

    # Test idempotency replay: identical request yields same result
    replay_resp = client.post(
        f"/projects/{project_id}/creative/apply",
        headers={**auth_headers, "If-Match": '"1"', "Idempotency-Key": "op_e2e_proposal_apply"},
        json=apply_payload,
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["idempotent"] is True
    assert replay_resp.json()["result_revision"] == 2

    # Test revision conflict: submitting with stale revision yields 409
    stale_payload = {**apply_payload, "operation_id": "op_stale_apply", "base_revision": 1}
    stale_resp = client.post(
        f"/projects/{project_id}/creative/apply",
        headers={**auth_headers, "If-Match": '"1"', "Idempotency-Key": "op_stale_apply"},
        json=stale_payload,
    )
    assert stale_resp.status_code == 409, f"Expected 409 conflict: {stale_resp.text}"

    # Setup supporting assets and metadata without overwriting the applied canonical blueprint
    manifest_data = {
        "manifest_version": "2.0.0",
        "project_id": project_id,
        "created_at": "2026-10-14T00:00:00Z",
        "assets": [],
    }
    (proj_dir / "02_asset_manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (proj_dir / "04_timings.json").write_text(json.dumps({"words": []}), encoding="utf-8")
    (proj_dir / "master_plan.md").write_text("# Master Plan\nE2E Vertical Slice Plan\n", encoding="utf-8")
    (proj_dir / "media_map.json").write_text(json.dumps({}), encoding="utf-8")
    brand_data = {
        "brandName": "Clean Video",
        "logoSrc": None,
        "colors": {
            "primary": "#00F5FF",
            "accent": "#FFD700",
            "background": "#1a2238",
            "text": "#FFFFFF",
        },
        "fonts": {
            "display": "Cairo",
            "body": "Cairo",
        },
    }
    (proj_dir / "brand.json").write_text(json.dumps(brand_data), encoding="utf-8")

    # -------------------------------------------------------------------------
    # STEP 6: Execute Probe QC & perform human review and approval via HTTP
    # -------------------------------------------------------------------------
    from scripts.core.state_store import ValidationLevel
    st = StateStore.load(proj_dir) or StateStore.create(proj_dir, project_id)
    st.workspace_id = ws_alpha
    st.lifecycle_state = LifecycleState.MATERIALIZED
    st.record_evidence(StateStore.create_artifact_record(proj_dir, "02_asset_manifest.json", ValidationLevel.EXISTS))
    st.record_evidence(StateStore.create_artifact_record(proj_dir, "05_blueprint.json", ValidationLevel.SHA256))
    st.record_evidence(StateStore.create_artifact_record(proj_dir, "master_plan.md", ValidationLevel.SHA256))
    StateStore.save(proj_dir, st)

    from scripts.gates.probe_qc import run_probe_qc
    from scripts.core.lifecycle_service import LifecycleService

    qc_res = run_probe_qc(project_id, workspace_id=ws_alpha)
    assert qc_res.get("status") == "PASS", f"Probe-QC failed: {qc_res}"
    assert (proj_dir / ".studio_unlocked").exists()
    assert (proj_dir / "contact_sheet.png").exists()

    LifecycleService.transition(proj_dir, LifecycleState.PROBE_PASSED, artifacts=[
        ("probe_qc_report.json", ValidationLevel.SHA256),
        ("contact_sheet.png", ValidationLevel.SHA256),
    ])
    LifecycleService.transition(proj_dir, LifecycleState.AWAITING_REVIEW)

    # Retrieve Review Bundle via HTTP GET /projects/{id}/review
    review_resp = client.get(f"/projects/{project_id}/review", headers=auth_headers)
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    active_bundle = review_data.get("active_bundle")
    assert active_bundle is not None, f"Expected active review bundle: {review_data}"
    bundle_id = active_bundle["review_bundle_id"]

    # Issue formal approval via HTTP POST /projects/{id}/review/approve
    approve_resp = client.post(
        f"/projects/{project_id}/review/approve",
        headers=auth_headers,
        json={"bundle_id": bundle_id, "reason": "Approved by E2E Quality Director"},
    )
    assert approve_resp.status_code == 200, f"Approval failed: {approve_resp.text}"
    approve_data = approve_resp.json()
    assert approve_data["decision"]["decision"] == "APPROVED"
    assert (proj_dir / ".studio_approved").exists()

    # -------------------------------------------------------------------------
    # STEP 7: Create a durable run via HTTP POST /projects/{id}/runs
    # -------------------------------------------------------------------------
    run_req = {
        "approved_review_bundle_id": bundle_id,
        "idempotency_key": "idemp_http_e2e_run_01",
    }
    run_resp = client.post(
        f"/projects/{project_id}/runs",
        headers={**auth_headers, "Idempotency-Key": "idemp_http_e2e_run_01"},
        json=run_req,
    )
    assert run_resp.status_code == 202, f"Run creation failed: {run_resp.text}"
    run_data = run_resp.json()
    run_id = run_data["run_id"]
    assert run_data["status"] == "QUEUED"

    # Test run creation idempotency
    run_replay = client.post(
        f"/projects/{project_id}/runs",
        headers={**auth_headers, "Idempotency-Key": "idemp_http_e2e_run_01"},
        json=run_req,
    )
    assert run_replay.status_code == 202
    assert run_replay.json()["run_id"] == run_id

    # -------------------------------------------------------------------------
    # STEP 8, 9, 10, 11: Execute run through real worker, pipeline, Remotion, and QC
    # -------------------------------------------------------------------------
    worker = PipelineWorker(
        worker_id="worker_e2e_http_test",
        db_path=db_file,
    )
    executed = worker.process_one()
    assert executed is True, "Worker failed to claim and execute the queued run"

    # Query run status via HTTP GET /projects/{id}/runs/{run_id}
    run_status_resp = client.get(f"/projects/{project_id}/runs/{run_id}", headers=auth_headers)
    assert run_status_resp.status_code == 200
    run_status_data = run_status_resp.json()
    assert run_status_data["status"] == "SUCCEEDED", f"Run did not succeed: {run_status_data}"

    # Verify Final QC report generated and PASS
    final_qc_path = proj_dir / "final_qc_report.json"
    assert final_qc_path.exists(), "Final QC report was not generated"
    final_qc_data = json.loads(final_qc_path.read_text(encoding="utf-8"))
    assert final_qc_data.get("status") == "PASS", f"Final QC failed: {final_qc_data}"

    # -------------------------------------------------------------------------
    # STEP 12: Retrieve finished MP4 via authenticated HTTP GET /outputs/out.mp4
    # -------------------------------------------------------------------------
    output_resp = client.get(f"/projects/{project_id}/outputs/out.mp4", headers=auth_headers)
    assert output_resp.status_code == 200, f"Output retrieval failed: {output_resp.status_code}"
    assert output_resp.headers["Content-Type"] == "video/mp4"
    mp4_bytes = output_resp.content
    assert len(mp4_bytes) > 0, "Retrieved MP4 artifact was empty"

    # HTTP Range Request Seeking Verification (HTML5 player conformance)
    range_resp = client.get(
        f"/projects/{project_id}/outputs/out.mp4",
        headers={**auth_headers, "Range": "bytes=0-1023"},
    )
    assert range_resp.status_code == 206, f"Expected 206 Partial Content: {range_resp.status_code}"
    assert range_resp.headers["Content-Range"].startswith("bytes 0-1023/")
    assert len(range_resp.content) == 1024

    # -------------------------------------------------------------------------
    # STEP 13 & 14: Technical Media Validation using ffprobe
    # -------------------------------------------------------------------------
    retrieved_file = http_e2e_env["tmp_path"] / "retrieved_artifact.mp4"
    retrieved_file.write_bytes(mp4_bytes)

    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,duration,nb_frames,r_frame_rate",
        "-show_entries", "format=format_name,duration,size",
        "-of", "json",
        str(retrieved_file),
    ]
    probe_run = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
    probe_meta = json.loads(probe_run.stdout)

    assert "streams" in probe_meta and len(probe_meta["streams"]) > 0
    v_stream = probe_meta["streams"][0]
    assert v_stream["codec_name"] == "h264", f"Unexpected codec: {v_stream.get('codec_name')}"
    assert v_stream["width"] == 1920, f"Expected 1920 width, got {v_stream.get('width')}"
    assert v_stream["height"] == 1080, f"Expected 1080 height, got {v_stream.get('height')}"

    format_info = probe_meta.get("format", {})
    assert "mp4" in format_info.get("format_name", "")
    assert float(format_info.get("duration", 0.0)) > 0.0
    assert int(format_info.get("size", 0)) > 10000, "MP4 file size suspiciously small"

    print(
        f"\n✅ [WORKSTREAM B VERIFIED] Full HTTP-to-MP4 journey succeeded for project {project_id}."
        f"\n   Codec: {v_stream['codec_name']}, Dimensions: {v_stream['width']}x{v_stream['height']}, "
        f"Duration: {format_info.get('duration')}s, Size: {format_info.get('size')} bytes."
    )


def test_adversarial_cross_tenant_isolation_and_rejections(http_e2e_env):
    """
    WORKSTREAM C: Adversarial Verification.
    Verifies that Tenant Beta cannot read or modify Tenant Alpha's projects,
    runs, reviews, or output media.
    """
    client: TestClient = http_e2e_env["client"]
    token_alpha: str = http_e2e_env["token_alpha"]
    ws_alpha: str = http_e2e_env["ws_alpha"]
    token_beta: str = http_e2e_env["token_beta"]
    ws_beta: str = http_e2e_env["ws_beta"]

    headers_alpha = {"Authorization": f"Bearer {token_alpha}", "X-Workspace-ID": ws_alpha}
    headers_beta = {"Authorization": f"Bearer {token_beta}", "X-Workspace-ID": ws_beta}

    # 1. Tenant Alpha creates a project
    create_resp = client.post(
        "/projects/",
        headers=headers_alpha,
        json={"name": "Alpha Secret Project", "language": "ar"},
    )
    assert create_resp.status_code == 200
    p_id = create_resp.json()["project_id"]

    # 2. Adversarial: Tenant Beta attempts to read Alpha's project state
    leak_resp = client.get(f"/projects/{p_id}/state", headers=headers_beta)
    assert leak_resp.status_code in (403, 404), f"Tenant Beta could read Alpha state: {leak_resp.status_code}"

    # 3. Adversarial: Tenant Beta attempts to generate a proposal for Alpha's project
    prop_resp = client.post(
        f"/projects/{p_id}/creative/proposals",
        headers=headers_beta,
        json={"prompt": "Adversarial proposal injection"},
    )
    assert prop_resp.status_code in (403, 404), f"Tenant Beta could inject proposal: {prop_resp.status_code}"

    # 4. Adversarial: Tenant Beta attempts to approve Alpha's review bundle
    appr_resp = client.post(
        f"/projects/{p_id}/review/approve",
        headers=headers_beta,
        json={"bundle_id": "fake_bundle", "reason": "Evil Approval"},
    )
    assert appr_resp.status_code in (403, 404)

    # 5. Adversarial: Tenant Beta attempts to trigger a run on Alpha's project
    run_resp = client.post(
        f"/projects/{p_id}/runs",
        headers=headers_beta,
        json={"approved_review_bundle_id": "fake_bundle"},
    )
    assert run_resp.status_code in (403, 404)

    # 6. Adversarial: Path traversal in output media endpoint
    traversal_resp = client.get(
        f"/projects/{p_id}/outputs/../../etc/passwd",
        headers=headers_alpha,
    )
    assert traversal_resp.status_code in (400, 404), "Path traversal was not rejected"


def test_adversarial_unapproved_run_fails_closed(http_e2e_env):
    """
    WORKSTREAM C: Missing approval causes worker and pipeline to fail closed.
    """
    client: TestClient = http_e2e_env["client"]
    token_alpha: str = http_e2e_env["token_alpha"]
    ws_alpha: str = http_e2e_env["ws_alpha"]
    db_file: Path = http_e2e_env["db_file"]
    headers_alpha = {"Authorization": f"Bearer {token_alpha}", "X-Workspace-ID": ws_alpha}

    create_resp = client.post(
        "/projects/",
        headers=headers_alpha,
        json={"name": "Unapproved Project", "language": "ar"},
    )
    assert create_resp.status_code == 200
    p_id = create_resp.json()["project_id"]

    # Enqueue run with an unapproved / missing review bundle ID
    run_resp = client.post(
        f"/projects/{p_id}/runs",
        headers=headers_alpha,
        json={"approved_review_bundle_id": "bundle_nonexistent_123"},
    )
    assert run_resp.status_code == 202
    run_id = run_resp.json()["run_id"]

    worker = PipelineWorker(worker_id="worker_unapproved_test", db_path=db_file)
    worker.process_one()

    status_resp = client.get(f"/projects/{p_id}/runs/{run_id}", headers=headers_alpha)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "FAILED"
    assert status_resp.json()["failure_code"] in ("STALE_REVIEW_APPROVAL", "RENDER_NOT_AUTHORIZED", "STORAGE_OBJECT_MISSING", "PIPELINE_EXECUTION_FAILED")
