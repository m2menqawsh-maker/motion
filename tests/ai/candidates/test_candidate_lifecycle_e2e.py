"""
tests/ai/candidates/test_candidate_lifecycle_e2e.py
===================================================
Authoritative End-to-End CREATE Lifecycle, Promotion & REUSE Learning Loop Suite (S28-07F).

Proves the complete closed-loop architectural invariant:
Project A (insufficient REUSE & COMPOSE -> NEEDS_CREATE)
  ↓
Candidate creation (DRAFT)
  ↓
Static validation (STATIC_PASS -> VALIDATING)
  ↓
Runtime validation (RUNTIME_PASS -> VALIDATED)
  ↓
Human review bundle freeze (AWAITING_APPROVAL)
  ↓
Human reviewer approval (APPROVED)
  ↓
Authorized PromotionService publication (PROMOTED)
  ↓
Canonical Registry updated (data, contracts, tsx, catalog, component)
  ↓
Project B (new project, new request)
  ↓
REUSE search discovers newly promoted canonical template
  ↓
TierPolicy selects REUSE without entering COMPOSE or CREATE
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest

from creative_governance.candidates.errors import (
    CandidateAuthorityError,
    CandidateConflictError,
    CandidateEligibilityError,
    CandidateInvalidStatusError,
    CandidateNotFoundError,
    CandidatePermissionError,
    CandidateReviewStaleError,
    CandidateReviewTamperedError,
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
from creative_governance.candidates.review_service import CandidateReviewService
from creative_governance.candidates.service import TemplateCandidateService
from creative_governance.candidates.validation_service import CandidateValidationService
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import (
    ComposeEvaluationResult,
    CreativePlan,
    CreativeTier,
    CreativeTierDecision,
    ReuseEvaluationResult,
    SceneIntent,
)
from ai.contracts.creative.template_candidate import (
    CandidatePromotionRecord,
    CandidateReviewDecision,
    CandidateReviewVerdict,
    CandidateStatus,
    CandidateValidationReport,
    PromotionRecordStatus,
    ValidationOverallResult,
    ValidationPhase,
)
from ai.planning.compose_engine import ComposeEngine
from ai.planning.reuse_engine import ReuseEngine
from ai.planning.tier_policy import CreativeTierPolicy
from scripts.core.security.permissions import Action
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend
from scripts.core.template_contract import (
    TemplateRegistryContract,
    get_template_contract,
    invalidate_template_contract_cache,
)
from scripts.core.template_registry_publisher import TemplateRegistryPublisher
from scripts.core.tenant_model import ProjectRecord, TenantContext

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_tenant(
    workspace_id: str = "ws_alpha",
    user_id: str = "usr_alice",
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


@pytest.fixture
def mock_workspace(tmp_path: Path) -> Path:
    """Prepares an isolated mock workspace containing real baseline canonical files."""
    ws = tmp_path / "mock_workspace"
    ws.mkdir(parents=True, exist_ok=True)

    # Registry files
    reg_dir = ws / "registry"
    reg_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-registry-data.json", reg_dir / "template-registry-data.json")
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-registry.tsx", reg_dir / "template-registry.tsx")
    shutil.copy2(WORKSPACE_ROOT / "registry" / "template-aliases.ts", reg_dir / "template-aliases.ts")

    # Contracts
    contracts_dir = ws / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "contracts" / "template-runtime-contract.json", contracts_dir / "template-runtime-contract.json")

    # Catalog
    gt_dir = ws / "ground-truth"
    gt_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WORKSPACE_ROOT / "ground-truth" / "template_catalog.json", gt_dir / "template_catalog.json")

    # Templates
    (ws / "templates" / "scenes").mkdir(parents=True, exist_ok=True)
    (ws / "templates" / "elements").mkdir(parents=True, exist_ok=True)
    (ws / "templates" / "effects").mkdir(parents=True, exist_ok=True)

    return ws


@pytest.fixture
def test_env(tmp_path: Path, mock_workspace: Path):
    """Sets up an end-to-end multi-tenant system environment."""
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    repo = InMemoryTemplateCandidateRepository()
    candidate_service = TemplateCandidateService(repository=repo, storage_service=storage)

    # Register projects
    candidate_service.register_project_for_test(
        ProjectRecord(
            id="proj_alpha_01",
            workspace_id="ws_alpha",
            created_by="usr_alice",
            name="Project Alpha",
        )
    )
    candidate_service.register_project_for_test(
        ProjectRecord(
            id="proj_beta_01",
            workspace_id="ws_beta",
            created_by="usr_bob",
            name="Project Beta",
        )
    )

    val_service = CandidateValidationService(
        candidate_service=candidate_service,
        repository=repo,
        storage_service=storage,
    )
    review_service = CandidateReviewService(
        repository=repo,
        storage_service=storage,
    )
    publisher = TemplateRegistryPublisher(workspace_root=mock_workspace)
    promotion_service = PromotionService(
        repository=repo,
        storage_service=storage,
        registry_publisher=publisher,
    )

    return {
        "storage": storage,
        "repo": repo,
        "candidate_service": candidate_service,
        "val_service": val_service,
        "review_service": review_service,
        "publisher": publisher,
        "promotion_service": promotion_service,
        "mock_workspace": mock_workspace,
    }


def make_policy_for_workspace(ws_path: Path) -> CreativeTierPolicy:
    """Builds a real CreativeTierPolicy bound to the mock workspace registry."""
    contract = get_template_contract(contract_path=ws_path / "contracts" / "template-runtime-contract.json", reload=True)
    reuse_engine = ReuseEngine(
        template_contract=contract,
        registry_data_path=ws_path / "registry" / "template-registry-data.json",
        catalog_path=ws_path / "ground-truth" / "template_catalog.json",
    )
    compose_engine = ComposeEngine(
        template_contract=contract,
    )
    return CreativeTierPolicy(reuse_engine=reuse_engine, compose_engine=compose_engine)


HEALTHY_COMPONENT_SOURCE = """
import React from 'react';
import { AbsoluteFill } from 'remotion';

