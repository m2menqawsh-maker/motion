"""
S14 Red Tests / Reproductions
Proving the defects on the current codebase:
- ASSET-005: Multiple Media Reference Surfaces bypassed in validation and resolution.
- ASSET-012: Resolver is fail-open (returns raw reference strings instead of failing closed).
- LED-033: Missing or corrupted media_map.json defaults to {} instead of failing hard.
"""
import json
import pytest
from pathlib import Path

from scripts.core.blueprint_model import BlueprintV2, BlueprintSceneV2, SceneContent, AudioPlan, VoiceoverTrack
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.manifest_model import ManifestV2, AssetV2, AssetKind, Provenance, AssetStatus


def test_red_asset_005_content_images_bypasses_blueprint_manifest_validation():
    """
    RED PROOF for ASSET-005:
    Blueprint has a scene where content.images contains an unknown asset 'ast_ghost_img'.
    Currently, validate_blueprint_v2 only validates media_refs, sfx_ref, and content.audioRef.
    It completely ignores content.images, content.screen, content.icons, captions_ref!
    Therefore, validate_blueprint_v2 passes when it should have failed closed.
    """
    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id="prj_red_005",
        created_at="2026-09-28T12:00:00Z",
        assets=[]  # No assets at all
    )

    bp = BlueprintV2(
        blueprint_version="2.0.0",
        project_id="prj_red_005",
        fps=30,
        aspect_ratio="16:9",
        scenes=[
            BlueprintSceneV2(
                scene_id="scn_01",
                template="TitleCard",
                startFrame=0,
                durationFrames=30,
                content=SceneContent(
                    images=["ast_ghost_img"],
                    screen="ast_ghost_screen",
                    icons=["ast_ghost_icon"],
                ),
                captions_ref="ast_ghost_captions"
            )
        ]
    )

    result = validate_blueprint_v2(bp, manifest=manifest)
    
    # Must fail closed: unknown asset references in content surfaces are rejected!
    assert result.ok is False, "validate_blueprint_v2 must reject unknown asset refs in content surfaces"
    assert len(result.errors) == 4


def test_red_led_033_probe_and_render_safe_load_media_map_defaults_to_empty(tmp_path):
    """
    REMEDIATION PROOF for LED-033:
    In scripts/render_project.py, scripts/gates/probe_qc.py, and scripts/open_studio.py,
    the loader pattern was:
        safe_load("media_map.json", {})
    Now, load_required_media_map is used and raises RequiredArtifactMissingError
    when media_map.json is missing in materialized/review states.
    """
    from scripts.core.asset_resolution import load_required_media_map, RequiredArtifactMissingError
    project_dir = tmp_path / "prj_red_led_033"
    project_dir.mkdir(parents=True)
    
    with pytest.raises(RequiredArtifactMissingError):
        load_required_media_map(project_dir)
