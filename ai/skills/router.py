"""
ai/skills/router.py
===================
Dynamic Skill Router for bounded, context-aware skill selection (S28-02).

Guarantees:
- Dynamic selection: returns bounded set (typically 2-4 skills), never all skills.
- Strict two-stage evaluation:
  1. Eligibility Gate (Hard incompatibility: status, audio mode, missing capabilities).
  2. Intent & Context Ranking (Trigger matches, task_type, semantic relevance).
- Hard audio mode enforcement: in MUSIC_ONLY mode, speech and voiceover skills are strictly excluded.
- Structured decision audit trail.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple

from ai.contracts.common import CapabilityType
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import SkillDefinition, SkillStatus
from ai.knowledge.indexer import tokenize
from ai.skills.contracts import (
    SkillCandidate,
    SkillRoutingContext,
    SkillRoutingResult,
)
from ai.skills.registry import SkillRegistry


class SkillRouter:
    """
    Evaluates and dynamically routes the small set of relevant skills
    matching the creative request.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def _check_eligibility(
        self,
        skill: SkillDefinition,
        context: SkillRoutingContext,
    ) -> Tuple[bool, Optional[str]]:
        """
        Stage 1: Hard Eligibility Gate.
        Evaluates status, audio mode constraints, and platform capability availability.
        """
        # 1. Lifecycle status gate
        if skill.status != SkillStatus.ACTIVE:
            return False, f"Skill status is '{skill.status}' (only ACTIVE allowed)"

        # 2. Audio mode hard incompatibility
        if context.audio_mode == AudioMode.MUSIC_ONLY:
            # Voiceover humanizer and speech-alignment skills are strictly incompatible
            if skill.task_type == "voiceover_humanization" or skill.skill_id == "skill_spoken_vo_humanizer":
                return False, "Incompatible with MUSIC_ONLY: voiceover humanization skill"
            # If skill requires speech alignment or text-to-speech for voiceover
            if CapabilityType.SPEECH_ALIGNMENT in skill.required_capabilities:
                return False, "Incompatible with MUSIC_ONLY: requires SPEECH_ALIGNMENT"

        # 3. Available capability gate (if environment restricts capabilities)
        if context.available_capabilities:
            available_set = set(context.available_capabilities)
            for req_cap in skill.required_capabilities:
                if req_cap not in available_set:
                    return False, f"Missing required capability '{req_cap}' in environment"

        return True, None

    def _score_skill(
        self,
        skill: SkillDefinition,
        context: SkillRoutingContext,
        query_tokens: List[str],
    ) -> Tuple[float, List[str]]:
        """
        Stage 2: Intent & Context Ranking.
        Scores relevance based on triggers, task_type, name, description, and context.
        """
        score = 0.0
        reasons: List[str] = []

        query_token_set = set(query_tokens)
        intent_lower = context.intent.lower()

        GENERIC_TERMS = {
            "video", "audio", "make", "create", "generate", "clip", "clips",
            "custom", "new", "best", "expert", "pro", "high", "fast", "top", "good",
            "using", "with", "without", "from"
        }

        # 1. Exact task_type match
        if context.task_type and skill.task_type.lower() == context.task_type.lower():
            score += 15.0
            reasons.append(f"Direct task_type match '{skill.task_type}'")

        # 2. Trigger conditions match
        for trigger in skill.trigger_conditions:
            trigger_lower = trigger.lower()
            if trigger_lower in intent_lower:
                score += 10.0
                reasons.append(f"Trigger phrase match: '{trigger}'")
            else:
                # Token overlap with trigger (excluding ubiquitous terms)
                trig_tokens = set(tokenize(trigger_lower)) - GENERIC_TERMS
                overlap = trig_tokens.intersection(query_token_set - GENERIC_TERMS)
                if overlap:
                    score += len(overlap) * 3.0
                    reasons.append(f"Trigger token match: {', '.join(overlap)}")

        # 3. Description & Name token matches (excluding ubiquitous terms)
        skill_text_tokens = set(tokenize(f"{skill.name} {skill.description}".lower())) - GENERIC_TERMS
        desc_overlap = skill_text_tokens.intersection(query_token_set - GENERIC_TERMS)
        if desc_overlap:
            score += len(desc_overlap) * 1.5
            reasons.append(f"Description matches ({len(desc_overlap)} terms)")

        # 4. Contextual audio mode preference boost
        if context.audio_mode == AudioMode.MUSIC_ONLY and "dynamic_montage" in skill.task_type:
            score += 5.0
            reasons.append("Boosted for MUSIC_ONLY audio montage context")
        elif context.audio_mode in (AudioMode.VO_ONLY, AudioMode.VO_MUSIC) and "voiceover" in skill.task_type:
            score += 4.0
            reasons.append("Boosted for Voiceover audio context")

        # 5. Video type alignment & suppression
        if context.video_type:
            vt = context.video_type.lower()
            if vt in skill.description.lower() or vt in skill.task_type.lower():
                score += 3.0
                reasons.append(f"Video type '{context.video_type}' aligned")
            # If context is explicitly explainer, dynamic montage is not suitable
            elif vt == "explainer" and skill.skill_id == "skill_dynamic_montage":
                score -= 10.0
            # If context is explicitly montage, explainer-only skills are penalized
            elif vt == "montage" and skill.skill_id in ("skill_avatar_explainer", "skill_spoken_vo_humanizer"):
                score -= 10.0

        return max(0.0, score), reasons

    def route_skills(self, context: SkillRoutingContext) -> SkillRoutingResult:
        """
        Dynamically evaluates all registered skills and selects the bounded relevant set.
        """
        all_skills = self.registry.list_all()
        query_tokens = tokenize(context.intent)

        candidate_evaluations: List[SkillCandidate] = []
        excluded_skills: Dict[str, str] = {}
        eligible_candidates: List[Tuple[float, SkillDefinition, List[str]]] = []

        MIN_RELEVANCE_THRESHOLD = 4.0

        for skill in all_skills:
            is_eligible, ineligibility_reason = self._check_eligibility(skill, context)

            if not is_eligible:
                excluded_skills[skill.skill_id] = ineligibility_reason or "INELIGIBLE"
                candidate_evaluations.append(
                    SkillCandidate(
                        skill=skill,
                        is_eligible=False,
                        ineligibility_reason=ineligibility_reason,
                        score=0.0,
                        match_reasons=[],
                    )
                )
                continue

            score, reasons = self._score_skill(skill, context, query_tokens)
            candidate_evaluations.append(
                SkillCandidate(
                    skill=skill,
                    is_eligible=True,
                    score=score,
                    match_reasons=reasons,
                )
            )

            # Consider eligible candidate only if score meets relevance threshold or explicit task_type
            is_explicit_task = context.task_type and context.task_type.lower() == skill.task_type.lower()
            if score >= MIN_RELEVANCE_THRESHOLD or is_explicit_task:
                eligible_candidates.append((score, skill, reasons))

        # Sort eligible candidates by score descending
        eligible_candidates.sort(key=lambda x: (x[0], x[1].skill_id), reverse=True)

        # Context Bounding: select top max_skills (default 2-4)
        selected_skills = [item[1] for item in eligible_candidates[: context.max_skills]]

        return SkillRoutingResult(
            context=context,
            selected_skills=selected_skills,
            candidate_evaluations=candidate_evaluations,
            excluded_skills=excluded_skills,
            audit_trail={
                "total_registered_skills": len(all_skills),
                "eligible_count": len(eligible_candidates),
                "selected_count": len(selected_skills),
                "excluded_count": len(excluded_skills),
            },
        )
