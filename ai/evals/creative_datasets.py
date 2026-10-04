"""
ai/evals/creative_datasets.py
=============================
Authoritative evaluation datasets and test corpus for Knowledge Retrieval & Skill Routing (S28-02).

Invariants:
- Ground truth is strictly segregated from model generation.
- Evaluation cases cover positive, negative, boundary, and ambiguous scenarios.
- Cases define expected documents/skills and strictly forbidden documents/skills.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import Field

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.common import CapabilityType
from ai.contracts.creative.brief import AudioMode


class KnowledgeEvalCase(AIContractModel):
    """Specification of an individual Knowledge Retrieval evaluation scenario."""
    case_id: str = Field(description="Unique identifier for the evaluation case")
    description: str = Field(description="Purpose of the test case")
    query: str = Field(description="Search text or creative user request")
    video_type: Optional[str] = Field(default=None)
    platform: Optional[str] = Field(default=None)
    audio_mode: Optional[strict_enum(AudioMode)] = Field(default=None)
    language: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = Field(default=None)
    version: Optional[str] = Field(default=None)
    expected_documents: List[str] = Field(
        default_factory=list,
        description="List of knowledge document IDs that SHOULD be present in results"
    )
    forbidden_documents: List[str] = Field(
        default_factory=list,
        description="List of knowledge document IDs that MUST NOT appear in results"
    )


class SkillRoutingEvalCase(AIContractModel):
    """Specification of an individual Skill Routing evaluation scenario."""
    case_id: str = Field(description="Unique identifier for the evaluation case")
    description: str = Field(description="Purpose of the test case")
    intent: str = Field(description="Creative request intent or prompt")
    audio_mode: Optional[strict_enum(AudioMode)] = Field(default=None)
    video_type: Optional[str] = Field(default=None)
    task_type: Optional[str] = Field(default=None)
    platform: Optional[str] = Field(default=None)
    available_capabilities: List[strict_enum(CapabilityType)] = Field(default_factory=list)
    max_skills: int = Field(default=4)
    expected_skills: List[str] = Field(
        default_factory=list,
        description="List of skill IDs that SHOULD be activated"
    )
    forbidden_skills: List[str] = Field(
        default_factory=list,
        description="List of skill IDs that MUST NOT be activated"
    )


def get_knowledge_retrieval_dataset() -> List[KnowledgeEvalCase]:
    """Returns the comprehensive benchmark evaluation dataset for Knowledge Retrieval."""
    return [
        KnowledgeEvalCase(
            case_id="k_case_01_music_only_montage",
            description="Music-only montage must retrieve motion/collage playbooks and strictly exclude voiceover SOPs",
            query="High energy dynamic video montage with rhythmic cuts and audio beat drops",
            video_type="montage",
            audio_mode=AudioMode.MUSIC_ONLY,
            expected_documents=["know_taste_motion_personality", "know_playbook_motion_collage"],
            forbidden_documents=["know_sop_spoken_vo", "know_playbook_video_copy", "know_sop_seedance_avatar"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_02_spoken_voiceover_humanizer",
            description="Voiceover script query must retrieve spoken VO humanizer and copywriting pacing rules",
            query="How to write conversational natural voiceover script pacing without robotic AI cadence",
            video_type="explainer",
            audio_mode=AudioMode.VO_ONLY,
            expected_documents=["know_sop_spoken_vo", "know_playbook_video_copy"],
            forbidden_documents=["know_playbook_ffmpeg"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_03_living_canvas_explainer",
            description="Living canvas explainer query retrieves continuous living canvas playbook",
            query="Create a continuous seamless living canvas explainer video for SaaS with camera motion",
            video_type="explainer",
            audio_mode=AudioMode.VO_MUSIC,
            expected_documents=["know_playbook_living_canvas"],
            forbidden_documents=["know_playbook_ffmpeg"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_04_remotion_spring_physics",
            description="Engineering Remotion query retrieves Remotion guide and Disney animation principles",
            query="Remotion declarative animation spring physics Disney principles interpolate math",
            expected_documents=["know_eng_remotion", "know_taste_disney"],
            forbidden_documents=["know_sop_spoken_vo"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_05_article_sprint_reels",
            description="Fast short-form article reel query retrieves hook sprint playbook",
            query="30-second fast-paced article sprint reels with high velocity hooks",
            video_type="sprint",
            platform="tiktok",
            expected_documents=["know_playbook_hook_sprint"],
            forbidden_documents=["know_playbook_tabletop"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_06_hyperrealistic_image_prompts",
            description="Image prompting query retrieves hyperrealistic image and lighting SOP",
            query="Photorealistic lighting optical lens choices and hyperrealistic image prompts",
            tags=["image", "prompting"],
            expected_documents=["know_sop_hyperrealistic"],
            forbidden_documents=["know_playbook_ffmpeg", "know_sop_spoken_vo"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_07_tabletop_layered_explainer",
            description="Tabletop concept query retrieves tabletop explainer playbook",
            query="Tiered concept layered tabletop explainer with top down camera layout",
            video_type="explainer",
            expected_documents=["know_playbook_tabletop"],
            forbidden_documents=["know_playbook_hook_sprint"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_08_competitor_review_conquest",
            description="Competitor review query retrieves review conquest playbook",
            query="Competitor review conquest video compilation highlighting product differentiation and social proof",
            video_type="review",
            expected_documents=["know_playbook_review"],
            forbidden_documents=["know_playbook_ffmpeg"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_09_ffmpeg_transcoding_recipes",
            description="FFmpeg audio/video CLI query retrieves FFmpeg recipes playbook",
            query="FFmpeg CLI commands for all-intra ProRes transcoding and audio normalization",
            category="PLAYBOOK",
            expected_documents=["know_playbook_ffmpeg"],
            forbidden_documents=["know_sop_spoken_vo", "know_taste_disney"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_10_sfx_binding_matrix",
            description="Sound design and audio ducking query retrieves SFX binding matrix",
            query="Sound design audio ducking gesture binding matrix for whooshes and pop sound effects",
            audio_mode=AudioMode.VO_MUSIC,
            expected_documents=["know_taste_sfx_matrix"],
            forbidden_documents=["know_playbook_ffmpeg"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_11_semantic_paraphrase_dialogue",
            description="Semantic paraphrase query (dialogue delivery natural rhythm and pause dynamics) retrieves spoken VO humanizer",
            query="dialogue delivery natural rhythm and pause dynamics without robotic monotonic cadence",
            video_type="explainer",
            audio_mode=AudioMode.VO_ONLY,
            expected_documents=["know_sop_spoken_vo"],
            forbidden_documents=["know_playbook_ffmpeg"],
        ),
        KnowledgeEvalCase(
            case_id="k_case_12_lexical_false_friend_ducking",
            description="False-friend query: heavy voiceover speech wording but semantic intent is audio volume ducking",
            query="audio volume ducking and sound design attenuation under spoken voiceover",
            audio_mode=AudioMode.VO_MUSIC,
            expected_documents=["know_taste_sfx_matrix", "know_sop_sound_design"],
            forbidden_documents=["know_taste_disney", "know_playbook_tabletop"],
        ),
    ]


def get_skill_routing_dataset() -> List[SkillRoutingEvalCase]:
    """Returns the comprehensive benchmark evaluation dataset for Skill Routing."""
    return [
        SkillRoutingEvalCase(
            case_id="s_case_01_music_only_montage",
            description="Music-only montage activates dynamic montage and strictly forbids spoken VO skills",
            intent="Assemble a dynamic fast-paced music montage ad with rhythmic cuts to background music",
            audio_mode=AudioMode.MUSIC_ONLY,
            video_type="montage",
            expected_skills=["skill_dynamic_montage"],
            forbidden_skills=["skill_spoken_vo_humanizer", "skill_prompt_expert"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_02_spoken_vo_script",
            description="Voiceover humanization intent activates spoken VO humanizer skill",
            intent="Humanize written copy into natural conversational spoken voiceover narration",
            audio_mode=AudioMode.VO_ONLY,
            expected_skills=["skill_spoken_vo_humanizer"],
            forbidden_skills=["skill_dynamic_montage"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_03_avatar_explainer",
            description="Avatar video intent activates avatar explainer skill",
            intent="Generate talking head avatar video with green screen removal and lip sync",
            video_type="explainer",
            expected_skills=["skill_avatar_explainer"],
            forbidden_skills=["skill_dynamic_montage"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_04_remotion_component",
            description="Remotion TSX component intent activates remocn skill",
            intent="Construct a custom declarative React component using Remotion and inspect template catalog",
            task_type="remotion_authoring",
            expected_skills=["skill_remocn"],
            forbidden_skills=["skill_prompt_expert"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_05_tailwind_motion_ui",
            description="Tailwind motion UI intent activates snapcn skill",
            intent="Build Tailwind animated motion UI component and product demo card",
            task_type="ui_component_authoring",
            expected_skills=["skill_snapcn"],
            forbidden_skills=["skill_spoken_vo_humanizer"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_06_broll_assembly",
            description="B-roll cutaways intent activates broll assembly skill",
            intent="Select and animate contextual B-roll cutaway footage with Ken Burns zoom",
            video_type="explainer",
            expected_skills=["skill_broll_assembly"],
            forbidden_skills=["skill_prompt_expert"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_07_prompt_engineering",
            description="Prompt optimization intent activates prompt expert skill",
            intent="Refine agent system instructions and optimize LLM prompt with XML tags and few-shot examples",
            task_type="prompt_engineering",
            expected_skills=["skill_prompt_expert"],
            forbidden_skills=["skill_dynamic_montage", "skill_avatar_explainer"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_08_kinetic_typography",
            description="Motion typography intent activates motion typography skill",
            intent="Add kinetic motion typography titles with word level audio sync and animated captions",
            audio_mode=AudioMode.VO_MUSIC,
            expected_skills=["skill_motion_typography"],
            forbidden_skills=["skill_dynamic_montage"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_09_music_video_no_vo",
            description="Music video beats strictly excludes avatar and spoken VO skills",
            intent="Music video with beat drops and visual collage without spoken dialogue",
            audio_mode=AudioMode.MUSIC_ONLY,
            expected_skills=["skill_dynamic_montage"],
            forbidden_skills=["skill_spoken_vo_humanizer", "skill_avatar_explainer"],
        ),
        SkillRoutingEvalCase(
            case_id="s_case_10_missing_capability_exclusion",
            description="Skill requiring unavailable capability is marked ineligible",
            intent="Generate talking head avatar video with green screen removal",
            available_capabilities=[CapabilityType.TEXT_GENERATION],  # Missing VIDEO_GENERATION, LIP_SYNC
            expected_skills=[],
            forbidden_skills=["skill_avatar_explainer"],
        ),
    ]
