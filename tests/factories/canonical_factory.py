"""
tests/factories/canonical_factory.py — Authoritative Factory for Canonical E2E Projects & Manifests (S24).

Enforces:
- LED-075 (P0): Zero tolerance for malformed manifest fixtures in E2E.
- Manifest v2 strictly conforms to `manifest.v2.schema.json` and `scripts/core/manifest_model.py`.
- Asset IDs conform to canonical naming: ast_<kind>_<idx>.
- Audio assets are calibrated to canonical -16 LUFS with exact onset sync.
- Taste-compliant master_plan.md and blueprint.schema.json valid blueprints.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.core.manifest_model import (
    ManifestV2,
    AssetV2,
    AssetKind,
    Provenance,
    AssetStatus,
)
from scripts.core.manifest_validator import validate_manifest_schema, validate_manifest_semantic
from scripts.core.state_store import StateStore


def generate_calibrated_tone_wav(
    out_path: Path,
    duration_seconds: float = 3.0,
    target_lufs: float = -16.0,
    with_chime_onsets: bool = False,
) -> Path:
    """Generates a calibrated sine tone normalized to target LUFS (-16 LUFS) for audio-aware E2E."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if with_chime_onsets:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "sine=frequency=880:duration=0.13",
            "-f", "lavfi",
            "-i", "sine=frequency=1320:duration=0.26",
            "-filter_complex",
            f"[0:a]adelay=200|200[a0];[1:a]adelay=340|340[a1];[a0][a1]amix=inputs=2:duration=longest,loudnorm=I={target_lufs}:TP=-1.5:LRA=11[out]",
            "-map", "[out]",
            str(out_path),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration_seconds}",
            "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
            str(out_path),
        ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to generate calibrated audio tone:\n{res.stderr}")
    return out_path


def create_canonical_manifest(
    project_id: str,
    assets: Optional[List[Dict[str, Any]]] = None,
    created_at: str = "2026-09-28T00:00:00Z",
) -> Dict[str, Any]:
    """
    Creates and validates a canonical Manifest v2 dictionary.
    Passes schema and semantic validators fail-closed.
    """
    manifest_dict = {
        "manifest_version": "2.0.0",
        "project_id": project_id,
        "created_at": created_at,
        "assets": assets or [],
        "metadata": {
            "factory": "canonical_factory_v2",
            "environment": "e2e_testing",
        },
    }

    # Strict validation gate
    validate_manifest_schema(manifest_dict)
    validate_manifest_semantic(manifest_dict, expected_project_id=project_id)
    return manifest_dict


