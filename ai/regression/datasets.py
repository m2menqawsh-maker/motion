"""
ai/regression/datasets.py
=========================
Canonical Evaluation Dataset Inventory for Creative Regression Suite (S28-08B).

Provides authoritative CreativeEvalCases across all 13 required categories:
1. INTENT (Multilingual, short, vague, detailed, contradictory, provenance)
2. KNOWLEDGE_RETRIEVAL (Precision@K, Recall@K, MRR, metadata filtering, semantic ranking)
3. SKILL_ROUTING (Required skills present, irrelevant absent, forbidden absent)
4. RECIPE_SELECTION (Hard eligibility, platform, audio mode, speech prerequisite)
5. AUDIO_MODE (SILENT, MUSIC_ONLY, VO_MUSIC, zero audio leakage)
6. NARRATIVE (Logical flow, hook relevance, duration fit, redundancy)
7. TASTE (Overdesign avoidance, visual intent, emotional fit, exception waivers)
8. CREATIVE_PLAN (Brief coverage, beat coverage, duration fit, schema validity, determinism)
9. TEMPLATE_SELECTION (REUSE retrieval, aspect filtering, props compatibility)
10. TIER_SELECTION (REUSE -> COMPOSE -> CREATE progression, anti-bypass)
11. COMPOSITION (Lego feasibility, registered components only, layer bindings)
12. CANDIDATE_DECISION (Separation of duties, AI approval blocked, lifecycle progression)
13. STYLE_ADHERENCE (Current request wins, brand > inferred, local != global rule)

Includes deliberately bad cases (negative gates) to prove the regression suite detects regressions.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.regression import (
    CreativeEvalCase,
    EvalCategory,
    EvalSeverity,
    GradingMethod,
    TraceAssertion,
    TraceAssertionType,
)


def get_all_creative_eval_cases() -> List[CreativeEvalCase]:
    """Returns the complete, authoritative creative regression evaluation cases."""
    cases: List[CreativeEvalCase] = []
    cases.extend(get_intent_cases())
    cases.extend(get_knowledge_retrieval_cases())
    cases.extend(get_skill_routing_cases())
    cases.extend(get_recipe_selection_cases())
    cases.extend(get_audio_mode_cases())
    cases.extend(get_narrative_cases())
    cases.extend(get_taste_cases())
    cases.extend(get_creative_plan_cases())
    cases.extend(get_template_selection_cases())
    cases.extend(get_tier_selection_cases())
    cases.extend(get_composition_cases())
    cases.extend(get_candidate_decision_cases())
    cases.extend(get_style_adherence_cases())
    return cases


# ============================================================================
# 1. INTENT EVAL CASES
# ============================================================================

def get_intent_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="intent_01_arabic_explicit_saas",
            category=EvalCategory.INTENT,
            tags=["arabic", "explicit", "saas"],
            input_fixture={
                "user_request": "بدي ريل سريع لمنتج SaaS بدون تعليق صوتي بس موسيقى وستايل clean.",
                "workspace_constraints": {"target_platforms": ["instagram_reels"]},
            },
            expected_decisions={
                "video_type": "SAAS_DEMO",
                "audio_mode": "MUSIC_ONLY",
                "pace": "FAST",
                "style": "CLEAN",
                "provenance_video_type": "EXPLICIT",
                "provenance_audio_mode": "EXPLICIT",
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="intent_02_english_detailed_explainer",
            category=EvalCategory.INTENT,
            tags=["english", "detailed", "explainer"],
            input_fixture={
                "user_request": "Create a 30s explainer video for technical architects about cloud scaling with voiceover and background music.",
                "workspace_constraints": {"target_platforms": ["youtube"]},
            },
            expected_decisions={
                "video_type": "EXPLAINER",
                "audio_mode": "VO_MUSIC",
                "target_duration_seconds": 30.0,
                "provenance_video_type": "EXPLICIT",
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="intent_03_mixed_language_kinetic",
            category=EvalCategory.INTENT,
            tags=["mixed", "short", "colors"],
            input_fixture={
                "user_request": "عمل montage ad سريع للـ product مع BGM only وألوان #FF5733 و#1E3A8A",
            },
            expected_decisions={
                "audio_mode": "MUSIC_ONLY",
                "detected_language": "MIXED",
            },
            allowed_outputs=["DYNAMIC_MONTAGE", "PRODUCT_AD", "montage", "ad"],
            grading_method=GradingMethod.SET_MEMBERSHIP,
            severity=EvalSeverity.MAJOR,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="intent_04_vague_preserves_uncertainty",
            category=EvalCategory.INTENT,
            tags=["vague", "epistemic_safety"],
            input_fixture={
                "user_request": "بدي فيديو تسويقي ممتاز للشركة",
            },
            expected_decisions={
                "provenance_video_type": "UNKNOWN",
                "provenance_audio_mode": "DEFAULTED",
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        # Adversarial / Contradictory negative gate
        CreativeEvalCase(
            case_id="intent_05_contradictory_silent_vs_vo",
            category=EvalCategory.INTENT,
            tags=["contradictory", "negative_gate", "adversarial"],
            input_fixture={
                "user_request": "فيديو صامت بدون صوت نهائياً واعمل فيه تعليق صوتي احترافي",
            },
            expected_decisions={
                "has_contradiction": True,
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="adversarial",
        ),
    ]


# ============================================================================
# 2. KNOWLEDGE RETRIEVAL EVAL CASES
# ============================================================================

def get_knowledge_retrieval_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="know_retrieval_01_spoken_vo_playbook",
            category=EvalCategory.KNOWLEDGE_RETRIEVAL,
            tags=["knowledge", "voiceover", "retrieval"],
            input_fixture={
                "query": "conversational narration script voiceover cadence speech pauses",
                "category": "SOP",
            },
            allowed_outputs=["know_sop_spoken_vo", "know_playbook_video_copy"],
            forbidden_outputs=["know_sop_audio_mastering_silent", "know_sop_sports_highlight"],
            grading_method=GradingMethod.RANKING_RETRIEVAL,
            retrieval_k=3,
            min_precision_at_k=0.33,
            min_recall_at_k=0.50,
            min_mrr=0.50,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="know_retrieval_02_video_architecture_spec",
            category=EvalCategory.KNOWLEDGE_RETRIEVAL,
            tags=["knowledge", "engineering", "retrieval"],
            input_fixture={
                "query": "Remotion composition structure sequence layout safe zones",
                "category": "ENGINEERING_GUIDE",
            },
            allowed_outputs=["know_eng_remotion"],
            forbidden_outputs=["know_recipe_avatar_explainer"],
            grading_method=GradingMethod.RANKING_RETRIEVAL,
            retrieval_k=3,
            min_precision_at_k=0.33,
            min_mrr=0.50,
            severity=EvalSeverity.MAJOR,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="know_retrieval_03_wrong_metadata_exclusion",
            category=EvalCategory.KNOWLEDGE_RETRIEVAL,
            tags=["knowledge", "metadata_filter", "negative_gate"],
            input_fixture={
                "query": "audio mastering cadence",
                "category": "NON_EXISTENT_CATEGORY",
            },
            allowed_outputs=[],  # Expecting zero results for mismatched metadata
            grading_method=GradingMethod.RANKING_RETRIEVAL,
            retrieval_k=3,
            min_precision_at_k=1.0,  # Empty top-k yields 1.0
            severity=EvalSeverity.CRITICAL,
            source="adversarial",
        ),
    ]


# ============================================================================
# 3. SKILL ROUTING EVAL CASES
# ============================================================================

def get_skill_routing_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="skill_routing_01_music_only_excludes_vo",
            category=EvalCategory.SKILL_ROUTING,
            tags=["skills", "music_only", "eligibility"],
            input_fixture={
                "intent": "Assemble an energetic music montage ad with fast rhythmic cuts and beat sync",
                "video_type": "montage",
                "audio_mode": "MUSIC_ONLY",
                "max_skills": 3,
            },
            allowed_outputs=["skill_dynamic_montage"],
            forbidden_outputs=["skill_spoken_vo_humanizer"],
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_EXISTS,
                    target_event_or_span="skill_selected",
                    expected_value="skill_dynamic_montage",
                    description="Dynamic montage skill must be routed",
                ),
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_ABSENT,
                    target_event_or_span="skill_selected",
                    expected_value="skill_spoken_vo_humanizer",
                    description="VO humanizer must be excluded under MUSIC_ONLY",
                ),
            ],
            grading_method=GradingMethod.TRACE_ASSERTION,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="skill_routing_02_explainer_selects_vo_skill",
            category=EvalCategory.SKILL_ROUTING,
            tags=["skills", "vo_music", "explainer"],
            input_fixture={
                "intent": "Humanize conversational narration script and voiceover cadence for a SaaS explainer",
                "video_type": "explainer",
                "audio_mode": "VO_MUSIC",
                "max_skills": 3,
            },
            allowed_outputs=["skill_spoken_vo_humanizer"],
            forbidden_outputs=[],
            grading_method=GradingMethod.SET_MEMBERSHIP,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="skill_routing_03_bounded_selection",
            category=EvalCategory.SKILL_ROUTING,
            tags=["skills", "bounding"],
            input_fixture={
                "intent": "Create an avatar video explainer with kinetic captions and b-roll",
                "max_skills": 2,
            },
            expected_constraints={"max_selected_count": 2},
            grading_method=GradingMethod.RANGE,
            severity=EvalSeverity.MAJOR,
            source="canonical_golden",
        ),
    ]


# ============================================================================
# 4. RECIPE SELECTION EVAL CASES
# ============================================================================

def get_recipe_selection_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="recipe_01_music_only_selects_montage",
            category=EvalCategory.RECIPE_SELECTION,
            tags=["recipe", "music_only"],
            input_fixture={
                "user_request": "بدي ريل سريع لمنتج SaaS بدون تعليق صوتي بس موسيقى",
                "platform": "instagram_reels",
            },
            allowed_outputs=["dynamic-montage-ad", "faceless-broll-ad", "motion-collage-explainer"],
            forbidden_outputs=["captioned-talking-head", "avatar-explainer"],
            grading_method=GradingMethod.SET_MEMBERSHIP,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="recipe_02_talking_head_requires_speech_media",
            category=EvalCategory.RECIPE_SELECTION,
            tags=["recipe", "talking_head", "prerequisite"],
            input_fixture={
                "user_request": "ريلز لحديث الكاميرا مع مؤسس الشركة ولكن بدون ملفات صوتية مرفوعة",
                "platform": "instagram_reels",
                "has_source_speech_media": False,
            },
            forbidden_outputs=["captioned-talking-head"],
            grading_method=GradingMethod.SET_MEMBERSHIP,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        # Deliberately bad: avatar explainer under MUSIC_ONLY
        CreativeEvalCase(
            case_id="recipe_03_deliberate_bad_music_only_tts_recipe",
            category=EvalCategory.RECIPE_SELECTION,
            tags=["recipe", "negative_gate", "deliberately_bad"],
            input_fixture={
                "user_request": "أريد فيديو أفاتار توضيحي avatar explainer يشرح ميزات المنصة بدون أي صوت متحدث بس موسيقى فقط",
                "platform": "youtube",
            },
            forbidden_outputs=["avatar-explainer", "avatar-product-walkthrough"],
            is_deliberately_bad=True,
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_ABSENT,
                    target_event_or_span="recipe_selected",
                    expected_value="avatar-explainer",
                    description="Avatar recipe requires TTS and cannot be selected under MUSIC_ONLY",
                ),
            ],
            grading_method=GradingMethod.TRACE_ASSERTION,
            severity=EvalSeverity.BLOCKER,
            source="adversarial",
        ),
    ]


# ============================================================================
# 5. AUDIO MODE EVAL CASES
# ============================================================================

def get_audio_mode_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="audio_01_silent_mode_zero_audio_tools",
            category=EvalCategory.AUDIO_MODE,
            tags=["audio", "silent", "zero_leakage"],
            input_fixture={
                "user_request": "فيديو صامت تماماً لشرح الواجهة بدون صوت وبدون موسيقى",
                "audio_mode": "SILENT",
            },
            expected_decisions={
                "audio_mode": "SILENT",
                "spoken_text_present": False,
                "audio_intent": "silent_mode_no_audio",
            },
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_ABSENT,
                    target_event_or_span="tool_invoked",
                    field_path="tool",
                    forbidden_values=["tts_generate", "voiceover_synthesis", "music_generate", "sfx_generate"],
                    description="SILENT mode must never invoke audio generation tools",
                ),
            ],
            grading_method=GradingMethod.TRACE_ASSERTION,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="audio_02_music_only_no_spoken_dialogue",
            category=EvalCategory.AUDIO_MODE,
            tags=["audio", "music_only", "no_dialogue"],
            input_fixture={
                "user_request": "مقطع استعراضي موسيقي فقط بدون كلام",
                "audio_mode": "MUSIC_ONLY",
            },
            expected_decisions={
                "audio_mode": "MUSIC_ONLY",
                "spoken_text_present": False,
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
    ]


# ============================================================================
# 6. NARRATIVE EVAL CASES
# ============================================================================

def get_narrative_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="narrative_01_golden_saas_arc",
            category=EvalCategory.NARRATIVE,
            tags=["narrative", "golden", "saas"],
            input_fixture={
                "video_type": "SAAS_DEMO",
                "duration": 30.0,
                "goal": "Enterprise Cloud Orchestration Platform",
            },
            rubric_thresholds={
                "narrative_coherence": 0.70,
                "hook_relevance": 0.70,
                "duration_fit": 0.80,
            },
            grading_method=GradingMethod.RUBRIC_SCORE,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        # Deliberately bad: weak hook
        CreativeEvalCase(
            case_id="narrative_02_deliberate_bad_weak_hook",
            category=EvalCategory.NARRATIVE,
            tags=["narrative", "negative_gate", "deliberately_bad"],
            input_fixture={
                "core_hook": "Hello world this is some video",
                "phase": "generic",
            },
            rubric_thresholds={
                "hook_relevance": 0.70,
            },
            is_deliberately_bad=True,
            grading_method=GradingMethod.RUBRIC_SCORE,
            severity=EvalSeverity.MAJOR,
            source="adversarial",
        ),
    ]


# ============================================================================
# 7. TASTE EVAL CASES
# ============================================================================

def get_taste_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="taste_01_silent_waives_gestural_audio",
            category=EvalCategory.TASTE,
            tags=["taste", "silent", "exception_waiver"],
            input_fixture={
                "rule_id": "rule_gestural_audio_sync",
                "audio_mode": "SILENT",
            },
            expected_decisions={
                "is_applicable": False,
                "waived_by_exception": "AudioMode is SILENT",
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.MAJOR,
            source="canonical_golden",
        ),
        # Deliberately bad: unceasing explosive motion
        CreativeEvalCase(
            case_id="taste_02_deliberate_bad_constant_explosive_motion",
            category=EvalCategory.TASTE,
            tags=["taste", "negative_gate", "deliberately_bad", "overdesign"],
            input_fixture={
                "motion_energies": ["explosive", "explosive", "explosive", "explosive"],
            },
            rubric_thresholds={
                "overdesign_avoidance": 0.70,
            },
            is_deliberately_bad=True,
            grading_method=GradingMethod.RUBRIC_SCORE,
            severity=EvalSeverity.CRITICAL,
            source="adversarial",
        ),
    ]


# ============================================================================
# 8. CREATIVE PLAN EVAL CASES
# ============================================================================

def get_creative_plan_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="plan_01_brief_and_beat_coverage",
            category=EvalCategory.CREATIVE_PLAN,
            tags=["plan", "coverage", "validator"],
            input_fixture={
                "scenario": "sc_01_saas_demo",
                "video_type": "SAAS_DEMO",
                "duration": 30.0,
                "audio_mode": "VO_MUSIC",
            },
            expected_constraints={
                "brief_coverage": 1.0,
                "schema_valid": True,
                "status": "PROPOSED",
            },
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_EXISTS,
                    target_event_or_span="creative_plan_validated",
                    expected_value="VALID",
                    description="Creative plan must be schema valid and structurally intact",
                ),
            ],
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="plan_02_blueprint_compiler_determinism",
            category=EvalCategory.CREATIVE_PLAN,
            tags=["plan", "compiler", "determinism"],
            input_fixture={
                "repeat_runs": 3,
                "scenario": "sc_01_saas_demo",
            },
            expected_decisions={
                "equality_rate": 1.0,
                "unique_structural_hashes": 1,
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
    ]


# ============================================================================
# 9. TEMPLATE SELECTION EVAL CASES
# ============================================================================

def get_template_selection_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="template_01_counter_retrieval",
            category=EvalCategory.TEMPLATE_SELECTION,
            tags=["template", "reuse", "retrieval"],
            input_fixture={
                "intent_label": "statistic",
                "spoken_text": "Over 10,000 teams use this daily.",
                "required_aspect": "9:16",
            },
            allowed_outputs=["animatedcounter-element", "rui-stat-card", "rui-metric-ticker"],
            forbidden_outputs=["rui-talking-head-layout", "rui-code-reveal"],
            grading_method=GradingMethod.RANKING_RETRIEVAL,
            retrieval_k=3,
            min_precision_at_k=0.33,
            min_recall_at_k=0.33,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="template_02_aspect_filter_exclusion",
            category=EvalCategory.TEMPLATE_SELECTION,
            tags=["template", "aspect_filter", "negative_gate"],
            input_fixture={
                "intent_label": "code_demo",
                "required_aspect": "16:9",
                "template_aspect_overrides": {"rui-code-accordion": ["9:16"]},
            },
            forbidden_outputs=["rui-code-accordion"],
            grading_method=GradingMethod.SET_MEMBERSHIP,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
    ]


# ============================================================================
# 10. TIER SELECTION EVAL CASES
# ============================================================================

def get_tier_selection_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="tier_01_progression_order",
            category=EvalCategory.TIER_SELECTION,
            tags=["tier", "order", "trace_grading"],
            input_fixture={
                "scene_intent": "statistic",
            },
            expected_decisions={
                "selected_tier": "REUSE",
            },
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.ORDERED_BEFORE,
                    target_event_or_span="reuse_evaluation",
                    secondary_target="compose_evaluation",
                    description="REUSE must be evaluated before COMPOSE",
                ),
            ],
            grading_method=GradingMethod.TRACE_ASSERTION,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        # Deliberately bad: CREATE chosen when matching REUSE exists
        CreativeEvalCase(
            case_id="tier_02_deliberate_bad_create_bypasses_reuse",
            category=EvalCategory.TIER_SELECTION,
            tags=["tier", "anti_bypass", "negative_gate", "deliberately_bad"],
            input_fixture={
                "scene_intent": "statistic",
                "requested_tier": "CREATE",
                "matching_reuse_exists": True,
            },
            expected_decisions={
                "selected_tier": "REUSE",  # Policy must force REUSE
                "bypass_denied": True,
            },
            is_deliberately_bad=True,
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_ABSENT,
                    target_event_or_span="tier_selected",
                    expected_value="CREATE",
                    description="CREATE must be rejected when valid REUSE template exists",
                ),
            ],
            grading_method=GradingMethod.TRACE_ASSERTION,
            severity=EvalSeverity.BLOCKER,
            source="adversarial",
        ),
    ]


# ============================================================================
# 11. COMPOSITION EVAL CASES
# ============================================================================

def get_composition_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="compose_01_badge_over_layout",
            category=EvalCategory.COMPOSITION,
            tags=["compose", "lego", "feasibility"],
            input_fixture={
                "intent_label": "stat_with_badge",
                "primary_visual_job": "proof",
                "audio_mode": "VO_MUSIC",
            },
            expected_decisions={
                "is_composable": True,
                "used_registered_components_only": True,
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        # Negative case: force unknown component
        CreativeEvalCase(
            case_id="compose_02_deliberate_bad_unknown_lego_component",
            category=EvalCategory.COMPOSITION,
            tags=["compose", "negative_gate", "deliberately_bad"],
            input_fixture={
                "force_unknown_component": "totally-fake-unregistered-layer-xyz",
            },
            expected_decisions={
                "is_composable": False,
            },
            is_deliberately_bad=True,
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="adversarial",
        ),
    ]


# ============================================================================
# 12. CANDIDATE DECISION EVAL CASES
# ============================================================================

def get_candidate_decision_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="candidate_01_separation_of_duties",
            category=EvalCategory.CANDIDATE_DECISION,
            tags=["candidate", "governance", "separation_of_duties"],
            input_fixture={
                "creator_principal": "usr_creator_01",
                "reviewer_principal": "usr_creator_01",  # Same principal!
            },
            expected_decisions={
                "approval_allowed": False,
                "error": "CandidateAuthorityError",
            },
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_ABSENT,
                    target_event_or_span="candidate_approved",
                    description="Creator cannot approve own candidate",
                ),
            ],
            grading_method=GradingMethod.TRACE_ASSERTION,
            severity=EvalSeverity.BLOCKER,
            source="adversarial",
        ),
        CreativeEvalCase(
            case_id="candidate_02_ai_principal_cannot_approve",
            category=EvalCategory.CANDIDATE_DECISION,
            tags=["candidate", "governance", "ai_boundary"],
            input_fixture={
                "reviewer_principal": "service_ai_worker",
                "principal_type": "SERVICE",
            },
            expected_decisions={
                "approval_allowed": False,
                "error": "CandidateAuthorityError",
            },
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_ABSENT,
                    target_event_or_span="candidate_approved",
                    description="Non-human principal cannot approve template candidates",
                ),
            ],
            grading_method=GradingMethod.TRACE_ASSERTION,
            severity=EvalSeverity.BLOCKER,
            source="adversarial",
        ),
        CreativeEvalCase(
            case_id="candidate_03_draft_cannot_bypass_validation",
            category=EvalCategory.CANDIDATE_DECISION,
            tags=["candidate", "lifecycle", "negative_gate"],
            input_fixture={
                "initial_status": "DRAFT",
                "attempt_direct_action": "PROMOTE",
            },
            expected_decisions={
                "allowed": False,
                "error": "CandidateInvalidStatusError",
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.BLOCKER,
            source="adversarial",
        ),
    ]


# ============================================================================
# 13. STYLE ADHERENCE EVAL CASES (S28-08A INTEGRATION)
# ============================================================================

def get_style_adherence_cases() -> List[CreativeEvalCase]:
    return [
        CreativeEvalCase(
            case_id="style_01_current_request_overrides_stored_preference",
            category=EvalCategory.STYLE_ADHERENCE,
            tags=["style", "personalization", "precedence", "critical_gate"],
            input_fixture={
                "stored_profile": {
                    "pacing_preference": "fast",
                    "motion_intensity": "high",
                    "music_tendencies": "energetic",
                },
                "current_request": "اعمل الفيديو هادئ، حركة بسيطة، بدون موسيقى",
                "audio_mode": "SILENT",
            },
            expected_decisions={
                "effective_pacing": "calm",
                "effective_motion_intensity": "low",
                "effective_music_preference": "none",
                "winning_source_pacing": "CURRENT_REQUEST",
                "is_overridden_pacing": True,
            },
            trace_assertions=[
                TraceAssertion(
                    assertion_type=TraceAssertionType.EVENT_EXISTS,
                    target_event_or_span="style_pacing_resolved",
                    field_path="winning_source",
                    expected_value="CURRENT_REQUEST",
                    description="Current explicit request must win over stored preference",
                ),
                TraceAssertion(
                    assertion_type=TraceAssertionType.SELECTED_VALUE_EQUALS,
                    target_event_or_span="style_pacing_resolved",
                    field_path="is_overridden",
                    expected_value=True,
                    description="Overridden flag must be True when request supersedes preference",
                ),
            ],
            grading_method=GradingMethod.TRACE_ASSERTION,
            severity=EvalSeverity.BLOCKER,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="style_02_brand_constraint_overrides_inferred_preference",
            category=EvalCategory.STYLE_ADHERENCE,
            tags=["style", "brand", "precedence"],
            input_fixture={
                "stored_profile": {
                    "visual_complexity": "rich",
                    "provenance": {"visual_complexity": "INFERRED"},
                },
                "brand_constraints": {
                    "visual_complexity": "minimal",
                },
                "current_request": "video about product",
            },
            expected_decisions={
                "effective_visual_complexity": "minimal",
                "winning_source": "BRAND_CONSTRAINT",
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
        CreativeEvalCase(
            case_id="style_03_single_scene_critique_not_permanent_global_rule",
            category=EvalCategory.STYLE_ADHERENCE,
            tags=["style", "learning", "memory_policy"],
            input_fixture={
                "raw_feedback": "هذا المشهد حركته كثيرة",
                "target_type": "SCENE",
            },
            expected_decisions={
                "confidence": 0.4,
                "is_explicit_general_rule": False,
                "action": "REQUIRE_CONFIRMATION",
                "direct_write": False,
            },
            grading_method=GradingMethod.EXACT,
            severity=EvalSeverity.CRITICAL,
            source="canonical_golden",
        ),
    ]
