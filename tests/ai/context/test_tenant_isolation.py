"""
tests/ai/context/test_tenant_isolation.py
=========================================
Cross-Tenant Context Attack Suite and Authorization Boundaries (S27.8).
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.memory import MemoryType
from ai.context import (
    ContextBuilder,
    ContextPackage,
    ContextRequest,
    DeterministicKnowledgeRetriever,
    KnowledgeDocument,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
)
from ai.memory.models import TrustedTenantContext
from ai.memory.types import MemoryScope
from tests.ai.context.conftest import (
    MockLifecycleDTO,
    MockProjectService,
    make_test_memory_service,
)


class TestCrossTenantContextIsolation:

    def test_cross_tenant_context_attack_suite(self):
        """
        Section 63 Mandatory Gate:
        Workspace A owns:
        - 100 highly relevant memories
        - 10 knowledge items
        - project facts
        Workspace B issues a semantically identical request.
        Expected:
        - Exactly 0 items from Workspace A appear in Workspace B's ContextPackage.
        """
        mem_svc = make_test_memory_service()
        ctx_a = TrustedTenantContext(workspace_id="ws_alpha", user_id="usr_alice")
        ctx_b = TrustedTenantContext(workspace_id="ws_beta", user_id="usr_bob")

        # 1. Populate Workspace A with 100 relevant memories
        for i in range(100):
            mem_svc.store_memory(
                context=ctx_a,
                content=f"Secret Alpha strategy {i}: focus on high conversion e-commerce hooks",
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.WORKSPACE,
                confidence=0.95,
                metadata={"domain": "tone", "confidential": "true"},
            )

        # 2. Populate 10 Workspace A knowledge items and 2 global items
        knowledge_docs = []
        for i in range(10):
            knowledge_docs.append(
                KnowledgeDocument(
                    doc_id=f"alpha_doc_{i}",
                    title=f"Alpha Proprietary Playbook {i}",
                    content=f"Confidential revenue playbook {i}",
                    tags=["guidelines", "strategy"],
                    workspace_id="ws_alpha",
                )
            )
        knowledge_docs.append(
            KnowledgeDocument(
                doc_id="global_doc_1",
                title="Public Pacing Guide",
                content="Standard open public pacing guidelines.",
                tags=["guidelines"],
                workspace_id=None,  # global
            )
        )
        know_retriever = DeterministicKnowledgeRetriever(knowledge_docs)

        # 3. Project service with projects for both workspaces
        proj_svc = MockProjectService({
            "prj_alpha_1": MockLifecycleDTO(project_id="prj_alpha_1", lifecycle_state="PLAN_READY"),
            "prj_beta_1": MockLifecycleDTO(project_id="prj_beta_1", lifecycle_state="DRAFT"),
        })

        builder = ContextBuilder(
            project_service=proj_svc,
            memory_service=mem_svc,
            knowledge_retriever=know_retriever,
        )

        # 4. Workspace B issues request with identical query
        req_b = ContextRequest(
            request_id="req_beta_attack_001",
            trusted_context=ctx_b,
            capability=CapabilityType.TEXT_GENERATION,
            project_id="prj_beta_1",
            query_text="focus on high conversion e-commerce hooks strategy",
            created_at=datetime.now(timezone.utc),
        )

        package_b: ContextPackage = builder.build(req_b)

        # 5. Audit all items in Workspace B context package
        all_items_b = package_b.all_items()
        assert len(all_items_b) > 0

        leaked_alpha_items = []
        for it in all_items_b:
            if "Secret Alpha" in it.content or "alpha_doc" in (it.source_id or "") or "ws_alpha" in it.content:
                leaked_alpha_items.append(it)

        assert len(leaked_alpha_items) == 0, (
            f"Cross-tenant isolation violation! Found {len(leaked_alpha_items)} leaked Alpha items in Beta context: "
            f"{[it.id for it in leaked_alpha_items]}"
        )
        # Ensure memory context contains 0 items for ws_beta (since ws_beta has no memories stored)
        assert len(package_b.memory_context.items) == 0

    def test_revoked_project_access_fails_closed(self):
        """Section 33: Revoked project access causes fail-closed ProjectAccessDeniedError."""
        ctx = TrustedTenantContext(
            workspace_id="ws_1",
            user_id="usr_1",
            accessible_projects=["prj_allowed"],
        )
        proj_svc = MockProjectService({
            "prj_forbidden": MockLifecycleDTO(project_id="prj_forbidden"),
        })
        builder = ContextBuilder(project_service=proj_svc)

        req = ContextRequest(
            request_id="req_denied",
            trusted_context=ctx,
            capability=CapabilityType.PLANNING,
            project_id="prj_forbidden",
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(ProjectAccessDeniedError):
            builder.build(req)

    def test_deleted_project_fails_closed(self):
        """Section 34: Deleted or non-existent project causes fail-closed ProjectNotFoundError."""
        ctx = TrustedTenantContext(workspace_id="ws_1", user_id="usr_1")
        proj_svc = MockProjectService({})
        builder = ContextBuilder(project_service=proj_svc)

        req = ContextRequest(
            request_id="req_missing",
            trusted_context=ctx,
            capability=CapabilityType.PLANNING,
            project_id="prj_deleted_123",
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(ProjectNotFoundError):
            builder.build(req)
