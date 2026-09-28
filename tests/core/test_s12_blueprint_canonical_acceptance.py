"""
tests/core/test_s12_blueprint_canonical_acceptance.py — S12 Blueprint Canonical Acceptance Suite.
Tests structural, semantic, timing, asset, and audio invariants for Blueprint v2.
"""
import json
import pytest
from pathlib import Path

from scripts.core.blueprint_model import BlueprintV2, BlueprintSceneV2, AudioPlan, VoiceoverTrack, MusicTrack
from scripts.core.blueprint_loader import load_blueprint, save_blueprint
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.blueprint_migration import is_legacy_blueprint_v1, migrate_blueprint_to_v2
from scripts.core.blueprint_errors import (
    BlueprintError,
    BlueprintNotFoundError,
    BlueprintParseError,
    BlueprintVersionError,
    BlueprintValidationError,
    BlueprintProjectMismatchError,
)
from scripts.core.manifest_model import ManifestV2, AssetV2, AssetKind, Provenance, AssetStatus


FIXTURES_DIR = Path("tests/fixtures/blueprint")


def test_valid_minimal_blueprint_passes():
    """Happy path: Minimal valid Blueprint v2 loads and passes validation."""
    fixture_path = FIXTURES_DIR / "valid_minimal_blueprint.json"
    bp = load_blueprint(fixture_path, expected_project_id="prj_minimal_01")
    assert bp.blueprint_version == "2.0.0"
    assert bp.project_id == "prj_minimal_01"
    assert bp.fps == 30
    assert bp.aspect_ratio == "16:9"
    assert len(bp.scenes) == 1
    assert bp.total_duration_frames == 90
    assert bp.total_duration_seconds == 3.0


def test_valid_multi_scene_blueprint_with_transitions_and_effects():
    """Multi-scene Blueprint with transitions and effects parses and derives duration."""
    fixture_path = FIXTURES_DIR / "valid_multi_scene_blueprint.json"
    bp = load_blueprint(fixture_path, expected_project_id="prj_multi_02")
    assert len(bp.scenes) == 2
    assert bp.scenes[0].transition is not None
    assert bp.scenes[0].transition.type == "fade"
    assert len(bp.scenes[1].effects) == 1
    assert bp.scenes[1].effects[0].effect == "camera-shake"
    # scene 1: 0 to 120, scene 2: 120 to 300
    assert bp.total_duration_frames == 300
    assert bp.total_duration_seconds == 5.0  # 300 / 60


def test_valid_audio_plan_passes_and_validates_against_manifest():
    """Valid AudioPlan with voiceover, background music, and global SFX passes with Manifest."""
    fixture_path = FIXTURES_DIR / "valid_audio_plan_blueprint.json"

    # Construct Manifest matching fixture assets
    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id="prj_audio_03",
        created_at="2026-09-28T12:00:00Z",
        assets=[
            AssetV2(asset_id="ast_vo_lead", kind=AssetKind.VO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="vo.mp3"),
            AssetV2(asset_id="ast_music_ambient", kind=AssetKind.MUSIC, provenance=Provenance.CACHE_REUSE, status=AssetStatus.READY, source_path="music.mp3"),
            AssetV2(asset_id="ast_sfx_impact", kind=AssetKind.SFX, provenance=Provenance.MCP_FETCH, status=AssetStatus.READY, source_path="impact.wav"),
            AssetV2(asset_id="ast_sfx_whoosh", kind=AssetKind.SFX, provenance=Provenance.CACHE_REUSE, status=AssetStatus.READY, source_path="whoosh.wav"),
        ]
    )

    bp = load_blueprint(fixture_path, expected_project_id="prj_audio_03", manifest=manifest)
    assert bp.audio is not None
    assert bp.audio.voiceover is not None
    assert bp.audio.voiceover.asset_ref == "ast_vo_lead"
    assert bp.audio.music is not None
    assert bp.audio.music.volume == 0.2
    assert bp.audio.music.ducking.enabled is True
    assert len(bp.audio.global_sfx) == 1


