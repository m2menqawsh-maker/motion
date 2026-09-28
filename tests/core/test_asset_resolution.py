"""
tests/core/test_asset_resolution.py — S14 Canonical AssetRef & Fail-Closed Media Resolution Suite (Python).

Comprehensive verification for:
- ASSET-005: Multiple Media Reference Surfaces
- ASSET-012: Resolver Fail-Closed Behavior
- LED-033: Mandatory media_map Loader & Error Surface
- Cross-Language Golden Fixture Consistency
- Negative and Positive contract enforcement
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
    validate_asset_refs_against_media_map,
    UnknownAssetReferenceError,
    MalformedAssetRefError,
    RequiredArtifactMissingError,
    ArtifactCorruptedError,
    AssetResolutionError,
)

GOLDEN_FIXTURE_PATH = Path("contracts/fixtures/asset_resolution_golden.json")


# ─── 1. Cross-Language Golden Fixture Tests ─────────────────────────────────

def test_cross_language_golden_fixtures():
    """Verify that Python adheres to the shared golden fixture identically to TypeScript."""
    assert GOLDEN_FIXTURE_PATH.exists(), f"Golden fixture missing at {GOLDEN_FIXTURE_PATH}"
    data = json.loads(GOLDEN_FIXTURE_PATH.read_text(encoding="utf-8"))

    for tc in data["test_cases"]:
        ref = tc["ref"]
        media_map = tc["media_map"]
        should_succeed = tc["should_succeed"]

        if should_succeed:
            res = resolve_asset_reference(ref, media_map)
            assert res == tc["expected_resolution"], f"Mismatch for {tc['id']}: {res} != {tc['expected_resolution']}"
        else:
            expected_err = tc["expected_error"]
            with pytest.raises(AssetResolutionError) as exc_info:
                resolve_asset_reference(ref, media_map)
            assert exc_info.value.code == expected_err, f"Wrong error code for {tc['id']}: {exc_info.value.code} != {expected_err}"


# ─── 2. Negative Tests Suite ─────────────────────────────────────────────────

def test_negative_unknown_image_logical_ref():
    """Unknown image logical ref fails closed."""
    media_map = {"ast_known_img": "projects/p1/generations/g1/known.png"}
    with pytest.raises(UnknownAssetReferenceError) as exc:
        resolve_asset_reference("ast_unknown_img", media_map, field_path="scenes[0].content.images[0]")
    assert exc.value.code == "UNKNOWN_ASSET_REFERENCE"
    assert exc.value.asset_id == "ast_unknown_img"


def test_negative_unknown_video_screen_logical_ref():
    """Unknown video/screen logical ref fails closed."""
    media_map = {"ast_known": "projects/p1/generations/g1/known.mp4"}
    with pytest.raises(UnknownAssetReferenceError) as exc:
        resolve_asset_reference("ast_unknown_screen", media_map, field_path="scenes[0].content.screen")
    assert exc.value.code == "UNKNOWN_ASSET_REFERENCE"
    assert exc.value.asset_id == "ast_unknown_screen"


def test_negative_unknown_icon_logical_ref():
    """Unknown icon logical ref fails closed."""
    media_map = {}
    with pytest.raises(UnknownAssetReferenceError) as exc:
        resolve_asset_reference("ast_missing_icon", media_map, field_path="scenes[0].content.icons[0]")
    assert exc.value.code == "UNKNOWN_ASSET_REFERENCE"


def test_negative_unknown_audio_logical_ref():
    """Unknown voiceover/music audio logical ref fails closed."""
    media_map = {}
    with pytest.raises(UnknownAssetReferenceError) as exc:
        resolve_asset_reference("ast_missing_vo", media_map, field_path="audio.voiceover.asset_ref")
    assert exc.value.code == "UNKNOWN_ASSET_REFERENCE"


def test_negative_unknown_sfx_logical_ref():
    """Unknown scene SFX ref fails closed."""
    media_map = {}
    with pytest.raises(UnknownAssetReferenceError) as exc:
        resolve_asset_reference("ast_missing_sfx", media_map, field_path="scenes[0].sfx_ref")
    assert exc.value.code == "UNKNOWN_ASSET_REFERENCE"


def test_negative_empty_string_asset_ref():
    """Empty string asset ref raises MalformedAssetRefError."""
    with pytest.raises(MalformedAssetRefError) as exc:
        parse_asset_ref("")
    assert exc.value.code == "MALFORMED_ASSET_REF"


def test_negative_malformed_tagged_ref_unknown_kind():
    """Tagged ref with invalid kind raises MalformedAssetRefError."""
    with pytest.raises(MalformedAssetRefError) as exc:
        parse_asset_ref({"kind": "ftp_server", "path": "ftp://example.com"})
    assert exc.value.code == "MALFORMED_ASSET_REF"


def test_negative_malformed_tagged_ref_missing_properties():
    """Tagged ref missing required asset_id or url raises MalformedAssetRefError."""
    with pytest.raises(MalformedAssetRefError):
        parse_asset_ref({"kind": "asset"})  # missing asset_id
    with pytest.raises(MalformedAssetRefError):
        parse_asset_ref({"kind": "url"})  # missing url


def test_negative_bare_url_string_disallowed():
    """Bare URL string cannot guess URL semantics and must fail closed."""
    with pytest.raises(MalformedAssetRefError) as exc:
        parse_asset_ref("https://external-cdn.com/asset.png")
    assert exc.value.code == "MALFORMED_ASSET_REF"
    assert "looks like a URL" in exc.value.reason


def test_negative_bare_path_string_disallowed():
    """Bare filesystem path cannot guess path semantics and must fail closed."""
    with pytest.raises(MalformedAssetRefError) as exc:
        parse_asset_ref("/var/media/sample.png")
    assert exc.value.code == "MALFORMED_ASSET_REF"
    assert "looks like a filesystem path" in exc.value.reason


def test_negative_missing_media_map_post_materialization(tmp_path):
    """Post-materialization lifecycle state rejects missing media_map.json."""
    proj = tmp_path / "prj_missing"
    proj.mkdir()
    with pytest.raises(RequiredArtifactMissingError) as exc:
        load_required_media_map(proj, state=LifecycleState.MATERIALIZED, workspace_root=tmp_path)
    assert exc.value.code == "REQUIRED_ARTIFACT_MISSING"


def test_negative_malformed_json_media_map(tmp_path):
    """Malformed JSON in media_map.json raises ArtifactCorruptedError."""
    proj = tmp_path / "prj_corrupt_json"
    proj.mkdir()
    (proj / "media_map.json").write_text("{ unclosed", encoding="utf-8")
    with pytest.raises(ArtifactCorruptedError) as exc:
        load_required_media_map(proj, state=LifecycleState.MATERIALIZED, workspace_root=tmp_path)
    assert exc.value.code == "ARTIFACT_CORRUPTED"


def test_negative_media_map_not_an_object(tmp_path):
    """media_map.json containing an array or integer raises ArtifactCorruptedError."""
    proj = tmp_path / "prj_array_map"
    proj.mkdir()
    (proj / "media_map.json").write_text("[\"item1\"]", encoding="utf-8")
    with pytest.raises(ArtifactCorruptedError) as exc:
        load_required_media_map(proj, state=LifecycleState.MATERIALIZED, workspace_root=tmp_path)
    assert "must be a JSON object" in exc.value.reason


def test_negative_media_map_path_escape(tmp_path):
    """media_map.json containing relative path traversal raises ArtifactCorruptedError."""
    proj = tmp_path / "prj_escape"
    proj.mkdir()
    (proj / "media_map.json").write_text(json.dumps({"ast_1": "../../../secret.txt"}), encoding="utf-8")
    with pytest.raises(ArtifactCorruptedError) as exc:
        load_required_media_map(proj, state=LifecycleState.MATERIALIZED, workspace_root=tmp_path)
    assert "Path traversal" in exc.value.reason


def test_negative_media_map_missing_generation_file(tmp_path):
    """media_map pointing to missing file on disk raises ArtifactCorruptedError."""
    workspace = tmp_path / "ws"
    proj = workspace / "projects" / "prj_missing_gen"
    proj.mkdir(parents=True)
    pub = workspace / "remotion-app" / "public"
    pub.mkdir(parents=True)
    (proj / "media_map.json").write_text(
        json.dumps({"ast_1": "projects/prj_missing_gen/generations/gen_001/missing.mp4"}),
        encoding="utf-8"
    )
    with pytest.raises(ArtifactCorruptedError) as exc:
        load_required_media_map(proj, state=LifecycleState.MATERIALIZED, verify_files_on_disk=True, workspace_root=workspace)
    assert "references missing generation file on disk" in exc.value.reason


# ─── 3. Positive Tests Suite ─────────────────────────────────────────────────

def test_positive_valid_logical_reference_resolves_to_generation_path():
    """Valid logical reference resolves deterministically to S13 generation path."""
    media_map = {
        "ast_hero": "projects/prj_01/generations/gen_42/hero.mp4"
    }
    resolved = resolve_asset_reference("ast_hero", media_map)
    assert resolved == "projects/prj_01/generations/gen_42/hero.mp4"


def test_positive_multiple_scenes_reuse_asset():
    """Multiple scenes referencing the same asset ID resolve deterministically."""
    media_map = {
        "ast_shared_bg": "projects/prj_01/generations/gen_42/bg.png"
    }
    r1 = resolve_asset_reference("ast_shared_bg", media_map, scene_id="s1")
    r2 = resolve_asset_reference("ast_shared_bg", media_map, scene_id="s2")
    assert r1 == r2 == "projects/prj_01/generations/gen_42/bg.png"


def test_positive_audioplan_references():
    """Voiceover, music, and global SFX resolve through canonical authority."""
    media_map = {
        "ast_vo": "projects/prj_01/generations/gen_42/vo.mp3",
        "ast_bgm": "projects/prj_01/generations/gen_42/bgm.mp3",
        "ast_sfx": "projects/prj_01/generations/gen_42/whoosh.wav",
    }
    bp = BlueprintV2(
        blueprint_version="2.0.0",
        project_id="prj_01",
        fps=30,
        aspect_ratio="16:9",
        scenes=[],
        audio=AudioPlan(
            voiceover=VoiceoverTrack(asset_ref="ast_vo"),
            music=MusicTrack(asset_ref="ast_bgm"),
            global_sfx=[GlobalSfxTrack(asset_ref="ast_sfx")],
        ),
    )
    errs = validate_asset_refs_against_media_map(bp, media_map, project_id="prj_01")
    assert len(errs) == 0


def test_positive_pre_materialization_tolerates_missing_map(tmp_path):
    """Project before MATERIALIZED (e.g. DRAFT or BLUEPRINT_READY) succeeds without media_map."""
    proj = tmp_path / "prj_draft"
    proj.mkdir()
    result = load_required_media_map(proj, state=LifecycleState.BLUEPRINT_READY, workspace_root=tmp_path)
    assert result == {}


def test_positive_rematerialization_atomic_generation_swap(tmp_path):
    """
    S13 Preservation Invariant:
    When re-materializing from Generation A to Generation B, updating media_map.json
    causes load_required_media_map to immediately read Generation B paths.
    """
    workspace = tmp_path / "ws"
    proj = workspace / "projects" / "prj_atomic"
    proj.mkdir(parents=True)
    pub = workspace / "remotion-app" / "public" / "projects" / "prj_atomic" / "generations"
    gen_a = pub / "gen_001"
    gen_b = pub / "gen_002"
    gen_a.mkdir(parents=True)
    gen_b.mkdir(parents=True)

    (gen_a / "asset.mp4").write_text("gen A content", encoding="utf-8")
    (gen_b / "asset.mp4").write_text("gen B content", encoding="utf-8")

    map_file = proj / "media_map.json"

    # Step 1: Generation A active
    map_file.write_text(json.dumps({"ast_main": "projects/prj_atomic/generations/gen_001/asset.mp4"}), encoding="utf-8")
    map_a = load_required_media_map(proj, state=LifecycleState.MATERIALIZED, verify_files_on_disk=True, workspace_root=workspace)
    assert map_a["ast_main"] == "projects/prj_atomic/generations/gen_001/asset.mp4"

    # Step 2: Generation B committed via atomic swap
    map_file.write_text(json.dumps({"ast_main": "projects/prj_atomic/generations/gen_002/asset.mp4"}), encoding="utf-8")
    map_b = load_required_media_map(proj, state=LifecycleState.MATERIALIZED, verify_files_on_disk=True, workspace_root=workspace)
    assert map_b["ast_main"] == "projects/prj_atomic/generations/gen_002/asset.mp4"
    assert "gen_001" not in map_b["ast_main"]


@pytest.mark.parametrize("state", list(LifecycleState))
def test_lifecycle_state_media_map_requirement_governed_strictly_by_s06_authority(tmp_path, state):
    """
    Parametric verification across EVERY LifecycleState in the system (LED-033):
    1. Queries the single authoritative S06 RequiredEvidencePolicy.
    2. Verifies that load_required_media_map behavior (when media_map is missing)
       deterministically matches RequiredEvidencePolicy.is_artifact_required(state, 'media_map').
    3. Guarantees zero hardcoded lifecycle drift between S06 and S14.
    """
    from scripts.core.evidence_matrix import RequiredEvidencePolicy
    
    is_required = RequiredEvidencePolicy.is_artifact_required(state, "media_map")
    
    proj_dir = tmp_path / f"prj_{state.value.lower()}"
    proj_dir.mkdir(parents=True)
    
    # Save project state without media_map.json
    state_file = proj_dir / ".pipeline_state.json"
    state_file.write_text(json.dumps({
        "project_id": proj_dir.name,
        "lifecycle_state": state.value,
        "revision": 1,
        "artifact_records": []
    }), encoding="utf-8")
    
    if is_required:
        # Must fail closed with RequiredArtifactMissingError!
        with pytest.raises(RequiredArtifactMissingError) as exc_info:
            load_required_media_map(proj_dir, workspace_root=tmp_path)
        assert exc_info.value.artifact_name == "media_map.json"
        
        # Also when state is explicitly passed
        with pytest.raises(RequiredArtifactMissingError):
            load_required_media_map(proj_dir, state=state, workspace_root=tmp_path)
            
        # Corrupted media_map must fail closed with ArtifactCorruptedError!
        (proj_dir / "media_map.json").write_text("NOT_JSON{{{", encoding="utf-8")
        with pytest.raises(ArtifactCorruptedError):
            load_required_media_map(proj_dir, state=state, workspace_root=tmp_path)
    else:
        # Must tolerate missing media_map and return empty dict!
        res1 = load_required_media_map(proj_dir, workspace_root=tmp_path)
        assert res1 == {}
        
        res2 = load_required_media_map(proj_dir, state=state, workspace_root=tmp_path)
        assert res2 == {}
