"""
tests/ai/context/test_knowledge_router_adapter.py
==================================================
Verification suite for KnowledgeRouterAdapter bridging KnowledgeRouter
to KnowledgeRetriever protocol for ContextBuilder (REALITY-007).
"""

import pytest
from ai.context.adapters.knowledge_router_adapter import KnowledgeRouterAdapter
from ai.context.retrieval import KnowledgeRetriever
from ai.context.types import ContextAuthority, ContextItem, ContextSection, ContextSourceType
from ai.knowledge.router import KnowledgeRouter
from ai.memory.models import TrustedTenantContext


@pytest.fixture
def tenant_alpha() -> TrustedTenantContext:
    return TrustedTenantContext(
        workspace_id="ws_alpha",
        user_id="usr_alice",
        roles=["editor"],
        accessible_projects=["prj_alpha_1"],
    )


@pytest.fixture
def tenant_beta() -> TrustedTenantContext:
    return TrustedTenantContext(
        workspace_id="ws_beta",
        user_id="usr_bob",
        roles=["editor"],
        accessible_projects=["prj_beta_1"],
    )


def test_adapter_protocol_compliance():
    """Verify that KnowledgeRouterAdapter satisfies the KnowledgeRetriever protocol."""
    router = KnowledgeRouter()
    adapter = KnowledgeRouterAdapter(router=router)
    # Check that retrieve_knowledge method exists and is callable
    assert hasattr(adapter, "retrieve_knowledge")
    assert callable(adapter.retrieve_knowledge)


def test_adapter_retrieves_canonical_knowledge(tenant_alpha):
    """Verify that KnowledgeRouterAdapter retrieves real chunks from indexed catalog."""
    router = KnowledgeRouter()
    router.initialize_canonical_catalog(verify_hash=True)
    adapter = KnowledgeRouterAdapter(router=router)

    items = adapter.retrieve_knowledge(
        context=tenant_alpha,
        tags=["ffmpeg", "normalization"],
        query="ffmpeg audio normalization",
        limit=5,
    )

    assert len(items) > 0
    for it in items:
        assert isinstance(it, ContextItem)
        assert it.section == ContextSection.KNOWLEDGE
        assert it.source_type == ContextSourceType.KNOWLEDGE
        assert it.authority == ContextAuthority.DOMAIN_SOURCE_OF_TRUTH
        assert it.content_hash is not None
        assert len(it.content_hash) == 64
        assert "ffmpeg" in it.content.lower() or "audio" in it.content.lower() or "codec" in it.content.lower()


def test_adapter_enforces_tenant_isolation(tenant_alpha, tenant_beta):
    """Verify that workspace-scoped knowledge from tenant beta cannot be retrieved by tenant alpha."""
    from ai.knowledge.contracts import KnowledgeChunk
    router = KnowledgeRouter()
    adapter = KnowledgeRouterAdapter(router=router)

    # Manually register a chunk for beta
    beta_chunk = KnowledgeChunk.create(
        document_id="know_custom_beta_confidential",
        section="Beta Confidential Strategy",
        version="1.0.0",
        source="references/beta.md",
        content="Confidential proprietary pricing algorithm for workspace beta.",
        category="PLAYBOOK",
        tags=["pricing", "strategy"],
        metadata={"workspace_id": "ws_beta"},
    )
    router.indexer._chunks[beta_chunk.chunk_id] = beta_chunk
    router.indexer._doc_chunks[beta_chunk.document_id] = [beta_chunk.chunk_id]
    for tok in ["pricing", "strategy", "algorithm", "confidential"]:
        if tok not in router.indexer._inverted_index:
            router.indexer._inverted_index[tok] = set()
        router.indexer._inverted_index[tok].add(beta_chunk.chunk_id)

    # Tenant Alpha should NOT retrieve beta's chunk
    alpha_items = adapter.retrieve_knowledge(
        context=tenant_alpha,
        tags=["pricing"],
        query="pricing strategy",
        limit=5,
    )
    for it in alpha_items:
        assert "workspace beta" not in it.content.lower()
        assert it.metadata.get("workspace_id") != "ws_beta"


def test_adapter_sanitizes_secrets(tenant_alpha):
    """Verify that chunks containing secrets or tokens are excluded by adapter."""
    from ai.knowledge.contracts import KnowledgeChunk
    router = KnowledgeRouter()
    adapter = KnowledgeRouterAdapter(router=router)

    # Register a chunk with an apparent secret key
    secret_chunk = KnowledgeChunk.create(
        document_id="know_leaked_secret",
        section="Leaked Credentials Section",
        version="1.0.0",
        source="references/leak.md",
        content="Leaked key: sk-live-abcdef1234567890abcdef1234567890",
        category="PLAYBOOK",
        tags=["secret"],
    )
    router.indexer._chunks[secret_chunk.chunk_id] = secret_chunk
    router.indexer._doc_chunks[secret_chunk.document_id] = [secret_chunk.chunk_id]
    for tok in ["secret", "leaked", "key"]:
        if tok not in router.indexer._inverted_index:
            router.indexer._inverted_index[tok] = set()
        router.indexer._inverted_index[tok].add(secret_chunk.chunk_id)

    items = adapter.retrieve_knowledge(
        context=tenant_alpha,
        tags=["secret"],
        query="leaked key",
        limit=5,
    )
    for it in items:
        assert "sk-live-" not in it.content
