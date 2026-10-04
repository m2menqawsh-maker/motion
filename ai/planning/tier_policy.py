"""
ai/planning/tier_policy.py
==========================
Authoritative Creative Tier Policy for S28-06 (Part C).

Deterministic machine-enforced policy governing:
REUSE (first priority)
  ↓ if insufficient
COMPOSE (second priority)
  ↓ if insufficient
CREATE-needed escalation (evidence-only, stops pipeline, NO runtime creation)

Critical Invariants:
1. Canonical Template Registry is reusable-template authority.
2. COMPOSE starts ONLY after REUSE is verified insufficient.
3. Escalation to CREATE is allowed ONLY when BOTH REUSE and COMPOSE are insufficient.
4. Anti-Bypass: Any caller or planner request for CREATE when REUSE or COMPOSE
   is sufficient is strictly REJECTED by policy.
5. No Evidence -> No Escalation. Full structured audit evidence is preserved.
6. S28-06 DOES NOT EXECUTE CREATE. Zero source code generation, zero workspace mutation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import (
    CompositionPlan,
    CreativePlan,
    CreativeTier,
    CreativeTierDecision,
    SceneIntent,
)
from ai.planning.compose_engine import ComposeEngine
from ai.planning.errors import TemplateRegistryUnavailableError
from ai.planning.reuse_engine import ReuseEngine
from scripts.core.template_contract import TemplateContractError


class CreativeTierPolicy:
    """
    Deterministic machine-enforced policy engine evaluating and selecting
    the implementation tier (REUSE, COMPOSE, or CREATE escalation) per scene.
    """

    def __init__(
        self,
        reuse_engine: Optional[ReuseEngine] = None,
        compose_engine: Optional[ComposeEngine] = None,
    ) -> None:
        self.reuse_engine = reuse_engine or ReuseEngine()
        self.compose_engine = compose_engine or ComposeEngine()

    def reload(self) -> None:
        """Reloads policy engines and contract caches deterministically."""
        if hasattr(self.reuse_engine, "reload"):
            self.reuse_engine.reload()

    def decide(
        self,
        scene_intent: SceneIntent,
        requested_tier: Optional[CreativeTier] = None,
        aspect_ratio: str = "9:16",
        audio_mode: Optional[AudioMode] = None,
        expected_family: Optional[str] = None,
        required_props: Optional[List[str]] = None,
        required_media: Optional[List[str]] = None,
        candidate_composition: Optional[CompositionPlan] = None,
        template_aspect_overrides: Optional[Dict[str, List[str]]] = None,
        force_unregistered_id_for_testing: Optional[str] = None,
        force_unknown_component_for_testing: Optional[str] = None,
    ) -> CreativeTierDecision:
        """
        Evaluates scene intent across tiers in deterministic order (REUSE -> COMPOSE -> CREATE-needed).
        Enforces anti-bypass rules and guarantees evidence completeness.
        """
        decision_id = f"dec_{scene_intent.scene_id}"
        need_desc = f"{scene_intent.intent_label} ({scene_intent.primary_visual_job}, aspect={aspect_ratio})"

        # ---------------------------------------------------------------------
        # Tier 1: REUSE Evaluation (Section 8-22)
        # ---------------------------------------------------------------------
        # Invariant: Template Registry must be valid & available to evaluate REUSE/COMPOSE.
        # Registry failure must NEVER silently justify CREATE escalation (S28-08D Sec 11).
        contract = getattr(self.reuse_engine, "contract", None)
        if not contract or len(contract.list_canonical_ids()) == 0:
            raise TemplateRegistryUnavailableError(
                "Template Registry is unavailable, empty, or unreadable. Cannot evaluate tier sufficiency."
            )

        try:
            reuse_res = self.reuse_engine.evaluate(
                scene_intent=scene_intent,
                aspect_ratio=aspect_ratio,
                audio_mode=audio_mode,
                expected_family=expected_family,
                required_props=required_props,
                required_media=required_media,
                template_aspect_overrides=template_aspect_overrides,
                force_unregistered_id_for_testing=force_unregistered_id_for_testing,
            )
        except (TemplateContractError, FileNotFoundError, json.JSONDecodeError) as exc:
            raise TemplateRegistryUnavailableError(f"Template Registry failure during reuse evaluation: {exc}") from exc

        reuse_checked = list(reuse_res.candidates_checked)

        if reuse_res.sufficiency and reuse_res.selected_candidate:
            # Check for Anti-Bypass attempt (Section 37, 74)
            if requested_tier in (CreativeTier.CREATE, CreativeTier.COMPOSE):
                rationale = (
                    f"Anti-Bypass Enforcement: Caller requested {requested_tier.value}, but matching registered "
                    f"template '{reuse_res.selected_candidate}' is sufficient (fit score {reuse_res.ranked_candidates[0].fit_score:.2f}). "
                    f"Bypass request denied by policy. REUSE tier enforced."
                )
            else:
                rationale = reuse_res.rationale

            return CreativeTierDecision(
                decision_id=decision_id,
                scene_id=scene_intent.scene_id,
                selected_tier=CreativeTier.REUSE,
                rationale=rationale,
                template_ref=reuse_res.selected_candidate,
                composite_elements=[],
                needs_create_evaluation=False,
                requested_need=need_desc,
                reuse_candidates_checked=reuse_checked,
                reuse_result=reuse_res,
                compose_candidates_checked=[],
                compose_result=None,
                composition_plan=None,
            )

        # ---------------------------------------------------------------------
        # Tier 2: COMPOSE Evaluation (Starts ONLY after REUSE is insufficient)
        # ---------------------------------------------------------------------
        try:
            compose_res = self.compose_engine.evaluate(
                scene_intent=scene_intent,
                reuse_result=reuse_res,
                candidate_plan=candidate_composition,
                audio_mode=audio_mode,
                aspect_ratio=aspect_ratio,
                force_unknown_component_for_testing=force_unknown_component_for_testing,
            )
        except (TemplateContractError, FileNotFoundError, json.JSONDecodeError) as exc:
            raise TemplateRegistryUnavailableError(f"Template Registry failure during compose evaluation: {exc}") from exc

        compose_checked = list(compose_res.components_checked)

        if compose_res.sufficiency and compose_res.composition_plan:
            # Check for Anti-Bypass attempt (Section 38, 75)
            if requested_tier == CreativeTier.CREATE:
                rationale = (
                    f"Anti-Bypass Enforcement: Caller requested CREATE, but registered Lego composition "
                    f"using base '{compose_res.composition_plan.base_template_or_primitive}' is sufficient. "
                    f"Escalation denied by policy. COMPOSE tier enforced."
                )
            else:
                rationale = (
                    f"REUSE insufficient ({reuse_res.rationale}). "
                    f"COMPOSE sufficient using registered Lego anchor '{compose_res.composition_plan.base_template_or_primitive}' "
                    f"and {len(compose_res.composition_plan.layers)} layers."
                )

            composite_elements = [compose_res.composition_plan.base_template_or_primitive] + [
                layer.element_ref for layer in compose_res.composition_plan.layers
            ]

            return CreativeTierDecision(
                decision_id=decision_id,
                scene_id=scene_intent.scene_id,
                selected_tier=CreativeTier.COMPOSE,
                rationale=rationale,
                template_ref=compose_res.composition_plan.base_template_or_primitive,
                composite_elements=composite_elements,
                needs_create_evaluation=False,
                requested_need=need_desc,
                reuse_candidates_checked=reuse_checked,
                reuse_result=reuse_res,
                compose_candidates_checked=compose_checked,
                compose_result=compose_res,
                composition_plan=compose_res.composition_plan,
            )

        # ---------------------------------------------------------------------
        # Tier 3: Escalation to CREATE-needed (Both REUSE and COMPOSE insufficient)
        # ---------------------------------------------------------------------
        # Full audit evidence is required (Section 35, 39, 40)
        rationale = (
            f"Escalation to CREATE justified: REUSE insufficient ({reuse_res.rationale}) "
            f"and COMPOSE insufficient ({compose_res.rationale}). "
            f"Candidate creation needed for S28-07 evaluation."
        )

        decision = CreativeTierDecision(
            decision_id=decision_id,
            scene_id=scene_intent.scene_id,
            selected_tier=CreativeTier.CREATE,
            rationale=rationale,
            template_ref=None,
            composite_elements=[],
            needs_create_evaluation=True,  # Signals escalation for S28-07
            requested_need=need_desc,
            reuse_candidates_checked=reuse_checked,
            reuse_result=reuse_res,
            compose_candidates_checked=compose_checked,
            compose_result=compose_res,
            composition_plan=None,
        )

        # Invariant (Section 36, 70): STOP! NO CREATE EXECUTION!
        return decision

    def decide_for_plan(
        self,
        creative_plan: CreativePlan,
        aspect_ratio: str = "9:16",
        audio_mode: Optional[AudioMode] = None,
    ) -> List[CreativeTierDecision]:
        """
        Evaluates tier decisions for all scenes in a CreativePlan independently (Section 92).
        Supports multi-scene heterogeneous tiers (e.g. Scene 1 REUSE, Scene 2 COMPOSE, Scene 3 CREATE).
        """
        decisions: List[CreativeTierDecision] = []
        for scene in sorted(creative_plan.scenes, key=lambda s: s.scene_index):
            dec = self.decide(
                scene_intent=scene,
                aspect_ratio=aspect_ratio,
                audio_mode=audio_mode,
            )
            decisions.append(dec)
        return decisions
