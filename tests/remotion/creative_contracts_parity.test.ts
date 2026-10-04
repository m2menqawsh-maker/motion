import { describe, it, expect } from "vitest";
import type {
  AudioMode,
  CreativeBrief,
  CreativeConstraints,
  CreativeIntent,
  NarrativePlan,
  NarrativeBeat,
  SkillDefinition,
  KnowledgeDescriptor,
  RecipeDefinition,
  RecipeSelection,
  TasteRule,
  TasteDecision,
  CreativeTier,
  CreativeTierDecision,
  SceneIntent,
  CompositionPlan,
  CreativePlan,
  TemplateCandidate,
  CandidateValidationReport,
  CandidateReviewBundle,
  CandidateReviewDecision,
  CandidateReviewVerdict,
  PromotionDecision,
  PromotionManifest,
  CandidatePromotionRecord,
  PromotionRecordStatus,
  UserStyleProfile,
  CreativeFeedback,
  DirectorRecommendationBundle,
  NarrativeDirection,
  MotionDirection,
  EmotionDirection,
  SfxDirection,
  CreativeConflict,
  ResolvedCreativeGuidance,
  CreativePlanValidationResult,
  ResolvedTemplateDecision,
  BlueprintCompilationResult,
  ReuseCandidateScore,
  ReuseEvaluationResult,
  ComposeComponentRef,
  ComposeEvaluationResult,
  EffectiveUserStyle,
  FeedbackCategory,
  FeedbackClassification,
  FeedbackSentiment,
  FeedbackTargetType,
  StyleDecisionTrace,
  StylePreferenceProvenance,
  WinningSource,
  CreativeUsageEvent,
  CreativeProjectCostSummary,
  EfficiencyFinding,
  CreativeCostAuditRun,
  CostProvenance,
  EfficiencyFindingType,
  EfficiencySeverity,
} from "../../contracts/generated/creative_contracts";

import creativeBriefSchema from "../../schemas/creative/creative_brief.schema.json";
import narrativePlanSchema from "../../schemas/creative/narrative_plan.schema.json";
import recipeDefinitionSchema from "../../schemas/creative/recipe_definition.schema.json";
import tasteRuleSchema from "../../schemas/creative/taste_rule.schema.json";
import creativePlanSchema from "../../schemas/creative/creative_plan.schema.json";
import templateCandidateSchema from "../../schemas/creative/template_candidate.schema.json";
import candidateReviewBundleSchema from "../../schemas/creative/candidate_review_bundle.schema.json";
import candidateReviewDecisionSchema from "../../schemas/creative/candidate_review_decision.schema.json";
import promotionDecisionSchema from "../../schemas/creative/promotion_decision.schema.json";
import promotionManifestSchema from "../../schemas/creative/promotion_manifest.schema.json";
import candidatePromotionRecordSchema from "../../schemas/creative/candidate_promotion_record.schema.json";
import directorRecommendationBundleSchema from "../../schemas/creative/director_recommendation_bundle.schema.json";
import resolvedCreativeGuidanceSchema from "../../schemas/creative/resolved_creative_guidance.schema.json";
import reuseEvaluationResultSchema from "../../schemas/creative/reuse_evaluation_result.schema.json";
import composeEvaluationResultSchema from "../../schemas/creative/compose_evaluation_result.schema.json";
import creativeConflictSchema from "../../schemas/creative/creative_conflict.schema.json";
import creativePlanValidationResultSchema from "../../schemas/creative/creative_plan_validation_result.schema.json";
import resolvedTemplateDecisionSchema from "../../schemas/creative/resolved_template_decision.schema.json";
import blueprintCompilationResultSchema from "../../schemas/creative/blueprint_compilation_result.schema.json";
import userStyleProfileSchema from "../../schemas/creative/user_style_profile.schema.json";
import creativeFeedbackSchema from "../../schemas/creative/creative_feedback.schema.json";
import feedbackClassificationSchema from "../../schemas/creative/feedback_classification.schema.json";
import effectiveUserStyleSchema from "../../schemas/creative/effective_user_style.schema.json";
import creativeUsageEventSchema from "../../schemas/creative/creative_usage_event.schema.json";
import creativeProjectCostSummarySchema from "../../schemas/creative/creative_project_cost_summary.schema.json";
import efficiencyFindingSchema from "../../schemas/creative/efficiency_finding.schema.json";
import creativeCostAuditRunSchema from "../../schemas/creative/creative_cost_audit_run.schema.json";

