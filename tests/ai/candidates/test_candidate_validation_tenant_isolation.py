"""
tests/ai/candidates/test_candidate_validation_tenant_isolation.py
================================================================
Tenant isolation tests for CandidateValidationService (S28-07B).

Invariants:
1. Workspace A cannot validate Candidate B (cross-tenant validation denied).
2. Workspace A cannot read Candidate B validation report.
3. Cross-tenant validation_id lookup returns None.
4. Validation evidence keys in StorageService are strictly tenant-partitioned.
"""

from __future__ import annotations

import pytest

from creative_governance.candidates.errors import CandidateNotFoundError
from creative_governance.candidates.repository import InMemoryTemplateCandidateRepository
from creative_governance.candidates.service import TemplateCandidateService
from creative_governance.candidates.validation_service import CandidateValidationService
from ai.contracts.creative.template_candidate import (
    CandidateStatus,
    ValidationOverallResult,
)
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend
from scripts.core.tenant_model import TenantContext, ProjectRecord


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
def multi_tenant_validation_stack(tmp_path):
    storage = LocalStorageBackend(root_dir=tmp_path / "storage")
    repo = InMemoryTemplateCandidateRepository()
    candidate_service = TemplateCandidateService(
        repository=repo,
        storage_service=storage,
    )
    # Register project for Tenant A
    candidate_service.register_project_for_test(
        ProjectRecord(
            id="prj_a_001",
            workspace_id="ws_tenant_a",
            created_by="usr_a",
            name="Project A",
        )
    )
    # Register project for Tenant B
    candidate_service.register_project_for_test(
        ProjectRecord(
            id="prj_b_001",
            workspace_id="ws_tenant_b",
            created_by="usr_b",
            name="Project B",
        )
    )
    validation_service = CandidateValidationService(
        candidate_service=candidate_service,
        repository=repo,
        storage_service=storage,
    )
    return candidate_service, validation_service, repo, storage


def test_cross_tenant_cannot_validate_candidate(
    multi_tenant_validation_stack,
    tenant_a,
    tenant_b,
    valid_create_decision,
    valid_creative_plan,
):
    """Proves Workspace B cannot trigger validation on Candidate belonging to Workspace A."""
    cand_service, val_service, _, _ = multi_tenant_validation_stack

    cand_a = cand_service.create_candidate(
        tenant_context=tenant_a,
        source_project_id="prj_a_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="import React from 'react'; export const CA = () => <div>A</div>;",
        template_schema={"type": "object", "properties": {"v": {"type": "string"}}},
        dependencies=[],
        fixtures={"v": "test"},
    )

    # Tenant B attempts to validate Candidate A -> must fail closed with CandidateNotFoundError
    with pytest.raises(CandidateNotFoundError):
        val_service.validate_candidate_static(tenant_b, cand_a.candidate_id)


def test_cross_tenant_cannot_read_validation_report(
    multi_tenant_validation_stack,
    tenant_a,
    tenant_b,
    valid_create_decision,
    valid_creative_plan,
):
    """Proves Workspace B cannot retrieve or list validation reports belonging to Workspace A."""
    cand_service, val_service, _, storage = multi_tenant_validation_stack

    cand_a = cand_service.create_candidate(
        tenant_context=tenant_a,
        source_project_id="prj_a_001",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="import React from 'react'; export const CA = () => <div>A</div>;",
        template_schema={"type": "object", "properties": {"v": {"type": "string"}}},
        dependencies=[],
        fixtures={"v": "test"},
    )

    report_a = val_service.validate_candidate_static(tenant_a, cand_a.candidate_id)
    assert report_a.overall_result == ValidationOverallResult.PASS

    # 1. Tenant B look up by validation_id -> returns None
    assert val_service.get_validation_report(tenant_b, report_a.validation_id) is None

    # 2. Tenant B list reports for candidate_a -> raises CandidateNotFoundError
    with pytest.raises(CandidateNotFoundError):
        val_service.list_validation_reports(tenant_b, cand_a.candidate_id)

    # 3. Storage evidence key isolation
    report_key = report_a.evidence_refs.get("report_json", "")
    assert "workspaces/ws_tenant_a/" in report_key
    assert "ws_tenant_b" not in report_key
