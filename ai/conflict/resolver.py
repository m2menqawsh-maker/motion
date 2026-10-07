"""
ai/conflict/resolver.py
=======================
Creative Conflict Resolver: detects, evaluates, and resolves creative contradictions (S28-04).

Precedence Authority:
1. HARD_SYSTEM_CONSTRAINT (AudioMode, security, lifecycle bounds)
2. USER_EXPLICIT_REQUIREMENT (User brief explicit intent and constraints)
3. RECIPE_CONSTRAINT (Recipe workflow topology and platform bounds)
4. DIRECTOR_RECOMMENDATION (Creative Directors structured advice)
5. SOFT_TASTE_PREFERENCE (Advisory taste rules and preferences)

Guarantees:
- Hard vs Soft conflict distinction.
- Conflicting directives are never ignored or silently discarded.
- Equal-priority unresolvable hard conflicts result in FAILED_UNRESOLVED_CONFLICT status.
- Zero runtime authority mutation: outputs guidance, never authorizes tools or approves QC.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import JsonValue

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import AudioMode, ProvenanceType
from ai.contracts.creative.conflict import (
    ConflictPrecedenceRank,
    ConflictSeverity,
    ConflictStatus,
    CreativeConflict,
    ResolvedCreativeGuidance,
)
from ai.contracts.creative.directors import DirectorRecommendationBundle
from ai.contracts.creative.taste import TasteContext, TasteDecision

logger = logging.getLogger(__name__)


class ConflictResolver:
    """
    Detects and resolves creative tensions across Brief, Recipe, Directors, and Taste Rules.
    """

    def resolve(
        self,
        context: TasteContext,
        director_bundle: DirectorRecommendationBundle,
        taste_decisions: List[TasteDecision],
        injected_hard_conflicts: Optional[List[CreativeConflict]] = None,
    ) -> ResolvedCreativeGuidance:
        """
        Executes comprehensive conflict detection and resolution.
        Produces canonical ResolvedCreativeGuidance.
        """
        detected_conflicts: List[CreativeConflict] = []
        brief = context.brief
        audio_mode = brief.constraints.audio_mode
        recipe_id = context.recipe_id.lower()
        user_tone = (brief.interpreted_intent.tone or "").lower()
        user_style = (brief.interpreted_intent.style or "").lower()

        # ---------------------------------------------------------------------
        # 1. Detection: Hard AudioMode Violations
        # ---------------------------------------------------------------------
        if audio_mode == AudioMode.SILENT:
            # Check if any SFX direction had sound cues
            has_sfx = any(len(s.sound_cues) > 0 for s in director_bundle.sfx_directions)
            if has_sfx:
                conflict = CreativeConflict(
                    conflict_id=f"conf_{uuid.uuid4().hex[:10]}",
                    conflict_type="AUDIO_MODE_VIOLATION",
                    severity=ConflictSeverity.HARD,
                    description="Director recommended SFX cues under SILENT audio mode.",
                    conflicting_parties=["AudioMode:SILENT", "SfxDirector:sound_cues"],
                    competing_directives={
                        "system_audio_mode": "SILENT",
                        "director_sfx_count": sum(len(s.sound_cues) for s in director_bundle.sfx_directions),
                    },
                    applied_precedence=ConflictPrecedenceRank.HARD_SYSTEM_CONSTRAINT,
                    resolved_directive={"sound_cues": [], "action": "suppress_all_audio"},
                    status=ConflictStatus.RESOLVED,
                    reason_summary="AudioMode SILENT is a hard system constraint overriding creative SFX recommendations.",
                )
                detected_conflicts.append(conflict)

        elif audio_mode == AudioMode.MUSIC_ONLY:
            # Check if any narrative direction proposed spoken voiceover
            has_spoken = any(bool(n.spoken_line) for n in director_bundle.narrative_directions)
            if has_spoken:
                conflict = CreativeConflict(
                    conflict_id=f"conf_{uuid.uuid4().hex[:10]}",
                    conflict_type="AUDIO_MODE_VIOLATION",
                    severity=ConflictSeverity.HARD,
                    description="Spoken voiceover line proposed under MUSIC_ONLY audio mode.",
                    conflicting_parties=["AudioMode:MUSIC_ONLY", "NarrativeDirector:spoken_line"],
                    competing_directives={
                        "system_audio_mode": "MUSIC_ONLY",
                        "director_spoken_lines_present": True,
                    },
                    applied_precedence=ConflictPrecedenceRank.HARD_SYSTEM_CONSTRAINT,
                    resolved_directive={"spoken_lines": None, "action": "visual_progression_only"},
                    status=ConflictStatus.RESOLVED,
                    reason_summary="AudioMode MUSIC_ONLY is a hard system constraint strictly forbidding voiceover delivery.",
                )
                detected_conflicts.append(conflict)

        # ---------------------------------------------------------------------
        # 2. Detection: User Intent vs Recipe Energy (e.g. User CALM vs Recipe FAST)
        # ---------------------------------------------------------------------
        is_user_calm = any(w in f"{user_tone} {user_style}" for w in ["calm", "premium", "luxury", "slow", "deliberate"])
        is_recipe_fast = any(w in recipe_id for w in ["sprint", "fast", "montage", "energetic", "dynamic"])

        if is_user_calm and is_recipe_fast:
            conflict = CreativeConflict(
                conflict_id=f"conf_{uuid.uuid4().hex[:10]}",
                conflict_type="STYLE_TENSION",
                severity=ConflictSeverity.CREATIVE_TENSION,
                description=f"User explicitly requested calm/premium pacing ({user_tone}), but selected recipe '{context.recipe_id}' defaults to high-energy sprinting.",
                conflicting_parties=[f"User:{user_tone}", f"Recipe:{context.recipe_id}"],
                competing_directives={
                    "user_preference": user_tone,
                    "recipe_default_pace": "FAST_ENERGETIC",
                },
                applied_precedence=ConflictPrecedenceRank.USER_EXPLICIT_REQUIREMENT,
                resolved_directive={
                    "adopted_motion_personality": "Cinematic",
                    "pacing": "controlled_with_breathing_space",
                    "action": "prioritize_user_calm_over_recipe_fast",
                },
                status=ConflictStatus.RESOLVED,
                reason_summary="User explicit creative requirement takes precedence over recipe default pacing.",
            )
            detected_conflicts.append(conflict)

        # ---------------------------------------------------------------------
        # 3. Detection: MotionDirector vs Recipe Cuts (e.g. CALM vs AGGRESSIVE_FAST)
        # ---------------------------------------------------------------------
        calm_motion_dirs = [m for m in director_bundle.motion_directions if m.motion_energy == "calm"]
        if calm_motion_dirs and "sprint" in recipe_id:
            conflict = CreativeConflict(
                conflict_id=f"conf_{uuid.uuid4().hex[:10]}",
                conflict_type="MOTION_ENERGY_CONFLICT",
                severity=ConflictSeverity.CREATIVE_TENSION,
                description="MotionDirector recommended CALM energy while recipe is high-velocity sprint.",
                conflicting_parties=["MotionDirector:calm", f"Recipe:{context.recipe_id}"],
                competing_directives={
                    "motion_energy": "calm",
                    "recipe_energy": "AGGRESSIVE_FAST",
                },
                applied_precedence=ConflictPrecedenceRank.RECIPE_CONSTRAINT,
                resolved_directive={
                    "motion_energy": "controlled_dynamic",
                    "action": "harmonize_calm_motion_with_snappy_sprint_transitions",
                },
                status=ConflictStatus.RESOLVED,
                reason_summary="Recipe sprint structure requires minimum dynamic velocity; harmonized with controlled smooth easing.",
            )
            detected_conflicts.append(conflict)

        # ---------------------------------------------------------------------
        # 4. Injected / Additional Hard Conflicts
        # ---------------------------------------------------------------------
        if injected_hard_conflicts:
            detected_conflicts.extend(injected_hard_conflicts)

        # Check for unresolved conflicts
        unresolved = [c for c in detected_conflicts if c.status == ConflictStatus.UNRESOLVED]
        overall_status = "FAILED_UNRESOLVED_CONFLICT" if unresolved else "SUCCESS"

        now = datetime.now(timezone.utc)
        provenance = ProvenanceRecord(
            source="ai.conflict.resolver.ConflictResolver",
            model_id="conflict_resolver_v1",
            provider_id="internal",
            timestamp=now,
            latency_ms=5,
        )

        return ResolvedCreativeGuidance(
            guidance_id=f"guid_{uuid.uuid4().hex[:12]}",
            brief_id=brief.brief_id,
            recipe_id=context.recipe_id,
            narrative_plan=context.narrative_plan,
            taste_decisions=taste_decisions,
            narrative_directions=director_bundle.narrative_directions,
            motion_directions=director_bundle.motion_directions,
            emotion_directions=director_bundle.emotion_directions,
            sfx_directions=director_bundle.sfx_directions,
            detected_conflicts=detected_conflicts,
            unresolved_conflicts=unresolved,
            status=overall_status,
            provenance=provenance,
            created_at=now,
        )