import fixtures from "../ai/contracts/fixtures/creative_contract_fixtures.json";


describe("Creative Contracts TypeScript & JSON Schema Parity (S28-01)", () => {
  it("validates CreativeBrief compilation, typing, and schema parity", () => {
    const rawBrief = fixtures.valid.creative_brief;
    const brief: CreativeBrief = {
      brief_id: rawBrief.brief_id,
      project_id: rawBrief.project_id,
      workspace_id: rawBrief.workspace_id,
      user_request_raw: rawBrief.user_request_raw,
      interpreted_intent: rawBrief.interpreted_intent,
      constraints: rawBrief.constraints as CreativeConstraints,
      provenance: rawBrief.provenance,
      created_at: rawBrief.created_at,
      version: rawBrief.version,
    };

    expect(brief.brief_id).toBe("brief_tech_saas_001");
    expect(brief.constraints.audio_mode).toBe("VO_MUSIC");
    expect(creativeBriefSchema.title).toBe("CreativeBrief");
    expect(creativeBriefSchema.required).toContain("brief_id");
    expect(creativeBriefSchema.required).toContain("project_id");
    expect(creativeBriefSchema.required).toContain("interpreted_intent");
    expect(creativeBriefSchema.required).toContain("constraints");
    expect(creativeBriefSchema.required).toContain("provenance");
  });

  it("validates NarrativePlan and NarrativeBeat compilation and schema parity", () => {
    const rawPlan = fixtures.valid.narrative_plan;
    const plan: NarrativePlan = {
      narrative_id: rawPlan.narrative_id,
      brief_id: rawPlan.brief_id,
      core_hook: rawPlan.core_hook,
      beats: rawPlan.beats as NarrativeBeat[],
      arc_structure: rawPlan.arc_structure,
      estimated_total_duration_sec: rawPlan.estimated_total_duration_sec,
      provenance: rawPlan.provenance,
      created_at: rawPlan.created_at,
    };

    expect(plan.beats.length).toBe(3);
    expect(plan.estimated_total_duration_sec).toBe(30.0);
    expect(narrativePlanSchema.title).toBe("NarrativePlan");
    expect(narrativePlanSchema.required).toContain("narrative_id");
    expect(narrativePlanSchema.required).toContain("beats");
    expect(narrativePlanSchema.required).toContain("estimated_total_duration_sec");
  });

  it("validates RecipeDefinition provider neutrality and schema parity", () => {
    const rawRecipe = fixtures.valid.recipe_definition;
    const recipe: RecipeDefinition = {
      recipe_id: rawRecipe.recipe_id,
      name: rawRecipe.name,
      version: rawRecipe.version,
      description: rawRecipe.description,
      best_for: rawRecipe.best_for,
      not_for: rawRecipe.not_for,
      platforms: rawRecipe.platforms,
      aspect_ratios: rawRecipe.aspect_ratios,
      duration_seconds_min: rawRecipe.duration_seconds_min,
      duration_seconds_max: rawRecipe.duration_seconds_max,
      duration_seconds_target: rawRecipe.duration_seconds_target,
      stages: rawRecipe.stages,
      required_skills: rawRecipe.required_skills,
      required_capabilities: rawRecipe.required_capabilities as any,
      routing_keywords: rawRecipe.routing_keywords,
      routing_negative_keywords: rawRecipe.routing_negative_keywords,
      deliverables: rawRecipe.deliverables,
    };

    expect(recipe.recipe_id).toBe("living-canvas-explainer");
    expect(recipe.stages.length).toBe(3);
    expect(recipeDefinitionSchema.title).toBe("RecipeDefinition");
    expect(recipeDefinitionSchema.required).toContain("recipe_id");
    expect(recipeDefinitionSchema.required).toContain("stages");
    expect(recipeDefinitionSchema.required).toContain("routing_keywords");
  });

  it("validates TasteRule and TasteDecision compilation and schema parity", () => {
    const rawRule = fixtures.valid.taste_rule;
    const rule: TasteRule = {
      rule_id: rawRule.rule_id,
      category: rawRule.category,
      name: rawRule.name,
      description: rawRule.description,
      rationale: rawRule.rationale,
      citation_source: rawRule.citation_source,
      severity: rawRule.severity as any,
      parameters: rawRule.parameters,
    };

    expect(rule.rule_id).toBe("taste_beat_density_v2");
    expect(rule.severity).toBe("MANDATORY_CREATIVE");
    expect(tasteRuleSchema.title).toBe("TasteRule");
    expect(tasteRuleSchema.required).toContain("rule_id");
    expect(tasteRuleSchema.required).toContain("citation_source");
  });

  it("validates CreativePlan and CreativeTierDecision compilation and schema parity", () => {
    const rawPlan = fixtures.valid.creative_plan;
    const plan: CreativePlan = {
      plan_id: rawPlan.plan_id,
      brief_id: rawPlan.brief_id,
      recipe_id: rawPlan.recipe_id,
      title: rawPlan.title,
      narrative_plan: rawPlan.narrative_plan as any,
      scenes: rawPlan.scenes as any,
      compositions: rawPlan.compositions,
      tier_decisions: rawPlan.tier_decisions as any,
      total_estimated_duration_sec: rawPlan.total_estimated_duration_sec,
      status: rawPlan.status as any,
      provenance: rawPlan.provenance,
      created_at: rawPlan.created_at,
    };

    expect(plan.plan_id).toBe("cplan_tech_001");
    expect(plan.status).toBe("PROPOSED");
    expect(creativePlanSchema.title).toBe("CreativePlan");
    expect(creativePlanSchema.required).toContain("plan_id");
    expect(creativePlanSchema.required).toContain("scenes");
    expect(creativePlanSchema.required).toContain("narrative_plan");
  });

  it("validates TemplateCandidate and PromotionDecision compilation and schema parity", () => {
    const rawCand = fixtures.valid.template_candidate;
    const cand: TemplateCandidate = {
      candidate_id: rawCand.candidate_id,
      name: rawCand.name,
      description: rawCand.description,
      source_code_path: rawCand.source_code_path,
      origin_project_id: rawCand.origin_project_id,
      author: rawCand.author,
      proposed_category: rawCand.proposed_category,
      proposed_tags: rawCand.proposed_tags,
      target_tier: rawCand.target_tier as any,
      required_provenance: rawCand.required_provenance,
      created_at: rawCand.created_at,
    };

    const rawPromo = fixtures.valid.promotion_decision;
    const promo: PromotionDecision = {
      decision_id: rawPromo.decision_id,
      candidate_id: rawPromo.candidate_id,
      status: rawPromo.status as any,
      promoted_template_id: rawPromo.promoted_template_id,
      authorized_by: rawPromo.authorized_by,
      reasoning: rawPromo.reasoning,
      decided_at: rawPromo.decided_at,
    };

    expect(cand.candidate_id).toBe("cand_custom_pulse_box");
    expect(promo.status).toBe("APPROVED");
    expect(promo.authorized_by).toBe("usr_lead_architect");

    expect(templateCandidateSchema.title).toBe("TemplateCandidate");
    expect(templateCandidateSchema.required).toContain("candidate_id");
    expect(templateCandidateSchema.required).toContain("required_provenance");

    expect(promotionDecisionSchema.title).toBe("PromotionDecision");
    expect(promotionDecisionSchema.required).toContain("decision_id");
    expect(promotionDecisionSchema.required).toContain("authorized_by");
  });

  it("validates CandidateReviewBundle and CandidateReviewDecision compilation and schema parity (S28-07D)", () => {
    const bundle: CandidateReviewBundle = {
      review_bundle_id: "rbd_bundle_123456",
      candidate_id: "cand_custom_pulse_box",
      workspace_id: "ws_default",
      candidate_content_hash: "hash_candidate_123",
      candidate_revision: 1,
      static_validation_id: "val_static_123",
      runtime_validation_id: "val_runtime_456",
      static_report_hash: "hash_static_rep_123",
      runtime_report_hash: "hash_runtime_rep_456",
      render_evidence_refs: { "smoke_frame": "key_smoke.png" },
      representative_frame_refs: ["key_smoke.png"],
      probe_report_ref: "key_probe.json",
      qc_report_ref: "key_qc.json",
      source_code_hash: "hash_src_123",
      schema_hash: "hash_schema_123",
      fixtures_hash: "hash_fixtures_123",
      created_at: "2026-10-02T19:00:00Z",
      review_policy_version: "1.0.0",
      review_bundle_hash: "hash_bundle_digest_123",
    };

    const decision: CandidateReviewDecision = {
      decision_id: "rdec_decision_123456",
      review_bundle_id: "rbd_bundle_123456",
      candidate_id: "cand_custom_pulse_box",
      workspace_id: "ws_default",
      decision: "APPROVED" as CandidateReviewVerdict,
      reviewer_principal_id: "usr_human_reviewer",
      reviewer_role: "reviewer",
      reason: "Verified motion quality and runtime safety bounds.",
      candidate_content_hash: "hash_candidate_123",
      candidate_revision: 1,
      review_bundle_hash: "hash_bundle_digest_123",
      static_validation_report_hash: "hash_static_rep_123",
      runtime_validation_report_hash: "hash_runtime_rep_456",
      decided_at: "2026-10-02T19:05:00Z",
      decision_revision: 1,
    };

    expect(bundle.review_bundle_id).toBe("rbd_bundle_123456");
    expect(decision.decision).toBe("APPROVED");
    expect(decision.reviewer_principal_id).toBe("usr_human_reviewer");

    expect(candidateReviewBundleSchema.title).toBe("CandidateReviewBundle");
    expect(candidateReviewBundleSchema.required).toContain("review_bundle_id");
    expect(candidateReviewBundleSchema.required).toContain("candidate_content_hash");
    expect(candidateReviewBundleSchema.required).toContain("review_bundle_hash");

    expect(candidateReviewDecisionSchema.title).toBe("CandidateReviewDecision");
    expect(candidateReviewDecisionSchema.required).toContain("decision_id");
    expect(candidateReviewDecisionSchema.required).toContain("reviewer_principal_id");
    expect(candidateReviewDecisionSchema.required).toContain("decision");
  });

  it("validates PromotionManifest and CandidatePromotionRecord compilation and schema parity (S28-07E)", () => {
    const manifest: PromotionManifest = {
      promotion_id: "prom_manifest_123456",
      candidate_id: "cand_custom_pulse_box",
      workspace_id: "ws_default",
      candidate_content_hash: "hash_candidate_123",
      candidate_revision: 1,
      approval_decision_id: "rdec_decision_123456",
      review_bundle_id: "rbd_bundle_123456",
      review_bundle_hash: "hash_bundle_digest_123",
      static_validation_id: "val_static_123",
      runtime_validation_id: "val_runtime_456",
      target_template_id: "pulse-box",
      target_template_version: "1.0.0",
      source_code_hash: "hash_src_123",
      schema_hash: "hash_schema_123",
      promotion_policy_version: "1.0.0",
      created_at: "2026-10-02T19:10:00Z",
      promotion_manifest_hash: "hash_manifest_digest_123",
    };

    const record: CandidatePromotionRecord = {
      promotion_id: "prom_record_123456",
      candidate_id: "cand_custom_pulse_box",
      workspace_id: "ws_default",
      promotion_manifest_hash: "hash_manifest_digest_123",
      approval_decision_id: "rdec_decision_123456",
      review_bundle_hash: "hash_bundle_digest_123",
      target_template_id: "pulse-box",
      target_template_version: "1.0.0",
      pre_publish_registry_hash: "hash_pre_reg_123",
      post_publish_registry_hash: "hash_post_reg_456",
      published_artifact_hashes: {
        "templates/elements/PulseBox.tsx": "hash_src_123",
      },
      status: "COMMITTED" as PromotionRecordStatus,
      started_at: "2026-10-02T19:10:00Z",
      completed_at: "2026-10-02T19:10:05Z",
      promoted_by_principal_id: "usr_admin_promoter",
    };

    expect(manifest.target_template_id).toBe("pulse-box");
    expect(record.status).toBe("COMMITTED");
    expect(record.promoted_by_principal_id).toBe("usr_admin_promoter");

    expect(promotionManifestSchema.title).toBe("PromotionManifest");
    expect(promotionManifestSchema.required).toContain("promotion_id");
    expect(promotionManifestSchema.required).toContain("target_template_id");
    expect(promotionManifestSchema.required).toContain("promotion_manifest_hash");

    expect(candidatePromotionRecordSchema.title).toBe("CandidatePromotionRecord");
    expect(candidatePromotionRecordSchema.required).toContain("promotion_id");
    expect(candidatePromotionRecordSchema.required).toContain("target_template_id");
    expect(candidatePromotionRecordSchema.required).toContain("status");
  });


  it("validates DirectorRecommendationBundle and sub-directions compilation and schema parity (S28-04)", () => {
    const rawPlan = fixtures.valid.narrative_plan;
    const bundle: DirectorRecommendationBundle = {
      brief_id: "brief_001",
      narrative_directions: [
        {
          beat_id: "beat_001",
          narrative_focus: "Establish core tension and problem",
          pacing_instruction: "fast",
          information_density: "moderate",
          spoken_line: "Stop wasting hours on manual edits.",
          visual_progression_cue: "Kinetic typography reveal",
          taste_rule_ids: ["taste_avoid_constant_motion"],
          reason_summary: "High urgency opening",
        },
      ],
      motion_directions: [
        {
          scene_id: "scene_001",
          motion_energy: "high",
          motion_personality: "Energetic",
          entry_style: "fast-zoom-in",
          exit_style: "whip-pan",
          camera_intent: "punchy-push",
          text_motion: "word-by-word-pop",
          visual_hierarchy: ["Primary headline", "Supporting badge"],
          taste_rule_ids: ["taste_motion_personality_curves"],
          reason_summary: "Energetic archetype for social ad",
        },
      ],
      emotion_directions: [
        {
          beat_or_scene_id: "beat_001",
          primary_emotion: "Curiosity",
          intensity: "high",
          emotional_progression: "Curiosity -> Urgency",
          color_pairing_hint: "high-contrast neon",
          taste_rule_ids: ["taste_color_discipline"],
          reason_summary: "High initial engagement",
        },
      ],
      sfx_directions: [
        {
          beat_or_scene_id: "beat_001",
          audio_mode: "VO_MUSIC",
          sound_cues: [{ sound: "whoosh-deep.wav", time_offset: 0.1 }],
          ducking_profile: "heavy_under_voiceover",
          taste_rule_ids: ["taste_gestural_audio_binding"],
          reason_summary: "Sync whoosh to kinetic text pop",
        },
      ],
      created_at: rawPlan.created_at,
    };

    expect(bundle.brief_id).toBe("brief_001");
    expect(bundle.motion_directions?.[0].motion_personality).toBe("Energetic");
    expect(bundle.sfx_directions?.[0].audio_mode).toBe("VO_MUSIC");

    expect(directorRecommendationBundleSchema.title).toBe("DirectorRecommendationBundle");
    expect(directorRecommendationBundleSchema.required).toContain("brief_id");
    expect(directorRecommendationBundleSchema.required).toContain("created_at");
  });

  it("validates CreativeConflict and ResolvedCreativeGuidance compilation and schema parity (S28-04)", () => {
    const rawPlan = fixtures.valid.narrative_plan;
    const rawRule = fixtures.valid.taste_rule;
    const now = rawPlan.created_at;

    const conflict: CreativeConflict = {
      conflict_id: "conf_001",
      conflict_type: "AUDIO_MODE_VIOLATION",
      severity: "HARD",
      description: "SFX cues proposed in SILENT audio mode",
      conflicting_parties: ["director:sfx", "brief:audio_mode"],
      competing_directives: { sfx_count: 3, allowed_sfx: 0 },
      applied_precedence: "HARD_SYSTEM_CONSTRAINT",
      status: "RESOLVED",
      resolved_directive: { sfx_count: 0 },
      reason_summary: "AudioMode constraint takes highest precedence; SFX muted.",
    };

    const guidance: ResolvedCreativeGuidance = {
      guidance_id: "guidance_001",
      brief_id: "brief_001",
      recipe_id: "recipe_001",
      narrative_plan: rawPlan as any,
      taste_decisions: [
        {
          decision_id: "dec_001",
          rule_id: rawRule.rule_id,
          context_ref: "beat_001",
          applied_value: "Apply motion hierarchy",
          reasoning: "Prevents fatigue",
          citation: rawRule.citation_source,
          confidence: 0.95,
          rule_ids: [rawRule.rule_id],
          evidence: ["Multi-beat narrative"],
          reason_summary: "Applied motion hierarchy",
        },
      ],
      detected_conflicts: [conflict],
      unresolved_conflicts: [],
      status: "SUCCESS",
      provenance: rawPlan.provenance,
      created_at: now,
    };

    expect(guidance.status).toBe("SUCCESS");
    expect(guidance.detected_conflicts?.length).toBe(1);
    expect(guidance.detected_conflicts?.[0].applied_precedence).toBe("HARD_SYSTEM_CONSTRAINT");

    expect(creativeConflictSchema.title).toBe("CreativeConflict");
    expect(creativeConflictSchema.required).toContain("conflict_id");
    expect(creativeConflictSchema.required).toContain("conflicting_parties");
    expect(creativeConflictSchema.required).toContain("applied_precedence");

    expect(resolvedCreativeGuidanceSchema.title).toBe("ResolvedCreativeGuidance");
    expect(resolvedCreativeGuidanceSchema.required).toContain("guidance_id");
    expect(resolvedCreativeGuidanceSchema.required).toContain("brief_id");
    expect(resolvedCreativeGuidanceSchema.required).toContain("narrative_plan");
  });

  it("validates CreativePlanValidationResult, ResolvedTemplateDecision, and BlueprintCompilationResult compilation and schema parity (S28-05)", () => {
    const valResult: CreativePlanValidationResult = {
      valid: true,
      errors: [],
      warnings: ["Minor padding suggestion"],
      checked_invariants: ["COVERS_USER_GOAL", "DURATION_FITS", "NO_FORBIDDEN_AUDIO_OPERATION"],
    };

    expect(valResult.valid).toBe(true);
    expect(valResult.checked_invariants?.length).toBe(3);
    expect(creativePlanValidationResultSchema.title).toBe("CreativePlanValidationResult");
    expect(creativePlanValidationResultSchema.required).toContain("valid");

    const templateDecision: ResolvedTemplateDecision = {
      scene_id: "scene_001",
      template_id: "StatCard",
      template_props: { value: "100ms", title: "Speed" },
    };

    expect(templateDecision.scene_id).toBe("scene_001");
    expect(templateDecision.template_id).toBe("StatCard");
    expect(resolvedTemplateDecisionSchema.title).toBe("ResolvedTemplateDecision");
    expect(resolvedTemplateDecisionSchema.required).toContain("scene_id");
    expect(resolvedTemplateDecisionSchema.required).toContain("template_id");

    const compileResult: BlueprintCompilationResult = {
      success: true,
      blueprint: { project_id: "test", blueprint_version: "2.0.0", scenes: [] },
      compiler_version: "1.0.0",
      errors: [],
      warnings: [],
    };

    expect(compileResult.success).toBe(true);
    expect(blueprintCompilationResultSchema.title).toBe("BlueprintCompilationResult");
    expect(blueprintCompilationResultSchema.required).toContain("success");
  });

  it("validates ReuseEvaluationResult and ComposeEvaluationResult schema parity (S28-06)", () => {
    const reuseScore: ReuseCandidateScore = {
      template_id: "rui-stat-card",
      eligible: true,
      hard_filter_failures: [],
      fit_score: 0.95,
      score_breakdown: { content: 1.0, motion: 0.9, duration: 0.95 },
      sufficient: true,
    };

    const reuseResult: ReuseEvaluationResult = {
      need_description: "Display performance metrics counter",
      candidates_checked: ["rui-stat-card", "rui-countdown-timer"],
      eligible_candidates: ["rui-stat-card"],
      ranked_candidates: [reuseScore],
      selected_candidate: "rui-stat-card",
      rejection_reasons: {},
      sufficiency: true,
      rationale: "rui-stat-card matches performance metrics intent with score 0.95.",
    };

    expect(reuseResult.sufficiency).toBe(true);
    expect(reuseResult.selected_candidate).toBe("rui-stat-card");
    expect(reuseEvaluationResultSchema.title).toBe("ReuseEvaluationResult");
    expect(reuseEvaluationResultSchema.required).toContain("need_description");
    expect(reuseEvaluationResultSchema.required).toContain("sufficiency");

    const composeResult: ComposeEvaluationResult = {
      need_description: "Complex multi-layer UI breakdown",
      components_checked: ["rui-split-screen", "animatedtext-element", "gradient-element"],
      eligible_components: ["rui-split-screen", "animatedtext-element"],
      composition_plan: {
        composition_id: "comp_001",
        scene_id: "scene_002",
        base_template_or_primitive: "rui-split-screen",
        layers: [
          {
            layer_type: "primary",
            element_ref: "animatedtext-element",
            properties: { text: "Modular Architecture" },
          },
        ],
        layout_zone: "split_left",
        transition: "fade",
        effects: ["camera-shake"],
      },
      rejection_reasons: [],
      sufficiency: true,
      rationale: "Successfully composed split screen with animated text and camera-shake effect.",
    };

    expect(composeResult.sufficiency).toBe(true);
    expect(composeResult.composition_plan?.base_template_or_primitive).toBe("rui-split-screen");
    expect(composeEvaluationResultSchema.title).toBe("ComposeEvaluationResult");
    expect(composeEvaluationResultSchema.required).toContain("need_description");
    expect(composeEvaluationResultSchema.required).toContain("sufficiency");
  });

  it("validates UserStyleProfile, CreativeFeedback, FeedbackClassification, and EffectiveUserStyle parity (S28-08A)", () => {
    const userProfile: UserStyleProfile = {
      profile_id: "prof_test_user",
      workspace_id: "ws_alpha",
      user_id: "usr_editor_1",
      preferred_motion_personality: "Cinematic",
      motion_intensity: "low",
      preferred_color_palette: ["#112233", "#445566"],
      pacing_preference: "calm",
      text_density: "minimal",
      caption_style: "compact",
      music_tendencies: "ambient",
      transition_preference: "subtle_dissolve",
      visual_complexity: "clean",
      preferred_voices: ["voice_eleven_adam"],
      disliked_patterns: ["electronic_music"],
      taste_preferences: { prefer_dark_mode: true },
      provenance_by_dimension: {
        pacing: {
          dimension: "pacing",
          epistemic_status: "EXPLICIT",
          confidence: 0.9,
          source_type: "USER_STATEMENT",
          evidence_count: 1,
          last_observed_at: "2026-10-02T12:00:00Z",
          rationale: "Explicit user prompt request",
        },
      },
      updated_at: "2026-10-02T12:00:00Z",
    };

    expect(userProfile.profile_id).toBe("prof_test_user");
    expect(userProfile.pacing_preference).toBe("calm");
    expect(userStyleProfileSchema.title).toBe("UserStyleProfile");
    expect(userStyleProfileSchema.required).toContain("profile_id");
    expect(userStyleProfileSchema.required).toContain("workspace_id");

    const classification: FeedbackClassification = {
      classification_id: "cls_001",
      feedback_id: "fb_001",
      workspace_id: "ws_alpha",
      user_id: "usr_editor_1",
      project_id: "prj_001",
      target_type: "SCENE",
      target_reference: "scene_001",
      category: "MOTION",
      sentiment: "NEGATIVE",
      preference_dimension: "motion_intensity",
      proposed_value: "low",
      scope: "PROJECT",
      confidence: 0.4,
      source: "AI_INFERENCE",
      is_explicit_general_rule: false,
      created_at: "2026-10-02T12:05:00Z",
    };

    expect(classification.target_type).toBe("SCENE");
    expect(feedbackClassificationSchema.title).toBe("FeedbackClassification");
    expect(feedbackClassificationSchema.required).toContain("classification_id");
    expect(feedbackClassificationSchema.required).toContain("category");

    const feedback: CreativeFeedback = {
      feedback_id: "fb_001",
      project_id: "prj_001",
      workspace_id: "ws_alpha",
      user_id: "usr_editor_1",
      plan_id: "cplan_001",
      user_rating: 4,
      liked_aspects: ["color_palette"],
      disliked_aspects: ["too_much_motion"],
      critique_text: "هذا المشهد حركته كثيرة",
      target_type: "SCENE",
      target_reference: "scene_001",
      classification,
      created_at: "2026-10-02T12:05:00Z",
    };

    expect(feedback.feedback_id).toBe("fb_001");
    expect(creativeFeedbackSchema.title).toBe("CreativeFeedback");
    expect(creativeFeedbackSchema.required).toContain("feedback_id");
    expect(creativeFeedbackSchema.required).toContain("project_id");

    const trace: StyleDecisionTrace = {
      dimension: "pacing",
      considered_value: "fast",
      considered_source: "CONFIRMED_USER_PREFERENCE",
      considered_confidence: 0.95,
      applied_value: "calm",
      is_overridden: true,
      override_reason: "Current explicit request overrides stored user preference",
      winning_source: "CURRENT_REQUEST",
    };

    const effectiveStyle: EffectiveUserStyle = {
      profile_id: "prof_test_user",
      workspace_id: "ws_alpha",
      user_id: "usr_editor_1",
      pacing: "calm",
      motion_intensity: "low",
      motion_personality: "Cinematic",
      trace_records: [trace],
      resolved_at: "2026-10-02T12:10:00Z",
    };

    expect(effectiveStyle.pacing).toBe("calm");
    expect(effectiveStyle.trace_records?.[0].is_overridden).toBe(true);
    expect(effectiveStyle.trace_records?.[0].winning_source).toBe("CURRENT_REQUEST");
    expect(effectiveUserStyleSchema.title).toBe("EffectiveUserStyle");
    expect(effectiveUserStyleSchema.required).toContain("workspace_id");
    expect(effectiveUserStyleSchema.required).toContain("resolved_at");
  });

  it("validates CreativeUsageEvent, CreativeProjectCostSummary, EfficiencyFinding, and CreativeCostAuditRun parity (S28-08C)", () => {
    const usageEvent: CreativeUsageEvent = {
      event_id: "use_123456789abc",
      workspace_id: "ws_alpha",
      project_id: "proj_99",
      run_id: "run_alpha_01",
      stage: "PLANNING",
      subsystem: "creative_planner",
      operation_type: "AI_COMPLETION",
      provider: "openai",
      model: "gpt-4o",
      input_tokens: 1200,
      output_tokens: 450,
      cached_input_tokens: 300,
      cache_hit: true,
      request_count: 1,
      generation_count: 0,
      retrieval_items: 0,
      latency_ms: 642.5,
      cost_provenance: "ESTIMATED",
      estimated_cost: "0.012750",
      currency: "USD",
      pricing_version: "2026.09.v1",
      created_at: "2026-10-02T12:00:00Z",
      input_hash: "hash_abc123",
      details: { tier: "REUSE" },
    };

    expect(usageEvent.event_id).toBe("use_123456789abc");
    expect(usageEvent.cost_provenance).toBe("ESTIMATED");
    expect(creativeUsageEventSchema.title).toBe("CreativeUsageEvent");
    expect(creativeUsageEventSchema.required).toContain("event_id");
    expect(creativeUsageEventSchema.required).toContain("workspace_id");

    const summary: CreativeProjectCostSummary = {
      workspace_id: "ws_alpha",
      project_id: "proj_99",
      run_count: 3,
      planning_tokens: 4500,
      retrieval_tokens: 1200,
      ai_calls: 5,
      generation_calls: 0,
      reuse_count: 4,
      compose_count: 1,
      create_count: 0,
      total_latency_ms: 2150.0,
      actual_cost: "0.000000",
      estimated_cost: "0.038500",
      currency: "USD",
      pricing_version: "2026.09.v1",
    };

    expect(summary.project_id).toBe("proj_99");
    expect(summary.reuse_count).toBe(4);
    expect(creativeProjectCostSummarySchema.title).toBe("CreativeProjectCostSummary");
    expect(creativeProjectCostSummarySchema.required).toContain("project_id");
    expect(creativeProjectCostSummarySchema.required).toContain("workspace_id");

    const finding: EfficiencyFinding = {
      finding_id: "eff_finding_01",
      workspace_id: "ws_alpha",
      project_id: "proj_99",
      run_id: "run_alpha_01",
      finding_type: "UNNECESSARY_GENERATION",
      severity: "CRITICAL",
      observed_value: 1,
      expected_bound: 0,
      evidence_refs: ["use_123456789abc"],
      summary: "Media generation invoked despite reusable template selected.",
    };

    expect(finding.finding_type).toBe("UNNECESSARY_GENERATION");
    expect(finding.severity).toBe("CRITICAL");
    expect(efficiencyFindingSchema.title).toBe("EfficiencyFinding");
    expect(efficiencyFindingSchema.required).toContain("finding_type");
    expect(efficiencyFindingSchema.required).toContain("severity");

    const auditRun: CreativeCostAuditRun = {
      run_id: "audit_run_01",
      policy_version: "S28-08C",
      projects_evaluated: 1,
      usage_totals: { total_ai_calls: 5 },
      cost_totals: { total_estimated_cost: "0.038500" },
      latency_summary: { avg_latency_ms: 430.0 },
      tier_distribution: { reuse_rate: 0.8, compose_rate: 0.2, create_rate: 0.0 },
      findings: [finding],
      started_at: "2026-10-02T12:00:00Z",
      completed_at: "2026-10-02T12:01:00Z",
      verdict: "PASS",
    };

    expect(auditRun.verdict).toBe("PASS");
    expect(creativeCostAuditRunSchema.title).toBe("CreativeCostAuditRun");
    expect(creativeCostAuditRunSchema.required).toContain("run_id");
  });
});