def test_unsupported_blueprint_version_fails_closed():
    """Blueprint with unsupported version (e.g. 99.0.0) fails validation."""
    fixture_path = FIXTURES_DIR / "invalid_version_blueprint.json"
    with pytest.raises(BlueprintValidationError) as exc_info:
        load_blueprint(fixture_path)
    assert "blueprint_version" in str(exc_info.value)


def test_missing_mandatory_blueprint_file_fails():
    """Missing 05_blueprint.json throws BlueprintNotFoundError."""
    non_existent = Path("projects/prj_nonexistent_xyz_123/05_blueprint.json")
    with pytest.raises(BlueprintNotFoundError):
        load_blueprint(non_existent)


def test_project_id_mismatch_fails_closed():
    """Blueprint project_id mismatching expected_project_id triggers hard failure."""
    fixture_path = FIXTURES_DIR / "valid_minimal_blueprint.json"
    with pytest.raises(BlueprintProjectMismatchError) as exc_info:
        load_blueprint(fixture_path, expected_project_id="prj_expected_different")
    assert "prj_minimal_01" in str(exc_info.value)
    assert "prj_expected_different" in str(exc_info.value)


def test_invalid_fps_fails_closed():
    """Negative or out-of-range FPS fails validation."""
    fixture_path = FIXTURES_DIR / "invalid_fps_blueprint.json"
    with pytest.raises(BlueprintValidationError) as exc_info:
        load_blueprint(fixture_path)
    assert "fps" in str(exc_info.value)


def test_invalid_aspect_ratio_fails_closed():
    """Unsupported aspect ratio fails validation."""
    fixture_path = FIXTURES_DIR / "invalid_aspect_ratio_blueprint.json"
    with pytest.raises(BlueprintValidationError) as exc_info:
        load_blueprint(fixture_path)
    assert "aspect_ratio" in str(exc_info.value)


def test_invalid_start_frame_fails_closed():
    """Negative startFrame fails validation."""
    fixture_path = FIXTURES_DIR / "invalid_start_frame_blueprint.json"
    with pytest.raises(BlueprintValidationError) as exc_info:
        load_blueprint(fixture_path)
    assert "startFrame" in str(exc_info.value)


def test_invalid_duration_frames_fails_closed():
    """Zero or negative durationFrames fails validation."""
    fixture_path = FIXTURES_DIR / "invalid_duration_frames_blueprint.json"
    with pytest.raises(BlueprintValidationError) as exc_info:
        load_blueprint(fixture_path)
    assert "durationFrames" in str(exc_info.value)


def test_duplicate_scene_id_fails_validation():
    """Scenes having duplicate scene_id fail semantic validation."""
    data = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_dup_scene",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "scene_dup", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30},
            {"scene_id": "scene_dup", "template": "ShowcaseWrapper", "startFrame": 30, "durationFrames": 30},
        ]
    }
    res = validate_blueprint_v2(data)
    assert res.ok is False
    assert any("duplicate scene_id" in err for err in res.errors)


def test_invalid_audio_volume_fails_validation():
    """Audio track with volume outside [0.0, 1.0] fails validation."""
    fixture_path = FIXTURES_DIR / "invalid_audio_volume_blueprint.json"
    with pytest.raises(BlueprintValidationError) as exc_info:
        load_blueprint(fixture_path)
    assert "volume" in str(exc_info.value)


def test_wrong_asset_kind_for_audio_slot_fails():
    """Voiceover referencing an 'image' asset fails semantic kind check."""
    fixture_path = FIXTURES_DIR / "invalid_audio_asset_kind_blueprint.json"

    manifest = ManifestV2(
        manifest_version="2.0.0",
        project_id="prj_bad_kind",
        created_at="2026-09-28T12:00:00Z",
        assets=[
            AssetV2(asset_id="ast_image_as_vo", kind=AssetKind.IMAGE, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="img.png"),
        ]
    )

    with pytest.raises(BlueprintValidationError) as exc_info:
        load_blueprint(fixture_path, expected_project_id="prj_bad_kind", manifest=manifest)
    assert "kind" in str(exc_info.value) and ("vo" in str(exc_info.value) or "audio" in str(exc_info.value))


