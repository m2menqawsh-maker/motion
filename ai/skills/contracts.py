"""
ai/skills/contracts.py
======================
Runtime types, routing context, and evaluation results for the Skills Platform (S28-02).

Guarantees:
- Skill = How the system handles a task type (Skill ≠ Permission, Skill ≠ Tool).
- Strict separation between eligible skills and ranked skills.
- Tool needs declared by skills are subject to ToolAuthorizationPolicy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import Field, JsonValue, model_validator

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.common import CapabilityType
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import SkillDefinition, SkillStatus
from ai.knowledge.contracts import KnowledgeChunk, RetrievedChunk


class SkillRoutingContext(AIContractModel):
    """
    Context for dynamic skill selection based on creative request, intent, and platform constraints.
    """
    intent: str = Field(description="Creative request intent, user prompt, or task specification")
    task_type: Optional[str] = Field(default=None, description="Optional explicit task category (e.g., 'motion_typography')")
    audio_mode: Optional[strict_enum(AudioMode)] = Field(default=None, description="Audio presentation mode (e.g. MUSIC_ONLY)")
    video_type: Optional[str] = Field(default=None, description="Target video type (e.g., 'montage', 'explainer')")
    platform: Optional[str] = Field(default=None, description="Target delivery platform (e.g., 'tiktok', 'youtube')")
    available_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Capabilities available in current environment (if restricted)"
    )
    user_context: Dict[str, JsonValue] = Field(default_factory=dict, description="Additional context parameters")
    max_skills: int = Field(default=4, ge=1, le=10, description="Maximum number of skills to route (default 2-4)")


class SkillCandidate(AIContractModel):
    """Evaluation of an individual skill during routing."""
    skill: SkillDefinition = Field(description="The evaluated skill definition")
    is_eligible: bool = Field(description="Whether the skill passed hard compatibility constraints")
    ineligibility_reason: Optional[str] = Field(default=None, description="Reason if marked ineligible")
    score: float = Field(default=0.0, ge=0.0, description="Relevance score if eligible")
    match_reasons: List[str] = Field(default_factory=list, description="Explanations for selection or scoring")


class SkillRoutingResult(AIContractModel):
    """The bounded result of a skill routing operation."""
    context: SkillRoutingContext = Field(description="The routing context that initiated selection")
    selected_skills: List[SkillDefinition] = Field(default_factory=list, description="Selected bounded skills (typically 2-4)")
    candidate_evaluations: List[SkillCandidate] = Field(default_factory=list, description="All evaluated candidates")
    excluded_skills: Dict[str, str] = Field(default_factory=dict, description="Map of skill_id -> exclusion reason")
    audit_trail: Dict[str, JsonValue] = Field(default_factory=dict, description="Observability trail")


class SkillContext(AIContractModel):
    """
    Prepared execution context for an active skill.
    Contains verified knowledge retrieved via KnowledgeRouter and declared capabilities.
    """
    skill: SkillDefinition = Field(description="The authoritative SkillDefinition")
    creative_context: Dict[str, JsonValue] = Field(default_factory=dict, description="Validated operational context")
    retrieved_knowledge: List[RetrievedChunk] = Field(
        default_factory=list,
        description="Knowledge chunks resolved via KnowledgeRouter for this skill"
    )
    declared_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Capabilities required by this skill"
    )
    declared_tools: List[str] = Field(
        default_factory=list,
        description="Discrete tools declared by this skill (subject to ToolAuthorizationPolicy)"
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_chunks(cls, data: Any) -> Any:
        if isinstance(data, dict) and "retrieved_knowledge" in data:
            coerced = []
            for item in data["retrieved_knowledge"]:
                if isinstance(item, KnowledgeChunk):
                    coerced.append(RetrievedChunk(chunk=item, score=1.0))
                else:
                    coerced.append(item)
            data["retrieved_knowledge"] = coerced
        return data
