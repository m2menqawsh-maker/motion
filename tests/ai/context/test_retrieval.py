"""
tests/ai/context/test_retrieval.py
==================================
Tests for candidate retrievers and tenant authorization boundaries (S27.8).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.memory import MemoryType
from ai.context import (
    ContextAuthority,
    ContextItem,
    ContextNeeds,
    ContextRequest,
    ContextSection,
    ContextSourceType,
    DeterministicKnowledgeRetriever,
    ExclusionReason,
    KnowledgeDocument,
    MemoryRetriever,
    ProjectAccessDeniedError,
    ProjectFactRetriever,
    ProjectNotFoundError,
    contains_secret,
)
from ai.memory.models import TrustedTenantContext
from ai.memory.types import MemoryScope, SourceType
from tests.ai.context.conftest import (
    MockAssetService,
    MockLifecycleDTO,
    MockProjectService,
    MockReviewService,
    make_test_memory_service,
)


class TestSecretSanitization:

    def test_secret_detection(self):
        assert contains_secret("sk-1234567890abcdef1234567890abcdef") is True  # pragma: allowlist
        assert contains_secret("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz") is True
        assert contains_secret("-----BEGIN RSA PRIVATE KEY-----") is True  # pragma: allowlist
        assert contains_secret("ghp_123456789012345678901234567890123456") is True  # pragma: allowlist
        assert contains_secret("AKIA1234567890ABCDEF") is True  # pragma: allowlist
        assert contains_secret("This is ordinary text without keys.") is False


class TestProjectFactRetrieval:

    def test_project_facts_success(self):
        ctx = TrustedTenantContext(workspace_id="ws_1", user_id="u1", accessible_projects=["p1"])
        proj_svc = MockProjectService({
            "p1": MockLifecycleDTO(
                project_id="p1",
                lifecycle_state="ASSETS_READY",
                revision=3,
                allowed_actions=["run:execute"],
                blocked_reason="Waiting for input",
            )
        })
        asset_svc = MockAssetService({
            "p1": [{"asset_id": "ast_1", "filename": "audio.wav", "kind": "AUDIO", "status": "READY"}]
        })
        retriever = ProjectFactRetriever(project_service=proj_svc, asset_service=asset_svc)

        needs = ContextNeeds(needs_project_state=True, needs_assets=True)
        facts = retriever.retrieve_project_facts(ctx, "p1", needs)

        keys = {f.canonical_key: f for f in facts}
        assert "fact:project:status" in keys
        assert keys["fact:project:status"].content == "Project status: ASSETS_READY"
        assert keys["fact:project:status"].authority == ContextAuthority.DOMAIN_SOURCE_OF_TRUTH

        assert "fact:project:revision" in keys
        assert keys["fact:project:revision"].content == "Project revision: 3"

        assert "fact:project:blocked_reason" in keys
        assert "fact:asset:ast_1" in keys

    def test_revoked_project_access_fails_closed(self):
        # User not granted access to p2
        ctx = TrustedTenantContext(workspace_id="ws_1", user_id="u1", accessible_projects=["p1"])
        proj_svc = MockProjectService({"p2": MockLifecycleDTO(project_id="p2")})
        retriever = ProjectFactRetriever(project_service=proj_svc)

        with pytest.raises(ProjectAccessDeniedError):
            retriever.retrieve_project_facts(ctx, "p2", ContextNeeds())

    def test_deleted_project_fails_closed(self):
        ctx = TrustedTenantContext(workspace_id="ws_1", user_id="u1")
        proj_svc = MockProjectService({})  # p_missing does not exist
        retriever = ProjectFactRetriever(project_service=proj_svc)

        with pytest.raises(ProjectNotFoundError):
            retriever.retrieve_project_facts(ctx, "p_missing", ContextNeeds())


class TestMemoryRetrieval:

    def test_memory_retrieval_and_filtering(self):
        now = datetime.now(timezone.utc)
        ctx = TrustedTenantContext(workspace_id="ws_1", user_id="u1")
        mem_svc = make_test_memory_service()

        # 1. Active relevant preference
        mem_svc.store_memory(
            context=ctx,
            content="Prefers 9:16 vertical layout and punchy captions",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            confidence=0.9,
            metadata={"domain": "visual"},
        )

        # 2. Expired memory
        mem_svc.store_memory(
            context=ctx,
            content="Old expired decision",
            memory_type=MemoryType.PROJECT,
            scope=MemoryScope.PROJECT,
            project_id="p1",
            confidence=0.9,
            expires_at=now - timedelta(hours=1),
        )

        # 3. Irrelevant preference (font preference for speech-to-text request)
        mem_svc.store_memory(
            context=ctx,
            content="Prefers serif typography and italic quotes",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            confidence=0.9,
            metadata={"domain": "visual"},
        )

        # 4. Low confidence memory
        mem_svc.store_memory(
            context=ctx,
            content="Vaguely thinks user dislikes blue",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            confidence=0.1,  # below 0.2
            metadata={"domain": "visual"},
        )

        # 5. Secret-laden memory
        mem_svc.store_memory(
            context=ctx,
            content="My secret key is sk-1234567890abcdef1234567890abcdef",  # pragma: allowlist
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            confidence=0.9,
            metadata={"domain": "visual"},
        )

        retriever = MemoryRetriever(memory_service=mem_svc)
        req = ContextRequest(
            request_id="r_stt",
            trusted_context=ctx,
            capability=CapabilityType.SPEECH_TO_TEXT,
            created_at=now,
        )
        needs = ContextNeeds(
            allowed_memory_types=[MemoryType.USER_PREFERENCE.value, MemoryType.PROJECT.value],
            preference_domains=["audio", "speech"],  # visual should be excluded
        )

        items, exclusions = retriever.retrieve_memories(ctx, req, needs, now=now)

        # Expired, irrelevant, low confidence, and secret should be excluded
        excl_reasons = [e.reason for e in exclusions]
        assert ExclusionReason.EXPIRED in excl_reasons
        assert ExclusionReason.IRRELEVANT in excl_reasons
        assert ExclusionReason.LOW_CONFIDENCE in excl_reasons
        assert ExclusionReason.SECRET_DETECTED in excl_reasons


class TestKnowledgeRetrieval:

    def test_tenant_safe_knowledge(self):
        ctx_a = TrustedTenantContext(workspace_id="ws_alpha", user_id="u1")
        ctx_b = TrustedTenantContext(workspace_id="ws_beta", user_id="u2")

        doc_global = KnowledgeDocument(
            doc_id="doc_global",
            title="Global Taste Rules",
            content="Texts must not overlap.",
            tags=["taste", "rules"],
            workspace_id=None,  # global
        )
        doc_alpha = KnowledgeDocument(
            doc_id="doc_alpha_private",
            title="Alpha Private Brand Book",
            content="Alpha private color palette #112233.",
            tags=["brand"],
            workspace_id="ws_alpha",  # private to ws_alpha
        )

        retriever = DeterministicKnowledgeRetriever([doc_global, doc_alpha])

        # ws_alpha sees both global and its private doc
        items_a = retriever.retrieve_knowledge(ctx_a, tags=["taste", "brand"])
        doc_ids_a = {it.source_id for it in items_a}
        assert "doc_global" in doc_ids_a
        assert "doc_alpha_private" in doc_ids_a

        # ws_beta sees global but NEVER ws_alpha's private doc
        items_b = retriever.retrieve_knowledge(ctx_b, tags=["taste", "brand"])
        doc_ids_b = {it.source_id for it in items_b}
        assert "doc_global" in doc_ids_b
        assert "doc_alpha_private" not in doc_ids_b
