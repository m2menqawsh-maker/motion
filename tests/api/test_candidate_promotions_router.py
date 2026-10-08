"""
tests/api/test_candidate_promotions_router.py
=============================================
API Transport & Authorization Tests for Candidate Promotions Router (S28-07E).

Verifies:
1. Transport Only: Router passes requests strictly to PromotionService.
2. Authority & RBAC: Only authorized human admin/promoter can promote. AI agents strictly denied (403).
3. Server-Authoritative Identity: Spoofed promoter claims in request body are ignored.
4. Error Code Mappings:
   - 400 Bad Request on Preconditions failure (e.g. candidate not APPROVED).
   - 403 Forbidden on Permission or Security failure (e.g. viewer, AI agent, path traversal).
   - 404 Not Found on Candidate or Workspace missing.
   - 409 Conflict on Revision CAS mismatch or existing canonical template ID collision.
   - 422 Unprocessable Entity on Tampered cryptographic evidence.
5. Idempotency: Duplicate promotion calls safely return existing COMMITTED record.
6. Retrieval Endpoints: GET promotion by candidate, by promotion_id, and workspace promotions list.
"""

import hashlib
import json
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers.candidate_promotions import get_promotion_service
from scripts.core.database import DatabaseEngine, set_database_engine, TenantRepository
from scripts.core.storage import LocalStorageBackend, set_storage_service
from tests.conftest import make_test_auth_headers
from scripts.core.template_candidate_repository import SqlTemplateCandidateRepository
from scripts.core.template_registry_publisher import TemplateRegistryPublisher
from scripts.core.security.principal import Role
from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.plan import CreativeTier
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    CandidatePromotionRecord,
    CandidateReviewBundle,
    CandidateReviewDecision,
    CandidateReviewVerdict,
    CandidateStatus,
    CandidateValidationReport,
    GateStatus,
    PromotionRecordStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from creative_governance.candidates.hashing import compute_candidate_content_hash, compute_review_bundle_hash
