"""
ai/regression/rubric_grader.py
==============================
Rubric and Pairwise Grading Engine for Creative Regression (S28-08B).

Reuses the canonical S28-04 CreativeRubricsEvaluator without creating a redundant judge.
Invariants:
- Rubrics measure Brief Adherence, Narrative Coherence, Pacing, Visual Intent,
  Emotional Fit, and Overdesign Avoidance.
- Pairwise comparisons (A vs B) produce structured verdicts with per-dimension deltas.
- Calibration compares automated grading against human ground truth.
- Invariant: Taste evaluation != QC. Rubrics cannot approve production promotion.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field

from ai.contracts.base import AIContractModel
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.conflict import ResolvedCreativeGuidance
from ai.contracts.creative.regression import (
    JudgeCalibrationRecord,
    PairwiseGradeResult,
)
from ai.narrative.metrics import NarrativeMetricsEvaluator

logger = logging.getLogger(__name__)


class ScenarioRubricScores(AIContractModel):
    """Rubric evaluation scores for a creative output [0.0 - 1.0]."""
    brief_adherence: float = Field(ge=0.0, le=1.0)
    narrative_coherence: float = Field(ge=0.0, le=1.0)
    pacing: float = Field(ge=0.0, le=1.0)
    visual_intent: float = Field(ge=0.0, le=1.0)
    emotional_fit: float = Field(ge=0.0, le=1.0)
    overdesign_avoidance: float = Field(ge=0.0, le=1.0)
    composite_score: float = Field(ge=0.0, le=1.0)
    passed: bool


class PairwiseComparisonResult(AIContractModel):
    """Pairwise evaluation comparing Candidate A vs Candidate B."""
    scenario_id: str
    preferred_candidate: str  # "A" or "B" or "TIE"
    margin: float
    rubric_deltas: Dict[str, float]
    rationale: str


class CreativeRubricsEvaluator:
    """
    Evaluates creative guidance outputs against deterministic and heuristic rubrics.
    """

    def __init__(self) -> None:
        self.narrative_metrics = NarrativeMetricsEvaluator()

    def evaluate_guidance(
        self,
        guidance: ResolvedCreativeGuidance,
        brief: CreativeBrief,
    ) -> ScenarioRubricScores:
        """Evaluates resolved creative guidance across all 6 core rubrics."""
        # 1. Brief Adherence
        brief_score = self._score_brief_adherence(guidance, brief)

        # 2. Narrative Coherence
        narrative_res = self.narrative_metrics.evaluate(guidance.narrative_plan, brief)
        narrative_score = round(
            (narrative_res.goal_coverage + narrative_res.logical_flow + narrative_res.hook_relevance) / 3.0,
            2,
        )

        # 3. Pacing
        pacing_score = self._score_pacing(guidance, brief)

        # 4. Visual Intent
        visual_score = self._score_visual_intent(guidance)

        # 5. Emotional Fit
        emotional_score = self._score_emotional_fit(guidance, brief)

        # 6. Overdesign Avoidance
        overdesign_score = self._score_overdesign_avoidance(guidance)

        composite = round(
            (brief_score * 0.25)
            + (narrative_score * 0.20)
            + (pacing_score * 0.15)
            + (visual_score * 0.15)
            + (emotional_score * 0.15)
            + (overdesign_score * 0.10),
            2,
        )

        passed = (
            composite >= 0.75
            and brief_score >= 0.70
            and narrative_score >= 0.70
            and guidance.status == "SUCCESS"
        )

        return ScenarioRubricScores(
            brief_adherence=brief_score,
            narrative_coherence=narrative_score,
            pacing=pacing_score,
            visual_intent=visual_score,
            emotional_fit=emotional_score,
            overdesign_avoidance=overdesign_score,
            composite_score=composite,
            passed=passed,
        )

    def _score_brief_adherence(self, guidance: ResolvedCreativeGuidance, brief: CreativeBrief) -> float:
        score = 1.0
        # Check AudioMode compliance
        audio_mode = brief.constraints.audio_mode
        if audio_mode == AudioMode.SILENT:
            if any(len(s.sound_cues) > 0 for s in guidance.sfx_directions):
                score -= 0.5
        elif audio_mode == AudioMode.MUSIC_ONLY:
            if any(bool(n.spoken_line) for n in guidance.narrative_directions):
                score -= 0.5

        # Check duration match
        target_dur = brief.constraints.target_duration_seconds or 30.0
        diff = abs(guidance.narrative_plan.estimated_total_duration_sec - target_dur)
        if diff > 3.0:
            score -= min(0.3, diff / target_dur)

        # Check unresolved conflict penalty
        if guidance.unresolved_conflicts:
            score -= 0.4

        return max(0.0, round(score, 2))

    def _score_pacing(self, guidance: ResolvedCreativeGuidance, brief: CreativeBrief) -> float:
        beats = guidance.narrative_plan.beats
        if not beats:
            return 0.0

        durations = [b.estimated_duration_sec for b in beats]
        # Check rollercoaster effect: durations should vary (not all identical)
        variance = max(durations) - min(durations)
        if len(durations) > 2 and variance < 0.5:
            return 0.6  # Monotonous pacing penalty

        return 0.95

    def _score_visual_intent(self, guidance: ResolvedCreativeGuidance) -> float:
        motion_dirs = guidance.motion_directions
        if not motion_dirs:
            return 0.0

        score = 1.0
        # Check that camera intent and hierarchy are defined
        for m in motion_dirs:
            if not m.camera_intent or not m.visual_hierarchy:
                score -= 0.1

        # Overdesign penalty reduces visual intent clarity
        explosive_count = sum(1 for m in motion_dirs if m.motion_energy == "explosive")
        if explosive_count > len(motion_dirs) / 2.0:
            score -= 0.30

        return max(0.2, round(score, 2))

    def _score_emotional_fit(self, guidance: ResolvedCreativeGuidance, brief: CreativeBrief) -> float:
        emotion_dirs = guidance.emotion_directions
        if not emotion_dirs:
            return 0.5

        # Check for direct emotional incongruity
        brief_tone = (brief.interpreted_intent.tone or "").lower()
        is_energetic = any(w in brief_tone for w in ["energetic", "dynamic", "fast", "bold", "hype", "celebration"])
        is_calm_luxury = any(w in brief_tone for w in ["calm", "luxury", "premium", "elegant", "sophisticated"])

        for e in emotion_dirs:
            pe = e.primary_emotion.lower()
            if is_energetic and any(w in pe for w in ["grief", "sorrow", "sadness", "depression"]):
                return 0.30  # Heavy mismatch: grief in an energetic brief
            if is_calm_luxury and any(w in pe for w in ["panic", "chaos", "frenzy"]):
                return 0.35

        valid_progressions = sum(1 for e in emotion_dirs if e.emotional_progression and e.primary_emotion)
        ratio = valid_progressions / len(emotion_dirs)
        return round(0.5 + (ratio * 0.45), 2)

    def _score_overdesign_avoidance(self, guidance: ResolvedCreativeGuidance) -> float:
        motion_dirs = guidance.motion_directions
        if not motion_dirs:
            return 1.0

        explosive_count = sum(1 for m in motion_dirs if m.motion_energy == "explosive")
        if explosive_count > len(motion_dirs) / 2.0:
            return 0.20  # Constant explosive motion penalty

        return 0.95

    def compare_pairwise(
        self,
        scenario_id: str,
        guidance_a: ResolvedCreativeGuidance,
        guidance_b: ResolvedCreativeGuidance,
        brief: CreativeBrief,
    ) -> PairwiseComparisonResult:
        """Performs pairwise comparison between Candidate A and Candidate B."""
        scores_a = self.evaluate_guidance(guidance_a, brief)
        scores_b = self.evaluate_guidance(guidance_b, brief)

        margin = round(scores_a.composite_score - scores_b.composite_score, 2)
        if margin > 0.05:
            preferred = "A"
            rationale = f"Candidate A outperforms Candidate B by +{margin} composite score."
        elif margin < -0.05:
            preferred = "B"
            rationale = f"Candidate B outperforms Candidate A by +{abs(margin)} composite score."
        else:
            preferred = "TIE"
            rationale = f"Candidates are equivalent within 0.05 margin (delta={margin})."

        deltas = {
            "brief_adherence": round(scores_a.brief_adherence - scores_b.brief_adherence, 2),
            "narrative_coherence": round(scores_a.narrative_coherence - scores_b.narrative_coherence, 2),
            "pacing": round(scores_a.pacing - scores_b.pacing, 2),
            "visual_intent": round(scores_a.visual_intent - scores_b.visual_intent, 2),
            "emotional_fit": round(scores_a.emotional_fit - scores_b.emotional_fit, 2),
            "overdesign_avoidance": round(scores_a.overdesign_avoidance - scores_b.overdesign_avoidance, 2),
        }

        return PairwiseComparisonResult(
            scenario_id=scenario_id,
            preferred_candidate=preferred,
            margin=abs(margin),
            rubric_deltas=deltas,
            rationale=rationale,
        )


class RubricGrader:
    """
    Grader wrapping canonical CreativeRubricsEvaluator for regression testing.
    """

    def __init__(self) -> None:
        self._evaluator = CreativeRubricsEvaluator()

    def grade_guidance(
        self,
        guidance: ResolvedCreativeGuidance,
        brief: CreativeBrief,
        thresholds: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Grades creative guidance against brief using canonical rubrics.
        """
        scores = self._evaluator.evaluate_guidance(guidance, brief)
        thresh = thresholds or {}
        min_composite = thresh.get("composite_score", 0.75)
        min_brief = thresh.get("brief_adherence", 0.70)
        min_narrative = thresh.get("narrative_coherence", 0.70)
        min_overdesign = thresh.get("overdesign_avoidance", 0.70)

        passed = (
            scores.composite_score >= min_composite
            and scores.brief_adherence >= min_brief
            and scores.narrative_coherence >= min_narrative
            and scores.overdesign_avoidance >= min_overdesign
            and guidance.status == "SUCCESS"
        )

        reasons = []
        if scores.composite_score < min_composite:
            reasons.append(f"Composite score ({scores.composite_score}) < threshold ({min_composite})")
        if scores.brief_adherence < min_brief:
            reasons.append(f"Brief adherence ({scores.brief_adherence}) < threshold ({min_brief})")
        if scores.narrative_coherence < min_narrative:
            reasons.append(f"Narrative coherence ({scores.narrative_coherence}) < threshold ({min_narrative})")
        if scores.overdesign_avoidance < min_overdesign:
            reasons.append(f"Overdesign avoidance ({scores.overdesign_avoidance}) < threshold ({min_overdesign})")
        if guidance.status != "SUCCESS":
            reasons.append(f"Guidance status is '{guidance.status}', expected 'SUCCESS'")

        return {
            "passed": passed,
            "composite_score": scores.composite_score,
            "score_breakdown": {
                "brief_adherence": scores.brief_adherence,
                "narrative_coherence": scores.narrative_coherence,
                "pacing": scores.pacing,
                "visual_intent": scores.visual_intent,
                "emotional_fit": scores.emotional_fit,
                "overdesign_avoidance": scores.overdesign_avoidance,
            },
            "reasons": reasons,
        }

    def compare_pairwise(
        self,
        scenario_id: str,
        guidance_a: ResolvedCreativeGuidance,
        guidance_b: ResolvedCreativeGuidance,
        brief: CreativeBrief,
    ) -> PairwiseGradeResult:
        """
        Executes structured pairwise comparison between candidate A and candidate B.
        """
        res = self._evaluator.compare_pairwise(scenario_id, guidance_a, guidance_b, brief)
        return PairwiseGradeResult(
            scenario_id=res.scenario_id,
            preferred_candidate=res.preferred_candidate,
            margin=res.margin,
            per_dimension_deltas=res.rubric_deltas,
            rationale=res.rationale,
        )

    def evaluate_calibration(
        self,
        calibration_pairs: List[Tuple[str, ResolvedCreativeGuidance, ResolvedCreativeGuidance, CreativeBrief, str]],
        min_agreement_rate: float = 0.80,
    ) -> JudgeCalibrationRecord:
        """
        Evaluates agreement between automated pairwise grading and human ground truth labels.
        Each item in calibration_pairs is: (scenario_id, cand_a, cand_b, brief, expected_human_pref)
        """
        total = len(calibration_pairs)
        if total == 0:
            return JudgeCalibrationRecord(
                total_calibration_pairs=0,
                agreement_count=0,
                agreement_rate=1.0,
                disagreements=[],
                calibrated=True,
            )

        agreements = 0
        disagreements: List[Dict[str, Any]] = []

        for sc_id, cand_a, cand_b, brief, human_pref in calibration_pairs:
            cmp_res = self.compare_pairwise(sc_id, cand_a, cand_b, brief)
            if cmp_res.preferred_candidate == human_pref:
                agreements += 1
            else:
                disagreements.append({
                    "scenario_id": sc_id,
                    "human_pref": human_pref,
                    "evaluator_pref": cmp_res.preferred_candidate,
                    "margin": cmp_res.margin,
                    "rationale": cmp_res.rationale,
                })

        rate = round(agreements / total, 4)
        calibrated = rate >= min_agreement_rate

        return JudgeCalibrationRecord(
            total_calibration_pairs=total,
            agreement_count=agreements,
            agreement_rate=rate,
            disagreements=disagreements,
            calibrated=calibrated,
            calibration_method="DETERMINISTIC_RUBRICS",
        )

    def grade_rubric_scores(
        self,
        scores: Dict[str, float],
        thresholds: Dict[str, float],
    ) -> Tuple[bool, List[str]]:
        """Evaluates numerical rubric metric scores against required thresholds."""
        reasons = []
        passed = True
        for metric, thresh in thresholds.items():
            val = scores.get(metric, 1.0)
            if val < thresh:
                passed = False
                reasons.append(f"Metric '{metric}' score ({val}) < threshold ({thresh})")
        return passed, reasons

    def evaluate_pairwise(
        self,
        scenario_id: str,
        scores_a: Dict[str, float],
        scores_b: Dict[str, float],
    ) -> PairwiseGradeResult:
        """Executes structured pairwise comparison using score dictionaries."""
        mean_a = sum(scores_a.values()) / max(1, len(scores_a))
        mean_b = sum(scores_b.values()) / max(1, len(scores_b))
        delta = round(abs(mean_a - mean_b), 4)
        margin = min(1.0, delta)

        per_dim_deltas = {}
        all_keys = set(scores_a.keys()) | set(scores_b.keys())
        for k in all_keys:
            per_dim_deltas[k] = round(scores_a.get(k, 0.0) - scores_b.get(k, 0.0), 4)

        if delta < 0.05:
            pref = "TIE"
            rationale = f"Candidates A and B are of comparable quality within margin {delta} <= 0.05."
        elif mean_a > mean_b:
            pref = "A"
            rationale = f"Candidate A outperformed B with composite margin of {delta}."
        else:
            pref = "B"
            rationale = f"Candidate B outperformed A with composite margin of {delta}."

        return PairwiseGradeResult(
            scenario_id=scenario_id,
            preferred_candidate=pref,
            margin=margin,
            per_dimension_deltas=per_dim_deltas,
            rationale=rationale,
        )

    def calibrate_against_ground_truth(
        self,
        ground_truth: List[Dict[str, Any]],
        evaluator_decisions: List[Dict[str, Any]],
        min_agreement_threshold: float = 0.80,
    ) -> JudgeCalibrationRecord:
        """Evaluates calibration against a list of human-labeled scenario outcomes."""
        eval_map = {d["scenario_id"]: d.get("preferred_candidate") for d in evaluator_decisions}
        agreements = 0
        disagreements = []
        total = len(ground_truth)

        for gt in ground_truth:
            sc_id = gt["scenario_id"]
            human_pref = gt.get("human_preferred")
            eval_pref = eval_map.get(sc_id)
            if human_pref == eval_pref:
                agreements += 1
            else:
                disagreements.append({
                    "scenario_id": sc_id,
                    "human_preferred": human_pref,
                    "evaluator_preferred": eval_pref,
                })

        rate = round(agreements / max(1, total), 4)
        calibrated = rate >= min_agreement_threshold

        return JudgeCalibrationRecord(
            total_calibration_pairs=total,
            agreement_count=agreements,
            agreement_rate=rate,
            disagreements=disagreements,
            calibrated=calibrated,
            calibration_method="DETERMINISTIC_RUBRICS",
        )

