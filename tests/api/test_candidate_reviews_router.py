"""
tests/api/test_candidate_reviews_router.py
==========================================
API Transport & Authorization Tests for Candidate Reviews Router (S28-07D).

Verifies:
1. Transport Only: Router passes requests to domain service and never mutates status directly.
2. Server-Authoritative Identity: Spoofed reviewer claims in request payload are ignored.
3. Multi-Tenant Isolation & Role Authorization at HTTP boundary.
"""

import hashlib
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from scripts.core.database import DatabaseEngine, set_database_engine, TenantRepository
from scripts.core.storage import LocalStorageBackend, set_storage_service
from scripts.core.template_candidate_repository import SqlTemplateCandidateRepository
from scripts.core.security.principal import Role
from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.plan import CreativeTier
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    CandidateStatus,
    CandidateValidationReport,
    GateStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from creative_governance.candidates.hashing import compute_candidate_content_hash


@pytest.fixture
def api_candidate_env(tmp_path):
    # Setup hermetic DB
    db_file = tmp_path / "candidates_api_test.db"
    db_engine = DatabaseEngine(f"sqlite:///{db_file}")
    set_database_engine(db_engine)

    # Setup storage
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_svc = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage_svc)

    tenant_repo = TenantRepository(db_engine)

    # Create workspace Alpha
    user_alpha_admin = tenant_repo.create_user("usr_alpha_admin", "admin@alpha.com")
    user_alpha_rev = tenant_repo.create_user("usr_alpha_reviewer", "reviewer@alpha.com")
    user_alpha_view = tenant_repo.create_user("usr_alpha_viewer", "viewer@alpha.com")
    ws_alpha = tenant_repo.create_workspace("ws_alpha", "Workspace Alpha", created_by=user_alpha_admin.id)
    tenant_repo.add_member("ws_alpha", user_alpha_admin.id, Role.ADMIN)
    tenant_repo.add_member("ws_alpha", user_alpha_rev.id, Role.REVIEWER)
    tenant_repo.add_member("ws_alpha", user_alpha_view.id, Role.VIEWER)

    # Create workspace Beta
    user_beta_rev = tenant_repo.create_user("usr_beta_reviewer", "reviewer@beta.com")
    ws_beta = tenant_repo.create_workspace("ws_beta", "Workspace Beta", created_by=user_beta_rev.id)
    tenant_repo.add_member("ws_beta", user_beta_rev.id, Role.REVIEWER)

    # Setup a VALIDATED candidate in workspace Alpha
    cand_repo = SqlTemplateCandidateRepository(db_engine)
    source_code = "export const Widget = () => <div>Widget</div>;"
    schema = {"type": "object"}
    deps = ["react"]
    fixtures = {}
    content_hash = compute_candidate_content_hash(
        source_code=source_code,
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        why_reuse_failed="none found",
        why_compose_failed="cannot compose",
        creative_plan_reference="cplan_01",
        creative_tier_decision_reference="tier_01",
    )
    now = "2026-10-02T19:00:00Z"
    cand = TemplateCandidate(
        candidate_id="cand_http_001",
        workspace_id="ws_alpha",
        source_project_id="prj_alpha",
        creator_ai_run_id="run_ai_01",
        creative_plan_reference="cplan_01",
        creative_tier_decision_reference="tier_01",
        why_reuse_failed="none found",
        why_compose_failed="cannot compose",
        source_code=source_code,
        source_code_path="workspaces/ws_alpha/candidates/cand_http_001/source.tsx",
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        content_hash=content_hash,
        revision=1,
        status=CandidateStatus.VALIDATED,
        name="HTTP Test Candidate",
        description="Candidate for HTTP API testing",
        author="usr_creator_external",
        proposed_category="elements/ui",
        proposed_tags=["ui"],
        target_tier=CreativeTier.REUSE,
        required_provenance=ProvenanceRecord(source="plan:cplan_01:decision:tier_01", timestamp=now),
        created_at=now,
        updated_at=now,
    )
    cand_repo.save_candidate(cand)

    # Static report
    static_rep = CandidateValidationReport(
        validation_id="val_s_http",
        candidate_id="cand_http_001",
        workspace_id="ws_alpha",
        candidate_content_hash=content_hash,
        candidate_revision=1,
        phase=ValidationPhase.STATIC,
        policy_version="1.0.0",
        started_at=now,
        completed_at=now,
        gates=[CandidateGateResult(gate_id="contract_gate", status=GateStatus.PASS, summary="ok")],
        overall_result=ValidationOverallResult.PASS,
    )
    cand_repo.save_validation_report(static_rep)

    # Runtime report
    runtime_rep = CandidateValidationReport(
        validation_id="val_r_http",
        candidate_id="cand_http_001",
        workspace_id="ws_alpha",
        candidate_content_hash=content_hash,
        candidate_revision=1,
        phase=ValidationPhase.RUNTIME,
        policy_version="1.0.0",
        started_at=now,
        completed_at=now,
        gates=[CandidateGateResult(gate_id="render_smoke_gate", status=GateStatus.PASS, summary="ok")],
        overall_result=ValidationOverallResult.PASS,
        evidence_refs={"probe_report": "candidates/ws_alpha/cand_http_001/probe.json"},
        static_validation_id=static_rep.validation_id,
        static_validation_report_hash=hashlib.sha256(static_rep.model_dump_json().encode("utf-8")).hexdigest(),
    )
    cand_repo.save_validation_report(runtime_rep)

    client = TestClient(app)

    return {
        "client": client,
        "cand": cand,
        "ws_alpha": ws_alpha,
        "ws_beta": ws_beta,
        "user_admin": user_alpha_admin,
        "user_reviewer": user_alpha_rev,
        "user_viewer": user_alpha_view,
        "user_beta_reviewer": user_beta_rev,
    }


