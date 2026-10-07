"""
ai/skills/loader.py
===================
Skill loading, schema validation, and catalog initialization (S28-02).

Guarantees:
- Skill = How the system handles a task type (Skill ≠ Permission, Skill ≠ Tool).
- Strict validation against SkillDefinition: invalid skills are STRICTLY REJECTED.
- Rejection of unknown capabilities, invalid schemas, or malformed definitions.
- Loading from markdown files with YAML frontmatter (.agents/skills/).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml
from pydantic import ValidationError

from ai.contracts.common import CapabilityType
from ai.contracts.creative.skills_knowledge import SkillDefinition, SkillStatus
from ai.skills.registry import SkillRegistry


class SkillLoaderError(Exception):
    """Base exception for Skill Loader errors."""
    pass


class SkillValidationError(SkillLoaderError):
    """Raised when a skill definition fails Pydantic validation."""
    pass


class SkillSourceNotFoundError(SkillLoaderError):
    """Raised when a skill source file is missing."""
    pass


class SkillLoader:
    """
    Loads, parses, and validates SkillDefinitions from disk or structured representations.
    """

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = workspace_root or Path.cwd()

    def validate_skill(self, raw_data: Dict[str, Any]) -> SkillDefinition:
        """
        Validates raw dictionary data against the canonical SkillDefinition schema.
        Raises SkillValidationError if invalid (extra fields, bad types, missing required fields).
        """
        try:
            return SkillDefinition.model_validate(raw_data)
        except ValidationError as exc:
            raise SkillValidationError(
                f"Skill definition validation failed for id '{raw_data.get('skill_id', 'unknown')}': {exc}"
            ) from exc

    def load_from_markdown(self, markdown_path: Path | str, skill_id_override: Optional[str] = None) -> SkillDefinition:
        """
        Parses a SKILL.md file containing YAML frontmatter and markdown sections.
        """
        path = Path(markdown_path)
        if not path.is_absolute():
            path = (self.workspace_root / path).resolve()

        if not path.exists() or not path.is_file():
            raise SkillSourceNotFoundError(f"Skill file not found at: {path}")

        content = path.read_text(encoding="utf-8")

        # Parse YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            raise SkillValidationError(f"Missing YAML frontmatter in skill file: {path}")

        fm_text = frontmatter_match.group(1)
        body_text = frontmatter_match.group(2).strip()

        try:
            fm_data = yaml.safe_load(fm_text) or {}
        except Exception as exc:
            raise SkillValidationError(f"Failed to parse YAML frontmatter in {path}: {exc}") from exc

        name = fm_data.get("name", path.parent.name)
        skill_id = skill_id_override or f"skill_{name.replace('-', '_')}"
        description = fm_data.get("description", "")
        if not description:
            # Extract first paragraph from body
            paragraphs = [p.strip() for p in body_text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
            description = paragraphs[0] if paragraphs else f"Operational skill for {name}"

        raw_dict = {
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "task_type": fm_data.get("task_type", name),
            "version": fm_data.get("version", "1.0.0"),
            "status": fm_data.get("status", "ACTIVE"),
            "trigger_conditions": fm_data.get("trigger_conditions", [name.replace("-", " ")]),
            "required_context": fm_data.get("required_context", []),
            "required_capabilities": fm_data.get("required_capabilities", []),
            "allowed_tools": fm_data.get("allowed_tools", []),
            "required_knowledge": fm_data.get("required_knowledge", []),
            "applicable_recipe_ids": fm_data.get("applicable_recipe_ids", []),
            "metadata": fm_data.get("metadata", {}),
        }

        return self.validate_skill(raw_dict)

    @classmethod
    def get_canonical_skills(cls) -> List[SkillDefinition]:
        """
        Returns the authoritative initial list of SkillDefinitions for the platform.
        """
        return [
            SkillDefinition(
                skill_id="skill_motion_typography",
                name="Motion Typography Skill",
                description="Orchestrates kinetic typography, word-level audio synchronization, and emphasis gestures.",
                task_type="motion_typography",
                version="1.0.0",
                status=SkillStatus.ACTIVE,
                trigger_conditions=[
                    "kinetic typography",
                    "motion titles",
                    "captions",
                    "word sync",
                    "text animation",
                    "kinetic text",
                ],
                required_context=["script_text"],
                required_capabilities=[CapabilityType.TEXT_TO_SPEECH, CapabilityType.SPEECH_ALIGNMENT],
                allowed_tools=["patch_blueprint"],
                required_knowledge=["know_taste_motion_personality"],
                applicable_recipe_ids=["dynamic-montage-ad", "living-canvas-explainer"],
                metadata={"default_font": "Inter", "max_wps": 3.2},
            ),
            SkillDefinition(
                skill_id="skill_spoken_vo_humanizer",
                name="Spoken VO Humanizer Skill",
                description="Translates written copy into conversational spoken scripts eliminating robotic cadence.",
                task_type="voiceover_humanization",
                version="1.0.0",
                status=SkillStatus.ACTIVE,
                trigger_conditions=[
                    "spoken voiceover",
                    "natural speech",
                    "humanize script",
                    "conversational narration",
                    "vo cadence",
                    "voiceover",
                ],
                required_context=["script_draft"],
                required_capabilities=[CapabilityType.TEXT_TO_SPEECH],
                allowed_tools=[],
                required_knowledge=["know_sop_spoken_vo", "know_playbook_video_copy"],
                applicable_recipe_ids=["avatar-explainer", "living-canvas-explainer", "review-conquest-compilation"],
                metadata={"target_wpm": 150},
            ),
            SkillDefinition(
                skill_id="skill_avatar_explainer",
                name="Avatar Explainer Skill",
                description="Coordinates AI avatar video synthesis, lip synchronization, green-screen extraction, and framing.",
                task_type="avatar_explainer",
                version="1.0.0",
                status=SkillStatus.ACTIVE,
                trigger_conditions=[
                    "avatar",
                    "talking head",
                    "presenter",
                    "avatar explainer",
                    "spokesperson",
                ],
                required_context=["avatar_id", "speech_audio_asset_id"],
                required_capabilities=[
                    CapabilityType.VIDEO_GENERATION,
                    CapabilityType.LIP_SYNC,
                    CapabilityType.BACKGROUND_REMOVAL,
                ],
                allowed_tools=["create_project_asset", "patch_blueprint"],
                required_knowledge=["know_sop_seedance_avatar", "know_sop_spoken_vo"],
                applicable_recipe_ids=["avatar-explainer", "captioned-talking-head", "avatar-vo-broll"],
                metadata={"default_avatar": "seedance_v1"},
            ),
            SkillDefinition(
                skill_id="skill_dynamic_montage",
                name="Dynamic Montage Assembly Skill",
                description="Orchestrates high-energy video montage cuts synchronized to musical rhythm, beat drops, and SFX.",
                task_type="dynamic_montage",
                version="1.0.0",
                status=SkillStatus.ACTIVE,
                trigger_conditions=[
                    "dynamic montage",
                    "music montage",
                    "rhythmic cuts",
                    "beat sync",
                    "fast montage",
                    "music video",
                    "montage",
                ],
                required_context=["music_track_asset_id"],
                required_capabilities=[CapabilityType.BEAT_DETECTION],
                allowed_tools=["patch_blueprint"],
                required_knowledge=[
                    "know_playbook_motion_collage",
                    "know_taste_sfx_matrix",
                    "know_taste_motion_personality",
                ],
                applicable_recipe_ids=["dynamic-montage-ad"],
                metadata={"min_shot_duration_sec": 0.8, "max_shot_duration_sec": 2.5},
            ),
            SkillDefinition(
                skill_id="skill_broll_assembly",
                name="B-Roll Assembly Skill",
                description="Selects, crops, and applies camera motion (Ken Burns) and transitions to contextual B-roll clips.",
                task_type="broll_assembly",
                version="1.0.0",
                status=SkillStatus.ACTIVE,
                trigger_conditions=[
                    "broll",
                    "cutaway",
                    "visual footage",
                    "stock footage",
                    "b-roll",
                    "visual proof",
                ],
                required_context=["scene_descriptions"],
                required_capabilities=[CapabilityType.IMAGE_GENERATION, CapabilityType.VIDEO_GENERATION],
                allowed_tools=["create_project_asset", "patch_blueprint"],
                required_knowledge=["know_sop_hyperrealistic", "know_taste_disney"],
                applicable_recipe_ids=["avatar-vo-broll", "faceless-broll-ad"],
                metadata={"ken_burns_zoom_range": [1.0, 1.15]},
            ),
            SkillDefinition(
                skill_id="skill_remocn",
                name="Remocn React Component Skill",
                description="Selects verified templates from the registry and constructs React/TSX scene compositions.",
                task_type="remotion_authoring",
                version="1.0.0",
                status=SkillStatus.ACTIVE,
                trigger_conditions=[
                    "remocn",
                    "remotion",
                    "react component",
                    "tsx",
                    "custom template",
                    "declarative scene",
                ],
                required_context=["composition_plan"],
                required_capabilities=[],
                allowed_tools=["patch_blueprint"],
                required_knowledge=["know_eng_remotion", "know_taste_motion_personality"],
                applicable_recipe_ids=["living-canvas-explainer", "motion-graphics"],
                metadata={"authoring_tier": "COMPOSE"},
            ),
            SkillDefinition(
                skill_id="skill_snapcn",
                name="Snapcn Tailwind Motion UI Skill",
                description="Selects and styles Tailwind motion UI components and archetypes for product video compositions.",
                task_type="ui_component_authoring",
                version="1.0.0",
                status=SkillStatus.ACTIVE,
                trigger_conditions=[
                    "snapcn",
                    "tailwind",
                    "ui component",
                    "motion primitive",
                    "product demo",
                ],
                required_context=["composition_plan"],
                required_capabilities=[],
                allowed_tools=["patch_blueprint"],
                required_knowledge=["know_eng_remotion"],
                applicable_recipe_ids=["screencast-demo", "living-canvas-explainer"],
                metadata={"styling_framework": "tailwind"},
            ),
            SkillDefinition(
                skill_id="skill_prompt_expert",
                name="Prompt Engineering Expert Skill",
                description="Expert guidance on prompt design, custom instructions, XML structuring, and prompt optimization.",
                task_type="prompt_engineering",
                version="1.0.0",
                status=SkillStatus.ACTIVE,
                trigger_conditions=[
                    "prompt engineering",
                    "prompt optimization",
                    "custom instructions",
                    "system prompt",
                    "prompt tuning",
                ],
                required_context=[],
                required_capabilities=[],
                allowed_tools=[],
                required_knowledge=[],
                applicable_recipe_ids=[],
                metadata={"domain": "meta_prompting"},
            ),
        ]

    def load_canonical_catalog(self, registry: Optional[SkillRegistry] = None) -> List[SkillDefinition]:
        """Loads canonical skills and registers them in registry if provided."""
        skills = self.get_canonical_skills()
        if registry is not None:
            registry.register_many(skills)
        return skills
