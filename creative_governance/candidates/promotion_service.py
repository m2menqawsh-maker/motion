"""
creative_governance/candidates/promotion_service.py
==================================
Canonical Promotion Domain Authority for TemplateCandidate (S28-07E).

Invariants & Authority Rules:
1. Validation ≠ Approval: Machine validation qualifies candidates; only humans can approve.
2. Approval ≠ Promotion: An APPROVED candidate is NOT registered or reusable until promoted.
3. PromotionService = Sole Promotion Authority: No other layer can set CandidateStatus.PROMOTED
   or publish templates to the canonical registry.
4. AI ≠ Promotion Authority: AI agents, LLMs, and service principals are strictly forbidden
   from triggering promotion.
5. Strict RBAC: Promotion requires authenticated Principal with Role.ADMIN or Action.TEMPLATE_PROMOTE.
   VIEWER, EDITOR, and REVIEWER-only roles are strictly denied.
6. Tenant Isolation: All actions require and enforce TenantContext matching candidate ownership.
7. Cryptographic Reverification: Preflight verifies static pass, runtime pass, review bundle digest,
   and approval decision hashes against current candidate bytes.
8. Preflight Zero-Mutation: Any precondition or identity failure aborts before touching canonical files.
9. Staged Publication & Atomic Rollback: Publication is fully prepared in isolated staging; any failure
   triggers rollback journal restoring exact prior canonical state.
10. Idempotency: Retrying promotion with the exact same candidate snapshot and target identity returns
    the existing PromotionRecord without duplicate artifacts or registry divergence.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from creative_governance.candidates.errors import (
    CandidateConflictError,
    CandidateInvalidStatusError,
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
    compute_promotion_manifest_hash,
    compute_review_bundle_hash,
)
from creative_governance.candidates.policies import FORBIDDEN_DEPENDENCY_PACKAGES
from creative_governance.candidates.repository import TemplateCandidateRepository
from ai.contracts.creative.template_candidate import (
    CandidatePromotionRecord,
    CandidateReviewVerdict,
    CandidateStatus,
    PromotionManifest,
    PromotionRecordStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from scripts.core.security.permissions import Action, ROLE_PERMISSIONS_MATRIX
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import StorageService
from scripts.core.tenant_model import TenantContext
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.core.template_registry_publisher import (
        RollbackJournal,
        StagedPublication,
        TemplateRegistryPublisher,
    )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PromotionService:
    """
    Authoritative domain service orchestrating the safe promotion of APPROVED
    TemplateCandidates into the Canonical Template Registry (S28-07E).
    """

    def __init__(
        self,
        repository: TemplateCandidateRepository,
        storage_service: StorageService,
        registry_publisher: Optional[Any] = None,
    ) -> None:
        self.repository = repository
        self.storage_service = storage_service
        if registry_publisher is None:
            from scripts.core.template_registry_publisher import TemplateRegistryPublisher
            registry_publisher = TemplateRegistryPublisher()
        self.publisher = registry_publisher

    # =========================================================================
    # AUTHORIZATION & PRECONDITIONS
    # =========================================================================

    def _verify_promotion_authority(
        self, tenant_context: TenantContext, candidate: TemplateCandidate
    ) -> Principal:
        """
        Enforces human administrator / promotion authority, RBAC permissions,
        anti-AI rules, and tenant confinement.
        """
        principal = tenant_context.principal

        # 1. Must be authenticated
        if not principal.is_authenticated:
            raise PromotionSecurityError("Unauthenticated caller cannot promote template candidates.")

        # 2. Strict AI Prohibitions (AI ≠ Promotion Authority)
        if not principal.is_human or principal.principal_type in (
            PrincipalType.SERVICE,
            PrincipalType.SYSTEM_WORKER,
            PrincipalType.ANONYMOUS,
        ):
            raise PromotionSecurityError(
                f"Principal '{principal.principal_id}' ({principal.principal_type.value}) is not a human user. "
                f"Promotion requires explicit human administrator authority."
            )

        forbidden_names = {
            "ai", "agent", "llm", "claude", "gpt", "gpt-4o",
            "creative_planner", "anonymous", "system-worker",
        }
        rev_lower = principal.principal_id.lower().strip()
        if any(f in rev_lower for f in forbidden_names):
            raise PromotionSecurityError(
                f"Identity '{principal.principal_id}' is forbidden from authorizing template promotion."
            )

        # 3. RBAC Enforcement: Must have Role.ADMIN or Action.TEMPLATE_PROMOTE
        has_admin_role = (
            Role.ADMIN in principal.roles or tenant_context.role == Role.ADMIN or principal.is_admin
        )
        has_promote_action = any(
            Action.TEMPLATE_PROMOTE in ROLE_PERMISSIONS_MATRIX.get(r, set())
            for r in (principal.roles | {tenant_context.role})
        )

        if not (has_admin_role or has_promote_action):
            raise CandidatePermissionError(
                f"Principal '{principal.principal_id}' with role '{tenant_context.role.value}' "
                f"lacks required permission '{Action.TEMPLATE_PROMOTE.value}'."
            )

        # 4. Multi-Tenant Boundary: Caller must belong to candidate's workspace
        if candidate.workspace_id != tenant_context.workspace_id:
            raise CandidateNotFoundError(
                f"Candidate '{candidate.candidate_id}' not found in workspace '{tenant_context.workspace_id}'."
            )

        return principal

    def _resolve_source_code(self, candidate: TemplateCandidate) -> str:
        """Loads and verifies candidate source code from storage or entity."""
        source_code = candidate.source_code
        if not source_code:
            source_key = (
                candidate.storage_keys.get("source")
                or candidate.storage_keys.get("source_code")
                or candidate.source_code_path
            )
            if source_key:
                try:
                    raw_bytes = self.storage_service.get(source_key)
                    source_code = raw_bytes.decode("utf-8") if isinstance(raw_bytes, bytes) else str(raw_bytes)
                except Exception as e:
                    raise PromotionPreconditionError(f"Failed to load candidate source from storage key '{source_key}': {e}")

        if not source_code or not source_code.strip():
            raise PromotionPreconditionError(f"Candidate '{candidate.candidate_id}' has empty source code.")
        return source_code

    # =========================================================================
    # CORE PROMOTION ORCHESTRATION
    # =========================================================================

    def promote_candidate(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        target_template_id: str,
        expected_revision: int,
        target_template_version: str = "1.0.0",
        promotion_policy_version: str = "1.0.0",
    ) -> CandidatePromotionRecord:
        """
        Orchestrates full candidate promotion:
        1. Preconditions verification & RBAC check.
        2. Idempotency evaluation.
        3. Preflight check (zero mutation).
        4. PromotionManifest freeze.
        5. Isolated staging publication.
        6. Staged consistency check.
        7. Atomic canonical commit with rollback journal.
        8. Live post-publish verification.
        9. Status transition: APPROVED → PROMOTED via CAS.
        10. Durable CandidatePromotionRecord persistence.
        """
        workspace_id = tenant_context.workspace_id
        candidate = self.repository.get_candidate(candidate_id, workspace_id)
        if not candidate:
            raise CandidateNotFoundError(f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'.")

        # 0. CAS Expected Revision Check
        if candidate.revision != expected_revision:
            raise CandidateConflictError(
                f"Candidate '{candidate_id}' revision conflict: expected {expected_revision}, got {candidate.revision}."
            )

        # 1. Authority & Tenant Check
        principal = self._verify_promotion_authority(tenant_context, candidate)

        # 2. Check Candidate Status & Idempotency
        if candidate.status != CandidateStatus.APPROVED:
            if candidate.status == CandidateStatus.PROMOTED:
                existing_record = self.repository.get_promotion_record_by_candidate(candidate_id, workspace_id)
                if existing_record and existing_record.status == PromotionRecordStatus.COMMITTED:
                    if existing_record.target_template_id == target_template_id:
                        # Safe idempotent return
                        return existing_record
                    else:
                        raise CandidateConflictError(
                            f"Candidate '{candidate_id}' already promoted as template '{existing_record.target_template_id}'."
                        )
            raise PromotionPreconditionError(
                f"Candidate '{candidate_id}' is in status '{candidate.status.value}'. "
                f"Candidate status must be 'APPROVED' for promotion."
            )

        # 2.5 Idempotency Check for APPROVED candidate (in case retry happened)
        existing_record = self.repository.get_promotion_record_by_candidate(candidate_id, workspace_id)
        if existing_record and existing_record.status == PromotionRecordStatus.COMMITTED:
            if existing_record.target_template_id == target_template_id:
                return existing_record
            else:
                raise CandidateConflictError(
                    f"Candidate '{candidate_id}' already promoted as template '{existing_record.target_template_id}'."
                )

        # 2.6 Target Template Identity Preflight Check
        self.publisher.validate_target_identity(target_template_id)

        # 3. Retrieve and Reverifiy Approval Decision
        decisions = self.repository.list_review_decisions(candidate_id, workspace_id)
        decision = decisions[-1] if decisions else None
        if not decision:
            raise PromotionPreconditionError(
                f"No authoritative human review decision found for candidate '{candidate_id}'."
            )
        if decision.decision != CandidateReviewVerdict.APPROVED:
            raise PromotionPreconditionError(
                f"Authoritative review decision is '{decision.decision.value}', not 'APPROVED'."
            )
        if decision.candidate_content_hash != candidate.content_hash:
            raise PromotionTamperedError(
                f"Candidate content hash mismatch: candidate has {candidate.content_hash[:8]}, decision has {decision.candidate_content_hash[:8]}."
            )
        if decision.candidate_revision != candidate.revision:
            raise PromotionTamperedError(
                f"Candidate revision mismatch: candidate has {candidate.revision}, decision has {decision.candidate_revision}."
            )

        # 4. Retrieve and Reverifiy Review Bundle
        bundle = self.repository.get_review_bundle(decision.review_bundle_id, workspace_id)
        if not bundle:
            raise PromotionPreconditionError(
                f"Review bundle '{decision.review_bundle_id}' not found in workspace."
            )
        if bundle.review_bundle_hash != decision.review_bundle_hash:
            raise PromotionTamperedError(
                f"Review bundle hash mismatch: bundle has {bundle.review_bundle_hash[:8]}, decision has {decision.review_bundle_hash[:8]}."
            )

        recomputed_bundle_hash = compute_review_bundle_hash(
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
        if recomputed_bundle_hash != bundle.review_bundle_hash:
            raise PromotionTamperedError("Review bundle cryptographic digest mismatch or tampering detected.")

        # 5. Reverifiy Static and Runtime Validation Reports
        static_report = self.repository.get_validation_report(bundle.static_validation_id, workspace_id)
        if not static_report or static_report.overall_result != ValidationOverallResult.PASS:
            raise PromotionPreconditionError("Passing static validation report missing or invalid.")
        if static_report.candidate_content_hash != candidate.content_hash or static_report.candidate_revision != candidate.revision:
            raise PromotionTamperedError("Static validation report drifted from candidate snapshot.")
        computed_static_hash = hashlib.sha256(static_report.model_dump_json().encode("utf-8")).hexdigest()
        if computed_static_hash != bundle.static_report_hash:
            raise PromotionTamperedError("Static validation report tampered or drifted from review bundle.")

        runtime_report = self.repository.get_validation_report(bundle.runtime_validation_id, workspace_id)
        if not runtime_report or runtime_report.overall_result != ValidationOverallResult.PASS:
            raise PromotionPreconditionError("Passing runtime validation report missing or invalid.")
        if runtime_report.candidate_content_hash != candidate.content_hash or runtime_report.candidate_revision != candidate.revision:
            raise PromotionTamperedError("Runtime validation report drifted from candidate snapshot.")
        computed_runtime_hash = hashlib.sha256(runtime_report.model_dump_json().encode("utf-8")).hexdigest()
        if computed_runtime_hash != bundle.runtime_report_hash:
            raise PromotionTamperedError("Runtime validation report tampered or drifted from review bundle.")

        # 6. Resolve and Reverifiy Source Code & Schema
        source_code = self._resolve_source_code(candidate)
        actual_source_hash = hashlib.sha256((source_code or "").encode("utf-8")).hexdigest()
        if actual_source_hash != bundle.source_code_hash:
            raise PromotionTamperedError(
                f"Approved source code hash mismatch: expected {bundle.source_code_hash[:8]}, got {actual_source_hash[:8]}"
            )

        actual_schema_hash = hashlib.sha256(
            json.dumps(candidate.template_schema, sort_keys=True, separators=(',', ':')).encode("utf-8")
        ).hexdigest()
        if actual_schema_hash != bundle.schema_hash:
            raise PromotionTamperedError("Approved schema hash mismatch or tampering detected.")

        # 7. Check Dependency Policy
        for dep in candidate.dependencies:
            dep_clean = str(dep).strip().lower()
            if dep_clean in FORBIDDEN_DEPENDENCY_PACKAGES:
                raise PromotionSecurityError(f"Candidate uses forbidden dependency '{dep}'.")

        # 8. Deterministic Manifest Calculation
        temp_promotion_id = f"prom_{uuid.uuid4().hex[:12]}"
        manifest_hash = compute_promotion_manifest_hash(
            promotion_id=temp_promotion_id,
            candidate_id=candidate.candidate_id,
            workspace_id=candidate.workspace_id,
            candidate_content_hash=candidate.content_hash,
            candidate_revision=candidate.revision,
            approval_decision_id=decision.decision_id,
            review_bundle_id=bundle.review_bundle_id,
            review_bundle_hash=bundle.review_bundle_hash,
            static_validation_id=bundle.static_validation_id,
            runtime_validation_id=bundle.runtime_validation_id,
            target_template_id=target_template_id,
            target_template_version=target_template_version,
            source_code_hash=bundle.source_code_hash,
            schema_hash=bundle.schema_hash,
            promotion_policy_version=promotion_policy_version,
        )

        # 11. Freeze Promotion Manifest
        manifest = PromotionManifest(
            promotion_id=temp_promotion_id,
            candidate_id=candidate.candidate_id,
            workspace_id=candidate.workspace_id,
            candidate_content_hash=candidate.content_hash,
            candidate_revision=candidate.revision,
            approval_decision_id=decision.decision_id,
            review_bundle_id=bundle.review_bundle_id,
            review_bundle_hash=bundle.review_bundle_hash,
            static_validation_id=bundle.static_validation_id,
            runtime_validation_id=bundle.runtime_validation_id,
            target_template_id=target_template_id,
            target_template_version=target_template_version,
            source_code_hash=bundle.source_code_hash,
            schema_hash=bundle.schema_hash,
            promotion_policy_version=promotion_policy_version,
            created_at=_now_utc(),
            promotion_manifest_hash=manifest_hash,
        )

        # 12. Create Durable Promotion Record in PREPARING State
        prom_record = CandidatePromotionRecord(
            promotion_id=temp_promotion_id,
            candidate_id=candidate.candidate_id,
            workspace_id=candidate.workspace_id,
            promotion_manifest_hash=manifest_hash,
            approval_decision_id=decision.decision_id,
            review_bundle_hash=bundle.review_bundle_hash,
            target_template_id=target_template_id,
            target_template_version=target_template_version,
            pre_publish_registry_hash="",
            status=PromotionRecordStatus.PREPARING,
            started_at=_now_utc(),
            promoted_by_principal_id=principal.principal_id,
        )
        self.repository.save_promotion_record(prom_record)

        # 13. Isolated Staging
        try:
            staged = self.publisher.prepare_staged_publication(
                candidate=candidate,
                target_template_id=target_template_id,
                source_code=source_code,
            )
            prom_record = prom_record.model_copy(update={
                "pre_publish_registry_hash": staged.pre_publish_registry_hash
            })
            self.repository.save_promotion_record(prom_record)

            # Staging consistency checks
            self.publisher.verify_staged_publication(
                staged=staged,
                expected_source_hash=bundle.source_code_hash,
            )
        except Exception as exc:
            prom_record = prom_record.model_copy(update={
                "status": PromotionRecordStatus.FAILED,
                "error_message": str(exc),
                "completed_at": _now_utc(),
            })
            self.repository.save_promotion_record(prom_record)
            raise

        # 14. Atomic Publication Commit with Rollback Journal
        try:
            post_publish_hash, published_artifact_hashes, journal = self.publisher.commit_publication(staged)
        except Exception as exc:
            prom_record = prom_record.model_copy(update={
                "status": PromotionRecordStatus.ROLLED_BACK,
                "error_message": f"Canonical commit failed, rolled back: {exc}",
                "completed_at": _now_utc(),
            })
            self.repository.save_promotion_record(prom_record)
            raise

        # 15. Post-Publish Live Canonical Verification
        try:
            self.publisher.verify_canonical_publication(
                target_template_id=target_template_id,
                component_name=staged.component_name,
                rel_file_path=staged.rel_file_path,
                expected_source_hash=bundle.source_code_hash,
            )
        except Exception as exc:
            # Immediate rollback on post-publish verification failure
            self.publisher.rollback(journal)
            err_msg = f"Post-publish verification failed, rolled back: {exc}"
            prom_record = prom_record.model_copy(update={
                "status": PromotionRecordStatus.ROLLED_BACK,
                "error_message": err_msg,
                "completed_at": _now_utc(),
            })
            self.repository.save_promotion_record(prom_record)
            raise PromotionRollbackError(err_msg)

        # 16. Authoritative Status Transition: APPROVED → PROMOTED via CAS
        try:
            self.repository.update_candidate_status_cas(
                candidate_id=candidate.candidate_id,
                workspace_id=workspace_id,
                status=CandidateStatus.PROMOTED,
                expected_revision=expected_revision,
            )
        except Exception as exc:
            # If candidate CAS update fails, rollback canonical publication to prevent divergence
            self.publisher.rollback(journal)
            err_msg = f"Candidate CAS status update failed, rolled back: {exc}"
            prom_record = prom_record.model_copy(update={
                "status": PromotionRecordStatus.ROLLED_BACK,
                "error_message": err_msg,
                "completed_at": _now_utc(),
            })
            self.repository.save_promotion_record(prom_record)
            raise CandidateConflictError(err_msg)

        # 17. Finalize and Persist PromotionRecord
        prom_record = prom_record.model_copy(update={
            "status": PromotionRecordStatus.COMMITTED,
            "post_publish_registry_hash": post_publish_hash,
            "published_artifact_hashes": published_artifact_hashes,
            "completed_at": _now_utc(),
        })
        saved_record = self.repository.save_promotion_record(prom_record)

        # Also store durable record JSON in StorageService
        storage_key = f"workspaces/{workspace_id}/candidates/{candidate_id}/promotion_{temp_promotion_id}_record.json"
        try:
            self.storage_service.put(
                storage_key,
                saved_record.model_dump_json().encode("utf-8"),
                content_type="application/json",
            )
        except Exception:
            pass  # SQL table is the durable primary store

        return saved_record

    def get_promotion_record(
        self, tenant_context: TenantContext, promotion_id: str
    ) -> Optional[CandidatePromotionRecord]:
        """Retrieves a promotion record enforcing tenant isolation."""
        return self.repository.get_promotion_record(promotion_id, tenant_context.workspace_id)

    def get_candidate_promotion(
        self, tenant_context: TenantContext, candidate_id: str
    ) -> Optional[CandidatePromotionRecord]:
        """Retrieves latest promotion record for candidate enforcing tenant isolation."""
        return self.repository.get_promotion_record_by_candidate(candidate_id, tenant_context.workspace_id)

    def list_promotions(
        self, tenant_context: TenantContext, candidate_id: Optional[str] = None
    ) -> List[CandidatePromotionRecord]:
        """Lists promotion records for current workspace."""
        return self.repository.list_promotion_records(tenant_context.workspace_id, candidate_id=candidate_id)


def create_promotion_service() -> PromotionService:
    """Factory creating PromotionService with database and storage dependencies."""
    from scripts.core.database import get_database_engine
    from scripts.core.template_candidate_repository import SqlTemplateCandidateRepository
    from scripts.core.storage import get_storage_service

    repo = SqlTemplateCandidateRepository(get_database_engine())
    storage = get_storage_service()
    return PromotionService(repository=repo, storage_service=storage)
