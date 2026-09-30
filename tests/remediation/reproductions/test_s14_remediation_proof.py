"""
S14 Green Remediation Proof Tests
Proving that the defects have been eliminated:
- ASSET-005: Multiple Media Reference Surfaces are declaratively discovered and validated.
- ASSET-012: Resolver is fail-closed, raising UnknownAssetReferenceError and never leaking raw references.
- LED-033: Missing or corrupted media_map fails hard with RequiredArtifactMissingError / ArtifactCorruptedError.
"""
import json
import pytest
from pathlib import Path

from scripts.core.state_model import LifecycleState
from scripts.core.blueprint_model import (
    BlueprintV2,
    BlueprintSceneV2,
    SceneContent,
    AudioPlan,
    VoiceoverTrack,
    MusicTrack,
    GlobalSfxTrack,
)
from scripts.core.manifest_model import (
    ManifestV2,
    AssetV2,
    AssetKind,
    Provenance,
    AssetStatus,
)
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.asset_resolution import (
    collect_asset_references,
    resolve_asset_reference,
    parse_asset_ref,
    load_required_media_map,
    UnknownAssetReferenceError,
    MalformedAssetRefError,
    RequiredArtifactMissingError,
    ArtifactCorruptedError,
    AssetResolutionError,
)


def test_asset_005_all_media_surfaces_discovered_and_validated():
    """
    PASS PROOF for ASSET-005:
    Every media-bearing field (audio tracks, scene media_refs, sfx_ref, captions_ref,
    surface.logoSrc, content.images, screen, icons, audioRef) is discovered
    and validated against Manifest v2.
    """
    bp = BlueprintV2(
        blueprint_version="2.0.0",
        project_id="prj_proof_005",
        fps=30,
        aspect_ratio="16:9",
        scenes=[
            BlueprintSceneV2(
                scene_id="scn_01",
                template="MultiMediaCard",
                startFrame=0,
                durationFrames=60,
                media_refs=["ast_img_1"],
                sfx_ref="ast_sfx_pop",
                captions_ref="ast_caps_1",
                surface={"logoSrc": "ast_logo_brand"},
                content=SceneContent(
                    images=["ast_gallery_1", "ast_gallery_2"],
                    screen="ast_screen_video",
                    icons=["ast_icon_star"],
                    audioRef="ast_scene_audio",
                ),
            )
        ],
        audio=AudioPlan(
            voiceover=VoiceoverTrack(asset_ref="ast_vo_main"),
            music=MusicTrack(asset_ref="ast_bgm_track"),
            global_sfx=[GlobalSfxTrack(asset_ref="ast_global_whoosh")],
        ),
    )

    occurrences = collect_asset_references(bp)
    slots = [occ.slot for occ in occurrences]

    # Verify that all 11 distinct surfaces are discovered!
    assert "audio.voiceover" in slots
    assert "audio.music" in slots
    assert "audio.global_sfx" in slots
    assert "scenes.media_refs" in slots
    assert "scenes.sfx_ref" in slots
    assert "scenes.captions_ref" in slots
    assert "scenes.surface.logoSrc" in slots
    assert "scenes.content.images" in slots
    assert "scenes.content.screen" in slots
    assert "scenes.content.icons" in slots
    assert "scenes.content.audioRef" in slots

    # Manifest missing content.images[0]
    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id="prj_proof_005",
        created_at="2026-09-28T12:00:00Z",
        assets=[
            AssetV2(asset_id="ast_vo_main", kind=AssetKind.VO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_bgm_track", kind=AssetKind.MUSIC, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_global_whoosh", kind=AssetKind.SFX, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_img_1", kind=AssetKind.IMAGE, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_sfx_pop", kind=AssetKind.SFX, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_caps_1", kind=AssetKind.JSON, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_logo_brand", kind=AssetKind.LOGO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            # ast_gallery_1 is omitted!
            AssetV2(asset_id="ast_gallery_2", kind=AssetKind.IMAGE, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_screen_video", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_icon_star", kind=AssetKind.ICON, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
            AssetV2(asset_id="ast_scene_audio", kind=AssetKind.AUDIO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY),
        ]
    )

    res = validate_blueprint_v2(bp, manifest=manifest)
    assert res.ok is False
    assert any("ast_gallery_1" in err for err in res.errors), f"Expected ast_gallery_1 error, got: {res.errors}"


def test_asset_012_resolver_fail_closed_and_typed_error():
    """
    PASS PROOF for ASSET-012:
    - Missing logical reference raises UnknownAssetReferenceError with structured context.
    - Never falls back to raw string.
    - Bare URLs or paths fail closed without guessing.
    - Explicit tagged URL passes through.
    """
    media_map = {
        "ast_known": "projects/p1/generations/g1/known.mp4"
    }

    # 1. Valid logical resolution
    resolved = resolve_asset_reference("ast_known", media_map, field_path="scenes[0].media_refs[0]", scene_id="s1")
    assert resolved == "projects/p1/generations/g1/known.mp4"

    # 2. Unknown logical reference: MUST raise UnknownAssetReferenceError
    with pytest.raises(UnknownAssetReferenceError) as exc_info:
        resolve_asset_reference("ast_missing", media_map, field_path="scenes[0].content.screen", scene_id="s1", project_id="p1")

    err = exc_info.value
    assert err.code == "UNKNOWN_ASSET_REFERENCE"
    assert err.asset_id == "ast_missing"
    assert err.scene_id == "s1"
    assert err.field_path == "scenes[0].content.screen"
    assert err.project_id == "p1"
    assert "Logical asset 'ast_missing' not found in media_map" in str(err)

    # 3. Explicit tagged external URL passes through cleanly
    tagged_url = {"kind": "url", "url": "https://cdn.example.com/logo.png"}
    resolved_url = resolve_asset_reference(tagged_url, media_map)
    assert resolved_url == "https://cdn.example.com/logo.png"

    # 4. Bare string URL is NOT guessed: fails closed with MalformedAssetRefError
    with pytest.raises(MalformedAssetRefError) as exc_url:
        resolve_asset_reference("https://cdn.example.com/logo.png", media_map)
    assert exc_url.value.code == "MALFORMED_ASSET_REF"

    # 5. Bare string path is NOT guessed: fails closed with MalformedAssetRefError
    with pytest.raises(MalformedAssetRefError) as exc_path:
        resolve_asset_reference("/etc/passwd", media_map)
    assert exc_path.value.code == "MALFORMED_ASSET_REF"

    # 6. Empty string reference fails closed
    with pytest.raises(MalformedAssetRefError) as exc_empty:
        resolve_asset_reference("", media_map)
    assert exc_empty.value.code == "MALFORMED_ASSET_REF"


def test_led_033_missing_or_corrupt_media_map_fails_hard(tmp_path):
    """
    PASS PROOF for LED-033:
    - Missing media_map in MATERIALIZED state raises RequiredArtifactMissingError.
    - Corrupted JSON or invalid non-object structure raises ArtifactCorruptedError.
    - Escaping paths or non-existent generation files raise ArtifactCorruptedError.
    - Pre-materialization states (e.g. DRAFT) return empty dict safely when map is absent.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    proj_dir = workspace / "projects" / "prj_led_033"
    proj_dir.mkdir(parents=True)

    pub_proj = workspace / "remotion-app" / "public" / "projects" / "prj_led_033"
    gen_dir = pub_proj / "generations" / "gen_001"
    gen_dir.mkdir(parents=True)
    video_file = gen_dir / "hero.mp4"
    video_file.write_text("dummy video", encoding="utf-8")

    # 1. Missing media_map in MATERIALIZED state -> RequiredArtifactMissingError
    with pytest.raises(RequiredArtifactMissingError) as exc_missing:
        load_required_media_map(proj_dir, state=LifecycleState.MATERIALIZED, workspace_root=workspace)
    assert exc_missing.value.code == "REQUIRED_ARTIFACT_MISSING"

    # 2. Missing media_map in pre-materialization state (e.g. BLUEPRINT_READY) -> returns empty dict
    pre_map = load_required_media_map(proj_dir, state=LifecycleState.BLUEPRINT_READY, workspace_root=workspace)
    assert pre_map == {}

    # 3. Corrupt JSON in media_map.json -> ArtifactCorruptedError
    map_file = proj_dir / "media_map.json"
    map_file.write_text("{ broken json", encoding="utf-8")
    with pytest.raises(ArtifactCorruptedError) as exc_corrupt:
        load_required_media_map(proj_dir, state=LifecycleState.MATERIALIZED, workspace_root=workspace)
    assert exc_corrupt.value.code == "ARTIFACT_CORRUPTED"
    assert "Malformed JSON" in exc_corrupt.value.reason

    # 4. JSON is not an object (e.g. array) -> ArtifactCorruptedError
    map_file.write_text('["ast_1"]', encoding="utf-8")
    with pytest.raises(ArtifactCorruptedError) as exc_non_obj:
        load_required_media_map(proj_dir, state=LifecycleState.MATERIALIZED, workspace_root=workspace)
    assert "must be a JSON object" in exc_non_obj.value.reason

    # 5. Path traversal / escape in media_map value -> ArtifactCorruptedError
    map_file.write_text(json.dumps({"ast_1": "../../../etc/passwd"}), encoding="utf-8")
    with pytest.raises(ArtifactCorruptedError) as exc_traversal:
        load_required_media_map(proj_dir, state=LifecycleState.MATERIALIZED, workspace_root=workspace)
    assert "Path traversal" in exc_traversal.value.reason

    # 6. References missing file on disk -> ArtifactCorruptedError
    map_file.write_text(json.dumps({"ast_ghost": "projects/prj_led_033/generations/gen_001/ghost.mp4"}), encoding="utf-8")
    with pytest.raises(ArtifactCorruptedError) as exc_disk:
        load_required_media_map(proj_dir, state=LifecycleState.MATERIALIZED, verify_files_on_disk=True, workspace_root=workspace)
    assert "references missing generation file on disk" in exc_disk.value.reason

    # 7. Valid media_map with existing generation file -> succeeds and returns generation paths
    valid_map_data = {"ast_hero": "projects/prj_led_033/generations/gen_001/hero.mp4"}
    map_file.write_text(json.dumps(valid_map_data), encoding="utf-8")
    loaded = load_required_media_map(proj_dir, state=LifecycleState.MATERIALIZED, verify_files_on_disk=True, workspace_root=workspace)
    assert loaded == valid_map_data
