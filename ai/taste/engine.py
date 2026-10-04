"""
ai/taste/engine.py
==================
Taste Engine (v1): evaluates applicable taste rules and synthesizes auditable TasteDecisions (S28-04).

Guarantees:
- Taste ≠ QC: Taste guides aesthetic choices and proposals; never overrides QC or Core lifecycle.
- Traceability: Every TasteDecision records governing rule, citation, evidence, and confidence.
- No Hidden CoT: Stores only short, auditable rationale summaries.
- Provider Neutrality: Zero hardcoded third-party vendor SDKs.
- Zero Registry Mutation: Registry remains read-only during taste evaluation.
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Optional
from ai.contracts.creative.taste import TasteContext, TasteDecision, TasteRule
from ai.taste.evaluator import TasteEvaluator
from ai.taste.registry import TasteRuleRegistry

logger = logging.getLogger(__name__)


class TasteEngine:
    """
    Evaluates creative principles against the project's NarrativePlan and context,
    yielding structured, traceable TasteDecisions.
    """

    def __init__(
        self,
        registry: Optional[TasteRuleRegistry] = None,
        evaluator: Optional[TasteEvaluator] = None,
    ) -> None:
        self.registry = registry or TasteRuleRegistry()
        self.evaluator = evaluator or TasteEvaluator()

    def evaluate_taste(self, context: TasteContext) -> List[TasteDecision]:
        """
        Executes taste evaluation across global project context and individual narrative beats.
        Yields a typed List[TasteDecision].
        """
        decisions: List[TasteDecision] = []
        rules = self.registry.list_all()

        # 1. Global / Canvas-level rule evaluation
        for rule in rules:
            res = self.evaluator.evaluate(rule, context, target_ref="canvas_global")
            if res.is_applicable:
                decision = TasteDecision(
                    decision_id=f"dec_{uuid.uuid4().hex[:12]}",
                    rule_id=rule.rule_id,
                    context_ref="canvas_global",
                    applied_value=rule.recommendation or str(rule.parameters),
                    reasoning=rule.rationale,
                    citation=rule.citation_source,
                    confidence=res.confidence,
                    rule_ids=[rule.rule_id],
                    evidence=res.evidence,
                    reason_summary=f"Applied {rule.name}: {rule.recommendation}",
                )
                decisions.append(decision)

        # 2. Beat-specific rule evaluations
        for beat in context.narrative_plan.beats:
            beat_ref = beat.beat_id
            for rule in rules:
                if rule.category in ["typography", "gesture", "sound_design", "rhythm"]:
                    res = self.evaluator.evaluate(rule, context, target_ref=beat_ref)
                    if res.is_applicable:
                        # Avoid duplicating identical rule on the same target ref
                        already_decided = any(d.rule_id == rule.rule_id and d.context_ref == beat_ref for d in decisions)
                        if not already_decided:
                            decision = TasteDecision(
                                decision_id=f"dec_{uuid.uuid4().hex[:12]}",
                                rule_id=rule.rule_id,
                                context_ref=beat_ref,
                                applied_value=f"Beat {beat.beat_index} ({beat.phase}): {rule.recommendation}",
                                reasoning=f"{rule.rationale} Aligned with beat phase '{beat.phase}'.",
                                citation=rule.citation_source,
                                confidence=res.confidence,
                                rule_ids=[rule.rule_id],
                                evidence=res.evidence,
                                reason_summary=f"Beat {beat.beat_id} guided by {rule.name}.",
                            )
                            decisions.append(decision)

        return decisions
