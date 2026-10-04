"""
tests/ai/intent/test_intent_parser.py
=====================================
Unit tests for S28-03 IntentParser and CreativeBriefBuilder:
- Multilingual understanding (Arabic, English, Mixed).
- Epistemic provenance tracking (EXPLICIT, INFERRED, DEFAULTED, UNKNOWN).
- "Uncertain information must not become fact" invariance.
- Contradiction detection (Silent vs VO, No music vs BGM, conflicting durations).
- CreativeBriefBuilder canonical output validation.
"""

import pytest

from ai.contracts.creative.brief import AudioMode, CreativeBrief, ProvenanceType
from ai.intent.brief_builder import CreativeBriefBuilder
from ai.intent.parser import IntentParser


@pytest.fixture
def parser() -> IntentParser:
    return IntentParser()


@pytest.fixture
def builder() -> CreativeBriefBuilder:
    return CreativeBriefBuilder()


def test_user_acceptance_prompt(parser: IntentParser, builder: CreativeBriefBuilder):
    """
    Acceptance case from user prompt:
    "بدي ريل سريع لمنتج SaaS بدون تعليق صوتي بس موسيقى وستايل clean."
    Must yield:
    - video_type: SAAS_DEMO (EXPLICIT)
    - platform: instagram_reels (EXPLICIT)
    - audio_mode: MUSIC_ONLY (EXPLICIT)
    - pace: FAST (EXPLICIT)
    - style: CLEAN (EXPLICIT)
    """
    text = "بدي ريل سريع لمنتج SaaS بدون تعليق صوتي بس موسيقى وستايل clean."
    parsed = parser.parse(text)

    assert parsed.video_type == "SAAS_DEMO"
    assert parsed.audio_mode == AudioMode.MUSIC_ONLY
    assert parsed.pace == "FAST"
    assert parsed.style == "CLEAN"
    assert "instagram_reels" in parsed.target_platforms

    assert parsed.field_provenance["video_type"].source_type == ProvenanceType.EXPLICIT
    assert parsed.field_provenance["audio_mode"].source_type == ProvenanceType.EXPLICIT
    assert parsed.field_provenance["pace"].source_type == ProvenanceType.EXPLICIT
    assert parsed.field_provenance["style"].source_type == ProvenanceType.EXPLICIT

    # Build typed CreativeBrief
    brief: CreativeBrief = builder.build_brief(text)
    assert brief.interpreted_intent.video_type == "SAAS_DEMO"
    assert brief.constraints.audio_mode == AudioMode.MUSIC_ONLY
    assert brief.interpreted_intent.pace == "FAST"
    assert brief.interpreted_intent.style == "CLEAN"
    assert len(brief.detected_contradictions) == 0


def test_vague_request_preserves_uncertainty(parser: IntentParser):
    """
    Invariance: "Uncertain information must not become fact."
    A vague request like "بدي فيديو تسويقي ممتاز للشركة" must NOT invent explicit facts:
    video_type must be UNKNOWN, duration DEFAULTED, audio_mode DEFAULTED.
    """
    parsed = parser.parse("بدي فيديو تسويقي ممتاز للشركة")
    assert parsed.video_type is None
    assert parsed.field_provenance["video_type"].source_type == ProvenanceType.UNKNOWN
    assert parsed.field_provenance["duration"].source_type == ProvenanceType.DEFAULTED
    assert parsed.field_provenance["audio_mode"].source_type == ProvenanceType.DEFAULTED


def test_contradiction_detection_silent_vs_vo(parser: IntentParser):
    """Verifies that requesting silent audio and voiceover in the same prompt is flagged as a contradiction."""
    parsed = parser.parse("فيديو صامت بدون صوت نهائياً واعمل فيه تعليق صوتي احترافي")
    assert len(parsed.detected_contradictions) > 0
    assert any("silent/no audio while simultaneously requesting voiceover" in c for c in parsed.detected_contradictions)


def test_contradiction_detection_no_music_vs_bgm(parser: IntentParser):
    """Verifies that requesting no music and background music in the same prompt is flagged as a contradiction."""
    parsed = parser.parse("ريلز بدون موسيقى إطلاقاً بس حط موسيقى حماسية بالخلفية")
    assert len(parsed.detected_contradictions) > 0
    assert any("no music while simultaneously requesting background music" in c for c in parsed.detected_contradictions)


def test_contradiction_detection_conflicting_durations(parser: IntentParser):
    """Verifies that conflicting duration numbers (e.g. 15s and 90s) are flagged as a contradiction."""
    parsed = parser.parse("فيديو سريع مدته 15 ثانية واجعله طويل 90 ثانية")
    assert len(parsed.detected_contradictions) > 0
    assert any("conflicting duration numbers" in c.lower() for c in parsed.detected_contradictions)


def test_mixed_language_and_color_extraction(parser: IntentParser):
    """Verifies entity extraction on mixed Arabic/English text including hex colors."""
    parsed = parser.parse("عمل montage ad سريع للـ product مع BGM only وألوان #FF5733 و#1E3A8A")
    assert parsed.detected_language == "MIXED"
    assert parsed.video_type == "DYNAMIC_MONTAGE"
    assert parsed.audio_mode == AudioMode.MUSIC_ONLY
    assert parsed.brand_colors == ["#FF5733", "#1E3A8A"]
    assert parsed.field_provenance["brand_colors"].source_type == ProvenanceType.EXPLICIT
