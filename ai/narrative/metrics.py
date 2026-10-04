"""
ai/narrative/metrics.py
=======================
Evaluation metrics for NarrativePlans (S28-04).

Evaluates:
1. Goal Coverage
2. Logical Flow
3. Hook Relevance
4. Redundancy (Non-redundancy)
5. Duration Fit
6. Narrative-Type Appropriateness (e.g., Music Montage must not have spoken voiceover)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.narrative import NarrativePlan
from ai.narrative.contracts import NarrativeMetricsResult


class NarrativeMetricsEvaluator:
    """
    Evaluates a NarrativePlan against objective creative rubrics.
    """

    def evaluate(self, plan: NarrativePlan, brief: CreativeBrief) -> NarrativeMetricsResult:
        """Runs the multi-metric evaluation suite on a NarrativePlan."""
        details: Dict[str, Any] = {}

        # 1. Goal Coverage
        goal_score, goal_notes = self._evaluate_goal_coverage(plan, brief)
        details["goal_coverage"] = goal_notes

        # 2. Logical Flow
        flow_score, flow_notes = self._evaluate_logical_flow(plan)
        details["logical_flow"] = flow_notes

        # 3. Hook Relevance
        hook_score, hook_notes = self._evaluate_hook_relevance(plan, brief)
        details["hook_relevance"] = hook_notes

        # 4. Redundancy
        redundancy_score, redundancy_notes = self._evaluate_redundancy(plan)
        details["redundancy"] = redundancy_notes

        # 5. Duration Fit
        duration_score, duration_notes = self._evaluate_duration_fit(plan, brief)
        details["duration_fit"] = duration_notes

        # 6. Narrative Type Appropriateness
        type_score, type_notes = self._evaluate_narrative_type_appropriateness(plan, brief)
        details["narrative_type_appropriateness"] = type_notes

        # Passing threshold: all scores >= 0.70 and redundancy <= 0.35
        passed = (
            goal_score >= 0.70
            and flow_score >= 0.70
            and hook_score >= 0.70
            and redundancy_score <= 0.35
            and duration_score >= 0.80
            and type_score >= 0.80
        )

        return NarrativeMetricsResult(
            plan_id=plan.narrative_id,
            goal_coverage=round(goal_score, 2),
            logical_flow=round(flow_score, 2),
            hook_relevance=round(hook_score, 2),
            redundancy_score=round(redundancy_score, 2),
            duration_fit=round(duration_score, 2),
            narrative_type_appropriateness=round(type_score, 2),
            passed=passed,
            details=details,
        )

    def _evaluate_goal_coverage(self, plan: NarrativePlan, brief: CreativeBrief) -> Tuple[float, str]:
        all_text = " ".join([b.key_message for b in plan.beats]).lower()
        goal_words = set(re.findall(r"\w+", brief.interpreted_intent.goal.lower()))
        takeaway_words = set(re.findall(r"\w+", brief.interpreted_intent.key_takeaway.lower()))
        stop_words = {"the", "a", "an", "is", "in", "to", "for", "with", "and", "or", "of", "how", "this", "that"}
        key_words = (goal_words | takeaway_words) - stop_words

        if not key_words:
            return 1.0, "No specific keywords to check"

        matched = sum(1 for w in key_words if w in all_text)
        ratio = matched / max(len(key_words), 1)
        # Generous smoothing for creative rephrasing
        score = min(1.0, max(0.4, ratio + 0.3))
        return score, f"Keyword coverage {matched}/{len(key_words)}"

    def _evaluate_logical_flow(self, plan: NarrativePlan) -> Tuple[float, str]:
        phases = [b.phase.lower() for b in plan.beats]
        if not phases:
            return 0.0, "Empty beats"

        score = 1.0
        reasons = []

        # Hook / intro should be at index 0
        if not any(h in phases[0] for h in ["hook", "intro", "spark", "question", "visual_hook"]):
            score -= 0.3
            reasons.append("First beat is not a recognizable hook/intro phase")

        # CTA / Payoff / Resolution should be at the end
        last_phase = phases[-1]
        if not any(e in last_phase for e in ["cta", "payoff", "summary", "wrap_up", "resolution"]):
            score -= 0.2
            reasons.append("Final beat is not a closing/cta phase")

        # Check sequential monotonicity
        indices = [b.beat_index for b in plan.beats]
        if indices != list(range(len(indices))):
            score -= 0.5
            reasons.append("Beat indices are not strictly sequential")

        return max(0.0, score), "; ".join(reasons) or "Proper story arc structure"

    def _evaluate_hook_relevance(self, plan: NarrativePlan, brief: CreativeBrief) -> Tuple[float, str]:
        if not plan.beats:
            return 0.0, "No beats"
        first_beat = plan.beats[0]
        hook_msg = (first_beat.key_message + " " + (first_beat.visual_hook_description or "")).lower()

        # If audio mode is music only, visual hook is evaluated
        if brief.constraints.audio_mode == AudioMode.MUSIC_ONLY:
            if first_beat.visual_hook_description and len(first_beat.visual_hook_description) > 5:
                return 1.0, "Rich visual hook for music montage"
            return 0.5, "Sparse visual hook description"

        goal_keywords = [w for w in re.findall(r"\w+", brief.interpreted_intent.goal.lower()) if len(w) > 3]
        if any(w in hook_msg for w in goal_keywords):
            return 1.0, "Hook directly anchors brief goal"
        return 0.8, "Hook creates curiosity aligned with theme"

    def _evaluate_redundancy(self, plan: NarrativePlan) -> Tuple[float, str]:
        messages = [b.key_message.strip().lower() for b in plan.beats]
        unique_messages = set(messages)
        if len(unique_messages) < len(messages):
            # Duplicate beat message detected
            penalty = (len(messages) - len(unique_messages)) / len(messages)
            return min(1.0, penalty + 0.3), f"Duplicate beat messages detected: {len(messages) - len(unique_messages)}"

        # Check Jaccard overlap between consecutive beats
        max_overlap = 0.0
        for i in range(len(messages) - 1):
            w1 = set(messages[i].split())
            w2 = set(messages[i + 1].split())
            if w1 and w2:
                overlap = len(w1 & w2) / len(w1 | w2)
                max_overlap = max(max_overlap, overlap)

        if max_overlap > 0.6:
            return 0.5, f"High semantic word overlap ({round(max_overlap, 2)}) between consecutive beats"

        return round(max_overlap * 0.3, 2), "Low redundancy across beats"

    def _evaluate_duration_fit(self, plan: NarrativePlan, brief: CreativeBrief) -> Tuple[float, str]:
        c = brief.constraints
        actual = plan.estimated_total_duration_sec

        if c.target_duration_seconds is not None:
            target = c.target_duration_seconds
            diff = abs(actual - target)
            if diff <= 0.5:
                return 1.0, f"Exact duration match ({actual}s vs target {target}s)"
            elif diff <= 3.0:
                return 0.85, f"Close duration match ({actual}s vs target {target}s)"
            else:
                score = max(0.0, 1.0 - (diff / target))
                return score, f"Duration divergence ({actual}s vs target {target}s)"

        if c.min_duration_seconds is not None and actual < c.min_duration_seconds:
            return 0.4, f"Duration {actual}s below min {c.min_duration_seconds}s"

        if c.max_duration_seconds is not None and actual > c.max_duration_seconds:
            return 0.4, f"Duration {actual}s above max {c.max_duration_seconds}s"

        return 1.0, f"Duration {actual}s comfortably within bounds"

    def _evaluate_narrative_type_appropriateness(self, plan: NarrativePlan, brief: CreativeBrief) -> Tuple[float, str]:
        # Rule: Music montage must not have spoken voiceover requirements
        if brief.constraints.audio_mode == AudioMode.MUSIC_ONLY:
            for b in plan.beats:
                msg = b.key_message.lower()
                if "voiceover" in msg or "spoken" in msg or "narrator says" in msg:
                    return 0.2, "Violation: Spoken narrative script detected in MUSIC_ONLY montage"
            return 1.0, "Appropriate visual-only narrative for MUSIC_ONLY"

        # Rule: Explainer should have an explanatory mechanism beat
        video_type = (brief.interpreted_intent.video_type or "").upper()
        if "EXPLAINER" in video_type:
            phases = [b.phase.lower() for b in plan.beats]
            if not any(p in phases for p in ["mechanism", "foundation", "solution", "explanation"]):
                return 0.5, "Explainer missing core mechanism/explanation beat"

        return 1.0, "Narrative structure matches video archetype"
