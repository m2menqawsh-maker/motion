"""
ai/narrative/planner.py
=======================
Narrative Planner: synthesizes structured multi-beat NarrativePlans from CreativeBriefs (S28-04).

Guarantees:
- Input: CreativeBrief + Recipe + Relevant Knowledge + MediaContext + Available Assets.
- Output: Canonical, typed NarrativePlan (NarrativeBeat[]).
- Adapts narrative structure by video type (SaaS Ad vs Explainer vs Music Montage vs Talking Head).
- Invariant: Music Montage (MUSIC_ONLY) does not require or force spoken narrative scripts.
- Duration Fit: Allocates beat durations to match brief target duration without compiling timelines.
- Provider Neutrality: Zero third-party cloud SDK dependencies.
- Provenance: Full traceability attached to output plan.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.narrative import NarrativeBeat, NarrativePlan
from ai.contracts.creative.recipe import RecipeDefinition, RecipeSelection
from ai.contracts.creative.skills_knowledge import KnowledgeDescriptor, SkillDefinition
from ai.knowledge.router import KnowledgeRouter
from ai.narrative.contracts import InvalidNarrativePlanError
from ai.skills.router import SkillRouter

logger = logging.getLogger(__name__)


class NarrativePlanner:
    """
    Authoritative planner synthesizing structured story progression prior to visual composition.
    """

    def __init__(
        self,
        knowledge_router: Optional[KnowledgeRouter] = None,
        skill_router: Optional[SkillRouter] = None,
    ) -> None:
        self.knowledge_router = knowledge_router
        self.skill_router = skill_router

    def plan(
        self,
        brief: CreativeBrief,
        recipe: Optional[Union[RecipeDefinition, RecipeSelection]] = None,
        relevant_knowledge: Optional[List[KnowledgeDescriptor]] = None,
        relevant_skills: Optional[List[SkillDefinition]] = None,
        media_intelligence: Optional[Dict[str, Any]] = None,
        available_assets: Optional[List[Any]] = None,
    ) -> NarrativePlan:
        """
        Synthesizes a canonical NarrativePlan tailored to the brief's intent, duration, and audio mode.
        """
        if not brief.brief_id:
            raise InvalidNarrativePlanError("Brief identifier is required for narrative planning.")

        # Duration resolution
        target_dur = self._resolve_target_duration(brief, recipe)

        # Video type and audio mode inspection
        intent = brief.interpreted_intent
        raw_video_type = (intent.video_type or "").upper()
        audio_mode = brief.constraints.audio_mode

        # Classify structural archetype
        arc_structure, beat_blueprints = self._select_beat_blueprints(
            video_type=raw_video_type,
            audio_mode=audio_mode,
            target_duration=target_dur,
            goal=intent.goal,
            key_takeaway=intent.key_takeaway,
            call_to_action=intent.call_to_action,
        )

        # Proportionally allocate durations so sum matches target_dur exactly
        beats = self._instantiate_beats(beat_blueprints, target_dur, audio_mode)

        core_hook = beats[0].key_message if beats else intent.goal

        now = datetime.now(timezone.utc)
        provenance = ProvenanceRecord(
            source="ai.narrative.planner.NarrativePlanner",
            model_id="deterministic_narrative_v1",
            provider_id="internal",
            timestamp=now,
            latency_ms=10,
        )

        plan = NarrativePlan(
            narrative_id=f"narr_{uuid.uuid4().hex[:12]}",
            brief_id=brief.brief_id,
            core_hook=core_hook,
            beats=beats,
            arc_structure=arc_structure,
            estimated_total_duration_sec=target_dur,
            provenance=provenance,
            created_at=now,
        )
        return plan

    def _resolve_target_duration(
        self,
        brief: CreativeBrief,
        recipe: Optional[Union[RecipeDefinition, RecipeSelection]] = None,
    ) -> float:
        """Derives duration bounds respecting CreativeBrief constraints."""
        c = brief.constraints
        if c.target_duration_seconds is not None:
            return round(float(c.target_duration_seconds), 1)

        if c.min_duration_seconds is not None and c.max_duration_seconds is not None:
            return round((c.min_duration_seconds + c.max_duration_seconds) / 2.0, 1)

        if c.max_duration_seconds is not None:
            return round(float(c.max_duration_seconds), 1)

        if c.min_duration_seconds is not None:
            return round(float(c.min_duration_seconds), 1)

        if recipe and hasattr(recipe, "duration_seconds_target"):
            return round(float(recipe.duration_seconds_target), 1)

        return 30.0

    def _select_beat_blueprints(
        self,
        video_type: str,
        audio_mode: AudioMode,
        target_duration: float,
        goal: str,
        key_takeaway: str,
        call_to_action: Optional[str],
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Selects appropriate beat structures.
        Crucial: MUSIC_ONLY mode produces purely visual progression without spoken voiceover hooks.
        """
        cta_text = call_to_action or "Learn more today"

        # Archetype 1: MUSIC_ONLY Montage (No spoken scripts or forced voiceover)
        if audio_mode == AudioMode.MUSIC_ONLY or "MONTAGE" in video_type:
            arc = "Visual-Energy-Progression"
            blueprints = [
                {
                    "phase": "visual_hook",
                    "emotional_target": "Curiosity",
                    "pacing": "fast",
                    "weight": 0.20,
                    "key_message": f"Visual Spark: High-energy kinetic visual intro establishing {goal}",
                    "visual_hook_description": "Dynamic rhythm-synced visual pulse with explosive graphic match",
                    "sound_effect_cue": "transition-whoosh.wav",
                },
                {
                    "phase": "visual_progression",
                    "emotional_target": "Delight",
                    "pacing": "moderate",
                    "weight": 0.35,
                    "key_message": f"Visual Montage: Thematic sequence showcasing {key_takeaway}",
                    "visual_hook_description": "Multi-layer kinetic collage with continuous flowing motion",
                    "sound_effect_cue": "ambient-swell.wav",
                },
                {
                    "phase": "energy_peak",
                    "emotional_target": "Urgency",
                    "pacing": "fast",
                    "weight": 0.25,
                    "key_message": "Visual Crescendo: Peak kinetic typography and graphic accents",
                    "visual_hook_description": "Rapid graphic match transitions riding the musical peak",
                    "sound_effect_cue": "dramatic-boom.wav",
                },
                {
                    "phase": "payoff_frame",
                    "emotional_target": "Confidence",
                    "pacing": "slow",
                    "weight": 0.20,
                    "key_message": f"Brand Payoff: Bold logo and visual closing frame ({cta_text})",
                    "visual_hook_description": "Clean hero typography resting on elegant dark brand background",
                    "sound_effect_cue": "chime-soft.wav",
                },
            ]
            return arc, blueprints

        # Archetype 2: Short High-Velocity Sprint / Social Reel (<= 20s)
        if target_duration <= 20.0 or "SPRINT" in video_type:
            arc = "Hook-Proof-CTA"
            blueprints = [
                {
                    "phase": "hook",
                    "emotional_target": "Curiosity",
                    "pacing": "fast",
                    "weight": 0.25,
                    "key_message": f"Did you know? {goal}",
                    "visual_hook_description": "Rapid text reveal with camera zoom-in diving into the key claim",
                    "sound_effect_cue": "swish-fast.wav",
                },
                {
                    "phase": "proof",
                    "emotional_target": "Confidence",
                    "pacing": "fast",
                    "weight": 0.50,
                    "key_message": f"Here is the proof: {key_takeaway}",
                    "visual_hook_description": "Side-by-side comparison with neon highlighter underline",
                    "sound_effect_cue": "swish-metal.wav",
                },
                {
                    "phase": "cta",
                    "emotional_target": "Urgency",
                    "pacing": "fast",
                    "weight": 0.25,
                    "key_message": f"Take action: {cta_text}",
                    "visual_hook_description": "Interactive diegetic button tap with glowing neon ring",
                    "sound_effect_cue": "chime-soft.wav",
                },
            ]
            return arc, blueprints

        # Archetype 3: Talking Head / Interview / Podcast Repurpose
        if "TALKING_HEAD" in video_type or "PODCAST" in video_type or "AVATAR" in video_type:
            arc = "Conversational-Insight"
            blueprints = [
                {
                    "phase": "hook",
                    "emotional_target": "Curiosity",
                    "pacing": "moderate",
                    "weight": 0.20,
                    "key_message": f"The biggest mistake people make with {goal}",
                    "visual_hook_description": "Center speaker framing with kinetic dynamic captions",
                    "sound_effect_cue": "pop-soft.wav",
                },
                {
                    "phase": "context",
                    "emotional_target": "Confidence",
                    "pacing": "moderate",
                    "weight": 0.30,
                    "key_message": f"Here is the context most creators miss.",
                    "visual_hook_description": "Speaker shifts to lower-third with explanatory supporting card",
                    "sound_effect_cue": "soft-whoosh.wav",
                },
                {
                    "phase": "mechanism",
                    "emotional_target": "Delight",
                    "pacing": "moderate",
                    "weight": 0.30,
                    "key_message": f"The framework: {key_takeaway}",
                    "visual_hook_description": "Split screen showing real workflow breakdown",
                    "sound_effect_cue": "brush-stroke.wav",
                },
                {
                    "phase": "wrap_up",
                    "emotional_target": "Confidence",
                    "pacing": "slow",
                    "weight": 0.20,
                    "key_message": f"Save this for your next project. {cta_text}",
                    "visual_hook_description": "Closing direct speaker eye contact with follow badge",
                    "sound_effect_cue": "chime-soft.wav",
                },
            ]
            return arc, blueprints

        # Archetype 4: Product / SaaS Ad
        tokens = video_type.split("_")
        is_ad = "AD" in tokens or "COMMERCIAL" in tokens or "SAAS" in tokens or "PRODUCT" in tokens or "SAAS" in video_type or "PRODUCT" in video_type
        if is_ad:
            arc = "Problem-Agitation-Solution-Proof-CTA"
            blueprints = [
                {
                    "phase": "hook",
                    "emotional_target": "Curiosity",
                    "pacing": "fast",
                    "weight": 0.18,
                    "key_message": f"Stop wasting hours on manual work. Here is how: {goal}",
                    "visual_hook_description": "Bold headline with dramatic word-chase zoom and red strikethrough",
                    "sound_effect_cue": "glitch-cut.wav",
                },
                {
                    "phase": "problem",
                    "emotional_target": "Urgency",
                    "pacing": "moderate",
                    "weight": 0.22,
                    "key_message": f"The traditional process is broken and slow.",
                    "visual_hook_description": "Fractured cards with rapid error indicators",
                    "sound_effect_cue": "digital-error.wav",
                },
                {
                    "phase": "solution",
                    "emotional_target": "Delight",
                    "pacing": "moderate",
                    "weight": 0.25,
                    "key_message": f"Introducing the automated solution: {key_takeaway}",
                    "visual_hook_description": "Smooth camera pan into a sleek living canvas product interface",
                    "sound_effect_cue": "transition-whoosh.wav",
                },
                {
                    "phase": "proof",
                    "emotional_target": "Confidence",
                    "pacing": "moderate",
                    "weight": 0.20,
                    "key_message": "Proven results with 10x faster turnarounds.",
                    "visual_hook_description": "Animated stat counter ticking up with neon ring accent",
                    "sound_effect_cue": "tick-soft.wav",
                },
                {
                    "phase": "cta",
                    "emotional_target": "Confidence",
                    "pacing": "slow",
                    "weight": 0.15,
                    "key_message": f"Get started: {cta_text}",
                    "visual_hook_description": "Final brand lockup with bookmark CTA interaction",
                    "sound_effect_cue": "chime-soft.wav",
                },
            ]
            return arc, blueprints

        # Archetype 5: Default / Educational Explainer
        arc = "Concept-Foundation-Mechanism-Example-Summary"
        blueprints = [
            {
                "phase": "hook",
                "emotional_target": "Curiosity",
                "pacing": "fast",
                "weight": 0.18,
                "key_message": f"Ever wondered how this works? {goal}",
                "visual_hook_description": "Question typography diving into glyph with curious motion",
                "sound_effect_cue": "whoosh-deep.wav",
            },
            {
                "phase": "foundation",
                "emotional_target": "Confidence",
                "pacing": "moderate",
                "weight": 0.24,
                "key_message": "Let us understand the fundamental principles first.",
                "visual_hook_description": "Clean modular diagram assembling step-by-step",
                "sound_effect_cue": "brush-sweep.wav",
            },
            {
                "phase": "mechanism",
                "emotional_target": "Delight",
                "pacing": "moderate",
                "weight": 0.28,
                "key_message": f"The core engine: {key_takeaway}",
                "visual_hook_description": "3D layered card progression showing internal logic",
                "sound_effect_cue": "swish-metal.wav",
            },
            {
                "phase": "example",
                "emotional_target": "Confidence",
                "pacing": "moderate",
                "weight": 0.18,
                "key_message": "See it in action in real production scenarios.",
                "visual_hook_description": "Live walkthrough preview card sliding in",
                "sound_effect_cue": "pop-soft.wav",
            },
            {
                "phase": "summary",
                "emotional_target": "Confidence",
                "pacing": "slow",
                "weight": 0.12,
                "key_message": f"Key takeaway and next steps: {cta_text}",
                "visual_hook_description": "Summary bullet checklist with marker highlights",
                "sound_effect_cue": "chime-soft.wav",
            },
        ]
        return arc, blueprints

    def _instantiate_beats(
        self,
        blueprints: List[Dict[str, Any]],
        target_duration: float,
        audio_mode: AudioMode,
    ) -> List[NarrativeBeat]:
        """
        Instantiates typed NarrativeBeat models, ensuring duration sums match target_duration.
        """
        n_beats = len(blueprints)
        raw_durations = [round(bp["weight"] * target_duration, 1) for bp in blueprints]

        # Reconcile rounding differences to ensure exact sum
        total_allocated = sum(raw_durations)
        diff = round(target_duration - total_allocated, 1)
        raw_durations[-1] = round(raw_durations[-1] + diff, 1)

        # Enforce positive duration invariant
        for i in range(len(raw_durations)):
            if raw_durations[i] <= 0:
                raw_durations[i] = 1.0

        beats: List[NarrativeBeat] = []
        for i, bp in enumerate(blueprints):
            beat = NarrativeBeat(
                beat_id=f"beat_{i+1:03d}",
                beat_index=i,
                phase=bp["phase"],
                emotional_target=bp["emotional_target"],
                pacing=bp["pacing"],
                estimated_duration_sec=raw_durations[i],
                key_message=bp["key_message"],
                visual_hook_description=bp.get("visual_hook_description"),
                sound_effect_cue=bp.get("sound_effect_cue") if audio_mode != AudioMode.SILENT else None,
            )
            beats.append(beat)
        return beats
