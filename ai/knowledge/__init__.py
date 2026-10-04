"""
ai/knowledge/__init__.py
========================
Canonical Knowledge Platform package for Creative Intelligence (S28-02).

Guarantees:
- Knowledge = Information & Experience (Knowledge ≠ Runtime Authority).
- Strict separation of responsibilities:
  * KnowledgeRegistry: what documents are known and their metadata.
  * KnowledgeLoader: source loading and integrity validation.
  * KnowledgeIndexer: semantic boundary chunking and searchable indexing.
  * KnowledgeRetriever: multi-stage retrieval, reranking, deduplication, bounding.
  * KnowledgeRouter: creative context scoping and skill knowledge resolution.
"""

from __future__ import annotations

from ai.knowledge.contracts import (
    KnowledgeChunk,
    KnowledgeRetrievalQuery,
    KnowledgeRetrievalResult,
    RetrievalMode,
    RetrievedChunk,
)
from ai.knowledge.semantic import (
    BaseSemanticScorer,
    DenseConceptSemanticScorer,
    ProviderSemanticScorer,
    UnavailableSemanticScorer,
)
from ai.knowledge.indexer import (
    KnowledgeIndexer,
    tokenize,
)
from ai.knowledge.loader import (
    KnowledgeHashMismatchError,
    KnowledgeLoader,
    KnowledgeLoaderError,
    KnowledgeRetiredError,
    KnowledgeSourceNotFoundError,
    LoadedKnowledgeDocument,
)
from ai.knowledge.registry import (
    DuplicateKnowledgeError,
    KnowledgeNotFoundError,
    KnowledgeRegistry,
    KnowledgeRegistryError,
)
from ai.knowledge.retriever import (
    KnowledgeRetriever,
)
from ai.knowledge.router import (
    KnowledgeRouter,
)

__all__ = [
    # Contracts & Models
    "KnowledgeChunk",
    "KnowledgeRetrievalQuery",
    "RetrievedChunk",
    "KnowledgeRetrievalResult",
    "RetrievalMode",
    # Semantic Scorer
    "BaseSemanticScorer",
    "DenseConceptSemanticScorer",
    "ProviderSemanticScorer",
    "UnavailableSemanticScorer",
    # Registry
    "KnowledgeRegistry",
    "KnowledgeRegistryError",
    "DuplicateKnowledgeError",
    "KnowledgeNotFoundError",
    # Loader
    "KnowledgeLoader",
    "LoadedKnowledgeDocument",
    "KnowledgeLoaderError",
    "KnowledgeSourceNotFoundError",
    "KnowledgeHashMismatchError",
    "KnowledgeRetiredError",
    # Indexer
    "KnowledgeIndexer",
    "tokenize",
    # Retriever
    "KnowledgeRetriever",
    # Router
    "KnowledgeRouter",
]
