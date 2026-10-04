"""
tests/ai/feedback/test_feedback_tenant_isolation.py
===================================================
Multi-tenant and User Isolation Security Invariants (S28-08A Section 19).

Invariants:
1. User A cannot read or query User B's style profile.
2. Workspace A cannot mutate Workspace B feedback (fails closed with TenantAuthorizationError).
3. Cross-user feedback submission without authorization fails closed.
4. Project-scoped feedback cannot escape project boundary or actor access.
5. Cross-tenant profile lookup fails closed.
6. Project-scoped feedback preferences do not leak across distinct projects.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ai.contracts.creative.feedback import (
    CreativeFeedback,
    FeedbackTargetType,
)
from ai.feedback.service import CreativeFeedbackService
from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
from ai.memory.models import MemoryFilter, TrustedTenantContext
from ai.memory.policy import MemoryPolicy
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.service import MemoryService, TenantAuthorizationError
from ai.memory.types import EpistemicStatus, MemoryScope, MemoryType
from ai.style.resolver import UserStyleResolver


@pytest.fixture
def memory_env():
    repo = InMemoryMemoryRepository()
    policy = MemoryPolicy()
    embedder = DeterministicFakeEmbeddingProvider(dimension=64)
    service = MemoryService(repository=repo, embedding_provider=embedder, policy=policy)
    feedback_service = CreativeFeedbackService(memory_service=service)
    return service, feedback_service


@pytest.fixture
def ctx_tenant_a_user_1():
    return TrustedTenantContext(
        workspace_id="ws_alpha",
        user_id="usr_alice",
        accessible_projects={"proj_alpha_1", "proj_alpha_2"},
        accessible_users={"usr_alice"},
    )


@pytest.fixture
def ctx_tenant_a_user_2():
    return TrustedTenantContext(
        workspace_id="ws_alpha",
        user_id="usr_bob",
        accessible_projects={"proj_alpha_1"},
        accessible_users={"usr_bob"},
    )


@pytest.fixture
def ctx_tenant_b_user_1():
    return TrustedTenantContext(
        workspace_id="ws_beta",
        user_id="usr_charlie",
        accessible_projects={"proj_beta_1"},
        accessible_users={"usr_charlie"},
    )


class TestFeedbackTenantIsolation:
    """Rigorous verification of Section 19 Multi-Tenant & User Isolation."""

    def test_user_a_cannot_read_user_b_profile(
        self,
        memory_env,
        ctx_tenant_a_user_1,
        ctx_tenant_a_user_2,
    ):
        """User A and User B within the same workspace have strictly isolated personal preferences."""
        service, _ = memory_env

        # Store explicit preference for Alice (User 1)
        service.store_memory(
            context=ctx_tenant_a_user_1,
            content="User preference for pacing: fast",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            user_id="usr_alice",
            structured_payload={"dimension": "pacing", "value": "fast"},
            metadata={"dimension": "pacing", "value": "fast"},
            epistemic_status=EpistemicStatus.EXPLICIT,
            confidence=0.9,
        )

        # Alice loads profile -> sees fast pacing
        alice_profile = UserStyleResolver.load_profile(ctx_tenant_a_user_1, service)
        assert alice_profile.pacing_preference == "fast"
        assert "pacing" in alice_profile.provenance_by_dimension

        # Bob (User 2) loads profile -> MUST NOT see Alice's pacing preference
        bob_profile = UserStyleResolver.load_profile(ctx_tenant_a_user_2, service)
        assert bob_profile.pacing_preference is None
        assert "pacing" not in bob_profile.provenance_by_dimension

    def test_workspace_a_cannot_mutate_workspace_b_feedback(
        self,
        memory_env,
        ctx_tenant_a_user_1,
    ):
        """A caller authenticated in Workspace Alpha cannot submit or mutate feedback for Workspace Beta."""
        _, feedback_service = memory_env

        now = datetime.now(timezone.utc)
        malicious_feedback = CreativeFeedback(
            feedback_id="fb_tamper_001",
            project_id="proj_beta_1",
            target_type=FeedbackTargetType.GENERAL_STYLE,
            critique_text="اعتمد دائمًا ريتم هادئ",
            workspace_id="ws_beta",
            user_id="usr_charlie",
            created_at=now,
        )

        with pytest.raises(TenantAuthorizationError) as exc_info:
            feedback_service.process_feedback(ctx_tenant_a_user_1, malicious_feedback)

        assert "Cross-tenant feedback rejected" in str(exc_info.value)
        assert "ws_alpha" in str(exc_info.value)
        assert "ws_beta" in str(exc_info.value)

    def test_actor_cannot_mutate_feedback_for_unauthorized_user(
        self,
        memory_env,
        ctx_tenant_a_user_1,
    ):
        """An actor in Workspace Alpha cannot forge feedback on behalf of another user they cannot access."""
        _, feedback_service = memory_env
        now = datetime.now(timezone.utc)

        # Alice tries to submit feedback on behalf of Bob
        cross_user_feedback = CreativeFeedback(
            feedback_id="fb_cross_user_001",
            project_id="proj_alpha_1",
            target_type=FeedbackTargetType.GENERAL_STYLE,
            critique_text="اعتمد دائمًا ريتم سريع",
            workspace_id="ws_alpha",
            user_id="usr_bob",  # Alice does not have access to Bob
            created_at=now,
        )

        with pytest.raises(TenantAuthorizationError) as exc_info:
            feedback_service.process_feedback(ctx_tenant_a_user_1, cross_user_feedback)

        assert "Cross-user feedback rejected" in str(exc_info.value)
        assert "usr_alice" in str(exc_info.value)
        assert "usr_bob" in str(exc_info.value)

    def test_project_scoped_feedback_cannot_escape_project_boundary(
        self,
        memory_env,
        ctx_tenant_a_user_2,
    ):
        """Bob cannot submit feedback for a project he does not have access to."""
        _, feedback_service = memory_env
        now = datetime.now(timezone.utc)

        # Bob only has access to proj_alpha_1, attempts to submit feedback on proj_alpha_2
        unauthorized_proj_feedback = CreativeFeedback(
            feedback_id="fb_unauth_proj_001",
            project_id="proj_alpha_2",  # Forbidden for Bob
            target_type=FeedbackTargetType.SCENE,
            critique_text="هذا المشهد حركته كثيرة",
            workspace_id="ws_alpha",
            user_id="usr_bob",
            created_at=now,
        )

        with pytest.raises(TenantAuthorizationError) as exc_info:
            feedback_service.process_feedback(ctx_tenant_a_user_2, unauthorized_proj_feedback)

        assert "does not have access to project 'proj_alpha_2'" in str(exc_info.value)

    def test_cross_tenant_profile_lookup_fails_closed(
        self,
        memory_env,
        ctx_tenant_b_user_1,
    ):
        """Cross-tenant direct memory query or profile loading fails closed without leakage."""
        service, _ = memory_env

        # Attempt to forge a memory query for ws_alpha using Charlie's token (ws_beta)
        mismatched_filter = MemoryFilter(
            workspace_id="ws_alpha",  # Attempting to read ws_alpha
            memory_types=[MemoryType.USER_PREFERENCE],
        )

        with pytest.raises(TenantAuthorizationError) as exc_info:
            service.query_structured(ctx_tenant_b_user_1, mismatched_filter)

        assert "Cross-tenant query rejected" in str(exc_info.value)
        assert "ws_beta" in str(exc_info.value)
        assert "ws_alpha" in str(exc_info.value)

    def test_cross_workspace_isolation_end_to_end(
        self,
        memory_env,
        ctx_tenant_a_user_1,
        ctx_tenant_b_user_1,
    ):
        """
        Full lifecycle: Alice in ws_alpha learns a style preference.
        Charlie in ws_beta learns an opposite style preference.
        Neither profile affects the other.
        """
        service, feedback_service = memory_env
        now = datetime.now(timezone.utc)

        # Alice: "اعتمد دائمًا ريتم سريع" (always adopt fast pacing)
        feedback_a = CreativeFeedback(
            feedback_id="fb_a_001",
            project_id="proj_alpha_1",
            target_type=FeedbackTargetType.GENERAL_STYLE,
            critique_text="اعتمد دائمًا ريتم سريع",
            workspace_id="ws_alpha",
            user_id="usr_alice",
            created_at=now,
        )
        res_a = feedback_service.process_feedback(ctx_tenant_a_user_1, feedback_a)
        assert res_a.persisted is True

        # Charlie: "اعتمد دائمًا ريتم بطيء" (always adopt slow pacing)
        feedback_b = CreativeFeedback(
            feedback_id="fb_b_001",
            project_id="proj_beta_1",
            target_type=FeedbackTargetType.GENERAL_STYLE,
            critique_text="اعتمد دائمًا ريتم بطيء",
            workspace_id="ws_beta",
            user_id="usr_charlie",
            created_at=now,
        )
        res_b = feedback_service.process_feedback(ctx_tenant_b_user_1, feedback_b)
        assert res_b.persisted is True

        # Verify Alice's profile
        alice_profile = UserStyleResolver.load_profile(ctx_tenant_a_user_1, service)
        assert alice_profile.pacing_preference == "fast"
        assert alice_profile.workspace_id == "ws_alpha"

        # Verify Charlie's profile
        charlie_profile = UserStyleResolver.load_profile(ctx_tenant_b_user_1, service)
        assert charlie_profile.pacing_preference == "slow"
        assert charlie_profile.workspace_id == "ws_beta"
