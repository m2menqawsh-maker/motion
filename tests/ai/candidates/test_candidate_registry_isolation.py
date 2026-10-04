"""
tests/ai/candidates/test_candidate_registry_isolation.py
=========================================================
Canonical Registry Isolation Test Suite (S28-07A).

Mandatory Requirement:
Candidate operations (creation, update, storage, listing, deletion)
MUST NOT alter:
- registry/template-registry-data.json
- registry/template-registry.tsx
- contracts/template-runtime-contract.json
- ground-truth/template_catalog.json
- any source file in templates/
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import pytest
from datetime import datetime, timezone

from ai.contracts.creative.plan import (
    CreativePlan,
    CreativePlanStatus,
    CreativeTier,
    CreativeTierDecision,
    ComposeEvaluationResult,
    ReuseEvaluationResult,
)
from ai.contracts.common import ProvenanceRecord
from creative_governance.candidates.service import TemplateCandidateService
from creative_governance.candidates.validation_service import CandidateValidationService
from creative_governance.candidates.repository import InMemoryTemplateCandidateRepository
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.tenant_model import TenantContext, ProjectRecord
from scripts.core.storage import LocalStorageBackend

ROOT = Path(__file__).resolve().parents[3]


def _hash_file(path: Path) -> str:
    if not path.exists():
        return "NON_EXISTENT"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_directory(dir_path: Path) -> dict[str, str]:
    if not dir_path.exists():
        return {}
    res = {}
    for p in sorted(dir_path.rglob("*")):
        if p.is_file() and not p.name.endswith(".pyc") and "__pycache__" not in str(p):
            rel = str(p.relative_to(dir_path))
            res[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return res


def test_candidate_flow_never_mutates_canonical_registry(tmp_path, valid_create_decision, valid_creative_plan):
    # 1. Snapshot canonical registry state before candidate execution
    registry_data_path = ROOT / "registry" / "template-registry-data.json"
    registry_tsx_path = ROOT / "registry" / "template-registry.tsx"
    runtime_contract_path = ROOT / "contracts" / "template-runtime-contract.json"
    catalog_path = ROOT / "ground-truth" / "template_catalog.json"
    templates_dir = ROOT / "templates"

    snap_reg_data = _hash_file(registry_data_path)
    snap_reg_tsx = _hash_file(registry_tsx_path)
    snap_runtime = _hash_file(runtime_contract_path)
    snap_catalog = _hash_file(catalog_path)
    snap_templates = _hash_directory(templates_dir)

    # 2. Execute candidate operations
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    repo = InMemoryTemplateCandidateRepository()
    service = TemplateCandidateService(repository=repo, storage_service=storage)

    tenant = TenantContext(
        workspace_id="ws_iso_test",
        user_id="usr_iso",
        role=Role.EDITOR,
        principal=Principal(
            principal_id="usr_iso",
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        ),
    )
    service.register_project_for_test(
        ProjectRecord(id="prj_iso", workspace_id="ws_iso_test", created_by="usr_iso", name="Iso Proj")
    )

    # Create candidate
    cand = service.create_candidate(
        tenant_context=tenant,
        source_project_id="prj_iso",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const Novel = () => <div>Novel Candidate</div>;",
        fixtures={"prop": 1},
    )

    # Update candidate
    service.update_draft_candidate(
        tenant_context=tenant,
        candidate_id=cand.candidate_id,
        expected_revision=1,
        source_code="export const NovelUpdated = () => <div>Updated Candidate</div>;",
    )

    # 3. Snapshot canonical registry state after candidate execution
    post_reg_data = _hash_file(registry_data_path)
    post_reg_tsx = _hash_file(registry_tsx_path)
    post_runtime = _hash_file(runtime_contract_path)
    post_catalog = _hash_file(catalog_path)
    post_templates = _hash_directory(templates_dir)

    # 4. Mandatory Invariant Assertions
    assert snap_reg_data == post_reg_data, "Canonical registry/template-registry-data.json was mutated!"
    assert snap_reg_tsx == post_reg_tsx, "Canonical registry/template-registry.tsx was mutated!"
    assert snap_runtime == post_runtime, "Canonical contracts/template-runtime-contract.json was mutated!"
    assert snap_catalog == post_catalog, "Canonical ground-truth/template_catalog.json was mutated!"
    assert snap_templates == post_templates, "Canonical templates/ directory was mutated!"


def test_static_validation_flow_never_mutates_canonical_registry(tmp_path, valid_create_decision, valid_creative_plan):
    # 1. Snapshot canonical registry state before validation execution
    registry_data_path = ROOT / "registry" / "template-registry-data.json"
    registry_tsx_path = ROOT / "registry" / "template-registry.tsx"
    runtime_contract_path = ROOT / "contracts" / "template-runtime-contract.json"
    catalog_path = ROOT / "ground-truth" / "template_catalog.json"
    templates_dir = ROOT / "templates"

    snap_reg_data = _hash_file(registry_data_path)
    snap_reg_tsx = _hash_file(registry_tsx_path)
    snap_runtime = _hash_file(runtime_contract_path)
    snap_catalog = _hash_file(catalog_path)
    snap_templates = _hash_directory(templates_dir)

    # 2. Execute candidate operations and static validation
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    repo = InMemoryTemplateCandidateRepository()
    candidate_service = TemplateCandidateService(repository=repo, storage_service=storage)
    validation_service = CandidateValidationService(
        repository=repo,
        storage_service=storage,
        candidate_service=candidate_service,
    )

    tenant = TenantContext(
        workspace_id="ws_iso_val",
        user_id="usr_iso_val",
        role=Role.EDITOR,
        principal=Principal(
            principal_id="usr_iso_val",
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        ),
    )
    candidate_service.register_project_for_test(
        ProjectRecord(id="prj_iso_val", workspace_id="ws_iso_val", created_by="usr_iso_val", name="Iso Val Proj")
    )

    valid_code = (
        'import React from "react";\n'
        'export interface NovelProps { title: string; }\n'
        'export const NovelCandidate: React.FC<NovelProps> = ({ title }) => <div>{title}</div>;\n'
    )
    valid_schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}},
        "required": ["title"],
    }
    cand = candidate_service.create_candidate(
        tenant_context=tenant,
        source_project_id="prj_iso_val",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code=valid_code,
        template_schema=valid_schema,
        fixtures={"title": "Hello Isolation"},
    )

    # Run static validation
    report = validation_service.validate_candidate_static(
        tenant_context=tenant,
        candidate_id=cand.candidate_id,
    )
    assert report.overall_result.value == "PASS"

    # 3. Snapshot canonical registry state after validation execution
    post_reg_data = _hash_file(registry_data_path)
    post_reg_tsx = _hash_file(registry_tsx_path)
    post_runtime = _hash_file(runtime_contract_path)
    post_catalog = _hash_file(catalog_path)
    post_templates = _hash_directory(templates_dir)

    # 4. Mandatory Invariant Assertions
    assert snap_reg_data == post_reg_data, "Canonical registry/template-registry-data.json was mutated!"
    assert snap_reg_tsx == post_reg_tsx, "Canonical registry/template-registry.tsx was mutated!"
    assert snap_runtime == post_runtime, "Canonical contracts/template-runtime-contract.json was mutated!"
    assert snap_catalog == post_catalog, "Canonical ground-truth/template_catalog.json was mutated!"
    assert snap_templates == post_templates, "Canonical templates/ directory was mutated!"


def test_review_and_approval_flow_never_mutates_canonical_registry(tmp_path):
    """
    S28-07D Invariant Test:
    Candidate review opening and approval MUST NOT alter:
    - registry/template-registry-data.json
    - registry/template-registry.tsx
    - contracts/template-runtime-contract.json
    - ground-truth/template_catalog.json
    - any source file in templates/
    """
    from creative_governance.candidates.review_service import CandidateReviewService
    from ai.contracts.creative.template_candidate import (
        TemplateCandidate,
        CandidateStatus,
        CandidateValidationReport,
        ValidationPhase,
        ValidationOverallResult,
        CandidateGateResult,
        GateStatus,
        CandidateReviewVerdict,
    )
    from creative_governance.candidates.hashing import compute_candidate_content_hash

    # 1. Snapshot canonical registry state before review/approval execution
    registry_data_path = ROOT / "registry" / "template-registry-data.json"
    registry_tsx_path = ROOT / "registry" / "template-registry.tsx"
    runtime_contract_path = ROOT / "contracts" / "template-runtime-contract.json"
    catalog_path = ROOT / "ground-truth" / "template_catalog.json"
    templates_dir = ROOT / "templates"

    snap_reg_data = _hash_file(registry_data_path)
    snap_reg_tsx = _hash_file(registry_tsx_path)
    snap_runtime = _hash_file(runtime_contract_path)
    snap_catalog = _hash_file(catalog_path)
    snap_templates = _hash_directory(templates_dir)

    # 2. Setup candidate in VALIDATED state with static and runtime pass reports
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    repo = InMemoryTemplateCandidateRepository()
    review_service = CandidateReviewService(repository=repo, storage_service=storage)

    workspace_id = "ws_iso_review"
    candidate_id = "cand_iso_review_001"
    now = datetime.now(timezone.utc).isoformat()
    source_code = "export const IsoReview = () => <div>Iso Review</div>;"
    schema = {"type": "object", "properties": {"msg": {"type": "string"}}}
    fixtures = {"msg": "iso"}
    deps = ["framer-motion"]

    content_hash = compute_candidate_content_hash(
        source_code=source_code,
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        why_reuse_failed="none",
        why_compose_failed="none",
        creative_plan_reference="cplan_iso",
        creative_tier_decision_reference="tier_iso",
    )

    candidate = TemplateCandidate(
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        source_project_id="prj_iso_rev",
        creator_ai_run_id="run_ai_iso",
        creative_plan_reference="cplan_iso",
        creative_tier_decision_reference="tier_iso",
        why_reuse_failed="none",
        why_compose_failed="none",
        source_code=source_code,
        source_code_path=f"workspaces/{workspace_id}/projects/prj_iso_rev/candidates/{candidate_id}/source.tsx",
        template_schema=schema,
        dependencies=deps,
        fixtures=fixtures,
        content_hash=content_hash,
        revision=1,
        status=CandidateStatus.VALIDATED,
        name="Iso Review Candidate",
        description="Candidate for isolation test",
        author="usr_creator_iso",
        proposed_category="elements/text",
        proposed_tags=["test"],
        target_tier=CreativeTier.REUSE,
        required_provenance=ProvenanceRecord(source="test", timestamp=now),
        storage_keys={"source_code": f"workspaces/{workspace_id}/candidates/{candidate_id}/source.tsx"},
        created_at=now,
        updated_at=now,
    )
    repo.save_candidate(candidate)

    static_report = CandidateValidationReport(
        validation_id=f"val_static_{candidate_id}",
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        candidate_content_hash=content_hash,
        candidate_revision=1,
        phase=ValidationPhase.STATIC,
        policy_version="1.0.0",
        started_at=now,
        completed_at=now,
        gates=[CandidateGateResult(gate_id="contract_gate", status=GateStatus.PASS, summary="ok")],
        overall_result=ValidationOverallResult.PASS,
        evidence_refs={"report": f"candidates/{workspace_id}/{candidate_id}/static_report.json"},
    )
    repo.save_validation_report(static_report)

    runtime_report = CandidateValidationReport(
        validation_id=f"val_runtime_{candidate_id}",
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        candidate_content_hash=content_hash,
        candidate_revision=1,
        phase=ValidationPhase.RUNTIME,
        policy_version="1.0.0",
        started_at=now,
        completed_at=now,
        gates=[CandidateGateResult(gate_id="smoke_gate", status=GateStatus.PASS, summary="ok")],
        overall_result=ValidationOverallResult.PASS,
        evidence_refs={"smoke_frame_0": f"candidates/{workspace_id}/{candidate_id}/smoke_0.png"},
        static_validation_id=static_report.validation_id,
        static_validation_report_hash=hashlib.sha256(static_report.model_dump_json().encode("utf-8")).hexdigest(),
    )
    repo.save_validation_report(runtime_report)

    # 3. Open Review (Transition to AWAITING_APPROVAL)
    reviewer_tenant = TenantContext(
        workspace_id=workspace_id,
        user_id="usr_human_reviewer",
        role=Role.REVIEWER,
        principal=Principal(
            principal_id="usr_human_reviewer",
            principal_type=PrincipalType.HUMAN,
            roles={Role.REVIEWER},
        ),
    )
    bundle = review_service.open_review(
        tenant_context=reviewer_tenant,
        candidate_id=candidate_id,
        expected_revision=1,
    )
    cand_awaiting = repo.get_candidate(candidate_id=candidate_id, workspace_id=workspace_id)
    assert cand_awaiting.status == CandidateStatus.AWAITING_APPROVAL

    # 4. Reviewer Decision (Transition to APPROVED)
    decision = review_service.approve(
        tenant_context=reviewer_tenant,
        candidate_id=candidate_id,
        review_bundle_id=bundle.review_bundle_id,
        expected_revision=1,
        reason="Verified visual quality and contract compliance.",
    )
    assert decision.decision == CandidateReviewVerdict.APPROVED

    # Check candidate status is APPROVED, NOT PROMOTED
    updated_cand = repo.get_candidate(candidate_id=candidate_id, workspace_id=workspace_id)
    assert updated_cand.status == CandidateStatus.APPROVED

    # 5. Snapshot canonical registry state after review & approval
    post_reg_data = _hash_file(registry_data_path)
    post_reg_tsx = _hash_file(registry_tsx_path)
    post_runtime = _hash_file(runtime_contract_path)
    post_catalog = _hash_file(catalog_path)
    post_templates = _hash_directory(templates_dir)

    # 6. Mandatory Invariant Assertions
    assert snap_reg_data == post_reg_data, "Canonical registry/template-registry-data.json was mutated!"
    assert snap_reg_tsx == post_reg_tsx, "Canonical registry/template-registry.tsx was mutated!"
    assert snap_runtime == post_runtime, "Canonical contracts/template-runtime-contract.json was mutated!"
    assert snap_catalog == post_catalog, "Canonical ground-truth/template_catalog.json was mutated!"
    assert snap_templates == post_templates, "Canonical templates/ directory was mutated!"

