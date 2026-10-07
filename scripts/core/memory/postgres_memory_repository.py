"""
scripts/core/memory/postgres_memory_repository.py
=================================================
PostgreSQL + pgvector persistent implementation of MemoryRepository (S27.6).

Architectural Boundaries (ADR-004):
- Lives in scripts/core/ (approved persistence layer) to satisfy S27.0 architecture guards.
- Enforces strict tenant isolation: `workspace_id = %s` filter is executed directly in SQL
  prior to ranking or similarity calculation.
- Exact Vector Search: Performs exhaustive tenant-filtered L2/cosine distance without HNSW.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple

import psycopg
from psycopg.rows import dict_row

from ai.memory.models import (
    Clock,
    EmbeddingRecord,
    MemoryEntry,
    MemoryFilter,
    MemorySearchResult,
    SystemClock,
)
from ai.memory.repository import MemoryRepository
from ai.memory.types import (
    ConfidenceLevel,
    EpistemicStatus,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
)

SCHEMA_MIGRATION_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS _ai_memory_schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_memory_entries (
    id VARCHAR(64) PRIMARY KEY,
    workspace_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64),
    project_id VARCHAR(64),
    session_id VARCHAR(64),
    memory_type VARCHAR(32) NOT NULL,
    scope VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    structured_payload JSONB,
    source_type VARCHAR(32) NOT NULL,
    source_id VARCHAR(64),
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    confidence_level VARCHAR(16) NOT NULL,
    epistemic_status VARCHAR(16) NOT NULL DEFAULT 'EXPLICIT',
    status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    content_hash VARCHAR(64) NOT NULL,
    supersedes_id VARCHAR(64),
    storage_ref VARCHAR(256),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ai_memory_ws ON ai_memory_entries(workspace_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_ws_proj ON ai_memory_entries(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_ws_type ON ai_memory_entries(workspace_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_ai_memory_ws_hash ON ai_memory_entries(workspace_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_ai_memory_ws_status ON ai_memory_entries(workspace_id, status);

CREATE TABLE IF NOT EXISTS ai_memory_embeddings (
    id VARCHAR(64) PRIMARY KEY,
    memory_id VARCHAR(64) NOT NULL REFERENCES ai_memory_entries(id) ON DELETE CASCADE,
    workspace_id VARCHAR(64) NOT NULL,
    project_id VARCHAR(64),
    memory_type VARCHAR(32) NOT NULL,
    embedding vector({dimension}) NOT NULL,
    embedding_model VARCHAR(64) NOT NULL,
    embedding_version VARCHAR(32) NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_embeddings_ws ON ai_memory_embeddings(workspace_id);
CREATE INDEX IF NOT EXISTS idx_ai_embeddings_mem ON ai_memory_embeddings(memory_id);
"""


