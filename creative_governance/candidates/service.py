"""
creative_governance/candidates/service.py
========================
Domain Service Authority for TemplateCandidate (S28-07A).

Invariants:
- AI ≠ Registry Authority (No direct canonical registry writes or mutations).
- TemplateCandidate ≠ Registered Template (Stays isolated in quarantine/candidate storage).
- Candidate creation is strictly predicated on an authoritative NEEDS_CREATE decision
  with auditable evidence that REUSE and COMPOSE are insufficient.
- Multi-tenant isolation: all operations require and enforce TenantContext.
- Status is strictly server-controlled: always starts as DRAFT. Caller cannot set APPROVED or PROMOTED.
- Large artifacts (source code, schema, fixtures) are stored via StorageService under server-generated keys.
- Optimistic Concurrency Control (CAS): updates require expected_revision matching current revision.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.plan import (
    CreativePlan,
    CreativeTier,
    CreativeTierDecision,
)
from ai.contracts.creative.template_candidate import (
    CandidateStatus,
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
    CandidateTenantMismatchError,
)
from creative_governance.candidates.hashing import compute_candidate_content_hash
from creative_governance.candidates.repository import TemplateCandidateRepository
from scripts.core.security.principal import Principal, Role
from scripts.core.storage import (
    StorageService,
    build_storage_key,
    validate_storage_key,
)
from scripts.core.tenant_model import TenantContext, ProjectRecord


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class TemplateCandidateService:
    """
    Authoritative domain service governing TemplateCandidate creation,
    retrieval, update, and lifecycle isolation.
    """

    def __init__(
        self,
        repository: TemplateCandidateRepository,
        storage_service: StorageService,
    ) -> None:
        self.repository = repository
        self.storage_service = storage_service
        self._test_projects: Dict[str, ProjectRecord] = {}

    def register_project_for_test(self, project: ProjectRecord) -> None:
        """Helper for registering in-memory test project records."""
        self._test_projects[project.id] = project

    def _verify_project_tenant(self, project_id: str, caller_workspace_id: str) -> None:
        """Enforces that the project belongs to the caller's authorized workspace."""
        if project_id in self._test_projects:
            proj = self._test_projects[project_id]
            if proj.workspace_id != caller_workspace_id:
                raise CandidateTenantMismatchError(
                    f"Project '{project_id}' belongs to workspace '{proj.workspace_id}', "
                    f"which does not belong to caller workspace '{caller_workspace_id}'."
                )
            return

        # Query database tenant registry
        try:
            from scripts.core.database import get_database_engine, TenantRepository
            repo = TenantRepository(get_database_engine())
            proj_rec = repo.get_project(project_id)
            if not proj_rec:
                raise CandidateTenantMismatchError(f"Project '{project_id}' not found.")
            if proj_rec.workspace_id != caller_workspace_id:
                raise CandidateTenantMismatchError(
                    f"Project '{project_id}' belongs to workspace '{proj_rec.workspace_id}', "
                    f"which does not belong to caller workspace '{caller_workspace_id}'."
                )
        except CandidateTenantMismatchError:
            raise
        except Exception as e:
            # If database engine is unavailable during tests, fall back to safe rejection if not registered
            raise CandidateTenantMismatchError(
                f"Failed to verify project '{project_id}' against workspace '{caller_workspace_id}': {e}"
            )

    def create_candidate(
        self,
        tenant_context: TenantContext,
        source_project_id: str,
        creative_plan: CreativePlan | str,
        tier_decision: CreativeTierDecision,
        source_code: str,
        template_schema: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        fixtures: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        author: Optional[str] = None,
        proposed_category: Optional[str] = None,
        proposed_tags: Optional[List[str]] = None,
        creator_ai_run_id: Optional[str] = None,
        requested_status: Optional[str] = None,
    ) -> TemplateCandidate:
        """
        Creates a new TemplateCandidate in isolated storage with initial status DRAFT.
        Requires proven NEEDS_CREATE decision with insufficient REUSE and COMPOSE evidence.
        """
        workspace_id = tenant_context.workspace_id

        # 1. Authority Guard: caller cannot specify non-DRAFT status
        if requested_status is not None:
            norm_status = str(requested_status).strip().upper()
            if norm_status != CandidateStatus.DRAFT.value:
                raise CandidateAuthorityError(
                    f"Caller cannot set candidate status to '{requested_status}'. "
                    f"TemplateCandidate creation strictly begins as DRAFT."
                )

        # 2. Tenant Confinement: verify project belongs to workspace
        self._verify_project_tenant(source_project_id, workspace_id)

        # 3. NEEDS_CREATE Provenance & Eligibility Guard (S28-06 -> S28-07)
        if not isinstance(tier_decision, CreativeTierDecision):
            raise CandidateEligibilityError(
                f"Candidate creation rejected: invalid tier_decision type {type(tier_decision)}."
            )

        if tier_decision.selected_tier != CreativeTier.CREATE:
            raise CandidateEligibilityError(
                f"Candidate creation rejected: tier_decision.selected_tier must be CREATE, "
                f"got '{tier_decision.selected_tier}'."
            )
        if not tier_decision.needs_create_evaluation:
            raise CandidateEligibilityError(
                "Candidate creation rejected: tier_decision.needs_create_evaluation must be True."
            )
        if tier_decision.reuse_result is None or tier_decision.reuse_result.sufficiency:
            raise CandidateEligibilityError(
                "Candidate creation rejected: insufficient evidence that REUSE failed."
            )
        if tier_decision.compose_result is None or tier_decision.compose_result.sufficiency:
            raise CandidateEligibilityError(
                "Candidate creation rejected: insufficient evidence that COMPOSE failed."
            )

        why_reuse_failed = tier_decision.reuse_result.rationale
        why_compose_failed = tier_decision.compose_result.rationale

        if isinstance(creative_plan, CreativePlan):
            plan_ref = creative_plan.plan_id
        elif isinstance(creative_plan, str):
            plan_ref = creative_plan.strip()
            if not plan_ref:
                raise CandidateEligibilityError("creative_plan reference cannot be empty.")
        else:
            raise CandidateEligibilityError(f"Invalid creative_plan type: {type(creative_plan)}")

        decision_ref = tier_decision.decision_id

        # 4. Generate Safe Candidate ID
        candidate_id = f"cand_{uuid.uuid4().hex[:12]}"

        # 5. Deterministic Server-Side Content Hashing
        schema_dict = template_schema or {}
        deps_list = dependencies or []
        fixtures_dict = fixtures or {}
        content_hash = compute_candidate_content_hash(
            source_code=source_code,
            template_schema=schema_dict,
            dependencies=deps_list,
            fixtures=fixtures_dict,
            why_reuse_failed=why_reuse_failed,
            why_compose_failed=why_compose_failed,
            creative_plan_reference=plan_ref,
            creative_tier_decision_reference=decision_ref,
        )

        # 6. Upload heavy artifacts to StorageService under isolated candidate namespace
        # workspaces/{workspace_id}/projects/{project_id}/candidates/{candidate_id}/{filename}
        source_key = build_storage_key(workspace_id, source_project_id, "candidates", candidate_id, "source.tsx")
        self.storage_service.put(source_key, source_code.encode("utf-8"), content_type="text/plain; charset=utf-8")

        storage_keys: Dict[str, str] = {"source_code": source_key}

        if schema_dict:
            schema_key = build_storage_key(workspace_id, source_project_id, "candidates", candidate_id, "schema.json")
            self.storage_service.put(schema_key, json.dumps(schema_dict).encode("utf-8"), content_type="application/json")
            storage_keys["schema"] = schema_key

        if fixtures_dict:
            fixtures_key = build_storage_key(workspace_id, source_project_id, "candidates", candidate_id, "fixtures.json")
            self.storage_service.put(fixtures_key, json.dumps(fixtures_dict).encode("utf-8"), content_type="application/json")
            storage_keys["fixtures"] = fixtures_key

        now = _now_utc()
        candidate = TemplateCandidate(
            candidate_id=candidate_id,
            workspace_id=workspace_id,
            source_project_id=source_project_id,
            origin_project_id=source_project_id,
            creator_ai_run_id=creator_ai_run_id,
            creative_plan_reference=plan_ref,
            creative_tier_decision_reference=decision_ref,
            why_reuse_failed=why_reuse_failed,
            why_compose_failed=why_compose_failed,
            source_code=source_code,
            source_code_path=source_key,
            template_schema=schema_dict,
            dependencies=deps_list,
            fixtures=fixtures_dict,
            content_hash=content_hash,
            revision=1,
            status=CandidateStatus.DRAFT,
            name=name or f"Candidate {candidate_id}",
            description=description or "Custom template candidate incubating under S28-07A.",
            author=author or tenant_context.user_id,
            proposed_category=proposed_category or "elements/ui",
            proposed_tags=proposed_tags or [],
            target_tier=CreativeTier.REUSE,
            required_provenance=ProvenanceRecord(
                source=f"plan:{plan_ref}:decision:{decision_ref}",
                timestamp=now,
            ),
            storage_keys=storage_keys,
            created_at=now,
            updated_at=now,
        )

        # 7. Persist to metadata repository
        return self.repository.save_candidate(candidate)

    def get_candidate(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
    ) -> TemplateCandidate:
        """
        Retrieves a candidate by ID scoped strictly to the caller's authorized workspace.
        Raises CandidateNotFoundError if not found or cross-tenant.
        """
        workspace_id = tenant_context.workspace_id
        candidate = self.repository.get_candidate(candidate_id, workspace_id)
        if not candidate:
            raise CandidateNotFoundError(
                f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'."
            )

        # If source_code was not in metadata, resolve from storage
        if not candidate.source_code and "source_code" in candidate.storage_keys:
            try:
                code_bytes = self.storage_service.get(candidate.storage_keys["source_code"])
                candidate = candidate.model_copy(update={"source_code": code_bytes.decode("utf-8")})
            except Exception:
                pass

        return candidate

    def list_candidates(
        self,
        tenant_context: TenantContext,
        project_id: Optional[str] = None,
    ) -> List[TemplateCandidate]:
        """
        Lists all candidates belonging to the caller's authorized workspace.
        """
        workspace_id = tenant_context.workspace_id
        return self.repository.list_candidates(workspace_id=workspace_id, project_id=project_id)

    def update_draft_candidate(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        expected_revision: int,
        source_code: Optional[str] = None,
        template_schema: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        fixtures: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        proposed_category: Optional[str] = None,
        proposed_tags: Optional[List[str]] = None,
        requested_status: Optional[str] = None,
    ) -> TemplateCandidate:
        """
        Updates a candidate while in DRAFT status using optimistic concurrency (CAS).
        Increments revision atomically (N -> N+1).
        """
        workspace_id = tenant_context.workspace_id

        # 1. Fetch current candidate (enforces workspace isolation)
        existing = self.repository.get_candidate(candidate_id, workspace_id)
        if not existing:
            raise CandidateNotFoundError(
                f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'."
            )

        # 2. Status Guard: only DRAFT candidates can be modified
        if existing.status != CandidateStatus.DRAFT:
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{existing.status}'. "
                f"Only DRAFT candidates may be modified."
            )

        # 3. Authority Guard: caller cannot change status
        if requested_status is not None:
            norm_status = str(requested_status).strip().upper()
            if norm_status != CandidateStatus.DRAFT.value:
                raise CandidateAuthorityError(
                    f"Caller cannot alter candidate status to '{requested_status}'. "
                    f"Status transitions are governed exclusively by domain gates."
                )

        # 4. Merge fields
        new_source = source_code if source_code is not None else existing.source_code
        new_schema = template_schema if template_schema is not None else existing.template_schema
        new_deps = dependencies if dependencies is not None else existing.dependencies
        new_fixtures = fixtures if fixtures is not None else existing.fixtures
        new_name = name if name is not None else existing.name
        new_desc = description if description is not None else existing.description
        new_cat = proposed_category if proposed_category is not None else existing.proposed_category
        new_tags = proposed_tags if proposed_tags is not None else existing.proposed_tags

        # 5. Recompute content hash server-side
        new_hash = compute_candidate_content_hash(
            source_code=new_source,
            template_schema=new_schema,
            dependencies=new_deps,
            fixtures=new_fixtures,
            why_reuse_failed=existing.why_reuse_failed,
            why_compose_failed=existing.why_compose_failed,
            creative_plan_reference=existing.creative_plan_reference,
            creative_tier_decision_reference=existing.creative_tier_decision_reference,
        )

        # 6. Update objects in StorageService
        storage_keys = dict(existing.storage_keys)
        if source_code is not None and "source_code" in storage_keys:
            self.storage_service.put(storage_keys["source_code"], new_source.encode("utf-8"), content_type="text/plain; charset=utf-8")

        if template_schema is not None:
            schema_key = storage_keys.get("schema") or build_storage_key(workspace_id, existing.source_project_id, "candidates", candidate_id, "schema.json")
            self.storage_service.put(schema_key, json.dumps(new_schema).encode("utf-8"), content_type="application/json")
            storage_keys["schema"] = schema_key

        if fixtures is not None:
            fixtures_key = storage_keys.get("fixtures") or build_storage_key(workspace_id, existing.source_project_id, "candidates", candidate_id, "fixtures.json")
            self.storage_service.put(fixtures_key, json.dumps(new_fixtures).encode("utf-8"), content_type="application/json")
            storage_keys["fixtures"] = fixtures_key

        now = _now_utc()
        candidate_to_update = existing.model_copy(
            update={
                "source_code": new_source,
                "template_schema": new_schema,
                "dependencies": new_deps,
                "fixtures": new_fixtures,
                "name": new_name,
                "description": new_desc,
                "proposed_category": new_cat,
                "proposed_tags": new_tags,
                "content_hash": new_hash,
                "storage_keys": storage_keys,
                "updated_at": now,
            }
        )

        # 7. Apply CAS update in repository
        return self.repository.update_candidate_cas(
            candidate=candidate_to_update,
            expected_revision=expected_revision,
        )

    def delete_candidate(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
    ) -> bool:
        """
        Deletes a candidate and its associated storage objects, scoped to caller workspace.
        """
        workspace_id = tenant_context.workspace_id
        candidate = self.repository.get_candidate(candidate_id, workspace_id)
        if not candidate:
            return False

        # Clean up storage objects
        for key in candidate.storage_keys.values():
            try:
                self.storage_service.delete(key)
            except Exception:
                pass

        return self.repository.delete_candidate(candidate_id, workspace_id)

    def transition_to_validating(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        expected_revision: int,
    ) -> TemplateCandidate:
        """
        Domain authority method transitioning a DRAFT candidate to VALIDATING
        after acquiring STATIC_PASS evidence (S28-07B).
        Strictly prevents transition to VALIDATED or APPROVED.
        """
        workspace_id = tenant_context.workspace_id
        existing = self.repository.get_candidate(candidate_id, workspace_id)
        if not existing:
            raise CandidateNotFoundError(f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'.")

        if existing.status not in (CandidateStatus.DRAFT, CandidateStatus.VALIDATING):
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{existing.status}'. Cannot transition to VALIDATING."
            )

        return self.repository.update_candidate_status_cas(
            candidate_id=candidate_id,
            workspace_id=workspace_id,
            status=CandidateStatus.VALIDATING,
            expected_revision=expected_revision,
        )

    def transition_to_validated(
        self,
        tenant_context: TenantContext,
        candidate_id: str,
        expected_revision: int,
        runtime_validation_report_id: str,
    ) -> TemplateCandidate:
        """
        Domain authority method transitioning a VALIDATING candidate to VALIDATED
        upon verification of full static and runtime validation evidence (S28-07C).
        Enforces CAS concurrency protection and precondition integrity.
        Candidate remains strictly NOT APPROVED and NOT PROMOTED.
        """
        workspace_id = tenant_context.workspace_id
        existing = self.repository.get_candidate(candidate_id, workspace_id)
        if not existing:
            raise CandidateNotFoundError(f"Candidate '{candidate_id}' not found in workspace '{workspace_id}'.")

        # 1. Precondition: candidate must currently be in VALIDATING status
        if existing.status != CandidateStatus.VALIDATING:
            raise CandidateInvalidStatusError(
                f"Candidate '{candidate_id}' is in status '{existing.status}'. "
                f"Only candidates in VALIDATING status can transition to VALIDATED."
            )

        # 2. Precondition: verify runtime validation report exists in repository
        runtime_report = self.repository.get_validation_report(runtime_validation_report_id, workspace_id)
        if not runtime_report:
            raise CandidateEligibilityError(
                f"Runtime validation report '{runtime_validation_report_id}' not found for candidate '{candidate_id}'."
            )

        if (
            runtime_report.phase != ValidationPhase.RUNTIME
            or runtime_report.overall_result != ValidationOverallResult.PASS
        ):
            raise CandidateEligibilityError(
                f"Runtime validation report '{runtime_validation_report_id}' has phase '{runtime_report.phase}' "
                f"and verdict '{runtime_report.overall_result}'. Transition to VALIDATED requires successful RUNTIME PASS."
            )

        # 3. Anti-stale guard: report must match current candidate snapshot exactly
        if (
            runtime_report.candidate_content_hash != existing.content_hash
            or runtime_report.candidate_revision != existing.revision
        ):
            raise CandidateConflictError(
                f"Candidate '{candidate_id}' revision drifted from runtime validation report. "
                f"Report hash {runtime_report.candidate_content_hash[:8]} vs current {existing.content_hash[:8]}."
            )

        # 4. Mandatory gate verification
        required_gates = {
            "render_smoke_gate",
            "runtime_contract_gate",
            "aspect_gate",
            "probe_gate",
            "qc_gate",
        }
        passed_gates = {g.gate_id for g in runtime_report.gates if g.status == GateStatus.PASS}
        missing = required_gates - passed_gates
        if missing:
            raise CandidateEligibilityError(
                f"Candidate '{candidate_id}' cannot transition to VALIDATED: missing passing gates {missing}."
            )

        # 5. Atomic CAS transition to VALIDATED
        return self.repository.update_candidate_status_cas(
            candidate_id=candidate_id,
            workspace_id=workspace_id,
            status=CandidateStatus.VALIDATED,
            expected_revision=expected_revision,
        )

