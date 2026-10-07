"""
tests/ai/planning/test_reuse_engine.py
======================================
Authoritative Unit Tests for S28-06 REUSE Engine:
- Canonical Template Registry authority (strict read-only, non-canonical rejected)
- Hard compatibility filters (aspect ratio, AudioMode, props, media, availability)
- Ranking determinism (content_fit, motion_fit, style_fit, duration_fit, media_fit)
- Suitability threshold enforcement (>= 0.70)
- Structured audit evidence (ReuseEvaluationResult)
"""

from __future__ import annotations

import pytest
from typing import Dict, List

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import SceneIntent
from ai.planning.reuse_engine import (
    DeterministicLexicalSemanticScorer,
    ReuseEngine,
)
from scripts.core.template_contract import TemplateRegistryContract


@pytest.fixture
def reuse_engine() -> ReuseEngine:
    return ReuseEngine()


def test_reuse_engine_registry_authority_read_only(reuse_engine: ReuseEngine):
    """Canonical Template Registry is sole template authority; REUSE cannot register or mutate."""
    contract = reuse_engine.contract
    assert isinstance(contract, TemplateRegistryContract)
    assert not hasattr(reuse_engine, "register_template")
    assert not hasattr(reuse_engine, "promote_candidate")
    assert not hasattr(reuse_engine, "mutate_template")


def test_reuse_engine_rejects_unregistered_template(reuse_engine: ReuseEngine):
    """Non-canonical template ID must fail closed and be marked non-eligible with explicit reason."""
    si = SceneIntent(
        scene_id="sc_01",
        scene_index=0,
        intent_label="statistic",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=3.0,
    )
    res = reuse_engine.evaluate(
        scene_intent=si,
        aspect_ratio="9:16",
        force_unregistered_id_for_testing="fake-unregistered-template-xyz",
    )
    assert "fake-unregistered-template-xyz" in res.candidates_checked
    assert "fake-unregistered-template-xyz" not in res.eligible_candidates
    assert "fake-unregistered-template-xyz" in res.rejection_reasons
    assert "not in the Canonical Template Registry" in res.rejection_reasons["fake-unregistered-template-xyz"][0]


def test_reuse_engine_aspect_ratio_hard_filter(reuse_engine: ReuseEngine):
    """Target 9:16 must exclude template restricted to 16:9 only, regardless of semantic relevance."""
    si = SceneIntent(
        scene_id="sc_aspect",
        scene_index=0,
        intent_label="statistic",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=4.0,
    )
    res = reuse_engine.evaluate(
        scene_intent=si,
        aspect_ratio="9:16",
        template_aspect_overrides={"rui-stat-card": ["16:9"]},
    )
    assert "rui-stat-card" not in res.eligible_candidates
    assert "rui-stat-card" in res.rejection_reasons
    reasons = " ".join(res.rejection_reasons["rui-stat-card"])
    assert "Aspect ratio mismatch" in reasons


def test_reuse_engine_audio_mode_forbids_spoken_templates(reuse_engine: ReuseEngine):
    """MUSIC_ONLY and SILENT modes strictly forbid spoken-word / audiogram templates."""
    si_audiogram = SceneIntent(
        scene_id="sc_audio",
        scene_index=0,
        intent_label="audiogram",
        mood="Conversational",
        motion_personality="Dynamic",
        primary_visual_job="speech",
        estimated_duration_sec=5.0,
        template_requirements=["audio_spectrum"],
    )
    res_music = reuse_engine.evaluate(
        scene_intent=si_audiogram,
        audio_mode=AudioMode.MUSIC_ONLY,
    )
    assert not res_music.sufficiency
    assert res_music.selected_candidate is None
    assert "rui-audiogram-scene" not in res_music.eligible_candidates
    assert "rui-podcast-clip" not in res_music.eligible_candidates


def test_reuse_engine_missing_required_props_excluded(reuse_engine: ReuseEngine):
    """Template missing caller required schema property is excluded prior to ranking."""
    si = SceneIntent(
        scene_id="sc_props",
        scene_index=0,
        intent_label="statistic",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=4.0,
    )
    res = reuse_engine.evaluate(
        scene_intent=si,
        required_props=["non_existent_custom_property_999"],
    )
    assert len(res.eligible_candidates) == 0
    assert not res.sufficiency
    assert res.selected_candidate is None


def test_reuse_engine_media_capability_filter(reuse_engine: ReuseEngine):
    """Template requiring video media when template schema has no video support is excluded."""
    si = SceneIntent(
        scene_id="sc_media",
        scene_index=0,
        intent_label="code_demo",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="mechanism",
        estimated_duration_sec=4.0,
    )
    res = reuse_engine.evaluate(
        scene_intent=si,
        required_media=["high_framerate_video_input"],
    )
    for cid in res.candidates_checked:
        if cid not in res.eligible_candidates and cid in res.rejection_reasons:
            reasons = " ".join(res.rejection_reasons[cid])
            if "video media capability" in reasons:
                assert True
                return
    assert False, "Expected at least one candidate rejected for unsupported video media"


def test_reuse_engine_ranking_and_suitability_threshold(reuse_engine: ReuseEngine):
    """Candidate above threshold (0.70) is selected; candidate below threshold is marked insufficient."""
    si_metric = SceneIntent(
        scene_id="sc_rank",
        scene_index=0,
        intent_label="statistic",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=3.0,
        spoken_text="Our platform reduced latency by 80 percent.",
    )
    res = reuse_engine.evaluate(scene_intent=si_metric)
    assert res.sufficiency is True
    assert res.selected_candidate in ("rui-metric-ticker", "animatedcounter-element", "rui-stat-card")
    best = next(c for c in res.ranked_candidates if c.template_id == res.selected_candidate)
    assert best.fit_score >= 0.70
    assert "content_fit" in best.score_breakdown
    assert "motion_fit" in best.score_breakdown
    assert "style_fit" in best.score_breakdown


