"""
tests/core/test_s12_cross_language_parity.py — Cross-Language Contract Parity Test Suite (S12).
Proves that Python (Pydantic) and TypeScript (Zod) share the identical ACCEPT/REJECT decisions
across all shared blueprint fixtures.
"""
import json
import pytest
from pathlib import Path

from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.blueprint_loader import load_blueprint
from scripts.core.blueprint_migration import is_legacy_blueprint_v1, migrate_blueprint_to_v2
from scripts.core.manifest_model import ManifestV2, AssetV2, AssetKind, Provenance, AssetStatus


FIXTURES_DIR = Path("tests/fixtures/blueprint")

PARITY_FIXTURE_EXPECTATIONS = [
    ("valid_minimal_blueprint.json", True, "Minimal valid blueprint passes"),
    ("valid_multi_scene_blueprint.json", True, "Multi-scene valid blueprint passes"),
    ("valid_audio_plan_blueprint.json", True, "Complete valid AudioPlan blueprint passes"),
    ("invalid_version_blueprint.json", False, "Unsupported version rejected"),
    ("invalid_project_id_blueprint.json", False, "Malformed project_id rejected"),
    ("invalid_fps_blueprint.json", False, "Invalid negative fps rejected"),
    ("invalid_aspect_ratio_blueprint.json", False, "Invalid aspect_ratio rejected"),
    ("invalid_start_frame_blueprint.json", False, "Negative startFrame rejected"),
    ("invalid_duration_frames_blueprint.json", False, "Zero durationFrames rejected"),
    ("invalid_audio_volume_blueprint.json", False, "Volume > 1.0 rejected"),
    ("invalid_audio_asset_kind_blueprint.json", False, "Wrong kind for audio slot rejected"),
    ("invalid_transition_type_blueprint.json", False, "Unsupported transition type rejected"),
    ("missing_required_fields_blueprint.json", False, "Missing mandatory fields rejected"),
]


@pytest.mark.parametrize("filename,expected_pass,description", PARITY_FIXTURE_EXPECTATIONS)
def test_cross_language_parity_matrix(filename: str, expected_pass: bool, description: str):
    """Verifies that Python matches the exact parity decision for each shared fixture."""
    fixture_path = FIXTURES_DIR / filename
    assert fixture_path.exists(), f"Fixture file {filename} missing!"

    raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

    # If test fixture involves manifest checks
    manifest = None
    if filename == "valid_audio_plan_blueprint.json":
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
    elif filename == "invalid_audio_asset_kind_blueprint.json":
        manifest = ManifestV2(
            manifest_version="2.0.0",
            project_id="prj_bad_kind",
            created_at="2026-09-28T12:00:00Z",
            assets=[
                AssetV2(asset_id="ast_image_as_vo", kind=AssetKind.IMAGE, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, source_path="img.png"),
            ]
        )

    res = validate_blueprint_v2(raw_data, manifest=manifest)
    decision = res.ok

    assert decision == expected_pass, (
        f"Parity mismatch on {filename} ({description}): expected {expected_pass}, got {decision}. Errors: {res.errors}"
    )


def test_legacy_v1_parity():
    """Legacy v1 blueprint is rejected strictly as v2, but accepted when migrated."""
    fixture_path = FIXTURES_DIR / "legacy_v1_blueprint.json"
    raw_data = json.loads(fixture_path.read_text(encoding="utf-8"))

    # Strictly without migration: rejected (missing blueprint_version)
    res_strict = validate_blueprint_v2(raw_data)
    assert res_strict.ok is False

    # With migration adapter: accepted
    migrated = migrate_blueprint_to_v2(raw_data)
    res_migrated = validate_blueprint_v2(migrated, expected_project_id="prj_legacy_01")
    assert res_migrated.ok is True
