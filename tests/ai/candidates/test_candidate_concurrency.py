"""
tests/ai/candidates/test_candidate_concurrency.py
=================================================
Optimistic concurrency and CAS tests for TemplateCandidate (S28-07A).

Invariants:
- Updates require expected_revision matching current candidate revision.
- Successful update atomically increments revision (N -> N+1).
- Stale update attempts raise CandidateConflictError.
- Revision sequence is strictly monotonic.
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
from creative_governance.candidates.errors import CandidateConflictError
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
def candidate_service(tmp_path):
    repo = InMemoryTemplateCandidateRepository()
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    service = TemplateCandidateService(repository=repo, storage_service=storage)
    service.register_project_for_test(
        ProjectRecord(id="prj_100", workspace_id="ws_acme", created_by="usr_alice", name="Proj 100")
    )
    return service


def test_cas_concurrency_protection(
    candidate_service, test_tenant, valid_create_decision, valid_creative_plan
):
    # 1. Create candidate -> revision 1
    cand = candidate_service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_100",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const Comp = () => <div>v1</div>;",
    )
    assert cand.revision == 1

    # 2. Writer A updates with expected_revision=1 -> succeeds, revision becomes 2
    updated_a = candidate_service.update_draft_candidate(
        tenant_context=test_tenant,
        candidate_id=cand.candidate_id,
        expected_revision=1,
        source_code="export const Comp = () => <div>v2-by-writer-A</div>;",
    )
    assert updated_a.revision == 2

    # 3. Writer B attempts update with stale expected_revision=1 -> conflict!
    with pytest.raises(CandidateConflictError, match="Stale revision"):
        candidate_service.update_draft_candidate(
            tenant_context=test_tenant,
            candidate_id=cand.candidate_id,
            expected_revision=1,  # Stale!
            source_code="export const Comp = () => <div>v2-by-writer-B</div>;",
        )

    # 4. Writer B fetches latest (rev 2) and updates with expected_revision=2 -> succeeds, revision becomes 3
    latest = candidate_service.get_candidate(tenant_context=test_tenant, candidate_id=cand.candidate_id)
    assert latest.revision == 2

    updated_b = candidate_service.update_draft_candidate(
        tenant_context=test_tenant,
        candidate_id=cand.candidate_id,
        expected_revision=latest.revision,
        source_code="export const Comp = () => <div>v3-by-writer-B</div>;",
    )
    assert updated_b.revision == 3