def test_api_open_review_and_authorization(api_candidate_env):
    """Verifies open_review API endpoint and role authorization."""
    client = api_candidate_env["client"]
    cand_id = api_candidate_env["cand"].candidate_id

    # 1. Viewer attempts to open review -> 403 Forbidden
    headers_viewer = {
        "X-Principal-ID": api_candidate_env["user_viewer"].id,
        "X-Principal-Roles": "viewer",
        "X-Workspace-ID": "ws_alpha",
    }
    resp_viewer = client.post(
        f"/candidates/{cand_id}/reviews/open",
        json={"expected_revision": 1},
        headers=headers_viewer,
    )
    assert resp_viewer.status_code == 403

    # 2. Reviewer opens review -> 201 Created
    headers_reviewer = {
        "X-Principal-ID": api_candidate_env["user_reviewer"].id,
        "X-Principal-Roles": "reviewer",
        "X-Workspace-ID": "ws_alpha",
    }
    resp_open = client.post(
        f"/candidates/{cand_id}/reviews/open",
        json={"expected_revision": 1},
        headers=headers_reviewer,
    )
    assert resp_open.status_code == 201
    bundle_data = resp_open.json()
    assert bundle_data["candidate_id"] == cand_id
    assert bundle_data["review_bundle_id"].startswith("rbd_")


def test_api_approve_ignores_spoofed_reviewer_identity(api_candidate_env):
    """
    Security Invariant: Client attempting to pass spoofed reviewer_id or approved_by
    in JSON payload is ignored; server binds strictly to authenticated principal.
    """
    client = api_candidate_env["client"]
    cand_id = api_candidate_env["cand"].candidate_id

    headers_reviewer = {
        "X-Principal-ID": api_candidate_env["user_reviewer"].id,
        "X-Principal-Roles": "reviewer",
        "X-Workspace-ID": "ws_alpha",
    }

    # Open review
    resp_open = client.post(
        f"/candidates/{cand_id}/reviews/open",
        json={"expected_revision": 1},
        headers=headers_reviewer,
    )
    assert resp_open.status_code == 201
    bundle_id = resp_open.json()["review_bundle_id"]

    # Spoofed payload: client attempts to claim they are "super_admin_god"
    spoofed_payload = {
        "expected_revision": 1,
        "reason": "Production ready.",
        "reviewer_id": "super_admin_god",
        "approved_by": "super_admin_god",
    }
    resp_approve = client.post(
        f"/candidates/{cand_id}/reviews/{bundle_id}/approve",
        json=spoofed_payload,
        headers=headers_reviewer,
    )
    assert resp_approve.status_code == 200
    decision_data = resp_approve.json()

    # Identity MUST be authenticated principal, NEVER spoofed payload value!
    assert decision_data["reviewer_principal_id"] == api_candidate_env["user_reviewer"].id
    assert decision_data["reviewer_principal_id"] != "super_admin_god"
    assert decision_data["decision"] == "APPROVED"


def test_api_cross_tenant_isolation(api_candidate_env):
    """Verifies that Workspace Beta reviewer cannot access or decide on Workspace Alpha candidate."""
    client = api_candidate_env["client"]
    cand_id = api_candidate_env["cand"].candidate_id

    headers_reviewer = {
        "X-Principal-ID": api_candidate_env["user_reviewer"].id,
        "X-Principal-Roles": "reviewer",
        "X-Workspace-ID": "ws_alpha",
    }
    resp_open = client.post(
        f"/candidates/{cand_id}/reviews/open",
        json={"expected_revision": 1},
        headers=headers_reviewer,
    )
    assert resp_open.status_code == 201
    bundle_id = resp_open.json()["review_bundle_id"]

    # Beta reviewer attempts to get bundle or approve candidate
    headers_beta = {
        "X-Principal-ID": api_candidate_env["user_beta_reviewer"].id,
        "X-Principal-Roles": "reviewer",
        "X-Workspace-ID": "ws_beta",
    }
    resp_beta_get = client.get(
        f"/candidates/{cand_id}/reviews/{bundle_id}",
        headers=headers_beta,
    )
    assert resp_beta_get.status_code == 404

    resp_beta_approve = client.post(
        f"/candidates/{cand_id}/reviews/{bundle_id}/approve",
        json={"expected_revision": 1, "reason": "Unauthorized"},
        headers=headers_beta,
    )
    assert resp_beta_approve.status_code == 404
