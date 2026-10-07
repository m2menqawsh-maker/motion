"""
ai/evals/creative_datasets_s28_06.py
====================================
Authoritative evaluation datasets for S28-06:
- Template Retrieval Ground Truth Dataset (Precision@K, Recall@K, Aspect, Props, Media, AudioMode)
- Composition Evaluation Ground Truth Dataset (Feasibility, Lego validation, Layer bindings)
- Deterministic 3-Tier Policy Evaluation Dataset (REUSE, COMPOSE, CREATE escalation, Anti-Bypass)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import Field

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.contracts.base import AIContractModel
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import CreativeTier, SceneIntent


class TemplateRetrievalEvalCase(AIContractModel):
    """Evaluation case measuring REUSE template retrieval and filtering quality (Section 53)."""
    case_id: str = Field(description="Unique case identifier")
    description: str = Field(description="Purpose of the test case")
    scene_intent: SceneIntent = Field(description="Input SceneIntent under evaluation")
    required_aspect: str = Field(default="9:16", description="Target aspect ratio")
    audio_mode: Optional[AudioMode] = Field(default=None, description="Active AudioMode")
    required_props: Optional[List[str]] = Field(default=None, description="Explicit required schema properties")
    required_media: Optional[List[str]] = Field(default=None, description="Explicit required media capabilities")
    acceptable_templates: List[str] = Field(description="Ground truth acceptable template canonical IDs")
    unacceptable_templates: List[str] = Field(default_factory=list, description="Ground truth unacceptable IDs")
    expected_family: Optional[str] = Field(default=None, description="Expected template family")
    template_aspect_overrides: Optional[Dict[str, List[str]]] = Field(default=None, description="Synthetic aspect overrides for testing")


class CompositionEvalCase(AIContractModel):
    """Evaluation case measuring COMPOSE engine feasibility and Lego validation (Section 55)."""
    case_id: str = Field(description="Unique case identifier")
    description: str = Field(description="Purpose of the test case")
    scene_intent: SceneIntent = Field(description="Input SceneIntent under evaluation")
    audio_mode: Optional[AudioMode] = Field(default=None, description="Active AudioMode")
    aspect_ratio: str = Field(default="9:16", description="Target aspect ratio")
    expected_composable: bool = Field(description="Whether registered Lego can satisfy the intent")
    expected_base_anchor: Optional[str] = Field(default=None, description="Expected base layout template")
    expected_layers: List[str] = Field(default_factory=list, description="Expected registered layers")
    force_unknown_component: Optional[str] = Field(default=None, description="Injected unknown component for negative test")


class TierPolicyEvalCase(AIContractModel):
    """Evaluation case measuring Tier Policy transitions and Anti-Bypass enforcement (Section 87)."""
    case_id: str = Field(description="Unique case identifier")
    description: str = Field(description="Purpose of the test case")
    scene_intent: SceneIntent = Field(description="Input SceneIntent under evaluation")
    requested_tier: Optional[CreativeTier] = Field(default=None, description="Caller/planner requested tier (for bypass tests)")
    expected_tier: CreativeTier = Field(description="Machine-enforced expected selected tier")
    expected_template_or_anchor: Optional[str] = Field(default=None, description="Expected template ref or base anchor")
    is_bypass_attempt: bool = Field(default=False, description="Whether this case tests anti-bypass denial")
    aspect_ratio: str = Field(default="9:16")
    audio_mode: Optional[AudioMode] = Field(default=None)


def get_template_retrieval_dataset() -> List[TemplateRetrievalEvalCase]:
    """Returns the comprehensive benchmark evaluation dataset for REUSE Template Retrieval."""
    return [
        TemplateRetrievalEvalCase(
            case_id="retrieval_01_metric_counter",
            description="Numeric metric callout retrieves stat-card or counter templates",
            scene_intent=SceneIntent(
                scene_id="sc_ret_01",
                scene_index=0,
                intent_label="statistic",
                mood="Technical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=4.0,
                spoken_text="Over 10,000 teams use this daily.",
                template_requirements=["numbers"],
            ),
            acceptable_templates=["animatedcounter-element", "rui-stat-card", "rui-metric-ticker"],
            unacceptable_templates=["rui-talking-head-layout", "rui-code-reveal"],
            expected_family="stat_card",
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_02_code_showcase",
            description="Code reveal intent retrieves code accordion, code reveal, or code diff wipe",
            scene_intent=SceneIntent(
                scene_id="sc_ret_02",
                scene_index=1,
                intent_label="code_demo",
                mood="Technical",
                motion_personality="Technical",
                primary_visual_job="mechanism",
                estimated_duration_sec=5.0,
                spoken_text="One line of code automates everything.",
                template_requirements=["code"],
            ),
            acceptable_templates=["rui-code-accordion", "rui-code-diff-wipe", "rui-code-reveal", "codeblock-element"],
            unacceptable_templates=["rui-audiogram-scene", "rui-sports-scorebug"],
            expected_family="code",
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_03_attention_hook",
            description="Attention hook intent retrieves hook-card or intro templates",
            scene_intent=SceneIntent(
                scene_id="sc_ret_03",
                scene_index=0,
                intent_label="hook",
                mood="Energetic",
                motion_personality="Energetic",
                primary_visual_job="action",
                estimated_duration_sec=3.0,
                spoken_text="Are you still doing video editing manually?",
                template_requirements=["headline"],
            ),
            acceptable_templates=["rui-hook-card", "rui-intro", "rui-title-card"],
            unacceptable_templates=["rui-faq-accordion", "rui-kanban-move"],
            expected_family="hook",
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_04_data_comparison_chart",
            description="Data comparison retrieves animated bar chart or comparison table",
            scene_intent=SceneIntent(
                scene_id="sc_ret_04",
                scene_index=2,
                intent_label="comparison",
                mood="Corporate",
                motion_personality="Cinematic",
                primary_visual_job="comparison",
                estimated_duration_sec=4.5,
                spoken_text="See the 4x performance difference.",
                template_requirements=["chart"],
            ),
            acceptable_templates=["rui-animated-bar-chart", "rui-comparison-table"],
            unacceptable_templates=["rui-talking-head-layout", "rui-podcast-clip"],
            expected_family="data",
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_05_cta_outro",
            description="Call to action retrieves end-card or callout spotlight",
            scene_intent=SceneIntent(
                scene_id="sc_ret_05",
                scene_index=3,
                intent_label="cta",
                mood="Energetic",
                motion_personality="Energetic",
                primary_visual_job="action",
                estimated_duration_sec=3.5,
                spoken_text="Start building with our platform today.",
                template_requirements=["call_to_action"],
            ),
            acceptable_templates=["rui-end-card", "rui-callout-spotlight"],
            unacceptable_templates=["codeblock-element", "matrixrain-element"],
            expected_family="cta",
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_06_talking_head_vlog",
            description="Talking head presenter intent retrieves talking-head-layout",
            scene_intent=SceneIntent(
                scene_id="sc_ret_06",
                scene_index=0,
                intent_label="talking_head",
                mood="Conversational",
                motion_personality="Cinematic",
                primary_visual_job="presenter",
                estimated_duration_sec=6.0,
                spoken_text="Welcome back to our weekly development sprint update.",
                template_requirements=["speaker"],
            ),
            acceptable_templates=["rui-talking-head-layout", "rui-creator-reel"],
            unacceptable_templates=["rui-code-reveal", "rui-terminal-simulator"],
            expected_family="talking_head",
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_07_audiogram_clip",
            description="Speech audiogram retrieves audiogram scene with audio wave",
            scene_intent=SceneIntent(
                scene_id="sc_ret_07",
                scene_index=1,
                intent_label="audiogram",
                mood="Conversational",
                motion_personality="Dynamic",
                primary_visual_job="speech",
                estimated_duration_sec=5.0,
                spoken_text="Listen to what the founders had to say about AI automation.",
                template_requirements=["audio_spectrum"],
            ),
            acceptable_templates=["rui-audiogram-scene", "rui-podcast-clip"],
            unacceptable_templates=["matrixrain-element", "codeblock-element"],
            expected_family="audiogram",
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_08_aspect_mismatch_negative",
            description="Target 9:16 excludes template restricted to 16:9 only",
            scene_intent=SceneIntent(
                scene_id="sc_ret_08",
                scene_index=0,
                intent_label="statistic",
                mood="Technical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=4.0,
            ),
            required_aspect="9:16",
            template_aspect_overrides={"rui-stat-card": ["16:9"]},
            acceptable_templates=["animatedcounter-element", "rui-metric-ticker"],
            unacceptable_templates=["rui-stat-card"],
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_09_audio_mode_music_only_negative",
            description="MUSIC_ONLY mode excludes spoken-word audiogram templates",
            scene_intent=SceneIntent(
                scene_id="sc_ret_09",
                scene_index=0,
                intent_label="audiogram",
                mood="Energetic",
                motion_personality="Cinematic",
                primary_visual_job="action",
                estimated_duration_sec=4.0,
                template_requirements=["audio_spectrum"],
            ),
            audio_mode=AudioMode.MUSIC_ONLY,
            acceptable_templates=[],  # Audiogram should be rejected
            unacceptable_templates=["rui-audiogram-scene", "rui-podcast-clip"],
        ),
        TemplateRetrievalEvalCase(
            case_id="retrieval_10_unsupported_props_negative",
            description="Missing required prop excludes candidate",
            scene_intent=SceneIntent(
                scene_id="sc_ret_10",
                scene_index=0,
                intent_label="hook",
                mood="Energetic",
                motion_personality="Energetic",
                primary_visual_job="action",
                estimated_duration_sec=3.0,
            ),
            required_props=["non_existent_specialized_prop_xyz"],
            acceptable_templates=[],  # Zero templates have this prop
            unacceptable_templates=["rui-hook-card", "rui-intro"],
        ),
    ]


def get_composition_eval_dataset() -> List[CompositionEvalCase]:
    """Returns the benchmark evaluation dataset for COMPOSE synthesis and validation."""
    return [
        CompositionEvalCase(
            case_id="compose_01_split_comparison",
            description="Side-by-side comparison composed from split screen, animated text, and stat card",
            scene_intent=SceneIntent(
                scene_id="sc_comp_01",
                scene_index=1,
                intent_label="split_comparison",
                mood="Analytical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=5.0,
                spoken_text="Side by side code comparison.",
                template_requirements=["split_side_by_side_comparison"],
            ),
            expected_composable=True,
            expected_base_anchor="rui-split-screen",
            expected_layers=["animatedtext-element", "rui-stat-card"],
        ),
        CompositionEvalCase(
            case_id="compose_02_code_metric_split",
            description="Live code split composed with syntax block and latency counter",
            scene_intent=SceneIntent(
                scene_id="sc_comp_02",
                scene_index=2,
                intent_label="code_demo",
                mood="Technical",
                motion_personality="Technical",
                primary_visual_job="mechanism",
                estimated_duration_sec=5.0,
                spoken_text="Watch the compilation in real time.",
                template_requirements=["code"],
            ),
            expected_composable=True,
            expected_base_anchor="rui-live-code-split",
            expected_layers=["codeblock-element", "animatedcounter-element"],
        ),
        CompositionEvalCase(
            case_id="compose_03_dashboard_populate",
            description="Metric dashboard composed with counter and gradient ambient backdrop",
            scene_intent=SceneIntent(
                scene_id="sc_comp_03",
                scene_index=3,
                intent_label="statistic",
                mood="Technical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=4.0,
                spoken_text="Scaling up to 500 operations per second.",
                template_requirements=["numbers"],
            ),
            expected_composable=True,
            expected_base_anchor="rui-dashboard-populate",
            expected_layers=["animatedcounter-element", "gradient-element"],
        ),
        CompositionEvalCase(
            case_id="compose_04_bento_feature_pan",
            description="Bento feature overview composed with text and spotlight callout",
            scene_intent=SceneIntent(
                scene_id="sc_comp_04",
                scene_index=4,
                intent_label="solution",
                mood="Modern",
                motion_personality="Cinematic",
                primary_visual_job="overview",
                estimated_duration_sec=6.0,
                spoken_text="A complete modular toolset at your fingertips.",
                template_requirements=["feature_walkthrough"],
            ),
            expected_composable=True,
            expected_base_anchor="rui-bento-pan",
            expected_layers=["animatedtext-element", "rui-callout-spotlight"],
        ),
        CompositionEvalCase(
            case_id="compose_05_unknown_component_violation",
            description="Injected unknown component in composition must fail validation closed",
            scene_intent=SceneIntent(
                scene_id="sc_comp_05",
                scene_index=5,
                intent_label="split_comparison",
                mood="Analytical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=5.0,
            ),
            expected_composable=False,
            force_unknown_component="fake-hacked-primitive-99",
        ),
        CompositionEvalCase(
            case_id="compose_06_impossible_need_outside_lego",
            description="Impossible custom requirement cannot be composed from Lego",
            scene_intent=SceneIntent(
                scene_id="sc_comp_06",
                scene_index=6,
                intent_label="novel_3d_simulation_quantum_field",
                mood="Mystical",
                motion_personality="Cinematic",
                primary_visual_job="quantum_interaction",
                estimated_duration_sec=5.0,
                template_requirements=["interactive_webgl_quantum_field"],
            ),
            expected_composable=False,
        ),
    ]


def get_tier_policy_eval_dataset() -> List[TierPolicyEvalCase]:
    """Returns the benchmark evaluation dataset for 3-Tier Policy decision making."""
    return [
        TierPolicyEvalCase(
            case_id="policy_01_reuse_standard_metric",
            description="Standard metric reveal selects REUSE tier",
            scene_intent=SceneIntent(
                scene_id="sc_pol_01",
                scene_index=0,
                intent_label="statistic",
                mood="Technical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=4.0,
            ),
            expected_tier=CreativeTier.REUSE,
            expected_template_or_anchor="animatedcounter-element",
        ),
        TierPolicyEvalCase(
            case_id="policy_02_compose_split_comparison",
            description="Composite split requirement selects COMPOSE tier",
            scene_intent=SceneIntent(
                scene_id="sc_pol_02",
                scene_index=1,
                intent_label="split_comparison",
                mood="Analytical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=5.0,
                template_requirements=["split_side_by_side_comparison"],
            ),
            expected_tier=CreativeTier.COMPOSE,
            expected_template_or_anchor="rui-split-screen",
        ),
        TierPolicyEvalCase(
            case_id="policy_03_create_escalation_impossible_need",
            description="Unsatisfiable need escalates to CREATE-needed without execution",
            scene_intent=SceneIntent(
                scene_id="sc_pol_03",
                scene_index=2,
                intent_label="novel_3d_simulation_quantum_field",
                mood="Mystical",
                motion_personality="Cinematic",
                primary_visual_job="quantum_physics",
                estimated_duration_sec=5.0,
                template_requirements=["interactive_webgl_quantum_field"],
            ),
            expected_tier=CreativeTier.CREATE,
        ),
        TierPolicyEvalCase(
            case_id="policy_04_anti_bypass_reuse_when_create_requested",
            description="Caller asks CREATE when REUSE available: policy denies and enforces REUSE",
            scene_intent=SceneIntent(
                scene_id="sc_pol_04",
                scene_index=0,
                intent_label="statistic",
                mood="Technical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=4.0,
            ),
            requested_tier=CreativeTier.CREATE,
            expected_tier=CreativeTier.REUSE,
            expected_template_or_anchor="animatedcounter-element",
            is_bypass_attempt=True,
        ),
        TierPolicyEvalCase(
            case_id="policy_05_anti_bypass_compose_when_create_requested",
            description="Caller asks CREATE when COMPOSE available: policy denies and enforces COMPOSE",
            scene_intent=SceneIntent(
                scene_id="sc_pol_05",
                scene_index=1,
                intent_label="split_comparison",
                mood="Analytical",
                motion_personality="Cinematic",
                primary_visual_job="proof",
                estimated_duration_sec=5.0,
                template_requirements=["split_side_by_side_comparison"],
            ),
            requested_tier=CreativeTier.CREATE,
            expected_tier=CreativeTier.COMPOSE,
            expected_template_or_anchor="rui-split-screen",
            is_bypass_attempt=True,
        ),
    ]
