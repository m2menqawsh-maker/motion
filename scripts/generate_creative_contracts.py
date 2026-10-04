#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_creative_contracts.py
======================================
Deterministic generator for Creative Intelligence Platform JSON Schemas and TypeScript contracts.

Authority Chain (S28-01):
    Pydantic Canonical Contracts (`ai/contracts/creative/*.py`)
                ↓
    JSON Schema (`schemas/creative/*.schema.json`)
                ↓
    TypeScript Types (`contracts/generated/creative_contracts.ts`, `remotion-app/src/types/creative_contracts.ts`)

Modes:
- Generation mode:   python scripts/generate_creative_contracts.py
- Verification mode: python scripts/generate_creative_contracts.py --check
  (Exits with code 1 if generated artifacts have drifted or are missing)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Type

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VENV_PY = ROOT / ".venv" / "bin" / "python"
if VENV_PY.exists() and Path(sys.executable) != VENV_PY:
    try:
        import pydantic
    except ImportError:
        os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)

from pydantic import BaseModel

from ai.contracts.creative import (
    AudioMode,
    BlueprintCompilationResult,
    CandidateGateResult,
    CandidatePromotionRecord,
    CandidateReviewBundle,
    CandidateReviewDecision,
    CandidateReviewVerdict,
    CandidateStatus,
    CandidateValidationReport,
    ComposeComponentRef,
    ComposeEvaluationResult,
    CompositionLayer,
    CompositionPlan,
    ConflictPrecedenceRank,
    ConflictSeverity,
    ConflictStatus,
    CreativeBrief,
    CreativeCaseGrade,
    CreativeConflict,
    CreativeConstraints,
    CreativeEvalCase,
    CreativeEvalRun,
    CreativeFeedback,
    CreativeIntent,
    CreativePlan,
    CreativePlanStatus,
    CreativePlanValidationResult,
    CreativeTier,
    CreativeTierDecision,
    DirectorRecommendationBundle,
    EmotionDirection,
    FieldProvenance,
    KnowledgeCategory,
    KnowledgeDescriptor,
    KnowledgeStatus,
    MotionDirection,
    NarrativeBeat,
    NarrativeDirection,
    NarrativePlan,
    PromotionDecision,
    PromotionManifest,
    PromotionRecordStatus,
    PromotionStatus,
    ProvenanceType,
    RecipeDefinition,
    RecipeSelection,
    RecipeStage,
    ResolvedCreativeGuidance,
    ResolvedTemplateDecision,
    ReuseCandidateScore,
    ReuseEvaluationResult,
    SceneIntent,
    SfxDirection,
    SkillDefinition,
    SkillStatus,
    TasteContext,
    TasteDecision,
    TasteRule,
    TasteRuleSeverity,
    TemplateCandidate,
    GateStatus,
    EffectiveUserStyle,
    EvalCategory,
    EvalSeverity,
    FeedbackCategory,
    FeedbackClassification,
    FeedbackSentiment,
    FeedbackTargetType,
    GradingMethod,
    JudgeCalibrationRecord,
    PairwiseGradeResult,
    StyleDecisionTrace,
    StylePreferenceProvenance,
    TraceAssertion,
    TraceAssertionResult,
    TraceAssertionType,
    UserStyleProfile,
    ValidationOverallResult,
    ValidationPhase,
    ValidationSnapshot,
    WinningSource,
    CostProvenance,
    CreativeCostAuditRun,
    CreativeProjectCostSummary,
    CreativeUsageEvent,
    EfficiencyFinding,
    EfficiencyFindingType,
    EfficiencySeverity,
    ThresholdProvenance,
)

SCHEMA_DIR = ROOT / "schemas" / "creative"
TS_OUTPUT_CONTRACTS = ROOT / "contracts" / "generated" / "creative_contracts.ts"
TS_OUTPUT_REMOTION = ROOT / "remotion-app" / "src" / "types" / "creative_contracts.ts"

