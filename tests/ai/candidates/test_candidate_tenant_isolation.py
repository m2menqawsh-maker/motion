"""
tests/ai/candidates/test_candidate_tenant_isolation.py
======================================================
Multi-tenant isolation and security invariants for TemplateCandidate (S28-07A).

Invariants:
- Workspace A creates candidate; Workspace B cannot read, update, list, resolve, or overwrite it.
- Candidate workspace_id is strictly derived from server TenantContext; client parameter is rejected if mismatched.
- Source project must belong to the caller's active workspace.
- Cross-tenant candidate ID probing returns 404 / CandidateNotFoundError (no enumeration leakage).
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
from ai.contracts.common import ProvenanceRecord
from creative_governance.candidates.service import TemplateCandidateService
from creative_governance.candidates.repository import InMemoryTemplateCandidateRepository
from creative_governance.candidates.errors import (
    CandidateNotFoundError,
    CandidateTenantMismatchError,
)
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.tenant_model import TenantContext, ProjectRecord
from scripts.core.storage import LocalStorageBackend


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def tenant_a():
    return TenantContext(
        workspace_id="ws_tenant_a",
        user_id="usr_a",
        role=Role.EDITOR,
        principal=Principal(
            principal_id="usr_a",
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        ),
    )


@pytest.fixture
def tenant_b():
    return TenantContext(
        workspace_id="ws_tenant_b",
        user_id="usr_b",
        role=Role.EDITOR,
        principal=Principal(
            principal_id="usr_b",
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR},
        ),
    )


@pytest.fixture
def candidate_service(tmp_path):
    repo = InMemoryTemplateCandidateRepository()
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    service = TemplateCandidateService(repository=repo, storage_service=storage)

    # Register project for tenant A and project for tenant B
    service.register_project_for_test(
        ProjectRecord(id="prj_a_001", workspace_id="ws_tenant_a", created_by="usr_a", name="Project A")
    )
    service.register_project_for_test(
        ProjectRecord(id="prj_b_001", workspace_id="ws_tenant_b", created_by="usr_b", name="Project B")
    )
    return service


def test_cross_tenant_isolation(
    candidate_service, tenant_a, tenant_b, valid_create_decision, valid_creative_plan
):
    # 1. Tenant A creates candidate
    cand_a = candidate_service.create_candidate(
        tenant_context=tenant_a,
        source_project_id="prj_a_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const CompA = () => <div>A</div>;",
    )
    assert cand_a.workspace_id == "ws_tenant_a"

    # 2. Tenant B attempts to get candidate of Tenant A -> Not found / Denied
    with pytest.raises(CandidateNotFoundError):
        candidate_service.get_candidate(tenant_context=tenant_b, candidate_id=cand_a.candidate_id)

    # 3. Tenant B attempts to update candidate of Tenant A -> Not found / Denied
    with pytest.raises(CandidateNotFoundError):
        candidate_service.update_draft_candidate(
            tenant_context=tenant_b,
            candidate_id=cand_a.candidate_id,
            expected_revision=1,
            source_code="export const CompHacked = () => <div>Hacked</div>;",
        )

    # 4. Tenant B lists candidates -> Tenant A's candidate is absent
    list_b = candidate_service.list_candidates(tenant_context=tenant_b)
    assert len(list_b) == 0

    list_a = candidate_service.list_candidates(tenant_context=tenant_a)
    assert len(list_a) == 1
    assert list_a[0].candidate_id == cand_a.candidate_id


def test_tenant_cannot_reference_project_outside_workspace(
    candidate_service, tenant_a, valid_create_decision, valid_creative_plan
):
    # Tenant A attempts to create a candidate referencing Tenant B's project
    with pytest.raises(CandidateTenantMismatchError, match="does not belong to caller workspace"):
        candidate_service.create_candidate(
            tenant_context=tenant_a,
            source_project_id="prj_b_001",  # belongs to Tenant B!
            creative_plan=valid_creative_plan,
            tier_decision=valid_create_decision,
            source_code="export const CompA = () => <div>A</div>;",
        )
