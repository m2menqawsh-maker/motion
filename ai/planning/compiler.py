"""
ai/planning/compiler.py
=======================
Canonical Blueprint Compiler for S28-05 (Part C).

Strict Boundary:
- CreativePlan = What should be made.
- Blueprint = How the runtime represents it.
- Compiler is a DETERMINISTIC TRANSLATOR, not an LLM writer.
- Translates high-level CreativePlan + external template decisions + asset refs + registry contracts
  into canonical BlueprintV2.
- READ / VALIDATE only on Template Registry and Asset Registry.
- Fails closed on:
  - Unknown template
  - Unknown asset
  - Invalid duration
  - Impossible overlapping timings
  - Forbidden capability
  - Missing required scene
  - Core validation failure
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Union

from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.plan import (
    BlueprintCompilationResult,
    CompositionPlan,
    CreativePlan,
    CreativeTier,
    CreativeTierDecision,
    ResolvedTemplateDecision,
)
from ai.planning.errors import (
    CompilerValidationError,
    ForbiddenCapabilityCompilerError,
    MissingRequiredSceneCompilerError,
    NeedsCreateEscalationCompilerError,
    TimingCompilerError,
    UnknownAssetCompilerError,
    UnknownTemplateCompilerError,
)
from scripts.core.blueprint_model import (
    AudioDucking,
    AudioPlan,
    BlueprintSceneV2,
    BlueprintV2,
    EffectRef,
    MusicTrack,
    SceneContent,
    TransitionRef,
    VoiceoverTrack,
)
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.manifest_model import ManifestV2
from scripts.core.template_contract import TemplateRegistryContract


class BlueprintCompiler:
    """
    Authoritative, deterministic compiler translating high-level CreativePlans
    into canonical, executable Blueprint v2 contracts.
    """

    def __init__(self, compiler_version: str = "1.0.0") -> None:
        self.compiler_version = compiler_version

    def compile(
        self,
        plan: CreativePlan,
        template_decisions: Optional[
            Union[
                Dict[str, str],
                Dict[str, ResolvedTemplateDecision],
                List[ResolvedTemplateDecision],
                List[CreativeTierDecision],
                Dict[str, CreativeTierDecision],
            ]
        ] = None,
        manifest: Optional[ManifestV2] = None,
        template_registry: Optional[TemplateRegistryContract] = None,
        project_id: Optional[str] = None,
        fps: int = 30,
        aspect_ratio: str = "9:16",
        audio_mode: Optional[AudioMode] = None,
        audio_assets: Optional[Dict[str, str]] = None,
        forbidden_capabilities: Optional[List[str]] = None,
        allow_custom_templates_for_testing: bool = False,
    ) -> BlueprintCompilationResult:
        """
        Compiles a CreativePlan into a structured BlueprintCompilationResult
        containing the canonical BlueprintV2 dictionary.
        """
        bp = self.compile_to_model(
            plan=plan,
            template_decisions=template_decisions,
            manifest=manifest,
            template_registry=template_registry,
            project_id=project_id,
            fps=fps,
            aspect_ratio=aspect_ratio,
            audio_mode=audio_mode,
            audio_assets=audio_assets,
            forbidden_capabilities=forbidden_capabilities,
            allow_custom_templates_for_testing=allow_custom_templates_for_testing,
        )

        return BlueprintCompilationResult(
            success=True,
            blueprint=bp.to_dict(),
            compiler_version=self.compiler_version,
            errors=[],
            warnings=[],
        )

    def compile_to_model(
        self,
        plan: CreativePlan,
        template_decisions: Optional[
            Union[
                Dict[str, str],
                Dict[str, ResolvedTemplateDecision],
                List[ResolvedTemplateDecision],
                List[CreativeTierDecision],
                Dict[str, CreativeTierDecision],
            ]
        ] = None,
        manifest: Optional[ManifestV2] = None,
        template_registry: Optional[TemplateRegistryContract] = None,
        project_id: Optional[str] = None,
        fps: int = 30,
        aspect_ratio: str = "9:16",
        audio_mode: Optional[AudioMode] = None,
        audio_assets: Optional[Dict[str, str]] = None,
        forbidden_capabilities: Optional[List[str]] = None,
        allow_custom_templates_for_testing: bool = False,
    ) -> BlueprintV2:
        """
        Compiles a CreativePlan directly to a validated BlueprintV2 Pydantic instance.
        """
        # 1. Basic Plan & Scene Presence (Section 43 & 45)
        if not plan or not plan.scenes:
            raise MissingRequiredSceneCompilerError("Cannot compile Blueprint: CreativePlan contains zero scenes.")

        target_project_id = project_id or (manifest.project_id if manifest else plan.brief_id)
        if not target_project_id or not target_project_id.strip():
            raise CompilerValidationError("project_id must be a non-empty alphanumeric string.")

        # 2. Normalize Decisions (supports ResolvedTemplateDecision, CreativeTierDecision, string IDs, dicts)
        raw_decisions = template_decisions
        if raw_decisions is None and plan.tier_decisions:
            raw_decisions = plan.tier_decisions

        tier_decisions_by_scene: Dict[str, CreativeTierDecision] = {}
        normalized_decisions: Dict[str, ResolvedTemplateDecision] = {}

        if isinstance(raw_decisions, list):
            for dec in raw_decisions:
                if isinstance(dec, CreativeTierDecision):
                    tier_decisions_by_scene[dec.scene_id] = dec
                elif isinstance(dec, ResolvedTemplateDecision):
                    normalized_decisions[dec.scene_id] = dec
        elif isinstance(raw_decisions, dict):
            for k, v in raw_decisions.items():
                if isinstance(v, CreativeTierDecision):
                    tier_decisions_by_scene[k] = v
                elif isinstance(v, ResolvedTemplateDecision):
                    normalized_decisions[k] = v
                elif isinstance(v, str):
                    normalized_decisions[k] = ResolvedTemplateDecision(
                        scene_id=k,
                        template_id=v,
                        template_props={},
                    )
                elif isinstance(v, dict):
                    normalized_decisions[k] = ResolvedTemplateDecision(
                        scene_id=k,
                        template_id=v.get("template_id", ""),
                        template_props=v.get("template_props", {}),
                    )

        # 3. Template Registry Authority & Template Validation (Section 34 & 36 & 47)
        reg = template_registry or TemplateRegistryContract()

        # 4. Manifest Asset Index (Section 35 & 47)
        manifest_asset_ids: Optional[Set[str]] = None
        if manifest:
            manifest_asset_ids = {a.asset_id for a in manifest.assets}

        # 5. Timing & Scene Assembly (Section 39 & 41 & 42)
        compiled_scenes: List[BlueprintSceneV2] = []
        current_frame = 0

        # Deterministic ordering by scene_index
        sorted_scenes = sorted(plan.scenes, key=lambda s: s.scene_index)

        for scene in sorted_scenes:
            # Check decision presence
            if scene.scene_id not in normalized_decisions and scene.scene_id not in tier_decisions_by_scene:
                raise MissingRequiredSceneCompilerError(
                    f"Missing required template decision for scene '{scene.scene_id}'."
                )

            # Timing Calculation & Validation (Section 41)
            duration_sec = scene.estimated_duration_sec
            if duration_sec <= 0:
                raise TimingCompilerError(
                    f"Invalid non-positive scene duration {duration_sec}s in scene '{scene.scene_id}'."
                )

            duration_frames = max(1, round(duration_sec * fps))
            start_frame = current_frame

            resolved_transition: Optional[TransitionRef] = None
            resolved_effects: List[EffectRef] = []
            template_props: Dict[str, Any] = {}

            if scene.scene_id in tier_decisions_by_scene:
                tier_dec = tier_decisions_by_scene[scene.scene_id]

                # If CREATE escalation: STOP! (Section 49, 91)
                if tier_dec.selected_tier == CreativeTier.CREATE:
                    raise NeedsCreateEscalationCompilerError(
                        f"Cannot compile Blueprint: scene '{scene.scene_id}' requires CREATE escalation (S28-07). "
                        f"REUSE and COMPOSE were insufficient. Compilation stopped awaiting candidate template creation."
                    )

                if tier_dec.selected_tier == CreativeTier.COMPOSE:
                    comp_plan = tier_dec.composition_plan
                    if not comp_plan and plan.compositions:
                        comp_plan = next((c for c in plan.compositions if c.scene_id == scene.scene_id), None)

                    if comp_plan:
                        raw_template_id = comp_plan.base_template_or_primitive
                        for layer in comp_plan.layers:
                            template_props.update(layer.properties)
                        if comp_plan.transition:
                            trans_frames = min(15, max(1, duration_frames - 1))
                            resolved_transition = TransitionRef(
                                type=comp_plan.transition,
                                durationFrames=trans_frames,
                            )
                        if comp_plan.effects:
                            resolved_effects = [EffectRef(effect=e, apply="scene") for e in comp_plan.effects]
                    else:
                        raw_template_id = tier_dec.template_ref or ""
                else:  # REUSE
                    raw_template_id = tier_dec.template_ref or ""
            else:
                decision = normalized_decisions[scene.scene_id]
                raw_template_id = decision.template_id
                template_props = decision.template_props or {}

            if not raw_template_id or not raw_template_id.strip():
                raise UnknownTemplateCompilerError(
                    f"Empty template_id provided for scene '{scene.scene_id}'."
                )

            # Resolve template against Template Registry
            entry = reg.resolve(raw_template_id)
            if not entry or not entry.runtime_available:
                if not allow_custom_templates_for_testing:
                    raise UnknownTemplateCompilerError(
                        f"Unknown or unregistered template '{raw_template_id}' in scene '{scene.scene_id}'."
                    )
                resolved_tpl = raw_template_id
            else:
                resolved_tpl = entry.canonical_id

            # Content construction
            content_text = scene.spoken_text or scene.intent_label.replace("_", " ").title()
            scene_content = SceneContent(text=content_text)

            blueprint_scene = BlueprintSceneV2(
                scene_id=scene.scene_id,
                template=resolved_tpl,
                startFrame=start_frame,
                durationFrames=duration_frames,
                content=scene_content,
                template_props=template_props,
                transition=resolved_transition,
                effects=resolved_effects,
            )
            compiled_scenes.append(blueprint_scene)

            # Advance current frame contiguously
            current_frame += duration_frames

        # Impossible overlapping timings guard (Section 42)
        for i in range(len(compiled_scenes) - 1):
            s1 = compiled_scenes[i]
            s2 = compiled_scenes[i + 1]
            if s2.startFrame < s1.endFrame:
                raise TimingCompilerError(
                    f"Impossible overlapping scene timing: scene '{s2.scene_id}' starts at frame {s2.startFrame} before preceding scene '{s1.scene_id}' ends at frame {s1.endFrame}."
                )

        # 6. Audio Mode & AudioPlan Compilation (Section 14 & 25 & 44)
        active_audio_mode = audio_mode or AudioMode.VO_MUSIC
        audio_plan = self._compile_audio_plan(
            audio_mode=active_audio_mode,
            audio_assets=audio_assets or {},
            manifest_asset_ids=manifest_asset_ids,
            forbidden_capabilities=forbidden_capabilities or [],
        )

        # 7. Construct Canonical Blueprint v2 (Section 31 & 37 & 40)
        primary_motion = (
            sorted_scenes[0].motion_personality if sorted_scenes else "Cinematic"
        )
        meta_dict: Dict[str, Any] = {
            "compiler_version": self.compiler_version,
            "plan_id": plan.plan_id,
            "recipe_id": plan.recipe_id,
            "motion_personality": primary_motion,
        }

        bp = BlueprintV2(
            blueprint_version="2.0.0",
            project_id=target_project_id,
            fps=fps,
            aspect_ratio=aspect_ratio,
            scenes=compiled_scenes,
            audio=audio_plan,
            meta=meta_dict,
        )

        # 8. Canonical Semantic Validation via Core validator (Section 46 & 47)
        val_result = validate_blueprint_v2(
            bp,
            expected_project_id=target_project_id,
            manifest=manifest,
        )
        if not val_result.ok:
            raise CompilerValidationError(
                f"Compiled Blueprint failed Core validation: {val_result.errors}",
                errors=val_result.errors,
            )

        return bp

    def _compile_audio_plan(
        self,
        audio_mode: AudioMode,
        audio_assets: Dict[str, str],
        manifest_asset_ids: Optional[Set[str]],
        forbidden_capabilities: List[str],
    ) -> Optional[AudioPlan]:
        """Compiles canonical AudioPlan while enforcing audio mode and capability safety."""
        # Defense-in-depth: check forbidden capabilities (Section 44)
        if "TEXT_TO_SPEECH" in forbidden_capabilities and "voiceover" in audio_assets:
            raise ForbiddenCapabilityCompilerError(
                "Capability 'TEXT_TO_SPEECH' is forbidden by system policy; cannot compile voiceover."
            )

        if audio_mode == AudioMode.SILENT:
            if audio_assets:
                # Disallow audio assets in silent mode
                for k, v in audio_assets.items():
                    if v and v.strip():
                        raise ForbiddenCapabilityCompilerError(
                            f"Audio asset '{k}={v}' provided in AudioMode.SILENT is strictly forbidden."
                        )
            return None

        if audio_mode == AudioMode.MUSIC_ONLY:
            if "voiceover" in audio_assets and audio_assets["voiceover"]:
                raise ForbiddenCapabilityCompilerError(
                    f"Voiceover track '{audio_assets['voiceover']}' is strictly forbidden in AudioMode.MUSIC_ONLY."
                )

            music_ref = audio_assets.get("music")
            if music_ref:
                if manifest_asset_ids is not None and music_ref not in manifest_asset_ids:
                    raise UnknownAssetCompilerError(
                        f"Music asset reference '{music_ref}' not found in manifest."
                    )
                music_track = MusicTrack(
                    asset_ref=music_ref,
                    volume=0.20,
                    startFrame=0,
                    loop=True,
                    mute=False,
                    ducking=None,
                )
                return AudioPlan(voiceover=None, music=music_track, global_sfx=[])
            return None

        if audio_mode == AudioMode.VO_ONLY:
            vo_ref = audio_assets.get("voiceover")
            if vo_ref:
                if manifest_asset_ids is not None and vo_ref not in manifest_asset_ids:
                    raise UnknownAssetCompilerError(
                        f"Voiceover asset reference '{vo_ref}' not found in manifest."
                    )
                vo_track = VoiceoverTrack(
                    asset_ref=vo_ref,
                    volume=1.0,
                    startFrame=0,
                    mute=False,
                )
                return AudioPlan(voiceover=vo_track, music=None, global_sfx=[])
            return None

        # VO_MUSIC or other combined modes
        vo_track: Optional[VoiceoverTrack] = None
        vo_ref = audio_assets.get("voiceover")
        if vo_ref:
            if manifest_asset_ids is not None and vo_ref not in manifest_asset_ids:
                raise UnknownAssetCompilerError(
                    f"Voiceover asset reference '{vo_ref}' not found in manifest."
                )
            vo_track = VoiceoverTrack(
                asset_ref=vo_ref,
                volume=1.0,
                startFrame=0,
                mute=False,
            )

        music_track: Optional[MusicTrack] = None
        music_ref = audio_assets.get("music")
        if music_ref:
            if manifest_asset_ids is not None and music_ref not in manifest_asset_ids:
                raise UnknownAssetCompilerError(
                    f"Music asset reference '{music_ref}' not found in manifest."
                )
            ducking = AudioDucking(enabled=True, ducking_volume=0.05, duck_under=["voiceover"]) if vo_track else None
            music_track = MusicTrack(
                asset_ref=music_ref,
                volume=0.15,
                startFrame=0,
                loop=True,
                mute=False,
                ducking=ducking,
            )

        if vo_track or music_track:
            return AudioPlan(voiceover=vo_track, music=music_track, global_sfx=[])
        return None
