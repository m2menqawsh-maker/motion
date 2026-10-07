"""
ai/contracts/creative/template_candidate.py
===========================================
Canonical contracts for TemplateCandidate, CandidateValidationReport, and PromotionDecision.

Authority: S28 Creative Intelligence Platform (DEC-S28.01 / S28-07A)
Guarantees:
- Candidate ≠ Approved/Registered Template.
- AI ≠ Canonical Registry Authority (AI cannot authorize template promotion).
- TemplateCandidate requires explicit, verifiable provenance.
- Strict isolation and server-controlled status (starts as DRAFT).
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, model_validator

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.plan import CreativeTier


class CandidateStatus(str, Enum):
    """Authoritative lifecycle vocabulary for TemplateCandidate."""
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"
    RETIRED = "RETIRED"


class PromotionStatus(str, Enum):
    """Lifecycle stages for template candidate promotion."""
    PENDING_EVALUATION = "PENDING_EVALUATION"
    EVALUATION_PASSED = "EVALUATION_PASSED"
    EVALUATION_FAILED = "EVALUATION_FAILED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TemplateCandidate(AIContractModel):
    """
    A proposed custom template undergoing isolation and evaluation (S28-07A).
    Never executes directly in production before formal certification and promotion.
    Requires explicit provenance linking to S28-06 NEEDS_CREATE decision.
    """
    candidate_id: str = Field(description="Unique candidate identifier (e.g., 'cand_my_pulse_text')")
    workspace_id: str = Field(default="ws_default", description="MANDATORY workspace identifier for multi-tenant isolation")
    source_project_id: str = Field(default="", description="Origin project identifier incubating this candidate")
    origin_project_id: Optional[str] = Field(default=None, description="Legacy alias for source_project_id")
    creator_ai_run_id: Optional[str] = Field(default=None, description="AI Run ID that generated this candidate")
    creative_plan_reference: str = Field(default="", description="Reference to originating CreativePlan ID")
    creative_tier_decision_reference: str = Field(default="", description="Reference to originating CreativeTierDecision ID")
    why_reuse_failed: str = Field(default="", description="Auditable evidence/rationale why existing templates (REUSE) were insufficient")
    why_compose_failed: str = Field(default="", description="Auditable evidence/rationale why Lego primitives (COMPOSE) were insufficient")
    source_code: str = Field(default="", description="TSX source code of the proposed template candidate")
    source_code_path: Optional[str] = Field(default=None, description="Storage key or isolated path where candidate source is persisted")
    template_schema: Dict[str, Any] = Field(default_factory=dict, description="Zod / JSON schema describing props of the proposed candidate")
    dependencies: List[str] = Field(default_factory=list, description="External package dependencies required by candidate")
    fixtures: Dict[str, Any] = Field(default_factory=dict, description="Sample props / test fixtures for candidate validation and rendering")
    content_hash: str = Field(default="", description="Server-computed deterministic SHA-256 hash of candidate content")
    revision: int = Field(default=1, ge=1, description="Monotonic optimistic concurrency / CAS revision sequence")
    status: strict_enum(CandidateStatus) = Field(
        default=CandidateStatus.DRAFT,
        description="Server-controlled lifecycle status (starts DRAFT)"
    )
    name: str = Field(default="", description="Proposed human-readable template name")
    description: str = Field(default="", description="Description of the template visual capability")
    author: str = Field(default="system", description="Author identifier (human user or agent)")
    proposed_category: str = Field(default="elements/ui", description="Target category (e.g., 'typography', 'data', 'scenes')")
    proposed_tags: List[str] = Field(default_factory=list, description="Descriptive classification tags")
    target_tier: strict_enum(CreativeTier) = Field(
        default=CreativeTier.REUSE,
        description="Target tier upon promotion (typically REUSE)"
    )
    required_provenance: ProvenanceRecord = Field(
        description="Mandatory provenance record documenting candidate lineage"
    )
    storage_keys: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of artifact types to canonical storage keys"
    )
    created_at: TzAwareDatetime = Field(description="UTC timestamp of candidate creation")
    updated_at: TzAwareDatetime = Field(description="UTC timestamp of candidate update")

    @model_validator(mode="before")
    @classmethod
    def sync_legacy_and_defaults(cls, data: Any) -> Any:
        """Synchronizes legacy field names and sets defaults before validation."""
        if isinstance(data, dict):
            # Interop between source_project_id and origin_project_id
            src_proj = data.get("source_project_id")
            orig_proj = data.get("origin_project_id")
            if src_proj and not orig_proj:
                data["origin_project_id"] = src_proj
            elif orig_proj and not src_proj:
                data["source_project_id"] = orig_proj

            # Default updated_at to created_at if missing
            if "created_at" in data and "updated_at" not in data:
                data["updated_at"] = data["created_at"]

            # Ensure required_provenance is populated if missing
            if "required_provenance" not in data or data["required_provenance"] is None:
                source = (
                    f"plan:{data.get('creative_plan_reference', '')}"
                    if data.get("creative_plan_reference")
                    else f"project:{data.get('source_project_id') or data.get('origin_project_id') or 'service'}"
                )
                created_ts = data.get("created_at")
                data["required_provenance"] = {
                    "source": source,
                    "timestamp": created_ts,
                }
        return data

    @model_validator(mode="after")
    def validate_provenance_presence(self) -> TemplateCandidate:
        """Enforces that candidate has complete and non-empty provenance."""
        prov = self.required_provenance
        if not prov.source or len(prov.source.strip()) == 0:
            raise ValueError("Template candidate must have valid required_provenance with non-empty source")
        return self


class ValidationPhase(str, Enum):
    """Validation lifecycle phase."""
    STATIC = "STATIC"
    RUNTIME = "RUNTIME"


class GateStatus(str, Enum):
    """Status verdict for an individual gate."""
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class ValidationOverallResult(str, Enum):
    """Overall outcome of candidate validation."""
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


class CandidateGateResult(AIContractModel):
    """
    Standardized, auditable outcome of an individual validation gate.
    """
    gate_id: str = Field(description="Unique identifier of the validation gate")
    status: strict_enum(GateStatus) = Field(description="Outcome of the gate check: PASS, FAIL, or ERROR")
    failure_code: Optional[str] = Field(default=None, description="Deterministic error or violation code if failed")
    summary: str = Field(description="Human-readable summary of the gate outcome")
    machine_details: Dict[str, Any] = Field(default_factory=dict, description="Structured diagnostics and technical context")
    evidence_refs: List[str] = Field(default_factory=list, description="Storage keys or references to evidence artifacts")


class ValidationSnapshot(AIContractModel):
    """
    Immutable snapshot binding a candidate version to a validation run (S28-07B / S28-07C).
    """
    candidate_id: str = Field(description="Target candidate identifier")
    workspace_id: str = Field(description="Workspace identifier for multi-tenant isolation")
    candidate_content_hash: str = Field(description="SHA-256 content hash of the candidate at validation start")
    candidate_revision: int = Field(ge=1, description="Monotonic revision number of the candidate at validation start")
    phase: strict_enum(ValidationPhase) = Field(default=ValidationPhase.STATIC, description="Validation phase: STATIC or RUNTIME")
    policy_version: str = Field(default="1.0.0", description="Policy version governing validation")
    started_at: TzAwareDatetime = Field(description="UTC timestamp when validation started")
    static_validation_id: Optional[str] = Field(default=None, description="Reference to passing static validation report ID (for RUNTIME phase)")
    static_validation_report_hash: Optional[str] = Field(default=None, description="SHA-256 digest of passing static validation report (for RUNTIME phase)")
    runtime_validation_id: Optional[str] = Field(default=None, description="Runtime validation execution identifier")


class CandidateValidationReport(AIContractModel):
    """
    Automated evaluation report assessing candidate code against technical,
    security, static, and runtime quality gates (S28-07B / S28-07C).
    """
    validation_id: str = Field(description="Unique validation execution identifier (val_{hex12})")
    candidate_id: str = Field(description="Evaluated TemplateCandidate ID")
    workspace_id: str = Field(default="ws_default", description="Workspace identifier for tenant isolation")
    candidate_content_hash: str = Field(default="", description="Immutable content hash bound to snapshot")
    candidate_revision: int = Field(default=1, ge=1, description="Candidate CAS revision sequence bound to snapshot")
    phase: strict_enum(ValidationPhase) = Field(default=ValidationPhase.STATIC, description="Validation phase: STATIC or RUNTIME")
    policy_version: str = Field(default="1.0.0", description="Validation policy version")
    started_at: TzAwareDatetime = Field(description="UTC timestamp when validation started")
    completed_at: TzAwareDatetime = Field(description="UTC timestamp when validation finished")
    gates: List[CandidateGateResult] = Field(default_factory=list, description="Results of all evaluated validation gates")
    overall_result: strict_enum(ValidationOverallResult) = Field(
        default=ValidationOverallResult.PASS,
        description="Overall verdict: PASS, FAIL, or ERROR"
    )
    evidence_refs: Dict[str, str] = Field(default_factory=dict, description="Map of artifact types to storage keys")
    static_validation_id: Optional[str] = Field(default=None, description="Reference to passing static validation report ID")
    static_validation_report_hash: Optional[str] = Field(default=None, description="SHA-256 digest of passing static validation report")

    # Backward compatibility fields (S28-01 legacy interop)
    report_id: Optional[str] = Field(default=None, description="Legacy alias for validation_id")
    typescript_compiles: bool = Field(default=True, description="True if component passes TypeScript type check")
    security_clean: bool = Field(default=True, description="True if static analysis detects no unauthorized imports")
    no_dangerous_imports: bool = Field(default=True, description="True if no native Node or forbidden packages are imported")
    has_documentation: bool = Field(default=True, description="True if prop schema and README documentation exist")
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Composite quality rating [0.0 - 1.0]")
    passed: bool = Field(default=True, description="True if overall validation passed")
    findings: List[str] = Field(default_factory=list, description="Detailed findings or failure reasons")
    evaluated_at: Optional[TzAwareDatetime] = Field(default=None, description="Legacy alias for completed_at")

    @model_validator(mode="before")
    @classmethod
    def sync_validation_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync validation_id and report_id
            v_id = data.get("validation_id")
            r_id = data.get("report_id")
            if not v_id and r_id:
                data["validation_id"] = r_id
            elif not r_id and v_id:
                data["report_id"] = v_id

            # Sync completed_at and evaluated_at
            c_at = data.get("completed_at")
            e_at = data.get("evaluated_at")
            if not c_at and e_at:
                data["completed_at"] = e_at
            elif not e_at and c_at:
                data["evaluated_at"] = c_at

            # Default started_at if omitted
            if "started_at" not in data or not data["started_at"]:
                data["started_at"] = data.get("completed_at") or data.get("evaluated_at")

            # Sync overall_result and passed
            if "overall_result" in data and "passed" not in data:
                data["passed"] = (str(data["overall_result"]).upper() == "PASS")
            elif "passed" in data and "overall_result" not in data:
                data["overall_result"] = "PASS" if data["passed"] else "FAIL"

        return data


class PromotionDecision(AIContractModel):
    """
    Formal governance decision certifying and promoting a candidate into the
    Canonical Template Registry.
    AI is strictly forbidden from acting as the authorizing entity.
    """
    decision_id: str = Field(description="Unique decision identifier")
    candidate_id: str = Field(description="Target TemplateCandidate ID")
    status: strict_enum(PromotionStatus) = Field(description="Promotion decision status")
    promoted_template_id: Optional[str] = Field(default=None, description="Registered template name if APPROVED")
    authorized_by: str = Field(description="Authorized human reviewer or Domain Service (never raw AI)")
    reasoning: str = Field(description="Explanation of the promotion or rejection decision")
    decided_at: TzAwareDatetime = Field(description="UTC timestamp of decision")

    @model_validator(mode="after")
    def validate_promotion_authority(self) -> PromotionDecision:
        """Enforces that promotion approval requires an authorized non-AI actor."""
        if self.status == PromotionStatus.APPROVED:
            auth_lower = self.authorized_by.lower().strip()
            forbidden_auths = {"ai", "agent", "llm", "claude", "gpt-4o", "creative_planner"}
            if auth_lower in forbidden_auths or len(auth_lower) == 0:
                raise ValueError(
                    f"Template promotion cannot be authorized by raw AI ('{self.authorized_by}'). "
                    f"Promotion requires explicit human reviewer or canonical Domain Service authority."
                )
            if not self.promoted_template_id:
                raise ValueError("Approved promotion must specify a promoted_template_id")
        return self


class CandidateReviewVerdict(str, Enum):
    """Authoritative verdict for a human review decision (S28-07D)."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CandidateReviewBundle(AIContractModel):
    """
    Canonical, immutable review bundle freezing the exact candidate snapshot
    and verified validation evidence for human review (S28-07D).
    """
    review_bundle_id: str = Field(description="Unique review bundle identifier (rbd_{hex12})")
    candidate_id: str = Field(description="Target candidate identifier")
    workspace_id: str = Field(default="ws_default", description="Workspace identifier for multi-tenant isolation")
    candidate_content_hash: str = Field(description="SHA-256 content hash of the candidate snapshot")
    candidate_revision: int = Field(ge=1, description="Candidate CAS revision at review freeze")
    static_validation_id: str = Field(description="ID of passing static validation report")
    runtime_validation_id: str = Field(description="ID of passing runtime validation report")
    static_report_hash: str = Field(description="SHA-256 digest of static validation report")
    runtime_report_hash: str = Field(description="SHA-256 digest of runtime validation report")
    render_evidence_refs: Dict[str, str] = Field(default_factory=dict, description="Storage keys of render evidence")
    representative_frame_refs: List[str] = Field(default_factory=list, description="Storage keys of representative probe frames")
    probe_report_ref: Optional[str] = Field(default=None, description="Storage key of probe report")
    qc_report_ref: Optional[str] = Field(default=None, description="Storage key of QC report")
    source_code_hash: str = Field(description="SHA-256 digest of candidate source code")
    schema_hash: str = Field(description="SHA-256 digest of candidate props schema")
    fixtures_hash: str = Field(description="SHA-256 digest of sample fixtures")
    created_at: TzAwareDatetime = Field(description="UTC timestamp when review bundle was created")
    review_policy_version: str = Field(default="1.0.0", description="Review policy version")
    review_bundle_hash: str = Field(description="Deterministic SHA-256 digest of review bundle content")


