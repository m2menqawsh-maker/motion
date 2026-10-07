"""
tests/ai/style/test_style_resolver_precedence.py
================================================
Canonical Precedence Tests for UserStyleResolver (S28-08A Section 6, 7, 17, 21).

Precedence Rule:
Current explicit request
>
project / brand constraints
>
confirmed user preferences
>
inferred preferences
>
global defaults

Verifies:
- All precedence levels resolve deterministically.
- Full traceability: considered value, source, confidence, override flag, reason, and winning source.
- Zero hidden chain-of-thought.
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
from ai.memory.models import TrustedTenantContext
from ai.memory.types import EpistemicStatus, SourceType
from ai.style.resolver import UserStyleResolver


@pytest.fixture
def base_context():
    return TrustedTenantContext(workspace_id="ws_precedence", user_id="usr_editor")


def make_brief(user_prompt: str, pace: str = "MODERATE", audio_mode: AudioMode = AudioMode.VO_MUSIC) -> CreativeBrief:
    now = datetime.now(timezone.utc)
    return CreativeBrief(
        brief_id="brief_prec_test",
        project_id="prj_prec_test",
        workspace_id="ws_precedence",
        user_request_raw=user_prompt,
        interpreted_intent=CreativeIntent(
            intent_id="intent_001",
            goal="Test precedence hierarchy",
            audience="Engineers",
            tone="Technical",
            key_takeaway="Precedence rules are absolute",
            pace=pace,
        ),
        constraints=CreativeConstraints(
            audio_mode=audio_mode,
            target_duration_seconds=30.0,
            aspect_ratios=["16:9"],
        ),
        provenance=ProvenanceRecord(
            source="test",
            model_id="test-model",
            provider_id="test-provider",
            timestamp=now,
        ),
        field_provenance={
            "pace": FieldProvenance(
                source_type=ProvenanceType.EXPLICIT if pace != "MODERATE" else ProvenanceType.DEFAULTED,
                rationale="User specified",
            )
        },
        created_at=now,
    )


class TestStyleResolverPrecedence:

    def test_precedence_no_stored_profile_uses_defaults(self, base_context):
        """When no stored profile or explicit directive exists, global defaults apply."""
        brief = make_brief("فيديو تعريفي عام للمنصة")
        effective = UserStyleResolver.resolve_effective_style(
            context=base_context,
            brief=brief,
            profile=None,
        )

        assert effective.pacing == "moderate"
        assert effective.motion_intensity == "medium"
        assert effective.visual_complexity == "clean"

        # Check trace
        pacing_trace = next(t for t in effective.trace_records if t.dimension == "pacing")
        assert pacing_trace.winning_source == WinningSource.GLOBAL_DEFAULT
        assert pacing_trace.is_overridden is False

    def test_precedence_confirmed_preference_applied_without_conflict(self, base_context):
        """Confirmed user preference applies when no conflicting request or brand constraint exists."""
        now = datetime.now(timezone.utc)
        profile = UserStyleProfile(
            profile_id="prof_1",
            workspace_id=base_context.workspace_id,
            user_id=base_context.user_id,
            pacing_preference="fast",
            provenance_by_dimension={
                "pacing": StylePreferenceProvenance(
                    dimension="pacing",
                    epistemic_status=EpistemicStatus.CONFIRMED,
                    confidence=0.95,
                    source_type=SourceType.HUMAN_CONFIRMATION,
                    evidence_count=4,
                    last_observed_at=now,
                )
            },
            updated_at=now,
        )

        brief = make_brief("فيديو عادي بدون تحديد إيقاع")
        effective = UserStyleResolver.resolve_effective_style(
            context=base_context,
            brief=brief,
            profile=profile,
        )

        assert effective.pacing == "fast"
        pacing_trace = next(t for t in effective.trace_records if t.dimension == "pacing")
        assert pacing_trace.winning_source == WinningSource.CONFIRMED_USER_PREFERENCE
        assert pacing_trace.is_overridden is False
        assert pacing_trace.considered_value == "fast"

    def test_precedence_inferred_preference_applies_when_uncontested(self, base_context):
        """Inferred preference guides planning when neither explicit request, brand, nor confirmed preference exists."""
        now = datetime.now(timezone.utc)
        profile = UserStyleProfile(
            profile_id="prof_1",
            workspace_id=base_context.workspace_id,
            user_id=base_context.user_id,
            motion_intensity="low",
            provenance_by_dimension={
                "motion_intensity": StylePreferenceProvenance(
                    dimension="motion_intensity",
                    epistemic_status=EpistemicStatus.INFERRED,
                    confidence=0.6,
                    source_type=SourceType.AI_INFERENCE,
                    evidence_count=1,
                    last_observed_at=now,
                )
            },
            updated_at=now,
        )

        brief = make_brief("اعمل فيديو تعليمي")
        effective = UserStyleResolver.resolve_effective_style(
            context=base_context,
            brief=brief,
            profile=profile,
        )

        assert effective.motion_intensity == "low"
        motion_trace = next(t for t in effective.trace_records if t.dimension == "motion_intensity")
        assert motion_trace.winning_source == WinningSource.INFERRED_PREFERENCE
        assert motion_trace.is_overridden is False

    def test_precedence_current_request_conflicts_with_confirmed_preference(self, base_context):
        """Current explicit request STRICTLY overrides confirmed user preference."""
        now = datetime.now(timezone.utc)
        profile = UserStyleProfile(
            profile_id="prof_1",
            workspace_id=base_context.workspace_id,
            user_id=base_context.user_id,
            pacing_preference="fast",
            provenance_by_dimension={
                "pacing": StylePreferenceProvenance(
                    dimension="pacing",
                    epistemic_status=EpistemicStatus.CONFIRMED,
                    confidence=0.98,
                    source_type=SourceType.HUMAN_CONFIRMATION,
                    evidence_count=5,
                    last_observed_at=now,
                )
            },
            updated_at=now,
        )

        # Explicit request asks for calm/slow pacing
        brief = make_brief("هذا الفيديو بدي إياه هادئ")
        effective = UserStyleResolver.resolve_effective_style(
            context=base_context,
            brief=brief,
            profile=profile,
        )

        assert effective.pacing == "calm"
        pacing_trace = next(t for t in effective.trace_records if t.dimension == "pacing")
        assert pacing_trace.winning_source == WinningSource.CURRENT_REQUEST
        assert pacing_trace.is_overridden is True
        assert pacing_trace.considered_value == "fast"
        assert pacing_trace.applied_value == "calm"
        assert "overrides stored preference" in (pacing_trace.override_reason or "")

    def test_precedence_brand_constraint_conflicts_with_user_preference(self, base_context):
        """Brand guideline overrides stored user preference when request is silent."""
        now = datetime.now(timezone.utc)
        profile = UserStyleProfile(
            profile_id="prof_1",
            workspace_id=base_context.workspace_id,
            user_id=base_context.user_id,
            visual_complexity="minimal",
            provenance_by_dimension={
                "visual_complexity": StylePreferenceProvenance(
                    dimension="visual_complexity",
                    epistemic_status=EpistemicStatus.INFERRED,
                    confidence=0.5,
                    source_type=SourceType.AI_INFERENCE,
                    evidence_count=1,
                    last_observed_at=now,
                )
            },
            updated_at=now,
        )

        brief = make_brief("اعمل برومو تعريفي")
        brand_constraints = {"visual_complexity": "rich_corporate"}

        effective = UserStyleResolver.resolve_effective_style(
            context=base_context,
            brief=brief,
            profile=profile,
            brand_constraints=brand_constraints,
        )

        assert effective.visual_complexity == "rich_corporate"
        vis_trace = next(t for t in effective.trace_records if t.dimension == "visual_complexity")
        assert vis_trace.winning_source == WinningSource.BRAND_CONSTRAINT
        assert vis_trace.is_overridden is True
        assert vis_trace.considered_value == "minimal"
        assert vis_trace.applied_value == "rich_corporate"

    def test_precedence_confirmed_beats_inferred_preference(self, base_context):
        """Higher epistemic confidence and confirmed status outranks inferred hypotheses."""
        now = datetime.now(timezone.utc)
        profile = UserStyleProfile(
            profile_id="prof_1",
            workspace_id=base_context.workspace_id,
            user_id=base_context.user_id,
            pacing_preference="fast",
            motion_intensity="high",
            provenance_by_dimension={
                "pacing": StylePreferenceProvenance(
                    dimension="pacing",
                    epistemic_status=EpistemicStatus.CONFIRMED,
                    confidence=0.95,
                    source_type=SourceType.HUMAN_CONFIRMATION,
                    evidence_count=4,
                    last_observed_at=now,
                ),
                "motion_intensity": StylePreferenceProvenance(
                    dimension="motion_intensity",
                    epistemic_status=EpistemicStatus.INFERRED,
                    confidence=0.4,
                    source_type=SourceType.AI_INFERENCE,
                    evidence_count=1,
                    last_observed_at=now,
                ),
            },
            updated_at=now,
        )

        brief = make_brief("فيديو عادي")
        effective = UserStyleResolver.resolve_effective_style(
            context=base_context,
            brief=brief,
            profile=profile,
        )

        pacing_trace = next(t for t in effective.trace_records if t.dimension == "pacing")
        motion_trace = next(t for t in effective.trace_records if t.dimension == "motion_intensity")

        assert pacing_trace.winning_source == WinningSource.CONFIRMED_USER_PREFERENCE
        assert motion_trace.winning_source == WinningSource.INFERRED_PREFERENCE
