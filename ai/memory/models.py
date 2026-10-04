"""
ai/memory/models.py
===================
Canonical domain models, value objects, and query filters for AI Memory (S27.6, S27.7).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

JsonObject = Dict[str, JsonValue]

from ai.memory.types import (
    ConfidenceLevel,
    EpistemicStatus,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
    WriteDecisionType,
    confidence_to_level,
)


class Clock(Protocol):
    """Protocol for abstracting time generation for deterministic testing."""
    def now_utc(self) -> datetime:
        ...


class SystemClock:
    """Standard system clock providing timezone-aware UTC datetimes."""
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


class FrozenClock:
    """Deterministic clock initialized with a fixed datetime, advancing manually."""
    def __init__(self, current_time: datetime):
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        self._current_time = current_time

    def now_utc(self) -> datetime:
        return self._current_time

    def advance(self, seconds: float) -> None:
        from datetime import timedelta
        self._current_time += timedelta(seconds=seconds)

    def set_time(self, new_time: datetime) -> None:
        if new_time.tzinfo is None:
            new_time = new_time.replace(tzinfo=timezone.utc)
        self._current_time = new_time


class TrustedTenantContext(BaseModel):
    """
    Authoritative server/caller context establishing tenant boundaries.
    
    Prevents AI models from masquerading as different tenants or bypassing isolation.
    """
    model_config = ConfigDict(frozen=True)

    workspace_id: str = Field(min_length=1, description="Authoritative workspace boundary")
    user_id: Optional[str] = Field(default=None, description="Current authenticated actor")
    roles: List[str] = Field(default_factory=list, description="Actor role claims")
    accessible_projects: Optional[List[str]] = Field(
        default=None,
        description="Explicit list of project IDs the actor has active permission to read/write. "
                    "If None, all projects in the workspace are accessible."
    )
    is_admin: bool = Field(default=False, description="System-level administrator flag")

    def can_access_project(self, project_id: Optional[str]) -> bool:
        """Verifies if the tenant context is authorized to access the given project."""
        if project_id is None:
            return True
        if self.is_admin:
            return True
        if self.accessible_projects is None:
            return True
        return project_id in self.accessible_projects

    def can_access_user(self, target_user_id: Optional[str]) -> bool:
        """Verifies if the tenant context is authorized for user-scoped memory."""
        if target_user_id is None:
            return True
        if self.is_admin:
            return True
        return self.user_id == target_user_id


class MemoryEntry(BaseModel):
    """
    Authoritative canonical representation of an individual memory item.
    """
    model_config = ConfigDict(frozen=False)

    id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:16]}")
    workspace_id: str = Field(min_length=1, description="Tenant workspace ID")
    user_id: Optional[str] = Field(default=None, description="Optional user association")
    project_id: Optional[str] = Field(default=None, description="Optional project association")
    session_id: Optional[str] = Field(default=None, description="Optional session/run association")

    memory_type: MemoryType = Field(description="Canonical memory tier")
    scope: MemoryScope = Field(description="Accessibility boundary")
    content: str = Field(min_length=1, description="Normalized text payload")
    structured_payload: Optional[Dict[str, JsonValue]] = Field(default=None, description="Optional structured data")

    source_type: SourceType = Field(description="Provenance source")
    source_id: Optional[str] = Field(default=None, description="Originating identifier")

    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    confidence_level: ConfidenceLevel = Field(description="Canonical classification")
    epistemic_status: EpistemicStatus = Field(default=EpistemicStatus.EXPLICIT)

    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(default=None)

    version: int = Field(default=1, ge=1, description="Monotonically increasing revision")
    content_hash: str = Field(min_length=1, description="Canonical SHA-256 hash of normalized content")
    supersedes_id: Optional[str] = Field(default=None, description="ID of previous memory replaced by this one")
    storage_ref: Optional[str] = Field(default=None, description="StorageService canonical object key for heavy blobs")
    metadata: Dict[str, JsonValue] = Field(default_factory=dict, description="Typed metadata dictionary")

    @model_validator(mode="after")
    def validate_scope_and_confidence(self) -> MemoryEntry:
        # Enforce GLOBAL scope restrictions:
        # GLOBAL scope cannot store private user/tenant memories.
        if self.scope == MemoryScope.GLOBAL:
            if self.workspace_id not in ("global", "system", "shared") and self.source_type != SourceType.SYSTEM_IMPORT:
                raise ValueError(
                    f"Illegal MemoryEntry: Scope GLOBAL is reserved for system-controlled safe shared knowledge. "
                    f"Tenant workspace '{self.workspace_id}' cannot create GLOBAL memory."
                )
            if self.user_id is not None:
                raise ValueError("Illegal MemoryEntry: Scope GLOBAL cannot be bound to a specific user.")
            if self.project_id is not None:
                raise ValueError("Illegal MemoryEntry: Scope GLOBAL cannot be bound to a specific project.")

        # Ensure confidence_level aligns with confidence score
        expected_level = confidence_to_level(self.confidence)
        if self.confidence_level != expected_level:
            object.__setattr__(self, "confidence_level", expected_level)

        return self

    def is_active(self, at_time: Optional[datetime] = None) -> bool:
        """Determines if the memory entry is actively retrievable at given reference time."""
        if self.status != MemoryStatus.ACTIVE:
            return False
        if self.expires_at is not None:
            ref_time = at_time or datetime.now(timezone.utc)
            if ref_time.tzinfo is None:
                ref_time = ref_time.replace(tzinfo=timezone.utc)
            exp_time = self.expires_at
            if exp_time.tzinfo is None:
                exp_time = exp_time.replace(tzinfo=timezone.utc)
            if exp_time <= ref_time:
                return False
        return True


class EmbeddingRecord(BaseModel):
    """
    Index representation associating a canonical memory entry with a vector embedding.
    """
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: f"emb_{uuid.uuid4().hex[:16]}")
    memory_id: str = Field(min_length=1)
    workspace_id: str = Field(min_length=1)
    project_id: Optional[str] = Field(default=None)
    memory_type: MemoryType = Field()
    embedding: List[float] = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    embedding_version: str = Field(default="1.0.0")
    dimension: int = Field(gt=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_dimension_alignment(self) -> EmbeddingRecord:
        if len(self.embedding) != self.dimension:
            raise ValueError(
                f"Embedding vector length ({len(self.embedding)}) does not match declared dimension ({self.dimension})"
            )
        return self


class MemoryFilter(BaseModel):
    """
    Structured query filter criteria for repository queries.
    """
    workspace_id: str = Field(min_length=1, description="Required tenant boundary")
    memory_types: Optional[List[MemoryType]] = Field(default=None)
    scopes: Optional[List[MemoryScope]] = Field(default=None)
    project_id: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    source_type: Optional[SourceType] = Field(default=None)
    source_id: Optional[str] = Field(default=None)
    status: Optional[MemoryStatus] = Field(default=None)
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    content_hash: Optional[str] = Field(default=None)
    include_inactive: bool = Field(default=False, description="Whether to include expired/deleted/superseded records")
    limit: int = Field(default=20, gt=0, le=100, description="Safe maximum bound")
    offset: int = Field(default=0, ge=0)


class MemorySearchResult(BaseModel):
    """Vector/semantic retrieval match."""
    model_config = ConfigDict(frozen=True)

    entry: MemoryEntry
    similarity_score: float = Field(ge=0.0, le=1.0, description="Canonical cosine similarity (1.0 = identical)")
    distance: float = Field(ge=0.0, description="Underlying metric distance")


class MemoryCandidate(BaseModel):
    """
    Unpersisted memory proposal submitted by AI models or domain events.
    Must be mediated by MemoryPolicy before storage.
    """
    proposed_type: MemoryType = Field(description="Requested memory tier")
    proposed_scope: MemoryScope = Field(description="Requested boundary scope")
    content: str = Field(min_length=1, description="Raw content proposal")
    structured_payload: Optional[Dict[str, JsonValue]] = Field(default=None)
    source_type: SourceType = Field(description="Provenance source")
    source_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    project_id: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)

    evidence: List[str] = Field(default_factory=list, description="Supporting context or message snippets")
    suggested_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    suggested_ttl_seconds: Optional[int] = Field(default=None, gt=0)
    storage_ref: Optional[str] = Field(default=None)
    metadata: Dict[str, JsonValue] = Field(default_factory=dict)


class MemoryWriteDecision(BaseModel):
    """
    Policy evaluation outcome governing whether and how a candidate is persisted.
    """
    decision_type: WriteDecisionType
    reason_code: str
    reason_detail: str
    candidate: MemoryCandidate

    final_type: Optional[MemoryType] = None
    final_scope: Optional[MemoryScope] = None
    final_confidence: Optional[float] = None
    final_confidence_level: Optional[ConfidenceLevel] = None
    epistemic_status: Optional[EpistemicStatus] = None

    normalized_content: Optional[str] = None
    content_hash: Optional[str] = None
    expires_at: Optional[datetime] = None

    target_entry_id: Optional[str] = None
    supersedes_id: Optional[str] = None
