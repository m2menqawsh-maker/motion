"""
ai/context/__init__.py
======================
Canonical Context Builder package for the AI and Media Intelligence platform (S27.8).
"""

from __future__ import annotations

from ai.context.types import (
    AUTHORITY_PRECEDENCE,
    BudgetExceededError,
    ContextAuthority,
    ContextBuilderError,
    ContextDiagnostics,
    ContextExclusion,
    ContextItem,
    ContextPackage,
    ContextRequest,
    ContextSection,
    ContextSectionPackage,
    ContextSourceType,
    ExclusionReason,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
)
from ai.context.needs import (
    ContextNeeds,
    classify_context_needs,
)
from ai.context.ranking import (
    ContextRanker,
    ContextRankingPolicy,
)
from ai.context.deduplication import (
    ContextDeduplicator,
)
from ai.context.compression import (
    ContextCompressor,
    DeterministicContextCompressor,
)
from ai.context.budgeting import (
    ConservativeTokenEstimator,
    ContextBudgetManager,
    ContextBudgetPolicy,
    DeterministicTokenEstimator,
    EstimatorKind,
    TokenEstimator,
)
from ai.context.retrieval import (
    DeterministicKnowledgeRetriever,
    KnowledgeDocument,
    KnowledgeRetriever,
    MemoryRetriever,
    ProjectFactRetriever,
    RequestRetriever,
    SharedConfigRetriever,
    SystemPolicyRetriever,
    contains_secret,
)
from ai.context.assembly import (
    CANONICAL_SECTION_ORDER,
    ContextAssembler,
)
from ai.context.builder import (
    ContextBuilder,
)

__all__ = [
    # Types & Enums
    "ContextSection",
    "ContextAuthority",
    "ContextSourceType",
    "ExclusionReason",
    "AUTHORITY_PRECEDENCE",
    "ContextItem",
    "ContextExclusion",
    "ContextDiagnostics",
    "ContextSectionPackage",
    "ContextRequest",
    "ContextPackage",
    # Errors
    "ContextBuilderError",
    "ProjectAccessDeniedError",
    "ProjectNotFoundError",
    "BudgetExceededError",
    # Needs
    "ContextNeeds",
    "classify_context_needs",
    # Ranking
    "ContextRanker",
    "ContextRankingPolicy",
    # Deduplication
    "ContextDeduplicator",
    # Compression
    "ContextCompressor",
    "DeterministicContextCompressor",
    # Budgeting
    "TokenEstimator",
    "EstimatorKind",
    "ConservativeTokenEstimator",
    "DeterministicTokenEstimator",
    "ContextBudgetPolicy",
    "ContextBudgetManager",
    # Retrieval
    "KnowledgeRetriever",
    "KnowledgeDocument",
    "DeterministicKnowledgeRetriever",
    "ProjectFactRetriever",
    "MemoryRetriever",
    "SystemPolicyRetriever",
    "SharedConfigRetriever",
    "RequestRetriever",
    "contains_secret",
    # Assembly
    "CANONICAL_SECTION_ORDER",
    "ContextAssembler",
    # Builder Facade
    "ContextBuilder",
]
