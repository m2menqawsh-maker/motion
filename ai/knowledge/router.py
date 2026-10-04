"""
ai/knowledge/router.py
======================
Knowledge Router for scoping and resolving creative knowledge (S28-02).

Guarantees:
- Knowledge = Information & Experience (Knowledge ≠ Runtime Authority).
- Single knowledge authority: Skills and Creative components retrieve knowledge
  via KnowledgeRouter rather than loading raw references/ files directly.
- Structured audit observability recording candidate filtering, selections,
  and explicit exclusion reasons.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import KnowledgeDescriptor, RetrievalMode
from ai.knowledge.contracts import (
    KnowledgeChunk,
    KnowledgeRetrievalQuery,
    KnowledgeRetrievalResult,
    RetrievedChunk,
)
from ai.knowledge.indexer import KnowledgeIndexer
from ai.knowledge.loader import KnowledgeLoader
from ai.knowledge.registry import KnowledgeRegistry
from ai.knowledge.retriever import KnowledgeRetriever
from ai.knowledge.semantic import BaseSemanticScorer


class KnowledgeRouter:
    """
    Coordinates registry, loader, indexer, and retriever into a unified,
    governed knowledge access point for Creative Intelligence.
    """

    def __init__(
        self,
        registry: Optional[KnowledgeRegistry] = None,
        indexer: Optional[KnowledgeIndexer] = None,
        loader: Optional[KnowledgeLoader] = None,
        semantic_scorer: Optional[BaseSemanticScorer] = None,
        workspace_root: Optional[Path] = None,
    ) -> None:
        self.workspace_root = workspace_root or Path.cwd()
        self.registry = registry or KnowledgeRegistry()
        self.indexer = indexer or KnowledgeIndexer()
        self.loader = loader or KnowledgeLoader(workspace_root=self.workspace_root)
        self.retriever = KnowledgeRetriever(
            indexer=self.indexer,
            registry=self.registry,
            semantic_scorer=semantic_scorer,
        )

    def initialize_canonical_catalog(self, verify_hash: bool = True) -> int:
        """
        Loads canonical descriptors from references/, indexes them, and registers them.
        Returns total number of indexed semantic chunks.
        """
        loaded_docs = self.loader.load_canonical_catalog(
            registry=self.registry,
            verify_hash=verify_hash,
        )
        total_chunks = self.indexer.index_many(loaded_docs)
        return total_chunks

    def route_knowledge(
        self,
        query: str,
        video_type: Optional[str] = None,
        platform: Optional[str] = None,
        audio_mode: Optional[AudioMode] = None,
        language: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        required_knowledge_ids: Optional[List[str]] = None,
        limit_chunks: int = 4,
        max_tokens: int = 2500,
        retrieval_mode: Optional[RetrievalMode] = None,
    ) -> KnowledgeRetrievalResult:
        """
        Routes and retrieves small, bounded, relevant knowledge matching the creative context.
        """
        retrieval_query = KnowledgeRetrievalQuery(
            query=query,
            video_type=video_type,
            platform=platform,
            audio_mode=audio_mode,
            language=language,
            tags=tags or [],
            category=category,
            required_knowledge_ids=required_knowledge_ids or [],
            limit_chunks=limit_chunks,
            max_tokens=max_tokens,
            retrieval_mode=retrieval_mode or RetrievalMode.HYBRID,
        )
        return self.retrieve(retrieval_query)

    def retrieve(self, query: KnowledgeRetrievalQuery) -> KnowledgeRetrievalResult:
        """
        Directly executes a structured KnowledgeRetrievalQuery via the retriever.
        """
        return self.retriever.retrieve(query)

    def resolve_skill_knowledge(
        self,
        skill_id: str,
        required_knowledge_ids: Sequence[str],
        audio_mode: Optional[AudioMode] = None,
        limit_chunks: int = 5,
    ) -> KnowledgeRetrievalResult:
        """
        Authoritative resolver for required_knowledge declared by a Skill.
        Retrieves matching chunks via the unified Knowledge Platform.
        """
        query = KnowledgeRetrievalQuery(
            query=f"skill:{skill_id} required knowledge",
            audio_mode=audio_mode,
            required_knowledge_ids=list(required_knowledge_ids),
            limit_chunks=limit_chunks,
        )
        return self.retriever.retrieve(query)