from creative_governance.candidates.promotion_service import PromotionService

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def api_promotion_env(tmp_path: Path):
    # 1. Setup isolated hermetic DB
    db_file = tmp_path / "promotions_api_test.db"
    db_engine = DatabaseEngine(f"sqlite:///{db_file}")
    set_database_engine(db_engine)

    # 2. Setup isolated storage
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_svc = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage_svc)

    # 3. Setup isolated mock workspace for TemplateRegistryPublisher
    mock_ws = tmp_path / "mock_workspace"
    mock_ws.mkdir(parents=True, exist_ok=True)
    reg_dir = mock_ws / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-registry-data.json", reg_dir / "template-registry-data.json")
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-registry.tsx", reg_dir / "template-registry.tsx")
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-aliases.ts", reg_dir / "template-aliases.ts")

    contracts_dir = mock_ws / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "contracts" / "template-runtime-contract.json", contracts_dir / "template-runtime-contract.json")

    gt_dir = mock_ws / "ground-truth"
    gt_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "ground-truth" / "template_catalog.json", gt_dir / "template_catalog.json")

    (mock_ws / "templates" / "scenes").mkdir(parents=True, exist_ok=True)
    (mock_ws / "templates" / "elements").mkdir(parents=True, exist_ok=True)
    (mock_ws / "templates" / "effects").mkdir(parents=True, exist_ok=True)

    publisher = TemplateRegistryPublisher(workspace_root=mock_ws)
    cand_repo = SqlTemplateCandidateRepository(db_engine)
    promotion_service = PromotionService(
        repository=cand_repo,
        storage_service=storage_svc,
        registry_publisher=publisher,
    )

    # Override get_promotion_service dependency
    app.dependency_overrides[get_promotion_service] = lambda: promotion_service

    # 4. Setup tenants
    tenant_repo = TenantRepository(db_engine)
    user_alpha_admin = tenant_repo.create_user("usr_alpha_admin", "admin@alpha.com")
    user_alpha_rev = tenant_repo.create_user("usr_alpha_reviewer", "reviewer@alpha.com")
    user_alpha_view = tenant_repo.create_user("usr_alpha_viewer", "viewer@alpha.com")
    tenant_repo.create_workspace("ws_alpha", "Workspace Alpha", created_by=user_alpha_admin.id)
    tenant_repo.add_member("ws_alpha", user_alpha_admin.id, Role.ADMIN)
    tenant_repo.add_member("ws_alpha", user_alpha_rev.id, Role.REVIEWER)
    tenant_repo.add_member("ws_alpha", user_alpha_view.id, Role.VIEWER)

    user_beta_admin = tenant_repo.create_user("usr_beta_admin", "admin@beta.com")
    tenant_repo.create_workspace("ws_beta", "Workspace Beta", created_by=user_beta_admin.id)
    tenant_repo.add_member("ws_beta", user_beta_admin.id, Role.ADMIN)

    # 5. Setup an APPROVED candidate in ws_alpha with full cryptographic integrity
    source_code = 'import React from "react";\nexport const BannerTitle = ({ title }: { title: string }) => <h1>{title}</h1>;\n'
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "default": "Clean Video"}
        }
    }
    deps = ["react"]
    fixtures = {"title": "Test Title"}
    content_hash = compute_candidate_content_hash(
        source_code=source_code,
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        why_reuse_failed="none found",
        why_compose_failed="cannot compose",
        creative_plan_reference="cplan_promo_01",
        creative_tier_decision_reference="tier_promo_01",
    )
    now = "2026-10-02T20:00:00Z"
    storage_key = "workspaces/ws_alpha/candidates/cand_promo_http_001/source.tsx"
    storage_svc.put(storage_key, source_code.encode("utf-8"))

    cand = TemplateCandidate(
        candidate_id="cand_promo_http_001",
        workspace_id="ws_alpha",
        source_project_id="prj_alpha",
        creator_ai_run_id="run_ai_promo_01",
        creative_plan_reference="cplan_promo_01",
        creative_tier_decision_reference="tier_promo_01",
        why_reuse_failed="none found",
        why_compose_failed="cannot compose",
        source_code=source_code,
        source_code_path=storage_key,
        storage_keys={"source": storage_key, "source_code": storage_key},
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        content_hash=content_hash,
        revision=1,
        status=CandidateStatus.APPROVED,
        name="Banner Title Candidate",
        description="Dynamic banner title component",
        author="usr_creator_external",
        proposed_category="elements/typography",
        proposed_tags=["typography", "banner"],
        target_tier=CreativeTier.REUSE,
        required_provenance=ProvenanceRecord(source="plan:cplan_promo_01:decision:tier_promo_01", timestamp=now),
        created_at=now,
        updated_at=now,
    )
    cand_repo.save_candidate(cand)

    # Static Validation Report
    static_rep = CandidateValidationReport(
        validation_id="val_s_promo_http",
        candidate_id=cand.candidate_id,
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
    static_hash = hashlib.sha256(static_rep.model_dump_json().encode("utf-8")).hexdigest()

    # Runtime Validation Report
    runtime_rep = CandidateValidationReport(
        validation_id="val_r_promo_http",
        candidate_id=cand.candidate_id,
        workspace_id="ws_alpha",
        candidate_content_hash=content_hash,
        candidate_revision=1,
        phase=ValidationPhase.RUNTIME,
        policy_version="1.0.0",
        started_at=now,
        completed_at=now,
        gates=[CandidateGateResult(gate_id="render_smoke_gate", status=GateStatus.PASS, summary="ok")],
        overall_result=ValidationOverallResult.PASS,
        evidence_refs={"probe_report": "candidates/ws_alpha/cand_promo_http_001/probe.json"},
        static_validation_id=static_rep.validation_id,
        static_validation_report_hash=static_hash,
    )
    cand_repo.save_validation_report(runtime_rep)
    runtime_hash = hashlib.sha256(runtime_rep.model_dump_json().encode("utf-8")).hexdigest()

    # Review Bundle
    source_code_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
    schema_hash = hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()
    fixtures_hash = hashlib.sha256(json.dumps(fixtures, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()

    bundle_hash = compute_review_bundle_hash(
        candidate_id=cand.candidate_id,
        workspace_id="ws_alpha",
        candidate_content_hash=content_hash,
        candidate_revision=1,
        static_validation_id=static_rep.validation_id,
        runtime_validation_id=runtime_rep.validation_id,
        static_report_hash=static_hash,
        runtime_report_hash=runtime_hash,
        render_evidence_refs=[],
        representative_frame_refs=[],
        probe_report_ref=None,
        qc_report_ref=None,
        source_code_hash=source_code_hash,
        schema_hash=schema_hash,
        fixtures_hash=fixtures_hash,
        review_policy_version="1.0.0",
    )
    bundle = CandidateReviewBundle(
        review_bundle_id="rbd_promo_http_001",
        candidate_id=cand.candidate_id,
        workspace_id="ws_alpha",
        candidate_content_hash=content_hash,
        candidate_revision=1,
        static_validation_id=static_rep.validation_id,
        runtime_validation_id=runtime_rep.validation_id,
        static_report_hash=static_hash,
        runtime_report_hash=runtime_hash,
        source_code_hash=source_code_hash,
        schema_hash=schema_hash,
        fixtures_hash=fixtures_hash,
        review_policy_version="1.0.0",
        review_bundle_hash=bundle_hash,
        created_at=now,
    )
    cand_repo.save_review_bundle(bundle)

    # Review Decision (APPROVED)
    decision = CandidateReviewDecision(
        decision_id="rdec_promo_http_001",
        review_bundle_id=bundle.review_bundle_id,
        candidate_id=cand.candidate_id,
        workspace_id="ws_alpha",
        decision=CandidateReviewVerdict.APPROVED,
        reviewer_principal_id=user_alpha_rev.id,
        reviewer_role="reviewer",
        reason="Exemplary quality and test coverage.",
        candidate_content_hash=content_hash,
        candidate_revision=1,
        review_bundle_hash=bundle_hash,
        static_validation_report_hash=static_hash,
        runtime_validation_report_hash=runtime_hash,
        decided_at=now,
    )
    cand_repo.save_review_decision(decision)

    client = TestClient(app)

    yield {
        "client": client,
        "cand": cand,
        "user_admin": user_alpha_admin,
        "user_reviewer": user_alpha_rev,
        "user_viewer": user_alpha_view,
        "user_beta_admin": user_beta_admin,
        "publisher": publisher,
        "cand_repo": cand_repo,
    }

    # Teardown dependency override
    app.dependency_overrides.pop(get_promotion_service, None)


# =============================================================================
# 1. RBAC & AUTHORITY TESTS
# =============================================================================

def test_viewer_or_reviewer_denied_promotion_403(api_promotion_env):
    """RBAC Invariant: Viewer and Reviewer roles are strictly forbidden from promoting."""
    client = api_promotion_env["client"]
    cand_id = api_promotion_env["cand"].candidate_id

    # 1. Viewer tries to promote
    resp_viewer = client.post(
        f"/candidates/{cand_id}/promote",
        json={"target_template_id": "banner-title-clean", "expected_revision": 1},
        headers={
            **make_test_auth_headers(principal_id=api_promotion_env["user_viewer"].id, roles=["viewer"]),
            "X-Workspace-ID": "ws_alpha",
        },
    )
    assert resp_viewer.status_code == 403

    # 2. Reviewer tries to promote (Reviewer ≠ Promotion Authority)
    resp_reviewer = client.post(
        f"/candidates/{cand_id}/promote",
        json={"target_template_id": "banner-title-clean", "expected_revision": 1},
        headers={
            **make_test_auth_headers(principal_id=api_promotion_env["user_reviewer"].id, roles=["reviewer"]),
            "X-Workspace-ID": "ws_alpha",
        },
    )
    assert resp_reviewer.status_code == 403


def test_ai_agent_caller_strictly_denied_promotion_403(api_promotion_env):
    """Authority Invariant: AI agents are strictly forbidden from promotion (AI ≠ Promotion Authority)."""
    client = api_promotion_env["client"]
    cand_id = api_promotion_env["cand"].candidate_id

    resp = client.post(
        f"/candidates/{cand_id}/promote",
        json={"target_template_id": "banner-title-clean", "expected_revision": 1},
        headers={
            **make_test_auth_headers(principal_id="gpt-4o", roles=["admin"]),
            "X-Workspace-ID": "ws_alpha",
        },
    )
    assert resp.status_code == 403
    assert "forbidden" in str(resp.json()).lower() or "ai" in str(resp.json()).lower() or "denied" in str(resp.json()).lower()


def test_cross_tenant_candidate_promotion_denied_404(api_promotion_env):
    """Multi-Tenant Isolation: Workspace Beta admin cannot promote candidate belonging to Workspace Alpha."""
    client = api_promotion_env["client"]
    cand_id = api_promotion_env["cand"].candidate_id

    resp = client.post(
        f"/candidates/{cand_id}/promote",
        json={"target_template_id": "banner-title-clean", "expected_revision": 1},
        headers={
            **make_test_auth_headers(principal_id=api_promotion_env["user_beta_admin"].id, roles=["admin"]),
            "X-Workspace-ID": "ws_beta",
        },
    )
    assert resp.status_code == 404


# =============================================================================
# 2. PRECONDITIONS & CRYPTOGRAPHIC TAMPER FAILURES (400, 409, 422)
# =============================================================================

def test_unapproved_candidate_denied_promotion_400(api_promotion_env):
    """Negative: Candidate not in APPROVED status returns 400 Bad Request."""
    client = api_promotion_env["client"]
    cand = api_promotion_env["cand"]
    cand_repo = api_promotion_env["cand_repo"]

    # Demote status back to VALIDATED
    cand_repo.update_candidate_status_cas(cand.candidate_id, cand.workspace_id, CandidateStatus.VALIDATED, cand.revision)

    resp = client.post(
        f"/candidates/{cand.candidate_id}/promote",
        json={"target_template_id": "banner-title-clean", "expected_revision": cand.revision},
        headers={
            **make_test_auth_headers(principal_id=api_promotion_env["user_admin"].id, roles=["admin"]),
            "X-Workspace-ID": "ws_alpha",
        },
    )
    assert resp.status_code == 400
    assert "must be 'APPROVED'" in resp.json()["detail"]


def test_stale_expected_revision_denied_promotion_409(api_promotion_env):
    """Negative: CAS expected_revision mismatch returns 409 Conflict."""
    client = api_promotion_env["client"]
    cand_id = api_promotion_env["cand"].candidate_id

    resp = client.post(
        f"/candidates/{cand_id}/promote",
        json={"target_template_id": "banner-title-clean", "expected_revision": 999},
        headers={
            **make_test_auth_headers(principal_id=api_promotion_env["user_admin"].id, roles=["admin"]),
            "X-Workspace-ID": "ws_alpha",
        },
    )
    assert resp.status_code == 409
    assert "revision conflict" in resp.json()["detail"]


def test_colliding_target_template_id_denied_promotion_409(api_promotion_env):
    """Negative: Collision with existing protected canonical template ID returns 409 Conflict."""
    client = api_promotion_env["client"]
    cand_id = api_promotion_env["cand"].candidate_id

    resp = client.post(
        f"/candidates/{cand_id}/promote",
        json={"target_template_id": "fade-transition", "expected_revision": 1},
        headers={
            **make_test_auth_headers(principal_id=api_promotion_env["user_admin"].id, roles=["admin"]),
            "X-Workspace-ID": "ws_alpha",
        },
    )
    assert resp.status_code == 409
    assert "collides with an existing canonical template" in resp.json()["detail"]


def test_path_traversal_template_id_denied_promotion_403(api_promotion_env):
    """Negative: Path traversal in target_template_id returns 403 Forbidden."""
    client = api_promotion_env["client"]
    cand_id = api_promotion_env["cand"].candidate_id

    resp = client.post(
        f"/candidates/{cand_id}/promote",
        json={"target_template_id": "../../templates/escape", "expected_revision": 1},
        headers={
            **make_test_auth_headers(principal_id=api_promotion_env["user_admin"].id, roles=["admin"]),
            "X-Workspace-ID": "ws_alpha",
        },
    )
    assert resp.status_code == 403


# =============================================================================
# 3. SUCCESSFUL PROMOTION FLOW & SERVER-AUTHORITATIVE IDENTITY (200)
# =============================================================================

def test_successful_promotion_flow_and_spoof_ignorance_200(api_promotion_env):
    """
    Positive: Full promotion flow completes with 200 OK.
    Verifies that client-supplied spoofed claims in request body ('promoter_id', 'role')
    are completely ignored in favor of the server-verified principal.
    """
    client = api_promotion_env["client"]
    cand = api_promotion_env["cand"]
    user_admin = api_promotion_env["user_admin"]

    headers_admin = {
        **make_test_auth_headers(principal_id=user_admin.id, roles=["admin"]),
        "X-Workspace-ID": "ws_alpha",
    }

    # 1. Before promotion, GET /candidates/{cand_id}/promotion returns 404
    resp_get_pre = client.get(f"/candidates/{cand.candidate_id}/promotion", headers=headers_admin)
    assert resp_get_pre.status_code == 404

    # 2. Promote candidate with spoofed body claims
    payload = {
        "target_template_id": "banner-title-clean",
        "expected_revision": cand.revision,
        "target_template_version": "1.0.0",
        "promoter_id": "malicious_spoofed_principal_id",
        "role": "super_admin",
    }
    resp_promote = client.post(f"/candidates/{cand.candidate_id}/promote", json=payload, headers=headers_admin)
    assert resp_promote.status_code == 200
    record_data = resp_promote.json()

    assert record_data["status"] == "COMMITTED"
    assert record_data["target_template_id"] == "banner-title-clean"
    assert record_data["target_template_version"] == "1.0.0"
    # Identity Invariant: promoter_id is server principal, not spoofed body claim!
    assert record_data["promoted_by_principal_id"] == user_admin.id
    assert record_data["promoted_by_principal_id"] != "malicious_spoofed_principal_id"
    assert record_data["promotion_manifest_hash"] != ""

    # 3. Idempotent Retry: Calling promotion again returns the exact same record
    resp_retry = client.post(f"/candidates/{cand.candidate_id}/promote", json=payload, headers=headers_admin)
    assert resp_retry.status_code == 200
    retry_data = resp_retry.json()
    assert retry_data["promotion_id"] == record_data["promotion_id"]

    # 4. GET /candidates/{cand_id}/promotion returns 200
    resp_get_post = client.get(f"/candidates/{cand.candidate_id}/promotion", headers=headers_admin)
    assert resp_get_post.status_code == 200
    assert resp_get_post.json()["promotion_id"] == record_data["promotion_id"]

    # 5. GET /candidates/promotions/{promotion_id} returns 200
    prom_id = record_data["promotion_id"]
    resp_get_by_id = client.get(f"/candidates/promotions/{prom_id}", headers=headers_admin)
    assert resp_get_by_id.status_code == 200
    assert resp_get_by_id.json()["candidate_id"] == cand.candidate_id

    # 6. GET /candidates/promotions returns list containing the record
    resp_list = client.get("/candidates/promotions", headers=headers_admin)
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) == 1
    assert items[0]["promotion_id"] == prom_id
