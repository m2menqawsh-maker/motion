"""
tests/ai/memory/test_tenant_isolation.py
========================================
Tenant Isolation and Cross-Tenant Attack Suite for S27.6.

Mandatory Gate:
- Workspace A stores 100 memories.
- Workspace B performs semantically identical query.
- Result: ZERO records from Workspace A leaked to Workspace B.
- Tests exact retrieval, semantic retrieval, structured query, source lookup,
  revoked project permissions, and deleted project boundaries.
"""

import pytest

from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
from ai.memory.models import (
    MemoryEntry,
    MemoryFilter,
    TrustedTenantContext,
)
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.service import MemoryService, TenantAuthorizationError
from ai.memory.types import (
    ConfidenceLevel,
    MemoryScope,
    MemoryType,
    SourceType,
)


class TestTenantIsolationSuite:

    @pytest.fixture
    def setup_service(self):
        embedder = DeterministicFakeEmbeddingProvider(dimension=128)
        repo = InMemoryMemoryRepository()
        service = MemoryService(repository=repo, embedding_provider=embedder)
        return service, repo, embedder

    def test_100_memory_cross_tenant_attack_suite(self, setup_service):
        """
        Mandatory Gate:
        Workspace A stores 100 memories.
        Workspace B performs identical semantic and exact queries.
        Must return ZERO Workspace A memories.
        """
        service, repo, embedder = setup_service

        ctx_a = TrustedTenantContext(
            workspace_id="ws_victim_alpha",
            user_id="usr_alice",
            roles=["owner"],
        )

        ctx_b = TrustedTenantContext(
            workspace_id="ws_attacker_beta",
            user_id="usr_mallory",
            roles=["owner"],
        )

        # 1. Workspace A stores 100 memories
        for i in range(100):
            service.store_memory(
                context=ctx_a,
                content=f"Confidential executive decision #{i}: All Q4 media projects must use corporate font Cairo.",
                memory_type=MemoryType.DECISION if i % 2 == 0 else MemoryType.USER_PREFERENCE,
                scope=MemoryScope.WORKSPACE if i % 2 == 0 else MemoryScope.USER,
                project_id=f"prj_{i % 5}",
                confidence=0.9,
                source_type=SourceType.DECISION,
                metadata={"secret_score": i},
            )

        # Verify Workspace A has 100 memories
        filter_a = MemoryFilter(workspace_id=ctx_a.workspace_id, limit=100)
        mems_a = service.query_structured(ctx_a, filter_a)
        assert len(mems_a) == 100, f"Expected 100 memories in ws_victim_alpha, got {len(mems_a)}"

        # 2. Attack: Workspace B performs semantically identical semantic search
        attack_query = "Confidential executive decision: Q4 media corporate font Cairo"
        results_b = service.query_semantic(
            context=ctx_b,
            query_text=attack_query,
            limit=50,
            min_similarity=0.0,
        )

        assert len(results_b) == 0, f"LEAK DETECTED! Attacker obtained {len(results_b)} memories from Victim!"

        # 3. Attack: Workspace B attempts exact structured query
        filter_b = MemoryFilter(workspace_id=ctx_b.workspace_id, limit=100)
        mems_b = service.query_structured(ctx_b, filter_b)
        assert len(mems_b) == 0

        # 4. Attack: Workspace B attempts cross-tenant query spoofing in MemoryFilter
        spoofed_filter = MemoryFilter(workspace_id=ctx_a.workspace_id, limit=100)
        with pytest.raises(TenantAuthorizationError, match="Cross-tenant query rejected"):
            service.query_structured(ctx_b, spoofed_filter)

        # 5. Attack: Workspace B attempts cross-tenant semantic query spoofing
        with pytest.raises(TenantAuthorizationError, match="Cross-tenant semantic query rejected"):
            service.query_semantic(
                context=ctx_b,
                query_text="font Cairo",
                filter_req=MemoryFilter(workspace_id=ctx_a.workspace_id),
            )

        # 6. Attack: Workspace B attempts direct get on victim's memory ID
        victim_id = mems_a[0].id
        leaked_entry = service.get_memory(ctx_b, victim_id)
        assert leaked_entry is None, "Direct ID get leaked cross-tenant memory!"

        # 7. Attack: Workspace B attempts to delete victim's memory
        deleted = service.delete_memory(ctx_b, victim_id)
        assert deleted is False, "Attacker was able to delete victim's memory!"

    def test_revoked_project_permissions_exclusion(self, setup_service):
        """
        User had access to prj_secret, stored memories, then permission was revoked.
        Subsequent retrieval must NOT return memories for prj_secret.
        """
        service, repo, _ = setup_service

        # Step 1: User has access to prj_public and prj_secret
        ctx_authorized = TrustedTenantContext(
            workspace_id="ws_multi_proj",
            user_id="usr_bob",
            roles=["member"],
            accessible_projects=["prj_public", "prj_secret"],
        )

        service.store_memory(
            context=ctx_authorized,
            content="Public guideline: Logo in top right.",
            memory_type=MemoryType.PROJECT,
            scope=MemoryScope.PROJECT,
            project_id="prj_public",
        )

        service.store_memory(
            context=ctx_authorized,
            content="Classified project fact: Secret launch date is November 1.",
            memory_type=MemoryType.PROJECT,
            scope=MemoryScope.PROJECT,
            project_id="prj_secret",
        )

        # Verify authorized query sees both
        res_before = service.query_structured(
            ctx_authorized,
            MemoryFilter(workspace_id="ws_multi_proj"),
        )
        assert len(res_before) == 2

        # Step 2: Permission to prj_secret is REVOKED
        ctx_revoked = TrustedTenantContext(
            workspace_id="ws_multi_proj",
            user_id="usr_bob",
            roles=["member"],
            accessible_projects=["prj_public"],  # prj_secret removed!
        )

        # Structured query must NOT expose prj_secret
        res_after = service.query_structured(
            ctx_revoked,
            MemoryFilter(workspace_id="ws_multi_proj"),
        )
        assert len(res_after) == 1
        assert res_after[0].project_id == "prj_public"

        # Semantic query must NOT expose prj_secret
        sem_res = service.query_semantic(
            ctx_revoked,
            query_text="Secret launch date",
        )
        assert len(sem_res) == 0

        # Attempting explicit filter on revoked project returns empty list
        filter_revoked = MemoryFilter(workspace_id="ws_multi_proj", project_id="prj_secret")
        res_explicit = service.query_structured(ctx_revoked, filter_revoked)
        assert len(res_explicit) == 0
