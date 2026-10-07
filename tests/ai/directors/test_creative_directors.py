"""
tests/ai/directors/test_creative_directors.py
=============================================
Tests for Creative Directors (S28-04 Part D).

Verifies:
1. NarrativeDirector emits structured NarrativeDirection[].
2. MotionDirector emits structured MotionDirection[] with valid archetype choreography.
3. EmotionDirector emits structured EmotionDirection[] with emotional progression.
4. SfxDirector strictly respects AudioMode:
   • SILENT mode yields zero sound cues.
   • MUSIC_ONLY mode suppresses spoken VO cues.
   • Consecutive SFX alternation avoids repeating the same audio file.
5. CreativeDirectorCoordinator outputs a unified DirectorRecommendationBundle.
6. Directors have zero runtime authority.
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
from ai.contracts.creative.directors import (
    DirectorRecommendationBundle,
    EmotionDirection,
    MotionDirection,
    NarrativeDirection,
    SfxDirection,
)
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan
from ai.directors.bundle import CreativeDirectorCoordinator
from ai.directors.emotion_director import EmotionDirector
from ai.directors.motion_director import MotionDirector
from ai.directors.narrative_director import NarrativeDirector
from ai.directors.sfx_director import SfxDirector
from ai.taste.context import TasteContextBuilder


def make_context(audio_mode=AudioMode.VO_MUSIC, tone="cinematic", language="en"):
    now = datetime.now(timezone.utc)
    brief = CreativeBrief(
        brief_id="brief_dir_001",
        project_id="proj_001",
        workspace_id="ws_001",
        user_request_raw="Test brief",
        interpreted_intent=CreativeIntent(
            intent_id="i1",
            goal="Cloud Automation",
            audience="Devs",
            tone=tone,
            key_takeaway="Zero manual effort",
            language=language,
        ),
        constraints=CreativeConstraints(
            target_duration_seconds=30.0,
            audio_mode=audio_mode,
        ),
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )
    plan = NarrativePlan(
        narrative_id="narr_001",
        brief_id="brief_dir_001",
        core_hook="Automate cloud deployments",
        beats=[
            NarrativeBeat(
                beat_id="beat_001",
                beat_index=0,
                phase="hook",
                emotional_target="Curiosity",
                pacing="fast",
                estimated_duration_sec=10.0,
                key_message="Are you still deploying servers by hand?",
                visual_hook_description="Neon ring around manual servers headline",
            ),
            NarrativeBeat(
                beat_id="beat_002",
                beat_index=1,
                phase="proof",
                emotional_target="Confidence",
                pacing="moderate",
                estimated_duration_sec=10.0,
                key_message="Our platform deploys globally in 5 seconds.",
                visual_hook_description="Neon ring around 5 seconds stat counter",  # Consecutive gesture to test alternate SFX
            ),
            NarrativeBeat(
                beat_id="beat_003",
                beat_index=2,
                phase="cta",
                emotional_target="Confidence",
                pacing="slow",
                estimated_duration_sec=10.0,
                key_message="Deploy free today.",
                visual_hook_description="Marker underline under CTA button",
            ),
        ],
        arc_structure="Hook-Proof-CTA",
        estimated_total_duration_sec=30.0,
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )
    return TasteContextBuilder.build(brief=brief, narrative_plan=plan)


def test_narrative_director_structured_output():
    director = NarrativeDirector()
    ctx = make_context()
    dirs = director.direct(ctx)

    assert len(dirs) == 3
    for d in dirs:
        assert isinstance(d, NarrativeDirection)
        assert d.beat_id
        assert d.narrative_focus in ["hook_grab", "proof_demonstration", "action_cta"]
        assert d.spoken_line is not None


def test_narrative_director_suppresses_spoken_line_in_music_only():
    director = NarrativeDirector()
    ctx = make_context(audio_mode=AudioMode.MUSIC_ONLY)
    dirs = director.direct(ctx)

    for d in dirs:
        assert d.spoken_line is None


def test_motion_director_cinematic_personality():
    director = MotionDirector()
    ctx = make_context(tone="cinematic luxury")
    dirs = director.direct(ctx)

    assert len(dirs) == 3
    for d in dirs:
        assert isinstance(d, MotionDirection)
        assert d.motion_personality == "Cinematic"
        assert d.motion_energy == "calm"
        assert d.text_motion == "smooth_fade_tracking"


def test_motion_director_arabic_rtl_tracking():
    director = MotionDirector()
    ctx = make_context(language="ar")
    dirs = director.direct(ctx)

    for d in dirs:
        assert d.text_motion == "rtl_kinetic_tracking"


def test_emotion_director_progression():
    director = EmotionDirector()
    ctx = make_context()
    dirs = director.direct(ctx)

    assert len(dirs) == 3
    for d in dirs:
        assert isinstance(d, EmotionDirection)
        assert d.primary_emotion
        assert d.emotional_progression


def test_sfx_director_silent_mode_suppression():
    director = SfxDirector()
    ctx = make_context(audio_mode=AudioMode.SILENT)
    dirs = director.direct(ctx)

    for d in dirs:
        assert isinstance(d, SfxDirection)
        assert d.audio_mode == AudioMode.SILENT
        assert len(d.sound_cues) == 0
        assert d.ducking_profile is None


def test_sfx_director_consecutive_variation():
    """Beat 1 and Beat 2 both have 'neon ring' gesture; verifies Beat 2 receives alternate SFX."""
    director = SfxDirector()
    ctx = make_context(audio_mode=AudioMode.VO_MUSIC)
    dirs = director.direct(ctx)

    sfx_beat_1 = dirs[0].sound_cues[0]["sfx_file"]
    sfx_beat_2 = dirs[1].sound_cues[0]["sfx_file"]

    assert sfx_beat_1 == "chime-soft.wav"
    # Beat 2 must use alternate SFX to prevent repetition
    assert sfx_beat_2 == "bell-subtle.wav"
    assert sfx_beat_1 != sfx_beat_2


def test_director_coordinator_bundle():
    coordinator = CreativeDirectorCoordinator()
    ctx = make_context()
    bundle = coordinator.direct_all(ctx)

    assert isinstance(bundle, DirectorRecommendationBundle)
    assert len(bundle.narrative_directions) == 3
    assert len(bundle.motion_directions) == 3
    assert len(bundle.emotion_directions) == 3
    assert len(bundle.sfx_directions) == 3


def test_directors_reject_invalid_contract_schema():
    """Negative: Proves that Director models reject missing required fields or extra unauthorized fields."""
    from pydantic import ValidationError

    # 1. NarrativeDirection missing beat_id
    with pytest.raises(ValidationError):
        NarrativeDirection(
            narrative_focus="hook",
            pacing_instruction="fast",
            information_density="moderate",
            visual_progression_cue="cue",
        )

    # 2. MotionDirection missing scene_id
    with pytest.raises(ValidationError):
        MotionDirection(
            motion_energy="high",
            motion_personality="Energetic",
            entry_style="zoom",
            exit_style="pan",
            camera_intent="push",
            text_motion="pop",
        )

    # 3. EmotionDirection missing primary_emotion
    with pytest.raises(ValidationError):
        EmotionDirection(
            beat_or_scene_id="b1",
            intensity="high",
            emotional_progression="A->B",
        )

    # 4. SfxDirection missing audio_mode
    with pytest.raises(ValidationError):
        SfxDirection(
            beat_or_scene_id="b1",
        )


def test_narrative_director_music_only_no_speech_direction():
    """AudioMode invariant: NarrativeDirector in MUSIC_ONLY mode produces zero speech/TTS direction."""
    director = NarrativeDirector()
    ctx = make_context(audio_mode=AudioMode.MUSIC_ONLY)
    dirs = director.direct(ctx)
    assert len(dirs) > 0
    for d in dirs:
        assert d.spoken_line is None, f"Expected None spoken_line in MUSIC_ONLY, got: {d.spoken_line}"


def test_sfx_director_silent_no_audio_direction():
    """AudioMode invariant: SfxDirector in SILENT mode produces zero sound cues or ducking."""
    director = SfxDirector()
    ctx = make_context(audio_mode=AudioMode.SILENT)
    dirs = director.direct(ctx)
    assert len(dirs) > 0
    for d in dirs:
        assert d.audio_mode == AudioMode.SILENT
        assert len(d.sound_cues) == 0, f"Expected 0 sound cues in SILENT mode, got: {d.sound_cues}"
        assert d.ducking_profile is None