def create_canonical_blueprint(
    project_id: str,
    template: str = "animatedtext-element",
    aspect: str = "16:9",
    fps: int = 30,
    duration_frames: int = 90,
    scenes: Optional[List[Dict[str, Any]]] = None,
    assets: Optional[List[Dict[str, Any]]] = None,
    audio: Optional[Dict[str, Any]] = None,
    content_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Creates a canonical Blueprint dictionary conforming to blueprint.schema.json."""
    if scenes is None:
        text_val = "مرحباً بكم في Clean Video Workspace!"
        surface_dict = {"text": text_val}
        content_dict = {"lines": [text_val]}
        template_props: Dict[str, Any] = {}
        if content_override:
            if "lines" in content_override:
                content_dict["lines"] = content_override["lines"]
            if "text" in content_override:
                surface_dict["text"] = content_override["text"]
            for k, v in content_override.items():
                if k in ["words", "images", "screen", "numbers", "range", "path", "icons", "audioRef", "spectrum", "lines"]:
                    content_dict[k] = v
                elif k != "text":
                    template_props[k] = v

        scenes = [
            {
                "scene_id": "scene_01",
                "startFrame": 0,
                "durationFrames": duration_frames,
                "template": template,
                "surface": surface_dict,
                "content": content_dict,
                "template_props": template_props,
            }
        ]

    meta = {
        "motion_personality": "Cinematic",
        "timings_path": f"projects/{project_id}/04_timings.json",
    }
    if not audio and not any(s.get("sfx_ref") for s in scenes):
        meta["silence_requested"] = True

    bp: Dict[str, Any] = {
        "project_id": project_id,
        "blueprint_version": "2.0.0",
        "fps": fps,
        "aspect_ratio": aspect,
        "meta": meta,
        "scenes": scenes,
    }

    if audio:
        bp["audio"] = audio

    return bp


def create_canonical_e2e_project(
    project_dir: Path,
    project_id: str,
    template: str = "animatedtext-element",
    aspect: str = "16:9",
    fps: int = 30,
    duration_frames: int = 90,
    with_audio: bool = False,
    content_override: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Scaffolds and injects all canonical files for an E2E project test run.
    Ensures:
    - 02_asset_manifest.json is canonical Manifest v2.
    - 04_timings.json is canonical timings.
    - master_plan.md satisfies taste gates.
    - 05_blueprint.json satisfies blueprint schema.
    - Initial state in .pipeline_state.json exists and is clean.
    """
    project_dir.mkdir(parents=True, exist_ok=True)
    assets_ready_dir = project_dir / "assets" / "ready"
    assets_ready_dir.mkdir(parents=True, exist_ok=True)

    manifest_assets: List[Dict[str, Any]] = []
    blueprint_assets: List[Dict[str, Any]] = []
    blueprint_audio: Optional[Dict[str, Any]] = None

    # Timings
    duration_seconds = round(duration_frames / fps, 2)
    timings = {
        "words": [
            {"word": "Clean", "start": 0.0, "end": min(1.0, duration_seconds)},
            {"word": "Video", "start": min(1.0, duration_seconds), "end": duration_seconds},
        ],
        "sentences": [
            {"sentence": "Clean Video Workspace Production Run", "start": 0.0, "end": duration_seconds}
        ],
        "silences": [],
    }

    if with_audio:
        sfx_dir = project_dir / "assets" / "sfx"
        sfx_dir.mkdir(parents=True, exist_ok=True)
        tone_path = sfx_dir / "tone_16lufs.wav"
        generate_calibrated_tone_wav(tone_path, duration_seconds=duration_seconds, target_lufs=-16.0)

        manifest_assets.append({
            "asset_id": "ast_sfx_01",
            "kind": "sfx",
            "provenance": "user_upload",
            "status": "ready",
            "source_path": f"projects/{project_id}/assets/sfx/tone_16lufs.wav",
        })
        blueprint_assets.append({
            "asset_id": "ast_sfx_01",
            "kind": "sfx",
            "source": "user_upload",
            "path": "assets/sfx/tone_16lufs.wav",
            "paid": False,
        })
        blueprint_audio = {
            "voiceover": None,
            "music": None,
            "global_sfx": [
                {
                    "asset_id": "ast_sfx_01",
                    "startFrame": 0,
                    "volume": 1.0,
                }
            ],
        }

    # 1. 02_asset_manifest.json
    manifest_data = create_canonical_manifest(project_id, assets=manifest_assets)
    (project_dir / "02_asset_manifest.json").write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 2. 04_timings.json
    (project_dir / "04_timings.json").write_text(
        json.dumps(timings, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 3. master_plan.md
    plan_text = f"""motion_taste_citation
treatment_citation

#### المشهد 1
sentence_index: 1
المدة {duration_seconds} ث
- القالب: {template}
- نمط الإطار: Neon Ring
- الانتقال: Dive

| الكلمة | البداية | النهاية |
|---|---|---|
| Clean | 0.0 | {min(1.0, duration_seconds)} |
| Video | {min(1.0, duration_seconds)} | {duration_seconds} |
"""
    (project_dir / "master_plan.md").write_text(plan_text, encoding="utf-8")

    # 4. 05_blueprint.json
    bp_data = create_canonical_blueprint(
        project_id=project_id,
        template=template,
        aspect=aspect,
        fps=fps,
        duration_frames=duration_frames,
        assets=blueprint_assets,
        audio=blueprint_audio,
        content_override=content_override,
    )
    (project_dir / "05_blueprint.json").write_text(
        json.dumps(bp_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 5. project.json
    project_meta = {
        "project_id": project_id,
        "name": f"E2E Test {project_id}",
        "language": "ar",
        "created_at": "2026-09-28T00:00:00Z",
        "voiceover": {
            "mode": "upload" if with_audio else "none"
        },
    }
    (project_dir / "project.json").write_text(
        json.dumps(project_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 5b. brand.json (Prevents black-frame false positives via calibrated dark slate #1a2238)
    brand_data = {
        "brandName": "Clean Video",
        "logoSrc": None,
        "colors": {
            "primary": "#00F5FF",
            "accent": "#FFD700",
            "background": "#1a2238",
            "text": "#FFFFFF",
        },
        "fonts": {
            "display": "Cairo",
            "body": "Cairo",
        },
    }
    (project_dir / "brand.json").write_text(
        json.dumps(brand_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 6. .pipeline_state.json
    if not (project_dir / StateStore.STATE_FILE).exists():
        StateStore.create(project_dir, project_id)

    return project_dir
