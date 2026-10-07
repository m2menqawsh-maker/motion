"""
ai/contracts/memory.py
======================
Contracts for long-term and working memory retrieval in the AI subsystem.

Invariants:
- Multi-tenant boundary: workspace_id is strictly required on queries to prevent
  cross-tenant vector or context leakage (ADR-004 DEC-06.4).
- Contract definition only; pgvector storage logic deferred to future stages.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import Field

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum
from ai.contracts.common import ProvenanceRecord


class MemoryType(str, Enum):
    """Categorization of AI memory structures."""
    WORKING = "WORKING"
    CONVERSATION = "CONVERSATION"
    PROJECT = "PROJECT"
    USER_PREFERENCE = "USER_PREFERENCE"
    WORKSPACE = "WORKSPACE"
    DECISION = "DECISION"
    KNOWLEDGE = "KNOWLEDGE"
    MEDIA_INTELLIGENCE = "MEDIA_INTELLIGENCE"
    # Legacy / macro categories retained for backward compatibility (ADR-004 DEC-06.2)
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"


class MemoryScope(str, Enum):
    """
    Authoritative boundary scopes for memory accessibility.
    
    GLOBAL is strictly restricted to system-controlled safe shared knowledge.
    User-generated or private tenant memory is forbidden in GLOBAL scope.
    """
    GLOBAL = "GLOBAL"
    WORKSPACE = "WORKSPACE"
    USER = "USER"
    PROJECT = "PROJECT"
    SESSION = "SESSION"


class SourceType(str, Enum):
    """Provenance origin of the memory record."""
    USER_STATEMENT = "USER_STATEMENT"
    CONVERSATION_SUMMARY = "CONVERSATION_SUMMARY"
    PROJECT_FACT = "PROJECT_FACT"
    HUMAN_CONFIRMATION = "HUMAN_CONFIRMATION"
    AI_INFERENCE = "AI_INFERENCE"
    MEDIA_ANALYSIS = "MEDIA_ANALYSIS"
    DECISION = "DECISION"
    SYSTEM_IMPORT = "SYSTEM_IMPORT"


class EpistemicStatus(str, Enum):
    """Epistemic classification distinguishing stated facts from AI inferences."""
    EXPLICIT = "EXPLICIT"    # Explicitly articulated by user or human
    INFERRED = "INFERRED"    # Inferred from model analysis or behavioral pattern
    CONFIRMED = "CONFIRMED"  # Validated through human verification or confirmation


MemoryTypeEnum = strict_enum(MemoryType)
MemoryScopeEnum = strict_enum(MemoryScope)
SourceTypeEnum = strict_enum(SourceType)
EpistemicStatusEnum = strict_enum(EpistemicStatus)


class MemoryQuery(AIContractModel):
    """
    Contract for semantic search and retrieval from AI memory.
    Enforces tenant scoping before vector ranking.
    """
    workspace_id: str = Field(min_length=1, description="Mandatory tenant isolation identifier")
    project_id: Optional[str] = Field(default=None, description="Optional project context constraint")
    session_id: Optional[str] = Field(default=None, description="Optional session context constraint")
    memory_type: MemoryTypeEnum = Field(description="Target memory tier")
    query_text: str = Field(min_length=1, description="Natural language semantic search query")
    limit: int = Field(default=10, gt=0, le=100, description="Maximum number of items to retrieve")
    minimum_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity/confidence threshold (0.0 to 1.0)",
    )


class MemoryEntry(AIContractModel):
    """An individual memory record retrieved from the memory subsystem."""
    entry_id: str = Field(min_length=1, description="Unique memory record identifier")
    memory_type: MemoryTypeEnum = Field(description="Memory category")
    content: str = Field(min_length=1, description="Textual or structured memory content")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Vector similarity or ranking score")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence metric of retrieved context")
    provenance: ProvenanceRecord = Field(description="Record of when and how this memory was formed")
    created_at: TzAwareDatetime = Field(description="Timezone-aware creation timestamp")


class MemoryResult(AIContractModel):
    """Outcome contract containing retrieved memory items matching a MemoryQuery."""
    entries: List[MemoryEntry] = Field(default_factory=list, description="Ranked retrieved memory items")
    total_found: int = Field(ge=0, description="Total number of matching memories discovered")
    query_duration_ms: int = Field(ge=0, description="Query execution duration in milliseconds")
