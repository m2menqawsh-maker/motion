"""
ai/feedback/classifier.py
=========================
Deterministic semantic classifier for CreativeFeedback events (S28-08A).

Maps unstructured qualitative critiques, liked/disliked aspects, and satisfaction ratings
into structured domain classifications (FeedbackClassification).

Guarantees:
- Distinguishes scene-local feedback from explicit general user style rules.
- Multilingual keyword & pattern matching (English and Arabic).
- AI Authority Restriction: Cannot forge EXPLICIT or mark arbitrary high confidence.
- Rejects malformed feedback payloads safely.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from ai.contracts.creative.feedback import (
    CreativeFeedback,
    FeedbackCategory,
    FeedbackClassification,
    FeedbackSentiment,
    FeedbackTargetType,
)
from ai.memory.models import TrustedTenantContext
from ai.memory.types import MemoryScope, SourceType


class MalformedFeedbackError(ValueError):
    """Raised when incoming feedback fails baseline integrity requirements."""
    pass


class FeedbackClassifier:
    """
    Analyzes creative feedback inputs to classify dimension, sentiment, target, and scope.
    """

    # General rule indicators (user asserting an enduring personal rule)
    GENERAL_RULE_PATTERNS = [
        re.compile(r"\b(?:دائم[اًا]|دايما|أنا دائم[اًا]|عندي|في كل الفيديوهات|قاعدتي|دائما)\b", re.IGNORECASE),
        re.compile(r"\b(?:لا تستخدم (?:أبدا|أبدًا)?\s*.*?\s*عندي)\b", re.IGNORECASE),
        re.compile(r"\b(?:always|never|for all my videos|in all videos|my general rule|i always|i never)\b", re.IGNORECASE),
    ]

    # Scene-specific indicators (local critique of current shot/scene)
    SCENE_TARGET_PATTERNS = [
        re.compile(r"\b(?:هذا المشهد|المشهد|اللقطة|هذه اللقطة|المشهد رقم|مشهد \d+)\b", re.IGNORECASE),
        re.compile(r"\b(?:this scene|the scene|scene \d+|this shot|the shot|this frame)\b", re.IGNORECASE),
    ]

    # Dimension pattern matchers (Arabic & English)
    MOTION_PATTERNS = [
        (re.compile(r"(?:حركت?ه?\s+كثيرة|الحركات\s+الكثيرة|كثير\s+الحركة|حركت?ه?\s+سريعة|الحركات\s+السريعة|حركة\s+مبالغ\s+فيها|too much motion|excessive motion|too fast movement)", re.IGNORECASE), "motion_intensity", "low", FeedbackCategory.MOTION, FeedbackSentiment.NEGATIVE),
        (re.compile(r"(?:حركة\s+بطيئة|حركة\s+قليلة|حركة\s+هادئة|slow motion|subtle motion|gentle movement|calm motion)", re.IGNORECASE), "motion_intensity", "low", FeedbackCategory.MOTION, FeedbackSentiment.POSITIVE),
        (re.compile(r"(?:حركة\s+ديناميكية|حركة\s+قوية|dynamic motion|energetic motion)", re.IGNORECASE), "motion_intensity", "high", FeedbackCategory.MOTION, FeedbackSentiment.POSITIVE),
        (re.compile(r"(?:حرك[ةات]|motion)", re.IGNORECASE), "motion_intensity", "standard", FeedbackCategory.MOTION, FeedbackSentiment.NEUTRAL),
    ]

    PACING_PATTERNS = [
        # Explicit positive preference statements
        (re.compile(r"(?:اعتمد (?:.*?)(?:ريتم|إيقاع) سريع|(?:ريتم|إيقاع) سريع|fast pace|rapid pace)", re.IGNORECASE), "pacing", "fast", FeedbackCategory.PACING, FeedbackSentiment.POSITIVE),
        (re.compile(r"(?:اعتمد (?:.*?)(?:ريتم|إيقاع) هادئ|(?:ريتم|إيقاع) هادئ|calm pacing|deliberate pace)", re.IGNORECASE), "pacing", "calm", FeedbackCategory.PACING, FeedbackSentiment.POSITIVE),
        (re.compile(r"(?:اعتمد (?:.*?)(?:ريتم|إيقاع) بطيء|(?:ريتم|إيقاع) بطيء|slow pace)", re.IGNORECASE), "pacing", "slow", FeedbackCategory.PACING, FeedbackSentiment.POSITIVE),
        # Complaints desiring the opposite
        (re.compile(r"(?:سريع جدا|too fast|pacing too fast|pacing_too_fast|hurried|rushed)", re.IGNORECASE), "pacing", "slow", FeedbackCategory.PACING, FeedbackSentiment.NEGATIVE),
        (re.compile(r"(?:بطيء جدا|too slow|pacing too slow|draggy|sluggish)", re.IGNORECASE), "pacing", "fast", FeedbackCategory.PACING, FeedbackSentiment.NEGATIVE),
    ]

    MUSIC_PATTERNS = [
        (re.compile(r"(?:موسيقى إلكترونية|لا تستخدم موسيقى إلكترونية|dislike electronic music|no electronic music)", re.IGNORECASE), "disliked_patterns", "electronic_music", FeedbackCategory.MUSIC, FeedbackSentiment.NEGATIVE),
        (re.compile(r"(?:بدون موسيقى|لا تستخدم موسيقى|أوقف الموسيقى|no music|without music|silent music)", re.IGNORECASE), "music_tendencies", "none", FeedbackCategory.MUSIC, FeedbackSentiment.NEGATIVE),
        (re.compile(r"(?:لا أحب هذا النوع من الموسيقى|نوع الموسيقى سيء|bad music|dislike this music)", re.IGNORECASE), "music_tendencies", "avoid_current_genre", FeedbackCategory.MUSIC, FeedbackSentiment.NEGATIVE),
        (re.compile(r"(?:موسيقى هادئة|موسيقى خلفية|ambient music|calm music)", re.IGNORECASE), "music_tendencies", "ambient", FeedbackCategory.MUSIC, FeedbackSentiment.POSITIVE),
    ]

    CAPTION_PATTERNS = [
        (re.compile(r"(?:كابتشن أصغر|خط أصغر|صغر الكابتشن|smaller captions|smaller font|captions too large|compact captions)", re.IGNORECASE), "caption_style", "compact", FeedbackCategory.CAPTION, FeedbackSentiment.CONSTRUCTIVE),
        (re.compile(r"(?:كابتشن أكبر|خط أكبر|كبر الكابتشن|larger captions|larger font|prominent captions)", re.IGNORECASE), "caption_style", "prominent", FeedbackCategory.CAPTION, FeedbackSentiment.CONSTRUCTIVE),
        (re.compile(r"(?:كابتشن|ترجمة|نصوص|subtitles|captions)", re.IGNORECASE), "caption_style", "standard", FeedbackCategory.CAPTION, FeedbackSentiment.NEUTRAL),
    ]

    VISUAL_PATTERNS = [
        (re.compile(r"(?:زحمة بصرية|كثير عناصر|too busy|too complex|visual clutter)", re.IGNORECASE), "visual_complexity", "minimal", FeedbackCategory.VISUAL, FeedbackSentiment.NEGATIVE),
        (re.compile(r"(?:ألوان داكنة|دارك مود|dark mode|dark colors)", re.IGNORECASE), "visual_complexity", "dark_mode", FeedbackCategory.VISUAL, FeedbackSentiment.POSITIVE),
        (re.compile(r"(?:ألوان زاهية|vibrant colors)", re.IGNORECASE), "visual_complexity", "vibrant", FeedbackCategory.VISUAL, FeedbackSentiment.POSITIVE),
    ]

    @classmethod
    def classify(cls, context: TrustedTenantContext, feedback: CreativeFeedback) -> FeedbackClassification:
        """
        Classifies an authenticated CreativeFeedback event into structured domain representation.
        """
        if not feedback or not feedback.feedback_id or not feedback.feedback_id.strip():
            raise MalformedFeedbackError("Feedback must have a non-empty feedback_id.")
        if not feedback.project_id or not feedback.project_id.strip():
            raise MalformedFeedbackError("Feedback must have a non-empty project_id.")

        text_to_analyze = (feedback.critique_text or "").strip()
        aspects_disliked = " ".join(feedback.disliked_aspects)
        aspects_liked = " ".join(feedback.liked_aspects)
        full_text = f"{text_to_analyze} {aspects_disliked} {aspects_liked}".strip()

        if not full_text and feedback.user_rating is None:
            raise MalformedFeedbackError("Feedback contains neither critique text, aspects, nor rating.")

        # 1. Determine Target Type & Scope
        is_general_rule = False
        target_type = feedback.target_type or FeedbackTargetType.PROJECT
        target_ref = feedback.target_reference

        for gen_pat in cls.GENERAL_RULE_PATTERNS:
            if gen_pat.search(full_text):
                is_general_rule = True
                target_type = FeedbackTargetType.GENERAL_STYLE
                break

        if not is_general_rule:
            for sc_pat in cls.SCENE_TARGET_PATTERNS:
                if sc_pat.search(full_text):
                    target_type = FeedbackTargetType.SCENE
                    if not target_ref and feedback.plan_id:
                        # Extract scene reference if mentioned
                        match = re.search(r"(?:scene|مشهد)\s*(\d+|_\w+)", full_text, re.IGNORECASE)
                        if match:
                            target_ref = f"scene_{match.group(1)}"
                        else:
                            target_ref = "scene_current"
                    break

        # 2. Extract Category, Dimension, Proposed Value, and Sentiment
        category = FeedbackCategory.GENERAL
        dimension: Optional[str] = None
        proposed_value: Optional[str] = None
        sentiment = FeedbackSentiment.NEUTRAL

        # Check domain patterns in order of specificity
        found_match = False
        for pattern_list in [cls.MOTION_PATTERNS, cls.PACING_PATTERNS, cls.MUSIC_PATTERNS, cls.CAPTION_PATTERNS, cls.VISUAL_PATTERNS]:
            for pattern, dim, val, cat, sent in pattern_list:
                if pattern.search(full_text):
                    dimension = dim
                    proposed_value = val
                    category = cat
                    sentiment = sent
                    found_match = True
                    break
            if found_match:
                break

        # If not matched by regex, infer from rating or general praise
        if not found_match:
            if feedback.user_rating is not None:
                if feedback.user_rating >= 4:
                    sentiment = FeedbackSentiment.POSITIVE
                elif feedback.user_rating <= 2:
                    sentiment = FeedbackSentiment.NEGATIVE
                else:
                    sentiment = FeedbackSentiment.NEUTRAL
            elif "ممتاز" in full_text or "great" in full_text or "excellent" in full_text or "رائع" in full_text:
                sentiment = FeedbackSentiment.POSITIVE
            elif "سيء" in full_text or "bad" in full_text or "horrible" in full_text:
                sentiment = FeedbackSentiment.NEGATIVE

        # 3. Domain-Controlled Scope & Confidence Allocation
        # (AI Authority Guard: Never assign confidence = 1.0; enforce epistemic separation)
        scope: MemoryScope
        confidence: float
        source_type: SourceType

        if is_general_rule:
            # User explicitly declared a global or enduring rule
            scope = MemoryScope.USER
            confidence = 0.9  # Canonical high confidence for explicit statements
            source_type = SourceType.USER_STATEMENT
        elif target_type == FeedbackTargetType.SCENE:
            # Local scene complaint: bound to project, low confidence inference
            scope = MemoryScope.PROJECT
            confidence = 0.4  # Canonical low confidence for weak single inference
            source_type = SourceType.AI_INFERENCE
        else:
            # Project-level critique without explicit general phrasing
            scope = MemoryScope.PROJECT
            confidence = 0.5  # Medium-low confidence
            source_type = SourceType.AI_INFERENCE

        now = datetime.now(timezone.utc)

        return FeedbackClassification(
            classification_id=f"cls_{uuid.uuid4().hex[:12]}",
            feedback_id=feedback.feedback_id,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            project_id=feedback.project_id if scope == MemoryScope.PROJECT else None,
            target_type=target_type,
            target_reference=target_ref,
            category=category,
            sentiment=sentiment,
            preference_dimension=dimension,
            proposed_value=proposed_value,
            scope=scope,
            confidence=confidence,
            source=source_type,
            is_explicit_general_rule=is_general_rule,
            created_at=now,
        )
