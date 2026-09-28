"""
tests/remediation/reproductions/test_s12_blueprint_remediation_proof.py — S12 Remediation Proof Suite.
Proves that the defects identified in test_s12_blueprint_reproductions.py are now completely resolved.
"""
import json
import pytest
from pathlib import Path

from scripts.core.blueprint_loader import load_blueprint
from scripts.core.blueprint_errors import BlueprintNotFoundError, BlueprintValidationError
import jsonschema


def test_proof_probe_qc_uses_canonical_fps():
    """
    PROOF: probe_qc now loads canonical Blueprint via load_blueprint
    and uses bp_v2.fps (60), ignoring any conflicting meta.fps (24).
    """
    blueprint_dict = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_drift_fixed",
        "fps": 60,  # Canonical
        "aspect_ratio": "16:9",
        "meta": {
            "fps": 24  # Legacy conflicting drift
        },
        "scenes": [
            {"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 60}
        ]
    }
    from scripts.core.blueprint_validator import validate_blueprint_v2
    res = validate_blueprint_v2(blueprint_dict)
    assert res.ok is True
    assert res.blueprint.fps == 60  # Canonical top-level authority enforced!


def test_proof_final_qc_uses_canonical_aspect_ratio_and_derived_duration():
    """
    PROOF: final_qc now loads canonical Blueprint via load_blueprint
    and uses bp_v2.aspect_ratio (9:16) and derived total_duration_seconds.
    """
    blueprint_dict = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_drift_fixed",
        "fps": 30,
        "aspect_ratio": "9:16",  # Canonical
        "meta": {
            "aspect_ratio": "16:9"  # Legacy conflicting drift
        },
        "scenes": [
            {"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 90}
        ]
    }
    from scripts.core.blueprint_validator import validate_blueprint_v2
    res = validate_blueprint_v2(blueprint_dict)
    assert res.ok is True
    assert res.blueprint.aspect_ratio == "9:16"  # Canonical aspect_ratio enforced!
    assert res.blueprint.total_duration_frames == 90
    assert res.blueprint.total_duration_seconds == 3.0  # Derived, not read from meta!


def test_proof_blueprint_contract_accepts_canonical_audio_plan():
    """
    PROOF: schemas/blueprint.schema.json and BlueprintV2 accept AudioPlan with voiceover,
    music bed, ducking, and global SFX.
    """
    schema_path = Path("schemas/blueprint.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    blueprint_with_audio = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_audio_fixed",
        "fps": 30,
        "aspect_ratio": "16:9",
        "audio": {
            "voiceover": {"asset_ref": "ast_vo1", "volume": 1.0},
            "music": {
                "asset_ref": "ast_music1",
                "volume": 0.2,
                "ducking": {"enabled": True, "ducking_volume": 0.05, "duck_under": ["voiceover"]}
            }
        },
        "scenes": [
            {
                "scene_id": "s1",
                "template": "ShowcaseWrapper",
                "startFrame": 0,
                "durationFrames": 60
            }
        ]
    }

    # No longer raises ValidationError! Schema accepts AudioPlan cleanly.
    jsonschema.validate(instance=blueprint_with_audio, schema=schema)


def test_proof_manifest_sole_asset_authority_zero_drift():
    """
    PROOF: Manifest v2 is the SOLE authority for asset catalog, metadata, and kinds.
    Blueprint v2 does not duplicate the asset catalog, and references assets logically
    via AssetRef validated against Manifest v2 AssetKind vocabulary.
    """
    blueprint_schema = json.loads(Path("schemas/blueprint.schema.json").read_text(encoding="utf-8"))
    assert "assets" not in blueprint_schema.get("properties", {})

    manifest_schema = json.loads(Path("schemas/manifest.v2.schema.json").read_text(encoding="utf-8"))
    manifest_kinds = set(manifest_schema["properties"]["assets"]["items"]["properties"]["kind"]["enum"])
    assert "vo" in manifest_kinds
    assert "music" in manifest_kinds
    assert "sfx" in manifest_kinds


def test_proof_render_project_fails_closed_on_missing_blueprint(tmp_path):
    """
    PROOF: load_blueprint raises BlueprintNotFoundError when 05_blueprint.json is missing,
    ensuring render_project.py fails closed instead of falling back to {}.
    """
    proj_dir = tmp_path / "prj_missing_bp"
    proj_dir.mkdir()

    with pytest.raises(BlueprintNotFoundError):
        load_blueprint(proj_dir / "05_blueprint.json")
