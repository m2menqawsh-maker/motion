"""
ai/context/needs.py
===================
Deterministic classification of context requirements (S27.8).

Classifies what facts, memories, knowledge, and assets are strictly
required for a given request capability, intent, and project state.
Avoids dumping unneeded data into prompts.
"""

from __future__ import annotations

from typing import List
from pydantic import Field

from ai.contracts.base import AIContractModel
from ai.contracts.common import CapabilityType
from ai.contracts.memory import MemoryType
from ai.context.types import ContextRequest


class ContextNeeds(AIContractModel):
    """
    Deterministic specification of candidate data needs for an AI request.
    """
    needs_project_state: bool = Field(default=True, description="Whether canonical project lifecycle state is needed")
    needs_assets: bool = Field(default=False, description="Whether asset registry metadata is needed")
    needs_review_status: bool = Field(default=False, description="Whether human review state is needed")
    needs_decisions: bool = Field(default=False, description="Whether recorded project decisions are needed")
    needs_preferences: bool = Field(default=False, description="Whether relevant user preferences are needed")
    needs_knowledge: bool = Field(default=False, description="Whether playbooks or documentation are needed")
    needs_conversation_history: bool = Field(default=False, description="Whether recent conversation history is needed")
    needs_media_context: bool = Field(default=False, description="Whether media intelligence refs are needed")
    allowed_memory_types: List[str] = Field(default_factory=list, description="Allowed MemoryType string values")
    preference_domains: List[str] = Field(default_factory=list, description="Relevant preference domains (e.g. 'audio', 'visual')")
    knowledge_tags: List[str] = Field(default_factory=list, description="Knowledge categorization tags to search")


def classify_context_needs(request: ContextRequest) -> ContextNeeds:
    """
    Determines context needs deterministically based on capability and request attributes.
    
    Guarantees:
    - Never dumps all data into prompt.
    - Tailors memory, knowledge, and asset retrieval to the specific capability.
    """
    cap = request.capability
    has_session = bool(request.session_id)
    has_recipe = bool(request.recipe_ref)

    # 1. Speech & Audio Capabilities
    speech_audio_caps = {
        CapabilityType.SPEECH_TO_TEXT,
        CapabilityType.LANGUAGE_DETECTION,
        CapabilityType.DIARIZATION,
        CapabilityType.SPEECH_ALIGNMENT,
        CapabilityType.TEXT_TO_SPEECH,
        CapabilityType.AUDIO_DENOISE,
        CapabilityType.AUDIO_ENHANCE,
        CapabilityType.VOCAL_ISOLATION,
        CapabilityType.BEAT_DETECTION,
        CapabilityType.MUSIC_GENERATION,
        CapabilityType.VOICE_ANALYSIS,
    }
    if cap in speech_audio_caps:
        return ContextNeeds(
            needs_project_state=bool(request.project_id),
            needs_assets=True,
            needs_review_status=False,
            needs_decisions=False,
            needs_preferences=True,
            needs_knowledge=has_recipe,
            needs_conversation_history=has_session,
            needs_media_context=True,
            allowed_memory_types=[
                MemoryType.USER_PREFERENCE.value,
                MemoryType.PROJECT.value,
                MemoryType.MEDIA_INTELLIGENCE.value,
            ] + ([MemoryType.CONVERSATION.value] if has_session else []),
            preference_domains=["audio", "speech", "voice", "language", "music"],
            knowledge_tags=["audio", "speech"] + (["recipe"] if has_recipe else []),
        )

    # 2. Vision & Visual Understanding Capabilities
    vision_caps = {
        CapabilityType.VISION,
        CapabilityType.VIDEO_UNDERSTANDING,
        CapabilityType.OCR,
        CapabilityType.SHOT_DETECTION,
        CapabilityType.OBJECT_DETECTION,
        CapabilityType.PERSON_DETECTION,
        CapabilityType.SCENE_CLASSIFICATION,
        CapabilityType.CAPTIONING,
    }
    if cap in vision_caps:
        return ContextNeeds(
            needs_project_state=bool(request.project_id),
            needs_assets=True,
            needs_review_status=False,
            needs_decisions=False,
            needs_preferences=True,
            needs_knowledge=has_recipe,
            needs_conversation_history=has_session,
            needs_media_context=True,
            allowed_memory_types=[
                MemoryType.USER_PREFERENCE.value,
                MemoryType.PROJECT.value,
                MemoryType.MEDIA_INTELLIGENCE.value,
            ] + ([MemoryType.CONVERSATION.value] if has_session else []),
            preference_domains=["visual", "video", "aspect_ratio", "style"],
            knowledge_tags=["vision", "video"] + (["recipe"] if has_recipe else []),
        )

    # 3. Visual Synthesis & Manipulation
    synthesis_caps = {
        CapabilityType.IMAGE_GENERATION,
        CapabilityType.VIDEO_GENERATION,
        CapabilityType.PERSON_SEGMENTATION,
        CapabilityType.BACKGROUND_REMOVAL,
        CapabilityType.LIP_SYNC,
        CapabilityType.UPSCALE,
    }
    if cap in synthesis_caps:
        return ContextNeeds(
            needs_project_state=bool(request.project_id),
            needs_assets=True,
            needs_review_status=True,
            needs_decisions=True,
            needs_preferences=True,
            needs_knowledge=True,
            needs_conversation_history=has_session,
            needs_media_context=True,
            allowed_memory_types=[
                MemoryType.USER_PREFERENCE.value,
                MemoryType.PROJECT.value,
                MemoryType.DECISION.value,
                MemoryType.MEDIA_INTELLIGENCE.value,
            ] + ([MemoryType.CONVERSATION.value] if has_session else []),
            preference_domains=["visual", "resolution", "style", "fps", "aspect_ratio"],
            knowledge_tags=["rendering", "visual", "taste"] + (["recipe"] if has_recipe else []),
        )

    # 4. Planning & Workflow Architecture
    if cap == CapabilityType.PLANNING:
        return ContextNeeds(
            needs_project_state=bool(request.project_id),
            needs_assets=True,
            needs_review_status=True,
            needs_decisions=True,
            needs_preferences=True,
            needs_knowledge=True,
            needs_conversation_history=True,
            needs_media_context=True,
            allowed_memory_types=[
                MemoryType.PROJECT.value,
                MemoryType.DECISION.value,
                MemoryType.USER_PREFERENCE.value,
                MemoryType.CONVERSATION.value,
                MemoryType.KNOWLEDGE.value,
            ],
            preference_domains=["workflow", "style", "pacing", "format", "brand"],
            knowledge_tags=["planning", "workflow", "playbook", "taste"] + (["recipe"] if has_recipe else []),
        )

    # 5. Core Language & Reasoning (TEXT_GENERATION, REASONING, SUMMARIZATION, TRANSLATION, etc.)
    return ContextNeeds(
        needs_project_state=bool(request.project_id),
        needs_assets=False,
        needs_review_status=False,
        needs_decisions=True,
        needs_preferences=True,
        needs_knowledge=True,
        needs_conversation_history=has_session,
        needs_media_context=False,
        allowed_memory_types=[
            MemoryType.USER_PREFERENCE.value,
            MemoryType.PROJECT.value,
            MemoryType.DECISION.value,
        ] + ([MemoryType.CONVERSATION.value] if has_session else []),
        preference_domains=["tone", "language", "format", "brand"],
        knowledge_tags=["general", "guidelines"] + (["recipe"] if has_recipe else []),
    )
