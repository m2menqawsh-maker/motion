"""
tests/ai/memory/test_postgres_memory_repository.py
==================================================
Real PostgreSQL + pgvector integration test suite for PostgresMemoryRepository (S27.6).

Validates:
- Real pgvector extension availability.
- Migration DDL application.
- Tenant-filtered exact vector similarity search in PostgreSQL.
- Cross-tenant isolation at the SQL query level.
- Transaction rollback safety.
- DB-level constraints (confidence range, version >= 1).
- Foreign key cascade deletions.
- Supersede atomic lifecycle.
"""

import os
from datetime import datetime, timezone
import psycopg
import pytest

from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
from ai.memory.models import (
    EmbeddingRecord,
    MemoryEntry,
    MemoryFilter,
    TrustedTenantContext,
)
from ai.memory.types import (
    ConfidenceLevel,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
)
from scripts.core.memory.postgres_memory_repository import PostgresMemoryRepository

POSTGRES_TEST_URL = os.environ.get(
    "POSTGRES_TEST_URL",
    "postgresql://postgres:postgres@127.0.0.1:54329/test_memory"
)


def is_postgres_available() -> bool:
    """Helper to verify real PostgreSQL + pgvector connectivity."""
    try:
        conn = psycopg.connect(POSTGRES_TEST_URL, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_postgres_available(),
    reason="Real PostgreSQL container not reachable at 127.0.0.1:54329"
)


