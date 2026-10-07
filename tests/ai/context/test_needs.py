"""
tests/ai/context/test_needs.py
==============================
Deterministic classification tests for ContextNeeds (S27.8).
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.memory import MemoryType
from ai.context import ContextRequest, classify_context_needs
from ai.memory.models import TrustedTenantContext


class TestContextNeedsClassification:

    @pytest.fixture
    def base_context(self) -> TrustedTenantContext:
        return TrustedTenantContext(workspace_id="ws_1", user_id="usr_1")

    def test_speech_to_text_needs(self, base_context):
        req = ContextRequest(
            request_id="r1",
            trusted_context=base_context,
            capability=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_1",
            created_at=datetime.now(timezone.utc),
        )
        needs = classify_context_needs(req)

        assert needs.needs_project_state is True
        assert needs.needs_assets is True
        assert needs.needs_media_context is True
        assert needs.needs_preferences is True
        assert needs.needs_knowledge is False
        assert "audio" in needs.preference_domains
        assert "speech" in needs.preference_domains
        assert "visual" not in needs.preference_domains
        assert MemoryType.USER_PREFERENCE.value in needs.allowed_memory_types
        assert MemoryType.MEDIA_INTELLIGENCE.value in needs.allowed_memory_types

    def test_vision_needs(self, base_context):
        req = ContextRequest(
            request_id="r2",
            trusted_context=base_context,
            capability=CapabilityType.VISION,
            project_id="prj_1",
            created_at=datetime.now(timezone.utc),
        )
        needs = classify_context_needs(req)

        assert needs.needs_assets is True
        assert needs.needs_media_context is True
        assert "visual" in needs.preference_domains
        assert "audio" not in needs.preference_domains

    def test_planning_needs(self, base_context):
        req = ContextRequest(
            request_id="r3",
            trusted_context=base_context,
            capability=CapabilityType.PLANNING,
            project_id="prj_1",
            created_at=datetime.now(timezone.utc),
        )
        needs = classify_context_needs(req)

        assert needs.needs_project_state is True
        assert needs.needs_assets is True
        assert needs.needs_review_status is True
        assert needs.needs_decisions is True
        assert needs.needs_preferences is True
        assert needs.needs_knowledge is True
        assert needs.needs_conversation_history is True
        assert "planning" in needs.knowledge_tags
        assert "workflow" in needs.knowledge_tags

    def test_text_generation_needs(self, base_context):
        req = ContextRequest(
            request_id="r4",
            trusted_context=base_context,
            capability=CapabilityType.TEXT_GENERATION,
            project_id="prj_1",
            created_at=datetime.now(timezone.utc),
        )
        needs = classify_context_needs(req)

        assert needs.needs_project_state is True
        assert needs.needs_assets is False
        assert needs.needs_review_status is False
        assert needs.needs_decisions is True
        assert needs.needs_knowledge is True

    def test_recipe_ref_triggers_knowledge(self, base_context):
        req = ContextRequest(
            request_id="r5",
            trusted_context=base_context,
            capability=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_1",
            recipe_ref="recipe_quick_hook",
            created_at=datetime.now(timezone.utc),
        )
        needs = classify_context_needs(req)

        assert needs.needs_knowledge is True
        assert "recipe" in needs.knowledge_tags

    def test_session_id_triggers_conversation_history(self, base_context):
        req = ContextRequest(
            request_id="r6",
            trusted_context=base_context,
            capability=CapabilityType.TEXT_GENERATION,
            session_id="session_42",
            created_at=datetime.now(timezone.utc),
        )
        needs = classify_context_needs(req)

        assert needs.needs_conversation_history is True
        assert MemoryType.CONVERSATION.value in needs.allowed_memory_types

    def test_classification_is_deterministic(self, base_context):
        req = ContextRequest(
            request_id="r7",
            trusted_context=base_context,
            capability=CapabilityType.PLANNING,
            project_id="prj_1",
            recipe_ref="recipe_hook",
            session_id="sess_1",
            created_at=datetime.now(timezone.utc),
        )
        first_needs = classify_context_needs(req)

        for _ in range(50):
            assert classify_context_needs(req) == first_needs
