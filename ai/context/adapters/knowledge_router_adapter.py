"""
ai/context/adapters/knowledge_router_adapter.py
================================================
Authoritative adapter bridging KnowledgeRouter to the KnowledgeRetriever protocol
used by ContextBuilder (REALITY-007).

Guarantees:
- Satisfies KnowledgeRetriever protocol:
    retrieve_knowledge(context, tags, query, recipe_ref, limit) -> List[ContextItem]
- Strict tenant boundary enforcement: workspace-specific knowledge items from
  other workspaces are strictly excluded.
- Secret sanitization: items containing secret patterns are rejected.
- Deterministic ContextItem mapping with DOMAIN_SOURCE_OF_TRUTH authority.
- Hard token and candidate limits.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai.context.retrieval import KnowledgeRetriever, contains_secret
from ai.context.types import (
    ContextAuthority,
    ContextItem,
    ContextSection,
    ContextSourceType,
)
from ai.knowledge.contracts import KnowledgeRetrievalQuery, KnowledgeRetrievalResult
from ai.knowledge.router import KnowledgeRouter
from ai.memory.models import TrustedTenantContext

logger = logging.getLogger("clean_video.knowledge_router_adapter")


class KnowledgeRouterAdapter:
    """
    Adapter bridging KnowledgeRouter to the KnowledgeRetriever protocol expected
    by ContextBuilder.
    """

    def __init__(self, router: Optional[KnowledgeRouter] = None) -> None:
        self._explicit_router = router

    @property
    def router(self) -> KnowledgeRouter:
        if self._explicit_router is not None:
            return self._explicit_router
        try:
            from ai.knowledge.catalog_service import get_knowledge_catalog_service
            return get_knowledge_catalog_service().router
        except Exception:
            return KnowledgeRouter()

    def retrieve_knowledge(
        self,
        context: TrustedTenantContext,
        tags: List[str],
        query: Optional[str] = None,
        recipe_ref: Optional[str] = None,
        limit: int = 10,
    ) -> List[ContextItem]:
        """
        Executes knowledge retrieval via KnowledgeRouter, enforcing tenant isolation,
        secret sanitization, and output contract mapping.
        """
        search_query = query or (recipe_ref or "creative knowledge")
        required_ids: List[str] = []
        if recipe_ref and recipe_ref.startswith("know_"):
            required_ids.append(recipe_ref)

        retrieval_query = KnowledgeRetrievalQuery(
            query=search_query,
            tags=tags or [],
            required_knowledge_ids=required_ids,
            limit_chunks=min(max(1, limit), 20),
            max_tokens=2500,
        )

        try:
            result: KnowledgeRetrievalResult = self.router.retrieve(retrieval_query)
        except Exception as exc:
            logger.warning("KnowledgeRouter query failed: %s", exc)
            return []

        context_items: List[ContextItem] = []
        for rc in result.chunks:
            chunk = rc.chunk

            # 1. Strict Tenant Isolation
            # If the chunk has an explicit workspace_id metadata or tag, enforce match
            chunk_ws = None
            if chunk.metadata and isinstance(chunk.metadata, dict):
                chunk_ws = chunk.metadata.get("workspace_id")
            if chunk_ws is not None and chunk_ws != context.workspace_id:
                logger.debug(
                    "Excluding cross-tenant knowledge chunk '%s' (workspace '%s' != caller '%s')",
                    chunk.chunk_id,
                    chunk_ws,
                    context.workspace_id,
                )
                continue

            # 2. Secret Sanitization Guard
            item_text = f"[{chunk.document_id}: {chunk.section}]\n{chunk.content}"
            if contains_secret(item_text):
                logger.warning(
                    "Secret pattern detected in knowledge chunk '%s'; excluding.",
                    chunk.chunk_id,
                )
                continue

            # 3. Canonical ContextItem Construction
            relevance = max(0.1, min(1.0, float(rc.score)))
            c_hash = ContextItem.compute_content_hash(item_text)

            meta: Dict[str, Any] = {
                "document_id": chunk.document_id,
                "section": chunk.section,
                "category": chunk.category,
                "authority_level": chunk.authority_level,
            }
            if chunk_ws:
                meta["workspace_id"] = chunk_ws

            item = ContextItem(
                id=f"know_{chunk.chunk_id}",
                section=ContextSection.KNOWLEDGE,
                content=item_text,
                source_type=ContextSourceType.KNOWLEDGE,
                source_id=chunk.document_id,
                authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
                canonical_key=f"knowledge:{chunk.document_id}:{chunk.chunk_id}",
                relevance_score=relevance,
                confidence=0.95,
                content_hash=c_hash,
                metadata=meta,
            )
            context_items.append(item)
            if len(context_items) >= limit:
                break

        return context_items