CANONICAL_MODELS: Dict[str, Type[BaseModel]] = {
    "field_provenance": FieldProvenance,
    "creative_intent": CreativeIntent,
    "creative_constraints": CreativeConstraints,
    "creative_brief": CreativeBrief,
    "narrative_beat": NarrativeBeat,
    "narrative_plan": NarrativePlan,
    "skill_definition": SkillDefinition,
    "knowledge_descriptor": KnowledgeDescriptor,
    "recipe_stage": RecipeStage,
    "recipe_definition": RecipeDefinition,
    "recipe_selection": RecipeSelection,
    "taste_rule": TasteRule,
    "taste_decision": TasteDecision,
    "taste_context": TasteContext,
    "narrative_direction": NarrativeDirection,
    "motion_direction": MotionDirection,
    "emotion_direction": EmotionDirection,
    "sfx_direction": SfxDirection,
    "director_recommendation_bundle": DirectorRecommendationBundle,
    "creative_conflict": CreativeConflict,
    "resolved_creative_guidance": ResolvedCreativeGuidance,
    "creative_tier_decision": CreativeTierDecision,
    "reuse_candidate_score": ReuseCandidateScore,
    "reuse_evaluation_result": ReuseEvaluationResult,
    "compose_component_ref": ComposeComponentRef,
    "compose_evaluation_result": ComposeEvaluationResult,
    "scene_intent": SceneIntent,
    "composition_layer": CompositionLayer,
    "composition_plan": CompositionPlan,
    "creative_plan": CreativePlan,
    "creative_plan_validation_result": CreativePlanValidationResult,
    "resolved_template_decision": ResolvedTemplateDecision,
    "blueprint_compilation_result": BlueprintCompilationResult,
    "template_candidate": TemplateCandidate,
    "candidate_gate_result": CandidateGateResult,
    "validation_snapshot": ValidationSnapshot,
    "candidate_validation_report": CandidateValidationReport,
    "candidate_review_bundle": CandidateReviewBundle,
    "candidate_review_decision": CandidateReviewDecision,
    "promotion_decision": PromotionDecision,
    "promotion_manifest": PromotionManifest,
    "candidate_promotion_record": CandidatePromotionRecord,
    "user_style_profile": UserStyleProfile,
    "creative_feedback": CreativeFeedback,
    "feedback_classification": FeedbackClassification,
    "style_preference_provenance": StylePreferenceProvenance,
    "style_decision_trace": StyleDecisionTrace,
    "effective_user_style": EffectiveUserStyle,
    "trace_assertion": TraceAssertion,
    "trace_assertion_result": TraceAssertionResult,
    "creative_eval_case": CreativeEvalCase,
    "creative_case_grade": CreativeCaseGrade,
    "pairwise_grade_result": PairwiseGradeResult,
    "judge_calibration_record": JudgeCalibrationRecord,
    "creative_eval_run": CreativeEvalRun,
    "creative_usage_event": CreativeUsageEvent,
    "creative_project_cost_summary": CreativeProjectCostSummary,
    "efficiency_finding": EfficiencyFinding,
    "creative_cost_audit_run": CreativeCostAuditRun,
}


def serialize_json_deterministic(data: Dict) -> str:
    """Serializes data structure into deterministic formatted JSON with sorted keys."""
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def generate_json_schemas() -> Dict[Path, str]:
    """Generates deterministic JSON Schema strings for each canonical creative contract."""
    files: Dict[Path, str] = {}

    bundled_defs = {}
    for name, model_cls in sorted(CANONICAL_MODELS.items()):
        schema = model_cls.model_json_schema()
        if "$defs" in schema:
            bundled_defs.update(schema["$defs"])
        bundled_defs[model_cls.__name__] = schema

        out_path = SCHEMA_DIR / f"{name}.schema.json"
        files[out_path] = serialize_json_deterministic(schema)

    # Consolidated bundle schema
    bundle = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CreativeContractsBundle",
        "description": "Consolidated schema bundle for Creative Intelligence Canonical Contracts (S28-01)",
        "$defs": bundled_defs,
    }
    files[SCHEMA_DIR / "creative_contracts.schema.json"] = serialize_json_deterministic(bundle)

    return files


