"""
tests/ai/memory/test_serialization.py
======================================
Deterministic serialization and persistence round-trip tests for MemoryEntry (AI-06R).

Guarantees:
1. Strict deterministic JSON round-trip: serialize -> persist -> deserialize without data loss.
2. Complete coverage for all JSON data types:
   - Nested objects (deep hierarchy)
   - Arrays (heterogeneous elements)
   - Strings (with special characters and symbols)
   - Integers and numbers
   - Booleans (True / False)
   - Null values
   - Arabic UTF-8 text
   - Mixed Arabic / English script
3. Strict rejection of invalid/untyped Python objects:
   - Open file handles
   - Class instances / custom objects
   - Functions / lambdas
   - Arbitrary bytes
"""

import os
from datetime import datetime, timezone
import psycopg
import pytest
from pydantic import ValidationError

from ai.memory.models import (
    EmbeddingRecord,
    MemoryCandidate,
    MemoryEntry,
)
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.types import (
    ConfidenceLevel,
    EpistemicStatus,
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
    try:
        conn = psycopg.connect(POSTGRES_TEST_URL, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


class ArbitraryUserClass:
    def __init__(self, val: str = "untrusted"):
        self.val = val


class TestMemorySerialization:

    @pytest.fixture
    def complex_memory_entry(self) -> MemoryEntry:
        now = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
        payload = {
            "nested_object": {
                "level_1": {
                    "level_2": {
                        "deep_key": "قيمة عميقة متداخلة",
                        "numeric_id": 98765,
                    }
                }
            },
            "arrays": [
                1,
                2,
                "عنصر مصفوفة عربي",
                "English Array Item",
                True,
                False,
                None,
                [10, 20, 30],
                {"nested_in_array": "قيمة داخل مصفوفة"},
            ],
            "strings": "نص قياسي يحتوي رموز: !@#$%^&*()_+|~=`{}[]:\";'<>?,./",
            "ints": 42,
            "negative_int": -100,
            "zero": 0,
            "booleans_true": True,
            "booleans_false": False,
            "null_value": None,
            "arabic_text": "اللغة العربية الفصحى: مرحباً بك في نظام الذاكرة الموحد للمشروع",
            "mixed_text": "Style guide: سرعة المونتاج 60fps مع دقة 4K UHD وموسيقى هادئة 120bpm",
        }
        metadata = {
            "category": "user_preference",
            "tag_arabic": "تفضيلات المشهد والمونتاج",
            "counter": 1001,
            "is_active": True,
            "optional_attr": None,
            "nested_meta": {
                "author": "محرر الفيديو",
                "revision": 2,
            },
        }

        return MemoryEntry(
            id="mem_ser_test_001",
            workspace_id="ws_ser_01",
            user_id="usr_arabic_01",
            project_id="prj_ser_01",
            session_id="ses_ser_01",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            content="تفضيل تحريري: استخدام موسيقى هادئة مع تعليق صوتي عربي وإنجليزي (Voiceover: 4K 60fps)",
            structured_payload=payload,
            source_type=SourceType.USER_STATEMENT,
            source_id="msg_src_100",
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            epistemic_status=EpistemicStatus.EXPLICIT,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            version=1,
            content_hash="canonical_sha256_hash_value_12345",
            metadata=metadata,
        )

    def test_pydantic_model_json_serialization_round_trip(self, complex_memory_entry):
        """Verifies deterministic Pydantic json dump and revalidation without data loss."""
        # 1. Serialize to JSON string
        json_str = complex_memory_entry.model_dump_json()
        assert isinstance(json_str, str)

        # 2. Deserialize from JSON string
        deserialized = MemoryEntry.model_validate_json(json_str)

        # 3. Assert deep equality
        assert deserialized.id == complex_memory_entry.id
        assert deserialized.content == complex_memory_entry.content
        assert deserialized.structured_payload == complex_memory_entry.structured_payload
        assert deserialized.metadata == complex_memory_entry.metadata
        assert deserialized.structured_payload["arabic_text"] == "اللغة العربية الفصحى: مرحباً بك في نظام الذاكرة الموحد للمشروع"
        assert deserialized.structured_payload["mixed_text"] == "Style guide: سرعة المونتاج 60fps مع دقة 4K UHD وموسيقى هادئة 120bpm"
        assert deserialized.metadata["tag_arabic"] == "تفضيلات المشهد والمونتاج"
        assert deserialized == complex_memory_entry

    def test_in_memory_persistence_round_trip(self, complex_memory_entry):
        """Verifies persistence through InMemoryMemoryRepository preserves exact types."""
        repo = InMemoryMemoryRepository()
        created = repo.create(complex_memory_entry)
        assert created == complex_memory_entry

        retrieved = repo.get(complex_memory_entry.id, complex_memory_entry.workspace_id)
        assert retrieved is not None
        assert retrieved.structured_payload == complex_memory_entry.structured_payload
        assert retrieved.metadata == complex_memory_entry.metadata
        assert retrieved == complex_memory_entry

    @pytest.mark.skipif(not is_postgres_available(), reason="PostgreSQL not available at 127.0.0.1:54329")
    def test_postgres_jsonb_persistence_round_trip(self, complex_memory_entry):
        """Verifies real PostgreSQL JSONB column round-trip preserves Unicode Arabic and nested structs."""
        repo = PostgresMemoryRepository(POSTGRES_TEST_URL, dimension=128, auto_migrate=True)
        # Ensure workspace clean
        with repo.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM ai_memory_entries WHERE workspace_id = %(ws)s;", {"ws": complex_memory_entry.workspace_id})

        created = repo.create(complex_memory_entry)
        retrieved = repo.get(complex_memory_entry.id, complex_memory_entry.workspace_id)

        assert retrieved is not None
        assert retrieved.id == complex_memory_entry.id
        assert retrieved.content == complex_memory_entry.content
        assert retrieved.structured_payload == complex_memory_entry.structured_payload
        assert retrieved.metadata == complex_memory_entry.metadata
        assert retrieved.structured_payload["arabic_text"] == "اللغة العربية الفصحى: مرحباً بك في نظام الذاكرة الموحد للمشروع"
        assert retrieved.structured_payload["mixed_text"] == "Style guide: سرعة المونتاج 60fps مع دقة 4K UHD وموسيقى هادئة 120bpm"
        assert retrieved.metadata["tag_arabic"] == "تفضيلات المشهد والمونتاج"
        assert retrieved.content_hash == complex_memory_entry.content_hash

    # -------------------------------------------------------------------------
    # Rejection of Invalid / Untyped Python Objects
    # -------------------------------------------------------------------------

    def test_rejection_of_custom_class_instance(self):
        """Rejects arbitrary class instances in structured_payload and metadata."""
        with pytest.raises(ValidationError):
            MemoryEntry(
                workspace_id="ws_01",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.WORKSPACE,
                content="Valid content",
                structured_payload={"invalid_obj": ArbitraryUserClass()},
                source_type=SourceType.USER_STATEMENT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="h1",
            )

        with pytest.raises(ValidationError):
            MemoryEntry(
                workspace_id="ws_01",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.WORKSPACE,
                content="Valid content",
                metadata={"invalid_obj": ArbitraryUserClass()},
                source_type=SourceType.USER_STATEMENT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="h1",
            )

    def test_rejection_of_open_file_handles(self):
        """Rejects open file handle descriptors in structured_payload and metadata."""
        with open(__file__, "r", encoding="utf-8") as f:
            with pytest.raises(ValidationError):
                MemoryEntry(
                    workspace_id="ws_01",
                    memory_type=MemoryType.KNOWLEDGE,
                    scope=MemoryScope.WORKSPACE,
                    content="Valid content",
                    structured_payload={"open_file": f},
                    source_type=SourceType.USER_STATEMENT,
                    confidence=0.9,
                    confidence_level=ConfidenceLevel.HIGH,
                    content_hash="h1",
                )

            with pytest.raises(ValidationError):
                MemoryEntry(
                    workspace_id="ws_01",
                    memory_type=MemoryType.KNOWLEDGE,
                    scope=MemoryScope.WORKSPACE,
                    content="Valid content",
                    metadata={"open_file": f},
                    source_type=SourceType.USER_STATEMENT,
                    confidence=0.9,
                    confidence_level=ConfidenceLevel.HIGH,
                    content_hash="h1",
                )

    def test_rejection_of_functions_and_callables(self):
        """Rejects lambdas, methods, and functions in structured_payload and metadata."""
        with pytest.raises(ValidationError):
            MemoryEntry(
                workspace_id="ws_01",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.WORKSPACE,
                content="Valid content",
                structured_payload={"function": lambda x: x * 2},
                source_type=SourceType.USER_STATEMENT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="h1",
            )

        with pytest.raises(ValidationError):
            MemoryEntry(
                workspace_id="ws_01",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.WORKSPACE,
                content="Valid content",
                metadata={"function": lambda x: x * 2},
                source_type=SourceType.USER_STATEMENT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="h1",
            )

    def test_rejection_of_raw_bytes(self):
        """Rejects non-contractual raw bytes in structured_payload and metadata."""
        with pytest.raises(ValidationError):
            MemoryEntry(
                workspace_id="ws_01",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.WORKSPACE,
                content="Valid content",
                structured_payload={"raw_binary": b"\x00\x01\x02\x03\xff"},
                source_type=SourceType.USER_STATEMENT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="h1",
            )

        with pytest.raises(ValidationError):
            MemoryEntry(
                workspace_id="ws_01",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.WORKSPACE,
                content="Valid content",
                metadata={"raw_binary": b"\x00\x01\x02\x03\xff"},
                source_type=SourceType.USER_STATEMENT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="h1",
            )

    def test_memory_candidate_rejects_untyped_objects(self):
        """Verifies that unpersisted proposals (MemoryCandidate) enforce the same typed boundaries."""
        with pytest.raises(ValidationError):
            MemoryCandidate(
                proposed_type=MemoryType.USER_PREFERENCE,
                proposed_scope=MemoryScope.USER,
                content="Candidate proposal",
                structured_payload={"obj": ArbitraryUserClass()},
                source_type=SourceType.USER_STATEMENT,
            )

        with pytest.raises(ValidationError):
            MemoryCandidate(
                proposed_type=MemoryType.USER_PREFERENCE,
                proposed_scope=MemoryScope.USER,
                content="Candidate proposal",
                metadata={"fn": lambda: None},
                source_type=SourceType.USER_STATEMENT,
            )
