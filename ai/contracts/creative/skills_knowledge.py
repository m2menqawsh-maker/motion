"""
ai/contracts/creative/skills_knowledge.py
=========================================
Canonical contracts for SkillDefinition and KnowledgeDescriptor.

Authority: S28 Creative Intelligence Platform (DEC-S28.01)
Guarantees:
- Skill = How the system handles a task type (Skill ≠ Permission, Skill ≠ Tool).
- Knowledge = Information and experience relied upon (Knowledge ≠ Runtime Authority).
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import Field, JsonValue, model_validator

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.common import CapabilityType
from ai.contracts.creative.brief import AudioMode


class KnowledgeStatus(str, Enum):
    """Lifecycle and eligibility status for Knowledge documents."""
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    DRAFT = "DRAFT"


class KnowledgeCategory(str, Enum):
    """Canonical categories for platform knowledge artifacts."""
    PLAYBOOK = "PLAYBOOK"
    SOP = "SOP"
    ENGINEERING_GUIDE = "ENGINEERING_GUIDE"
    TASTE_REFERENCE = "TASTE_REFERENCE"


class SkillStatus(str, Enum):
    """Operational status for skills."""
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    DISABLED = "DISABLED"
    DRAFT = "DRAFT"


class RetrievalMode(str, Enum):
    """Channel mode for knowledge retrieval operations."""
    HYBRID = "HYBRID"
    LEXICAL_ONLY = "LEXICAL_ONLY"
    SEMANTIC_ONLY = "SEMANTIC_ONLY"
    DEGRADED_LEXICAL = "DEGRADED_LEXICAL"


class SkillDefinition(AIContractModel):
    """
    Formal definition of an operational Skill: encapsulates how the system
    handles a specific task type and what capability primitives it orchestrates.
    """
    skill_id: str = Field(description="Unique skill identifier (e.g., 'skill_motion_typography')")
    name: str = Field(description="Human-readable skill name")
    description: str = Field(description="Detailed description of the task handling logic")
    task_type: str = Field(default="", description="Task category handled (e.g., 'motion_typography', 'avatar_explainer')")
    version: str = Field(default="1.0.0", description="Semver version of the skill definition")
    status: strict_enum(SkillStatus) = Field(
        default=SkillStatus.ACTIVE,
        description="Lifecycle and routing status of this skill"
    )
    trigger_conditions: List[str] = Field(
        default_factory=list,
        description="Intent phrases, keywords, or condition markers that trigger this skill"
    )
    required_context: List[str] = Field(
        default_factory=list,
        description="Context variables or parameters required to execute this skill"
    )
    required_capabilities: List[strict_enum(CapabilityType)] = Field(
        default_factory=list,
        description="Provider-neutral capabilities orchestrated by this skill"
    )
    allowed_tools: List[str] = Field(
        default_factory=list,
        description="Discrete domain tools this skill may request (subject to ToolAuthorizationPolicy)"
    )
    required_knowledge: List[str] = Field(
        default_factory=list,
        description="Knowledge document IDs required by this skill"
    )
    input_contract: Optional[str] = Field(
        default=None,
        description="Schema or specification name for input payload"
    )
    output_contract: Optional[str] = Field(
        default=None,
        description="Schema or specification name for output payload"
    )
    applicable_recipe_ids: List[str] = Field(
        default_factory=list,
        description="List of recipe IDs compatible with this skill"
    )
    metadata: Dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional structured operational parameters"
    )

    @model_validator(mode="before")
    @classmethod
    def _remap_purpose(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "purpose" in data and "description" not in data:
                data["description"] = data.pop("purpose")
        return data

    @property
    def purpose(self) -> str:
        return self.description


class KnowledgeDescriptor(AIContractModel):
    """
    Catalog descriptor for reference knowledge: documents, playbooks, guidelines,
    and heuristics used for creative reasoning without conveying runtime authority.
    """
    knowledge_id: str = Field(description="Unique knowledge item identifier")
    category: str = Field(description="Category (e.g., 'PLAYBOOK', 'SOP', 'ENGINEERING_GUIDE', 'TASTE_REFERENCE')")
    title: str = Field(description="Title of the knowledge document")
    source_uri: str = Field(description="Relative path or URI to the source artifact (e.g., 'references/...')")
    content_hash: str = Field(description="Cryptographic digest (SHA-256) of document content")
    version: str = Field(default="1.0.0", description="Semver version of the knowledge artifact")
    status: strict_enum(KnowledgeStatus) = Field(
        default=KnowledgeStatus.ACTIVE,
        description="Lifecycle and retrieval eligibility status"
    )
    tags: List[str] = Field(default_factory=list, description="Descriptive classification tags")
    video_types: List[str] = Field(
        default_factory=list,
        description="Applicable video types (e.g., 'explainer', 'montage', 'demo')"
    )
    platforms: List[str] = Field(
        default_factory=list,
        description="Target distribution platforms (e.g., 'youtube', 'tiktok', 'instagram')"
    )
    audio_modes: List[strict_enum(AudioMode)] = Field(
        default_factory=list,
        description="Compatible audio presentation modes"
    )
    language: str = Field(
        default="any",
        description="Language code for the knowledge artifact (e.g., 'ar', 'en', 'any')"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of knowledge or asset IDs this document depends upon"
    )
    authority_level: int = Field(default=5, ge=1, le=5, description="Hierarchy level (Level 5 = Reference, non-runtime)")
    summary: Optional[str] = Field(default=None, description="Concise synopsis of the knowledge content")

    @model_validator(mode="before")
    @classmethod
    def _remap_source_and_hash(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "source_path" in data and "source_uri" not in data:
                data["source_uri"] = data.pop("source_path")
            if "source_hash" in data and "content_hash" not in data:
                data["content_hash"] = data.pop("source_hash")
        return data

    @property
    def source_path(self) -> str:
        return self.source_uri

    @property
    def source_hash(self) -> str:
        return self.content_hash
