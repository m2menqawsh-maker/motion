"""
ai/contracts/creative/taste.py
==============================
Canonical contracts for TasteRule and TasteDecision.

Authority: S28 Creative Intelligence Platform (DEC-S28.01)
Guarantees:
- Taste Rule = Creative principle or rule influencing creative decisions (Taste ≠ QC).
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
- Immutability: models are frozen value objects.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.creative.brief import CreativeBrief
from ai.contracts.creative.feedback import UserStyleProfile
from ai.contracts.creative.narrative import NarrativePlan


class TasteRuleSeverity(str, Enum):
    """Enforcement severity of a taste rule (supports MUST/SHOULD/PREFER/AVOID and legacy aliases)."""
    MUST = "MUST"
    SHOULD = "SHOULD"
    PREFER = "PREFER"
    AVOID = "AVOID"
    # Backward compatibility aliases
    MANDATORY_CREATIVE = "MANDATORY_CREATIVE"
    PREFERRED = "PREFERRED"
    ADVISORY = "ADVISORY"


class TasteRule(AIContractModel):
    """
    Formal representation of a creative taste principle guiding aesthetic choices
    (e.g., spring physics, visual hierarchy, beat density, gestural sync).
    """
    rule_id: str = Field(description="Unique rule identifier (e.g., 'taste_beat_density_v2')")
    category: str = Field(description="Rule category (e.g., 'motion_personality', 'beat_density', 'gestural_sync')")
    name: str = Field(description="Human-readable rule name")
    description: str = Field(description="Technical and aesthetic explanation of the rule")
    rationale: str = Field(description="Creative justification derived from film/motion craft")
    citation_source: str = Field(description="Source citation path (e.g., 'references/4_taste_engine/user-signature-style.md#L10')")
    severity: strict_enum(TasteRuleSeverity) = Field(default=TasteRuleSeverity.PREFERRED, description="Enforcement severity")
    parameters: Dict[str, JsonValue] = Field(default_factory=dict, description="Concrete numerical or categorical parameters")
    version: str = Field(default="1.0.0", description="Semver version of this taste rule")
    applies_when: Dict[str, JsonValue] = Field(default_factory=dict, description="Structured criteria/predicates determining when rule applies")
    recommendation: str = Field(default="", description="Structured creative recommendation or instruction")
    priority: int = Field(default=50, ge=1, le=100, description="Evaluation priority rank (1-100, higher evaluated first)")
    exceptions: List[str] = Field(default_factory=list, description="Explicit conditions or contexts where rule is bypassed")
    source_knowledge_ids: List[str] = Field(default_factory=list, description="IDs of supporting knowledge documents establishing provenance")


class TasteDecision(AIContractModel):
    """
    Documented application of a specific TasteRule to a scene or shot element.
    Provides verifiable proof of compliance with the creative style system.
    """
    decision_id: str = Field(description="Unique identifier for this decision instance")
    rule_id: str = Field(description="ID of the governing TasteRule applied")
    context_ref: str = Field(description="Reference to the target scene or shot (e.g., 'scene_001_shot_002')")
    applied_value: str = Field(description="The concrete setting or parameter applied (e.g., 'cubic-bezier(0.4,0,0.2,1), 400ms')")
    reasoning: str = Field(description="Explanation of why this value was chosen for this context")
    citation: str = Field(description="Verbatim citation from the taste documentation proving alignment")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score [0.0 - 1.0]")
    rule_ids: List[str] = Field(default_factory=list, description="IDs of all rules influencing this decision")
    evidence: List[str] = Field(default_factory=list, description="Verifiable context citations or trigger evidence")
    reason_summary: str = Field(default="", description="Concise auditable rationale summary without hidden CoT")


class TasteContext(AIContractModel):
    """
    Contextual snapshot provided to TasteEngine and Creative Directors.
    """
    brief: CreativeBrief = Field(description="The underlying CreativeBrief")
    narrative_plan: NarrativePlan = Field(description="The planned narrative arc")
    recipe_id: str = Field(description="ID of the selected recipe")
    recipe_name: str = Field(default="", description="Name of the selected recipe")
    media_intelligence: Dict[str, JsonValue] = Field(default_factory=dict, description="Media intelligence signals")
    available_assets: List[str] = Field(default_factory=list, description="Asset URIs or identifiers available")
    user_style_profile: Optional[UserStyleProfile] = Field(default=None, description="Optional persistent user style profile")
    active_knowledge_ids: List[str] = Field(default_factory=list, description="IDs of relevant active knowledge descriptors")
    active_skill_ids: List[str] = Field(default_factory=list, description="IDs of relevant active skills")