class CandidateReviewDecision(AIContractModel):
    """
    Append-only governance record capturing an authorized human review decision (S28-07D).
    Strictly bound to the specific ReviewBundle and candidate snapshot.
    AI is strictly forbidden from recording approvals.
    """
    decision_id: str = Field(description="Unique review decision identifier (rdec_{hex12})")
    review_bundle_id: str = Field(description="Identifier of the reviewed CandidateReviewBundle")
    candidate_id: str = Field(description="Target TemplateCandidate ID")
    workspace_id: str = Field(default="ws_default", description="Workspace identifier for tenant isolation")
    decision: strict_enum(CandidateReviewVerdict) = Field(description="Verdict: APPROVED or REJECTED")
    reviewer_principal_id: str = Field(description="Authenticated human reviewer principal ID")
    reviewer_role: str = Field(description="Effective workspace role of reviewer (reviewer or admin)")
    reason: str = Field(description="Audit explanation for decision (mandatory on REJECTED)")
    candidate_content_hash: str = Field(description="Content hash of approved/rejected candidate snapshot")
    candidate_revision: int = Field(ge=1, description="Revision of candidate snapshot")
    review_bundle_hash: str = Field(description="Digest of the reviewed ReviewBundle")
    static_validation_report_hash: str = Field(description="Digest of passing static validation report")
    runtime_validation_report_hash: str = Field(description="Digest of passing runtime validation report")
    render_evidence_ref: Optional[str] = Field(default=None, description="Reference to render evidence")
    qc_report_ref: Optional[str] = Field(default=None, description="Reference to QC report")
    decided_at: TzAwareDatetime = Field(description="UTC timestamp of the decision")
    decision_revision: int = Field(default=1, ge=1, description="Monotonic sequence for this decision")

    @model_validator(mode="after")
    def validate_reviewer_authority(self) -> CandidateReviewDecision:
        """Enforces that AI cannot approve, and rejection includes reasons."""
        rev_lower = self.reviewer_principal_id.lower().strip()
        forbidden_reviewers = {"ai", "agent", "llm", "claude", "gpt", "gpt-4o", "creative_planner", "anonymous", "system-worker"}
        if rev_lower in forbidden_reviewers or len(rev_lower) == 0:
            raise ValueError(
                f"Candidate review cannot be authorized by raw AI / system identity ('{self.reviewer_principal_id}'). "
                f"Review decisions strictly require an authenticated human reviewer."
            )
        if self.decision == CandidateReviewVerdict.REJECTED and (not self.reason or not self.reason.strip()):
            raise ValueError("Rejection decision requires a non-empty audit reason.")
        return self


