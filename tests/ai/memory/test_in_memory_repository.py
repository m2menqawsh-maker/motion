"""
tests/ai/memory/test_in_memory_repository.py
============================================
Tests for InMemoryMemoryRepository CRUD, structured query filtering, and semantic search (S27.6).
"""

from datetime import datetime, timedelta, timezone
import pytest

from ai.memory.models import (
    EmbeddingRecord,
    FrozenClock,
    MemoryEntry,
    MemoryFilter,
    MemorySearchResult,
)
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.types import (
    ConfidenceLevel,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
)


class TestInMemoryMemoryRepository:

    @pytest.fixture
    def setup_repo(self):
        base_time = datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc)
        clock = FrozenClock(base_time)
        repo = InMemoryMemoryRepository(clock=clock)
        return repo, clock, base_time

    def test_crud_operations(self, setup_repo):
        """Verifies create, get, update, and soft delete."""
        repo, clock, base_time = setup_repo

        entry = MemoryEntry(
            id="mem_01",
            workspace_id="ws_01",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            content="User prefers Cairo font with high contrast background",
            source_type=SourceType.USER_STATEMENT,
            confidence=0.9,
            confidence_level=ConfidenceLevel.HIGH,
            status=MemoryStatus.ACTIVE,
            created_at=base_time,
            updated_at=base_time,
            content_hash="hash_01",
        )

        created = repo.create(entry)
        assert created.id == "mem_01"

        # Fetch
        fetched = repo.get("mem_01", "ws_01")
        assert fetched is not None
        assert fetched.content == entry.content

        # Update
        clock.advance(10)
        fetched.content = "User prefers Cairo font Bold"
        updated = repo.update(fetched)
        assert updated.content == "User prefers Cairo font Bold"
        assert updated.updated_at == clock.now_utc()

        # Soft Delete
        clock.advance(5)
        deleted = repo.delete("mem_01", "ws_01", hard_delete=False)
        assert deleted is True

        # Normal structured query should not return soft deleted record
        filter_req = MemoryFilter(workspace_id="ws_01")
        results = repo.query_structured(filter_req)
        assert len(results) == 0

        # Query with include_inactive=True should return it
        filter_all = MemoryFilter(workspace_id="ws_01", include_inactive=True)
        results_all = repo.query_structured(filter_all)
        assert len(results_all) == 1
        assert results_all[0].status == MemoryStatus.DELETED

    def test_structured_filtering_and_pagination(self, setup_repo):
        """Tests filtering across memory_type, scope, project_id, and limits."""
        repo, clock, base_time = setup_repo

        for i in range(15):
            clock.advance(1)
            repo.create(
                MemoryEntry(
                    id=f"mem_item_{i:02d}",
                    workspace_id="ws_alpha",
                    project_id="prj_10" if i % 2 == 0 else "prj_20",
                    memory_type=MemoryType.DECISION if i < 10 else MemoryType.USER_PREFERENCE,
                    scope=MemoryScope.PROJECT if i < 10 else MemoryScope.USER,
                    content=f"Decision rule number {i}",
                    source_type=SourceType.DECISION,
                    confidence=0.85,
                    confidence_level=ConfidenceLevel.HIGH,
                    status=MemoryStatus.ACTIVE,
                    created_at=clock.now_utc(),
                    updated_at=clock.now_utc(),
                    content_hash=f"hash_{i}",
                )
            )

        # Filter by project_id prj_10
        f_proj = MemoryFilter(workspace_id="ws_alpha", project_id="prj_10", limit=20)
        res_proj = repo.query_structured(f_proj)
        assert len(res_proj) == 8
        assert all(r.project_id == "prj_10" for r in res_proj)

        # Filter by memory_type USER_PREFERENCE
        f_type = MemoryFilter(workspace_id="ws_alpha", memory_types=[MemoryType.USER_PREFERENCE])
        res_type = repo.query_structured(f_type)
        assert len(res_type) == 5

        # Pagination: limit=5, offset=0
        f_page1 = MemoryFilter(workspace_id="ws_alpha", limit=5, offset=0)
        page1 = repo.query_structured(f_page1)
        assert len(page1) == 5

        # Pagination: limit=5, offset=5
        f_page2 = MemoryFilter(workspace_id="ws_alpha", limit=5, offset=5)
        page2 = repo.query_structured(f_page2)
        assert len(page2) == 5

        # Verify page1 and page2 don't overlap
        ids_p1 = {r.id for r in page1}
        ids_p2 = {r.id for r in page2}
        assert ids_p1.isdisjoint(ids_p2)

    def test_supersede_lifecycle(self, setup_repo):
        """Verifies supersede atomically marks old entry as SUPERSEDED and links new version."""
        repo, clock, base_time = setup_repo

        old = repo.create(
            MemoryEntry(
                id="mem_pref_old",
                workspace_id="ws_01",
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.USER,
                content="I prefer fast cuts",
                source_type=SourceType.USER_STATEMENT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                status=MemoryStatus.ACTIVE,
                created_at=base_time,
                updated_at=base_time,
                version=1,
                content_hash="hash_old",
            )
        )

        clock.advance(100)
        new_entry = MemoryEntry(
            id="mem_pref_new",
            workspace_id="ws_01",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            content="I now prefer slow cinematic cuts",
            source_type=SourceType.USER_STATEMENT,
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            status=MemoryStatus.ACTIVE,
            created_at=clock.now_utc(),
            updated_at=clock.now_utc(),
            content_hash="hash_new",
        )

        superseded = repo.supersede("mem_pref_old", new_entry)

        assert superseded.id == "mem_pref_new"
        assert superseded.version == 2
        assert superseded.supersedes_id == "mem_pref_old"

        # Check old record status
        old_record = repo.get("mem_pref_old", "ws_01")
        assert old_record.status == MemoryStatus.SUPERSEDED

        # Normal query returns ONLY active
        active_list = repo.query_structured(MemoryFilter(workspace_id="ws_01"))
        assert len(active_list) == 1
        assert active_list[0].id == "mem_pref_new"

    def test_expiration_filtering(self, setup_repo):
        """Verifies expired records are excluded from normal structured retrieval."""
        repo, clock, base_time = setup_repo

        repo.create(
            MemoryEntry(
                id="mem_exp_01",
                workspace_id="ws_01",
                memory_type=MemoryType.WORKING,
                scope=MemoryScope.SESSION,
                content="Temporary working memory",
                source_type=SourceType.AI_INFERENCE,
                confidence=0.6,
                confidence_level=ConfidenceLevel.MEDIUM,
                status=MemoryStatus.ACTIVE,
                created_at=base_time,
                updated_at=base_time,
                expires_at=base_time + timedelta(seconds=60),
                content_hash="hash_exp",
            )
        )

        # Before expiry
        assert len(repo.query_structured(MemoryFilter(workspace_id="ws_01"))) == 1

        # Advance past expiry
        clock.advance(61)
        assert len(repo.query_structured(MemoryFilter(workspace_id="ws_01"))) == 0

        # Query with include_inactive=True should return it
        assert len(repo.query_structured(MemoryFilter(workspace_id="ws_01", include_inactive=True))) == 1

    def test_embedding_record_vector_length_must_match_declared_dimension(self):
        """Verifies EmbeddingRecord rejects vector whose length mismatches declared dimension."""
        now = datetime.now(timezone.utc)
        # Vector length is 3, but dimension is declared as 128
        with pytest.raises(ValueError, match="Embedding vector length .* does not match declared dimension"):
            EmbeddingRecord(
                id="emb_dim_01",
                memory_id="mem_01",
                workspace_id="ws_01",
                memory_type=MemoryType.KNOWLEDGE,
                embedding=[0.1, 0.2, 0.3],
                embedding_model="test-model",
                dimension=128,
                created_at=now,
            )

    def test_in_memory_repository_dimension_invariants(self, setup_repo):
        """Verifies InMemoryMemoryRepository enforces configured vector dimension on insert and query."""
        _, clock, base_time = setup_repo
        repo = InMemoryMemoryRepository(clock=clock, dimension=128)

        # 1. Correct dimension insert -> PASS
        correct_record = EmbeddingRecord(
            id="emb_corr_01",
            memory_id="mem_01",
            workspace_id="ws_01",
            memory_type=MemoryType.KNOWLEDGE,
            embedding=[0.05] * 128,
            embedding_model="test-embedder",
            embedding_version="1.0.0",
            dimension=128,
            created_at=base_time,
        )
        repo.save_embedding(correct_record)
        assert repo.get_embedding("mem_01", "ws_01") is not None

        # 2. Wrong dimension insert -> REJECT
        wrong_record = EmbeddingRecord(
            id="emb_wrong_01",
            memory_id="mem_02",
            workspace_id="ws_01",
            memory_type=MemoryType.KNOWLEDGE,
            embedding=[0.05] * 256,
            embedding_model="test-embedder-large",
            embedding_version="1.0.0",
            dimension=256,
            created_at=base_time,
        )
        with pytest.raises(ValueError, match="Embedding dimension mismatch: repository configured for 128, got 256"):
            repo.save_embedding(wrong_record)

        # 3. Correct dimension query -> PASS
        results = repo.query_semantic("ws_01", query_vector=[0.05] * 128)
        assert isinstance(results, list)

        # 4. Wrong dimension query -> REJECT
        with pytest.raises(ValueError, match="Query vector dimension mismatch: repository configured for 128, got query vector of length 256"):
            repo.query_semantic("ws_01", query_vector=[0.05] * 256)

        with pytest.raises(ValueError, match="Query vector dimension mismatch: repository configured for 128, got query vector of length 64"):
            repo.query_semantic("ws_01", query_vector=[0.05] * 64)
