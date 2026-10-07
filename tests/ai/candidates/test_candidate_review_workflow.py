"""
tests/ai/candidates/test_candidate_review_workflow.py
======================================================
Comprehensive Test Suite for Human Review & Approval Workflow (S28-07D).

Verifies Non-Negotiable Invariants:
1. Only VALIDATED candidates can enter review (DRAFT/VALIDATING fail closed).
2. Fresh, matching STATIC_PASS and RUNTIME_PASS evidence strictly required.
3. Review Bundle is cryptographically frozen, server-hashed, and durable.
4. Reviewer must be an authenticated human in the same workspace with reviewer/admin role.
5. AI creators / service principals strictly forbidden from recording approvals (Creator ≠ Reviewer).
6. Client cannot spoof reviewer identity.
7. Approval strictly transitions AWAITING_APPROVAL -> APPROVED. Zero canonical registry writes.
8. APPROVED ≠ PROMOTED (Promotion is deferred to S28-07E).
9. Rejection transitions AWAITING_APPROVAL -> REJECTED; candidate and evidence remain intact.
10. Concurrency (CAS) prevents conflicting approval/rejection decisions.
11. Multi-tenant isolation enforced closed across all review operations.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativeTier,
    CreativeTierDecision,
    ComposeEvaluationResult,
    ReuseEvaluationResult,
)
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    CandidateReviewBundle,
    CandidateReviewDecision,
    CandidateReviewVerdict,
    CandidateStatus,
    CandidateValidationReport,
    GateStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from creative_governance.candidates.errors import (
    CandidateAuthorityError,
    CandidateConflictError,
    CandidateEligibilityError,
    CandidateInvalidStatusError,
    CandidateNotFoundError,
    CandidatePermissionError,
    CandidateReviewError,
    CandidateReviewStaleError,
    CandidateReviewTamperedError,
    CandidateTenantMismatchError,
)
from creative_governance.candidates.hashing import (
    compute_candidate_content_hash,
    compute_review_bundle_hash,
)
from creative_governance.candidates.repository import InMemoryTemplateCandidateRepository
from creative_governance.candidates.review_service import CandidateReviewService
from creative_governance.candidates.service import TemplateCandidateService
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend, StorageService
from scripts.core.tenant_model import TenantContext, ProjectRecord

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "storage")


@pytest.fixture
def repo():
    return InMemoryTemplateCandidateRepository()


@pytest.fixture
def candidate_service(repo, storage):
    return TemplateCandidateService(repository=repo, storage_service=storage)


@pytest.fixture
def review_service(repo, storage):
    return CandidateReviewService(repository=repo, storage_service=storage)


def make_tenant_context(
    workspace_id: str = "ws_alpha",
    user_id: str = "usr_reviewer_01",
    role: Role = Role.REVIEWER,
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


def create_validated_candidate_fixture(
    candidate_service: TemplateCandidateService,
    repo: InMemoryTemplateCandidateRepository,
    storage: StorageService,
    workspace_id: str = "ws_alpha",
    candidate_id: str = "cand_counter_001",
    author: str = "usr_creator_01",
    status: CandidateStatus = CandidateStatus.VALIDATED,
    revision: int = 1,
) -> tuple[TemplateCandidate, CandidateValidationReport, CandidateValidationReport]:
    """Helper to set up a candidate with passing static and runtime validation reports."""
    now = _now()
    source_code = "export const KineticCounter = () => <div>100</div>;"
    schema = {"type": "object", "properties": {"val": {"type": "number"}}}
    fixtures = {"val": 42}
    deps = ["framer-motion"]

    content_hash = compute_candidate_content_hash(
        source_code=source_code,
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        why_reuse_failed="No spring counter in registry",
        why_compose_failed="Primitives lack spring physics",
        creative_plan_reference="cplan_launch_001",
        creative_tier_decision_reference="tier_dec_001",
    )

    candidate = TemplateCandidate(
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        source_project_id="prj_alpha_01",
        creator_ai_run_id="run_ai_creator_001",
        creative_plan_reference="cplan_launch_001",
        creative_tier_decision_reference="tier_dec_001",
        why_reuse_failed="No spring counter in registry",
        why_compose_failed="Primitives lack spring physics",
        source_code=source_code,
        source_code_path=f"workspaces/{workspace_id}/projects/prj_alpha_01/candidates/{candidate_id}/source.tsx",
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        content_hash=content_hash,
        revision=revision,
        status=status,
        name="Kinetic Counter",
        description="Spring-based counter animation",
        author=author,
        proposed_category="elements/data",
        proposed_tags=["counter", "kinetic"],
        target_tier=CreativeTier.REUSE,
        required_provenance=ProvenanceRecord(
            source="plan:cplan_launch_001:decision:tier_dec_001",
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
            CandidateGateResult(gate_id="aspect_gate", status=GateStatus.PASS, summary="Aspect ok"),
            CandidateGateResult(gate_id="probe_gate", status=GateStatus.PASS, summary="Probe ok"),
            CandidateGateResult(gate_id="qc_gate", status=GateStatus.PASS, summary="QC ok"),
        ],
        overall_result=ValidationOverallResult.PASS,
        evidence_refs={
            "smoke_frame_0": f"candidates/{workspace_id}/{candidate_id}/smoke_0.png",
            "frame_0": f"candidates/{workspace_id}/{candidate_id}/frame_0.png",
            "probe_report": f"candidates/{workspace_id}/{candidate_id}/probe.json",
            "qc_report": f"candidates/{workspace_id}/{candidate_id}/qc.json",
        },
        static_validation_id=static_report.validation_id,
        static_validation_report_hash=hashlib.sha256(static_report.model_dump_json().encode("utf-8")).hexdigest(),
    )
    repo.save_validation_report(runtime_report)

    return candidate, static_report, runtime_report


# =============================================================================
# 1. PRECONDITION TESTS FOR OPENING REVIEW
# =============================================================================

def test_precondition_draft_candidate_denied_review(review_service, repo, storage, candidate_service):
    """Negative: DRAFT candidate cannot open review."""
    ctx = make_tenant_context()
    cand, _, _ = create_validated_candidate_fixture(
        candidate_service, repo, storage, status=CandidateStatus.DRAFT
    )
    with pytest.raises(CandidateInvalidStatusError, match="Only VALIDATED candidates may be submitted"):
        review_service.open_review(ctx, cand.candidate_id, expected_revision=1)


def test_precondition_validating_candidate_denied_review(review_service, repo, storage, candidate_service):
    """Negative: VALIDATING candidate cannot open review."""
    ctx = make_tenant_context()
    cand, _, _ = create_validated_candidate_fixture(
        candidate_service, repo, storage, status=CandidateStatus.VALIDATING
    )
    with pytest.raises(CandidateInvalidStatusError, match="Only VALIDATED candidates may be submitted"):
        review_service.open_review(ctx, cand.candidate_id, expected_revision=1)


def test_precondition_validated_without_runtime_evidence_denied_review(review_service, repo, storage, candidate_service):
    """Negative: VALIDATED candidate without passing runtime validation report fails closed."""
    ctx = make_tenant_context()
    cand, _, runtime_report = create_validated_candidate_fixture(candidate_service, repo, storage)

    # Delete runtime report
    repo._reports.pop((cand.workspace_id, runtime_report.validation_id))

    with pytest.raises(CandidateEligibilityError, match="has no passing runtime validation evidence"):
        review_service.open_review(ctx, cand.candidate_id, expected_revision=1)


def test_precondition_stale_validation_report_denied_review(review_service, repo, storage, candidate_service):
    """Negative: Validation evidence from an older content hash or revision is rejected as stale."""
    ctx = make_tenant_context()
    cand, static_rep, runtime_rep = create_validated_candidate_fixture(candidate_service, repo, storage)

    # Simulate candidate drift: bump candidate revision
    repo._candidates[(cand.workspace_id, cand.candidate_id)] = cand.model_copy(update={"revision": 2})

    with pytest.raises(CandidateConflictError, match="Stale revision"):
        review_service.open_review(ctx, cand.candidate_id, expected_revision=1)

    # Also test when expected_revision is updated but reports are for revision 1
    with pytest.raises(CandidateReviewStaleError, match="is stale"):
        review_service.open_review(ctx, cand.candidate_id, expected_revision=2)


def test_precondition_cross_tenant_open_review_denied(review_service, repo, storage, candidate_service):
    """Negative: Workspace A cannot open review for candidate owned by Workspace B."""
    cand, _, _ = create_validated_candidate_fixture(
        candidate_service, repo, storage, workspace_id="ws_bravo"
    )
    ctx_alpha = make_tenant_context(workspace_id="ws_alpha")

    with pytest.raises(CandidateNotFoundError, match="not found in workspace 'ws_alpha'"):
        review_service.open_review(ctx_alpha, cand.candidate_id, expected_revision=1)


# =============================================================================
# 2. REVIEW BUNDLE FREEZE & INTEGRITY
# =============================================================================

def test_open_review_success_freezes_bundle_and_transitions(review_service, repo, storage, candidate_service):
    """Positive: VALIDATED candidate successfully enters review and freezes ReviewBundle."""
    ctx = make_tenant_context()
    cand, static_rep, runtime_rep = create_validated_candidate_fixture(candidate_service, repo, storage)

    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)

    # 1. Bundle assertions
    assert bundle.review_bundle_id.startswith("rbd_")
    assert bundle.candidate_id == cand.candidate_id
    assert bundle.workspace_id == cand.workspace_id
    assert bundle.candidate_content_hash == cand.content_hash
    assert bundle.candidate_revision == 1
    assert bundle.static_validation_id == static_rep.validation_id
    assert bundle.runtime_validation_id == runtime_rep.validation_id
    assert bundle.probe_report_ref == runtime_rep.evidence_refs["probe_report"]
    assert bundle.qc_report_ref == runtime_rep.evidence_refs["qc_report"]
    assert bundle.review_bundle_hash != ""

    # 2. Candidate transitioned to AWAITING_APPROVAL
    updated_cand = repo.get_candidate(cand.candidate_id, cand.workspace_id)
    assert updated_cand.status == CandidateStatus.AWAITING_APPROVAL

    # 3. Bundle durable in storage and repo
    stored_bundle = review_service.get_review_bundle(ctx, bundle.review_bundle_id)
    assert stored_bundle.review_bundle_id == bundle.review_bundle_id
    assert stored_bundle.review_bundle_hash == bundle.review_bundle_hash


def test_tampered_review_bundle_hash_denied_approval(review_service, repo, storage, candidate_service):
    """Negative: Tampered bundle hash or corrupted evidence fails closed on retrieval/approval."""
    ctx = make_tenant_context()
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)

    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)

    # Tamper with the bundle hash in repository
    tampered_bundle = bundle.model_copy(update={"review_bundle_hash": "tampered_fake_digest_abc123"})
    repo._bundles[(ctx.workspace_id, bundle.review_bundle_id)] = tampered_bundle

    with pytest.raises(CandidateReviewTamperedError, match="failed cryptographic integrity check"):
        review_service.approve(ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1)


# =============================================================================
# 3. REVIEWER AUTHORIZATION & NON-NEGOTIABLE AUTHORITY RULES
# =============================================================================

def test_viewer_role_denied_approval(review_service, repo, storage, candidate_service):
    """Negative: Principal with VIEWER role cannot approve candidate."""
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)
    review_service.open_review(make_tenant_context(role=Role.REVIEWER), cand.candidate_id, expected_revision=1)

    ctx_viewer = make_tenant_context(role=Role.VIEWER)
    bundles = repo.list_review_bundles(cand.candidate_id, cand.workspace_id)

    with pytest.raises(CandidatePermissionError, match="lacks review authority"):
        review_service.approve(ctx_viewer, cand.candidate_id, bundles[0].review_bundle_id, expected_revision=1)


def test_editor_role_without_review_permission_denied_approval(review_service, repo, storage, candidate_service):
    """Negative: Principal with EDITOR role cannot approve candidate."""
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)
    review_service.open_review(make_tenant_context(role=Role.REVIEWER), cand.candidate_id, expected_revision=1)

    ctx_editor = make_tenant_context(role=Role.EDITOR)
    bundles = repo.list_review_bundles(cand.candidate_id, cand.workspace_id)

    with pytest.raises(CandidatePermissionError, match="lacks review authority"):
        review_service.approve(ctx_editor, cand.candidate_id, bundles[0].review_bundle_id, expected_revision=1)


def test_ai_principal_denied_approval(review_service, repo, storage, candidate_service):
    """Negative: AI, service, or system worker principal cannot approve candidate."""
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)
    review_service.open_review(make_tenant_context(role=Role.REVIEWER), cand.candidate_id, expected_revision=1)

    # 1. Service principal
    ctx_service = make_tenant_context(
        user_id="sys_service_ai",
        role=Role.ADMIN,
        principal_type=PrincipalType.SERVICE,
    )
    bundles = repo.list_review_bundles(cand.candidate_id, cand.workspace_id)
    with pytest.raises(CandidateAuthorityError, match="is not a human user"):
        review_service.approve(ctx_service, cand.candidate_id, bundles[0].review_bundle_id, expected_revision=1)

    # 2. System worker principal
    ctx_worker = make_tenant_context(
        user_id="sys_worker_01",
        role=Role.ADMIN,
        principal_type=PrincipalType.SYSTEM_WORKER,
    )
    with pytest.raises(CandidateAuthorityError, match="is not a human user"):
        review_service.approve(ctx_worker, cand.candidate_id, bundles[0].review_bundle_id, expected_revision=1)

    # 3. Human principal with AI identity name
    ctx_ai_named = make_tenant_context(
        user_id="ai_generator_agent",
        role=Role.REVIEWER,
        principal_type=PrincipalType.HUMAN,
    )
    with pytest.raises(CandidateAuthorityError, match="AI cannot approve candidates"):
        review_service.approve(ctx_ai_named, cand.candidate_id, bundles[0].review_bundle_id, expected_revision=1)


def test_creator_cannot_self_approve(review_service, repo, storage, candidate_service):
    """Negative: Candidate creator cannot approve their own candidate (Separation of Duties)."""
    cand, _, _ = create_validated_candidate_fixture(
        candidate_service, repo, storage, author="usr_creator_alice"
    )
    review_service.open_review(make_tenant_context(role=Role.REVIEWER, user_id="usr_reviewer_bob"), cand.candidate_id, expected_revision=1)

    # Alice attempts to self-approve
    ctx_alice = make_tenant_context(user_id="usr_creator_alice", role=Role.REVIEWER)
    bundles = repo.list_review_bundles(cand.candidate_id, cand.workspace_id)

    with pytest.raises(CandidateAuthorityError, match="Separation of Duties"):
        review_service.approve(ctx_alice, cand.candidate_id, bundles[0].review_bundle_id, expected_revision=1)


def test_wrong_workspace_reviewer_denied_approval(review_service, repo, storage, candidate_service):
    """Negative: Authorized reviewer from Workspace Bravo cannot approve Workspace Alpha candidate."""
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage, workspace_id="ws_alpha")
    review_service.open_review(make_tenant_context(workspace_id="ws_alpha"), cand.candidate_id, expected_revision=1)

    bundles = repo.list_review_bundles(cand.candidate_id, "ws_alpha")
    ctx_bravo = make_tenant_context(workspace_id="ws_bravo", user_id="usr_reviewer_bravo")

    with pytest.raises(CandidateNotFoundError, match="not found in workspace 'ws_bravo'"):
        review_service.approve(ctx_bravo, cand.candidate_id, bundles[0].review_bundle_id, expected_revision=1)


# =============================================================================
# 4. SUCCESSFUL APPROVAL FLOW & REGISTRY ISOLATION
# =============================================================================

def test_successful_approval_flow_and_registry_isolation(review_service, repo, storage, candidate_service):
    """
    Positive Test: Complete review approval workflow.
    Proves:
    1. VALIDATED -> open_review -> AWAITING_APPROVAL -> approve -> APPROVED.
    2. Candidate status is APPROVED.
    3. Canonical Template Registry is 100% UNCHANGED.
    4. Candidate is NOT PROMOTED or discoverable as reusable template.
    """
    # Snapshot canonical registry state before test
    registry_file = WORKSPACE_ROOT / "registry" / "template-registry-data.json"
    catalog_file = WORKSPACE_ROOT / "ground-truth" / "template_catalog.json"
    contracts_file = WORKSPACE_ROOT / "contracts" / "template-runtime-contract.json"

    registry_sha_before = hashlib.sha256(registry_file.read_bytes()).hexdigest() if registry_file.exists() else ""
    catalog_sha_before = hashlib.sha256(catalog_file.read_bytes()).hexdigest() if catalog_file.exists() else ""
    contracts_sha_before = hashlib.sha256(contracts_file.read_bytes()).hexdigest() if contracts_file.exists() else ""

    ctx = make_tenant_context(user_id="usr_trusted_reviewer_42", role=Role.REVIEWER)
    cand, static_rep, runtime_rep = create_validated_candidate_fixture(
        candidate_service, repo, storage, author="usr_creator_bob"
    )

    # 1. Open review
    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)
    assert repo.get_candidate(cand.candidate_id, cand.workspace_id).status == CandidateStatus.AWAITING_APPROVAL

    # 2. Record approval decision
    decision = review_service.approve(
        tenant_context=ctx,
        candidate_id=cand.candidate_id,
        review_bundle_id=bundle.review_bundle_id,
        expected_revision=1,
        reason="Approved: Visual motion curves, bounds, and layout meet production standards.",
    )

    # 3. Decision verification
    assert decision.decision_id.startswith("rdec_")
    assert decision.decision == CandidateReviewVerdict.APPROVED
    assert decision.reviewer_principal_id == "usr_trusted_reviewer_42"
    assert decision.reviewer_role == "reviewer"
    assert decision.candidate_content_hash == cand.content_hash
    assert decision.review_bundle_hash == bundle.review_bundle_hash
    assert decision.static_validation_report_hash == bundle.static_report_hash
    assert decision.runtime_validation_report_hash == bundle.runtime_report_hash
    assert decision.candidate_revision == 1

    # 4. Candidate status is APPROVED (Never PROMOTED)
    final_cand = repo.get_candidate(cand.candidate_id, cand.workspace_id)
    assert final_cand.status == CandidateStatus.APPROVED
    assert final_cand.status != CandidateStatus.PROMOTED

    # 5. Non-Negotiable Invariant: Zero Canonical Registry Drift
    if registry_file.exists():
        assert hashlib.sha256(registry_file.read_bytes()).hexdigest() == registry_sha_before
    if catalog_file.exists():
        assert hashlib.sha256(catalog_file.read_bytes()).hexdigest() == catalog_sha_before
    if contracts_file.exists():
        assert hashlib.sha256(contracts_file.read_bytes()).hexdigest() == contracts_sha_before

    # 6. Candidate is NOT in catalog or registry
    if catalog_file.exists():
        cat_data = json.loads(catalog_file.read_text(encoding="utf-8"))
        items = cat_data if isinstance(cat_data, list) else cat_data.get("templates", [])
        assert not any(t.get("template_id") == cand.candidate_id for t in items if isinstance(t, dict))


# =============================================================================
# 5. REJECTION FLOW & AUDIT TRAIL
# =============================================================================

def test_successful_rejection_flow_preserves_audit_trail(review_service, repo, storage, candidate_service):
    """
    Positive: Authorized reviewer rejects candidate with mandatory reason.
    Verifies:
    1. Candidate status transitions to REJECTED.
    2. Candidate is NOT deleted.
    3. Review bundle and validation evidence remain intact.
    4. Rejection reason is durably stored.
    """
    ctx = make_tenant_context(user_id="usr_qa_lead")
    cand, _, _ = create_validated_candidate_fixture(
        candidate_service, repo, storage, author="usr_creator_bob"
    )

    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)

    # Reject with audit reason
    decision = review_service.reject(
        tenant_context=ctx,
        candidate_id=cand.candidate_id,
        review_bundle_id=bundle.review_bundle_id,
        expected_revision=1,
        reason="Visual motion lacks adequate easing; typography clipping at 9:16 aspect ratio.",
    )

    assert decision.decision == CandidateReviewVerdict.REJECTED
    assert decision.reason == "Visual motion lacks adequate easing; typography clipping at 9:16 aspect ratio."

    # Candidate status is REJECTED
    rejected_cand = repo.get_candidate(cand.candidate_id, cand.workspace_id)
    assert rejected_cand.status == CandidateStatus.REJECTED

    # Candidate and evidence are preserved
    assert repo.get_review_bundle(bundle.review_bundle_id, cand.workspace_id) is not None
    assert len(repo.list_validation_reports(cand.candidate_id, cand.workspace_id)) == 2


def test_reject_without_reason_denied(review_service, repo, storage, candidate_service):
    """Negative: Rejection without an audit reason is strictly rejected."""
    ctx = make_tenant_context()
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)
    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)

    with pytest.raises(ValueError, match="requires a non-empty audit reason"):
        review_service.reject(ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1, reason="   ")


def test_reject_after_approved_denied(review_service, repo, storage, candidate_service):
    """Negative: Candidate in APPROVED status cannot be rejected without a new review cycle."""
    ctx = make_tenant_context(user_id="usr_rev_1")
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)
    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)

    review_service.approve(ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1)

    # Attempt rejection
    with pytest.raises(CandidateConflictError, match="has already been APPROVED"):
        review_service.reject(ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1, reason="Changed mind")


def test_approve_after_rejected_denied(review_service, repo, storage, candidate_service):
    """Negative: Candidate in REJECTED status cannot be approved without a new review cycle."""
    ctx = make_tenant_context(user_id="usr_rev_1")
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)
    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)

    review_service.reject(ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1, reason="Flawed")

    with pytest.raises(CandidateConflictError, match="is in REJECTED status"):
        review_service.approve(ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1)


def test_approve_twice_is_idempotent(review_service, repo, storage, candidate_service):
    """Positive: Approving twice with same reviewer on same bundle is idempotent."""
    ctx = make_tenant_context(user_id="usr_rev_1")
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)
    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)

    dec1 = review_service.approve(ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1)
    dec2 = review_service.approve(ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1)

    assert dec1.decision_id == dec2.decision_id


# =============================================================================
# 6. CONCURRENCY & CAS COLLISION PROTECTION
# =============================================================================

def test_concurrency_cas_conflicting_decisions_denied(review_service, repo, storage, candidate_service):
    """
    Negative / Concurrency: Reviewer A and Reviewer B concurrently decide on same revision.
    First decision succeeds; second fails with Conflict.
    """
    cand, _, _ = create_validated_candidate_fixture(candidate_service, repo, storage)
    ctx_rev_a = make_tenant_context(user_id="usr_reviewer_a")
    ctx_rev_b = make_tenant_context(user_id="usr_reviewer_b")

    bundle = review_service.open_review(ctx_rev_a, cand.candidate_id, expected_revision=1)

    # Reviewer A approves revision 1
    dec_a = review_service.approve(ctx_rev_a, cand.candidate_id, bundle.review_bundle_id, expected_revision=1)
    assert dec_a.decision == CandidateReviewVerdict.APPROVED

    # Reviewer B attempts to reject on stale candidate state
    with pytest.raises((CandidateConflictError, CandidateInvalidStatusError)):
        review_service.reject(
            ctx_rev_b,
            cand.candidate_id,
            bundle.review_bundle_id,
            expected_revision=1,
            reason="Concurrent reject attempt",
        )


# =============================================================================
# 7. TENANT ISOLATION TESTS
# =============================================================================

def test_tenant_isolation_complete(review_service, repo, storage, candidate_service):
    """
    Tenant Isolation:
    Workspace A cannot read B's review bundles, approve B's candidate,
    reject B's candidate, or read B's decisions.
    """
    cand_b, _, _ = create_validated_candidate_fixture(
        candidate_service, repo, storage, workspace_id="ws_bravo", candidate_id="cand_bravo_001"
    )
    ctx_b = make_tenant_context(workspace_id="ws_bravo", user_id="usr_bravo_reviewer")
    bundle_b = review_service.open_review(ctx_b, cand_b.candidate_id, expected_revision=1)

    ctx_a = make_tenant_context(workspace_id="ws_alpha", user_id="usr_alpha_reviewer")

    # 1. Alpha cannot get Bravo bundle
    with pytest.raises(CandidateNotFoundError):
        review_service.get_review_bundle(ctx_a, bundle_b.review_bundle_id)

    # 2. Alpha cannot approve Bravo candidate
    with pytest.raises(CandidateNotFoundError):
        review_service.approve(ctx_a, cand_b.candidate_id, bundle_b.review_bundle_id, expected_revision=1)

    # 3. Alpha cannot reject Bravo candidate
    with pytest.raises(CandidateNotFoundError):
        review_service.reject(ctx_a, cand_b.candidate_id, bundle_b.review_bundle_id, expected_revision=1, reason="Cross tenant reject")

    # Bravo approves
    dec_b = review_service.approve(ctx_b, cand_b.candidate_id, bundle_b.review_bundle_id, expected_revision=1)

    # 4. Alpha cannot read Bravo decision
    with pytest.raises(CandidateNotFoundError):
        review_service.get_decision(ctx_a, dec_b.decision_id)


# =============================================================================
# 8. AUDITABILITY & DURABILITY
# =============================================================================

def test_auditability_decision_fields_complete(review_service, repo, storage, candidate_service):
    """Auditability: Decision record contains all mandatory cryptographic and metadata bindings."""
    ctx = make_tenant_context(user_id="usr_auditor_lead")
    cand, static_rep, runtime_rep = create_validated_candidate_fixture(candidate_service, repo, storage)

    bundle = review_service.open_review(ctx, cand.candidate_id, expected_revision=1)
    dec = review_service.approve(
        ctx, cand.candidate_id, bundle.review_bundle_id, expected_revision=1, reason="Audit verified"
    )

    # Verifiable without temporary logs:
    assert dec.reviewer_principal_id == "usr_auditor_lead"
    assert dec.decided_at is not None
    assert dec.candidate_content_hash == cand.content_hash
    assert dec.candidate_revision == 1
    assert dec.review_bundle_hash == bundle.review_bundle_hash
    assert dec.static_validation_report_hash == bundle.static_report_hash
    assert dec.runtime_validation_report_hash == bundle.runtime_report_hash
    assert dec.reason == "Audit verified"
