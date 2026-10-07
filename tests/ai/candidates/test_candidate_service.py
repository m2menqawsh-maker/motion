"""
tests/ai/candidates/test_candidate_service.py
============================================
Domain authority tests for TemplateCandidateService (S28-07A).

Invariants:
- Candidate creation is strictly predicated on an authoritative NEEDS_CREATE decision.
- Missing REUSE/COMPOSE insufficiency evidence causes immediate rejection.
- Caller attempting to pass status=PROMOTED or status=APPROVED is rejected.
- Candidate always starts in DRAFT status.
- Content hash and revision are computed and managed server-side.
"""

from __future__ import annotations

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
from ai.contracts.creative.template_candidate import CandidateStatus, TemplateCandidate
from ai.contracts.common import ProvenanceRecord
from creative_governance.candidates.service import TemplateCandidateService
from creative_governance.candidates.repository import InMemoryTemplateCandidateRepository
from creative_governance.candidates.errors import (
    CandidateEligibilityError,
    CandidateAuthorityError,
    CandidateNotFoundError,
)
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.tenant_model import TenantContext, ProjectRecord
from scripts.core.storage import LocalStorageBackend


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def test_tenant():
    principal = Principal(
        principal_id="usr_alice",
        principal_type=PrincipalType.HUMAN,
        roles={Role.EDITOR},
    )
    return TenantContext(
        workspace_id="ws_acme",
        user_id="usr_alice",
        role=Role.EDITOR,
        principal=principal,
    )


@pytest.fixture
def mock_storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "storage")


@pytest.fixture
def candidate_service(mock_storage):
    repo = InMemoryTemplateCandidateRepository()
    service = TemplateCandidateService(
        repository=repo,
        storage_service=mock_storage,
    )
    # Register project so tenant verification succeeds
    service.register_project_for_test(
        ProjectRecord(
            id="prj_brand_001",
            workspace_id="ws_acme",
            created_by="usr_alice",
            name="Brand Launch",
        )
    )
    return service


def test_create_candidate_success_starts_as_draft(
    candidate_service, test_tenant, valid_create_decision, valid_creative_plan
):
    cand = candidate_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_brand_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const FluidText = () => <canvas />;",
        template_schema={"type": "object", "properties": {"viscosity": {"type": "number"}}},
        dependencies=["three@^0.160.0"],
        fixtures={"viscosity": 0.8},
        name="Fluid 3D Text",
        description="Interactive fluid dynamics typography for hero sequences",
    )

    assert cand.candidate_id.startswith("cand_")
    assert cand.status == CandidateStatus.DRAFT
    assert cand.workspace_id == "ws_acme"
    assert cand.source_project_id == "prj_brand_001"
    assert cand.revision == 1
    assert cand.content_hash != ""
    assert cand.why_reuse_failed == valid_create_decision.reuse_result.rationale
    assert cand.why_compose_failed == valid_create_decision.compose_result.rationale
    assert cand.creative_plan_reference == "cplan_launch_001"
    assert cand.creative_tier_decision_reference == "tier_dec_create_001"


def test_create_candidate_rejected_when_not_needs_create(
    candidate_service, test_tenant, valid_creative_plan
):
    # Tier is REUSE, not CREATE
    reuse_decision = CreativeTierDecision(
        decision_id="tier_dec_reuse_001",
        scene_id="scene_hero",
        selected_tier=CreativeTier.REUSE,
        rationale="Template tmpl-bold-kinetic is 100% sufficient.",
        template_ref="tmpl-bold-kinetic",
        composite_elements=[],
        needs_create_evaluation=False,
    )

    with pytest.raises(CandidateEligibilityError, match="selected_tier must be CREATE"):
        candidate_service.create_candidate(
            tenant_context=test_tenant,
            source_project_id="prj_brand_001",
            creative_plan=valid_creative_plan,
            tier_decision=reuse_decision,
            source_code="export const X = () => null;",
        )


def test_create_candidate_rejected_when_reuse_evidence_missing_or_sufficient(
    candidate_service, test_tenant, valid_creative_plan
):
    # Create decision with invalid / missing evidence
    invalid_decision = CreativeTierDecision.model_construct(
        decision_id="tier_dec_bad",
        scene_id="scene_hero",
        selected_tier=CreativeTier.CREATE,
        rationale="arbitrary claim",
        needs_create_evaluation=True,
        reuse_result=None,
        compose_result=None,
    )

    with pytest.raises(CandidateEligibilityError, match="insufficient evidence"):
        candidate_service.create_candidate(
            tenant_context=test_tenant,
            source_project_id="prj_brand_001",
            creative_plan=valid_creative_plan,
            tier_decision=invalid_decision,
            source_code="export const X = () => null;",
        )


def test_create_candidate_rejects_caller_setting_approved_or_promoted(
    candidate_service, test_tenant, valid_create_decision, valid_creative_plan
):
    with pytest.raises(CandidateAuthorityError, match="Caller cannot set candidate status"):
        candidate_service.create_candidate(
            tenant_context=test_tenant,
            source_project_id="prj_brand_001",
            creative_plan=valid_creative_plan,
            tier_decision=valid_create_decision,
            source_code="export const X = () => null;",
            requested_status="PROMOTED",
        )

    with pytest.raises(CandidateAuthorityError, match="Caller cannot set candidate status"):
        candidate_service.create_candidate(
            tenant_context=test_tenant,
            source_project_id="prj_brand_001",
            creative_plan=valid_creative_plan,
            tier_decision=valid_create_decision,
            source_code="export const X = () => null;",
            requested_status="APPROVED",
        )
