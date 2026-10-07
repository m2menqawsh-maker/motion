"""
tests/ai/narrative/test_narrative_planner.py
============================================
Unit tests for NarrativePlanner (S28-04 Part A).

Verifies:
1. Adapts narrative structure across video types (SaaS Ad, Explainer, Music Montage, Talking Head, Social Sprint).
2. Music Montage (MUSIC_ONLY) does not require or force spoken narrative scripts or voiceover.
3. Duration fit: duration scope aligns with CreativeBrief target duration without frame compiling.
4. Typed NarrativeBeat and sequential index constraints.
5. Rejection of invalid briefs.
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
from ai.contracts.creative.narrative import NarrativePlan
from ai.narrative.contracts import InvalidNarrativePlanError
from ai.narrative.planner import NarrativePlanner


@pytest.fixture
def narrative_planner():
    return NarrativePlanner()


def create_brief(
    video_type: str,
    audio_mode: AudioMode,
    target_duration: float = 30.0,
    goal: str = "Test Goal",
    key_takeaway: str = "Test Takeaway",
    language: str = "en",
) -> CreativeBrief:
    now = datetime.now(timezone.utc)
    return CreativeBrief(
        brief_id=f"brief_{video_type}_{audio_mode.value}".lower(),
        project_id="proj_test",
        workspace_id="ws_test",
        user_request_raw=f"Create a {video_type} about {goal}.",
        interpreted_intent=CreativeIntent(
            intent_id="intent_001",
            goal=goal,
            audience="General",
            tone="dynamic",
            key_takeaway=key_takeaway,
            call_to_action="Click here",
            video_type=video_type,
            language=language,
        ),
        constraints=CreativeConstraints(
            target_duration_seconds=target_duration,
            aspect_ratios=["9:16"],
            audio_mode=audio_mode,
        ),
        provenance=ProvenanceRecord(
            source="test",
            model_id="test",
            provider_id="test",
            timestamp=now,
            latency_ms=1,
        ),
        created_at=now,
    )


def test_saas_ad_narrative_structure(narrative_planner):
    brief = create_brief(
        video_type="SAAS_DEMO",
        audio_mode=AudioMode.VO_MUSIC,
        target_duration=30.0,
        goal="Automate cloud deployments",
        key_takeaway="Zero downtime infrastructure",
    )
    plan = narrative_planner.plan(brief)

    assert isinstance(plan, NarrativePlan)
    assert plan.arc_structure == "Problem-Agitation-Solution-Proof-CTA"
    assert len(plan.beats) == 5
    assert plan.estimated_total_duration_sec == 30.0
    phases = [b.phase for b in plan.beats]
    assert phases == ["hook", "problem", "solution", "proof", "cta"]
    # Beats have valid sequential indices
    assert [b.beat_index for b in plan.beats] == [0, 1, 2, 3, 4]


def test_music_montage_does_not_force_spoken_voiceover(narrative_planner):
    """Critical invariant: Music Montage in MUSIC_ONLY mode produces visual progression without spoken script."""
    brief = create_brief(
        video_type="DYNAMIC_MONTAGE",
        audio_mode=AudioMode.MUSIC_ONLY,
        target_duration=25.0,
        goal="Summer festival energy",
        key_takeaway="Unforgettable moments",
    )
    plan = narrative_planner.plan(brief)

    assert plan.arc_structure == "Visual-Energy-Progression"
    assert len(plan.beats) == 4
    phases = [b.phase for b in plan.beats]
    assert phases == ["visual_hook", "visual_progression", "energy_peak", "payoff_frame"]

    # Verify that beats contain visual directions, not spoken voiceover scripts
    for beat in plan.beats:
        assert "narrator says" not in beat.key_message.lower()
        assert beat.visual_hook_description is not None


def test_educational_explainer_structure(narrative_planner):
    brief = create_brief(
        video_type="EXPLAINER",
        audio_mode=AudioMode.VO_MUSIC,
        target_duration=45.0,
        goal="Explain quantum computing basics",
        key_takeaway="Qubits leverage superposition and entanglement",
    )
    plan = narrative_planner.plan(brief)

    assert plan.arc_structure == "Concept-Foundation-Mechanism-Example-Summary"
    assert len(plan.beats) == 5
    assert plan.estimated_total_duration_sec == 45.0
    assert plan.beats[0].phase == "hook"
    assert plan.beats[2].phase == "mechanism"


def test_talking_head_speech_progression(narrative_planner):
    brief = create_brief(
        video_type="TALKING_HEAD",
        audio_mode=AudioMode.SOURCE_AUDIO,
        target_duration=30.0,
        goal="Advice for first-time founders",
        key_takeaway="Talk to 50 customers before writing code",
    )
    plan = narrative_planner.plan(brief)

    assert plan.arc_structure == "Conversational-Insight"
    assert len(plan.beats) == 4
    assert plan.beats[0].phase == "hook"
    assert plan.beats[-1].phase == "wrap_up"


def test_short_sprint_duration_fit(narrative_planner):
    """15-second ad gets tight 3-beat structure matching duration."""
    brief = create_brief(
        video_type="ARTICLE_SPRINT",
        audio_mode=AudioMode.VO_MUSIC,
        target_duration=15.0,
        goal="Fast productivity hack",
        key_takeaway="Timeboxing calendar blocks",
    )
    plan = narrative_planner.plan(brief)

    assert plan.arc_structure == "Hook-Proof-CTA"
    assert len(plan.beats) == 3
    assert plan.estimated_total_duration_sec == 15.0
    total_beat_duration = sum(b.estimated_duration_sec for b in plan.beats)
    assert abs(total_beat_duration - 15.0) <= 0.1


def test_invalid_brief_missing_id_rejected(narrative_planner):
    now = datetime.now(timezone.utc)
    brief = CreativeBrief(
        brief_id="",
        project_id="proj_test",
        workspace_id="ws_test",
        user_request_raw="Test",
        interpreted_intent=CreativeIntent(
            intent_id="i1", goal="g", audience="a", tone="t", key_takeaway="k"
        ),
        constraints=CreativeConstraints(),
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )
    with pytest.raises(InvalidNarrativePlanError):
        narrative_planner.plan(brief)
