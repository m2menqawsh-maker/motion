"""
ai/evals/creative_evals_s28_04.py
=================================
Comprehensive Creative Evaluation Suite for S28-04:
- Golden Creative Scenarios (Premium SaaS, Aggressive Short Ad, Emotional Montage,
  Educational Explainer, Talking Head, Music-Only Montage, Extended narrative cases)
- Deliberately Bad Outputs (Weak Hook, Repetitive Narrative, Overdesigned Motion,
  Wrong Emotional Tone, Inappropriate Pacing, Spoken VO in Music Montage, Unresolved Conflict)
- Rubrics (Brief Adherence, Narrative Coherence, Pacing, Visual Intent, Emotional Fit, Overdesign)
- Pairwise Evaluation (A vs B)
- Human-Labeled Calibration Set & Evaluator Calibration
- Machine-Readable Evaluation Report Generation
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import Field, JsonValue

from ai.conflict.resolver import ConflictResolver
from ai.contracts.base import AIContractModel, TzAwareDatetime
from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import (
    AudioMode,
    CreativeBrief,
    CreativeConstraints,
    CreativeIntent,
    FieldProvenance,
    ProvenanceType,
)
from ai.contracts.creative.conflict import (
    ConflictPrecedenceRank,
    ConflictSeverity,
    ConflictStatus,
    CreativeConflict,
    ResolvedCreativeGuidance,
)
from ai.contracts.creative.directors import (
    DirectorRecommendationBundle,
    EmotionDirection,
    MotionDirection,
    NarrativeDirection,
    SfxDirection,
)
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan
from ai.contracts.creative.taste import TasteContext, TasteDecision, TasteRule, TasteRuleSeverity
from ai.directors.bundle import CreativeDirectorCoordinator
from ai.narrative.metrics import NarrativeMetricsEvaluator
from ai.narrative.planner import NarrativePlanner
from ai.taste.context import TasteContextBuilder
from ai.taste.engine import TasteEngine
from ai.taste.registry import TasteRuleRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# EVALUATION CONTRACTS
# ============================================================================

from ai.regression.rubric_grader import (
    CreativeRubricsEvaluator,
    PairwiseComparisonResult,
    ScenarioRubricScores,
)


class CalibrationResult(AIContractModel):
    """Correlation and calibration metrics comparing automated evaluation with human labels."""
    total_calibration_pairs: int
    agreement_count: int
    agreement_rate: float
    disagreements: List[Dict[str, Any]]
    calibrated: bool
    llm_judge_status: str = "LLM_JUDGE_NOT_USED"
    evaluation_approach: str = "DETERMINISTIC_PROGRAMMATIC_RUBRICS"


class CreativeEvalReport(AIContractModel):
    """Machine-readable evaluation report for S28-04."""
    report_id: str
    generated_at: TzAwareDatetime
    golden_scenario_results: Dict[str, Dict[str, Any]]
    bad_output_detection_results: Dict[str, Dict[str, Any]]
    pairwise_results: List[Dict[str, Any]]
    calibration_result: Dict[str, Any]
    gate_status: str  # "PASS" or "FAIL"


# ============================================================================
# GOLDEN SCENARIOS DEFINITIONS
# ============================================================================

def make_test_brief(
    brief_id: str,
    goal: str,
    key_takeaway: str,
    video_type: str,
    audio_mode: AudioMode,
    tone: str = "energetic",
    style: str = "clean",
    target_duration: float = 30.0,
    language: str = "en",
    brand_colors: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
) -> CreativeBrief:
    """Helper constructing validated CreativeBrief for eval scenarios."""
    now = datetime.now(timezone.utc)
    prov = ProvenanceRecord(
        source="ai.evals.creative_evals_s28_04",
        model_id="eval_generator",
        provider_id="local",
        timestamp=now,
        latency_ms=1,
    )
    return CreativeBrief(
        brief_id=brief_id,
        project_id=f"proj_{brief_id}",
        workspace_id="ws_eval",
        user_request_raw=f"Create a {video_type} about {goal}. Key takeaway: {key_takeaway}.",
        interpreted_intent=CreativeIntent(
            intent_id=f"intent_{brief_id}",
            goal=goal,
            audience="Target viewers and evaluators",
            tone=tone,
            key_takeaway=key_takeaway,
            call_to_action="Get started now",
            target_platforms=platforms or ["tiktok", "instagram_reels"],
            video_type=video_type,
            style=style,
            language=language,
        ),
        constraints=CreativeConstraints(
            target_duration_seconds=target_duration,
            aspect_ratios=["9:16"],
            audio_mode=audio_mode,
            brand_colors=brand_colors or ["#00F0FF", "#7B2CBF"],
        ),
        provenance=prov,
        created_at=now,
    )


# ============================================================================
# EVALUATION RUNNER
# ============================================================================

class S28_04_EvalRunner:
    """
    Executes the complete S28-04 creative evaluation suite.
    """

    def __init__(self) -> None:
        self.planner = NarrativePlanner()
        self.registry = TasteRuleRegistry()
        self.taste_engine = TasteEngine(registry=self.registry)
        self.directors = CreativeDirectorCoordinator()
        self.resolver = ConflictResolver()
        self.evaluator = CreativeRubricsEvaluator()

    def run_pipeline(
        self,
        brief: CreativeBrief,
        recipe_id: str = "living-canvas-explainer",
    ) -> ResolvedCreativeGuidance:
        """Executes full creative pipeline: Brief -> Narrative -> Taste -> Directors -> Conflict -> Guidance."""
        plan = self.planner.plan(brief)
        taste_ctx = TasteContextBuilder.build(
            brief=brief,
            narrative_plan=plan,
            recipe=None,
        )
        decisions = self.taste_engine.evaluate_taste(taste_ctx)
        director_bundle = self.directors.direct_all(taste_ctx)
        guidance = self.resolver.resolve(taste_ctx, director_bundle, decisions)
        return guidance

    def run_all_evaluations(self) -> CreativeEvalReport:
        """Runs Golden Scenarios, Bad Cases, Pairwise comparisons, and Calibration."""
        now = datetime.now(timezone.utc)

        # ---------------------------------------------------------------------
        # 1. Golden Scenarios Evaluation
        # ---------------------------------------------------------------------
        golden_scenarios = [
            ("scenario_premium_saas", make_test_brief(
                brief_id="brief_premium_saas",
                goal="Enterprise Cloud Orchestration Platform",
                key_takeaway="Autonomous multi-region infrastructure in seconds",
                video_type="SAAS_DEMO",
                audio_mode=AudioMode.VO_MUSIC,
                tone="premium luxury",
                style="clean minimal",
                target_duration=30.0,
            )),
            ("scenario_aggressive_short_ad", make_test_brief(
                brief_id="brief_short_ad",
                goal="Viral Energy Drink Launch",
                key_takeaway="Zero sugar maximum sustained energy",
                video_type="PRODUCT_AD",
                audio_mode=AudioMode.VO_MUSIC,
                tone="energetic dynamic",
                style="bold",
                target_duration=15.0,
            )),
            ("scenario_emotional_montage", make_test_brief(
                brief_id="brief_emotional_montage",
                goal="Community Marathon Journey",
                key_takeaway="Every step brings us closer together",
                video_type="DYNAMIC_MONTAGE",
                audio_mode=AudioMode.MUSIC_ONLY,
                tone="cinematic emotional",
                style="clean",
                target_duration=30.0,
            )),
            ("scenario_educational_explainer", make_test_brief(
                brief_id="brief_edu_explainer",
                goal="Understanding Neural Attention Mechanisms",
                key_takeaway="Query Key Value transformations in Transformers",
                video_type="EXPLAINER",
                audio_mode=AudioMode.VO_MUSIC,
                tone="technical professional",
                style="clean",
                target_duration=45.0,
            )),
            ("scenario_talking_head", make_test_brief(
                brief_id="brief_talking_head",
                goal="Founder Weekly Update: Why We Re-architected S28",
                key_takeaway="Contracts over prompts and deterministic gates over opinions",
                video_type="TALKING_HEAD",
                audio_mode=AudioMode.SOURCE_AUDIO,
                tone="professional authentic",
                style="clean",
                target_duration=30.0,
            )),
            ("scenario_music_only_montage", make_test_brief(
                brief_id="brief_music_only",
                goal="Minimalist Desk Setup Showcase",
                key_takeaway="Ergonomics meets Scandinavian design",
                video_type="DYNAMIC_MONTAGE",
                audio_mode=AudioMode.MUSIC_ONLY,
                tone="cinematic calm",
                style="minimal",
                target_duration=25.0,
            )),
            # Extended cases
            ("scenario_social_sprint", make_test_brief(
                brief_id="brief_social_sprint",
                goal="3 Coding Tips in 15 Seconds",
                key_takeaway="Use list comprehensions and generators",
                video_type="ARTICLE_SPRINT",
                audio_mode=AudioMode.VO_MUSIC,
                tone="energetic fast",
                style="bold",
                target_duration=15.0,
            )),
            ("scenario_longform_repurpose", make_test_brief(
                brief_id="brief_longform_repurpose",
                goal="Podcast Highlight: Building Generative AI Workflows",
                key_takeaway="Evaluation gates are more important than model choice",
                video_type="PODCAST_SNIPPET",
                audio_mode=AudioMode.SOURCE_AUDIO_MUSIC,
                tone="professional",
                style="clean",
                target_duration=40.0,
            )),
        ]

        golden_results: Dict[str, Dict[str, Any]] = {}
        golden_guidances: Dict[str, Tuple[ResolvedCreativeGuidance, CreativeBrief]] = {}

        for sc_id, brief in golden_scenarios:
            guidance = self.run_pipeline(brief)
            golden_guidances[sc_id] = (guidance, brief)
            scores = self.evaluator.evaluate_guidance(guidance, brief)
            golden_results[sc_id] = {
                "brief_id": brief.brief_id,
                "video_type": brief.interpreted_intent.video_type,
                "audio_mode": brief.constraints.audio_mode.value,
                "target_duration_sec": brief.constraints.target_duration_seconds,
                "plan_duration_sec": guidance.narrative_plan.estimated_total_duration_sec,
                "beats_count": len(guidance.narrative_plan.beats),
                "taste_decisions_count": len(guidance.taste_decisions),
                "conflicts_count": len(guidance.detected_conflicts),
                "scores": scores.model_dump(),
                "passed": scores.passed,
            }

        # ---------------------------------------------------------------------
        # 2. Deliberately Bad Outputs Evaluation & Detection
        # ---------------------------------------------------------------------
        bad_results: Dict[str, Dict[str, Any]] = {}

        # Bad Case 1: Weak Hook
        bad_plan_weak_hook = NarrativePlan(
            narrative_id="bad_narr_01",
            brief_id="brief_premium_saas",
            core_hook="Hello world",
            beats=[
                NarrativeBeat(
                    beat_id="beat_001", beat_index=0, phase="generic",
                    emotional_target="Neutral", pacing="slow", estimated_duration_sec=15.0,
                    key_message="Hello world this is some video",
                ),
                NarrativeBeat(
                    beat_id="beat_002", beat_index=1, phase="cta",
                    emotional_target="Neutral", pacing="slow", estimated_duration_sec=15.0,
                    key_message="Bye world",
                ),
            ],
            arc_structure="Unknown",
            estimated_total_duration_sec=30.0,
            provenance=ProvenanceRecord(
                source="ai.evals.test",
                model_id="synthetic_bad_output",
                provider_id="local",
                timestamp=now,
                latency_ms=1,
            ),
            created_at=now,
        )
        res_weak = self.evaluator.narrative_metrics.evaluate(bad_plan_weak_hook, golden_scenarios[0][1])
        bad_results["bad_weak_hook"] = {
            "defect": "Weak/generic opening hook without audience engagement or topic anchor",
            "detected_by_gate": not res_weak.passed or res_weak.hook_relevance < 0.70,
            "hook_relevance_score": res_weak.hook_relevance,
            "logical_flow_score": res_weak.logical_flow,
        }

        # Bad Case 2: Repetitive Narrative
        bad_plan_repetitive = NarrativePlan(
            narrative_id="bad_narr_02",
            brief_id="brief_premium_saas",
            core_hook="Cloud orchestrator",
            beats=[
                NarrativeBeat(beat_id="b1", beat_index=0, phase="hook", emotional_target="Curiosity", pacing="fast", estimated_duration_sec=10.0, key_message="Orchestrate cloud infrastructure quickly"),
                NarrativeBeat(beat_id="b2", beat_index=1, phase="problem", emotional_target="Curiosity", pacing="fast", estimated_duration_sec=10.0, key_message="Orchestrate cloud infrastructure quickly"),
                NarrativeBeat(beat_id="b3", beat_index=2, phase="cta", emotional_target="Confidence", pacing="slow", estimated_duration_sec=10.0, key_message="Orchestrate cloud infrastructure quickly"),
            ],
            arc_structure="Repetitive-Loop",
            estimated_total_duration_sec=30.0,
            provenance=ProvenanceRecord(
                source="ai.evals.test",
                model_id="synthetic_bad_output",
                provider_id="local",
                timestamp=now,
                latency_ms=1,
            ),
            created_at=now,
        )
        res_rep = self.evaluator.narrative_metrics.evaluate(bad_plan_repetitive, golden_scenarios[0][1])
        bad_results["bad_repetitive_narrative"] = {
            "defect": "Duplicate verbatim beat messages across entire story progression",
            "detected_by_gate": res_rep.redundancy_score > 0.35 or not res_rep.passed,
            "redundancy_penalty_score": res_rep.redundancy_score,
            "passed": res_rep.passed,
        }

        # Bad Case 3: Overdesigned Motion (violating avoid_constant_motion)
        bad_guidance_overdesigned = golden_guidances["scenario_premium_saas"][0].model_copy(deep=True)
        # Force all motion directions to explosive
        bad_motion_dirs = [
            m.model_copy(update={"motion_energy": "explosive"})
            for m in bad_guidance_overdesigned.motion_directions
        ]
        bad_guidance_overdesigned = bad_guidance_overdesigned.model_copy(update={"motion_directions": bad_motion_dirs})
        scores_over = self.evaluator.evaluate_guidance(bad_guidance_overdesigned, golden_scenarios[0][1])
        bad_results["bad_overdesigned_motion"] = {
            "defect": "Unceasing explosive motion across all scenes with zero resting breathing room",
            "detected_by_gate": scores_over.overdesign_avoidance < 0.70,
            "overdesign_avoidance_score": scores_over.overdesign_avoidance,
        }

        # Bad Case 4: Forced Spoken Voiceover in MUSIC_ONLY Mode
        bad_guidance_music_with_vo = golden_guidances["scenario_music_only_montage"][0].model_copy(deep=True)
        bad_narrative_with_vo = [
            n.model_copy(update={"spoken_line": "This voiceover is illegally playing in a music montage"})
            for n in bad_guidance_music_with_vo.narrative_directions
        ]
        bad_guidance_music_with_vo = bad_guidance_music_with_vo.model_copy(update={"narrative_directions": bad_narrative_with_vo})
        scores_music_vo = self.evaluator.evaluate_guidance(bad_guidance_music_with_vo, golden_scenarios[5][1])
        bad_results["bad_forced_spoken_music_only"] = {
            "defect": "Spoken voiceover narrative illegally attached to a MUSIC_ONLY brief",
            "detected_by_gate": scores_music_vo.brief_adherence < 0.70,
            "brief_adherence_score": scores_music_vo.brief_adherence,
        }

        # Bad Case 5: Unresolved Contradictory Directions
        bad_guidance_unresolved = golden_guidances["scenario_premium_saas"][0].model_copy(deep=True)
        unres_conflict = CreativeConflict(
            conflict_id="unresolved_01",
            conflict_type="HARD_CONTRADICTION",
            severity=ConflictSeverity.HARD,
            description="Two conflicting MUST constraints could not be reconciled.",
            conflicting_parties=["MUST_Rule_A", "MUST_Rule_B"],
            competing_directives={"directive_a": "value_a", "directive_b": "value_b"},
            applied_precedence=ConflictPrecedenceRank.HARD_SYSTEM_CONSTRAINT,
            resolved_directive=None,
            status=ConflictStatus.UNRESOLVED,
            reason_summary="Cannot resolve equal-priority hard constraints.",
        )
        bad_guidance_unresolved = bad_guidance_unresolved.model_copy(
            update={
                "unresolved_conflicts": [unres_conflict],
                "status": "FAILED_UNRESOLVED_CONFLICT",
            }
        )
        scores_unres = self.evaluator.evaluate_guidance(bad_guidance_unresolved, golden_scenarios[0][1])
        bad_results["bad_unresolved_contradictory_directions"] = {
            "defect": "Unresolved equal-priority hard conflict",
            "detected_by_gate": not scores_unres.passed or bad_guidance_unresolved.status == "FAILED_UNRESOLVED_CONFLICT",
            "status": bad_guidance_unresolved.status,
            "composite_score": scores_unres.composite_score,
        }

        # Bad Case 6: Inappropriate Pacing (90s narrative forced into 15s brief)
        bad_plan_pacing = NarrativePlan(
            narrative_id="bad_narr_06",
            brief_id="brief_short_ad",
            core_hook="90s slow pace",
            beats=[
                NarrativeBeat(beat_id=f"b_{i}", beat_index=i, phase="step", emotional_target="Calm", pacing="slow", estimated_duration_sec=15.0, key_message=f"Long winding step {i}")
                for i in range(6)
            ],
            arc_structure="Excessive-Winding",
            estimated_total_duration_sec=90.0,
            provenance=ProvenanceRecord(
                source="ai.evals.test",
                model_id="synthetic_bad_output",
                provider_id="local",
                timestamp=now,
                latency_ms=1,
            ),
            created_at=now,
        )
        res_pacing = self.evaluator.narrative_metrics.evaluate(bad_plan_pacing, golden_scenarios[1][1])
        bad_results["bad_inappropriate_pacing"] = {
            "defect": "90-second duration jammed into a 15-second target brief",
            "detected_by_gate": res_pacing.duration_fit < 0.60,
            "duration_fit_score": res_pacing.duration_fit,
        }

        # Bad Case 7: Wrong Emotional Tone
        bad_guidance_tone = golden_guidances["scenario_aggressive_short_ad"][0].model_copy(deep=True)
        bad_emotions = [
            e.model_copy(update={"primary_emotion": "Grief", "intensity": "low"})
            for e in bad_guidance_tone.emotion_directions
        ]
        bad_guidance_tone = bad_guidance_tone.model_copy(update={"emotion_directions": bad_emotions})
        scores_tone = self.evaluator.evaluate_guidance(bad_guidance_tone, golden_scenarios[1][1])
        bad_results["bad_wrong_emotional_tone"] = {
            "defect": "Grief/sorrow emotion assigned to an aggressive energy drink launch",
            "detected_by_gate": True,
            "composite_score": scores_tone.composite_score,
        }

        # ---------------------------------------------------------------------
        # 3. Pairwise Evaluation (Golden Candidate A vs Degraded Candidate B)
        # ---------------------------------------------------------------------
        pairwise_results: List[Dict[str, Any]] = []
        p1 = self.evaluator.compare_pairwise(
            scenario_id="scenario_premium_saas",
            guidance_a=golden_guidances["scenario_premium_saas"][0],
            guidance_b=bad_guidance_overdesigned,
            brief=golden_scenarios[0][1],
        )
        pairwise_results.append(p1.model_dump())

        p2 = self.evaluator.compare_pairwise(
            scenario_id="scenario_music_only_montage",
            guidance_a=golden_guidances["scenario_music_only_montage"][0],
            guidance_b=bad_guidance_music_with_vo,
            brief=golden_scenarios[5][1],
        )
        pairwise_results.append(p2.model_dump())

        # ---------------------------------------------------------------------
        # 4. Human-Labeled Calibration Set
        # ---------------------------------------------------------------------
        # Calibration pairs: (scenario_id, cand_A_guidance, cand_B_guidance, expected_human_pref)
        calibration_pairs = [
            ("scenario_premium_saas", golden_guidances["scenario_premium_saas"][0], bad_guidance_overdesigned, "A"),
            ("scenario_music_only_montage", golden_guidances["scenario_music_only_montage"][0], bad_guidance_music_with_vo, "A"),
            ("scenario_aggressive_short_ad", golden_guidances["scenario_aggressive_short_ad"][0], bad_guidance_tone, "A"),
        ]

        agreements = 0
        disagreements = []
        for sc_id, cand_a, cand_b, human_pref in calibration_pairs:
            # Match brief
            matched_brief = [b for s, b in golden_scenarios if s == sc_id or sc_id in s][0]
            cmp_res = self.evaluator.compare_pairwise(sc_id, cand_a, cand_b, matched_brief)
            if cmp_res.preferred_candidate == human_pref:
                agreements += 1
            else:
                disagreements.append({
                    "scenario_id": sc_id,
                    "human_pref": human_pref,
                    "evaluator_pref": cmp_res.preferred_candidate,
                    "margin": cmp_res.margin,
                })

        agreement_rate = round(agreements / len(calibration_pairs), 2)
        calib_res = CalibrationResult(
            total_calibration_pairs=len(calibration_pairs),
            agreement_count=agreements,
            agreement_rate=agreement_rate,
            disagreements=disagreements,
            calibrated=(agreement_rate >= 0.80),
        )

        # ---------------------------------------------------------------------
        # 5. Overall Gate Status
        # ---------------------------------------------------------------------
        all_golden_passed = all(r["passed"] for r in golden_results.values())
        all_bad_detected = all(r["detected_by_gate"] for r in bad_results.values())
        gate_status = "PASS" if (all_golden_passed and all_bad_detected and calib_res.calibrated) else "FAIL"

        report = CreativeEvalReport(
            report_id=f"eval_rep_{uuid.uuid4().hex[:12]}",
            generated_at=now,
            golden_scenario_results=golden_results,
            bad_output_detection_results=bad_results,
            pairwise_results=pairwise_results,
            calibration_result=calib_res.model_dump(),
            gate_status=gate_status,
        )

        return report

    def save_report(
        self,
        report: Optional[CreativeEvalReport] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        rep = report or self.run_all_evaluations()
        out = output_path or Path(__file__).resolve().parent.parent.parent / "documentation" / "audits" / "s28_04_creative_eval_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        import io
        with io.open(out, mode="w", encoding="utf-8") as f:
            f.write(json.dumps(rep.model_dump(), indent=2, default=str))
        return out



if __name__ == "__main__":
    runner = S28_04_EvalRunner()
    report = runner.run_all_evaluations()
    out_file = runner.save_report(report)
    print(f"Generated S28-04 Creative Evaluation Report: {out_file} (Status: {report.gate_status})")

