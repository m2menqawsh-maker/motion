"""
tests/ai/taste/test_taste_engine.py
===================================
Tests for TasteEngine, TasteEvaluator, and TasteDecision (S28-04 Part C).

Verifies:
1. TasteEngine produces typed TasteDecision[] with confidence, evidence, and reason_summary.
2. Traceability: Each decision links to rule ID, citation, and evidence without hidden CoT.
3. Exception handling: SILENT mode waives gestural audio sync.
4. Absence of UserStyleProfile is handled gracefully without error.
5. Invariants: Taste ≠ QC, Taste cannot mutate lifecycle or approve studio gates.
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
from ai.contracts.creative.taste import TasteContext, TasteDecision
from ai.taste.context import TasteContextBuilder
from ai.taste.engine import TasteEngine
from ai.taste.evaluator import TasteEvaluator
from ai.taste.registry import TasteRuleRegistry


@pytest.fixture
def taste_engine():
    return TasteEngine()


def make_context(audio_mode=AudioMode.VO_MUSIC, language="en", duration=30.0):
    now = datetime.now(timezone.utc)
    brief = CreativeBrief(
        brief_id="brief_taste_001",
        project_id="proj_001",
        workspace_id="ws_001",
        user_request_raw="Test brief",
        interpreted_intent=CreativeIntent(
            intent_id="i1",
            goal="Automate workflows",
            audience="Engineers",
            tone="cinematic",
            key_takeaway="Fast execution",
            language=language,
        ),
        constraints=CreativeConstraints(
            target_duration_seconds=duration,
            audio_mode=audio_mode,
            brand_colors=["#FF0055", "#00F0FF"],
        ),
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )
    plan = NarrativePlan(
        narrative_id="narr_001",
        brief_id="brief_taste_001",
        core_hook="Automate now",
        beats=[
            NarrativeBeat(
                beat_id="beat_001",
                beat_index=0,
                phase="hook",
                emotional_target="Curiosity",
                pacing="fast",
                estimated_duration_sec=10.0,
                key_message="Start here",
                visual_hook_description="Neon ring around hero text",
            ),
            NarrativeBeat(
                beat_id="beat_002",
                beat_index=1,
                phase="cta",
                emotional_target="Confidence",
                pacing="slow",
                estimated_duration_sec=20.0,
                key_message="Join today",
                visual_hook_description="Marker underline under cta button",
            ),
        ],
        arc_structure="Hook-CTA",
        estimated_total_duration_sec=duration,
        provenance=ProvenanceRecord(source="test", timestamp=now),
        created_at=now,
    )
    return TasteContextBuilder.build(
        brief=brief,
        narrative_plan=plan,
        user_style_profile=None,  # Explicitly test absent profile
    )


def test_taste_engine_produces_typed_decisions(taste_engine):
    ctx = make_context()
    decisions = taste_engine.evaluate_taste(ctx)

    assert len(decisions) > 0
    for d in decisions:
        assert isinstance(d, TasteDecision)
        assert d.decision_id
        assert d.rule_id
        assert d.citation
        assert 0.0 <= d.confidence <= 1.0
        assert len(d.rule_ids) > 0
        assert len(d.evidence) > 0
        assert d.reason_summary != ""
        # No hidden CoT: reason_summary should be concise
        assert len(d.reason_summary) < 500


def test_arabic_language_triggers_rtl_tracking_rule(taste_engine):
    ctx = make_context(language="ar")
    decisions = taste_engine.evaluate_taste(ctx)
    applied_rules = [d.rule_id for d in decisions]
    assert "taste_kinetic_rtl_tracking" in applied_rules


def test_silent_audio_mode_waives_gestural_sfx(taste_engine):
    """In SILENT mode, gestural audio sync rule is waived by exception."""
    ctx = make_context(audio_mode=AudioMode.SILENT)
    decisions = taste_engine.evaluate_taste(ctx)
    applied_rules = [d.rule_id for d in decisions]
    assert "taste_silent_audio_mode" in applied_rules


def test_taste_decision_cannot_be_qc_verdict():
    """Taste decision is an aesthetic proposal and cannot forge or substitute a QC report."""
    now = datetime.now(timezone.utc)
    dec = TasteDecision(
        decision_id="dec_01",
        rule_id="taste_avoid_constant_motion",
        context_ref="canvas_global",
        applied_value="Pause 200ms",
        reasoning="Prevents fatigue",
        citation="references/4_taste_engine/user-signature-style.md#L54",
        confidence=0.95,
        rule_ids=["taste_avoid_constant_motion"],
        evidence=["scene_density is high"],
        reason_summary="Applied rest pause",
    )
    # Ensure TasteDecision has no authority fields
    assert not hasattr(dec, "qc_passed")
    assert not hasattr(dec, "studio_approved")
    assert not hasattr(dec, "render_authorized")


def test_taste_decision_cannot_authorize_render(taste_engine):
    """Taste decisions are purely advisory creative suggestions and cannot authorize rendering."""
    ctx = make_context()
    decisions = taste_engine.evaluate_taste(ctx)
    for d in decisions:
        # Taste decisions cannot contain authorization tokens, signatures, or render execution flags
        assert not hasattr(d, "authorize_render")
        assert not hasattr(d, "render_token")
        assert not hasattr(d, "bypass_render_check")
        # Ensure it cannot pretend to be a render manifest or execution instruction
        assert "EXECUTE_RENDER" not in d.applied_value


def test_taste_cannot_mutate_lifecycle(taste_engine):
    """Taste subsystem has zero capability to transition or mutate pipeline lifecycle state."""
    # Ensure neither TasteEngine nor TasteRuleRegistry expose lifecycle mutation methods
    forbidden_lifecycle_methods = [
        "transition_state", "update_pipeline_state", "mark_qc_passed",
        "set_lifecycle_state", "unlock_pipeline", "advance_step"
    ]
    for method in forbidden_lifecycle_methods:
        assert not hasattr(taste_engine, method)
        assert not hasattr(taste_engine.evaluator, method)
        assert not hasattr(taste_engine.registry, method)


def test_taste_cannot_authorize_tools(taste_engine):
    """Taste decisions cannot grant tool execution authorizations."""
    ctx = make_context()
    decisions = taste_engine.evaluate_taste(ctx)
    for d in decisions:
        assert not hasattr(d, "authorized_tools")
        assert not hasattr(d, "grant_capability")
        assert not hasattr(d, "tool_signature")


def test_taste_cannot_write_canonical_template_registry(taste_engine):
    """Taste subsystem cannot write or mutate the canonical template registry catalog."""
    forbidden_registry_methods = [
        "promote_template", "write_template_catalog", "register_template_file",
        "save_canonical_template", "mutate_registry"
    ]
    for method in forbidden_registry_methods:
        assert not hasattr(taste_engine, method)
        assert not hasattr(taste_engine.registry, method)


def test_taste_rule_compliance_audit_all_15_rules(taste_engine):
    """Audit: All 15 active rules are valid, versioned, traceable, with 0 untraceable rules."""
    rules = taste_engine.registry.list_all()
    assert len(rules) == 15, "Expected exactly 15 canonical rules"

    untraceable = 0
    for r in rules:
        assert r.rule_id, "rule_id is required"
        assert r.version, f"version required for {r.rule_id}"
        assert r.recommendation, f"recommendation required for {r.rule_id}"
        assert r.priority > 0, f"priority required for {r.rule_id}"
        assert isinstance(r.applies_when, dict), f"applies_when required for {r.rule_id}"
        assert isinstance(r.exceptions, list), f"exceptions list required for {r.rule_id}"
        assert r.source_knowledge_ids and len(r.source_knowledge_ids) > 0, f"source_knowledge_ids required for {r.rule_id}"
        if not r.source_knowledge_ids:
            untraceable += 1

    assert untraceable == 0, "Untraceable active rules must be 0"

