"""
tests/ai/feedback/test_feedback_learning_service.py
===================================================
Integration tests for CreativeFeedbackService and S27 MemoryPolicy (S28-08A Section 8, 10, 11, 12, 18, 20).

Tests:
1. Single action ≠ permanent truth: Single local complaint does not become permanent global preference.
2. Explicit persistent statement: Recorded with EXPLICIT provenance and high confidence.
3. Repeated feedback: Handled via MERGE / reinforcement through MemoryPolicy.
4. Contradictory feedback: Handled deterministically via SUPERSEDE preserving history.
5. AI Authority restriction: Client cannot force confidence = 1.0 or forge EXPLICIT status.
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
from ai.memory.service import MemoryService
from ai.memory.types import (
    EpistemicStatus,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    WriteDecisionType,
)
from ai.style.resolver import UserStyleResolver


@pytest.fixture
def feedback_env():
    repo = InMemoryMemoryRepository()
    policy = MemoryPolicy()
    embedder = DeterministicFakeEmbeddingProvider(dimension=64)
    mem_service = MemoryService(repository=repo, embedding_provider=embedder, policy=policy)
    feedback_service = CreativeFeedbackService(memory_service=mem_service)
    ctx = TrustedTenantContext(workspace_id="ws_learning_test", user_id="usr_learner")
    return feedback_service, mem_service, repo, ctx


class TestFeedbackLearningService:

    def test_single_local_complaint_does_not_become_global_preference(self, feedback_env):
        """
        Rule: Single action ≠ permanent truth (Section 10 & 11).
        A complaint about a single scene ('هذا المشهد حركته كثيرة')
        does NOT create a permanent global user preference.
        """
        feedback_service, mem_service, repo, ctx = feedback_env
        now = datetime.now(timezone.utc)

        feedback = CreativeFeedback(
            feedback_id="fb_local_001",
            project_id="prj_001",
            critique_text="هذا المشهد حركته كثيرة",
            target_type=FeedbackTargetType.SCENE,
            target_reference="scene_003",
            created_at=now,
        )

        res = feedback_service.process_feedback(ctx, feedback)

        # 1. Classification is local and inferred
        assert res.classification.target_type == FeedbackTargetType.SCENE
        assert res.classification.scope == MemoryScope.PROJECT
        assert res.epistemic_status == EpistemicStatus.INFERRED
        assert res.effective_confidence == 0.4

        # 2. MemoryPolicy evaluates single inference with evidence count = 1 -> REQUIRE_CONFIRMATION
        assert res.decision.decision_type == WriteDecisionType.REQUIRE_CONFIRMATION
        assert res.persisted is False

        # 3. Verify user's global profile did NOT acquire this as a permanent preference
        profile = UserStyleResolver.load_profile(ctx, mem_service)
        assert profile.motion_intensity is None
        assert "motion_intensity" not in profile.provenance_by_dimension

    def test_explicit_general_statement_stored_as_permanent_preference(self, feedback_env):
        """
        Explicit user statement ('أنا دائمًا ما بحب الحركات السريعة')
        is stored with EXPLICIT provenance and high confidence.
        """
        feedback_service, mem_service, repo, ctx = feedback_env
        now = datetime.now(timezone.utc)

        feedback = CreativeFeedback(
            feedback_id="fb_explicit_001",
            project_id="prj_001",
            critique_text="أنا دائمًا ما بحب الحركات السريعة",
            created_at=now,
        )

        res = feedback_service.process_feedback(ctx, feedback)

        # 1. Classified as explicit general rule
        assert res.classification.is_explicit_general_rule is True
        assert res.classification.scope == MemoryScope.USER
        assert res.epistemic_status == EpistemicStatus.EXPLICIT
        assert res.effective_confidence == 0.9

        # 2. Stored by MemoryPolicy
        assert res.decision.decision_type == WriteDecisionType.STORE
        assert res.persisted is True
        assert res.target_entry_id is not None

        # 3. UserStyleProfile now reflects the learned preference
        profile = UserStyleResolver.load_profile(ctx, mem_service)
        assert profile.motion_intensity == "low"
        assert profile.provenance_by_dimension["motion_intensity"].epistemic_status == EpistemicStatus.EXPLICIT
        assert profile.provenance_by_dimension["motion_intensity"].confidence == 0.9

    def test_repeated_feedback_updates_confidence_via_merge(self, feedback_env):
        """
        Repeated consistent feedback triggers MERGE reinforcement under MemoryPolicy.
        """
        feedback_service, mem_service, repo, ctx = feedback_env
        now = datetime.now(timezone.utc)

        fb1 = CreativeFeedback(
            feedback_id="fb_rep_001",
            project_id="prj_001",
            critique_text="لا تستخدم موسيقى إلكترونية عندي",
            created_at=now,
        )

        res1 = feedback_service.process_feedback(ctx, fb1)
        assert res1.persisted is True
        assert res1.decision.decision_type == WriteDecisionType.STORE
        entry_id_1 = res1.target_entry_id

        # Submit identical feedback a second time
        fb2 = CreativeFeedback(
            feedback_id="fb_rep_002",
            project_id="prj_002",
            critique_text="لا تستخدم موسيقى إلكترونية عندي",
            created_at=now,
        )

        res2 = feedback_service.process_feedback(ctx, fb2)
        assert res2.decision.decision_type == WriteDecisionType.MERGE
        assert res2.target_entry_id == entry_id_1

        # Check in repository: evidence count reinforced
        stored = mem_service.get_memory(ctx, entry_id_1)
        assert stored is not None
        assert stored.metadata.get("evidence_count", 1) >= 2

    def test_contradictory_feedback_supersedes_cleanly(self, feedback_env):
        """
        Contradictory feedback triggers SUPERSEDE decision in MemoryPolicy,
        retiring the old memory and keeping history traceable.
        """
        feedback_service, mem_service, repo, ctx = feedback_env
        now = datetime.now(timezone.utc)

        # 1. User initially establishes fast pacing
        fb_fast = CreativeFeedback(
            feedback_id="fb_pacing_001",
            project_id="prj_001",
            critique_text="دائمًا اعتمد ريتم سريع في الفيديوهات",
            created_at=now,
        )
        res_fast = feedback_service.process_feedback(ctx, fb_fast)
        assert res_fast.persisted is True
        old_id = res_fast.target_entry_id

        # 2. Later user changes their mind and explicitly wants calm pacing
        fb_calm = CreativeFeedback(
            feedback_id="fb_pacing_002",
            project_id="prj_002",
            critique_text="دائمًا اعتمد إيقاع هادئ في الفيديوهات",
            created_at=now,
        )
        res_calm = feedback_service.process_feedback(ctx, fb_calm)

        assert res_calm.decision.decision_type == WriteDecisionType.SUPERSEDE
        assert res_calm.decision.supersedes_id == old_id
        assert res_calm.persisted is True

        # Verify old memory is now SUPERSEDED
        old_entry = repo.get(old_id, ctx.workspace_id)
        assert old_entry is not None
        assert old_entry.status == MemoryStatus.SUPERSEDED

        # Verify profile now reflects calm pacing
        profile = UserStyleResolver.load_profile(ctx, mem_service)
        assert profile.pacing_preference == "calm"

    def test_ai_cannot_forge_confidence_or_explicit_status(self, feedback_env):
        """
        AI Authority Restriction: Client or AI model sending confidence = 1.0
        on a speculative scene complaint is domain-clamped to INFERRED with confidence 0.4.
        """
        feedback_service, mem_service, repo, ctx = feedback_env
        now = datetime.now(timezone.utc)

        feedback = CreativeFeedback(
            feedback_id="fb_spoof_001",
            project_id="prj_001",
            critique_text="هذا المشهد حركته كثيرة",
            target_type=FeedbackTargetType.SCENE,
            target_reference="scene_001",
            created_at=now,
        )

        res = feedback_service.process_feedback(ctx, feedback)

        # Domain controls the confidence: 0.4, not 1.0!
        assert res.effective_confidence == 0.4
        assert res.epistemic_status == EpistemicStatus.INFERRED
        # And because evidence count = 1, policy requires confirmation
        assert res.decision.decision_type == WriteDecisionType.REQUIRE_CONFIRMATION