def generate_typescript_content() -> str:
    """
    Generates deterministic TypeScript type definitions directly from canonical Python authority.
    Includes strict enum unions, base JSON types, and interfaces for all creative models.
    """
    lines: List[str] = [
        "/* eslint-disable */",
        "// ============================================================================",
        "// GENERATED FILE — DO NOT EDIT MANUALLY",
        "// Generated by scripts/generate_creative_contracts.py from ai/contracts/creative",
        "// Single Authority: Python Pydantic Models (ai/contracts/creative/*.py)",
        "// ============================================================================",
        "",
        "import type { ProvenanceRecord, CapabilityType } from './ai_contracts';",
        "",
        "/** Generic JSON value representation strictly preventing unrestricted arbitrary objects. */",
        "export type JsonValue =",
        "  | string",
        "  | number",
        "  | boolean",
        "  | null",
        "  | JsonValue[]",
        "  | { [key: string]: JsonValue };",
        "",
        "/** ISO 8601 timezone-aware UTC datetime string (e.g. '2026-10-01T17:00:00Z'). */",
        "export type TzAwareDatetime = string;",
        "",
    ]

    # Enums to emit
    enums = [
        ("AudioMode", AudioMode),
        ("ProvenanceType", ProvenanceType),
        ("KnowledgeStatus", KnowledgeStatus),
        ("KnowledgeCategory", KnowledgeCategory),
        ("SkillStatus", SkillStatus),
        ("TasteRuleSeverity", TasteRuleSeverity),
        ("CandidateStatus", CandidateStatus),
        ("CreativeTier", CreativeTier),
        ("CreativePlanStatus", CreativePlanStatus),
        ("PromotionStatus", PromotionStatus),
        ("ConflictPrecedenceRank", ConflictPrecedenceRank),
        ("ConflictSeverity", ConflictSeverity),
        ("ConflictStatus", ConflictStatus),
        ("ValidationPhase", ValidationPhase),
        ("GateStatus", GateStatus),
        ("ValidationOverallResult", ValidationOverallResult),
        ("CandidateReviewVerdict", CandidateReviewVerdict),
        ("PromotionRecordStatus", PromotionRecordStatus),
        ("FeedbackCategory", FeedbackCategory),
        ("FeedbackTargetType", FeedbackTargetType),
        ("FeedbackSentiment", FeedbackSentiment),
        ("WinningSource", WinningSource),
        ("EvalCategory", EvalCategory),
        ("GradingMethod", GradingMethod),
        ("EvalSeverity", EvalSeverity),
        ("TraceAssertionType", TraceAssertionType),
        ("CostProvenance", CostProvenance),
        ("EfficiencyFindingType", EfficiencyFindingType),
        ("EfficiencySeverity", EfficiencySeverity),
        ("ThresholdProvenance", ThresholdProvenance),
    ]

    for enum_name, enum_cls in enums:
        members = [f'"{m.value}"' for m in enum_cls]
        union_str = " | ".join(members)
        lines.append(f"export type {enum_name} = {union_str};")
        lines.append("")

    interfaces_code = """
export interface FieldProvenance {
  source_type: ProvenanceType;
  rationale?: string | null;
  raw_reference?: string | null;
}

export interface CreativeIntent {
  intent_id: string;
  goal: string;
  audience: string;
  tone: string;
  key_takeaway: string;
  call_to_action?: string | null;
  target_platforms?: string[];
  video_type?: string | null;
  style?: string | null;
  pace?: string | null;
  language?: string | null;
}

export interface CreativeConstraints {
  min_duration_seconds?: number | null;
  max_duration_seconds?: number | null;
  target_duration_seconds?: number | null;
  aspect_ratios?: string[];
  audio_mode?: AudioMode;
  brand_colors?: string[];
  excluded_templates?: string[];
  forbidden_words?: string[];
  safe_zone_margin_px?: number | null;
}

export interface CreativeBrief {
  brief_id: string;
  project_id: string;
  workspace_id: string;
  user_request_raw: string;
  interpreted_intent: CreativeIntent;
  constraints: CreativeConstraints;
  provenance: ProvenanceRecord;
  field_provenance?: Record<string, FieldProvenance>;
  detected_contradictions?: string[];
  created_at: TzAwareDatetime;
  version?: string;
}

export interface NarrativeBeat {
  beat_id: string;
  beat_index: number;
  phase: string;
  emotional_target: string;
  pacing: string;
  estimated_duration_sec: number;
  key_message: string;
  visual_hook_description?: string | null;
  sound_effect_cue?: string | null;
}

export interface NarrativePlan {
  narrative_id: string;
  brief_id: string;
  core_hook: string;
  beats: NarrativeBeat[];
  arc_structure: string;
  estimated_total_duration_sec: number;
  provenance: ProvenanceRecord;
  created_at: TzAwareDatetime;
}

export interface SkillDefinition {
  skill_id: string;
  name: string;
  description: string;
  task_type?: string;
  version?: string;
  status?: SkillStatus;
  trigger_conditions?: string[];
  required_context?: string[];
  required_capabilities?: CapabilityType[];
  allowed_tools?: string[];
  required_knowledge?: string[];
  input_contract?: string | null;
  output_contract?: string | null;
  applicable_recipe_ids?: string[];
  metadata?: Record<string, JsonValue>;
}

export interface KnowledgeDescriptor {
  knowledge_id: string;
  category: string;
  title: string;
  source_uri: string;
  content_hash: string;
  version?: string;
  status?: KnowledgeStatus;
  tags?: string[];
  video_types?: string[];
  platforms?: string[];
  audio_modes?: AudioMode[];
  language?: string;
  dependencies?: string[];
  authority_level?: number;
  summary?: string | null;
}

export interface RecipeStage {
  stage_id: string;
  title: string;
  actions: string[];
  required_capabilities?: CapabilityType[];
  artifacts?: string[];
  paid_generation?: boolean;
}

export interface RecipeDefinition {
  recipe_id: string;
  name: string;
  version?: string;
  description: string;
  best_for: string[];
  not_for?: string[];
  platforms: string[];
  aspect_ratios: string[];
  duration_seconds_min: number;
  duration_seconds_max: number;
  duration_seconds_target: number;
  stages: RecipeStage[];
  owner?: string;
  supported_intents?: string[];
  supported_platforms?: string[];
  supported_audio_modes?: AudioMode[];
  required_skills?: string[];
  required_knowledge?: string[];
  required_capabilities?: CapabilityType[];
  optional_capabilities?: CapabilityType[];
  forbidden_capabilities?: CapabilityType[];
  phases?: string[];
  dependencies?: string[];
  quality_profile?: string | null;
  budget_profile?: string | null;
  fallback_strategy?: string | null;
  routing_keywords: string[];
  routing_negative_keywords?: string[];
  deliverables: string[];
}

export interface RecipeSelection {
  selection_id: string;
  brief_id: string;
  selected_recipe_id: string;
  confidence_score: number;
  matched_keywords?: string[];
  alternative_recipe_ids?: string[];
  selection_rationale: string;
  required_skills?: string[];
  required_knowledge?: string[];
  excluded_recipe_ids?: Record<string, string>;
  selection_reasons?: string[];
  provenance: ProvenanceRecord;
  created_at: TzAwareDatetime;
}

export interface TasteRule {
  rule_id: string;
  category: string;
  name: string;
  description: string;
  rationale: string;
  citation_source: string;
  severity?: TasteRuleSeverity;
  parameters?: Record<string, JsonValue>;
  version?: string;
  applies_when?: Record<string, JsonValue>;
  recommendation?: string;
  priority?: number;
  exceptions?: string[];
  source_knowledge_ids?: string[];
}

export interface TasteDecision {
  decision_id: string;
  rule_id: string;
  context_ref: string;
  applied_value: string;
  reasoning: string;
  citation: string;
  confidence?: number;
  rule_ids?: string[];
  evidence?: string[];
  reason_summary?: string;
}

export interface TasteContext {
  brief: CreativeBrief;
  narrative_plan: NarrativePlan;
  recipe_id: string;
  recipe_name?: string;
  media_intelligence?: Record<string, JsonValue>;
  available_assets?: string[];
  user_style_profile?: UserStyleProfile | null;
  active_knowledge_ids?: string[];
  active_skill_ids?: string[];
}

export interface NarrativeDirection {
  beat_id: string;
  narrative_focus: string;
  pacing_instruction: string;
  information_density: string;
  spoken_line?: string | null;
  visual_progression_cue: string;
  taste_rule_ids?: string[];
  reason_summary?: string;
}

export interface MotionDirection {
  scene_id: string;
  motion_energy: string;
  motion_personality: string;
  entry_style: string;
  exit_style: string;
  camera_intent: string;
  text_motion: string;
  visual_hierarchy?: string[];
  taste_rule_ids?: string[];
  reason_summary?: string;
}

export interface EmotionDirection {
  beat_or_scene_id: string;
  primary_emotion: string;
  intensity: string;
  emotional_progression: string;
  color_pairing_hint?: string | null;
  taste_rule_ids?: string[];
  reason_summary?: string;
}

export interface SfxDirection {
  beat_or_scene_id: string;
  audio_mode: AudioMode;
  sound_cues?: Record<string, JsonValue>[];
  ducking_profile?: string | null;
  taste_rule_ids?: string[];
  reason_summary?: string;
}

export interface DirectorRecommendationBundle {
  brief_id: string;
  narrative_directions?: NarrativeDirection[];
  motion_directions?: MotionDirection[];
  emotion_directions?: EmotionDirection[];
  sfx_directions?: SfxDirection[];
  created_at: TzAwareDatetime;
}

export interface CreativeConflict {
  conflict_id: string;
  conflict_type: string;
  severity: ConflictSeverity;
  description: string;
  conflicting_parties: string[];
  competing_directives: Record<string, JsonValue>;
  applied_precedence: ConflictPrecedenceRank;
  resolved_directive?: Record<string, JsonValue> | null;
  status: ConflictStatus;
  reason_summary: string;
}

export interface ResolvedCreativeGuidance {
  guidance_id: string;
  brief_id: string;
  recipe_id: string;
  narrative_plan: NarrativePlan;
  taste_decisions: TasteDecision[];
  narrative_directions?: NarrativeDirection[];
  motion_directions?: MotionDirection[];
  emotion_directions?: EmotionDirection[];
  sfx_directions?: SfxDirection[];
  detected_conflicts?: CreativeConflict[];
  unresolved_conflicts?: CreativeConflict[];
  status?: string;
  provenance: ProvenanceRecord;
  created_at: TzAwareDatetime;
}

export interface CompositionLayer {
  layer_type: string;
  element_ref: string;
  properties?: Record<string, JsonValue>;
}

export interface CompositionPlan {
  composition_id: string;
  scene_id: string;
  base_template_or_primitive: string;
  layers?: CompositionLayer[];
  layout_zone?: string;
  camera_motion?: string | null;
  gestural_elements?: string[];
  sfx_bindings?: Record<string, JsonValue>[];
  transition?: string | null;
  effects?: string[];
}

export interface ReuseCandidateScore {
  template_id: string;
  eligible: boolean;
  hard_filter_failures?: string[];
  fit_score: number;
  score_breakdown?: Record<string, number>;
  sufficient: boolean;
}

export interface ReuseEvaluationResult {
  need_description: string;
  candidates_checked?: string[];
  eligible_candidates?: string[];
  ranked_candidates?: ReuseCandidateScore[];
  selected_candidate?: string | null;
  rejection_reasons?: Record<string, string[]>;
  sufficiency: boolean;
  rationale: string;
}

export interface ComposeComponentRef {
  component_id: string;
  component_type: string;
  role: string;
  props?: Record<string, JsonValue>;
}

export interface ComposeEvaluationResult {
  need_description: string;
  components_checked?: string[];
  eligible_components?: string[];
  composition_plan?: CompositionPlan | null;
  rejection_reasons?: string[];
  sufficiency: boolean;
  rationale: string;
}

export interface CreativeTierDecision {
  decision_id: string;
  scene_id: string;
  selected_tier: CreativeTier;
  rationale: string;
  template_ref?: string | null;
  composite_elements?: string[];
  needs_create_evaluation?: boolean;
  requested_need?: string | null;
  reuse_candidates_checked?: string[];
  reuse_result?: ReuseEvaluationResult | null;
  compose_candidates_checked?: string[];
  compose_result?: ComposeEvaluationResult | null;
  composition_plan?: CompositionPlan | null;
}

export interface SceneIntent {
  scene_id: string;
  scene_index: number;
  beat_id?: string | null;
  intent_label: string;
  mood: string;
  motion_personality: string;
  primary_visual_job: string;
  estimated_duration_sec: number;
  spoken_text?: string | null;
  taste_decisions?: TasteDecision[];
  asset_requirements?: string[];
  audio_intent?: string | null;
  template_requirements?: string[];
}

export interface CreativePlan {
  plan_id: string;
  brief_id: string;
  recipe_id: string;
  title: string;
  narrative_plan: NarrativePlan;
  scenes: SceneIntent[];
  compositions?: CompositionPlan[];
  tier_decisions?: CreativeTierDecision[];
  total_estimated_duration_sec: number;
  status?: CreativePlanStatus;
  provenance: ProvenanceRecord;
  created_at: TzAwareDatetime;
}

export interface CreativePlanValidationResult {
  valid: boolean;
  errors?: string[];
  warnings?: string[];
  checked_invariants?: string[];
}

export interface ResolvedTemplateDecision {
  scene_id: string;
  template_id: string;
  template_props?: Record<string, JsonValue>;
}

export interface BlueprintCompilationResult {
  success: boolean;
  blueprint?: Record<string, JsonValue> | null;
  compiler_version?: string;
  errors?: string[];
  warnings?: string[];
}

export interface TemplateCandidate {
  candidate_id: string;
  workspace_id?: string;
  source_project_id?: string;
  origin_project_id?: string | null;
  creator_ai_run_id?: string | null;
  creative_plan_reference?: string;
  creative_tier_decision_reference?: string;
  why_reuse_failed?: string;
  why_compose_failed?: string;
  source_code?: string;
  source_code_path?: string | null;
  template_schema?: Record<string, JsonValue>;
  dependencies?: string[];
  fixtures?: Record<string, JsonValue>;
  content_hash?: string;
  revision?: number;
  status?: CandidateStatus;
  name?: string;
  description?: string;
  author?: string;
  proposed_category?: string;
  proposed_tags?: string[];
  target_tier?: CreativeTier;
  required_provenance: ProvenanceRecord;
  storage_keys?: Record<string, string>;
  created_at: TzAwareDatetime;
  updated_at?: TzAwareDatetime;
}

export interface CandidateGateResult {
  gate_id: string;
  status: GateStatus;
  failure_code?: string | null;
  summary: string;
  machine_details?: Record<string, JsonValue>;
  evidence_refs?: string[];
}

export interface ValidationSnapshot {
  candidate_id: string;
  workspace_id: string;
  candidate_content_hash: string;
  candidate_revision: number;
  phase?: ValidationPhase;
  policy_version?: string;
  started_at: TzAwareDatetime;
}

export interface CandidateValidationReport {
  validation_id: string;
  candidate_id: string;
  workspace_id?: string;
  candidate_content_hash?: string;
  candidate_revision?: number;
  phase?: ValidationPhase;
  policy_version?: string;
  started_at: TzAwareDatetime;
  completed_at: TzAwareDatetime;
  gates?: CandidateGateResult[];
  overall_result?: ValidationOverallResult;
  evidence_refs?: Record<string, string>;
  report_id?: string | null;
  typescript_compiles?: boolean;
  security_clean?: boolean;
  no_dangerous_imports?: boolean;
  has_documentation?: boolean;
  quality_score?: number;
  passed?: boolean;
  findings?: string[];
  evaluated_at?: TzAwareDatetime | null;
}

export interface CandidateReviewBundle {
  review_bundle_id: string;
  candidate_id: string;
  workspace_id?: string;
  candidate_content_hash: string;
  candidate_revision: number;
  static_validation_id: string;
  runtime_validation_id: string;
  static_report_hash: string;
  runtime_report_hash: string;
  render_evidence_refs?: Record<string, string>;
  representative_frame_refs?: string[];
  probe_report_ref?: string | null;
  qc_report_ref?: string | null;
  source_code_hash: string;
  schema_hash: string;
  fixtures_hash: string;
  created_at: TzAwareDatetime;
  review_policy_version?: string;
  review_bundle_hash?: string;
}

export interface CandidateReviewDecision {
  decision_id: string;
  review_bundle_id: string;
  candidate_id: string;
  workspace_id?: string;
  decision: CandidateReviewVerdict;
  reviewer_principal_id: string;
  reviewer_role: string;
  reason: string;
  candidate_content_hash: string;
  candidate_revision: number;
  review_bundle_hash: string;
  static_validation_report_hash: string;
  runtime_validation_report_hash: string;
  render_evidence_ref?: string | null;
  qc_report_ref?: string | null;
  decided_at: TzAwareDatetime;
  decision_revision?: number;
}

export interface PromotionDecision {
  decision_id: string;
  candidate_id: string;
  status: PromotionStatus;
  promoted_template_id?: string | null;
  authorized_by: string;
  reasoning: string;
  decided_at: TzAwareDatetime;
}

export interface PromotionManifest {
  promotion_id: string;
  candidate_id: string;
  workspace_id?: string;
  candidate_content_hash: string;
  candidate_revision: number;
  approval_decision_id: string;
  review_bundle_id: string;
  review_bundle_hash: string;
  static_validation_id: string;
  runtime_validation_id: string;
  target_template_id: string;
  target_template_version?: string;
  source_code_hash: string;
  schema_hash: string;
  promotion_policy_version?: string;
  created_at: TzAwareDatetime;
  promotion_manifest_hash: string;
}

export interface CandidatePromotionRecord {
  promotion_id: string;
  candidate_id: string;
  workspace_id?: string;
  promotion_manifest_hash: string;
  approval_decision_id: string;
  review_bundle_hash: string;
  target_template_id: string;
  target_template_version?: string;
  pre_publish_registry_hash: string;
  post_publish_registry_hash?: string;
  published_artifact_hashes?: Record<string, string>;
  status?: PromotionRecordStatus;
  started_at: TzAwareDatetime;
  completed_at?: TzAwareDatetime | null;
  error_message?: string | null;
  promoted_by_principal_id?: string | null;
}


export interface StylePreferenceProvenance {
  dimension: string;
  epistemic_status: string;
  confidence: number;
  source_type: string;
  evidence_count?: number;
  last_observed_at: TzAwareDatetime;
  source_id?: string | null;
  rationale?: string | null;
}

export interface UserStyleProfile {
  profile_id: string;
  workspace_id: string;
  user_id?: string | null;
  preferred_motion_personality?: string | null;
  motion_intensity?: string | null;
  preferred_color_palette?: string[];
  pacing_preference?: string | null;
  text_density?: string | null;
  caption_style?: string | null;
  music_tendencies?: string | null;
  transition_preference?: string | null;
  visual_complexity?: string | null;
  preferred_voices?: string[];
  disliked_patterns?: string[];
  taste_preferences?: Record<string, JsonValue>;
  provenance_by_dimension?: Record<string, StylePreferenceProvenance>;
  updated_at: TzAwareDatetime;
}

export interface FeedbackClassification {
  classification_id: string;
  feedback_id: string;
  workspace_id: string;
  user_id?: string | null;
  project_id?: string | null;
  target_type: FeedbackTargetType;
  target_reference?: string | null;
  category: FeedbackCategory;
  sentiment: FeedbackSentiment;
  preference_dimension?: string | null;
  proposed_value?: string | null;
  scope: string;
  confidence: number;
  source: string;
  is_explicit_general_rule?: boolean;
  created_at: TzAwareDatetime;
}

export interface CreativeFeedback {
  feedback_id: string;
  project_id: string;
  workspace_id?: string | null;
  user_id?: string | null;
  plan_id?: string | null;
  user_rating?: number | null;
  liked_aspects?: string[];
  disliked_aspects?: string[];
  critique_text?: string | null;
  target_type?: FeedbackTargetType | null;
  target_reference?: string | null;
  classification?: FeedbackClassification | null;
  created_at: TzAwareDatetime;
}

export interface StyleDecisionTrace {
  dimension: string;
  considered_value?: string | null;
  considered_source?: string | null;
  considered_confidence?: number | null;
  applied_value?: string | null;
  is_overridden?: boolean;
  override_reason?: string | null;
  winning_source: WinningSource;
}

export interface EffectiveUserStyle {
  profile_id?: string | null;
  workspace_id: string;
  user_id?: string | null;
  pacing?: string | null;
  motion_intensity?: string | null;
  motion_personality?: string | null;
  text_density?: string | null;
  caption_style?: string | null;
  music_preference?: string | null;
  transition_style?: string | null;
  visual_complexity?: string | null;
  preferred_color_palette?: string[];
  preferred_voices?: string[];
  disliked_patterns?: string[];
  trace_records?: StyleDecisionTrace[];
  resolved_at: TzAwareDatetime;
}

export interface TraceAssertion {
  assertion_type: TraceAssertionType;
  target_event_or_span: string;
  secondary_target?: string | null;
  field_path?: string | null;
  expected_value?: JsonValue | null;
  allowed_values?: JsonValue[] | null;
  forbidden_values?: JsonValue[] | null;
  min_count?: number | null;
  max_count?: number | null;
  description?: string;
}

export interface TraceAssertionResult {
  assertion_type: string;
  target: string;
  passed: boolean;
  details: string;
}

export interface CreativeEvalCase {
  case_id: string;
  version?: string;
  category: EvalCategory;
  tags?: string[];
  input_fixture: Record<string, JsonValue>;
  expected_constraints?: Record<string, JsonValue>;
  expected_decisions?: Record<string, JsonValue>;
  allowed_outputs?: JsonValue[];
  forbidden_outputs?: JsonValue[];
  grading_method: GradingMethod;
  severity?: EvalSeverity;
  source?: string;
  is_deliberately_bad?: boolean;
  trace_assertions?: TraceAssertion[];
  rubric_thresholds?: Record<string, number>;
  retrieval_k?: number;
  min_precision_at_k?: number | null;
  min_recall_at_k?: number | null;
  min_mrr?: number | null;
}

export interface CreativeCaseGrade {
  case_id: string;
  category: string;
  severity: string;
  grading_method: string;
  passed: boolean;
  score: number;
  score_breakdown?: Record<string, number>;
  reasons?: string[];
  trace_results?: TraceAssertionResult[];
  retrieved_items?: string[];
  expected_items?: string[];
  is_deliberately_bad?: boolean;
  detected_deliberate_bad?: boolean;
  duration_ms?: number;
}

export interface PairwiseGradeResult {
  scenario_id: string;
  preferred_candidate: string;
  margin: number;
  per_dimension_deltas?: Record<string, number>;
  rationale: string;
}

export interface JudgeCalibrationRecord {
  total_calibration_pairs: number;
  agreement_count: number;
  agreement_rate: number;
  disagreements?: Record<string, JsonValue>[];
  calibrated: boolean;
  calibration_method?: string;
}

export interface CreativeEvalRun {
  run_id: string;
  suite_version?: string;
  cases_total: number;
  passed_count: number;
  failed_count: number;
  pass_rate: number;
  by_category: Record<string, Record<string, JsonValue>>;
  by_severity: Record<string, Record<string, JsonValue>>;
  regressions?: Record<string, JsonValue>[];
  trace_failures?: Record<string, JsonValue>[];
  deliberately_bad_detected_count?: number;
  deliberately_bad_total_count?: number;
  judge_calibration?: JudgeCalibrationRecord | null;
  started_at: TzAwareDatetime;
  completed_at: TzAwareDatetime;
  verdict: string;
}

export interface CreativeUsageEvent {
  event_id: string;
  workspace_id: string;
  project_id?: string | null;
  run_id?: string | null;
  stage?: string | null;
  subsystem?: string | null;
  operation_type?: string;
  provider?: string | null;
  model?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  cached_input_tokens?: number | null;
  cache_hit?: boolean | null;
  request_count?: number;
  generation_count?: number;
  retrieval_items?: number;
  latency_ms?: number | null;
  cost_provenance?: CostProvenance;
  estimated_cost?: string | null;
  actual_cost?: string | null;
  currency?: string;
  pricing_version?: string | null;
  created_at: TzAwareDatetime;
  input_hash?: string | null;
  details?: Record<string, JsonValue>;
}

export interface CreativeProjectCostSummary {
  workspace_id: string;
  project_id: string;
  run_count?: number;
  planning_tokens?: number;
  retrieval_tokens?: number;
  ai_calls?: number;
  generation_calls?: number;
  reuse_count?: number;
  compose_count?: number;
  create_count?: number;
  total_latency_ms?: number;
  actual_cost?: string;
  estimated_cost?: string;
  currency?: string;
  pricing_version?: string | null;
  cost_coverage_complete?: boolean;
  known_cost_event_count?: number;
  unknown_cost_event_count?: number;
  tier_breakdown?: Record<string, JsonValue>;
  stage_breakdown?: Record<string, JsonValue>;
  model_breakdown?: Record<string, JsonValue>;
  provider_breakdown?: Record<string, JsonValue>;
  status_breakdown?: Record<string, JsonValue>;
}

export interface EfficiencyFinding {
  finding_id: string;
  workspace_id: string;
  project_id?: string | null;
  run_id?: string | null;
  finding_type: EfficiencyFindingType;
  severity: EfficiencySeverity;
  observed_value: JsonValue;
  expected_bound: JsonValue;
  evidence_refs?: string[];
  summary: string;
}

export interface CreativeCostAuditRun {
  run_id: string;
  policy_version?: string;
  projects_evaluated?: number;
  usage_totals?: Record<string, JsonValue>;
  cost_totals?: Record<string, JsonValue>;
  latency_summary?: Record<string, JsonValue>;
  tier_distribution?: Record<string, JsonValue>;
  cost_coverage_complete?: boolean;
  known_cost_event_count?: number;
  unknown_cost_event_count?: number;
  findings?: EfficiencyFinding[];
  started_at: TzAwareDatetime;
  completed_at: TzAwareDatetime;
  verdict?: string;
}
""".strip()

    lines.append(interfaces_code)
    lines.append("")
    return "\n".join(lines)