export interface ArchitectureDiagramProps {
  title: string;
  nodesCount?: number;
}

export const ArchitectureDiagram: React.FC<ArchitectureDiagramProps> = ({ title, nodesCount = 3 }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#101428', justifyContent: 'center', alignItems: 'center' }}>
      <h1 style={{ fontSize: 52, color: '#38BDF8', fontFamily: 'sans-serif' }}>{title}</h1>
      <p style={{ fontSize: 24, color: '#F1F5F9' }}>Active Nodes: {nodesCount}</p>
    </AbsoluteFill>
  );
};
"""

HEALTHY_COMPONENT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "nodesCount": {"type": "number", "minimum": 1, "maximum": 10},
        "architecture_nodes": {"type": "array"},
        "diagram_connectors": {"type": "array"},
    },
    "required": ["title"],
    "aspect_ratios": ["9:16", "16:9"],
    "fps": 30,
    "durationInFrames": 30,
}

HEALTHY_COMPONENT_FIXTURES = {
    "title": "Cloud Distributed Topology",
    "nodesCount": 4,
    "architecture_nodes": ["Gateway", "Service", "Database"],
    "diagram_connectors": ["HTTP", "gRPC"],
}


# =============================================================================
# 1. HAPPY PATH: FULL CREATE E2E & REUSE LEARNING LOOP
# =============================================================================

def test_full_create_to_reuse_learning_loop_e2e(test_env):
    """
    Core Mission Test:
    Project A -> REUSE fail -> COMPOSE fail -> NEEDS_CREATE -> Candidate DRAFT
    -> Static PASS -> Runtime PASS -> Human Review -> APPROVED -> Promotion -> PROMOTED
    -> Project B -> REUSE search discovers promoted template -> Uses it without CREATE!
    """
    env = test_env
    ws_path = env["mock_workspace"]
    cand_service = env["candidate_service"]
    val_service = env["val_service"]
    rev_service = env["review_service"]
    prom_service = env["promotion_service"]

    # Tenants
    tenant_creator = make_tenant("ws_alpha", "usr_alice", Role.EDITOR)
    tenant_reviewer = make_tenant("ws_alpha", "usr_carol", Role.REVIEWER)
    tenant_admin = make_tenant("ws_alpha", "usr_dave", Role.ADMIN)
    tenant_project_b = make_tenant("ws_beta", "usr_bob", Role.EDITOR)

    # -------------------------------------------------------------------------
    # STAGE 1: Project A S28-06 Decision (NEEDS_CREATE)
    # -------------------------------------------------------------------------
    policy_a = make_policy_for_workspace(ws_path)
    intent_a = SceneIntent(
        scene_id="scene_alpha_hero",
        scene_index=0,
        intent_label="system_architecture_diagram",
        primary_visual_job="architecture_flow",
        template_requirements=["architecture_nodes", "diagram_connectors"],
        motion_personality="Cinematic",
        mood="Cinematic",
        estimated_duration_sec=1.0,
    )
    decision_a = policy_a.decide(scene_intent=intent_a, aspect_ratio="9:16")

    assert decision_a.selected_tier == CreativeTier.CREATE, "Policy must select CREATE when REUSE & COMPOSE fail"
    assert decision_a.needs_create_evaluation is True
    assert decision_a.reuse_result.sufficiency is False
    assert decision_a.compose_result.sufficiency is False
    assert decision_a.template_ref is None

    # -------------------------------------------------------------------------
    # STAGE 2: Candidate Created (Starts strictly as DRAFT)
    # -------------------------------------------------------------------------
    cand = cand_service.create_candidate(
        tenant_context=tenant_creator,
        source_project_id="proj_alpha_01",
        creative_plan="cplan_alpha_001",
        tier_decision=decision_a,
        source_code=HEALTHY_COMPONENT_SOURCE,
        template_schema=HEALTHY_COMPONENT_SCHEMA,
        dependencies=[],
        fixtures=HEALTHY_COMPONENT_FIXTURES,
        name="ArchitectureDiagram",
        description="Scalable distributed architecture visualization.",
        proposed_category="scenes",
        proposed_tags=["architecture_nodes", "diagram_connectors", "system_architecture_diagram"],
    )

    assert cand.status == CandidateStatus.DRAFT, "Candidate must start strictly as DRAFT"
    assert cand.revision == 1
    assert cand.content_hash != ""
    assert cand.workspace_id == "ws_alpha"
    assert cand.source_project_id == "proj_alpha_01"

    # -------------------------------------------------------------------------
    # STAGE 3: Static Validation (STATIC_PASS -> VALIDATING, Never VALIDATED)
    # -------------------------------------------------------------------------
    static_report = val_service.validate_candidate_static(tenant_creator, cand.candidate_id)

    assert static_report.phase == ValidationPhase.STATIC
    assert static_report.overall_result == ValidationOverallResult.PASS
    assert len(static_report.gates) == 6

    cand_after_static = cand_service.get_candidate(tenant_creator, cand.candidate_id)
    assert cand_after_static.status == CandidateStatus.VALIDATING, "STATIC_PASS must transition to VALIDATING"
    assert cand_after_static.status != CandidateStatus.VALIDATED, "Static validation must NEVER set VALIDATED"

    # -------------------------------------------------------------------------
    # STAGE 4: Runtime Validation (RUNTIME_PASS -> VALIDATED, Never APPROVED)
    # -------------------------------------------------------------------------
    runtime_report = val_service.validate_candidate_runtime(tenant_creator, cand.candidate_id)

    assert runtime_report.phase == ValidationPhase.RUNTIME
    assert runtime_report.overall_result == ValidationOverallResult.PASS
    assert len(runtime_report.gates) == 5
    assert len(runtime_report.evidence_refs) > 0

    cand_after_runtime = cand_service.get_candidate(tenant_creator, cand.candidate_id)
    assert cand_after_runtime.status == CandidateStatus.VALIDATED, "RUNTIME_PASS must transition to VALIDATED"
    assert cand_after_runtime.status != CandidateStatus.APPROVED, "Runtime validation must NEVER set APPROVED"
    assert cand_after_runtime.status != CandidateStatus.PROMOTED, "Runtime validation must NEVER set PROMOTED"

    # -------------------------------------------------------------------------
    # STAGE 5: Human Review & Approval (AWAITING_APPROVAL -> APPROVED)
    # -------------------------------------------------------------------------
    # 5a. Open Review & Freeze Bundle
    review_bundle = rev_service.open_review(tenant_reviewer, cand.candidate_id, cand_after_runtime.revision)
    assert review_bundle.review_bundle_id != ""
    assert review_bundle.review_bundle_hash != ""

    cand_in_review = cand_service.get_candidate(tenant_creator, cand.candidate_id)
    assert cand_in_review.status == CandidateStatus.AWAITING_APPROVAL

    # 5b. Human Reviewer (Carol, NOT creator Alice) Approves
    approval_decision = rev_service.approve(
        tenant_context=tenant_reviewer,
        candidate_id=cand.candidate_id,
        review_bundle_id=review_bundle.review_bundle_id,
        expected_revision=cand_in_review.revision,
        reason="Architecture component visually verified, compliant with Remotion runtime standards.",
    )
    assert approval_decision.decision == CandidateReviewVerdict.APPROVED
    assert approval_decision.reviewer_principal_id == "usr_carol"

    cand_approved = cand_service.get_candidate(tenant_creator, cand.candidate_id)
    assert cand_approved.status == CandidateStatus.APPROVED, "Approval must transition to APPROVED"
    assert cand_approved.status != CandidateStatus.PROMOTED, "Approval must NEVER set PROMOTED"

    # -------------------------------------------------------------------------
    # STAGE 6: Authorized Promotion (APPROVED -> PROMOTED & Canonical Commit)
    # -------------------------------------------------------------------------
    target_id = "system-architecture-diagram"
    promotion_record = prom_service.promote_candidate(
        tenant_context=tenant_admin,
        candidate_id=cand.candidate_id,
        target_template_id=target_id,
        expected_revision=cand_approved.revision,
        target_template_version="1.0.0",
    )

    assert promotion_record.status == PromotionRecordStatus.COMMITTED
    assert promotion_record.target_template_id == target_id

    cand_promoted = cand_service.get_candidate(tenant_creator, cand.candidate_id)
    assert cand_promoted.status == CandidateStatus.PROMOTED

    # Assert canonical disk state was updated
    reg_data = json.loads((ws_path / "registry" / "template-registry-data.json").read_text(encoding="utf-8"))
    assert target_id in reg_data["templates"]

    contract_data = json.loads((ws_path / "contracts" / "template-runtime-contract.json").read_text(encoding="utf-8"))
    assert target_id in contract_data["templates"]
    assert "SystemArchitectureDiagram" in contract_data["aliases"]

    catalog_data = json.loads((ws_path / "ground-truth" / "template_catalog.json").read_text(encoding="utf-8"))
    cat_entry = next((item for item in catalog_data if item.get("id") == target_id), None)
    assert cat_entry is not None
    assert "architecture_nodes" in cat_entry.get("capabilities", [])

    component_dest = ws_path / "templates" / "scenes" / "SystemArchitectureDiagram.tsx"
    assert component_dest.exists()

    # -------------------------------------------------------------------------
    # STAGE 7: FRESH PROJECT LEARNING TEST (Project B Reuses Promoted Template)
    # -------------------------------------------------------------------------
    # Project B is in Workspace B, requesting the same capability
    policy_b = make_policy_for_workspace(ws_path)
    intent_b = SceneIntent(
        scene_id="scene_beta_overview",
        scene_index=0,
        intent_label="system_architecture_diagram",
        primary_visual_job="architecture_flow",
        template_requirements=["architecture_nodes", "diagram_connectors"],
        motion_personality="Cinematic",
        mood="Cinematic",
        estimated_duration_sec=1.0,
    )

    decision_b = policy_b.decide(scene_intent=intent_b, aspect_ratio="9:16")

    # PROVE THE LEARNING LOOP!
    assert decision_b.selected_tier == CreativeTier.REUSE, (
        f"Project B must discover and select REUSE tier for promoted template! Got '{decision_b.selected_tier}'"
    )
    assert decision_b.template_ref == target_id, (
        f"Project B template_ref must be '{target_id}', got '{decision_b.template_ref}'"
    )
    assert decision_b.needs_create_evaluation is False
    assert decision_b.reuse_result.sufficiency is True
    assert decision_b.compose_result is None, "Project B must NOT evaluate or enter COMPOSE"

    # -------------------------------------------------------------------------
    # STAGE 8: Full Cryptographic Lineage & Provenance Traceability
    # -------------------------------------------------------------------------
    # 1. Project A -> Decision A
    assert decision_a.decision_id == cand.creative_tier_decision_reference

    # 2. Candidate content hash immutability across validation & review
    assert cand.content_hash == static_report.candidate_content_hash
    assert cand.content_hash == runtime_report.candidate_content_hash
    assert cand.content_hash == review_bundle.candidate_content_hash
    assert cand.content_hash == approval_decision.candidate_content_hash

    # 3. Static & Runtime Report digests bound in ReviewBundle
    assert review_bundle.static_validation_id == static_report.validation_id
    assert review_bundle.runtime_validation_id == runtime_report.validation_id

    # 4. ReviewBundle hash bound in ApprovalDecision and PromotionRecord
    assert approval_decision.review_bundle_hash == review_bundle.review_bundle_hash
    assert promotion_record.review_bundle_hash == review_bundle.review_bundle_hash
    assert promotion_record.approval_decision_id == approval_decision.decision_id

    # 5. Promoted Template ID bound to Project B Decision
    assert promotion_record.target_template_id == decision_b.template_ref


# =============================================================================
# 2. PROMOTION VISIBILITY ACROSS ALL READERS
# =============================================================================

def test_promotion_visibility_and_deterministic_cache_invalidation(test_env):
    """
    Section 7: Validates that promotion immediately invalidates singleton caches
    so downstream consumers (contract, catalog, reuse engine) observe the new state.
    """
    env = test_env
    ws_path = env["mock_workspace"]
    prom_service = env["promotion_service"]
    cand_service = env["candidate_service"]
    val_service = env["val_service"]
    rev_service = env["review_service"]

    tenant_admin = make_tenant("ws_alpha", "usr_admin", Role.ADMIN)
    tenant_reviewer = make_tenant("ws_alpha", "usr_rev", Role.REVIEWER)

    # 1. Prime the singleton contract cache before promotion
    initial_contract = get_template_contract(contract_path=ws_path / "contracts" / "template-runtime-contract.json", reload=True)
    assert not initial_contract.is_valid("dynamic-stats-counter")

    # 2. Create and advance candidate to APPROVED
    cand = cand_service.create_candidate(
        tenant_context=tenant_admin,
        source_project_id="proj_alpha_01",
        creative_plan="cplan_vis_001",
        tier_decision=CreativeTierDecision(
            decision_id="dec_vis_001",
            scene_id="s1",
            selected_tier=CreativeTier.CREATE,
            rationale="Dynamic counter",
            needs_create_evaluation=True,
            reuse_result=ReuseEvaluationResult(need_description="test", candidates_checked=[], eligible_candidates=[], ranked_candidates=[], selected_candidate=None, rejection_reasons={}, sufficiency=False, rationale="fail"),
            compose_result=ComposeEvaluationResult(need_description="test", components_checked=[], eligible_components=[], composition_plan=None, rejection_reasons=["insufficient"], sufficiency=False, rationale="fail"),
        ),
        source_code=HEALTHY_COMPONENT_SOURCE,
        template_schema=HEALTHY_COMPONENT_SCHEMA,
        dependencies=[],
        fixtures=HEALTHY_COMPONENT_FIXTURES,
        name="StatsCounter",
        description="Dynamic stats counter",
        proposed_category="elements",
        proposed_tags=["stats", "counter"],
    )
    val_service.validate_candidate_static(tenant_admin, cand.candidate_id)
    val_service.validate_candidate_runtime(tenant_admin, cand.candidate_id)
    bundle = rev_service.open_review(tenant_admin, cand.candidate_id, cand.revision)
    rev_service.approve(tenant_reviewer, cand.candidate_id, bundle.review_bundle_id, cand.revision)

    # 3. Promote candidate
    prom_service.promote_candidate(
        tenant_context=tenant_admin,
        candidate_id=cand.candidate_id,
        target_template_id="dynamic-stats-counter",
        expected_revision=cand.revision,
    )

    # 4. Verify downstream readers immediately see the new template without manual restarts
    # 4a. Contract singleton
    refreshed_contract = get_template_contract()
    assert refreshed_contract.is_valid("dynamic-stats-counter"), "Contract singleton must reflect promoted template immediately"
    assert refreshed_contract.canonicalize("DynamicStatsCounter") == "dynamic-stats-counter"

    # 4b. Catalog reader
    catalog_items = json.loads((ws_path / "ground-truth" / "template_catalog.json").read_text(encoding="utf-8"))
    assert any(item["id"] == "dynamic-stats-counter" for item in catalog_items)

    # 4c. ReuseEngine reader
    engine = ReuseEngine(
        template_contract=refreshed_contract,
        registry_data_path=ws_path / "registry" / "template-registry-data.json",
        catalog_path=ws_path / "ground-truth" / "template_catalog.json",
    )
    assert "dynamic-stats-counter" in engine._template_metadata


# =============================================================================
# 3. TENANT ISOLATION: PRIVATE CANDIDATE EVIDENCE VS SHARED CANONICAL TEMPLATE
# =============================================================================

def test_tenant_isolation_private_evidence_vs_shared_canonical_template(test_env):
    """
    Section 16:
    Workspace A candidate and evidence are 100% tenant-isolated from Workspace B.
    Workspace B cannot read, validate, review, approve, or promote Candidate A.
    However, once promoted to the Canonical Registry, Workspace B normal REUSE can
    safely discover the public canonical template without leaking Workspace A private evidence.
    """
    env = test_env
    ws_path = env["mock_workspace"]
    cand_service = env["candidate_service"]
    val_service = env["val_service"]
    rev_service = env["review_service"]
    prom_service = env["promotion_service"]

    tenant_a_user = make_tenant("ws_alpha", "usr_alice", Role.EDITOR)
    tenant_a_reviewer = make_tenant("ws_alpha", "usr_carol", Role.REVIEWER)
    tenant_a_admin = make_tenant("ws_alpha", "usr_dave", Role.ADMIN)
    tenant_b_user = make_tenant("ws_beta", "usr_bob", Role.ADMIN)

    # 1. Create candidate in Workspace A
    cand_a = cand_service.create_candidate(
        tenant_context=tenant_a_user,
        source_project_id="proj_alpha_01",
        creative_plan="cplan_alpha_tenant",
        tier_decision=CreativeTierDecision(
            decision_id="dec_tenant_01",
            scene_id="s1",
            selected_tier=CreativeTier.CREATE,
            rationale="Novel component",
            needs_create_evaluation=True,
            reuse_result=ReuseEvaluationResult(need_description="test", candidates_checked=[], eligible_candidates=[], ranked_candidates=[], selected_candidate=None, rejection_reasons={}, sufficiency=False, rationale="fail"),
            compose_result=ComposeEvaluationResult(need_description="test", components_checked=[], eligible_components=[], composition_plan=None, rejection_reasons=["insufficient"], sufficiency=False, rationale="fail"),
        ),
        source_code=HEALTHY_COMPONENT_SOURCE,
        template_schema=HEALTHY_COMPONENT_SCHEMA,
        dependencies=[],
        fixtures=HEALTHY_COMPONENT_FIXTURES,
        name="GlobalSharedCard",
        description="Private evidence with shared target",
        proposed_category="elements",
        proposed_tags=["shared_card", "global_card"],
    )

    val_service.validate_candidate_static(tenant_a_user, cand_a.candidate_id)
    val_service.validate_candidate_runtime(tenant_a_user, cand_a.candidate_id)
    bundle = rev_service.open_review(tenant_a_reviewer, cand_a.candidate_id, cand_a.revision)

    # 2. Probe cross-tenant violations by Workspace B
    with pytest.raises(CandidateNotFoundError):
        cand_service.get_candidate(tenant_b_user, cand_a.candidate_id)

    with pytest.raises(CandidateNotFoundError):
        val_service.validate_candidate_static(tenant_b_user, cand_a.candidate_id)

    with pytest.raises(CandidateNotFoundError):
        val_service.validate_candidate_runtime(tenant_b_user, cand_a.candidate_id)

    with pytest.raises(CandidateNotFoundError):
        rev_service.open_review(tenant_b_user, cand_a.candidate_id, cand_a.revision)

    with pytest.raises((CandidateNotFoundError, CandidateTenantMismatchError)):
        rev_service.approve(tenant_b_user, cand_a.candidate_id, bundle.review_bundle_id, cand_a.revision)

    with pytest.raises(CandidateNotFoundError):
        prom_service.promote_candidate(tenant_b_user, cand_a.candidate_id, "global-shared-card", cand_a.revision)

    # 3. Workspace A approves and promotes
    rev_service.approve(tenant_a_reviewer, cand_a.candidate_id, bundle.review_bundle_id, cand_a.revision)
    prom_service.promote_candidate(tenant_a_admin, cand_a.candidate_id, "global-shared-card", cand_a.revision)

    # 4. After Promotion:
    # 4a. Private candidate evidence still DENIED to Workspace B
    with pytest.raises(CandidateNotFoundError):
        cand_service.get_candidate(tenant_b_user, cand_a.candidate_id)

    assert prom_service.get_candidate_promotion(tenant_b_user, cand_a.candidate_id) is None

    # 4b. But published Canonical Registry is globally visible and usable in Workspace B
    policy_b = make_policy_for_workspace(ws_path)
    intent_b = SceneIntent(
        scene_id="s_b_shared",
        scene_index=0,
        intent_label="global_card",
        primary_visual_job="shared_card",
        template_requirements=["shared_card", "global_card"],
        motion_personality="Cinematic",
        mood="Cinematic",
        estimated_duration_sec=1.0,
    )
    decision_b = policy_b.decide(scene_intent=intent_b, aspect_ratio="9:16")
    assert decision_b.selected_tier == CreativeTier.REUSE
    assert decision_b.template_ref == "global-shared-card"


# =============================================================================
# 4. LIFECYCLE TRANSITION AUDIT (Illegal Transitions Denied)
# =============================================================================

def test_lifecycle_state_audit_illegal_transitions_denied(test_env):
    """
    Section 13: Verifies that transitions outside the legal lifecycle:
    DRAFT -> VALIDATING -> VALIDATED -> AWAITING_APPROVAL -> APPROVED -> PROMOTED
    fail closed.
    """
    env = test_env
    cand_service = env["candidate_service"]
    val_service = env["val_service"]
    rev_service = env["review_service"]
    prom_service = env["promotion_service"]

    tenant_user = make_tenant("ws_alpha", "usr_alice", Role.EDITOR)
    tenant_reviewer = make_tenant("ws_alpha", "usr_carol", Role.REVIEWER)
    tenant_admin = make_tenant("ws_alpha", "usr_dave", Role.ADMIN)

    # 1. DRAFT state
    cand = cand_service.create_candidate(
        tenant_context=tenant_user,
        source_project_id="proj_alpha_01",
        creative_plan="cplan_trans_01",
        tier_decision=CreativeTierDecision(
            decision_id="dec_trans_01",
            scene_id="s1",
            selected_tier=CreativeTier.CREATE,
            rationale="Test",
            needs_create_evaluation=True,
            reuse_result=ReuseEvaluationResult(need_description="t", candidates_checked=[], eligible_candidates=[], ranked_candidates=[], selected_candidate=None, rejection_reasons={}, sufficiency=False, rationale="f"),
            compose_result=ComposeEvaluationResult(need_description="t", components_checked=[], eligible_components=[], composition_plan=None, rejection_reasons=["insufficient"], sufficiency=False, rationale="f"),
        ),
        source_code=HEALTHY_COMPONENT_SOURCE,
        template_schema=HEALTHY_COMPONENT_SCHEMA,
        dependencies=[],
        fixtures=HEALTHY_COMPONENT_FIXTURES,
        name="TransitionProbe",
    )
    assert cand.status == CandidateStatus.DRAFT

    # Illegal from DRAFT:
    with pytest.raises(CandidateInvalidStatusError):
        # DRAFT -> VALIDATED directly
        val_service.validate_candidate_runtime(tenant_user, cand.candidate_id)

    with pytest.raises(CandidateInvalidStatusError):
        # DRAFT -> AWAITING_APPROVAL directly
        rev_service.open_review(tenant_reviewer, cand.candidate_id, cand.revision)

    with pytest.raises(PromotionPreconditionError):
        # DRAFT -> PROMOTED directly
        prom_service.promote_candidate(tenant_admin, cand.candidate_id, "trans-probe", cand.revision)

    # 2. VALIDATING state
    val_service.validate_candidate_static(tenant_user, cand.candidate_id)
    cand_validating = cand_service.get_candidate(tenant_user, cand.candidate_id)
    assert cand_validating.status == CandidateStatus.VALIDATING

    # Illegal from VALIDATING:
    with pytest.raises(CandidateInvalidStatusError):
        # VALIDATING -> AWAITING_APPROVAL directly
        rev_service.open_review(tenant_reviewer, cand.candidate_id, cand.revision)

    with pytest.raises(PromotionPreconditionError):
        # VALIDATING -> PROMOTED directly
        prom_service.promote_candidate(tenant_admin, cand.candidate_id, "trans-probe", cand.revision)

    # 3. VALIDATED state
    val_service.validate_candidate_runtime(tenant_user, cand.candidate_id)
    cand_validated = cand_service.get_candidate(tenant_user, cand.candidate_id)
    assert cand_validated.status == CandidateStatus.VALIDATED

    # Illegal from VALIDATED:
    with pytest.raises(PromotionPreconditionError):
        # VALIDATED -> PROMOTED directly (bypassing review & approval)
        prom_service.promote_candidate(tenant_admin, cand.candidate_id, "trans-probe", cand.revision)

    # 4. AWAITING_APPROVAL state
    bundle = rev_service.open_review(tenant_reviewer, cand.candidate_id, cand.revision)
    cand_awaiting = cand_service.get_candidate(tenant_user, cand.candidate_id)
    assert cand_awaiting.status == CandidateStatus.AWAITING_APPROVAL

    # Illegal from AWAITING_APPROVAL:
    with pytest.raises(PromotionPreconditionError):
        # AWAITING_APPROVAL -> PROMOTED directly (bypassing human approval)
        prom_service.promote_candidate(tenant_admin, cand.candidate_id, "trans-probe", cand.revision)


# =============================================================================
# 5. REJECTED CANDIDATE IS BLOCKED FROM PROMOTION AND REUSE
# =============================================================================

def test_rejected_candidate_cannot_be_promoted_or_reused(test_env):
    """
    Section 14:
    A candidate rejected by the reviewer transitions to REJECTED.
    It cannot be promoted, cannot mutate the registry, and cannot be reused.
    """
    env = test_env
    ws_path = env["mock_workspace"]
    cand_service = env["candidate_service"]
    val_service = env["val_service"]
    rev_service = env["review_service"]
    prom_service = env["promotion_service"]

    tenant_user = make_tenant("ws_alpha", "usr_alice", Role.EDITOR)
    tenant_reviewer = make_tenant("ws_alpha", "usr_carol", Role.REVIEWER)
    tenant_admin = make_tenant("ws_alpha", "usr_dave", Role.ADMIN)

    cand = cand_service.create_candidate(
        tenant_context=tenant_user,
        source_project_id="proj_alpha_01",
        creative_plan="cplan_rej_01",
        tier_decision=CreativeTierDecision(
            decision_id="dec_rej_01",
            scene_id="s1",
            selected_tier=CreativeTier.CREATE,
            rationale="Rejection test",
            needs_create_evaluation=True,
            reuse_result=ReuseEvaluationResult(need_description="test", candidates_checked=[], eligible_candidates=[], ranked_candidates=[], selected_candidate=None, rejection_reasons={}, sufficiency=False, rationale="fail"),
            compose_result=ComposeEvaluationResult(need_description="test", components_checked=[], eligible_components=[], composition_plan=None, rejection_reasons=["insufficient"], sufficiency=False, rationale="fail"),
        ),
        source_code=HEALTHY_COMPONENT_SOURCE,
        template_schema=HEALTHY_COMPONENT_SCHEMA,
        dependencies=[],
        fixtures=HEALTHY_COMPONENT_FIXTURES,
        name="RejectedComponent",
        proposed_tags=["rejected_tag"],
    )

    val_service.validate_candidate_static(tenant_user, cand.candidate_id)
    val_service.validate_candidate_runtime(tenant_user, cand.candidate_id)
    bundle = rev_service.open_review(tenant_reviewer, cand.candidate_id, cand.revision)

    # Reviewer rejects candidate
    rejection_decision = rev_service.reject(
        tenant_context=tenant_reviewer,
        candidate_id=cand.candidate_id,
        review_bundle_id=bundle.review_bundle_id,
        expected_revision=cand.revision,
        reason="Component visual contrast violates brand palette standards.",
    )
    assert rejection_decision.decision == CandidateReviewVerdict.REJECTED

    cand_rejected = cand_service.get_candidate(tenant_user, cand.candidate_id)
    assert cand_rejected.status == CandidateStatus.REJECTED

    # Attempted promotion MUST FAIL
    with pytest.raises(PromotionPreconditionError):
        prom_service.promote_candidate(
            tenant_context=tenant_admin,
            candidate_id=cand.candidate_id,
            target_template_id="rejected-component",
            expected_revision=cand_rejected.revision,
        )

    # Verify not registered and not in REUSE
    contract = get_template_contract(contract_path=ws_path / "contracts" / "template-runtime-contract.json")
    assert not contract.is_valid("rejected-component")


# =============================================================================
# 6. FAILED PROMOTION ROLLBACK & RETRY RECOVERY
# =============================================================================

def test_failed_promotion_rollback_and_retry_recovery(test_env, monkeypatch):
    """
    Section 15:
    When promotion encounters an injected failure (e.g. post-publish verification error),
    disk state is cleanly restored, candidate remains APPROVED, and no template is published.
    A subsequent retry without fault succeeds completely, publishing the template and enabling REUSE.
    """
    env = test_env
    ws_path = env["mock_workspace"]
    cand_service = env["candidate_service"]
    val_service = env["val_service"]
    rev_service = env["review_service"]
    prom_service = env["promotion_service"]
    publisher = env["publisher"]

    tenant_user = make_tenant("ws_alpha", "usr_alice", Role.EDITOR)
    tenant_reviewer = make_tenant("ws_alpha", "usr_carol", Role.REVIEWER)
    tenant_admin = make_tenant("ws_alpha", "usr_dave", Role.ADMIN)

    # 1. Setup approved candidate
    cand = cand_service.create_candidate(
        tenant_context=tenant_user,
        source_project_id="proj_alpha_01",
        creative_plan="cplan_rec_01",
        tier_decision=CreativeTierDecision(
            decision_id="dec_rec_01",
            scene_id="s1",
            selected_tier=CreativeTier.CREATE,
            rationale="Recovery test",
            needs_create_evaluation=True,
            reuse_result=ReuseEvaluationResult(need_description="test", candidates_checked=[], eligible_candidates=[], ranked_candidates=[], selected_candidate=None, rejection_reasons={}, sufficiency=False, rationale="fail"),
            compose_result=ComposeEvaluationResult(need_description="test", components_checked=[], eligible_components=[], composition_plan=None, rejection_reasons=["insufficient"], sufficiency=False, rationale="fail"),
        ),
        source_code=HEALTHY_COMPONENT_SOURCE,
        template_schema=HEALTHY_COMPONENT_SCHEMA,
        dependencies=[],
        fixtures=HEALTHY_COMPONENT_FIXTURES,
        name="ResilientCard",
        proposed_category="scenes",
        proposed_tags=["resilient_tag"],
    )
    val_service.validate_candidate_static(tenant_user, cand.candidate_id)
    val_service.validate_candidate_runtime(tenant_user, cand.candidate_id)
    bundle = rev_service.open_review(tenant_reviewer, cand.candidate_id, cand.revision)
    rev_service.approve(tenant_reviewer, cand.candidate_id, bundle.review_bundle_id, cand.revision)

    target_id = "resilient-card"
    pre_reg_bytes = (ws_path / "registry" / "template-registry-data.json").read_bytes()

    # 2. Inject fault during post-publish verification
    def broken_verify(*args, **kwargs):
        raise PromotionRollbackError("Simulated disk verification corrupt header fault.")

    monkeypatch.setattr(publisher, "verify_canonical_publication", broken_verify)

    with pytest.raises(PromotionRollbackError):
        prom_service.promote_candidate(
            tenant_context=tenant_admin,
            candidate_id=cand.candidate_id,
            target_template_id=target_id,
            expected_revision=cand.revision,
        )

    # 3. Assert rollback: candidate is still APPROVED, disk is byte-for-byte restored
    cand_after_fail = cand_service.get_candidate(tenant_user, cand.candidate_id)
    assert cand_after_fail.status == CandidateStatus.APPROVED
    assert (ws_path / "registry" / "template-registry-data.json").read_bytes() == pre_reg_bytes
    assert not (ws_path / "templates" / "scenes" / "ResilientCard.tsx").exists()

    record_failed = prom_service.get_candidate_promotion(tenant_user, cand.candidate_id)
    assert record_failed.status == PromotionRecordStatus.ROLLED_BACK

    # 4. Remove monkeypatch fault and retry promotion
    monkeypatch.undo()

    retry_record = prom_service.promote_candidate(
        tenant_context=tenant_admin,
        candidate_id=cand.candidate_id,
        target_template_id=target_id,
        expected_revision=cand.revision,
    )

    assert retry_record.status == PromotionRecordStatus.COMMITTED
    cand_promoted = cand_service.get_candidate(tenant_user, cand.candidate_id)
    assert cand_promoted.status == CandidateStatus.PROMOTED
    assert (ws_path / "templates" / "scenes" / "ResilientCard.tsx").exists()

    # 5. REUSE discovery after successful recovery
    policy = make_policy_for_workspace(ws_path)
    intent = SceneIntent(
        scene_id="s_retry",
        scene_index=0,
        intent_label="resilient_card",
        primary_visual_job="resilient_tag",
        template_requirements=["resilient_tag"],
        motion_personality="Cinematic",
        mood="Cinematic",
        estimated_duration_sec=1.0,
    )
    decision = policy.decide(scene_intent=intent, aspect_ratio="9:16")
    assert decision.selected_tier == CreativeTier.REUSE
    assert decision.template_ref == target_id


# =============================================================================
# 7. RETRY SAFETY & IDEMPOTENCY ACROSS STAGES
# =============================================================================

def test_retry_safety_and_idempotency_across_stages(test_env):
    """
    Section 12: Tests retry safety across all stages (static validation, runtime validation,
    review open, approval, promotion) without generating duplicate rows or records.
    """
    env = test_env
    cand_service = env["candidate_service"]
    val_service = env["val_service"]
    rev_service = env["review_service"]
    prom_service = env["promotion_service"]

    tenant_user = make_tenant("ws_alpha", "usr_alice", Role.EDITOR)
    tenant_reviewer = make_tenant("ws_alpha", "usr_carol", Role.REVIEWER)
    tenant_admin = make_tenant("ws_alpha", "usr_dave", Role.ADMIN)

    cand = cand_service.create_candidate(
        tenant_context=tenant_user,
        source_project_id="proj_alpha_01",
        creative_plan="cplan_idem_01",
        tier_decision=CreativeTierDecision(
            decision_id="dec_idem_01",
            scene_id="s1",
            selected_tier=CreativeTier.CREATE,
            rationale="Idempotency probe",
            needs_create_evaluation=True,
            reuse_result=ReuseEvaluationResult(need_description="test", candidates_checked=[], eligible_candidates=[], ranked_candidates=[], selected_candidate=None, rejection_reasons={}, sufficiency=False, rationale="fail"),
            compose_result=ComposeEvaluationResult(need_description="test", components_checked=[], eligible_components=[], composition_plan=None, rejection_reasons=["insufficient"], sufficiency=False, rationale="fail"),
        ),
        source_code=HEALTHY_COMPONENT_SOURCE,
        template_schema=HEALTHY_COMPONENT_SCHEMA,
        dependencies=[],
        fixtures=HEALTHY_COMPONENT_FIXTURES,
        name="IdempotentCard",
    )

    # 1. Static validation retry
    rep1 = val_service.validate_candidate_static(tenant_user, cand.candidate_id)
    rep2 = val_service.validate_candidate_static(tenant_user, cand.candidate_id)
    assert rep1.validation_id == rep2.validation_id

    # 2. Runtime validation retry
    rrep1 = val_service.validate_candidate_runtime(tenant_user, cand.candidate_id)
    rrep2 = val_service.validate_candidate_runtime(tenant_user, cand.candidate_id)
    assert rrep1.validation_id == rrep2.validation_id

    # 3. Review open retry
    b1 = rev_service.open_review(tenant_reviewer, cand.candidate_id, cand.revision)
    b2 = rev_service.open_review(tenant_reviewer, cand.candidate_id, cand.revision)
    assert b1.review_bundle_id == b2.review_bundle_id

    # 4. Approval retry
    dec1 = rev_service.approve(tenant_reviewer, cand.candidate_id, b1.review_bundle_id, cand.revision)
    dec2 = rev_service.approve(tenant_reviewer, cand.candidate_id, b1.review_bundle_id, cand.revision)
    assert dec1.decision_id == dec2.decision_id

    # 5. Promotion retry
    prec1 = prom_service.promote_candidate(tenant_admin, cand.candidate_id, "idempotent-card", cand.revision)
    prec2 = prom_service.promote_candidate(tenant_admin, cand.candidate_id, "idempotent-card", cand.revision)
    assert prec1.promotion_id == prec2.promotion_id
    assert prec1.status == PromotionRecordStatus.COMMITTED
