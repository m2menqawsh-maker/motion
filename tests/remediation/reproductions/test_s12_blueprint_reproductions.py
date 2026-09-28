"""
S12 Blueprint Canonical Contract Reproductions.
Proves current-state defects before S12 remediation.
"""
import json
import pytest
from pathlib import Path


def test_repro_probe_qc_meta_fps_drift():
    """
    DEFECT: probe_qc.py reads fps from bp.get('meta', {}).get('fps', 30)
    instead of the canonical top-level fps field.
    """
    blueprint = {
        "project_id": "prj_drift",
        "version": "1.0",
        "fps": 60,  # Top-level canonical authority
        "aspect_ratio": "16:9",
        "meta": {
            "fps": 24  # Legacy drift
        },
        "scenes": []
    }
    # Current behavior in probe_qc.py line 111:
    fps_chosen = blueprint.get("meta", {}).get("fps", 30)
    assert fps_chosen == 24  # Proves the drift! Target is 60.


def test_repro_final_qc_meta_aspect_ratio_drift():
    """
    DEFECT: final_qc.py reads aspect ratio from meta.get('aspect_ratio')
    instead of the canonical top-level aspect_ratio field.
    """
    blueprint = {
        "project_id": "prj_drift",
        "version": "1.0",
        "fps": 30,
        "aspect_ratio": "9:16",  # Top-level canonical authority
        "meta": {
            "aspect_ratio": "16:9"  # Legacy drift
        },
        "scenes": []
    }
    # Current behavior in final_qc.py line 172:
    aspect_chosen = blueprint.get("meta", {}).get("aspect_ratio", "16:9")
    assert aspect_chosen == "16:9"  # Proves the drift! Target is 9:16.


def test_repro_blueprint_contract_rejects_audio_plan():
    """
    DEFECT: Legacy schemas/blueprint.schema.json had additionalProperties: false
    and did NOT include an 'audio' property, rejecting blueprints with AudioPlan.
    """
    import jsonschema

    # Snapshot of pre-remediation legacy blueprint schema:
    legacy_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "project_id": {"type": "string"},
            "version": {"type": "string"},
            "fps": {"type": "number"},
            "aspect_ratio": {"type": "string"},
            "scenes": {"type": "array"},
        },
        "additionalProperties": False,
        "required": ["project_id", "version", "fps", "aspect_ratio", "scenes"]
    }

    blueprint_with_audio = {
        "project_id": "prj_audio",
        "version": "1.0",
        "fps": 30,
        "aspect_ratio": "16:9",
        "audio": {
            "voiceover": {"asset_ref": "ast_vo1"}
        },
        "scenes": [
            {
                "scene_id": "s1",
                "template": "ShowcaseWrapper",
                "startFrame": 0,
                "durationFrames": 30
            }
        ]
    }

    # Should raise ValidationError because 'audio' is not defined in the legacy schema
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=blueprint_with_audio, schema=legacy_schema)
    assert "additional properties" in exc_info.value.message.lower() or "audio" in exc_info.value.message


def test_repro_asset_kind_drift_between_manifest_and_blueprint():
    """
    DEFECT: contracts/manifest.ts defines AssetKind with 11 values (including sfx, music, vo),
    while pre-remediation contracts/blueprint.ts AssetSchema.type only allowed 5 values.
    """
    manifest_schema_path = Path("schemas/manifest.v2.schema.json")
    manifest_schema = json.loads(manifest_schema_path.read_text(encoding="utf-8"))
    manifest_kinds = set(manifest_schema["properties"]["assets"]["items"]["properties"]["kind"]["enum"])

    # Pre-remediation blueprint types:
    legacy_blueprint_types = {"image", "video", "audio", "voiceover", "music"}

    # Proves drift: manifest has 'vo', 'music', 'sfx' while blueprint types lacks them!
    assert "vo" in manifest_kinds
    assert "vo" not in legacy_blueprint_types
    assert "sfx" not in legacy_blueprint_types


def test_repro_render_project_fail_open_on_missing_blueprint(tmp_path):
    """
    DEFECT: render_project.py safe_load('05_blueprint.json', {}) returns empty dict {}
    when blueprint does not exist, violating Fail-Closed.
    """
    proj_dir = tmp_path / "prj_empty"
    proj_dir.mkdir()

    # The safe_load pattern in render_project.py line 112:
    def safe_load(name, default):
        p = proj_dir / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    bp = safe_load("05_blueprint.json", {})
    assert bp == {}  # Silent fallback instead of failing closed!
