"""
tests/ai/narrative/test_narrative_metrics.py
============================================
Tests for NarrativeMetricsEvaluator (S28-04 Part A).

Verifies:
1. Goal coverage scoring.
2. Logical flow scoring.
3. Hook relevance scoring.
4. Redundancy detection on repetitive beats.
5. Duration fit scoring.
6. Violation caught when spoken voiceover is present in MUSIC_ONLY montage.
"""

import pytest
from datetime import datetime, timezone

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import (
    AudioMode,
    CreativeBrief,
    CreativeConstraints,
    CreativeIntent,
)
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan
from ai.narrative.metrics import NarrativeMetricsEvaluator


@pytest.fixture
def evaluator():
    return NarrativeMetricsEvaluator()


def make_plan(beats, brief_id="brief_001", total_duration=30.0):
    now = datetime.now(timezone.utc)
    return NarrativePlan(
        narrative_id="plan_test_001",
        brief_id=brief_id,
        core_hook=beats[0].key_message if beats else "None",
        beats=beats,
        arc_structure="Test-Arc",
        estimated_total_duration_sec=total_duration,
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )


def make_brief(audio_mode=AudioMode.VO_MUSIC, target_duration=30.0, video_type="SAAS_DEMO"):
    now = datetime.now(timezone.utc)
    return CreativeBrief(
        brief_id="brief_001",
        project_id="proj_001",
        workspace_id="ws_001",
        user_request_raw="Test request",
        interpreted_intent=CreativeIntent(
            intent_id="i1",
            goal="Automate cloud infrastructure",
            audience="Developers",
            tone="energetic",
            key_takeaway="Deploy faster with zero config",
            video_type=video_type,
        ),
        constraints=CreativeConstraints(
            target_duration_seconds=target_duration,
            audio_mode=audio_mode,
        ),
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )


def test_metrics_pass_on_well_structured_plan(evaluator):
    brief = make_brief()
    beats = [
        NarrativeBeat(beat_id="b1", beat_index=0, phase="hook", emotional_target="Curiosity", pacing="fast", estimated_duration_sec=6.0, key_message="Struggling to automate cloud infrastructure?"),
        NarrativeBeat(beat_id="b2", beat_index=1, phase="problem", emotional_target="Urgency", pacing="moderate", estimated_duration_sec=8.0, key_message="Manual setup creates friction and downtime."),
        NarrativeBeat(beat_id="b3", beat_index=2, phase="solution", emotional_target="Delight", pacing="moderate", estimated_duration_sec=8.0, key_message="Deploy faster with zero config using our automated platform."),
        NarrativeBeat(beat_id="b4", beat_index=3, phase="cta", emotional_target="Confidence", pacing="slow", estimated_duration_sec=8.0, key_message="Start deploying today with zero risk."),
    ]
    plan = make_plan(beats, total_duration=30.0)

    result = evaluator.evaluate(plan, brief)
    assert result.passed is True
    assert result.goal_coverage >= 0.70
    assert result.logical_flow >= 0.80
    assert result.hook_relevance >= 0.70
    assert result.redundancy_score <= 0.35
    assert result.duration_fit >= 0.90


def test_metrics_penalize_redundancy(evaluator):
    """Detects duplicate messages across beats."""
    brief = make_brief()
    beats = [
        NarrativeBeat(beat_id="b1", beat_index=0, phase="hook", emotional_target="Curiosity", pacing="fast", estimated_duration_sec=10.0, key_message="Deploy cloud infrastructure instantly"),
        NarrativeBeat(beat_id="b2", beat_index=1, phase="problem", emotional_target="Urgency", pacing="moderate", estimated_duration_sec=10.0, key_message="Deploy cloud infrastructure instantly"),
        NarrativeBeat(beat_id="b3", beat_index=2, phase="cta", emotional_target="Confidence", pacing="slow", estimated_duration_sec=10.0, key_message="Deploy cloud infrastructure instantly"),
    ]
    plan = make_plan(beats, total_duration=30.0)

    result = evaluator.evaluate(plan, brief)
    assert result.redundancy_score > 0.35
    assert result.passed is False


def test_metrics_penalize_spoken_vo_in_music_only(evaluator):
    """Enforces that spoken voiceover scripts in MUSIC_ONLY trigger a heavy penalty."""
    brief = make_brief(audio_mode=AudioMode.MUSIC_ONLY, video_type="DYNAMIC_MONTAGE")
    beats = [
        NarrativeBeat(beat_id="b1", beat_index=0, phase="visual_hook", emotional_target="Curiosity", pacing="fast", estimated_duration_sec=10.0, key_message="Voiceover narrator says: welcome to our product"),
        NarrativeBeat(beat_id="b2", beat_index=1, phase="visual_progression", emotional_target="Delight", pacing="moderate", estimated_duration_sec=10.0, key_message="Voiceover speaker explains the feature"),
        NarrativeBeat(beat_id="b3", beat_index=2, phase="payoff_frame", emotional_target="Confidence", pacing="slow", estimated_duration_sec=10.0, key_message="Voiceover closes with call to action"),
    ]
    plan = make_plan(beats, total_duration=30.0)

    result = evaluator.evaluate(plan, brief)
    assert result.narrative_type_appropriateness < 0.50
    assert result.passed is False