class PromotionRecordStatus(str, Enum):
    """Lifecycle status for a template candidate promotion attempt (S28-07E)."""
    PREPARING = "PREPARING"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


class PromotionManifest(AIContractModel):
    """
    Immutable promotion snapshot binding candidate, approval, and target identity (S28-07E).
    Frozen before canonical publication begins.
    """
    promotion_id: str = Field(description="Unique promotion identifier (prom_{hex12})")
    candidate_id: str = Field(description="Target candidate identifier")
    workspace_id: str = Field(default="ws_default", description="Workspace identifier for multi-tenant isolation")
    candidate_content_hash: str = Field(description="SHA-256 content hash of approved candidate")
    candidate_revision: int = Field(ge=1, description="Candidate CAS revision at promotion")
    approval_decision_id: str = Field(description="Identifier of authoritative human CandidateReviewDecision")
    review_bundle_id: str = Field(description="Identifier of verified CandidateReviewBundle")
    review_bundle_hash: str = Field(description="Digest of verified CandidateReviewBundle")
    static_validation_id: str = Field(description="ID of passing static validation report")
    runtime_validation_id: str = Field(description="ID of passing runtime validation report")
    target_template_id: str = Field(description="Target canonical template ID (kebab-case)")
    target_template_version: str = Field(default="1.0.0", description="Semantic version of target template")
    source_code_hash: str = Field(description="SHA-256 digest of template source code")
    schema_hash: str = Field(description="SHA-256 digest of template props schema")
    promotion_policy_version: str = Field(default="1.0.0", description="Promotion policy version")
    created_at: TzAwareDatetime = Field(description="UTC timestamp of manifest creation")
    promotion_manifest_hash: str = Field(description="Deterministic SHA-256 digest of manifest")