class PostgresMemoryRepository(MemoryRepository):
    """
    Production-grade PostgreSQL + pgvector repository implementing tenant isolation.
    """

    def __init__(
        self,
        db_url: str,
        dimension: int = 384,
        clock: Optional[Clock] = None,
        auto_migrate: bool = True,
    ):
        self.db_url = db_url
        self.dimension = dimension
        self.clock: Clock = clock or SystemClock()

        if auto_migrate:
            self._init_schema()

    def get_connection(self) -> psycopg.Connection:
        """Establishes a connection to PostgreSQL."""
        return psycopg.connect(self.db_url, row_factory=dict_row)

    @contextmanager
    def transaction(self) -> Generator[psycopg.Connection, None, None]:
        """Managed transaction context with automatic commit and rollback."""
        conn = self.get_connection()
        try:
            with conn.transaction():
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Applies initial schema migrations if tables do not exist."""
        sql = SCHEMA_MIGRATION_SQL.replace("{dimension}", str(self.dimension))
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def create(self, entry: MemoryEntry) -> MemoryEntry:
        sql = """
        INSERT INTO ai_memory_entries (
            id, workspace_id, user_id, project_id, session_id,
            memory_type, scope, content, structured_payload,
            source_type, source_id, confidence, confidence_level,
            epistemic_status, status, created_at, updated_at,
            expires_at, version, content_hash, supersedes_id,
            storage_ref, metadata
        ) VALUES (
            %(id)s, %(workspace_id)s, %(user_id)s, %(project_id)s, %(session_id)s,
            %(memory_type)s, %(scope)s, %(content)s, %(structured_payload)s,
            %(source_type)s, %(source_id)s, %(confidence)s, %(confidence_level)s,
            %(epistemic_status)s, %(status)s, %(created_at)s, %(updated_at)s,
            %(expires_at)s, %(version)s, %(content_hash)s, %(supersedes_id)s,
            %(storage_ref)s, %(metadata)s
        );
        """
        payload_json = json.dumps(entry.structured_payload, ensure_ascii=False) if entry.structured_payload is not None else None
        meta_json = json.dumps(entry.metadata, ensure_ascii=False)

        params = {
            "id": entry.id,
            "workspace_id": entry.workspace_id,
            "user_id": entry.user_id,
            "project_id": entry.project_id,
            "session_id": entry.session_id,
            "memory_type": entry.memory_type.value,
            "scope": entry.scope.value,
            "content": entry.content,
            "structured_payload": payload_json,
            "source_type": entry.source_type.value,
            "source_id": entry.source_id,
            "confidence": entry.confidence,
            "confidence_level": entry.confidence_level.value,
            "epistemic_status": entry.epistemic_status.value,
            "status": entry.status.value,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "expires_at": entry.expires_at,
            "version": entry.version,
            "content_hash": entry.content_hash,
            "supersedes_id": entry.supersedes_id,
            "storage_ref": entry.storage_ref,
            "metadata": meta_json,
        }

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

        return entry.model_copy(deep=True)

    def get(self, memory_id: str, workspace_id: str) -> Optional[MemoryEntry]:
        sql = """
        SELECT * FROM ai_memory_entries
        WHERE id = %(id)s AND workspace_id = %(workspace_id)s;
        """
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"id": memory_id, "workspace_id": workspace_id})
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_entry(row)

    def update(self, entry: MemoryEntry) -> MemoryEntry:
        now = self.clock.now_utc()
        entry.updated_at = now

        sql = """
        UPDATE ai_memory_entries SET
            user_id = %(user_id)s,
            project_id = %(project_id)s,
            session_id = %(session_id)s,
            memory_type = %(memory_type)s,
            scope = %(scope)s,
            content = %(content)s,
            structured_payload = %(structured_payload)s,
            source_type = %(source_type)s,
            source_id = %(source_id)s,
            confidence = %(confidence)s,
            confidence_level = %(confidence_level)s,
            epistemic_status = %(epistemic_status)s,
            status = %(status)s,
            updated_at = %(updated_at)s,
            expires_at = %(expires_at)s,
            version = %(version)s,
            content_hash = %(content_hash)s,
            supersedes_id = %(supersedes_id)s,
            storage_ref = %(storage_ref)s,
            metadata = %(metadata)s
        WHERE id = %(id)s AND workspace_id = %(workspace_id)s;
        """
        payload_json = json.dumps(entry.structured_payload, ensure_ascii=False) if entry.structured_payload is not None else None
        meta_json = json.dumps(entry.metadata, ensure_ascii=False)

        params = {
            "id": entry.id,
            "workspace_id": entry.workspace_id,
            "user_id": entry.user_id,
            "project_id": entry.project_id,
            "session_id": entry.session_id,
            "memory_type": entry.memory_type.value,
            "scope": entry.scope.value,
            "content": entry.content,
            "structured_payload": payload_json,
            "source_type": entry.source_type.value,
            "source_id": entry.source_id,
            "confidence": entry.confidence,
            "confidence_level": entry.confidence_level.value,
            "epistemic_status": entry.epistemic_status.value,
            "status": entry.status.value,
            "updated_at": entry.updated_at,
            "expires_at": entry.expires_at,
            "version": entry.version,
            "content_hash": entry.content_hash,
            "supersedes_id": entry.supersedes_id,
            "storage_ref": entry.storage_ref,
            "metadata": meta_json,
        }

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if cur.rowcount == 0:
                    raise KeyError(f"MemoryEntry '{entry.id}' not found in workspace '{entry.workspace_id}'.")

        return entry.model_copy(deep=True)

    def delete(self, memory_id: str, workspace_id: str, hard_delete: bool = False) -> bool:
        with self.transaction() as conn:
            with conn.cursor() as cur:
                if hard_delete:
                    cur.execute(
                        "DELETE FROM ai_memory_entries WHERE id = %(id)s AND workspace_id = %(workspace_id)s;",
                        {"id": memory_id, "workspace_id": workspace_id}
                    )
                else:
                    now = self.clock.now_utc()
                    cur.execute(
                        """
                        UPDATE ai_memory_entries
                        SET status = 'DELETED', updated_at = %(now)s
                        WHERE id = %(id)s AND workspace_id = %(workspace_id)s;
                        """,
                        {"id": memory_id, "workspace_id": workspace_id, "now": now}
                    )
                return cur.rowcount > 0

    def query_structured(self, filter: MemoryFilter) -> List[MemoryEntry]:
        conditions = ["workspace_id = %(workspace_id)s"]
        params: Dict[str, Any] = {"workspace_id": filter.workspace_id}

        now = self.clock.now_utc()

        # Status & Expiration
        if not filter.include_inactive:
            conditions.append("status = 'ACTIVE'")
            conditions.append("(expires_at IS NULL OR expires_at > %(now)s)")
            params["now"] = now
        elif filter.status:
            conditions.append("status = %(status)s")
            params["status"] = filter.status.value

        if filter.memory_types:
            conditions.append("memory_type = ANY(%(memory_types)s)")
            params["memory_types"] = [t.value for t in filter.memory_types]

        if filter.scopes:
            conditions.append("scope = ANY(%(scopes)s)")
            params["scopes"] = [s.value for s in filter.scopes]

        if filter.project_id is not None:
            conditions.append("project_id = %(project_id)s")
            params["project_id"] = filter.project_id

        if filter.session_id is not None:
            conditions.append("session_id = %(session_id)s")
            params["session_id"] = filter.session_id

        if filter.user_id is not None:
            conditions.append("user_id = %(user_id)s")
            params["user_id"] = filter.user_id

        if filter.source_type is not None:
            conditions.append("source_type = %(source_type)s")
            params["source_type"] = filter.source_type.value

        if filter.source_id is not None:
            conditions.append("source_id = %(source_id)s")
            params["source_id"] = filter.source_id

        if filter.min_confidence is not None:
            conditions.append("confidence >= %(min_confidence)s")
            params["min_confidence"] = filter.min_confidence

        if filter.content_hash is not None:
            conditions.append("content_hash = %(content_hash)s")
            params["content_hash"] = filter.content_hash

        safe_limit = max(1, min(filter.limit, 100))
        params["limit"] = safe_limit
        params["offset"] = filter.offset

        where_clause = " AND ".join(conditions)
        sql = f"""
        SELECT * FROM ai_memory_entries
        WHERE {where_clause}
        ORDER BY updated_at DESC, id ASC
        LIMIT %(limit)s OFFSET %(offset)s;
        """

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [self._row_to_entry(r) for r in rows]

    def query_semantic(
        self,
        workspace_id: str,
        query_vector: List[float],
        filter: Optional[MemoryFilter] = None,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> List[MemorySearchResult]:
        if len(query_vector) != self.dimension:
            raise ValueError(
                f"Query vector dimension mismatch: repository configured for {self.dimension}, "
                f"got query vector of length {len(query_vector)}"
            )

        conditions = [
            "e.workspace_id = %(workspace_id)s",
            "emb.workspace_id = %(workspace_id)s",
        ]
        params: Dict[str, Any] = {
            "workspace_id": workspace_id,
            "query_vec": str(query_vector),
        }

        now = self.clock.now_utc()

        if filter and filter.include_inactive:
            if filter.status:
                conditions.append("e.status = %(status)s")
                params["status"] = filter.status.value
        else:
            conditions.append("e.status = 'ACTIVE'")
            conditions.append("(e.expires_at IS NULL OR e.expires_at > %(now)s)")
            params["now"] = now

        if filter:
            if filter.memory_types:
                conditions.append("e.memory_type = ANY(%(memory_types)s)")
                params["memory_types"] = [t.value for t in filter.memory_types]
            if filter.scopes:
                conditions.append("e.scope = ANY(%(scopes)s)")
                params["scopes"] = [s.value for s in filter.scopes]
            if filter.project_id is not None:
                conditions.append("e.project_id = %(project_id)s")
                params["project_id"] = filter.project_id
            if filter.session_id is not None:
                conditions.append("e.session_id = %(session_id)s")
                params["session_id"] = filter.session_id
            if filter.user_id is not None:
                conditions.append("e.user_id = %(user_id)s")
                params["user_id"] = filter.user_id
            if filter.min_confidence is not None:
                conditions.append("e.confidence >= %(min_confidence)s")
                params["min_confidence"] = filter.min_confidence

        safe_limit = max(1, min(limit, 100))
        params["limit"] = safe_limit

        where_clause = " AND ".join(conditions)

        # Exact cosine search:
        # Distance = (emb.embedding <=> %(query_vec)s::vector)
        # Canonical similarity = 1.0 - distance
        sql = f"""
        SELECT
            e.*,
            (emb.embedding <=> %(query_vec)s::vector) AS distance,
            (1.0 - (emb.embedding <=> %(query_vec)s::vector)) AS similarity
        FROM ai_memory_entries e
        JOIN ai_memory_embeddings emb ON e.id = emb.memory_id
        WHERE {where_clause}
        ORDER BY similarity DESC, e.confidence DESC, e.updated_at DESC, e.id ASC
        LIMIT %(limit)s;
        """

        results: List[MemorySearchResult] = []
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                for row in rows:
                    sim = float(row["similarity"])
                    dist = float(row["distance"])
                    if sim < min_similarity:
                        continue
                    entry = self._row_to_entry(row)
                    results.append(
                        MemorySearchResult(
                            entry=entry,
                            similarity_score=round(sim, 6),
                            distance=round(dist, 6),
                        )
                    )
        return results

    def save_embedding(self, record: EmbeddingRecord) -> None:
        if record.dimension != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: repository configured for dimension {self.dimension}, "
                f"got record with dimension {record.dimension} "
                f"(model='{record.embedding_model}', version='{record.embedding_version}')"
            )
        if len(record.embedding) != self.dimension:
            raise ValueError(
                f"Embedding vector length mismatch: repository configured for dimension {self.dimension}, "
                f"got vector length {len(record.embedding)}"
            )

        sql = """
        INSERT INTO ai_memory_embeddings (
            id, memory_id, workspace_id, project_id, memory_type,
            embedding, embedding_model, embedding_version, dimension, created_at
        ) VALUES (
            %(id)s, %(memory_id)s, %(workspace_id)s, %(project_id)s, %(memory_type)s,
            %(embedding)s::vector, %(embedding_model)s, %(embedding_version)s, %(dimension)s, %(created_at)s
        )
        ON CONFLICT (id) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            embedding_model = EXCLUDED.embedding_model,
            embedding_version = EXCLUDED.embedding_version;
        """
        params = {
            "id": record.id,
            "memory_id": record.memory_id,
            "workspace_id": record.workspace_id,
            "project_id": record.project_id,
            "memory_type": record.memory_type.value,
            "embedding": str(record.embedding),
            "embedding_model": record.embedding_model,
            "embedding_version": record.embedding_version,
            "dimension": record.dimension,
            "created_at": record.created_at,
        }
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

    def get_embedding(self, memory_id: str, workspace_id: str) -> Optional[EmbeddingRecord]:
        sql = """
        SELECT id, memory_id, workspace_id, project_id, memory_type,
               embedding::text, embedding_model, embedding_version, dimension, created_at
        FROM ai_memory_embeddings
        WHERE memory_id = %(memory_id)s AND workspace_id = %(workspace_id)s;
        """
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"memory_id": memory_id, "workspace_id": workspace_id})
                row = cur.fetchone()
                if not row:
                    return None

                # Parse vector text [x, y, z] to float list
                raw_vec = row["embedding"].strip("[]").split(",")
                vec = [float(x.strip()) for x in raw_vec if x.strip()]

                return EmbeddingRecord(
                    id=row["id"],
                    memory_id=row["memory_id"],
                    workspace_id=row["workspace_id"],
                    project_id=row["project_id"],
                    memory_type=MemoryType(row["memory_type"]),
                    embedding=vec,
                    embedding_model=row["embedding_model"],
                    embedding_version=row["embedding_version"],
                    dimension=row["dimension"],
                    created_at=row["created_at"],
                )

    def find_by_hash(
        self,
        workspace_id: str,
        content_hash: str,
        memory_type: Optional[MemoryType] = None,
        scope: Optional[MemoryScope] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Optional[MemoryEntry]:
        conditions = [
            "workspace_id = %(workspace_id)s",
            "content_hash = %(content_hash)s",
            "status = 'ACTIVE'",
            "(expires_at IS NULL OR expires_at > %(now)s)",
        ]
        params: Dict[str, Any] = {
            "workspace_id": workspace_id,
            "content_hash": content_hash,
            "now": self.clock.now_utc(),
        }

        if memory_type is not None:
            conditions.append("memory_type = %(memory_type)s")
            params["memory_type"] = memory_type.value
        if scope is not None:
            conditions.append("scope = %(scope)s")
            params["scope"] = scope.value
        if user_id is not None:
            conditions.append("user_id = %(user_id)s")
            params["user_id"] = user_id
        if project_id is not None:
            conditions.append("project_id = %(project_id)s")
            params["project_id"] = project_id

        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM ai_memory_entries WHERE {where_clause} ORDER BY updated_at DESC LIMIT 1;"

        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                if not row:
                    return None
                return self._row_to_entry(row)

    def supersede(self, old_id: str, new_entry: MemoryEntry) -> MemoryEntry:
        now = self.clock.now_utc()
        with self.transaction() as conn:
            with conn.cursor() as cur:
                # 1. Fetch old entry to increment version
                cur.execute(
                    "SELECT version FROM ai_memory_entries WHERE id = %(id)s AND workspace_id = %(ws)s;",
                    {"id": old_id, "ws": new_entry.workspace_id}
                )
                row = cur.fetchone()
                if not row:
                    raise KeyError(f"MemoryEntry '{old_id}' not found in workspace '{new_entry.workspace_id}'.")

                old_version = row["version"]

                # 2. Mark old entry as SUPERSEDED
                cur.execute(
                    """
                    UPDATE ai_memory_entries
                    SET status = 'SUPERSEDED', updated_at = %(now)s
                    WHERE id = %(id)s AND workspace_id = %(ws)s;
                    """,
                    {"id": old_id, "ws": new_entry.workspace_id, "now": now}
                )

                # 3. Insert new entry linked via supersedes_id
                new_entry.supersedes_id = old_id
                new_entry.version = old_version + 1
                new_entry.created_at = now
                new_entry.updated_at = now

                payload_json = json.dumps(new_entry.structured_payload, ensure_ascii=False) if new_entry.structured_payload is not None else None
                meta_json = json.dumps(new_entry.metadata, ensure_ascii=False)

                insert_sql = """
                INSERT INTO ai_memory_entries (
                    id, workspace_id, user_id, project_id, session_id,
                    memory_type, scope, content, structured_payload,
                    source_type, source_id, confidence, confidence_level,
                    epistemic_status, status, created_at, updated_at,
                    expires_at, version, content_hash, supersedes_id,
                    storage_ref, metadata
                ) VALUES (
                    %(id)s, %(workspace_id)s, %(user_id)s, %(project_id)s, %(session_id)s,
                    %(memory_type)s, %(scope)s, %(content)s, %(structured_payload)s,
                    %(source_type)s, %(source_id)s, %(confidence)s, %(confidence_level)s,
                    %(epistemic_status)s, %(status)s, %(created_at)s, %(updated_at)s,
                    %(expires_at)s, %(version)s, %(content_hash)s, %(supersedes_id)s,
                    %(storage_ref)s, %(metadata)s
                );
                """
                params = {
                    "id": new_entry.id,
                    "workspace_id": new_entry.workspace_id,
                    "user_id": new_entry.user_id,
                    "project_id": new_entry.project_id,
                    "session_id": new_entry.session_id,
                    "memory_type": new_entry.memory_type.value,
                    "scope": new_entry.scope.value,
                    "content": new_entry.content,
                    "structured_payload": payload_json,
                    "source_type": new_entry.source_type.value,
                    "source_id": new_entry.source_id,
                    "confidence": new_entry.confidence,
                    "confidence_level": new_entry.confidence_level.value,
                    "epistemic_status": new_entry.epistemic_status.value,
                    "status": new_entry.status.value,
                    "created_at": new_entry.created_at,
                    "updated_at": new_entry.updated_at,
                    "expires_at": new_entry.expires_at,
                    "version": new_entry.version,
                    "content_hash": new_entry.content_hash,
                    "supersedes_id": new_entry.supersedes_id,
                    "storage_ref": new_entry.storage_ref,
                    "metadata": meta_json,
                }
                cur.execute(insert_sql, params)

        return new_entry.model_copy(deep=True)

    @staticmethod
    def _row_to_entry(row: Dict[str, Any]) -> MemoryEntry:
        payload = row["structured_payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)

        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        elif meta is None:
            meta = {}

        return MemoryEntry(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            project_id=row["project_id"],
            session_id=row["session_id"],
            memory_type=MemoryType(row["memory_type"]),
            scope=MemoryScope(row["scope"]),
            content=row["content"],
            structured_payload=payload,
            source_type=SourceType(row["source_type"]),
            source_id=row["source_id"],
            confidence=row["confidence"],
            confidence_level=ConfidenceLevel(row["confidence_level"]),
            epistemic_status=EpistemicStatus(row["epistemic_status"]),
            status=MemoryStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            expires_at=row["expires_at"],
            version=row["version"],
            content_hash=row["content_hash"],
            supersedes_id=row["supersedes_id"],
            storage_ref=row["storage_ref"],
            metadata=meta,
        )