def test_legacy_v1_migration_adapter():
    """Legacy v1 blueprint migrates automatically to canonical v2."""
    fixture_path = FIXTURES_DIR / "legacy_v1_blueprint.json"
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert is_legacy_blueprint_v1(raw) is True

    migrated = migrate_blueprint_to_v2(raw)
    assert migrated["blueprint_version"] == "2.0.0"
    assert "version" not in migrated
    assert migrated["audio"]["voiceover"]["asset_ref"] == "ast_vo_01"
    assert migrated["audio"]["music"]["asset_ref"] == "ast_music_01"
    assert migrated["audio"]["music"]["ducking"]["enabled"] is True
    assert migrated["scenes"][0]["transition"]["type"] == "fade"

    # Must pass canonical validation
    bp = load_blueprint(fixture_path, expected_project_id="prj_legacy_01", allow_migrate=True)
    assert bp.blueprint_version == "2.0.0"
    assert bp.audio.voiceover.asset_ref == "ast_vo_01"


def test_save_and_reload_fidelity(tmp_path):
    """Saving and reloading a Blueprint v2 preserves all fields and types."""
    bp_orig = BlueprintV2(
        blueprint_version="2.0.0",
        project_id="prj_roundtrip",
        fps=60,
        aspect_ratio="21:9",
        scenes=[
            BlueprintSceneV2(
                scene_id="s1",
                template="ShowcaseWrapper",
                startFrame=0,
                durationFrames=120,
                media_refs=["ast_1"],
                sfx_ref="ast_sfx"
            )
        ],
        audio=AudioPlan(
            voiceover=VoiceoverTrack(asset_ref="ast_vo", volume=0.9),
            music=MusicTrack(asset_ref="ast_bgm", volume=0.3)
        ),
        meta={"motion_personality": "Energetic"}
    )

    out_file = tmp_path / "05_blueprint.json"
    save_blueprint(bp_orig, out_file)

    bp_loaded = load_blueprint(out_file, expected_project_id="prj_roundtrip")
    assert bp_loaded.project_id == bp_orig.project_id
    assert bp_loaded.fps == 60
    assert bp_loaded.aspect_ratio == "21:9"
    assert bp_loaded.audio.voiceover.volume == 0.9
    assert bp_loaded.total_duration_frames == 120
    assert bp_loaded.total_duration_seconds == 2.0


def test_blueprint_v2_has_no_duplicate_assets_catalog():
    """
    REGRESSION: Manifest v2 is the sole authority for asset existence, metadata,
    and storage. Blueprint v2 must NEVER duplicate an asset catalog.
    """
    # 1. Python Pydantic model must not have an 'assets' field
    assert "assets" not in BlueprintV2.model_fields

    # 2. JSON Schema must not define an 'assets' property
    schema = json.loads(Path("schemas/blueprint.schema.json").read_text(encoding="utf-8"))
    assert "assets" not in schema.get("properties", {})


def test_transition_ref_structural_envelope_open_to_future_registry():
    """
    REGRESSION: TransitionRef must be an open structural envelope (identifier + timing),
    NOT a closed enum of runtime capabilities. Capability validation is deferred to S15/S16.
    """
    from scripts.core.blueprint_model import TransitionRef

    # Valid structural identifiers pass
    for valid_id in ["fade", "slide", "wipe", "custom_glitch_01", "directional-wipe", "cube_spin_3d"]:
        t = TransitionRef(type=valid_id, durationFrames=20)
        assert t.type == valid_id
        assert t.durationFrames == 20

    # Invalid identifiers fail closed
    for invalid_id in ["bad identifier with spaces", "invalid/slash", ""]:
        with pytest.raises(Exception):
            TransitionRef(type=invalid_id, durationFrames=20)
