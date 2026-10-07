"""
ai/memory/__init__.py
=====================
Public exports for AI Memory Subsystem (S27.6, S27.7).
"""

from ai.memory.types import (
    ConfidenceLevel,
    EpistemicStatus,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
    WriteDecisionType,
    confidence_to_level,
    level_to_min_confidence,
)
from ai.memory.models import (
    Clock,
    EmbeddingRecord,
    FrozenClock,
    MemoryCandidate,
    MemoryEntry,
    MemoryFilter,
    MemorySearchResult,
    MemoryWriteDecision,
    SystemClock,
    TrustedTenantContext,
)
from ai.memory.normalization import ContentNormalizer
from ai.memory.deduplication import DeduplicationEngine
from ai.memory.embeddings import EmbeddingProvider, DeterministicFakeEmbeddingProvider
from ai.memory.repository import MemoryRepository, InMemoryMemoryRepository
from ai.memory.policy import MemoryPolicy, MemoryPolicyConfig
from ai.memory.service import MemoryService, TenantAuthorizationError
from ai.memory.facade import ProjectMemoryFacade, ProjectAccessDeniedError, ProjectNotFoundError

__all__ = [
    # Types & Enums
    "ConfidenceLevel",
    "EpistemicStatus",
    "MemoryScope",
    "MemoryStatus",
    "MemoryType",
    "SourceType",
    "WriteDecisionType",
    "confidence_to_level",
    "level_to_min_confidence",
    # Models
    "Clock",
    "EmbeddingRecord",
    "FrozenClock",
    "MemoryCandidate",
    "MemoryEntry",
    "MemoryFilter",
    "MemorySearchResult",
    "MemoryWriteDecision",
    "SystemClock",
    "TrustedTenantContext",
    # Utilities & Components
    "ContentNormalizer",
    "DeduplicationEngine",
    "EmbeddingProvider",
    "DeterministicFakeEmbeddingProvider",
    "MemoryRepository",
    "InMemoryMemoryRepository",
    "MemoryPolicy",
    "MemoryPolicyConfig",
    "MemoryService",
    "TenantAuthorizationError",
    "ProjectMemoryFacade",
    "ProjectAccessDeniedError",
    "ProjectNotFoundError",
]