def test_reuse_engine_deterministic_lexical_scorer():
    """Deterministic lexical scorer computes stable similarity without external network calls."""
    scorer = DeterministicLexicalSemanticScorer()
    sim_exact = scorer.compute_similarity("database performance metric", "database performance metric counters")
    sim_none = scorer.compute_similarity("database performance", "cooking recipes garden flowers")
    assert sim_exact > 0.70
    assert sim_none == 0.0


def test_reuse_engine_audit_evidence_completeness(reuse_engine: ReuseEngine):
    """ReuseEvaluationResult contains full auditable trace without hidden chain-of-thought."""
    si = SceneIntent(
        scene_id="sc_audit",
        scene_index=0,
        intent_label="hook",
        mood="Energetic",
        motion_personality="Cinematic",
        primary_visual_job="action",
        estimated_duration_sec=3.0,
    )
    res = reuse_engine.evaluate(scene_intent=si)
    assert len(res.candidates_checked) > 0
    assert len(res.ranked_candidates) == len(res.candidates_checked)
    assert res.rationale != ""
    assert res.need_description != ""


def test_reuse_engine_explicit_template_family_filtering(reuse_engine: ReuseEngine):
    """Hard filter strictly excludes templates whose family does not match expected_family before ranking."""
    si = SceneIntent(
        scene_id="sc_fam_test",
        scene_index=0,
        intent_label="talking_head",
        mood="Thoughtful",
        motion_personality="Conversational",
        primary_visual_job="presenter",
        estimated_duration_sec=3.0,
    )
    res = reuse_engine.evaluate(scene_intent=si, expected_family="TalkingHead")
    assert "rui-talking-head-layout" in res.eligible_candidates
    assert "rui-stat-card" not in res.eligible_candidates
    assert "rui-code-reveal" not in res.eligible_candidates

    # Non-matching family candidates must have explicit family rejection reason
    stat_rejections = res.rejection_reasons.get("rui-stat-card", [])
    assert any("Template family 'StatCardWrapper' does not match expected family" in r for r in stat_rejections)


def test_reuse_engine_music_montage_excludes_talking_head(reuse_engine: ReuseEngine):
    """Talking-head and creator reel templates are hard-excluded when intent is music montage."""
    si = SceneIntent(
        scene_id="sc_montage_test",
        scene_index=0,
        intent_label="music_montage",
        mood="Energetic",
        motion_personality="Punchy",
        primary_visual_job="action",
        estimated_duration_sec=4.0,
    )
    res = reuse_engine.evaluate(scene_intent=si)
    assert "rui-talking-head-layout" not in res.eligible_candidates
    assert "rui-creator-reel" not in res.eligible_candidates

    th_reasons = res.rejection_reasons.get("rui-talking-head-layout", [])
    assert any("Talking-head/interview template is strictly incompatible with music montage intent" in r for r in th_reasons)


def test_reuse_engine_semantic_ranking_cannot_bypass_hard_filters(reuse_engine: ReuseEngine):
    """Semantic score or token similarity cannot bypass hard filters (aspect ratio, audio mode, etc.)."""
    si = SceneIntent(
        scene_id="sc_bypass_test",
        scene_index=0,
        intent_label="statistic",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=3.0,
        spoken_text="statistic counter proof metric numbers",
    )
    # Force aspect ratio mismatch on rui-stat-card (supports 16:9, but requested is 9:16)
    res = reuse_engine.evaluate(
        scene_intent=si,
        aspect_ratio="9:16",
        template_aspect_overrides={"rui-stat-card": ["16:9"]},
    )
    stat_score = next(c for c in res.ranked_candidates if c.template_id == "rui-stat-card")
    assert stat_score.eligible is False
    assert stat_score.fit_score == 0.0
    assert stat_score.sufficient is False
    assert len(stat_score.hard_filter_failures) > 0
    assert any("Aspect ratio mismatch" in f for f in stat_score.hard_filter_failures)
    assert res.selected_candidate != "rui-stat-card"


def test_reuse_engine_ranking_ablation_intent_vs_lexical(reuse_engine: ReuseEngine):
    """
    Ranking targeted test:
    Template A has high lexical token overlap with query words, but wrong creative/content intent.
    Template B has the correct creative/content intent, with weaker token overlap.
    After both pass hard filters, Template B (semantically correct) ranks higher than Template A.
    """
    si = SceneIntent(
        scene_id="sc_ablation_test",
        scene_index=0,
        intent_label="statistic",
        mood="Technical",
        motion_personality="Cinematic",
        primary_visual_job="proof",
        estimated_duration_sec=3.0,
        spoken_text="terminal code commit syntax deploy",  # High lexical overlap with code-reveal
    )
    res = reuse_engine.evaluate(scene_intent=si, aspect_ratio="9:16")

    score_stat = next(c for c in res.ranked_candidates if c.template_id == "rui-stat-card")
    score_code = next(c for c in res.ranked_candidates if c.template_id == "rui-code-reveal")

    # Both passed hard compatibility
    assert score_stat.eligible is True
    assert score_code.eligible is True

    # Semantically correct intent template (rui-stat-card) ranks higher than superficial lexical match
    assert score_stat.fit_score > score_code.fit_score
    assert score_stat.score_breakdown["content_fit"] > score_code.score_breakdown["content_fit"]
    assert res.selected_candidate in ("rui-stat-card", "rui-metric-ticker")
    assert res.selected_candidate != "rui-code-reveal"

