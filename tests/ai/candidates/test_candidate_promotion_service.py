"""
tests/ai/candidates/test_candidate_promotion_service.py
=======================================================
Comprehensive Test Suite for PromotionService & Canonical Publication (S28-07E).

Verifies Non-Negotiable Invariants:
1. Sole Authority: PromotionService is the sole authority for canonical template promotion.
2. Authority & RBAC: AI creator / agent principals and non-admin roles strictly denied.
3. Preconditions: Only APPROVED candidates with valid decision, bundle, and passing reports can promote.
4. Tamper Detection: Content hash, bundle hash, static/runtime report hash tampering fail closed.
5. Canonical Identity & Path Security: Traversal attacks, invalid naming, and ID collisions rejected.
6. Zero Mutation on Preflight/Staging Failure: Uncommitted failures leave canonical registry untouched.
7. Staged Publication & Atomic Commit: Atomic rollbacks on mid-flight failure restore clean state.
8. Post-Publish Verification: Comprehensive consistency verification of source, registry, contract, catalog.
9. CAS Transition: Transition to PROMOTED strictly conditional on successful commit & verification.
10. Idempotency: Duplicate promotion of same candidate returns existing record without re-publication.
11. Multi-Tenant Isolation: Cross-workspace promotions fail closed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import pytest

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
    PromotionManifest,
    PromotionRecordStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from creative_governance.candidates.errors import (
    CandidateConflictError,
    CandidateNotFoundError,
    CandidatePermissionError,
    CandidateTenantMismatchError,
    PromotionCollisionError,
    PromotionError,
    PromotionPreconditionError,
    PromotionRollbackError,
    PromotionSecurityError,
    PromotionTamperedError,
)
from creative_governance.candidates.hashing import (
    compute_candidate_content_hash,
    compute_promotion_manifest_hash,
    compute_review_bundle_hash,
)
from creative_governance.candidates.promotion_service import PromotionService
from creative_governance.candidates.repository import InMemoryTemplateCandidateRepository
from scripts.core.security.permissions import Action
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend
from scripts.core.template_registry_publisher import TemplateRegistryPublisher
from scripts.core.tenant_model import TenantContext

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def mock_workspace(tmp_path: Path) -> Path:
    """Prepares an isolated mock workspace containing real baseline registry and contracts."""
    ws = tmp_path / "mock_workspace"
    ws.mkdir(parents=True, exist_ok=True)

    # Copy registry files
    reg_dir = ws / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-registry-data.json", reg_dir / "template-registry-data.json")
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-registry.tsx", reg_dir / "template-registry.tsx")
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-aliases.ts", reg_dir / "template-aliases.ts")

    # Copy contracts
    contracts_dir = ws / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "contracts" / "template-runtime-contract.json", contracts_dir / "template-runtime-contract.json")

    # Copy ground-truth catalog
    gt_dir = ws / "ground-truth"
    gt_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "ground-truth" / "template_catalog.json", gt_dir / "template_catalog.json")

    # Templates directory
    (ws / "templates" / "scenes").mkdir(parents=True, exist_ok=True)
    (ws / "templates" / "elements").mkdir(parents=True, exist_ok=True)
    (ws / "templates" / "effects").mkdir(parents=True, exist_ok=True)

    return ws


@pytest.fixture
def storage(tmp_path: Path):
    return LocalStorageBackend(root_dir=tmp_path / "storage")


@pytest.fixture
def repo():
    return InMemoryTemplateCandidateRepository()


@pytest.fixture
def publisher(mock_workspace: Path):
    return TemplateRegistryPublisher(workspace_root=mock_workspace)


@pytest.fixture
def promotion_service(repo, storage, publisher):
    return PromotionService(repository=repo, storage_service=storage, registry_publisher=publisher)


def make_tenant_context(
    workspace_id: str = "ws_alpha",
    user_id: str = "usr_admin_01",
    role: Role = Role.ADMIN,
    principal_type: PrincipalType = PrincipalType.HUMAN,
) -> TenantContext:
    principal = Principal(
        principal_id=user_id,
        principal_type=principal_type,
        roles={role},
        project_scopes={"*": {role}},
    )
    return TenantContext(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
        principal=principal,
    )


def create_approved_candidate_fixture(
    repo: InMemoryTemplateCandidateRepository,
    storage: LocalStorageBackend,
    workspace_id: str = "ws_alpha",
    candidate_id: str = "cand_spring_quote_001",
    author: str = "usr_creator_01",
    revision: int = 1,
) -> tuple[TemplateCandidate, CandidateReviewDecision, CandidateReviewBundle, CandidateValidationReport, CandidateValidationReport]:
    """Sets up an APPROVED candidate fixture with passing static/runtime evidence and authoritative approval."""
    now = _now()
    source_code = (
        'import React from "react";\n'
        'export const SpringQuote = ({ text }: { text: string }) => <div>{text}</div>;\n'
    )
    schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "default": "Inspirational Quote"}
        }
    }
    fixtures = {"text": "Make each day your masterpiece."}
    deps = ["framer-motion"]

    content_hash = compute_candidate_content_hash(
        source_code=source_code,
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        why_reuse_failed="No spring quote template available",
        why_compose_failed="Quote typography requires custom spring physics",
        creative_plan_reference="cplan_promo_001",
        creative_tier_decision_reference="tier_dec_001",
    )

    candidate = TemplateCandidate(
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        source_project_id="prj_alpha_01",
        creator_ai_run_id="run_ai_creator_001",
        creative_plan_reference="cplan_promo_001",
        creative_tier_decision_reference="tier_dec_001",
        why_reuse_failed="No spring quote template available",
        why_compose_failed="Quote typography requires custom spring physics",
        source_code=source_code,
        source_code_path=f"workspaces/{workspace_id}/projects/prj_alpha_01/candidates/{candidate_id}/source.tsx",
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        content_hash=content_hash,
        revision=revision,
        status=CandidateStatus.APPROVED,
        name="Spring Quote Card",
        description="Spring physics typography quote card",
        author=author,
        proposed_category="elements/typography",
        proposed_tags=["quote", "typography", "spring"],
        target_tier=CreativeTier.REUSE,
        required_provenance=ProvenanceRecord(
            source="plan:cplan_promo_001:decision:tier_dec_001",
            timestamp=now,
        ),
        storage_keys={"source_code": f"workspaces/{workspace_id}/candidates/{candidate_id}/source.tsx"},
        created_at=now,
        updated_at=now,
    )
    repo.save_candidate(candidate)

    # Static report
    static_report = CandidateValidationReport(
        validation_id=f"val_static_{candidate_id}",
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        candidate_content_hash=content_hash,
        candidate_revision=revision,
        phase=ValidationPhase.STATIC,
        policy_version="1.0.0",
        started_at=now,
        completed_at=now,
        gates=[CandidateGateResult(gate_id="contract_gate", status=GateStatus.PASS, summary="Contract ok")],
        overall_result=ValidationOverallResult.PASS,
        evidence_refs={"report": f"candidates/{workspace_id}/{candidate_id}/static_report.json"},
    )
    repo.save_validation_report(static_report)

    # Runtime report
    static_rep_hash = hashlib.sha256(static_report.model_dump_json().encode("utf-8")).hexdigest()
    runtime_report = CandidateValidationReport(
        validation_id=f"val_runtime_{candidate_id}",
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        candidate_content_hash=content_hash,
        candidate_revision=revision,
        phase=ValidationPhase.RUNTIME,
        policy_version="1.0.0",
        started_at=now,
        completed_at=now,
        gates=[
            CandidateGateResult(gate_id="render_smoke_gate", status=GateStatus.PASS, summary="Smoke ok"),
            CandidateGateResult(gate_id="runtime_contract_gate", status=GateStatus.PASS, summary="Contract ok"),
        ],
        overall_result=ValidationOverallResult.PASS,
        evidence_refs={
            "smoke_frame_0": f"candidates/{workspace_id}/{candidate_id}/smoke_0.png",
            "frame_0": f"candidates/{workspace_id}/{candidate_id}/frame_0.png",
        },
        static_validation_id=static_report.validation_id,
        static_validation_report_hash=static_rep_hash,
    )
    repo.save_validation_report(runtime_report)

    runtime_rep_hash = hashlib.sha256(runtime_report.model_dump_json().encode("utf-8")).hexdigest()

    source_code_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
    schema_hash = hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()
    fixtures_hash = hashlib.sha256(json.dumps(fixtures, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()

    evidence_refs = {
        "smoke_frame_0": f"candidates/{workspace_id}/{candidate_id}/smoke_0.png",
        "frame_0": f"candidates/{workspace_id}/{candidate_id}/frame_0.png",
    }
    rep_frame_refs = [f"candidates/{workspace_id}/{candidate_id}/frame_0.png"]

    # Review Bundle
    bundle_hash = compute_review_bundle_hash(
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        candidate_content_hash=content_hash,
        candidate_revision=revision,
        static_validation_id=static_report.validation_id,
        runtime_validation_id=runtime_report.validation_id,
        static_report_hash=static_rep_hash,
        runtime_report_hash=runtime_rep_hash,
        render_evidence_refs=evidence_refs,
        representative_frame_refs=rep_frame_refs,
        probe_report_ref=None,
        qc_report_ref=None,
        source_code_hash=source_code_hash,
        schema_hash=schema_hash,
        fixtures_hash=fixtures_hash,
        review_policy_version="1.0.0",
    )
    bundle = CandidateReviewBundle(
        review_bundle_id=f"rbundle_{candidate_id}",
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        candidate_content_hash=content_hash,
        candidate_revision=revision,
        static_validation_id=static_report.validation_id,
        runtime_validation_id=runtime_report.validation_id,
        static_report_hash=static_rep_hash,
        runtime_report_hash=runtime_rep_hash,
        render_evidence_refs=evidence_refs,
        representative_frame_refs=rep_frame_refs,
        probe_report_ref=None,
        qc_report_ref=None,
        source_code_hash=source_code_hash,
        schema_hash=schema_hash,
        fixtures_hash=fixtures_hash,
        created_at=now,
        review_bundle_hash=bundle_hash,
    )
    repo.save_review_bundle(bundle)

    # Authoritative Review Decision
    decision = CandidateReviewDecision(
        decision_id=f"rdec_{candidate_id}",
        review_bundle_id=bundle.review_bundle_id,
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        decision=CandidateReviewVerdict.APPROVED,
        reviewer_principal_id="usr_human_reviewer_01",
        reviewer_role="reviewer",
        reason="Clean spring animation, verified contracts",
        candidate_content_hash=content_hash,
        candidate_revision=revision,
        review_bundle_hash=bundle_hash,
        static_validation_report_hash=static_rep_hash,
        runtime_validation_report_hash=runtime_rep_hash,
        decided_at=now,
    )
    repo.save_review_decision(decision)

    return candidate, decision, bundle, static_report, runtime_report


# =============================================================================
# 1. AUTHORITY & RBAC INVARIANT TESTS
# =============================================================================

def test_unauthenticated_caller_denied_promotion(promotion_service, repo, storage):
    """Negative: Unauthenticated caller cannot promote candidate."""
    create_approved_candidate_fixture(repo, storage)
    anon_principal = Principal(
        principal_id="",
        principal_type=PrincipalType.ANONYMOUS,
        roles=set(),
    )
    ctx = TenantContext(
        workspace_id="ws_alpha",
        user_id="",
        role=Role.VIEWER,
        principal=anon_principal,
    )

    with pytest.raises(PromotionSecurityError, match="Unauthenticated"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id="cand_spring_quote_001",
            target_template_id="spring-quote-card",
            expected_revision=1,
        )


def test_ai_agent_caller_strictly_denied_promotion(promotion_service, repo, storage):
    """Negative: AI Agent principal strictly denied promotion authority (AI ≠ Promotion Authority)."""
    create_approved_candidate_fixture(repo, storage)
    ai_principal = Principal(
        principal_id="ai_agent_creative_promoter",
        principal_type=PrincipalType.SERVICE,
        roles={Role.ADMIN},
    )
    ctx = TenantContext(
        workspace_id="ws_alpha",
        user_id="ai_agent_creative_promoter",
        role=Role.ADMIN,
        principal=ai_principal,
    )

    with pytest.raises(PromotionSecurityError, match="is not a human user|forbidden"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id="cand_spring_quote_001",
            target_template_id="spring-quote-card",
            expected_revision=1,
        )


@pytest.mark.parametrize("forbidden_id", ["claude", "gpt-4o", "creative_planner", "anonymous", "system-worker"])
def test_forbidden_principal_identities_denied_promotion(promotion_service, repo, storage, forbidden_id):
    """Negative: Disallowed or synthetic identities cannot promote candidates."""
    create_approved_candidate_fixture(repo, storage)
    ctx = make_tenant_context(user_id=forbidden_id, role=Role.ADMIN)

    with pytest.raises(PromotionSecurityError, match="forbidden from authorizing template promotion"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id="cand_spring_quote_001",
            target_template_id="spring-quote-card",
            expected_revision=1,
        )


@pytest.mark.parametrize("role", [Role.VIEWER, Role.EDITOR, Role.REVIEWER])
def test_insufficient_role_denied_promotion(promotion_service, repo, storage, role):
    """Negative: Non-admin roles lacking TEMPLATE_PROMOTE permission cannot promote."""
    create_approved_candidate_fixture(repo, storage)
    ctx = make_tenant_context(role=role)

    with pytest.raises(CandidatePermissionError, match="lacks required permission 'template:promote'"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id="cand_spring_quote_001",
            target_template_id="spring-quote-card",
            expected_revision=1,
        )


def test_cross_tenant_promotion_denied(promotion_service, repo, storage):
    """Negative: Admin from ws_beta cannot promote candidate owned by ws_alpha."""
    create_approved_candidate_fixture(repo, storage, workspace_id="ws_alpha")
    ctx_beta = make_tenant_context(workspace_id="ws_beta", role=Role.ADMIN)

    with pytest.raises((CandidateTenantMismatchError, CandidateNotFoundError)):
        promotion_service.promote_candidate(
            tenant_context=ctx_beta,
            candidate_id="cand_spring_quote_001",
            target_template_id="spring-quote-card",
            expected_revision=1,
        )


# =============================================================================
# 2. CANONICAL IDENTITY & PATH SECURITY TESTS
# =============================================================================

@pytest.mark.parametrize("malicious_id", [
    "../../templates/escape",
    "../escape",
    "templates/sub",
    "/root/escape",
    "\\windows\\path",
])
def test_path_traversal_template_id_denied(promotion_service, repo, storage, malicious_id):
    """Negative: Path traversal in target_template_id is rejected during preflight."""
    create_approved_candidate_fixture(repo, storage)
    ctx = make_tenant_context()

    with pytest.raises(PromotionSecurityError, match="Path traversal detected"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id="cand_spring_quote_001",
            target_template_id=malicious_id,
            expected_revision=1,
        )


@pytest.mark.parametrize("invalid_id", [
    "SpringQuoteCard",  # PascalCase
    "spring quote card",  # spaces
    "spring_quote_card",  # snake_case
    "quote@card!",  # special chars
    "--double-hyphen",
    "-lead-hyphen",
    "trail-hyphen-",
])
def test_invalid_template_id_naming_denied(promotion_service, repo, storage, invalid_id):
    """Negative: target_template_id must adhere strictly to lowercase kebab-case regex."""
    create_approved_candidate_fixture(repo, storage)
    ctx = make_tenant_context()

    with pytest.raises(PromotionSecurityError, match="violates canonical naming rule regex"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id="cand_spring_quote_001",
            target_template_id=invalid_id,
            expected_revision=1,
        )


def test_existing_canonical_template_collision_denied(promotion_service, repo, storage, publisher):
    """Negative: Collision with existing protected template ID is rejected."""
    create_approved_candidate_fixture(repo, storage)
    ctx = make_tenant_context()

    # Load existing template IDs from registry data
    raw_data = json.loads(publisher.registry_data_path.read_text(encoding="utf-8"))
    existing_id = list(raw_data["templates"].keys())[0]

    with pytest.raises(PromotionCollisionError, match="collides with an existing canonical template"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id="cand_spring_quote_001",
            target_template_id=existing_id,
            expected_revision=1,
        )


# =============================================================================
# 3. PRECONDITIONS TESTS
# =============================================================================

@pytest.mark.parametrize("bad_status", [
    CandidateStatus.DRAFT,
    CandidateStatus.VALIDATING,
    CandidateStatus.VALIDATED,
    CandidateStatus.AWAITING_APPROVAL,
    CandidateStatus.REJECTED,
    CandidateStatus.PROMOTED,
    CandidateStatus.RETIRED,
])
def test_non_approved_candidate_denied_promotion(promotion_service, repo, storage, bad_status):
    """Negative: Candidates not in APPROVED status cannot be promoted."""
    cand, _, _, _, _ = create_approved_candidate_fixture(repo, storage)
    cand = cand.model_copy(update={"status": bad_status})
    repo._candidates[(cand.workspace_id, cand.candidate_id)] = cand
    ctx = make_tenant_context()

    with pytest.raises(PromotionPreconditionError, match="must be 'APPROVED'"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )


def test_missing_review_decision_denied_promotion(promotion_service, repo, storage):
    """Negative: APPROVED status without authoritative review decision is rejected."""
    cand, decision, _, _, _ = create_approved_candidate_fixture(repo, storage)
    repo._decisions.clear()  # Remove decision
    ctx = make_tenant_context()

    with pytest.raises(PromotionPreconditionError, match="No authoritative human review decision found"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )


def test_rejected_decision_denied_promotion(promotion_service, repo, storage):
    """Negative: If latest decision is REJECTED, promotion fails closed."""
    cand, decision, bundle, _, _ = create_approved_candidate_fixture(repo, storage)
    # Clear decisions to avoid bundle conflict check in InMemory repo
    repo._decisions.clear()
    rejected_decision = CandidateReviewDecision(
        decision_id=f"rdec_reject_{cand.candidate_id}",
        review_bundle_id=bundle.review_bundle_id,
        candidate_id=cand.candidate_id,
        workspace_id=cand.workspace_id,
        decision=CandidateReviewVerdict.REJECTED,
        reviewer_principal_id="usr_human_reviewer_01",
        reviewer_role="reviewer",
        reason="Fails design system guidelines",
        candidate_content_hash=cand.content_hash,
        candidate_revision=cand.revision,
        review_bundle_hash=bundle.review_bundle_hash,
        static_validation_report_hash=decision.static_validation_report_hash,
        runtime_validation_report_hash=decision.runtime_validation_report_hash,
        decided_at=_now(),
    )
    repo.save_review_decision(rejected_decision)
    ctx = make_tenant_context()

    with pytest.raises(PromotionPreconditionError, match="decision is 'REJECTED'"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )


def test_failing_validation_reports_denied_promotion(promotion_service, repo, storage):
    """Negative: Validation reports with overall_result != PASS fail closed."""
    cand, _, _, static_rep, _ = create_approved_candidate_fixture(repo, storage)
    static_rep = static_rep.model_copy(update={"overall_result": ValidationOverallResult.FAIL})
    repo.save_validation_report(static_rep)
    ctx = make_tenant_context()

    with pytest.raises(PromotionPreconditionError, match="Passing static validation report missing"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )


# =============================================================================
# 4. CRYPTOGRAPHIC TAMPER DETECTION (FAIL CLOSED)
# =============================================================================

def test_tampered_candidate_content_hash_denied(promotion_service, repo, storage):
    """Negative: Content hash mismatch between candidate and approval decision rejected."""
    cand, _, _, _, _ = create_approved_candidate_fixture(repo, storage)
    cand = cand.model_copy(update={"content_hash": "0" * 64})
    repo._candidates[(cand.workspace_id, cand.candidate_id)] = cand
    ctx = make_tenant_context()

    with pytest.raises(PromotionTamperedError, match="Candidate content hash mismatch"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )


def test_tampered_review_bundle_hash_denied(promotion_service, repo, storage):
    """Negative: Review bundle digest altered after approval rejected."""
    cand, _, bundle, _, _ = create_approved_candidate_fixture(repo, storage)
    bundle = bundle.model_copy(update={"review_bundle_hash": "f" * 64})
    repo._bundles[(bundle.workspace_id, bundle.review_bundle_id)] = bundle
    ctx = make_tenant_context()

    with pytest.raises(PromotionTamperedError, match="Review bundle hash mismatch"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )


def test_tampered_static_report_hash_denied(promotion_service, repo, storage):
    """Negative: Tampered static validation report rejected."""
    cand, _, _, static_rep, _ = create_approved_candidate_fixture(repo, storage)
    tampered_gates = [CandidateGateResult(gate_id="contract_gate", status=GateStatus.PASS, summary="Tampered summary after approval")]
    static_rep = static_rep.model_copy(update={"gates": tampered_gates})
    repo.save_validation_report(static_rep)
    ctx = make_tenant_context()

    with pytest.raises(PromotionTamperedError, match="Static validation report tampered"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )


def test_tampered_runtime_report_hash_denied(promotion_service, repo, storage):
    """Negative: Tampered runtime validation report rejected."""
    cand, _, _, _, runtime_rep = create_approved_candidate_fixture(repo, storage)
    tampered_gates = [
        CandidateGateResult(gate_id="render_smoke_gate", status=GateStatus.PASS, summary="Tampered runtime summary"),
        CandidateGateResult(gate_id="runtime_contract_gate", status=GateStatus.PASS, summary="Contract ok"),
    ]
    runtime_rep = runtime_rep.model_copy(update={"gates": tampered_gates})
    repo.save_validation_report(runtime_rep)
    ctx = make_tenant_context()

    with pytest.raises(PromotionTamperedError, match="Runtime validation report tampered"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )


# =============================================================================
# 5. CAS REVISION CONCURRENCY & PREFLIGHT ZERO MUTATION
# =============================================================================

def test_cas_expected_revision_mismatch_denied(promotion_service, repo, storage, publisher):
    """Negative: Stale CAS revision rejected without modifying any canonical registry files."""
    cand, _, _, _, _ = create_approved_candidate_fixture(repo, storage, revision=2)
    ctx = make_tenant_context()
    pre_hash = hashlib.sha256(publisher.registry_data_path.read_bytes()).hexdigest()

    with pytest.raises(CandidateConflictError, match="revision conflict"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=1,  # Stale: actual revision is 2
        )

    # Invariant: Zero canonical mutations
    post_hash = hashlib.sha256(publisher.registry_data_path.read_bytes()).hexdigest()
    assert pre_hash == post_hash, "Registry must not be mutated when CAS check fails"


# =============================================================================
# 6. SUCCESSFUL CANONICAL PROMOTION (HAPPY PATH)
# =============================================================================

def test_successful_canonical_promotion(promotion_service, repo, storage, publisher, mock_workspace):
    """
    Positive: Full promotion lifecycle:
    Preflight PASS -> Staging PASS -> Commit PASS -> Verification PASS -> PROMOTED status.
    """
    cand, decision, bundle, _, _ = create_approved_candidate_fixture(repo, storage)
    ctx = make_tenant_context()

    pre_reg_hash = hashlib.sha256(publisher.registry_data_path.read_bytes()).hexdigest()

    record = promotion_service.promote_candidate(
        tenant_context=ctx,
        candidate_id=cand.candidate_id,
        target_template_id="spring-quote-card",
        expected_revision=cand.revision,
        target_template_version="1.0.0",
    )

    # 1. Assert CandidatePromotionRecord properties
    assert isinstance(record, CandidatePromotionRecord)
    assert record.status == PromotionRecordStatus.COMMITTED
    assert record.target_template_id == "spring-quote-card"
    assert record.target_template_version == "1.0.0"
    assert record.approval_decision_id == decision.decision_id
    assert record.review_bundle_hash == bundle.review_bundle_hash
    assert record.pre_publish_registry_hash == pre_reg_hash
    assert record.post_publish_registry_hash != ""
    assert record.promoted_by_principal_id == ctx.principal.principal_id
    assert len(record.published_artifact_hashes) >= 4

    # 2. Assert Candidate lifecycle status updated to PROMOTED via CAS
    updated_cand = repo.get_candidate(cand.candidate_id, cand.workspace_id)
    assert updated_cand is not None
    assert updated_cand.status == CandidateStatus.PROMOTED
    assert updated_cand.revision == cand.revision

    # 3. Assert canonical template component source file was created
    expected_src = mock_workspace / "templates" / "elements" / "SpringQuoteCard.tsx"
    assert expected_src.exists(), f"Source file {expected_src} must exist"
    assert "export const SpringQuote" in expected_src.read_text(encoding="utf-8")

    # 4. Assert template-registry-data.json contains new template
    reg_data = json.loads(publisher.registry_data_path.read_text(encoding="utf-8"))
    assert "spring-quote-card" in reg_data["templates"]
    entry = reg_data["templates"]["spring-quote-card"]
    assert entry["component_name"] == "SpringQuoteCard"
    assert entry["category"] == "text"
    assert entry["runtime_available"] is True

    # 5. Assert template-runtime-contract.json was regenerated
    contract_data = json.loads(publisher.contract_path.read_text(encoding="utf-8"))
    assert "spring-quote-card" in contract_data["templates"]
    assert "SpringQuoteCard" in contract_data["aliases"]

    # 6. Assert template-registry.tsx has import and binding
    tsx_text = publisher.registry_tsx_path.read_text(encoding="utf-8")
    assert 'import { SpringQuoteCard } from "../templates/elements/SpringQuoteCard";' in tsx_text
    assert "SpringQuoteCard," in tsx_text

    # 7. Assert template_catalog.json updated
    catalog_data = json.loads(publisher.catalog_path.read_text(encoding="utf-8"))
    assert any(item.get("id") == "spring-quote-card" for item in catalog_data)

    # 8. Assert PromotionManifest was stored deterministically
    assert record.promotion_manifest_hash != ""


# =============================================================================
# 7. IDEMPOTENCY
# =============================================================================

def test_promotion_idempotency_retry(promotion_service, repo, storage, publisher):
    """
    Positive: Re-invoking promotion with exact identical parameters returns existing
    record without re-publishing, incrementing version, or creating duplicates.
    """
    cand, _, _, _, _ = create_approved_candidate_fixture(repo, storage)
    ctx = make_tenant_context()

    # First promotion
    rec1 = promotion_service.promote_candidate(
        tenant_context=ctx,
        candidate_id=cand.candidate_id,
        target_template_id="spring-quote-card",
        expected_revision=1,
    )

    # Retry exact same promotion
    rec2 = promotion_service.promote_candidate(
        tenant_context=ctx,
        candidate_id=cand.candidate_id,
        target_template_id="spring-quote-card",
        expected_revision=rec1.candidate_id and 1,
    )

    assert rec1.promotion_id == rec2.promotion_id
    assert rec1.promotion_manifest_hash == rec2.promotion_manifest_hash
    assert rec2.status == PromotionRecordStatus.COMMITTED

    # Ensure no duplicates in registry
    reg_data = json.loads(publisher.registry_data_path.read_text(encoding="utf-8"))
    matching_entries = [k for k in reg_data["templates"].keys() if k == "spring-quote-card"]
    assert len(matching_entries) == 1, "Must not duplicate registry rows"


# =============================================================================
# 8. POST-PUBLISH FAILURE & CLEAN ROLLBACK
# =============================================================================

def test_post_publish_verification_failure_triggers_clean_rollback(promotion_service, repo, storage, publisher, mock_workspace):
    """
    Negative: If post-publish verification fails after commit, the RollbackJournal
    restores the original canonical state, candidate remains APPROVED, and record is ROLLED_BACK.
    """
    cand, _, _, _, _ = create_approved_candidate_fixture(repo, storage)
    ctx = make_tenant_context()

    pre_reg_bytes = publisher.registry_data_path.read_bytes()
    pre_contract_bytes = publisher.contract_path.read_bytes()
    pre_tsx_bytes = publisher.registry_tsx_path.read_bytes()

    # Artificially force verify_canonical_publication to fail
    def failing_verify(target_template_id, component_name, rel_file_path, expected_source_hash):
        raise PromotionError("Simulated post-publish consistency check failure (e.g. hash mismatch)")

    publisher.verify_canonical_publication = failing_verify

    with pytest.raises(PromotionRollbackError, match="rolled back"):
        promotion_service.promote_candidate(
            tenant_context=ctx,
            candidate_id=cand.candidate_id,
            target_template_id="spring-quote-card",
            expected_revision=cand.revision,
        )

    # 1. Candidate remains in APPROVED status (NOT PROMOTED)
    cand_after = repo.get_candidate(cand.candidate_id, cand.workspace_id)
    assert cand_after.status == CandidateStatus.APPROVED
    assert cand_after.revision == cand.revision

    # 2. Canonical files restored to exact pre-mutation state
    assert publisher.registry_data_path.read_bytes() == pre_reg_bytes
    assert publisher.contract_path.read_bytes() == pre_contract_bytes
    assert publisher.registry_tsx_path.read_bytes() == pre_tsx_bytes

    # 3. Destination template file cleaned up
    dest_src = mock_workspace / "templates" / "elements" / "SpringQuoteCard.tsx"
    assert not dest_src.exists(), "Materialized template source must be removed by rollback"

    # 4. Promotion record persisted as ROLLED_BACK
    records = repo.list_promotion_records(cand.workspace_id, cand.candidate_id)
    assert len(records) == 1
    assert records[0].status == PromotionRecordStatus.ROLLED_BACK
    assert "Simulated post-publish consistency check failure" in (records[0].error_message or "")