def write_file_atomic(path: Path, content: str) -> None:
    """Atomically writes content using a temporary sibling file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def check_artifacts() -> Tuple[bool, List[str]]:
    """
    Compares all on-disk artifacts against expected in-memory outputs.
    Returns (is_synced, diff_messages).
    """
    expected_schemas = generate_json_schemas()
    expected_ts = generate_typescript_content()

    stale_or_missing: List[str] = []

    # Check schemas
    for schema_path, expected_content in expected_schemas.items():
        if not schema_path.exists():
            stale_or_missing.append(f"Missing schema: {schema_path.relative_to(ROOT)}")
            continue
        current = schema_path.read_text(encoding="utf-8")
        if current != expected_content:
            stale_or_missing.append(f"Stale schema: {schema_path.relative_to(ROOT)}")

    # Check TypeScript outputs
    for ts_path in [TS_OUTPUT_CONTRACTS, TS_OUTPUT_REMOTION]:
        if not ts_path.exists():
            stale_or_missing.append(f"Missing TypeScript contract: {ts_path.relative_to(ROOT)}")
            continue
        current = ts_path.read_text(encoding="utf-8")
        if current != expected_ts:
            stale_or_missing.append(f"Stale TypeScript contract: {ts_path.relative_to(ROOT)}")

    return (len(stale_or_missing) == 0, stale_or_missing)


def generate_all() -> None:
    """Generates all JSON schemas and TypeScript contracts deterministically."""
    schemas = generate_json_schemas()
    for path, content in schemas.items():
        write_file_atomic(path, content)

    ts_content = generate_typescript_content()
    write_file_atomic(TS_OUTPUT_CONTRACTS, ts_content)
    write_file_atomic(TS_OUTPUT_REMOTION, ts_content)


def main() -> int:
    check_mode = "--check" in sys.argv

    if check_mode:
        synced, errors = check_artifacts()
        if synced:
            print("✅ Ground Truth Parity: Creative contracts, schemas, and TypeScript definitions are fully synchronized.")
            return 0
        else:
            print("❌ STALENESS DETECTED in Creative Contract artifacts:", file=sys.stderr)
            for err in errors:
                print(f"  • {err}", file=sys.stderr)
            print("\nRun `python scripts/generate_creative_contracts.py` to regenerate artifacts.", file=sys.stderr)
            return 1

    generate_all()
    print("✅ Successfully generated Creative contracts:")
    print(f"   • {len(CANONICAL_MODELS) + 1} JSON schemas -> {SCHEMA_DIR.relative_to(ROOT)}/")
    print(f"   • TypeScript contracts -> {TS_OUTPUT_CONTRACTS.relative_to(ROOT)}")
    print(f"   • TypeScript contracts -> {TS_OUTPUT_REMOTION.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
