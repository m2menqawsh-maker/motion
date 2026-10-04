"""
tests/ai/style/test_current_request_wins.py
===========================================
Critical Gate Test: S28-08A Section 16 & Section 6.

INVARIANT:
Current explicit request ALWAYS overrides remembered preferences.

Profile Setup:
- pacing = FAST
- motion_intensity = HIGH
- music = ENERGETIC

Current User Request:
"اعمل الفيديو هادئ، حركة بسيطة، بدون موسيقى"

Expected Result:
- calm / slow pacing
- low motion intensity
- SILENT / no music according to canonical AudioMode semantics
- Decision trace explicitly proves old preferences were considered and overridden
- End-to-end CreativePlanner produces scene intents strictly respecting the current request!
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import (
    AudioMode,
    CreativeBrief,
    CreativeConstraints,
    CreativeIntent,
    FieldProvenance,
    ProvenanceType,
)
from ai.contracts.creative.feedback import (
    StylePreferenceProvenance,
    UserStyleProfile,
    WinningSource,
)
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan
from ai.memory.models import TrustedTenantContext
from ai.memory.types import EpistemicStatus, SourceType
from ai.planning.creative_planner import CreativePlanner
from ai.style.resolver import UserStyleResolver


@pytest.fixture
def authoritative_context():
    return TrustedTenantContext(workspace_id="ws_critical_test", user_id="usr_critical")


@pytest.fixture
def high_energy_profile(authoritative_context):
    now = datetime.now(timezone.utc)
    return UserStyleProfile(
        profile_id="prof_high_energy",
        workspace_id=authoritative_context.workspace_id,
        user_id=authoritative_context.user_id,
        pacing_preference="fast",
        motion_intensity="high",
        preferred_motion_personality="Energetic",
        music_tendencies="energetic",
        provenance_by_dimension={
            "pacing": StylePreferenceProvenance(
                dimension="pacing",
                epistemic_status=EpistemicStatus.CONFIRMED,
                confidence=0.95,
                source_type=SourceType.HUMAN_CONFIRMATION,
                evidence_count=5,
                last_observed_at=now,
            ),
            "motion_intensity": StylePreferenceProvenance(
                dimension="motion_intensity",
                epistemic_status=EpistemicStatus.CONFIRMED,
                confidence=0.92,
                source_type=SourceType.HUMAN_CONFIRMATION,
                evidence_count=4,
                last_observed_at=now,
            ),
            "music_tendencies": StylePreferenceProvenance(
                dimension="music_tendencies",
                epistemic_status=EpistemicStatus.EXPLICIT,
                confidence=0.9,
                source_type=SourceType.USER_STATEMENT,
                evidence_count=2,
                last_observed_at=now,
            ),
        },
        updated_at=now,
    )


class TestCurrentRequestWinsGate:

    def test_section_16_critical_current_request_wins_resolver(
        self, authoritative_context, high_energy_profile
    ):
        """
        Critical Test (Section 16):
        Current request: "اعمل الفيديو هادئ، حركة بسيطة، بدون موسيقى"
        Profile: fast pacing, high motion, energetic music.
        Must yield calm pacing, low motion, and no music with full override traces.
        """
        now = datetime.now(timezone.utc)
        user_prompt = "اعمل الفيديو هادئ، حركة بسيطة، بدون موسيقى"

        brief = CreativeBrief(
            brief_id="brief_critical_001",
            project_id="prj_critical_001",
            workspace_id=authoritative_context.workspace_id,
            user_request_raw=user_prompt,
            interpreted_intent=CreativeIntent(
                intent_id="intent_crit_001",
                goal="Calm explainer",
                audience="Mindfulness practitioners",
                tone="Calm",
                key_takeaway="Simplicity and peace",
                pace="CALM",
            ),
            constraints=CreativeConstraints(
                audio_mode=AudioMode.SILENT,  # Explicitly without music
                target_duration_seconds=20.0,
                aspect_ratios=["9:16"],
            ),
            provenance=ProvenanceRecord(
                source="test",
                model_id="test-model",
                provider_id="test-provider",
                timestamp=now,
            ),
            field_provenance={
                "pace": FieldProvenance(
                    source_type=ProvenanceType.EXPLICIT,
                    raw_reference="هادئ",
                )
            },
            created_at=now,
        )

        effective_style = UserStyleResolver.resolve_effective_style(
            context=authoritative_context,
            brief=brief,
            profile=high_energy_profile,
        )

        # 1. Verify Effective Pacing is calm
        assert effective_style.pacing == "calm"
        pacing_trace = next(t for t in effective_style.trace_records if t.dimension == "pacing")
        assert pacing_trace.is_overridden is True
        assert pacing_trace.considered_value == "fast"
        assert pacing_trace.applied_value == "calm"
        assert pacing_trace.winning_source == WinningSource.CURRENT_REQUEST

        # 2. Verify Effective Motion Intensity is low
        assert effective_style.motion_intensity == "low"
        motion_trace = next(t for t in effective_style.trace_records if t.dimension == "motion_intensity")
        assert motion_trace.is_overridden is True
        assert motion_trace.considered_value == "high"
        assert motion_trace.applied_value == "low"
        assert motion_trace.winning_source == WinningSource.CURRENT_REQUEST

        # 3. Verify Music is none (SILENT mode / no music)
        assert effective_style.music_preference == "none"
        music_trace = next(t for t in effective_style.trace_records if t.dimension == "music_preference")
        assert music_trace.is_overridden is True
        assert music_trace.considered_value == "energetic"
        assert music_trace.applied_value == "none"
        assert music_trace.winning_source == WinningSource.CURRENT_REQUEST

    def test_section_16_critical_current_request_wins_planner_e2e(
        self, authoritative_context, high_energy_profile
    ):
        """
        Proves that CreativePlanner consumes the resolved effective style and does NOT
        inject high-energy motion or background music when user requested calm/silent.
        """
        now = datetime.now(timezone.utc)
        user_prompt = "اعمل الفيديو هادئ، حركة بسيطة، بدون موسيقى"

        brief = CreativeBrief(
            brief_id="brief_critical_002",
            project_id="prj_critical_002",
            workspace_id=authoritative_context.workspace_id,
            user_request_raw=user_prompt,
            interpreted_intent=CreativeIntent(
                intent_id="intent_crit_002",
                goal="Calm presentation",
                audience="Engineers",
                tone="Calm",
                key_takeaway="Peaceful clarity",
                pace="CALM",
            ),
            constraints=CreativeConstraints(
                audio_mode=AudioMode.SILENT,
                target_duration_seconds=10.0,
                aspect_ratios=["16:9"],
            ),
            provenance=ProvenanceRecord(
                source="test",
                model_id="test-model",
                provider_id="test-provider",
                timestamp=now,
            ),
            created_at=now,
        )

        narrative = NarrativePlan(
            narrative_id="np_crit_002",
            brief_id=brief.brief_id,
            core_hook="Peaceful opening hook",
            arc_structure="Hook-Payoff",
            beats=[
                NarrativeBeat(
                    beat_id="beat_01",
                    beat_index=0,
                    phase="HOOK",
                    emotional_target="calm",
                    pacing="calm",
                    key_message="Start with stillness and calm focus.",
                    estimated_duration_sec=5.0,
                ),
                NarrativeBeat(
                    beat_id="beat_02",
                    beat_index=1,
                    phase="PAYOFF",
                    emotional_target="peaceful",
                    pacing="calm",
                    key_message="Achieve total clarity and balance.",
                    estimated_duration_sec=5.0,
                ),
            ],
            estimated_total_duration_sec=10.0,
            provenance=ProvenanceRecord(
                source="test",
                model_id="test-model",
                provider_id="test-provider",
                timestamp=now,
            ),
            created_at=now,
        )

        planner = CreativePlanner()
        # Pass the high-energy profile directly to planner; planner must resolve and apply current request!
        plan = planner.plan(
            brief=brief,
            narrative_plan=narrative,
            user_style=high_energy_profile,
        )

        assert plan.total_estimated_duration_sec == 10.0
        assert len(plan.scenes) == 2

        for scene in plan.scenes:
            # 1. Motion personality MUST NOT be Energetic
            assert scene.motion_personality != "Energetic"
            assert scene.motion_personality == "Cinematic"

            # 2. Audio intent MUST strictly be silent
            assert scene.audio_intent == "silent_mode_no_audio"

            # 3. Spoken text MUST be None under SILENT mode
            assert scene.spoken_text is None
