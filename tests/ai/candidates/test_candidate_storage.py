"""
tests/ai/candidates/test_candidate_storage.py
============================================
Isolated StorageService tests for TemplateCandidate (S28-07A).

Invariants:
- Storage keys are server-controlled under workspaces/{ws}/projects/{prj}/candidates/{cand}/
- Traversal attempts (e.g. '../../registry') are completely rejected.
- Large candidate artifacts (source code, fixtures, schemas) are stored in StorageService.
- Persistent objects can be resolved reliably across service re-instantiations.
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
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.tenant_model import TenantContext, ProjectRecord
from scripts.core.storage import (
    LocalStorageBackend,
    StorageSecurityError,
    validate_storage_key,
)


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


def test_server_generated_storage_keys(tmp_path, test_tenant, valid_create_decision, valid_creative_plan):
    storage_root = tmp_path / "storage"
    storage = LocalStorageBackend(root_dir=storage_root)
    repo = InMemoryTemplateCandidateRepository()
    service = TemplateCandidateService(repository=repo, storage_service=storage)
    service.register_project_for_test(
        ProjectRecord(id="prj_100", workspace_id="ws_acme", created_by="usr_alice", name="Proj 100")
    )

    cand = service.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_100",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const Cube = () => <mesh />;",
        fixtures={"size": 10},
        template_schema={"type": "object"},
    )

    # Verify keys are server-generated under canonical category 'candidates'
    assert "source_code" in cand.storage_keys
    source_key = cand.storage_keys["source_code"]
    expected_prefix = f"workspaces/ws_acme/projects/prj_100/candidates/{cand.candidate_id}/"
    assert source_key.startswith(expected_prefix)
    assert source_key.endswith("source.tsx")

    # Verify storage service holds the payload
    assert storage.exists(source_key)
    raw_source = storage.get(source_key).decode("utf-8")
    assert raw_source == "export const Cube = () => <mesh />;"

    # Verify re-retrieval via service
    retrieved = service.get_candidate(tenant_context=test_tenant, candidate_id=cand.candidate_id)
    assert retrieved.source_code == "export const Cube = () => <mesh />;"
    assert retrieved.fixtures == {"size": 10}


def test_storage_key_rejects_path_traversal_attempts():
    with pytest.raises(StorageSecurityError):
        validate_storage_key("workspaces/ws_1/projects/prj_1/candidates/cand_1/../../../../registry/malicious.tsx")

    with pytest.raises(StorageSecurityError):
        validate_storage_key("/etc/passwd")


def test_persistence_resolves_across_service_restarts(tmp_path, test_tenant, valid_create_decision, valid_creative_plan):
    storage_root = tmp_path / "storage"
    storage = LocalStorageBackend(root_dir=storage_root)
    repo = InMemoryTemplateCandidateRepository()

    # Service Instance 1
    service1 = TemplateCandidateService(repository=repo, storage_service=storage)
    service1.register_project_for_test(
        ProjectRecord(id="prj_100", workspace_id="ws_acme", created_by="usr_alice", name="Proj 100")
    )
    cand = service1.create_candidate(
        tenant_context=test_tenant,
        source_project_id="prj_100",
        creative_plan=valid_creative_plan,
        tier_decision=valid_create_decision,
        source_code="export const DurableComp = () => <div>Durable</div>;",
    )

    # Service Instance 2 with same storage backend and repository
    service2 = TemplateCandidateService(repository=repo, storage_service=storage)
    service2.register_project_for_test(
        ProjectRecord(id="prj_100", workspace_id="ws_acme", created_by="usr_alice", name="Proj 100")
    )
    resolved = service2.get_candidate(tenant_context=test_tenant, candidate_id=cand.candidate_id)

    assert resolved.candidate_id == cand.candidate_id
    assert resolved.source_code == "export const DurableComp = () => <div>Durable</div>;"
    assert resolved.content_hash == cand.content_hash
