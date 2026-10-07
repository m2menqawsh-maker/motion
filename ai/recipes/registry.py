"""
ai/recipes/registry.py
======================
Canonical Recipe Registry and Legacy Recipe Migration/Wrapping Engine (S28-03).

Guarantees:
- Audits and wraps all 18 legacy production recipes (recipes/*.json) into canonical, versioned RecipeDefinition models.
- Preserves all legacy recipes on disk without premature modification or deletion.
- Strict Provider Neutrality (DEC-18 / DEC-19):
  • Zero vendor SDKs or third-party cloud provider names (OpenAI, ElevenLabs, HeyGen, Fal.ai, etc.)
    are permitted within RecipeDefinition contracts.
  • Provider Neutrality Guard validates every registered recipe definition.
  • Legacy vendor bindings are audited and mapped to provider-neutral CapabilityTypes.
- Decoupled from execution: Recipe declares what happens and in what order (stages, phases, dependencies);
  S27 ModelRouter retains provider execution authority.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ai.contracts.common import CapabilityType
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.recipe import RecipeDefinition, RecipeStage
from ai.recipes.contracts import (
    ProviderNeutralityViolationError,
    RecipeNotFoundError,
    RecipeValidationError,
)

logger = logging.getLogger(__name__)

import re

# Strict list of forbidden third-party provider / vendor names checked with word boundaries
FORBIDDEN_PROVIDER_PATTERNS = [
    re.compile(r"\bopenai\b", re.IGNORECASE),
    re.compile(r"\belevenlabs\b", re.IGNORECASE),
    re.compile(r"\beleven_v3\b", re.IGNORECASE),
    re.compile(r"\bheygen\b", re.IGNORECASE),
    re.compile(r"\bfal(?:\.ai|_seedance|-ai)?\b", re.IGNORECASE),
    re.compile(r"\bgroq\b", re.IGNORECASE),
    re.compile(r"\brunpod\b", re.IGNORECASE),
    re.compile(r"\bsuno\b", re.IGNORECASE),
    re.compile(r"\breplicate\b", re.IGNORECASE),
    re.compile(r"\bbytedance\b", re.IGNORECASE),
    re.compile(r"\bseedance\b", re.IGNORECASE),
]

# Normalization mapping for platforms
PLATFORM_NORMALIZATION: Dict[str, str] = {
    "instagram": "instagram_reels",
    "instagram reels": "instagram_reels",
    "instagram_reels": "instagram_reels",
    "reels": "instagram_reels",
    "tiktok": "tiktok",
    "youtube_shorts": "youtube_shorts",
    "youtube shorts": "youtube_shorts",
    "shorts": "youtube_shorts",
    "youtube": "youtube",
    "linkedin": "linkedin",
    "x": "x_twitter",
    "x_twitter": "x_twitter",
    "twitter": "x_twitter",
    "facebook": "facebook",
    "website": "website",
    "landing_page": "landing_page",
    "product_hunt": "product_hunt",
    "ads": "paid_ads",
}


def assert_provider_neutral(obj: Any, path: str = "") -> None:
    """
    Recursively inspects a data structure or Pydantic model to verify that
    no third-party cloud provider names are present in any string value.
    """
    if isinstance(obj, str):
        for pattern in FORBIDDEN_PROVIDER_PATTERNS:
            match = pattern.search(obj)
            if match:
                raise ProviderNeutralityViolationError(
                    f"Provider neutrality violation at '{path}': found forbidden provider name '{match.group(0)}' in value '{obj}'"
                )
    elif isinstance(obj, dict):
        for k, v in obj.items():
            assert_provider_neutral(k, f"{path}.key[{k}]")
            assert_provider_neutral(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple, set)):
        for idx, item in enumerate(obj):
            assert_provider_neutral(item, f"{path}[{idx}]")
    elif hasattr(obj, "model_dump"):
        assert_provider_neutral(obj.model_dump(), path)


class RecipeRegistry:
    """
    Authoritative registry of validated, provider-neutral production recipes.
    Loads and migrates legacy recipes from recipes/ into typed RecipeDefinitions.
    """

    def __init__(self, recipe_dir: Optional[Path] = None, auto_load: bool = True) -> None:
        self.recipe_dir = recipe_dir or (Path(__file__).resolve().parent.parent.parent / "recipes")
        self._recipes: Dict[str, RecipeDefinition] = {}
        self._legacy_provider_audit: Dict[str, List[str]] = {}

        if auto_load and self.recipe_dir.exists():
            self.load_from_directory(self.recipe_dir)

    def load_from_directory(self, dir_path: Path) -> None:
        """Discovers and migrates all legacy recipes in the target directory."""
        json_files = sorted(dir_path.glob("*.json"))
        for json_path in json_files:
            if json_path.name == "schema.json":
                continue  # Skip legacy draft schema
            try:
                recipe = self._migrate_recipe_file(json_path)
                self.register(recipe)
            except Exception as e:
                logger.error("Failed to migrate legacy recipe %s: %s", json_path, e)
                raise RecipeValidationError(f"Failed to migrate recipe '{json_path.name}': {e}") from e

    def _migrate_recipe_file(self, json_path: Path) -> RecipeDefinition:
        """Parses a legacy JSON recipe file and wraps it into a canonical RecipeDefinition."""
        raw_text = json_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)

        recipe_id = data.get("id") or json_path.stem

        # 1. Audit legacy provider bindings
        legacy_bindings = self._audit_legacy_providers(data)
        if legacy_bindings:
            self._legacy_provider_audit[recipe_id] = legacy_bindings

        # 2. Extract and normalize metadata
        name = data.get("name", recipe_id.replace("-", " ").title())
        version = data.get("version", "1.0.0")
        description = self._clean_provider_names(data.get("description", f"Production recipe for {name}"))
        best_for = [self._clean_provider_names(item) for item in data.get("best_for", ["General video production"])]
        not_for = [self._clean_provider_names(item) for item in data.get("not_for", [])]

        raw_platforms = data.get("platforms", ["instagram_reels", "tiktok", "youtube_shorts"])
        platforms = [PLATFORM_NORMALIZATION.get(p.lower().strip(), p.lower().strip()) for p in raw_platforms]
        aspect_ratios = data.get("aspect_ratios", ["9:16"])

        duration_dict = data.get("duration_seconds", {})
        min_sec = float(duration_dict.get("min", 15.0))
        max_sec = float(duration_dict.get("max", 60.0))
        target_sec = float(duration_dict.get("target", (min_sec + max_sec) / 2.0))

        # 3. Determine canonical supported intents
        supported_intents = self._resolve_supported_intents(recipe_id, best_for, data.get("routing_keywords", []))

        # 4. Determine canonical supported audio modes
        supported_audio_modes = self._resolve_supported_audio_modes(recipe_id)

        # 5. Determine provider-neutral required and optional capabilities
        required_capabilities, optional_capabilities = self._resolve_capabilities(recipe_id, data)

        # 6. Determine required skills and knowledge from S28-02
        required_skills = self._resolve_required_skills(recipe_id)
        required_knowledge = self._resolve_required_knowledge(recipe_id)

        # 7. Convert stages to provider-neutral RecipeStage models
        stages = self._migrate_stages(recipe_id, data.get("stages", []))

        # 8. Define phases and dependencies
        phases = [
            "INTAKE",
            "SCRIPT_AND_STORYBOARD",
            "ASSET_COLLECTION",
            "COMPOSITION",
            "FINISHING",
            "QUALITY_GATES",
            "PACKAGING",
        ]
        dependencies = self._resolve_dependencies(recipe_id)

        # 9. Routing keywords (cleaned of provider names)
        raw_keywords = data.get("routing_keywords", [recipe_id])
        routing_keywords = [self._clean_provider_names(k) for k in raw_keywords if self._clean_provider_names(k)]
        raw_neg_keywords = data.get("routing_negative_keywords", [])
        routing_negative_keywords = [self._clean_provider_names(k) for k in raw_neg_keywords if self._clean_provider_names(k)]

        deliverables = data.get("deliverables", ["master_video.mp4"])

        # 10. Fallback strategy
        fallback_strategy = self._resolve_fallback_strategy(recipe_id)

        # Build canonical RecipeDefinition
        recipe_def = RecipeDefinition(
            recipe_id=recipe_id,
            name=name,
            version=version,
            owner="CreativePlatform",
            description=description,
            best_for=best_for,
            not_for=not_for,
            platforms=platforms,
            supported_platforms=platforms,
            aspect_ratios=aspect_ratios,
            duration_seconds_min=min_sec,
            duration_seconds_max=max_sec,
            duration_seconds_target=target_sec,
            stages=stages,
            supported_intents=supported_intents,
            supported_audio_modes=supported_audio_modes,
            required_skills=required_skills,
            required_knowledge=required_knowledge,
            required_capabilities=required_capabilities,
            optional_capabilities=optional_capabilities,
            forbidden_capabilities=[],
            phases=phases,
            dependencies=dependencies,
            quality_profile="STANDARD",
            budget_profile=self._resolve_budget_profile(recipe_id),
            fallback_strategy=fallback_strategy,
            routing_keywords=routing_keywords,
            routing_negative_keywords=routing_negative_keywords,
            deliverables=deliverables,
        )

        # Invariant Guard: Provider neutrality verification
        assert_provider_neutral(recipe_def, f"RecipeDefinition[{recipe_id}]")

        return recipe_def

    def _audit_legacy_providers(self, data: Dict[str, Any]) -> List[str]:
        """Collects legacy third-party vendor names found in the unmigrated source JSON."""
        findings = set()
        raw_str = json.dumps(data)
        for pattern in FORBIDDEN_PROVIDER_PATTERNS:
            matches = pattern.findall(raw_str)
            for m in matches:
                findings.add(m.lower())
        return sorted(list(findings))

    def _clean_provider_names(self, text: str) -> str:
        """Removes or neutralizes vendor references for provider-neutral contracts."""
        replacements = [
            (re.compile(r"\belevenlabs(?:\s+eleven_v3)?\b", re.IGNORECASE), "text_to_speech"),
            (re.compile(r"\beleven_v3\b", re.IGNORECASE), "expressive_speech"),
            (re.compile(r"\bopenai_whisper\b", re.IGNORECASE), "speech_to_text"),
            (re.compile(r"\bwhisper(?:-large-v3)?\b", re.IGNORECASE), "speech_to_text"),
            (re.compile(r"\bheygen\b", re.IGNORECASE), "avatar_synthesis"),
            (re.compile(r"\bfal(?:\.ai)?(?:\s+bytedance/seedance-2\.5/[a-z0-9\-]+)?\b", re.IGNORECASE), "video_synthesis"),
            (re.compile(r"\bfal_seedance\b", re.IGNORECASE), "video_synthesis"),
            (re.compile(r"\bseedance\b", re.IGNORECASE), "avatar_motion"),
            (re.compile(r"\bsuno\b", re.IGNORECASE), "music_generation"),
            (re.compile(r"\bopenai\b", re.IGNORECASE), "ai_synthesis"),
            (re.compile(r"\brunpod\b", re.IGNORECASE), "gpu_cluster"),
            (re.compile(r"\bgroq\b", re.IGNORECASE), "fast_speech_alignment"),
            (re.compile(r"\bbytedance\b", re.IGNORECASE), "video_synthesis"),
            (re.compile(r"\breplicate\b", re.IGNORECASE), "video_synthesis"),
        ]
        cleaned = text
        for pattern, repl in replacements:
            cleaned = pattern.sub(repl, cleaned)
        return cleaned

    def _resolve_supported_intents(self, recipe_id: str, best_for: List[str], keywords: List[str]) -> List[str]:
        """Maps recipe metadata to canonical intent categories."""
        intents = set()
        combined = " ".join([recipe_id] + best_for + keywords).lower()

        if any(w in combined for w in ["saas", "سارس", "برنامج", "تطبيق", "screencast", "demo", "استعراض"]):
            intents.add("SAAS_DEMO")
        if any(w in combined for w in ["منتاج", "مونتاج", "montage", "سريع", "ديناميكي", "dynamic", "energetic"]):
            intents.add("DYNAMIC_MONTAGE")
        if any(w in combined for w in ["أفاتار", "avatar", "شخصية", "مقدم"]):
            intents.add("AVATAR_EXPLAINER")
        if any(w in combined for w in ["talking_head", "talking-head", "متحدث", "مؤسس", "مقابلة"]):
            intents.add("TALKING_HEAD")
        if any(w in combined for w in ["شرح", "explainer", "تعليمي", "فكرة"]):
            intents.add("EXPLAINER")
        if any(w in combined for w in ["إعلان", "ad", "ads", "ترويج", "تيك توك", "ريلز", "social"]):
            intents.add("PRODUCT_AD")
            intents.add("REEL_AD")
        if any(w in combined for w in ["مقال", "article", "sprint"]):
            intents.add("ARTICLE_SPRINT")
        if any(w in combined for w in ["longform", "repurpose", "تقطيع"]):
            intents.add("LONGFORM_REPURPOSE")
        if any(w in combined for w in ["review", "مراجعة", "منافس"]):
            intents.add("REVIEW_CONQUEST")
        if any(w in combined for w in ["موشن", "motion graphics", "motion-graphics"]):
            intents.add("MOTION_GRAPHICS")

        if not intents:
            intents.add("GENERAL_VIDEO")
        return sorted(list(intents))

    def _resolve_supported_audio_modes(self, recipe_id: str) -> List[AudioMode]:
        """Assigns governed canonical audio modes compatible with this recipe topology."""
        if recipe_id == "dynamic-montage-ad":
            # Dynamic montage can execute as music-only (pure kinetic montage) or with VO
            return [AudioMode.MUSIC_ONLY, AudioMode.VO_MUSIC, AudioMode.VO_ONLY]

        if recipe_id in ("motion-graphics", "screencast-demo"):
            return [AudioMode.MUSIC_ONLY, AudioMode.VO_MUSIC, AudioMode.VO_ONLY, AudioMode.SILENT]

        if recipe_id in ("captioned-talking-head", "longform-repurpose"):
            # Talking head and repurposed clips strictly require source media audio
            return [AudioMode.SOURCE_AUDIO, AudioMode.SOURCE_AUDIO_MUSIC]

        if recipe_id.startswith("avatar-"):
            # Avatar recipes strictly require spoken voiceover for lip sync
            return [AudioMode.VO_MUSIC, AudioMode.VO_ONLY]

        if recipe_id in ("living-canvas-explainer", "motion-collage-explainer", "faceless-broll-ad"):
            return [AudioMode.VO_MUSIC, AudioMode.MUSIC_ONLY, AudioMode.VO_ONLY]

        if recipe_id == "agent-browser-proof":
            return [AudioMode.VO_ONLY, AudioMode.VO_MUSIC, AudioMode.MUSIC_ONLY, AudioMode.SILENT]

        # Standard commercial default
        return [AudioMode.VO_MUSIC, AudioMode.VO_ONLY]

    def _resolve_capabilities(self, recipe_id: str, data: Dict[str, Any]) -> Tuple[List[CapabilityType], List[CapabilityType]]:
        """Extracts provider-neutral required and optional capabilities."""
        required = set()
        optional = set()

        if recipe_id == "dynamic-montage-ad":
            required.add(CapabilityType.BEAT_DETECTION)
            optional.add(CapabilityType.TEXT_TO_SPEECH)
            optional.add(CapabilityType.SPEECH_ALIGNMENT)
            optional.add(CapabilityType.MUSIC_GENERATION)
            optional.add(CapabilityType.AUDIO_ENHANCE)

        elif recipe_id.startswith("avatar-"):
            required.add(CapabilityType.VIDEO_GENERATION)
            required.add(CapabilityType.LIP_SYNC)
            required.add(CapabilityType.TEXT_TO_SPEECH)
            required.add(CapabilityType.SPEECH_ALIGNMENT)
            optional.add(CapabilityType.IMAGE_GENERATION)
            optional.add(CapabilityType.BEAT_DETECTION)

        elif recipe_id in ("captioned-talking-head", "longform-repurpose"):
            required.add(CapabilityType.SPEECH_TO_TEXT)
            required.add(CapabilityType.SPEECH_ALIGNMENT)
            required.add(CapabilityType.CAPTIONING)
            optional.add(CapabilityType.AUDIO_DENOISE)
            optional.add(CapabilityType.SHOT_DETECTION)

        elif recipe_id in ("faceless-broll-ad", "ugc-ai-ad"):
            required.add(CapabilityType.IMAGE_GENERATION)
            required.add(CapabilityType.VIDEO_GENERATION)
            optional.add(CapabilityType.TEXT_TO_SPEECH)
            optional.add(CapabilityType.SPEECH_ALIGNMENT)

        elif recipe_id == "living-canvas-explainer":
            optional.add(CapabilityType.TEXT_TO_SPEECH)
            optional.add(CapabilityType.SPEECH_ALIGNMENT)
            optional.add(CapabilityType.BEAT_DETECTION)

        elif recipe_id == "motion-collage-explainer":
            required.add(CapabilityType.IMAGE_GENERATION)
            optional.add(CapabilityType.VIDEO_GENERATION)
            optional.add(CapabilityType.TEXT_TO_SPEECH)

        elif recipe_id in ("agent-browser-proof", "screencast-demo"):
            required.add(CapabilityType.VIDEO_UNDERSTANDING)
            optional.add(CapabilityType.TEXT_TO_SPEECH)

        else:
            optional.add(CapabilityType.TEXT_TO_SPEECH)
            optional.add(CapabilityType.SPEECH_ALIGNMENT)

        return sorted(list(required), key=lambda x: x.value), sorted(list(optional), key=lambda x: x.value)

    def _resolve_required_skills(self, recipe_id: str) -> List[str]:
        """Maps to canonical S28-02 skill identifiers."""
        mapping = {
            "dynamic-montage-ad": ["skill_dynamic_montage", "skill_motion_typography"],
            "avatar-explainer": ["skill_avatar_explainer"],
            "avatar-hook-broll": ["skill_avatar_explainer", "skill_broll_assembly"],
            "avatar-insta-split": ["skill_avatar_explainer"],
            "avatar-product-walkthrough": ["skill_avatar_explainer"],
            "avatar-vo-broll": ["skill_avatar_explainer", "skill_broll_assembly"],
            "captioned-talking-head": ["skill_motion_typography"],
            "faceless-broll-ad": ["skill_broll_assembly"],
            "living-canvas-explainer": ["skill_snapcn", "skill_motion_typography"],
            "longform-repurpose": ["skill_motion_typography"],
            "misotts-article-sprint": ["skill_avatar_explainer"],
            "motion-collage-explainer": ["skill_motion_typography"],
            "motion-graphics": ["skill_remocn", "skill_motion_typography"],
            "review-conquest-compilation": ["skill_broll_assembly"],
            "screencast-demo": ["skill_remocn"],
            "tabletop-levels-explainer": ["skill_broll_assembly"],
            "ugc-ai-ad": ["skill_broll_assembly"],
        }
        return mapping.get(recipe_id, [])

    def _resolve_required_knowledge(self, recipe_id: str) -> List[str]:
        """Maps to canonical S28-02 knowledge descriptors."""
        mapping = {
            "living-canvas-explainer": ["know_playbook_living_canvas"],
            "motion-collage-explainer": ["know_playbook_motion_collage"],
            "tabletop-levels-explainer": ["know_playbook_tabletop"],
            "misotts-article-sprint": ["know_playbook_hook_sprint"],
            "review-conquest-compilation": ["know_playbook_video_copy"],
            "avatar-explainer": ["know_sop_seedance_avatar", "know_sop_spoken_vo"],
            "avatar-hook-broll": ["know_sop_seedance_avatar"],
            "avatar-insta-split": ["know_sop_seedance_avatar"],
            "dynamic-montage-ad": ["know_taste_sfx_matrix", "know_eng_audio_sync"],
        }
        return mapping.get(recipe_id, [])

    def _migrate_stages(self, recipe_id: str, raw_stages: List[Dict[str, Any]]) -> List[RecipeStage]:
        """Converts legacy stage dicts into typed, provider-neutral RecipeStage objects."""
        if not raw_stages:
            return [
                RecipeStage(
                    stage_id="intake",
                    title="Intake & Brief Synthesis",
                    actions=["Synthesize creative brief", "Analyze available media"],
                    required_capabilities=[],
                ),
                RecipeStage(
                    stage_id="composition",
                    title="Remotion Composition Assembly",
                    actions=["Assemble timeline layout", "Bind visual motion properties"],
                    required_capabilities=[],
                ),
                RecipeStage(
                    stage_id="quality_gates",
                    title="Technical Probe & QC",
                    actions=["Run probe QC", "Verify safe zones"],
                    required_capabilities=[],
                ),
            ]

        migrated = []
        for idx, stage in enumerate(raw_stages):
            s_id = stage.get("id", f"stage_{idx}")
            title = self._clean_provider_names(stage.get("title", f"Stage {idx}"))
            raw_actions = stage.get("actions", ["Execute stage operations"])
            actions = [self._clean_provider_names(a) for a in raw_actions]

            # Stage capabilities
            stage_caps = []
            s_id_lower = s_id.lower()
            if "voice" in s_id_lower or "tts" in s_id_lower:
                if recipe_id.startswith("avatar-") or recipe_id in ("tabletop-levels-explainer", "misotts-article-sprint"):
                    stage_caps.append(CapabilityType.TEXT_TO_SPEECH)
                    stage_caps.append(CapabilityType.SPEECH_ALIGNMENT)
            if "avatar" in s_id_lower:
                stage_caps.append(CapabilityType.VIDEO_GENERATION)
                stage_caps.append(CapabilityType.LIP_SYNC)

            artifacts = [self._clean_provider_names(art) for art in stage.get("artifacts", [])]
            paid_gen = bool(stage.get("paid_generation", False))

            migrated.append(
                RecipeStage(
                    stage_id=s_id,
                    title=title,
                    actions=actions,
                    required_capabilities=stage_caps,
                    artifacts=artifacts,
                    paid_generation=paid_gen,
                )
            )
        return migrated

    def _resolve_dependencies(self, recipe_id: str) -> List[str]:
        """Returns runtime asset or media dependencies."""
        if recipe_id in ("captioned-talking-head", "longform-repurpose"):
            return ["source_video_asset", "speech_track"]
        if recipe_id in ("agent-browser-proof", "screencast-demo"):
            return ["screen_recording_asset"]
        return []

    def _resolve_budget_profile(self, recipe_id: str) -> str:
        if recipe_id in ("captioned-talking-head", "screencast-demo", "motion-graphics"):
            return "LOW"
        if recipe_id.startswith("avatar-") or recipe_id in ("tabletop-levels-explainer", "ugc-ai-ad"):
            return "HIGH"
        return "STANDARD"

    def _resolve_fallback_strategy(self, recipe_id: str) -> Optional[str]:
        fallbacks = {
            "avatar-explainer": "living-canvas-explainer",
            "avatar-hook-broll": "dynamic-montage-ad",
            "avatar-insta-split": "dynamic-montage-ad",
            "avatar-product-walkthrough": "screencast-demo",
            "avatar-vo-broll": "faceless-broll-ad",
            "tabletop-levels-explainer": "motion-collage-explainer",
            "ugc-ai-ad": "faceless-broll-ad",
        }
        return fallbacks.get(recipe_id)

    def register(self, recipe: RecipeDefinition) -> None:
        """Registers a validated RecipeDefinition into the memory registry."""
        assert_provider_neutral(recipe, f"RecipeRegistry.register({recipe.recipe_id})")
        self._recipes[recipe.recipe_id] = recipe

    def get(self, recipe_id: str) -> Optional[RecipeDefinition]:
        """Retrieves a recipe by its canonical identifier."""
        return self._recipes.get(recipe_id)

    def get_or_raise(self, recipe_id: str) -> RecipeDefinition:
        """Retrieves a recipe or raises RecipeNotFoundError."""
        recipe = self.get(recipe_id)
        if recipe is None:
            raise RecipeNotFoundError(f"Recipe '{recipe_id}' is not registered in the RecipeRegistry.")
        return recipe

    def list_all(self) -> List[RecipeDefinition]:
        """Returns all registered recipe definitions sorted by recipe_id."""
        return [self._recipes[k] for k in sorted(self._recipes.keys())]

    def count(self) -> int:
        """Returns total count of active registered recipes."""
        return len(self._recipes)

    def get_legacy_provider_audit(self) -> Dict[str, List[str]]:
        """Returns the audit record of legacy provider names stripped during migration."""
        return dict(self._legacy_provider_audit)
