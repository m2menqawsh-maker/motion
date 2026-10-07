"""
tests/ai/context/test_determinism.py
====================================
Tests for strict determinism, invariant hashing, and ordering stability (S27.8).
"""

from __future__ import annotations

import random
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
)
from ai.memory.models import TrustedTenantContext
from ai.memory.types import MemoryScope
from tests.ai.context.conftest import (
    MockAssetService,
    MockLifecycleDTO,
    MockProjectService,
    MockReviewService,
    make_test_memory_service,
)


class TestContextDeterminism:

    def _make_builder_and_request(self, lifecycle_state: str = "PLAN_READY", extra_unrequested_assets: bool = False):
        fixed_time = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
        ctx = TrustedTenantContext(workspace_id="ws_alpha", user_id="usr_alice")

        proj_svc = MockProjectService({
            "prj_100": MockLifecycleDTO(
                project_id="prj_100",
                lifecycle_state=lifecycle_state,
                revision=1,
            )
        })

        asset_dict = {"prj_100": [{"asset_id": "ast_1", "kind": "AUDIO", "filename": "audio.wav", "status": "READY"}]}
        if extra_unrequested_assets:
            # Add an extra asset that is not used in TEXT_GENERATION capability
            asset_dict["prj_100"].append({"asset_id": "ast_unrelated_99", "kind": "FONT", "filename": "font.ttf", "status": "READY"})

        asset_svc = MockAssetService(asset_dict)
        review_svc = MockReviewService()
        mem_svc = make_test_memory_service()

        mem_svc.store_memory(
            context=ctx,
            content="Brand voice is concise, energetic, and professional",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.WORKSPACE,
            confidence=0.9,
            metadata={"domain": "tone"},
        )
        mem_svc.store_memory(
            context=ctx,
            content="Preferred video duration is 30 seconds",
            memory_type=MemoryType.PROJECT,
            scope=MemoryScope.PROJECT,
            project_id="prj_100",
            confidence=0.85,
        )

        know_ret = DeterministicKnowledgeRetriever([
            KnowledgeDocument(
                doc_id="playbook_scripting",
                title="Shortform Scripting Playbook",
                content="Hook in first 2 seconds. Deliver payoff at 20 seconds.",
                tags=["general", "guidelines"],
            )
        ])

        builder = ContextBuilder(
            project_service=proj_svc,
            asset_service=asset_svc,
            review_service=review_svc,
            memory_service=mem_svc,
            knowledge_retriever=know_ret,
        )

        request = ContextRequest(
            request_id="req_fixed_001",
            trusted_context=ctx,
            capability=CapabilityType.TEXT_GENERATION,
            project_id="prj_100",
            query_text="Write a 30-second script hook",
            created_at=fixed_time,
        )

        return builder, request

    def test_100_runs_determinism(self):
        """
        Executing ContextBuilder.build(...) 100 times on the exact same fixture
        must yield:
        - Exactly 1 unique context_hash
        - Identical section packages and item IDs
        - Identical prompt serialization
        """
        builder, request = self._make_builder_and_request()

        hashes = set()
        serialized_outputs = set()
        first_package: ContextPackage = builder.build(request)

        for _ in range(100):
            pkg = builder.build(request)
            hashes.add(pkg.context_hash)
            serialized_outputs.add(pkg.to_prompt_text())

        assert len(hashes) == 1, f"Expected 1 unique hash, got {len(hashes)}"
        assert len(serialized_outputs) == 1
        assert list(hashes)[0] == first_package.context_hash

    def test_registry_order_shuffling_invariance(self):
        """
        Changing the input registration order of candidate items
        must NOT change the final assembled ContextPackage or its context_hash.
        """
        fixed_time = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
        ctx = TrustedTenantContext(workspace_id="ws_alpha", user_id="usr_alice")

        docs = [
            KnowledgeDocument(doc_id=f"doc_{i}", title=f"Doc {i}", content=f"Content {i}", tags=["guidelines"])
            for i in range(10)
        ]

        # Order A
        builder_a = ContextBuilder(
            knowledge_retriever=DeterministicKnowledgeRetriever(docs)
        )
        req_a = ContextRequest(
            request_id="req_shuffle",
            trusted_context=ctx,
            capability=CapabilityType.TEXT_GENERATION,
            created_at=fixed_time,
        )
        pkg_a = builder_a.build(req_a)

        # Order B: Shuffled
        shuffled_docs = list(docs)
        random.Random(42).shuffle(shuffled_docs)
        builder_b = ContextBuilder(
            knowledge_retriever=DeterministicKnowledgeRetriever(shuffled_docs)
        )
        req_b = ContextRequest(
            request_id="req_shuffle",
            trusted_context=ctx,
            capability=CapabilityType.TEXT_GENERATION,
            created_at=fixed_time,
        )
        pkg_b = builder_b.build(req_b)

        assert pkg_a.context_hash == pkg_b.context_hash
        assert [it.id for it in pkg_a.knowledge_context.items] == [it.id for it in pkg_b.knowledge_context.items]

    def test_same_state_hash_identical(self):
        """Section 60: Identical inputs and state yield identical context hash."""
        builder1, req1 = self._make_builder_and_request()
        builder2, req2 = self._make_builder_and_request()

        pkg1 = builder1.build(req1)
        pkg2 = builder2.build(req2)

        assert pkg1.context_hash == pkg2.context_hash

    def test_changed_relevant_state_changes_hash(self):
        """Section 61: Changing relevant state (e.g. project status) changes context hash."""
        builder1, req1 = self._make_builder_and_request(lifecycle_state="PLAN_READY")
        builder2, req2 = self._make_builder_and_request(lifecycle_state="REVIEW_APPROVED")

        pkg1 = builder1.build(req1)
        pkg2 = builder2.build(req2)

        assert pkg1.context_hash != pkg2.context_hash

    def test_irrelevant_state_change_does_not_change_hash(self):
        """
        Section 62: State change not retrieved by capability (e.g. asset registry
        change when capability is TEXT_GENERATION) does not change context hash.
        """
        builder1, req1 = self._make_builder_and_request(extra_unrequested_assets=False)
        builder2, req2 = self._make_builder_and_request(extra_unrequested_assets=True)

        pkg1 = builder1.build(req1)
        pkg2 = builder2.build(req2)

        assert pkg1.context_hash == pkg2.context_hash