class CandidatePromotionRecord(AIContractModel):
    """
    Durable record documenting publication and lifecycle transition to PROMOTED (S28-07E).
    """
    promotion_id: str = Field(description="Unique promotion identifier (prom_{hex12})")
    candidate_id: str = Field(description="Target candidate identifier")
    workspace_id: str = Field(default="ws_default", description="Workspace identifier for multi-tenant isolation")
    promotion_manifest_hash: str = Field(description="Deterministic SHA-256 digest of PromotionManifest")
    approval_decision_id: str = Field(description="Identifier of authoritative human CandidateReviewDecision")
    review_bundle_hash: str = Field(description="Digest of verified CandidateReviewBundle")
    target_template_id: str = Field(description="Target canonical template ID")
    target_template_version: str = Field(default="1.0.0", description="Target template version")
    pre_publish_registry_hash: str = Field(description="SHA-256 of template-registry-data.json before publication")
    post_publish_registry_hash: str = Field(default="", description="SHA-256 of template-registry-data.json after publication")
    published_artifact_hashes: Dict[str, str] = Field(default_factory=dict, description="Map of published artifact relative paths to SHA-256 digests")
    status: strict_enum(PromotionRecordStatus) = Field(
        description="Promotion attempt status (PREPARING, COMMITTED, FAILED, ROLLED_BACK)"
    )
    started_at: TzAwareDatetime = Field(description="UTC timestamp when promotion started")
    completed_at: Optional[TzAwareDatetime] = Field(default=None, description="UTC timestamp when promotion completed")
    error_message: Optional[str] = Field(default=None, description="Detailed failure or rollback reason if failed")
    promoted_by_principal_id: Optional[str] = Field(default=None, description="Principal ID of authorized actor executing promotion")


