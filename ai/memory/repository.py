"""
ai/memory/repository.py
=======================
Repository boundary interface and hermetic in-memory adapter for AI Memory (S27.6).

Invariants:
- Never imports raw SQL drivers (sqlite3, psycopg2, asyncpg, etc.) as mandated by S27.0.
- Mandatory tenant isolation: every query enforces workspace_id filtering prior to vector similarity.
"""

from __future__ import annotations

import copy
import math
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ai.memory.models import (
    Clock,
    EmbeddingRecord,
    MemoryEntry,
    MemoryFilter,
    MemorySearchResult,
    SystemClock,
)
from ai.memory.types import MemoryScope, MemoryStatus, MemoryType


class MemoryRepository(ABC):
    """
    Authoritative abstraction for memory persistence and vector indexing.
    """

    @abstractmethod
    def create(self, entry: MemoryEntry) -> MemoryEntry:
        """Persists a new memory entry."""
        raise NotImplementedError

    @abstractmethod
    def get(self, memory_id: str, workspace_id: str) -> Optional[MemoryEntry]:
        """Retrieves a single memory entry scoped to the given workspace."""
        raise NotImplementedError

    @abstractmethod
    def update(self, entry: MemoryEntry) -> MemoryEntry:
        """Updates an existing memory entry within its workspace boundary."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, memory_id: str, workspace_id: str, hard_delete: bool = False) -> bool:
        """Soft-deletes (or hard-deletes) a memory entry within its workspace boundary."""
        raise NotImplementedError

    @abstractmethod
    def query_structured(self, filter: MemoryFilter) -> List[MemoryEntry]:
        """Performs structured filtering by tenant, type, scope, project, session, status, etc."""
        raise NotImplementedError

    @abstractmethod
    def query_semantic(
        self,
        workspace_id: str,
        query_vector: List[float],
        filter: Optional[MemoryFilter] = None,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> List[MemorySearchResult]:
        """
        Executes tenant-isolated vector similarity search.
        
        Strict rule: workspace_id isolation MUST be applied BEFORE similarity calculation.
        """
        raise NotImplementedError

    @abstractmethod
    def save_embedding(self, record: EmbeddingRecord) -> None:
        """Persists a vector embedding record associated with a memory item."""
        raise NotImplementedError

    @abstractmethod
    def get_embedding(self, memory_id: str, workspace_id: str) -> Optional[EmbeddingRecord]:
        """Retrieves an embedding record by memory ID and workspace boundary."""
        raise NotImplementedError

    @abstractmethod
    def find_by_hash(
        self,
        workspace_id: str,
        content_hash: str,
        memory_type: Optional[MemoryType] = None,
        scope: Optional[MemoryScope] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Optional[MemoryEntry]:
        """Finds an existing active memory entry matching the content hash and entity constraints."""
        raise NotImplementedError

    @abstractmethod
    def supersede(self, old_id: str, new_entry: MemoryEntry) -> MemoryEntry:
        """Atomically marks old_id as SUPERSEDED and inserts new_entry with supersedes_id linked."""
        raise NotImplementedError


class InMemoryMemoryRepository(MemoryRepository):
    """
    Hermetic, thread-safe in-memory adapter for unit testing and local execution.
    """

    def __init__(self, clock: Optional[Clock] = None, dimension: Optional[int] = None):
        self._lock = threading.RLock()
        self.clock: Clock = clock or SystemClock()
        self.dimension = dimension
        # Structure: {(workspace_id, memory_id): MemoryEntry}
        self._entries: Dict[Tuple[str, str], MemoryEntry] = {}
        # Structure: {(workspace_id, memory_id): EmbeddingRecord}
        self._embeddings: Dict[Tuple[str, str], EmbeddingRecord] = {}

    def create(self, entry: MemoryEntry) -> MemoryEntry:
        with self._lock:
            key = (entry.workspace_id, entry.id)
            if key in self._entries:
                raise ValueError(f"MemoryEntry with ID '{entry.id}' already exists in workspace '{entry.workspace_id}'.")
            cloned = entry.model_copy(deep=True)
            self._entries[key] = cloned
            return cloned.model_copy(deep=True)

    def get(self, memory_id: str, workspace_id: str) -> Optional[MemoryEntry]:
        with self._lock:
            key = (workspace_id, memory_id)
            entry = self._entries.get(key)
            if not entry:
                return None
            return entry.model_copy(deep=True)

    def update(self, entry: MemoryEntry) -> MemoryEntry:
        with self._lock:
            key = (entry.workspace_id, entry.id)
            if key not in self._entries:
                raise KeyError(f"Cannot update non-existent MemoryEntry '{entry.id}' in workspace '{entry.workspace_id}'.")
            cloned = entry.model_copy(deep=True)
            cloned.updated_at = self.clock.now_utc()
            self._entries[key] = cloned
            return cloned.model_copy(deep=True)

    def delete(self, memory_id: str, workspace_id: str, hard_delete: bool = False) -> bool:
        with self._lock:
            key = (workspace_id, memory_id)
            entry = self._entries.get(key)
            if not entry:
                return False
            if hard_delete:
                del self._entries[key]
                self._embeddings.pop(key, None)
            else:
                entry.status = MemoryStatus.DELETED
                entry.updated_at = self.clock.now_utc()
            return True

    def query_structured(self, filter: MemoryFilter) -> List[MemoryEntry]:
        with self._lock:
            now = self.clock.now_utc()
            results: List[MemoryEntry] = []

            for (ws, _), entry in self._entries.items():
                # 1. Mandatory tenant isolation
                if ws != filter.workspace_id:
                    continue

                # 2. Status filtering & Expiration
                if not filter.include_inactive:
                    if not entry.is_active(at_time=now):
                        continue
                else:
                    if filter.status and entry.status != filter.status:
                        continue

                # 3. Optional attribute filters
                if filter.memory_types and entry.memory_type not in filter.memory_types:
                    continue
                if filter.scopes and entry.scope not in filter.scopes:
                    continue
                if filter.project_id is not None and entry.project_id != filter.project_id:
                    continue
                if filter.session_id is not None and entry.session_id != filter.session_id:
                    continue
                if filter.user_id is not None and entry.user_id != filter.user_id:
                    continue
                if filter.source_type is not None and entry.source_type != filter.source_type:
                    continue
                if filter.source_id is not None and entry.source_id != filter.source_id:
                    continue
                if filter.min_confidence is not None and entry.confidence < filter.min_confidence:
                    continue
                if filter.content_hash is not None and entry.content_hash != filter.content_hash:
                    continue

                results.append(entry.model_copy(deep=True))

            # Deterministic sorting: updated_at DESC, id ASC
            results.sort(key=lambda e: (-e.updated_at.timestamp(), e.id))

            # Pagination
            start = filter.offset
            end = start + min(filter.limit, 100)
            return results[start:end]

    def query_semantic(
        self,
        workspace_id: str,
        query_vector: List[float],
        filter: Optional[MemoryFilter] = None,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> List[MemorySearchResult]:
        with self._lock:
            expected_dim = self.dimension
            if expected_dim is None and self._embeddings:
                expected_dim = next(iter(self._embeddings.values())).dimension
            if expected_dim is not None and len(query_vector) != expected_dim:
                raise ValueError(
                    f"Query vector dimension mismatch: repository configured for {expected_dim}, "
                    f"got query vector of length {len(query_vector)}"
                )

            now = self.clock.now_utc()
            safe_limit = max(1, min(limit, 100))
            scored: List[Tuple[float, float, MemoryEntry]] = []

            # 1. Filter candidates strictly by workspace first
            for (ws, mem_id), entry in self._entries.items():
                if ws != workspace_id:
                    continue

                # Status / Expiration check
                if filter and filter.include_inactive:
                    if filter.status and entry.status != filter.status:
                        continue
                else:
                    if not entry.is_active(at_time=now):
                        continue

                # Apply structural filters if provided
                if filter:
                    if filter.memory_types and entry.memory_type not in filter.memory_types:
                        continue
                    if filter.scopes and entry.scope not in filter.scopes:
                        continue
                    if filter.project_id is not None and entry.project_id != filter.project_id:
                        continue
                    if filter.session_id is not None and entry.session_id != filter.session_id:
                        continue
                    if filter.user_id is not None and entry.user_id != filter.user_id:
                        continue
                    if filter.min_confidence is not None and entry.confidence < filter.min_confidence:
                        continue

                # Fetch embedding for this entry
                emb_rec = self._embeddings.get((ws, mem_id))
                if not emb_rec:
                    continue

                sim = self._cosine_similarity(query_vector, emb_rec.embedding)
                if sim < min_similarity:
                    continue

                # Cosine distance = 1.0 - similarity (bounded)
                dist = max(0.0, 1.0 - sim)
                scored.append((sim, dist, entry))

            # Deterministic tie-breaking:
            # 1. Similarity score DESC
            # 2. Confidence DESC
            # 3. Updated_at DESC
            # 4. ID ASC
            scored.sort(
                key=lambda item: (
                    -item[0],
                    -item[2].confidence,
                    -item[2].updated_at.timestamp(),
                    item[2].id,
                )
            )

            results: List[MemorySearchResult] = []
            for sim, dist, entry in scored[:safe_limit]:
                results.append(
                    MemorySearchResult(
                        entry=entry.model_copy(deep=True),
                        similarity_score=round(sim, 6),
                        distance=round(dist, 6),
                    )
                )
            return results

    def save_embedding(self, record: EmbeddingRecord) -> None:
        with self._lock:
            if len(record.embedding) != record.dimension:
                raise ValueError(
                    f"Embedding vector length ({len(record.embedding)}) does not match record dimension ({record.dimension})"
                )
            if self.dimension is not None:
                if record.dimension != self.dimension:
                    raise ValueError(
                        f"Embedding dimension mismatch: repository configured for {self.dimension}, "
                        f"got {record.dimension} (model='{record.embedding_model}', version='{record.embedding_version}')"
                    )
            elif self._embeddings:
                existing_dim = next(iter(self._embeddings.values())).dimension
                if record.dimension != existing_dim:
                    raise ValueError(
                        f"Embedding dimension mismatch: repository index dimension is {existing_dim}, "
                        f"got {record.dimension}"
                    )
            key = (record.workspace_id, record.memory_id)
            self._embeddings[key] = record.model_copy(deep=True)

    def get_embedding(self, memory_id: str, workspace_id: str) -> Optional[EmbeddingRecord]:
        with self._lock:
            key = (workspace_id, memory_id)
            emb = self._embeddings.get(key)
            if not emb:
                return None
            return emb.model_copy(deep=True)

    def find_by_hash(
        self,
        workspace_id: str,
        content_hash: str,
        memory_type: Optional[MemoryType] = None,
        scope: Optional[MemoryScope] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Optional[MemoryEntry]:
        with self._lock:
            now = self.clock.now_utc()
            for (ws, _), entry in self._entries.items():
                if ws != workspace_id:
                    continue
                if entry.content_hash != content_hash:
                    continue
                if not entry.is_active(at_time=now):
                    continue
                if memory_type is not None and entry.memory_type != memory_type:
                    continue
                if scope is not None and entry.scope != scope:
                    continue
                if user_id is not None and entry.user_id != user_id:
                    continue
                if project_id is not None and entry.project_id != project_id:
                    continue
                return entry.model_copy(deep=True)
            return None

    def supersede(self, old_id: str, new_entry: MemoryEntry) -> MemoryEntry:
        with self._lock:
            key_old = (new_entry.workspace_id, old_id)
            old = self._entries.get(key_old)
            if not old:
                raise KeyError(f"Cannot supersede non-existent MemoryEntry '{old_id}' in workspace '{new_entry.workspace_id}'.")

            # 1. Mark old entry as superseded
            old.status = MemoryStatus.SUPERSEDED
            old.updated_at = self.clock.now_utc()

            # 2. Link supersedes_id and increment version
            new_entry.supersedes_id = old_id
            new_entry.version = old.version + 1

            # 3. Store new entry
            return self.create(new_entry)

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        if len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        val = dot / (norm1 * norm2)
        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, val))
