"""
tests/ai/feedback/test_feedback_classification.py
=================================================
Semantic and scope classification tests for CreativeFeedback (S28-08A Section 8, 9, 10, 18).

Tests:
- Multilingual feedback analysis (Arabic & English).
- Local scene-specific critique vs explicit general user style rule.
- Dimension mapping: pacing, motion, music, caption, visual.
- Strict rejection of malformed feedback payloads.
- AI Authority boundaries: domain-assigned confidence and scope.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ai.contracts.creative.feedback import (
    CreativeFeedback,
    FeedbackCategory,
    FeedbackSentiment,
    FeedbackTargetType,
)
from ai.feedback.classifier import FeedbackClassifier, MalformedFeedbackError
from ai.memory.models import TrustedTenantContext
from ai.memory.types import MemoryScope, SourceType


@pytest.fixture
def auth_context():
    return TrustedTenantContext(workspace_id="ws_fb_test", user_id="usr_reviewer")


class TestFeedbackClassification:

    def test_classify_scene_praise(self, auth_context):
        """'المشهد ممتاز' is classified as scene-level positive feedback."""
        now = datetime.now(timezone.utc)
        feedback = CreativeFeedback(
            feedback_id="fb_01",
            project_id="prj_01",
            critique_text="المشهد ممتاز",
            target_type=FeedbackTargetType.SCENE,
            target_reference="scene_001",
            created_at=now,
        )

        cls_res = FeedbackClassifier.classify(auth_context, feedback)

        assert cls_res.sentiment == FeedbackSentiment.POSITIVE
        assert cls_res.target_type == FeedbackTargetType.SCENE
        assert cls_res.target_reference == "scene_001"
        assert cls_res.is_explicit_general_rule is False
        assert cls_res.scope == MemoryScope.PROJECT
        assert cls_res.confidence == 0.4  # Low confidence for local critique

    def test_classify_scene_local_motion_complaint(self, auth_context):
        """'هذا المشهد حركته كثيرة' is classified as scene-specific, not global rule."""
        now = datetime.now(timezone.utc)
        feedback = CreativeFeedback(
            feedback_id="fb_02",
            project_id="prj_01",
            critique_text="هذا المشهد حركته كثيرة",
            created_at=now,
        )

        cls_res = FeedbackClassifier.classify(auth_context, feedback)

        assert cls_res.category == FeedbackCategory.MOTION
        assert cls_res.preference_dimension == "motion_intensity"
        assert cls_res.proposed_value == "low"
        assert cls_res.sentiment == FeedbackSentiment.NEGATIVE
        assert cls_res.target_type == FeedbackTargetType.SCENE
        assert cls_res.is_explicit_general_rule is False
        assert cls_res.scope == MemoryScope.PROJECT
        assert cls_res.confidence == 0.4
        assert cls_res.source == SourceType.AI_INFERENCE

    def test_classify_dislike_music_genre(self, auth_context):
        """'لا أحب هذا النوع من الموسيقى' maps to music dimension."""
        now = datetime.now(timezone.utc)
        feedback = CreativeFeedback(
            feedback_id="fb_03",
            project_id="prj_01",
            critique_text="لا أحب هذا النوع من الموسيقى",
            created_at=now,
        )

        cls_res = FeedbackClassifier.classify(auth_context, feedback)

        assert cls_res.category == FeedbackCategory.MUSIC
        assert cls_res.preference_dimension == "music_tendencies"
        assert cls_res.sentiment == FeedbackSentiment.NEGATIVE

    def test_classify_caption_size_adjustment(self, auth_context):
        """'خلي الكابتشن أصغر' maps to caption_style compact."""
        now = datetime.now(timezone.utc)
        feedback = CreativeFeedback(
            feedback_id="fb_04",
            project_id="prj_01",
            critique_text="خلي الكابتشن أصغر",
            created_at=now,
        )

        cls_res = FeedbackClassifier.classify(auth_context, feedback)

        assert cls_res.category == FeedbackCategory.CAPTION
        assert cls_res.preference_dimension == "caption_style"
        assert cls_res.proposed_value == "compact"
        assert cls_res.sentiment == FeedbackSentiment.CONSTRUCTIVE

    def test_classify_explicit_general_rule(self, auth_context):
        """'أنا دائمًا ما بحب الحركات السريعة' is recognized as an explicit general user rule."""
        now = datetime.now(timezone.utc)
        feedback = CreativeFeedback(
            feedback_id="fb_05",
            project_id="prj_01",
            critique_text="أنا دائمًا ما بحب الحركات السريعة",
            created_at=now,
        )

        cls_res = FeedbackClassifier.classify(auth_context, feedback)

        assert cls_res.is_explicit_general_rule is True
        assert cls_res.target_type == FeedbackTargetType.GENERAL_STYLE
        assert cls_res.scope == MemoryScope.USER
        assert cls_res.confidence == 0.9  # High confidence for explicit statement
        assert cls_res.source == SourceType.USER_STATEMENT
        assert cls_res.category == FeedbackCategory.MOTION
        assert cls_res.preference_dimension in ("motion_intensity", "pacing")

    def test_classify_explicit_forbidden_pattern(self, auth_context):
        """'لا تستخدم موسيقى إلكترونية عندي' maps to disliked pattern with explicit provenance."""
        now = datetime.now(timezone.utc)
        feedback = CreativeFeedback(
            feedback_id="fb_06",
            project_id="prj_01",
            critique_text="لا تستخدم موسيقى إلكترونية عندي",
            created_at=now,
        )

        cls_res = FeedbackClassifier.classify(auth_context, feedback)

        assert cls_res.is_explicit_general_rule is True
        assert cls_res.preference_dimension == "disliked_patterns"
        assert cls_res.proposed_value == "electronic_music"
        assert cls_res.scope == MemoryScope.USER
        assert cls_res.confidence == 0.9
        assert cls_res.source == SourceType.USER_STATEMENT

    def test_classify_english_general_rule(self, auth_context):
        """English explicit general rule 'Always use dark mode for all my videos'."""
        now = datetime.now(timezone.utc)
        feedback = CreativeFeedback(
            feedback_id="fb_07",
            project_id="prj_01",
            critique_text="Always use dark mode for all my videos",
            created_at=now,
        )

        cls_res = FeedbackClassifier.classify(auth_context, feedback)

        assert cls_res.is_explicit_general_rule is True
        assert cls_res.scope == MemoryScope.USER
        assert cls_res.confidence == 0.9
        assert cls_res.proposed_value == "dark_mode"

    def test_reject_malformed_feedback(self, auth_context):
        """Rejects empty feedback_id, empty project_id, or empty content."""
        now = datetime.now(timezone.utc)

        # Missing feedback_id
        with pytest.raises(MalformedFeedbackError):
            FeedbackClassifier.classify(
                auth_context,
                CreativeFeedback(
                    feedback_id="",
                    project_id="prj_01",
                    critique_text="Some text",
                    created_at=now,
                ),
            )

        # Missing project_id
        with pytest.raises(MalformedFeedbackError):
            FeedbackClassifier.classify(
                auth_context,
                CreativeFeedback(
                    feedback_id="fb_01",
                    project_id="",
                    critique_text="Some text",
                    created_at=now,
                ),
            )

        # Empty content without rating
        with pytest.raises(MalformedFeedbackError):
            FeedbackClassifier.classify(
                auth_context,
                CreativeFeedback(
                    feedback_id="fb_01",
                    project_id="prj_01",
                    critique_text=None,
                    user_rating=None,
                    liked_aspects=[],
                    disliked_aspects=[],
                    created_at=now,
                ),
            )
