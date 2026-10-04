"""
creative_governance/candidates/review_service.py
===============================
Human Review & Approval Domain Authority for TemplateCandidate (S28-07D).

Invariants & Authority Rules:
1. Validation ≠ Approval: Successful static and runtime gates (VALIDATED) do NOT constitute approval.
2. Approval ≠ Promotion: An APPROVED candidate is NOT promoted, registered, or available for reuse.
3. AI ≠ Reviewer Authority: AI creators, agents, LLMs, and service principals are strictly forbidden
   from approving template candidates. Only authenticated human reviewers may record decisions.
4. Creator ≠ Approver: The entity that generated/authored the candidate cannot approve it (Separation of Duties).
5. Immutable Evidence Binding: Decisions are cryptographically bound to the frozen ReviewBundle hash,
   content hash, candidate revision, and validation report digests.
6. Tenant Isolation: All actions require and enforce TenantContext matching candidate ownership.
7. Anti-Stale Concurrency: Optimistic Concurrency Control (CAS) ensures candidate state has not drifted.
8. Zero Registry Mutation: This service has zero authority or code to mutate the Canonical Template Registry.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.contracts.creative.template_candidate import (
    CandidateReviewBundle,
    CandidateReviewDecision,
    CandidateReviewVerdict,
    CandidateStatus,
    CandidateValidationReport,
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
from creative_governance.candidates.hashing import compute_review_bundle_hash
from creative_governance.candidates.repository import TemplateCandidateRepository
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import (
    StorageService,
    build_storage_key,
)
from scripts.core.tenant_model import TenantContext


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class CandidateReviewService:
    """
    Authoritative domain service governing TemplateCandidate review bundles,
    human evaluation workflows, and approval/rejection decisions (S28-07D).
    """

    def __init__(
        self,
        repository: TemplateCandidateRepository,
        storage_service: StorageService,
    ) -> None:
        self.repository = repository
        self.storage_service = storage_service

    # =========================================================================
    # INTERNAL VERIFICATION HELPERS
    # =========================================================================

    def _verify_workspace_access(self, tenant_context: TenantContext, candidate: TemplateCandidate) -> None:
        """Enforces strict multi-tenant confinement."""
        if candidate.workspace_id != tenant_context.workspace_id:
            raise CandidateNotFoundError(
                f"Candidate '{candidate.candidate_id}' not found in workspace '{tenant_context.workspace_id}'."
            )

    def _verify_human_reviewer_authority(
        self,
        tenant_context: TenantContext,
        candidate: TemplateCandidate,
    ) -> Principal:
        """
        Enforces human reviewer authentication, RBAC permissions, non-AI authority,
        and Separation of Duties (Creator ≠ Approver).
        """
        principal = tenant_context.principal

        # 1. Must be authenticated
        if not principal.is_authenticated:
            raise CandidateAuthorityError("Authentication required to review template candidates.")

        # 2. Must be HUMAN (Principle 3: AI cannot approve)
        if not principal.is_human or principal.principal_type in (
            PrincipalType.SERVICE,
            PrincipalType.SYSTEM_WORKER,
            PrincipalType.ANONYMOUS,
        ):
            raise CandidateAuthorityError(
                f"Principal '{principal.principal_id}' ({principal.principal_type.value}) is not a human user. "
                f"Template candidate approval strictly requires an authenticated human reviewer."
            )

        # Explicit safeguard against known agent / AI names
        rev_lower = principal.principal_id.lower().strip()
        forbidden_actors = {"ai", "agent", "llm", "claude", "gpt", "gpt-4o", "creative_planner", "system-worker"}
        if any(f in rev_lower for f in forbidden_actors):
            raise CandidateAuthorityError(
                f"Principal '{principal.principal_id}' identified as automated agent. AI cannot approve candidates."
            )

        # 3. RBAC: Must possess REVIEWER or ADMIN role
        if tenant_context.role not in (Role.REVIEWER, Role.ADMIN):
            raise CandidatePermissionError(
                f"Principal '{principal.principal_id}' with role '{tenant_context.role.value}' "
                f"lacks review authority. Review operations require 'reviewer' or 'admin' role."
            )

        # 4. Separation of Duties: Creator ≠ Approver
        # If candidate was created by this user or AI run associated with user
        if candidate.author and candidate.author.strip() not in ("", "system"):
            if candidate.author.strip() == principal.principal_id.strip():
                raise CandidateAuthorityError(
                    f"Creator '{candidate.author}' cannot approve their own template candidate (Separation of Duties)."
                )

        return principal

    def _get_verified_validation_evidence(
        self,
        candidate: TemplateCandidate,
        workspace_id: str,
    ) -> tuple[CandidateValidationReport, CandidateValidationReport]:
        """
        Retrieves and verifies passing static and runtime validation reports
        bound exactly to the candidate's current content hash and revision.
        Fails closed if evidence is missing, stale, or incomplete.
        """
        reports = self.repository.list_validation_reports(candidate.candidate_id, workspace_id)

        # Find latest passing static report
        static_reports = [
            r for r in reports
            if r.phase == ValidationPhase.STATIC and r.overall_result == ValidationOverallResult.PASS
        ]
        # Find latest passing runtime report
        runtime_reports = [
            r for r in reports
            if r.phase == ValidationPhase.RUNTIME and r.overall_result == ValidationOverallResult.PASS
        ]

        if not static_reports:
            raise CandidateEligibilityError(
                f"Candidate '{candidate.candidate_id}' has no passing static validation evidence (STATIC_PASS required)."
            )
        if not runtime_reports:
            raise CandidateEligibilityError(
                f"Candidate '{candidate.candidate_id}' has no passing runtime validation evidence (RUNTIME_PASS required)."
            )

        latest_static = static_reports[-1]
        latest_runtime = runtime_reports[-1]

        # Verify static report matches current candidate snapshot
        if (
            latest_static.candidate_content_hash != candidate.content_hash
            or latest_static.candidate_revision != candidate.revision
        ):
            raise CandidateReviewStaleError(
                f"Static validation report '{latest_static.validation_id}' is stale. "
                f"Report hash {latest_static.candidate_content_hash[:8]} vs current {candidate.content_hash[:8]}."
            )

        # Verify runtime report matches current candidate snapshot
        if (
            latest_runtime.candidate_content_hash != candidate.content_hash
            or latest_runtime.candidate_revision != candidate.revision
        ):
            raise CandidateReviewStaleError(
                f"Runtime validation report '{latest_runtime.validation_id}' is stale. "
                f"Report hash {latest_runtime.candidate_content_hash[:8]} vs current {candidate.content_hash[:8]}."
            )

        # Verify cross-reference link
        if latest_runtime.static_validation_id and latest_runtime.static_validation_id != latest_static.validation_id:
            raise CandidateReviewStaleError(
                f"Runtime validation report references static validation '{latest_runtime.static_validation_id}', "
                f"which does not match current static validation '{latest_static.validation_id}'."
            )

        return latest_static, latest_runtime

    # =========================================================================
    # 1. REVIEW BUNDLE FREEZE & TRANSITION TO AWAITING_APPROVAL
    # =========================================================================

    def open_review(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        expected_revision: int,
    ) -> CandidateReviewBundle:
        """
        Creates an immutable, canonical ReviewBundle freezing all validation evidence,
        and transitions candidate lifecycle state from VALIDATED to AWAITING_APPROVAL.

        Preconditions:
        - Candidate must be in VALIDATED status.
        - Verified, fresh STATIC_PASS and RUNTIME_PASS evidence must exist.
        - Tenant authorization must succeed.
        - CAS expected revision must succeed.
        """
        workspace_id = tenant_context.workspace_id

        # 1. Role verification for opening review: reviewer or admin
        if tenant_context.role not in (Role.REVIEWER, Role.ADMIN):
            raise CandidatePermissionError(
                f"Role '{tenant_context.role.value}' lacks permission to open review for candidates."
            )

        # 2. Fetch candidate
        candidate = self.repository.get_candidate(candidate_id, workspace_id)
        if not candidate:
            raise CandidateNotFoundError(f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'.")

        self._verify_workspace_access(tenant_context, candidate)

        # 3. Precondition: status must be strictly VALIDATED (or idempotent return if already AWAITING_APPROVAL)
        if candidate.status != CandidateStatus.VALIDATED:
            if candidate.status == CandidateStatus.AWAITING_APPROVAL:
                active_bundle = self.get_active_review_bundle_for_candidate(tenant_context, candidate_id)
                if active_bundle:
                    return active_bundle
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{candidate.status.value}'. "
                f"Only VALIDATED candidates may be submitted for human review."
            )

        # 4. CAS check
        if candidate.revision != expected_revision:
            raise CandidateConflictError(
                f"Stale revision on candidate '{candidate_id}': expected {expected_revision}, got {candidate.revision}."
            )

        # 5. Fetch verified static and runtime evidence
        static_report, runtime_report = self._get_verified_validation_evidence(candidate, workspace_id)

        # 6. Compute component hashes for cryptographic freeze
        # If source_code was not in memory, read from StorageService
        source_code = candidate.source_code
        if not source_code and "source_code" in candidate.storage_keys:
            try:
                source_code = self.storage_service.get(candidate.storage_keys["source_code"]).decode("utf-8")
            except Exception:
                source_code = ""

        source_code_hash = hashlib.sha256((source_code or "").encode("utf-8")).hexdigest()
        schema_hash = hashlib.sha256(
            json.dumps(candidate.template_schema or {}, sort_keys=True, separators=(',', ':')).encode("utf-8")
        ).hexdigest()
        fixtures_hash = hashlib.sha256(
            json.dumps(candidate.fixtures or {}, sort_keys=True, separators=(',', ':')).encode("utf-8")
        ).hexdigest()
        static_report_hash = hashlib.sha256(static_report.model_dump_json().encode("utf-8")).hexdigest()
        runtime_report_hash = hashlib.sha256(runtime_report.model_dump_json().encode("utf-8")).hexdigest()

        # Extract representative frame references
        evidence_refs = dict(runtime_report.evidence_refs or {})
        rep_frame_refs = sorted([
            v for k, v in evidence_refs.items()
            if "frame" in k or k.startswith("probe_frame")
        ])
        probe_ref = evidence_refs.get("probe_report")
        qc_ref = evidence_refs.get("qc_report")

        review_bundle_id = f"rbd_{uuid.uuid4().hex[:12]}"
        now = _now_utc()
        policy_version = "1.0.0"

        # Compute deterministic bundle digest
        review_bundle_hash = compute_review_bundle_hash(
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            candidate_content_hash=candidate.content_hash,
            candidate_revision=candidate.revision,
            static_validation_id=static_report.validation_id,
            runtime_validation_id=runtime_report.validation_id,
            static_report_hash=static_report_hash,
            runtime_report_hash=runtime_report_hash,
            render_evidence_refs=evidence_refs,
            representative_frame_refs=rep_frame_refs,
            probe_report_ref=probe_ref,
            qc_report_ref=qc_ref,
            source_code_hash=source_code_hash,
            schema_hash=schema_hash,
            fixtures_hash=fixtures_hash,
            review_policy_version=policy_version,
        )

        bundle = CandidateReviewBundle(
            review_bundle_id=review_bundle_id,
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            candidate_content_hash=candidate.content_hash,
            candidate_revision=candidate.revision,
            static_validation_id=static_report.validation_id,
            runtime_validation_id=runtime_report.validation_id,
            static_report_hash=static_report_hash,
            runtime_report_hash=runtime_report_hash,
            render_evidence_refs=evidence_refs,
            representative_frame_refs=rep_frame_refs,
            probe_report_ref=probe_ref,
            qc_report_ref=qc_ref,
            source_code_hash=source_code_hash,
            schema_hash=schema_hash,
            fixtures_hash=fixtures_hash,
            created_at=now,
            review_policy_version=policy_version,
            review_bundle_hash=review_bundle_hash,
        )

        # 7. Persist bundle in durable storage and repository
        bundle_key = build_storage_key(
            workspace_id,
            candidate.source_project_id or "default",
            "candidates",
            candidate.candidate_id,
            f"review_{review_bundle_id}_bundle.json",
        )
        self.storage_service.put(
            bundle_key,
            bundle.model_dump_json().encode("utf-8"),
            content_type="application/json",
        )
        saved_bundle = self.repository.save_review_bundle(bundle)

        # 8. Transition candidate to AWAITING_APPROVAL via CAS
        self.repository.update_candidate_status_cas(
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            status=CandidateStatus.AWAITING_APPROVAL,
            expected_revision=expected_revision,
        )

        return saved_bundle

    # =========================================================================
    # 2. QUERY REVIEW BUNDLE
    # =========================================================================

    def get_review_bundle(
        self,
        tenant_context: TenantContext,
        review_bundle_id: str,
    ) -> CandidateReviewBundle:
        """
        Retrieves a ReviewBundle by ID scoped strictly to caller's workspace,
        verifying bundle integrity.
        """
        workspace_id = tenant_context.workspace_id
        bundle = self.repository.get_review_bundle(review_bundle_id, workspace_id)
        if not bundle:
            raise CandidateNotFoundError(
                f"Review bundle '{review_bundle_id}' not found in workspace '{workspace_id}'."
            )

        # Verify bundle integrity
        recomputed_hash = compute_review_bundle_hash(
            candidate_id=bundle.candidate_id,
            workspace_id=bundle.workspace_id,
            candidate_content_hash=bundle.candidate_content_hash,
            candidate_revision=bundle.candidate_revision,
            static_validation_id=bundle.static_validation_id,
            runtime_validation_id=bundle.runtime_validation_id,
            static_report_hash=bundle.static_report_hash,
            runtime_report_hash=bundle.runtime_report_hash,
            render_evidence_refs=bundle.render_evidence_refs,
            representative_frame_refs=bundle.representative_frame_refs,
            probe_report_ref=bundle.probe_report_ref,
            qc_report_ref=bundle.qc_report_ref,
            source_code_hash=bundle.source_code_hash,
            schema_hash=bundle.schema_hash,
            fixtures_hash=bundle.fixtures_hash,
            review_policy_version=bundle.review_policy_version,
        )
        if bundle.review_bundle_hash != recomputed_hash:
            raise CandidateReviewTamperedError(
                f"Review bundle '{review_bundle_id}' failed cryptographic integrity check."
            )

        return bundle

    def get_active_review_bundle_for_candidate(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
    ) -> Optional[CandidateReviewBundle]:
        """Returns the most recent ReviewBundle for a candidate in the workspace."""
        workspace_id = tenant_context.workspace_id
        bundles = self.repository.list_review_bundles(candidate_id, workspace_id)
        return bundles[-1] if bundles else None

    # =========================================================================
    # 3. APPROVAL DECISION
    # =========================================================================

    def approve(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        review_bundle_id: str,
        expected_revision: int,
        reason: Optional[str] = None,
    ) -> CandidateReviewDecision:
        """
        Records a trusted human review APPROVAL decision.
        Transitions candidate state from AWAITING_APPROVAL to APPROVED.

        Guarantees:
        - Only authenticated human reviewer can approve.
        - AI is strictly prohibited from approving.
        - Separation of duties: Creator cannot approve.
        - Review bundle must match current candidate snapshot and validation evidence.
        - Idempotent on identical reviewer approval; conflicts on conflicting decision.
        - ZERO Registry mutation or promotion invocation.
        """
        workspace_id = tenant_context.workspace_id

        # 1. Fetch candidate
        candidate = self.repository.get_candidate(candidate_id, workspace_id)
        if not candidate:
            raise CandidateNotFoundError(f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'.")

        self._verify_workspace_access(tenant_context, candidate)

        # 2. Verify human reviewer authority and separation of duties
        principal = self._verify_human_reviewer_authority(tenant_context, candidate)

        # 3. Lifecycle state check: must be AWAITING_APPROVAL
        if candidate.status != CandidateStatus.AWAITING_APPROVAL:
            if candidate.status == CandidateStatus.APPROVED:
                # Check for idempotent return if already approved with same bundle & reviewer
                existing_decision = self.repository.get_active_decision_for_bundle(review_bundle_id, workspace_id)
                if (
                    existing_decision
                    and existing_decision.decision == CandidateReviewVerdict.APPROVED
                    and existing_decision.reviewer_principal_id == principal.principal_id
                ):
                    return existing_decision
                raise CandidateConflictError(
                    f"Candidate '{candidate_id}' is already APPROVED."
                )
            if candidate.status == CandidateStatus.REJECTED:
                raise CandidateConflictError(
                    f"Candidate '{candidate_id}' is in REJECTED status. Cannot approve without a new review cycle."
                )
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{candidate.status.value}'. "
                f"Only candidates in AWAITING_APPROVAL can be approved."
            )

        # 4. CAS check
        if candidate.revision != expected_revision:
            raise CandidateConflictError(
                f"Stale revision on candidate '{candidate_id}': expected {expected_revision}, got {candidate.revision}."
            )

        # 5. Review bundle integrity and binding check
        bundle = self.get_review_bundle(tenant_context, review_bundle_id)
        if bundle.candidate_id != candidate.candidate_id:
            raise CandidateEligibilityError(
                f"Review bundle '{review_bundle_id}' is bound to candidate '{bundle.candidate_id}', not '{candidate_id}'."
            )

        # Anti-stale: bundle must match candidate snapshot exactly
        if (
            bundle.candidate_content_hash != candidate.content_hash
            or bundle.candidate_revision != candidate.revision
        ):
            raise CandidateReviewStaleError(
                f"Review bundle '{review_bundle_id}' is stale. Candidate snapshot drifted."
            )

        # Check validation evidence is still valid and unchanged
        static_report, runtime_report = self._get_verified_validation_evidence(candidate, workspace_id)
        if static_report.validation_id != bundle.static_validation_id:
            raise CandidateReviewStaleError("Static validation evidence has been replaced since review freeze.")
        if runtime_report.validation_id != bundle.runtime_validation_id:
            raise CandidateReviewStaleError("Runtime validation evidence has been replaced since review freeze.")

        # 6. Check existing decisions for this review bundle (conflict protection)
        existing_decision = self.repository.get_active_decision_for_bundle(review_bundle_id, workspace_id)
        if existing_decision:
            if (
                existing_decision.decision == CandidateReviewVerdict.APPROVED
                and existing_decision.reviewer_principal_id == principal.principal_id
            ):
                return existing_decision
            raise CandidateConflictError(
                f"A decision has already been recorded for review bundle '{review_bundle_id}' "
                f"(verdict: {existing_decision.decision.value} by {existing_decision.reviewer_principal_id})."
            )

        # 7. Create append-only CandidateReviewDecision
        decision_id = f"rdec_{uuid.uuid4().hex[:12]}"
        now = _now_utc()
        effective_role = tenant_context.role.value
        audit_reason = (reason or "").strip() or f"Candidate approved by human reviewer '{principal.principal_id}'"

        decision = CandidateReviewDecision(
            decision_id=decision_id,
            review_bundle_id=bundle.review_bundle_id,
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            decision=CandidateReviewVerdict.APPROVED,
            reviewer_principal_id=principal.principal_id,
            reviewer_role=effective_role,
            reason=audit_reason,
            candidate_content_hash=candidate.content_hash,
            candidate_revision=candidate.revision,
            review_bundle_hash=bundle.review_bundle_hash,
            static_validation_report_hash=bundle.static_report_hash,
            runtime_validation_report_hash=bundle.runtime_report_hash,
            render_evidence_ref=bundle.probe_report_ref,
            qc_report_ref=bundle.qc_report_ref,
            decided_at=now,
            decision_revision=1,
        )

        # 8. Persist decision in storage and repository
        decision_key = build_storage_key(
            workspace_id,
            candidate.source_project_id or "default",
            "candidates",
            candidate.candidate_id,
            f"decision_{decision_id}.json",
        )
        self.storage_service.put(
            decision_key,
            decision.model_dump_json().encode("utf-8"),
            content_type="application/json",
        )
        saved_decision = self.repository.save_review_decision(decision)

        # 9. Transition candidate status to APPROVED via CAS
        self.repository.update_candidate_status_cas(
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            status=CandidateStatus.APPROVED,
            expected_revision=expected_revision,
        )

        # Strict Authority Guard: Zero registry writes, zero promotion calls.
        return saved_decision

    # =========================================================================
    # 4. REJECTION DECISION
    # =========================================================================

    def reject(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        review_bundle_id: str,
        expected_revision: int,
        reason: str,
    ) -> CandidateReviewDecision:
        """
        Records a trusted human review REJECTION decision.
        Transitions candidate state from AWAITING_APPROVAL to REJECTED.

        Guarantees:
        - Only authorized human reviewer can reject.
        - Audit reason is mandatory.
        - Existing candidate and validation evidence remain intact (not deleted).
        - Idempotent on identical reviewer rejection; conflicts if already approved.
        """
        workspace_id = tenant_context.workspace_id

        # Mandatory audit reason check
        if not reason or not reason.strip():
            raise ValueError("Rejection decision requires a non-empty audit reason.")

        # 1. Fetch candidate
        candidate = self.repository.get_candidate(candidate_id, workspace_id)
        if not candidate:
            raise CandidateNotFoundError(f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'.")

        self._verify_workspace_access(tenant_context, candidate)

        # 2. Verify human reviewer authority
        principal = self._verify_human_reviewer_authority(tenant_context, candidate)

        # 3. Lifecycle state check: must be AWAITING_APPROVAL
        if candidate.status != CandidateStatus.AWAITING_APPROVAL:
            if candidate.status == CandidateStatus.APPROVED:
                raise CandidateConflictError(
                    f"Candidate '{candidate_id}' has already been APPROVED. Cannot reject an approved candidate."
                )
            if candidate.status == CandidateStatus.REJECTED:
                # Idempotent return if already rejected by same reviewer
                existing_decision = self.repository.get_active_decision_for_bundle(review_bundle_id, workspace_id)
                if (
                    existing_decision
                    and existing_decision.decision == CandidateReviewVerdict.REJECTED
                    and existing_decision.reviewer_principal_id == principal.principal_id
                ):
                    return existing_decision
                raise CandidateConflictError(
                    f"Candidate '{candidate_id}' is already REJECTED."
                )
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{candidate.status.value}'. "
                f"Only candidates in AWAITING_APPROVAL can be rejected."
            )

        # 4. CAS check
        if candidate.revision != expected_revision:
            raise CandidateConflictError(
                f"Stale revision on candidate '{candidate_id}': expected {expected_revision}, got {candidate.revision}."
            )

        # 5. Review bundle integrity check
        bundle = self.get_review_bundle(tenant_context, review_bundle_id)
        if bundle.candidate_id != candidate.candidate_id:
            raise CandidateEligibilityError(
                f"Review bundle '{review_bundle_id}' is bound to candidate '{bundle.candidate_id}', not '{candidate_id}'."
            )

        # 6. Check existing decisions
        existing_decision = self.repository.get_active_decision_for_bundle(review_bundle_id, workspace_id)
        if existing_decision:
            if (
                existing_decision.decision == CandidateReviewVerdict.REJECTED
                and existing_decision.reviewer_principal_id == principal.principal_id
            ):
                return existing_decision
            raise CandidateConflictError(
                f"A decision has already been recorded for review bundle '{review_bundle_id}'."
            )

        # 7. Create append-only CandidateReviewDecision
        decision_id = f"rdec_{uuid.uuid4().hex[:12]}"
        now = _now_utc()
        effective_role = tenant_context.role.value

        decision = CandidateReviewDecision(
            decision_id=decision_id,
            review_bundle_id=bundle.review_bundle_id,
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            decision=CandidateReviewVerdict.REJECTED,
            reviewer_principal_id=principal.principal_id,
            reviewer_role=effective_role,
            reason=reason.strip(),
            candidate_content_hash=candidate.content_hash,
            candidate_revision=candidate.revision,
            review_bundle_hash=bundle.review_bundle_hash,
            static_validation_report_hash=bundle.static_report_hash,
            runtime_validation_report_hash=bundle.runtime_report_hash,
            render_evidence_ref=bundle.probe_report_ref,
            qc_report_ref=bundle.qc_report_ref,
            decided_at=now,
            decision_revision=1,
        )

        # 8. Persist decision in storage and repository
        decision_key = build_storage_key(
            workspace_id,
            candidate.source_project_id or "default",
            "candidates",
            candidate.candidate_id,
            f"decision_{decision_id}.json",
        )
        self.storage_service.put(
            decision_key,
            decision.model_dump_json().encode("utf-8"),
            content_type="application/json",
        )
        saved_decision = self.repository.save_review_decision(decision)

        # 9. Transition candidate status to REJECTED via CAS (candidate is NOT deleted)
        self.repository.update_candidate_status_cas(
            candidate_id=candidate.candidate_id,
            workspace_id=workspace_id,
            status=CandidateStatus.REJECTED,
            expected_revision=expected_revision,
        )

        return saved_decision

    # =========================================================================
    # 5. QUERY DECISIONS
    # =========================================================================

    def get_decision(
        self,
        tenant_context: TenantContext,
        decision_id: str,
    ) -> Optional[CandidateReviewDecision]:
        """Retrieves a single review decision scoped strictly to caller's workspace."""
        workspace_id = tenant_context.workspace_id
        decision = self.repository.get_review_decision(decision_id, workspace_id)
        if not decision:
            raise CandidateNotFoundError(
                f"Review decision '{decision_id}' not found in workspace '{workspace_id}'."
            )
        return decision

    def list_decisions(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
    ) -> List[CandidateReviewDecision]:
        """Lists all review decisions for a candidate scoped strictly to caller's workspace."""
        workspace_id = tenant_context.workspace_id
        return self.repository.list_review_decisions(candidate_id, workspace_id)
