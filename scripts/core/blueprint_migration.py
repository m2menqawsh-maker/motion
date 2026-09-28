"""
scripts/core/blueprint_migration.py — Blueprint Migration Adapter (S12).
Centralized migration and compatibility adapter for legacy Blueprint representations.
Upgrades v1/legacy blueprints to canonical Blueprint v2.
"""
from __future__ import annotations

import copy
from typing import Dict, Any, Optional

from scripts.core.blueprint_errors import BlueprintVersionError, BlueprintValidationError


SUPPORTED_V2_VERSIONS = ["2.0.0", "2.0"]
SUPPORTED_LEGACY_VERSIONS = ["1.0", "1", 1]


def is_legacy_blueprint_v1(raw: Dict[str, Any]) -> bool:
    """Detects whether raw data represents a legacy (v1 or unversioned) Blueprint."""
    if not isinstance(raw, dict):
        return False
    bp_ver = raw.get("blueprint_version")
    if bp_ver in SUPPORTED_V2_VERSIONS:
        return False
    v = raw.get("version")
    return v in SUPPORTED_LEGACY_VERSIONS or ("scenes" in raw and bp_ver is None)


def migrate_blueprint_to_v2(raw: Dict[str, Any], project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Transforms a legacy (v1) blueprint dict into a canonical Blueprint v2 dict.
    Fails closed on unsupported versions or unrecoverable malformed schemas.
    """
    if not isinstance(raw, dict):
        raise BlueprintValidationError(["Blueprint payload must be a JSON object"])

    data = copy.deepcopy(raw)
    bp_ver = data.get("blueprint_version")

    # Already canonical v2
    if bp_ver in SUPPORTED_V2_VERSIONS:
        if project_id and data.get("project_id") != project_id:
            # Keep as-is, let validator handle mismatch
            pass
        return data

    # Check for unsupported explicit versions
    v = data.get("version")
    if v is not None and v not in SUPPORTED_LEGACY_VERSIONS and bp_ver not in SUPPORTED_V2_VERSIONS:
        raise BlueprintVersionError(
            version=str(v),
            supported_versions=SUPPORTED_V2_VERSIONS + [str(lv) for lv in SUPPORTED_LEGACY_VERSIONS]
        )

    # 1. Project ID
    if not data.get("project_id") and project_id:
        data["project_id"] = project_id

    # 2. Metadata, FPS and Aspect Ratio migration
    meta = data.get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}

    if "fps" not in data or data["fps"] is None:
        if "fps" in meta:
            data["fps"] = meta.pop("fps")
        else:
            data["fps"] = 30  # Default only during legacy migration

    if "aspect_ratio" not in data or not data["aspect_ratio"]:
        if "aspect_ratio" in meta:
            data["aspect_ratio"] = meta.pop("aspect_ratio")
        else:
            data["aspect_ratio"] = "16:9"

    # Clean legacy non-metadata keys from meta
    for k in ["duration_sec", "approval", "project_id", "fps", "aspect_ratio"]:
        meta.pop(k, None)
    data["meta"] = meta

    # 3. Audio Migration into canonical AudioPlan
    legacy_audio = data.get("audio") or {}
    canonical_audio: Dict[str, Any] = {}

    # Check top-level legacy audio keys
    vo_ref = data.pop("voiceover", None) or legacy_audio.get("voiceover_ref") or legacy_audio.get("voiceover")
    if vo_ref:
        if isinstance(vo_ref, str):
            canonical_audio["voiceover"] = {"asset_ref": vo_ref, "volume": 1.0, "startFrame": 0}
        elif isinstance(vo_ref, dict) and "asset_ref" in vo_ref:
            canonical_audio["voiceover"] = vo_ref

    music_ref = data.pop("bgm", None) or legacy_audio.get("music_ref") or legacy_audio.get("bgm")
    if music_ref:
        music_vol = data.pop("bgmVolume", None) or legacy_audio.get("bgmVolume") or legacy_audio.get("volume", 0.15)
        ducking_conf = None
        if "music_ducking_db" in legacy_audio:
            ducking_conf = {"enabled": True, "ducking_volume": 0.05, "duck_under": ["voiceover"]}
        elif "ducking" in legacy_audio:
            ducking_conf = legacy_audio["ducking"]

        if isinstance(music_ref, str):
            m_dict: Dict[str, Any] = {"asset_ref": music_ref, "volume": float(music_vol), "startFrame": 0, "loop": True}
            if ducking_conf:
                m_dict["ducking"] = ducking_conf
            canonical_audio["music"] = m_dict
        elif isinstance(music_ref, dict) and "asset_ref" in music_ref:
            canonical_audio["music"] = music_ref

    if "global_sfx" in legacy_audio and isinstance(legacy_audio["global_sfx"], list):
        canonical_audio["global_sfx"] = legacy_audio["global_sfx"]

    if canonical_audio:
        data["audio"] = canonical_audio
    else:
        data.pop("audio", None)

    # 4. Scenes Migration
    scenes = data.get("scenes") or []
    migrated_scenes = []
    for s in scenes:
        if not isinstance(s, dict):
            continue
        sc = copy.deepcopy(s)
        # Transition normalization
        trans = sc.get("transition")
        if isinstance(trans, str):
            sc["transition"] = {"type": trans, "durationFrames": 15}
        elif isinstance(trans, dict):
            if "durationFrames" not in trans:
                trans["durationFrames"] = 15

        # Template props normalization
        if "template_props" not in sc or not isinstance(sc["template_props"], dict):
            sc["template_props"] = sc.get("props") or {}

        migrated_scenes.append(sc)
    data["scenes"] = migrated_scenes

    # 5. Manifest v2 is the sole authority for asset catalog; drop duplicate assets from Blueprint
    data.pop("assets", None)

    # 6. Set version to 2.0.0 and remove legacy version
    data["blueprint_version"] = "2.0.0"
    data.pop("version", None)

    return data
