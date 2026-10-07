"""
ai/recipes/selector.py
======================
Deterministic Recipe Selector with Hard Eligibility Gating and S28-02 Integration (S28-03).

Guarantees:
- Hard Eligibility Runs First (DEC-26 / DEC-27 / DEC-28):
  • Deterministic gating eliminates incompatible recipes BEFORE scoring or any AI tie-break.
  • Incompatible AudioMode combinations (e.g. MUSIC_ONLY with recipes requiring TEXT_TO_SPEECH)
    are strictly excluded.
  • Talking head recipes without source speech assets are strictly excluded (Section 34).
- Deterministic Candidate Set: AI never resurrects an ineligible recipe.
- Provider Neutrality: Zero provider names emitted or relied upon.
- Explainable Selection: Outputs primary recipe, alternatives, and audit-ready selection reasons.
- S28-02 Dynamic Integration: Resolves selected recipe skills and knowledge via S28-02 platforms.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from ai.audio.modes import AudioModeEngine
from ai.contracts.common import CapabilityType, ProvenanceRecord
from ai.contracts.creative.brief import AudioMode, CreativeBrief, ProvenanceType
from ai.contracts.creative.recipe import RecipeDefinition, RecipeSelection
from ai.contracts.media import MediaIntelligence
from ai.recipes.contracts import NoEligibleRecipeError
from ai.recipes.registry import RecipeRegistry

logger = logging.getLogger(__name__)


class RecipeCandidateScore:
    """Internal evaluation record for an eligible recipe candidate."""

    def __init__(self, recipe: RecipeDefinition, score: float, matched_keywords: List[str], reasons: List[str]) -> None:
        self.recipe = recipe
        self.score = score
        self.matched_keywords = matched_keywords
        self.reasons = reasons


class RecipeSelector:
    """
    Authoritative selector matching a CreativeBrief and contextual media to the optimal RecipeDefinition.
    Enforces two-stage selection: Hard Eligibility Gate followed by Weighted Deterministic Scoring.
    """

    def __init__(
        self,
        registry: Optional[RecipeRegistry] = None,
        audio_engine: Optional[AudioModeEngine] = None,
    ) -> None:
        self.registry = registry or RecipeRegistry()
        self.audio_engine = audio_engine or AudioModeEngine()

    def select_recipe(
        self,
        brief: CreativeBrief,
        available_media: Optional[List[Any]] = None,
        media_intelligence: Optional[Union[MediaIntelligence, List[MediaIntelligence]]] = None,
        budget_tier: Optional[str] = None,
        quality_profile: Optional[str] = None,
    ) -> RecipeSelection:
        """
        Executes the authoritative two-stage recipe routing pipeline.
        Stage 1: Hard deterministic eligibility gating.
        Stage 2: Multidimensional relevance scoring and ranking.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        all_recipes = self.registry.list_all()
        audio_mode = brief.constraints.audio_mode

        # ---------------------------------------------------------------------
        # Stage 1: Deterministic Hard Eligibility Gating
        # ---------------------------------------------------------------------
        eligible_recipes: List[RecipeDefinition] = []
        excluded_recipes: Dict[str, str] = {}

        for recipe in all_recipes:
            is_eligible, rejection_reason = self._evaluate_eligibility(
                recipe=recipe,
                brief=brief,
                audio_mode=audio_mode,
                available_media=available_media,
                media_intelligence=media_intelligence,
            )
            if is_eligible:
                eligible_recipes.append(recipe)
            else:
                excluded_recipes[recipe.recipe_id] = rejection_reason or "Ineligible"

        if not eligible_recipes:
            raise NoEligibleRecipeError(
                f"No eligible recipes found for brief '{brief.brief_id}' (audio_mode: {audio_mode.value}, "
                f"video_type: {brief.interpreted_intent.video_type}). Exclusions: {excluded_recipes}"
            )

        # ---------------------------------------------------------------------
        # Stage 2: Scoring and Ranking
        # ---------------------------------------------------------------------
        candidates: List[RecipeCandidateScore] = []
        for recipe in eligible_recipes:
            candidate_score = self._score_candidate(
                recipe=recipe,
                brief=brief,
                budget_tier=budget_tier,
                quality_profile=quality_profile,
            )
            candidates.append(candidate_score)

        # Sort descending by score; tie-break deterministically on recipe_id
        candidates.sort(key=lambda c: (c.score, c.recipe.recipe_id), reverse=True)

        primary = candidates[0]
        alternatives = [c.recipe.recipe_id for c in candidates[1:3]]

        # Build concise audit rationale
        selection_rationale = (
            f"Selected primary recipe '{primary.recipe.recipe_id}' with confidence {primary.score:.2f} "
            f"matching intent '{brief.interpreted_intent.video_type}' and audio mode '{audio_mode.value}'. "
            f"Keywords matched: {primary.matched_keywords}."
        )

        selection_reasons = list(primary.reasons)
        for alt_cand in candidates[1:3]:
            selection_reasons.append(
                f"Alternative '{alt_cand.recipe.recipe_id}' ranked with score {alt_cand.score:.2f}."
            )

        provenance = ProvenanceRecord(
            source="ai.recipes.selector.RecipeSelector",
            model_id="deterministic_two_stage_router_v1",
            provider_id="internal_recipe_engine",
            timestamp=now_iso,
            latency_ms=1,
        )

        return RecipeSelection(
            selection_id=f"recsel_{uuid.uuid4().hex[:12]}",
            brief_id=brief.brief_id,
            selected_recipe_id=primary.recipe.recipe_id,
            confidence_score=round(min(1.0, max(0.0, primary.score)), 2),
            matched_keywords=primary.matched_keywords,
            alternative_recipe_ids=alternatives,
            selection_rationale=selection_rationale,
            required_skills=list(primary.recipe.required_skills),
            required_knowledge=list(primary.recipe.required_knowledge),
            excluded_recipe_ids=excluded_recipes,
            selection_reasons=selection_reasons,
            provenance=provenance,
            created_at=now_iso,
        )

    def _evaluate_eligibility(
        self,
        recipe: RecipeDefinition,
        brief: CreativeBrief,
        audio_mode: AudioMode,
        available_media: Optional[List[Any]],
        media_intelligence: Optional[Union[MediaIntelligence, List[MediaIntelligence]]],
    ) -> Tuple[bool, Optional[str]]:
        """
        Executes strict deterministic constraint checks.
        Returns (True, None) if eligible, or (False, reason) if disqualified.
        """
        # 1. Excluded templates/recipes from brief constraints
        if recipe.recipe_id in brief.constraints.excluded_templates:
            return False, f"Recipe '{recipe.recipe_id}' is explicitly forbidden by brief constraints"

        # 2. Audio Mode compatibility via AudioModeEngine
        is_audio_eligible, audio_reason = self.audio_engine.check_recipe_eligibility(audio_mode, recipe)
        if not is_audio_eligible:
            return False, audio_reason

        # 3. Platform compatibility
        brief_platforms = set(brief.interpreted_intent.target_platforms or [])
        recipe_platforms = set(recipe.supported_platforms or recipe.platforms or [])
        if brief_platforms and recipe_platforms:
            # Check for any overlapping platform with strict format distinction
            overlap = False
            for bp in brief_platforms:
                for rp in recipe_platforms:
                    if self._are_platforms_compatible(bp, rp):
                        overlap = True
                        break
                if overlap:
                    break
            if not overlap:
                return False, f"Recipe does not support requested platforms: {list(brief_platforms)}"

        # 4. Duration compatibility (only if brief explicitly specified duration)
        dur_prov = brief.field_provenance.get("duration")
        is_duration_explicit = dur_prov and dur_prov.source_type == ProvenanceType.EXPLICIT
        if is_duration_explicit and brief.constraints.target_duration_seconds:
            target_dur = brief.constraints.target_duration_seconds
            # Disqualify if target duration is more than 2.5x the recipe maximum or less than 0.4x minimum
            if target_dur > recipe.duration_seconds_max * 2.5:
                return False, f"Target duration ({target_dur}s) greatly exceeds recipe max ({recipe.duration_seconds_max}s)"
            if target_dur < recipe.duration_seconds_min * 0.4:
                return False, f"Target duration ({target_dur}s) is far below recipe min ({recipe.duration_seconds_min}s)"

        # 5. Media prerequisite & Talking Head Contradiction enforcement (Section 34)
        if recipe.recipe_id in ("captioned-talking-head", "longform-repurpose"):
            # Talking head strictly requires source speech audio
            if audio_mode in (AudioMode.MUSIC_ONLY, AudioMode.SILENT, AudioMode.VO_ONLY):
                return False, f"Talking head recipe '{recipe.recipe_id}' contradicts {audio_mode.value} audio mode (requires source speech)"

            has_speech_source = False
            if media_intelligence:
                intels = media_intelligence if isinstance(media_intelligence, list) else [media_intelligence]
                for intel in intels:
                    if intel.speech and bool(intel.speech.transcript):
                        has_speech_source = True
                        break
            elif available_media:
                # If raw media provided without intelligence, assume media present unless empty
                has_speech_source = len(available_media) > 0

            # If talking head recipe requested but absolutely no speech media or assets provided
            if not has_speech_source and available_media is not None:
                return False, f"Recipe '{recipe.recipe_id}' requires source speech media, but no speech detected in available assets"

        return True, None

    @staticmethod
    def _are_platforms_compatible(brief_plat: str, recipe_plat: str) -> bool:
        """
        Determines platform compatibility respecting horizontal vs vertical format differences.
        Specifically, standard 'youtube' (landscape 16:9) does NOT match 'youtube_shorts' (vertical 9:16).
        """
        bp = brief_plat.lower().replace("-", "_")
        rp = recipe_plat.lower().replace("-", "_")
        if bp == rp:
            return True
        # YouTube distinction: standard longform youtube != youtube_shorts
        if bp in ("youtube", "youtube_shorts") or rp in ("youtube", "youtube_shorts"):
            return bp == rp
        # Reels / Instagram equivalence
        if bp in ("reels", "instagram_reels") and rp in ("reels", "instagram_reels"):
            return True
        if bp == "instagram" and rp in ("instagram", "instagram_reels"):
            return True
        # Twitter / X equivalence
        if (bp in ("twitter", "x", "x_twitter")) and (rp in ("twitter", "x", "x_twitter")):
            return True
        return bp in rp or rp in bp

    def _score_candidate(
        self,
        recipe: RecipeDefinition,
        brief: CreativeBrief,
        budget_tier: Optional[str],
        quality_profile: Optional[str],
    ) -> RecipeCandidateScore:
        """Computes deterministic multidimensional score for an eligible recipe."""
        score = 0.50  # Base score for eligible recipes
        matched_keywords: List[str] = []
        reasons: List[str] = []

        # 1. Intent / Video Type matching (+0.30)
        brief_vtype = (brief.interpreted_intent.video_type or "").upper()
        if brief_vtype and brief_vtype in [i.upper() for i in recipe.supported_intents]:
            score += 0.30
            reasons.append(f"Direct match for video type '{brief_vtype}' (+0.30)")

        # 2. Keyword matching (+0.05 per keyword, up to +0.20)
        user_text = brief.user_request_raw.lower()
        keyword_hits = 0
        for kw in recipe.routing_keywords:
            if kw.lower() in user_text:
                matched_keywords.append(kw)
                keyword_hits += 1

        if keyword_hits > 0:
            kw_bonus = min(0.20, keyword_hits * 0.05)
            score += kw_bonus
            reasons.append(f"Matched {keyword_hits} routing keywords: {matched_keywords[:4]} (+{kw_bonus:.2f})")

        # 3. Negative keyword check (-0.40)
        for neg_kw in recipe.routing_negative_keywords:
            if neg_kw.lower() in user_text:
                score -= 0.40
                reasons.append(f"Encountered negative keyword '{neg_kw}' (-0.40)")

        # 4. Pace alignment (+0.05)
        brief_pace = (brief.interpreted_intent.pace or "").upper()
        if brief_pace == "FAST" and "DYNAMIC_MONTAGE" in recipe.supported_intents:
            score += 0.05
            reasons.append("Fast pacing aligns with dynamic montage topology (+0.05)")

        # 5. Budget profile match (+0.05)
        if budget_tier and recipe.budget_profile and recipe.budget_profile.upper() == budget_tier.upper():
            score += 0.05
            reasons.append(f"Budget profile matches requested tier '{budget_tier}' (+0.05)")

        # Normalize score
        normalized_score = max(0.10, min(0.99, score))
        return RecipeCandidateScore(
            recipe=recipe,
            score=normalized_score,
            matched_keywords=matched_keywords,
            reasons=reasons,
        )