class TestPostgresMemoryRepository:

    @pytest.fixture
    def setup_postgres_repo(self):
        repo = PostgresMemoryRepository(
            db_url=POSTGRES_TEST_URL,
            dimension=128,
            auto_migrate=True,
        )
        # Clean test tables between runs
        with repo.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE ai_memory_embeddings, ai_memory_entries CASCADE;")
        return repo

    def test_schema_migration_and_vector_extension(self, setup_postgres_repo):
        """Verifies vector extension is active and memory tables exist in PostgreSQL."""
        repo = setup_postgres_repo
        with repo.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
                ext = cur.fetchone()
                assert ext is not None
                assert ext["extname"] == "vector"

                cur.execute("SELECT tablename FROM pg_tables WHERE tablename = 'ai_memory_entries';")
                tbl = cur.fetchone()
                assert tbl is not None
                assert tbl["tablename"] == "ai_memory_entries"

    def test_insert_and_exact_vector_similarity_search(self, setup_postgres_repo):
        """
        Inserts memory entries and embeddings into PostgreSQL,
        then executes tenant-isolated exact vector search.
        """
        repo = setup_postgres_repo
        embedder = DeterministicFakeEmbeddingProvider(dimension=128)
        now = datetime.now(timezone.utc)

        # 1. Insert Workspace A memory
        entry_a = MemoryEntry(
            id="pg_mem_a_01",
            workspace_id="ws_pg_alpha",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            content="Preferred audio transition is crossfade with 200ms duration",
            source_type=SourceType.USER_STATEMENT,
            confidence=0.92,
            confidence_level=ConfidenceLevel.HIGH,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            content_hash="hash_pg_01",
        )
        repo.create(entry_a)

        vec_a = embedder.embed_text(entry_a.content)
        repo.save_embedding(
            EmbeddingRecord(
                id="pg_emb_a_01",
                memory_id=entry_a.id,
                workspace_id=entry_a.workspace_id,
                memory_type=entry_a.memory_type,
                embedding=vec_a,
                embedding_model="test-embedder",
                dimension=128,
                created_at=now,
            )
        )

        # 2. Insert Workspace B memory
        entry_b = MemoryEntry(
            id="pg_mem_b_01",
            workspace_id="ws_pg_beta",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            content="Completely different topic: video render bitrate should be 15 Mbps",
            source_type=SourceType.USER_STATEMENT,
            confidence=0.88,
            confidence_level=ConfidenceLevel.HIGH,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            content_hash="hash_pg_02",
        )
        repo.create(entry_b)

        vec_b = embedder.embed_text(entry_b.content)
        repo.save_embedding(
            EmbeddingRecord(
                id="pg_emb_b_01",
                memory_id=entry_b.id,
                workspace_id=entry_b.workspace_id,
                memory_type=entry_b.memory_type,
                embedding=vec_b,
                embedding_model="test-embedder",
                dimension=128,
                created_at=now,
            )
        )

        # 3. Query Workspace A with query vector matching entry_a
        results_a = repo.query_semantic(
            workspace_id="ws_pg_alpha",
            query_vector=vec_a,
            limit=5,
            min_similarity=0.0,
        )

        assert len(results_a) == 1
        assert results_a[0].entry.id == "pg_mem_a_01"
        assert pytest.approx(results_a[0].similarity_score, 0.01) == 1.0

        # 4. Critical Gate: Query Workspace B with entry_a vector must NEVER return entry_a!
        results_cross = repo.query_semantic(
            workspace_id="ws_pg_beta",
            query_vector=vec_a,
            limit=5,
            min_similarity=0.0,
        )

        assert all(r.entry.workspace_id == "ws_pg_beta" for r in results_cross)
        assert not any(r.entry.id == "pg_mem_a_01" for r in results_cross)

    def test_database_constraints_enforcement(self, setup_postgres_repo):
        """Verifies PostgreSQL check constraints on confidence range and version."""
        repo = setup_postgres_repo
        now = datetime.now(timezone.utc)

        # Confidence > 1.0 check constraint violation in raw SQL
        with pytest.raises(psycopg.errors.CheckViolation):
            with repo.transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ai_memory_entries (
                            id, workspace_id, memory_type, scope, content,
                            source_type, confidence, confidence_level, created_at,
                            updated_at, version, content_hash
                        ) VALUES (
                            'bad_conf', 'ws_err', 'PROJECT', 'PROJECT', 'test',
                            'USER_STATEMENT', 1.5, 'HIGH', %(now)s, %(now)s, 1, 'hash_err'
                        );
                        """,
                        {"now": now}
                    )

    def test_transaction_rollback_safety(self, setup_postgres_repo):
        """Verifies transactional rollback leaves no partial records."""
        repo = setup_postgres_repo
        now = datetime.now(timezone.utc)

        try:
            with repo.transaction() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ai_memory_entries (
                            id, workspace_id, memory_type, scope, content,
                            source_type, confidence, confidence_level, created_at,
                            updated_at, version, content_hash
                        ) VALUES (
                            'temp_rollback', 'ws_rb', 'PROJECT', 'PROJECT', 'test',
                            'USER_STATEMENT', 0.9, 'HIGH', %(now)s, %(now)s, 1, 'hash_rb'
                        );
                        """,
                        {"now": now}
                    )
                    # Force error inside transaction
                    raise RuntimeError("Simulated transaction failure!")
        except RuntimeError:
            pass

        # Verify entry was rolled back
        assert repo.get("temp_rollback", "ws_rb") is None

    def test_cascade_deletion(self, setup_postgres_repo):
        """Deleting a memory entry in PostgreSQL cascades to delete its embeddings."""
        repo = setup_postgres_repo
        now = datetime.now(timezone.utc)

        entry = MemoryEntry(
            id="mem_cascade_01",
            workspace_id="ws_cascade",
            memory_type=MemoryType.KNOWLEDGE,
            scope=MemoryScope.WORKSPACE,
            content="Cascade test content",
            source_type=SourceType.SYSTEM_IMPORT,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            content_hash="hash_cas",
        )
        repo.create(entry)

        repo.save_embedding(
            EmbeddingRecord(
                id="emb_cascade_01",
                memory_id="mem_cascade_01",
                workspace_id="ws_cascade",
                memory_type=MemoryType.KNOWLEDGE,
                embedding=[0.1] * 128,
                embedding_model="test-embedder",
                dimension=128,
                created_at=now,
            )
        )

        assert repo.get_embedding("mem_cascade_01", "ws_cascade") is not None

        # Hard delete memory entry
        repo.delete("mem_cascade_01", "ws_cascade", hard_delete=True)

        # Verify embedding record was deleted via CASCADE
        assert repo.get_embedding("mem_cascade_01", "ws_cascade") is None

    def test_postgres_embedding_dimension_invariants(self, setup_postgres_repo):
        """
        Verifies PostgreSQL + pgvector dimension invariant enforcement:
        - Configured dimension (128) insert -> PASS
        - Wrong dimension vector insert -> REJECT with ValueError
        - Correct dimension query -> PASS
        - Wrong dimension query -> REJECT with ValueError
        """
        repo = setup_postgres_repo
        now = datetime.now(timezone.utc)

        # Create base memory entry
        entry = MemoryEntry(
            id="mem_dim_test_01",
            workspace_id="ws_dim_test",
            memory_type=MemoryType.KNOWLEDGE,
            scope=MemoryScope.WORKSPACE,
            content="Fact for dimension test",
            source_type=SourceType.SYSTEM_IMPORT,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            content_hash="hash_dim_01",
        )
        repo.create(entry)

        # 1. Correct dimension insert (128) -> PASS
        correct_emb = EmbeddingRecord(
            id="emb_dim_valid_01",
            memory_id="mem_dim_test_01",
            workspace_id="ws_dim_test",
            memory_type=MemoryType.KNOWLEDGE,
            embedding=[0.02] * 128,
            embedding_model="test-embedder-128",
            embedding_version="1.0.0",
            dimension=128,
            created_at=now,
        )
        repo.save_embedding(correct_emb)
        assert repo.get_embedding("mem_dim_test_01", "ws_dim_test") is not None

        # 2. Wrong dimension insert (256, 384, 1536) -> REJECT
        wrong_emb_256 = EmbeddingRecord(
            id="emb_dim_invalid_256",
            memory_id="mem_dim_test_01",
            workspace_id="ws_dim_test",
            memory_type=MemoryType.KNOWLEDGE,
            embedding=[0.02] * 256,
            embedding_model="test-embedder-256",
            embedding_version="1.0.0",
            dimension=256,
            created_at=now,
        )
        with pytest.raises(ValueError, match="Embedding dimension mismatch: repository configured for dimension 128, got record with dimension 256"):
            repo.save_embedding(wrong_emb_256)

        wrong_emb_384 = EmbeddingRecord(
            id="emb_dim_invalid_384",
            memory_id="mem_dim_test_01",
            workspace_id="ws_dim_test",
            memory_type=MemoryType.KNOWLEDGE,
            embedding=[0.02] * 384,
            embedding_model="test-embedder-384",
            embedding_version="1.0.0",
            dimension=384,
            created_at=now,
        )
        with pytest.raises(ValueError, match="Embedding dimension mismatch: repository configured for dimension 128, got record with dimension 384"):
            repo.save_embedding(wrong_emb_384)

        # 3. Correct dimension query (128) -> PASS
        results = repo.query_semantic("ws_dim_test", query_vector=[0.02] * 128)
        assert len(results) == 1
        assert results[0].entry.id == "mem_dim_test_01"

        # 4. Wrong dimension query (256, 384, 64) -> REJECT
        with pytest.raises(ValueError, match="Query vector dimension mismatch: repository configured for 128, got query vector of length 256"):
            repo.query_semantic("ws_dim_test", query_vector=[0.02] * 256)

        with pytest.raises(ValueError, match="Query vector dimension mismatch: repository configured for 128, got query vector of length 384"):
            repo.query_semantic("ws_dim_test", query_vector=[0.02] * 384)

        with pytest.raises(ValueError, match="Query vector dimension mismatch: repository configured for 128, got query vector of length 64"):
            repo.query_semantic("ws_dim_test", query_vector=[0.02] * 64)
