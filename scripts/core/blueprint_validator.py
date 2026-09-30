"""
scripts/core/blueprint_validator.py — Blueprint Semantic Validation (S12).
Enforces Project Identity, Scene Timing Invariants, AssetKind Compatibility,
and AudioPlan Semantics.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional, Union
from pydantic import ValidationError

from scripts.core.blueprint_model import BlueprintV2, BlueprintSceneV2
from scripts.core.manifest_model import ManifestV2, AssetKind


class BlueprintValidationResult:
    """Structured result of Blueprint validation."""
    def __init__(self, ok: bool, errors: List[str], blueprint: Optional[BlueprintV2] = None):
        self.ok = ok
        self.errors = errors
        self.blueprint = blueprint

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:
        return f"<BlueprintValidationResult ok={self.ok} errors={len(self.errors)}>"


def validate_blueprint_v2(
    data: Union[Dict[str, Any], BlueprintV2],
    expected_project_id: Optional[str] = None,
    manifest: Optional[ManifestV2] = None,
) -> BlueprintValidationResult:
    """
    Validates a Blueprint instance against structural and semantic rules.
    Fails closed on any discrepancy.
    """
    errors: List[str] = []

    # 1. Structural validation
    bp: Optional[BlueprintV2] = None
    if isinstance(data, BlueprintV2):
        bp = data
    else:
        try:
            bp = BlueprintV2.model_validate(data)
        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(p) for p in err["loc"])
                errors.append(f"[{loc}] {err['msg']}")
            return BlueprintValidationResult(ok=False, errors=errors)
        except Exception as e:
            return BlueprintValidationResult(ok=False, errors=[f"Structural validation error: {str(e)}"])

    # 2. Project Identity Invariant
    if expected_project_id and bp.project_id != expected_project_id:
        errors.append(
            f"Project ID mismatch: blueprint contains '{bp.project_id}', but expected '{expected_project_id}'"
        )

    if manifest and bp.project_id != manifest.project_id:
        errors.append(
            f"Project ID mismatch with Manifest: blueprint contains '{bp.project_id}', but manifest has '{manifest.project_id}'"
        )

    # 3. Scene Identity & Timing Invariants
    seen_scene_ids = set()
    manifest_assets_by_id: Dict[str, AssetKind] = {}
    if manifest:
        for a in manifest.assets:
            manifest_assets_by_id[a.asset_id] = a.kind

    for idx, scene in enumerate(bp.scenes):
        # Unique scene_id
        if scene.scene_id in seen_scene_ids:
            errors.append(f"scenes[{idx}]: duplicate scene_id '{scene.scene_id}'")
        seen_scene_ids.add(scene.scene_id)

        # Non-negative startFrame and positive durationFrames
        if scene.startFrame < 0:
            errors.append(f"scenes[{idx}] ('{scene.scene_id}'): startFrame {scene.startFrame} must be >= 0")
        if scene.durationFrames <= 0:
            errors.append(f"scenes[{idx}] ('{scene.scene_id}'): durationFrames {scene.durationFrames} must be >= 1")

        # Transition validation
        if scene.transition:
            if scene.transition.durationFrames >= scene.durationFrames:
                errors.append(
                    f"scenes[{idx}] ('{scene.scene_id}'): transition durationFrames ({scene.transition.durationFrames}) "
                    f"must be strictly less than scene durationFrames ({scene.durationFrames})"
                )

    # 4. AudioPlan Volume Validation
    if bp.audio:
        if bp.audio.voiceover:
            vo = bp.audio.voiceover
            if not (0.0 <= vo.volume <= 1.0):
                errors.append(f"audio.voiceover: volume {vo.volume} must be between 0.0 and 1.0")

        if bp.audio.music:
            bgm = bp.audio.music
            if not (0.0 <= bgm.volume <= 1.0):
                errors.append(f"audio.music: volume {bgm.volume} must be between 0.0 and 1.0")
            if bgm.ducking and not (0.0 <= bgm.ducking.ducking_volume <= 1.0):
                errors.append(f"audio.music.ducking: ducking_volume {bgm.ducking.ducking_volume} must be between 0.0 and 1.0")

        for sfx_idx, sfx in enumerate(bp.audio.global_sfx):
            if not (0.0 <= sfx.volume <= 1.0):
                errors.append(f"audio.global_sfx[{sfx_idx}]: volume {sfx.volume} must be between 0.0 and 1.0")

    # 5. Authoritative Manifest Reference Validation (ASSET-005)
    if manifest:
        from scripts.core.asset_resolution import collect_asset_references, MalformedAssetRefError
        try:
            occurrences = collect_asset_references(bp)
        except MalformedAssetRefError as e:
            errors.append(str(e))
            return BlueprintValidationResult(ok=False, errors=errors, blueprint=bp)

        scene_indices = {s.scene_id: idx for idx, s in enumerate(bp.scenes)}

        for occ in occurrences:
            if occ.is_logical and occ.asset_id:
                aid = occ.asset_id
                if aid not in manifest_assets_by_id:
                    if occ.scene_id:
                        idx = scene_indices.get(occ.scene_id, 0)
                        slot_name = occ.slot.split(".")[-1] if "." in occ.slot else occ.slot
                        slot_desc = "media_ref" if "media_refs" in occ.slot else slot_name
                        errors.append(
                            f"scenes[{idx}] ('{occ.scene_id}'): referenced {slot_desc} '{aid}' not found in manifest"
                        )
                    else:
                        track = occ.field_path.split(".")[1]
                        errors.append(f"audio.{track}: referenced asset '{aid}' not found in manifest")
                elif occ.expected_kinds:
                    found_kind = manifest_assets_by_id[aid]
                    found_kind_str = getattr(found_kind, "value", str(found_kind))
                    is_compat = any(
                        found_kind_str == ek or getattr(found_kind, "name", "").lower() == ek.lower()
                        for ek in occ.expected_kinds
                    )
                    if not is_compat:
                        expected_desc = " or ".join(f"'{k}'" for k in occ.expected_kinds)
                        if occ.scene_id:
                            idx = scene_indices.get(occ.scene_id, 0)
                            slot_name = occ.slot.split(".")[-1] if "." in occ.slot else occ.slot
                            slot_desc = "media_ref" if "media_refs" in occ.slot else slot_name
                            errors.append(
                                f"scenes[{idx}] ('{occ.scene_id}'): {slot_desc} '{aid}' has kind '{found_kind_str}', expected {expected_desc}"
                            )
                        else:
                            track = occ.field_path.split(".")[1]
                            errors.append(
                                f"audio.{track}: asset '{aid}' has kind '{found_kind_str}', expected {expected_desc}"
                            )

    if errors:
        return BlueprintValidationResult(ok=False, errors=errors, blueprint=bp)

    return BlueprintValidationResult(ok=True, errors=[], blueprint=bp)
