"""
tests/ai/memory/test_models.py
==============================
Unit tests for AI Memory canonical models, scopes, statuses, and validation invariants (S27.6).
"""

from datetime import datetime, timedelta, timezone
import pytest

from ai.memory.models import (
    FrozenClock,
    MemoryEntry,
    MemoryFilter,
    SystemClock,
    TrustedTenantContext,
)
from ai.memory.types import (
    ConfidenceLevel,
    EpistemicStatus,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
    confidence_to_level,
    level_to_min_confidence,
)


class TestMemoryModels:

    def test_all_canonical_memory_types_supported(self):
        """Validates all 8 canonical types plus backward-compatible types."""
        expected_types = {
            "WORKING",
            "CONVERSATION",
            "PROJECT",
            "USER_PREFERENCE",
            "WORKSPACE",
            "DECISION",
            "KNOWLEDGE",
            "MEDIA_INTELLIGENCE",
            "EPISODIC",
            "SEMANTIC",
        }
        actual_types = {t.value for t in MemoryType}
        assert expected_types.issubset(actual_types)

    def test_all_canonical_memory_scopes_supported(self):
        """Validates canonical memory scopes."""
        expected_scopes = {"GLOBAL", "WORKSPACE", "USER", "PROJECT", "SESSION"}
        actual_scopes = {s.value for s in MemoryScope}
        assert expected_scopes == actual_scopes

    def test_memory_entry_valid_instantiation(self):
        """Verifies creating a pristine typed MemoryEntry."""
        now = datetime.now(timezone.utc)
        entry = MemoryEntry(
            workspace_id="ws_main",
            user_id="usr_01",
            project_id="prj_100",
            session_id="sess_50",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            content="User prefers minimalist typography with 1.2 line height",
            source_type=SourceType.USER_STATEMENT,
            source_id="msg_001",
            confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            epistemic_status=EpistemicStatus.EXPLICIT,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            content_hash="abc1234567890abcdef",
            metadata={"category": "typography"},
        )
        assert entry.id.startswith("mem_")
        assert entry.version == 1
        assert entry.confidence_level == ConfidenceLevel.HIGH
        assert entry.is_active(now) is True

    def test_global_scope_guards_against_tenant_private_memory(self):
        """Enforces that GLOBAL scope rejects tenant-private or user-bound content."""
        # 1. Tenant workspace cannot create GLOBAL memory
        with pytest.raises(ValueError, match="Scope GLOBAL is reserved"):
            MemoryEntry(
                workspace_id="ws_tenant_123",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.GLOBAL,
                content="Some fact",
                source_type=SourceType.USER_STATEMENT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="1234567890",
            )

        # 2. Cannot bind user_id to GLOBAL memory
        with pytest.raises(ValueError, match="Scope GLOBAL cannot be bound to a specific user"):
            MemoryEntry(
                workspace_id="global",
                user_id="usr_01",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.GLOBAL,
                content="Some fact",
                source_type=SourceType.SYSTEM_IMPORT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="1234567890",
            )

        # 3. Cannot bind project_id to GLOBAL memory
        with pytest.raises(ValueError, match="Scope GLOBAL cannot be bound to a specific project"):
            MemoryEntry(
                workspace_id="global",
                project_id="prj_01",
                memory_type=MemoryType.KNOWLEDGE,
                scope=MemoryScope.GLOBAL,
                content="Some fact",
                source_type=SourceType.SYSTEM_IMPORT,
                confidence=0.9,
                confidence_level=ConfidenceLevel.HIGH,
                content_hash="1234567890",
            )

        # 4. Valid GLOBAL memory created by system
        global_entry = MemoryEntry(
            workspace_id="global",
            memory_type=MemoryType.KNOWLEDGE,
            scope=MemoryScope.GLOBAL,
            content="Standard broadcast safe audio loudness is -16 LUFS for dialog",
            source_type=SourceType.SYSTEM_IMPORT,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            content_hash="1234567890",
        )
        assert global_entry.scope == MemoryScope.GLOBAL

    def test_confidence_level_mapping_and_thresholds(self):
        """Validates confidence classification thresholds."""
        assert confidence_to_level(0.0) == ConfidenceLevel.LOW
        assert confidence_to_level(0.49) == ConfidenceLevel.LOW
        assert confidence_to_level(0.50) == ConfidenceLevel.MEDIUM
        assert confidence_to_level(0.79) == ConfidenceLevel.MEDIUM
        assert confidence_to_level(0.80) == ConfidenceLevel.HIGH
        assert confidence_to_level(1.0) == ConfidenceLevel.HIGH

        assert level_to_min_confidence(ConfidenceLevel.LOW) == 0.0
        assert level_to_min_confidence(ConfidenceLevel.MEDIUM) == 0.5
        assert level_to_min_confidence(ConfidenceLevel.HIGH) == 0.8

    def test_expiration_clock_behavior(self):
        """Verifies is_active() evaluates expiration timestamps correctly without sleep."""
        base_time = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
        clock = FrozenClock(base_time)

        entry = MemoryEntry(
            workspace_id="ws_test",
            memory_type=MemoryType.WORKING,
            scope=MemoryScope.SESSION,
            content="Scratchpad temporary calculation",
            source_type=SourceType.AI_INFERENCE,
            confidence=0.6,
            confidence_level=ConfidenceLevel.MEDIUM,
            expires_at=base_time + timedelta(seconds=60),
            content_hash="hash_working_123",
        )

        # At T=0, active
        assert entry.is_active(clock.now_utc()) is True

        # Advance 30 seconds -> still active
        clock.advance(30)
        assert entry.is_active(clock.now_utc()) is True

        # Advance 31 seconds -> T=61, expired!
        clock.advance(31)
        assert entry.is_active(clock.now_utc()) is False

    def test_trusted_tenant_context_permission_checks(self):
        """Verifies TrustedTenantContext enforces project and user boundaries."""
        ctx_restricted = TrustedTenantContext(
            workspace_id="ws_acme",
            user_id="usr_alice",
            roles=["editor"],
            accessible_projects=["prj_alpha", "prj_beta"],
            is_admin=False,
        )

        assert ctx_restricted.can_access_project("prj_alpha") is True
        assert ctx_restricted.can_access_project("prj_beta") is True
        assert ctx_restricted.can_access_project("prj_gamma") is False
        assert ctx_restricted.can_access_user("usr_alice") is True
        assert ctx_restricted.can_access_user("usr_bob") is False

        # Admin bypass
        ctx_admin = TrustedTenantContext(
            workspace_id="ws_acme",
            user_id="usr_admin",
            roles=["admin"],
            accessible_projects=None,
            is_admin=True,
        )
        assert ctx_admin.can_access_project("prj_gamma") is True
        assert ctx_admin.can_access_user("usr_bob") is True
