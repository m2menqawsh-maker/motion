"""
api/services/creative_service.py — Production AI Creative Orchestration Service.
S28 / PR-003: Connects AI perception, narrative, planning, and compilation
to the authoritative authoring and tenant persistence pipeline.

Guarantees:
- Derives principal, workspace, and project authorization strictly from server-verified TenantContext.
- Executes REAL deterministic AI domain components (IntentParser, BriefBuilder, RecipeSelector,
  NarrativePlanner, CreativePlanner, CreativeTierPolicy, BlueprintCompiler).
- Zero hallucinated/placeholder template IDs; verifies against Canonical Template Registry.
- CreativePlan remains strictly advisory (status=PROPOSED); does not write .studio_approved,
  does not mutate canonical state, and does not trigger durable runs during proposal generation.
- Explicit apply commits candidate blueprints via CanonicalDocumentRepository with revision CAS
  and durable idempotency via AuthoringIdempotencyRepository.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from api.core.errors import (
    APIError,
    ProjectNotFoundError,
    RevisionConflictError,
)
from api.schemas.creative import (
    ApplyCreativeProposalRequest,
    CreativeProposalRequest,
    CreativeProposalResponse,
)
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.plan import CreativePlan, CreativeTier, ResolvedTemplateDecision, SceneIntent
from ai.intent.brief_builder import CreativeBriefBuilder
from ai.intent.parser import IntentParser
from ai.narrative.planner import NarrativePlanner
from ai.planning.compiler import BlueprintCompiler
from ai.planning.compose_engine import ComposeEngine
from ai.planning.creative_planner import CreativePlanner
from ai.planning.reuse_engine import ReuseEngine
from ai.planning.tier_policy import CreativeTierPolicy
from ai.recipes.registry import RecipeRegistry
from ai.recipes.selector import RecipeSelector
from scripts.core.authoring_idempotency_repository import AuthoringIdempotencyRepository
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.canonical_document_repository import (
    CanonicalDocumentRepository,
    DocumentValidationError,
)
from scripts.core.state_store import StateConflictError, StateNotFoundError
from scripts.core.template_contract import TemplateRegistryContract
from scripts.core.tenant_model import TenantContext
from scripts.security.path_security import validate_project_id

logger = logging.getLogger("clean_video.creative_service")

# Mapping high-level scene intent categories to verified capabilities in the Canonical Template Registry
INTENT_CAPABILITY_MAP: Dict[str, List[str]] = {
    "hook": ["hook", "headline", "title"],
    "problem": ["code", "syntax", "split"],
    "solution": ["bento", "showcase", "cards"],
    "proof": ["metric", "stat", "numbers", "counter"],
    "cta": ["call_to_action", "button", "summary"],
    "overview": ["grid", "cards", "pan"],
}

# Suspicious keywords attempting to override server security, role checks, or review gates
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"set\s+role\s*=\s*(?:admin|superuser|root)", re.IGNORECASE),
    re.compile(r"bypass\s+(?:auth|gates|review|qc)", re.IGNORECASE),
    re.compile(r"write\s+\.studio_approved", re.IGNORECASE),
    re.compile(r"auto[_-]?approve", re.IGNORECASE),
]


class CreativeService:
    """Production domain service orchestrating AI creative generation and authoritative apply."""

    _doc_repo = CanonicalDocumentRepository()
    _idemp_repo = AuthoringIdempotencyRepository()
    _recipe_registry = RecipeRegistry()
    _template_registry = TemplateRegistryContract()
    _intent_parser = IntentParser()
    _brief_builder = CreativeBriefBuilder(parser=_intent_parser)
    _narrative_planner = NarrativePlanner()
    _creative_planner = CreativePlanner()
    _reuse_engine = ReuseEngine(template_contract=_template_registry)
    _compose_engine = ComposeEngine(template_contract=_template_registry)
    _tier_policy = CreativeTierPolicy(reuse_engine=_reuse_engine, compose_engine=_compose_engine)
    _compiler = BlueprintCompiler()

    @classmethod
    def _compute_payload_hash(cls, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def generate_proposal(
        cls,
        project_id: str,
        tenant_context: TenantContext,
        req: CreativeProposalRequest,
    ) -> CreativeProposalResponse:
        """
        Generates an advisory AI CreativePlan and candidate BlueprintV2 from natural language.
        Strictly read-only with respect to canonical document state.
        """
        validate_project_id(project_id)
        ws_id = tenant_context.workspace_id

        # 1. Prompt validation & injection inspection
        cleaned_prompt = req.prompt.strip()
        if not cleaned_prompt:
            raise APIError(message="Creative prompt cannot be empty or whitespace.", status_code=400)

        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(cleaned_prompt):
                logger.warning(
                    f"Prompt injection pattern detected in project '{project_id}' for workspace '{ws_id}'."
                )
                raise APIError(
                    message="Prompt injection attempt rejected: directives modifying roles, gates, or security policies are forbidden.",
                    status_code=400,
                )

        # 2. Verify project existence and tenant boundary in canonical store
        conn = cls._doc_repo.db.get_connection()
        try:
            cur = conn.execute(
                "SELECT revision, workspace_id FROM project_states WHERE project_id = ?",
                (project_id,),
            )
            state_row = cur.fetchone()
            if not state_row:
                raise ProjectNotFoundError(project_id)
            curr_rev, db_ws = state_row[0], state_row[1]
            if db_ws != ws_id:
                from scripts.core.database import TenantSecurityError
                raise TenantSecurityError(
                    f"Cross-tenant access rejected: Project belongs to '{db_ws}', not '{ws_id}'."
                )
        finally:
            conn.close()

        # 3. Detect prompt contradictions (e.g., silent mode + voiceover request)
        contradictions = cls._intent_parser._detect_contradictions(cleaned_prompt)
        if contradictions:
            logger.info(f"Contradictory creative prompt detected: {contradictions}")
            raise APIError(
                message=f"Contradictory creative instructions detected: {'; '.join(contradictions)}",
                status_code=400,
            )

        # 4. Synthesize CreativeBrief using real parser with authoritative project context
        workspace_constraints: Dict[str, Any] = {}
        brief: CreativeBrief = cls._brief_builder.build_brief(
            user_request=cleaned_prompt,
            project_id=project_id,
            workspace_id=ws_id,
            workspace_constraints=workspace_constraints,
        )

        # Apply optional explicit request constraints
        updated_constraints = brief.constraints
        if req.aspect_ratio:
            updated_constraints = updated_constraints.model_copy(update={"aspect_ratios": [req.aspect_ratio]})
        if req.target_duration:
            updated_constraints = updated_constraints.model_copy(update={"target_duration_seconds": req.target_duration})
        if req.audio_mode:
            audio_mode_enum = AudioMode(req.audio_mode)
            updated_constraints = updated_constraints.model_copy(update={"audio_mode": audio_mode_enum})
        brief = brief.model_copy(update={"constraints": updated_constraints})

        # 5. Deterministic Recipe Selection
        try:
            recipe_selection = RecipeSelector(cls._recipe_registry).select_recipe(brief)
            recipe = cls._recipe_registry.get(recipe_selection.selected_recipe_id)
        except Exception as exc:
            logger.error(f"Recipe selection failed for brief '{brief.brief_id}': {exc}")
            raise APIError(message=f"Recipe selection failed: {exc}", status_code=422)

        # 6. Structured Narrative Planning
        try:
            narrative_plan = cls._narrative_planner.plan(brief=brief, recipe=recipe)
        except Exception as exc:
            logger.error(f"Narrative planning failed: {exc}")
            raise APIError(message=f"Narrative planning failed: {exc}", status_code=422)

        # 7. Advisory Creative Planning
        try:
            creative_plan: CreativePlan = cls._creative_planner.plan(
                brief=brief,
                narrative_plan=narrative_plan,
                recipe=recipe,
            )
        except Exception as exc:
            logger.error(f"Creative planning failed: {exc}")
            raise APIError(message=f"Creative planning failed: {exc}", status_code=422)

        # 8. Deterministic Template Resolution via Tier Policy & Canonical Registry
        target_aspect = req.aspect_ratio or (brief.constraints.aspect_ratios[0] if brief.constraints.aspect_ratios else "9:16")
        template_decisions: Dict[str, str] = {}
        diagnostics: List[Dict[str, Any]] = []

        for idx, scene in enumerate(creative_plan.scenes):
            intent_label = scene.intent_label.lower()
            candidate_reqs: List[str] = []

            for key, capabilities in INTENT_CAPABILITY_MAP.items():
                if key in intent_label:
                    candidate_reqs = capabilities
                    break
            if not candidate_reqs:
                candidate_reqs = ["hook" if idx == 0 else "cards"]

            # Evaluate registered candidates with tier policy
            selected_template: Optional[str] = None
            for req_tag in candidate_reqs:
                scene_with_req = scene.model_copy(update={"template_requirements": [req_tag]})
                decision = cls._tier_policy.decide(
                    scene_intent=scene_with_req,
                    aspect_ratio=target_aspect,
                    audio_mode=brief.constraints.audio_mode,
                )
                if decision.template_ref and cls._template_registry.is_valid(decision.template_ref):
                    selected_template = decision.template_ref
                    break

            if not selected_template:
                # Fallback to general canonical template if tier evaluation was inconclusive
                if idx == 0:
                    selected_template = "rui-intro"
                elif idx == len(creative_plan.scenes) - 1:
                    selected_template = "rui-end-card"
                else:
                    selected_template = "rui-bento-pan"

            if not cls._template_registry.is_valid(selected_template):
                raise APIError(
                    message=f"NEEDS_TEMPLATE_DECISION: Template '{selected_template}' is not registered in canonical contract.",
                    status_code=422,
                )

            template_decisions[scene.scene_id] = selected_template

        # 9. Deterministic Blueprint Compilation
        try:
            compilation_result = cls._compiler.compile(
                plan=creative_plan,
                template_decisions=template_decisions,
                project_id=project_id,
                fps=30,
                aspect_ratio=target_aspect,
                audio_mode=brief.constraints.audio_mode,
            )
            if not compilation_result.success:
                raise APIError(
                    message=f"Blueprint compilation failed: {'; '.join(compilation_result.errors)}",
                    status_code=422,
                )
            candidate_blueprint = compilation_result.blueprint
        except APIError:
            raise
        except Exception as exc:
            logger.error(f"Blueprint compilation error: {exc}")
            raise APIError(message=f"Blueprint compilation error: {exc}", status_code=500)

        # 10. Canonical BlueprintV2 Validation
        try:
            validate_blueprint_v2(candidate_blueprint)
        except Exception as exc:
            logger.error(f"Canonical blueprint validation failed on compiled proposal: {exc}")
            raise APIError(
                message=f"Compiled candidate blueprint failed schema validation: {exc}",
                status_code=500,
            )

        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
        return CreativeProposalResponse(
            proposal_id=proposal_id,
            status="PROPOSED",
            project_id=project_id,
            workspace_id=ws_id,
            base_revision=curr_rev,
            prompt=cleaned_prompt,
            brief=brief.model_dump(),
            recipe_id=recipe.recipe_id,
            narrative_hook=narrative_plan.core_hook,
            creative_plan=creative_plan.model_dump(),
            candidate_blueprint=candidate_blueprint,
            diagnostics=diagnostics,
            approval_required=True,
            can_apply=True,
        )

    @classmethod
    def apply_proposal(
        cls,
        project_id: str,
        tenant_context: TenantContext,
        req: ApplyCreativeProposalRequest,
        actor_id: str,
    ) -> Dict[str, Any]:
        """
        Authoritative transaction boundary for explicitly applying an AI creative proposal.
        Enforces CAS optimistic revision check and durable idempotency.
        """
        validate_project_id(project_id)
        ws_id = tenant_context.workspace_id

        operation_id = req.operation_id or f"op_{uuid.uuid4().hex[:12]}"

        # 1. Determine base revision
        expected_revision = req.base_revision
        if expected_revision is None:
            _, curr_rev = cls._doc_repo.get_document(workspace_id=ws_id, project_id=project_id)
            expected_revision = curr_rev
        expected_revision = int(expected_revision)

        # 2. Durable Idempotency Check
        payload_hash = cls._compute_payload_hash(req.model_dump())
        from scripts.core.authoring_idempotency_repository import IdempotencyConflictError as RepoIdempConflictError
        from api.core.errors import IdempotencyConflictError as APIIdempConflictError

        try:
            claim_status, cached_res = cls._idemp_repo.try_claim_leader(
                workspace_id=ws_id,
                project_id=project_id,
                operation_id=operation_id,
                operation_type="apply_creative_proposal",
                base_revision=expected_revision,
                payload_hash=payload_hash,
            )
        except RepoIdempConflictError as ice:
            raise APIIdempConflictError(
                idempotency_key=operation_id,
                message=str(ice),
            )

        if claim_status == "COMPLETED" and cached_res is not None:
            logger.info(f"Replaying cached idempotent proposal apply for '{operation_id}'")
            return {**cached_res, "idempotent": True}

        # 3. Verify Candidate Blueprint
        try:
            validate_blueprint_v2(req.blueprint)
        except Exception as exc:
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, {"error": "INVALID_BLUEPRINT", "details": str(exc)})
            raise APIError(message=f"Candidate blueprint rejected by schema validation: {exc}", status_code=400)

        # 4. Transactional CAS Commit to SQL + StorageService
        try:
            provenance = {
                "actor_id": actor_id,
                "operation_id": operation_id,
                "action": "apply_creative_proposal",
                "proposal_id": req.proposal_id,
            }
            committed_doc, next_rev, storage_key = cls._doc_repo.commit_candidate(
                workspace_id=ws_id,
                project_id=project_id,
                expected_revision=expected_revision,
                candidate_doc=req.blueprint,
                actor_id=actor_id,
                operation_id=operation_id,
                provenance=provenance,
            )
        except StateConflictError as sce:
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, {"error": "REVISION_CONFLICT", "details": str(sce)})
            raise RevisionConflictError(
                expected_revision=expected_revision,
                actual_revision=-1,
                message=str(sce),
            )
        except DocumentValidationError as dve:
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, {"error": "DOCUMENT_VALIDATION_ERROR", "details": str(dve)})
            raise APIError(message=str(dve), status_code=400)

        final_result = {
            "success": True,
            "operation_id": operation_id,
            "proposal_id": req.proposal_id,
            "base_revision": expected_revision,
            "result_revision": next_rev,
            "blueprint": committed_doc,
            "storage_key": storage_key,
            "provenance": provenance,
            "idempotent": False,
        }

        # 5. Mark Idempotency Record
        cls._idemp_repo.mark_completed(
            workspace_id=ws_id,
            project_id=project_id,
            operation_id=operation_id,
            result_revision=next_rev,
            result_payload=final_result,
        )

        return final_result
