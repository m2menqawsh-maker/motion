"""
Acceptance test suite for S11:
Manifest v2 + Canonical Loader + Migration + Project Identity.
Verifies all 15 specific test requirements from the S11 directive.
"""

import json
import pytest
from pathlib import Path
import shutil

from scripts.core.manifest_model import (
    ManifestV2,
    AssetV2,
    AssetKind,
    Provenance,
    AssetStatus,
)
from scripts.core.manifest_errors import (
    ManifestError,
    ManifestNotFoundError,
    ManifestValidationError,
    ManifestMigrationError,
    ProjectIdentityMismatchError,
)
from scripts.core.manifest_loader import (
    load_manifest,
    save_manifest,
    validate_manifest_dict,
)
from scripts.core.manifest_migration import (
    detect_manifest_version,
    migrate_manifest_data,
    migrate_manifest_file,
)
from scripts.core.project_identity import (
    validate_project_identity,
    ProjectIdentityReport,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "manifest"


class TestManifestV2Validation:
    """Tests 1, 2, 3, 4, 5, 6, 12, 13: Schema and Semantic Invariants."""

    def test_01_valid_manifest_v2_passes(self):
        """1. Valid Manifest v2 passes cleanly and produces typed ManifestV2."""
        fixture_path = FIXTURES_DIR / "valid_manifest_v2.json"
        manifest = load_manifest(fixture_path, expected_project_id="prj_canonical_01")
        
        assert isinstance(manifest, ManifestV2)
        assert manifest.manifest_version in ("2.0.0", "2.0")
        assert manifest.project_id == "prj_canonical_01"
        assert len(manifest.assets) == 3
        
        hero = manifest.get_asset("ast_video_hero")
        assert hero is not None
        assert hero.kind == AssetKind.VIDEO
        assert hero.provenance == Provenance.USER_UPLOAD
        assert hero.status == AssetStatus.READY
        assert hero.processed_path == "assets/ready/hero_norm.mp4"

    def test_02_duplicate_asset_ids_fail_semantically(self):
        """2. Duplicate asset IDs fail semantically before any side effects."""
        fixture_path = FIXTURES_DIR / "duplicate_id_manifest.json"
        with pytest.raises(ManifestValidationError) as exc_info:
            load_manifest(fixture_path)
        
        err = exc_info.value
        assert err.code == "DUPLICATE_ASSET_ID"
        assert err.asset_id == "ast_video_hero"
        assert "Duplicate asset_id" in str(err)

    def test_03_invalid_asset_kind_fails(self):
        """3. Invalid AssetKind fails closed with structured error."""
        fixture_path = FIXTURES_DIR / "invalid_kind_manifest.json"
        with pytest.raises(ManifestValidationError) as exc_info:
            load_manifest(fixture_path)
        
        err = exc_info.value
        assert err.code == "INVALID_ASSET_KIND"
        assert "unsupported_executable_format" in str(err)

    def test_04_invalid_provenance_fails(self):
        """4. Invalid provenance fails closed with structured error."""
        fixture_path = FIXTURES_DIR / "invalid_provenance_manifest.json"
        with pytest.raises(ManifestValidationError) as exc_info:
            load_manifest(fixture_path)
        
        err = exc_info.value
        assert err.code == "INVALID_PROVENANCE"
        assert "alien_teleportation" in str(err)

    def test_05_invalid_status_fails(self):
        """5. Invalid status fails closed with structured error."""
        fixture_path = FIXTURES_DIR / "invalid_status_manifest.json"
        with pytest.raises(ManifestValidationError) as exc_info:
            load_manifest(fixture_path)
        
        err = exc_info.value
        assert err.code == "INVALID_STATUS"
        assert "in_the_cloud_somewhere" in str(err)

    def test_06_unsupported_manifest_version_fails(self):
        """6. Unsupported manifest_version fails closed with UNSUPPORTED_VERSION."""
        fixture_path = FIXTURES_DIR / "unsupported_version_manifest.json"
        with pytest.raises(ManifestValidationError) as exc_info:
            load_manifest(fixture_path)
        
        err = exc_info.value
        assert err.code == "UNSUPPORTED_VERSION"
        assert "99.0.0" in str(err)

    def test_12_schema_valid_but_semantic_invalid_fails(self):
        """12. Schema-valid but semantic-invalid Manifest fails (e.g. status=ready without paths)."""
        data = {
            "manifest_version": "2.0.0",
            "project_id": "prj_semantic_test",
            "created_at": "2026-09-28T12:00:00Z",
            "assets": [
                {
                    "asset_id": "ast_empty_ready",
                    "kind": "video",
                    "provenance": "user_upload",
                    "status": "ready",
                    # Both source_path and processed_path are missing!
                    "source_path": None,
                    "processed_path": None
                }
            ]
        }
        with pytest.raises(ManifestValidationError) as exc_info:
            validate_manifest_dict(data)
        
        assert exc_info.value.code == "MISSING_REQUIRED_PATH"
        assert "ast_empty_ready" in str(exc_info.value)

    def test_13_invalid_manifest_leaves_zero_side_effects(self, tmp_path):
        """13. Attempting to load/save invalid manifest leaves no temporary or partial files."""
        target_dir = tmp_path / "projects" / "prj_side_effects"
        target_dir.mkdir(parents=True)
        manifest_file = target_dir / "02_asset_manifest.json"
        
        # Write duplicate id manifest
        shutil.copy(FIXTURES_DIR / "duplicate_id_manifest.json", manifest_file)
        
        files_before = set(target_dir.iterdir())
        with pytest.raises(ManifestValidationError):
            load_manifest(manifest_file)
        
        files_after = set(target_dir.iterdir())
        assert files_before == files_after, "Side effects or temp files were left behind!"


class TestManifestMigration:
    """Tests 7, 8, 9: Deterministic and Idempotent Migration."""

    def test_07_legacy_manifest_migrates_to_v2_correctly(self):
        """7. Legacy Manifest migrates deterministically to v2."""
        fixture_path = FIXTURES_DIR / "legacy_v1_valid_manifest.json"
        legacy_data = json.loads(fixture_path.read_text(encoding="utf-8"))
        
        assert detect_manifest_version(legacy_data) == "1.0.0"
        
        migrated, was_migrated = migrate_manifest_data(legacy_data)
        assert was_migrated is True
        assert migrated["manifest_version"] == "2.0.0"
        assert migrated["project_id"] == "prj_legacy_01"
        assert len(migrated["assets"]) == 3
        
        # Verify first asset: bg_cyber.png
        # Legacy: type="image", source="ready", origin="pixabay", path="assets/ready/bg_cyber.png"
        ast0 = migrated["assets"][0]
        assert ast0["asset_id"] == "ast_bg_01"
        assert ast0["kind"] == "image"
        assert ast0["provenance"] == "mcp_fetch"  # origin: pixabay mapped to mcp_fetch
        assert ast0["status"] == "ready"
        assert ast0["processed_path"] == "assets/ready/bg_cyber.png"
        assert ast0["metadata"]["approved"] is True
        assert ast0["metadata"]["origin_detail"] == "pixabay"
        
        # Verify third asset: whoosh_metal.mp3
        # Legacy: type="sfx", source="cache", origin="pexels", path="assets/cache/whoosh_metal.mp3"
        ast2 = migrated["assets"][2]
        assert ast2["asset_id"] == "ast_whoosh_01"
        assert ast2["kind"] == "sfx"
        assert ast2["provenance"] == "cache_reuse"
        assert ast2["status"] == "ready"
        assert ast2["processed_path"] == "assets/cache/whoosh_metal.mp3"
        
        # Validate resulting dict passes full ManifestV2 validation
        validated = validate_manifest_dict(migrated)
        assert isinstance(validated, ManifestV2)

    def test_08_migration_is_strictly_idempotent(self):
        """8. Migration idempotency: running migration twice on v2 causes zero mutations/drift."""
        fixture_path = FIXTURES_DIR / "legacy_v1_valid_manifest.json"
        legacy_data = json.loads(fixture_path.read_text(encoding="utf-8"))
        
        # First migration pass
        v2_pass1, was_migrated1 = migrate_manifest_data(legacy_data)
        assert was_migrated1 is True
        
        # Second migration pass on output
        v2_pass2, was_migrated2 = migrate_manifest_data(v2_pass1)
        assert was_migrated2 is False
        assert v2_pass1 == v2_pass2

    def test_09_ambiguous_legacy_manifest_not_guessed_silently(self):
        """9. Ambiguous legacy manifest is not guessed; fails closed with ManifestMigrationError."""
        fixture_path = FIXTURES_DIR / "legacy_v1_ambiguous_manifest.json"
        ambiguous_data = json.loads(fixture_path.read_text(encoding="utf-8"))
        
        with pytest.raises(ManifestMigrationError) as exc_info:
            migrate_manifest_data(ambiguous_data)
        
        assert "Cannot migrate ambiguous" in str(exc_info.value)


class TestProjectIdentityEnforcement:
    """Tests 10, 11: Exact Project Identity Matching."""

    def test_10_manifest_project_id_mismatch_fails_closed(self):
        """10. manifest.project_id != expected project ID -> hard failure."""
        fixture_path = FIXTURES_DIR / "project_id_mismatch_manifest.json"
        with pytest.raises(ManifestValidationError) as exc_info:
            load_manifest(fixture_path, expected_project_id="prj_canonical_01")
        
        err = exc_info.value
        assert err.code == "PROJECT_ID_MISMATCH"
        assert "prj_impostor_99" in str(err)
        assert "prj_canonical_01" in str(err)

    def test_11_multi_artifact_project_identity_consistency(self, tmp_path):
        """
        11. Project identity must be consistent across:
        directory name == state.project_id == project.json == manifest.project_id == blueprint.project_id
        """
        project_id = "prj_identity_test"
        pdir = tmp_path / "projects" / project_id
        pdir.mkdir(parents=True)

        # 1. Matching artifacts -> passes
        (pdir / "project.json").write_text(json.dumps({"project_id": project_id}), encoding="utf-8")
        (pdir / "02_asset_manifest.json").write_text(
            json.dumps({
                "manifest_version": "2.0.0",
                "project_id": project_id,
                "created_at": "2026-09-28T12:00:00Z",
                "assets": []
            }),
            encoding="utf-8"
        )
        (pdir / "05_blueprint.json").write_text(json.dumps({"project_id": project_id, "scenes": []}), encoding="utf-8")
        
        report = validate_project_identity(pdir)
        assert report.is_valid is True
        assert report.project_id == project_id

        # 2. Corrupt one artifact with mismatch -> raises ProjectIdentityMismatchError
        (pdir / "05_blueprint.json").write_text(json.dumps({"project_id": "prj_mismatch_bp", "scenes": []}), encoding="utf-8")
        with pytest.raises(ProjectIdentityMismatchError) as exc_info:
            validate_project_identity(pdir)
        
        assert "prj_mismatch_bp" in str(exc_info.value)
        assert project_id in str(exc_info.value)


class TestFailClosedLoaderSemantics:
    """Tests 14, 15: Canonical Loader fail closed behavior."""

    def test_14_missing_manifest_fails_closed(self, tmp_path):
        """14. Missing mandatory manifest does NOT return {} or default; raises ManifestNotFoundError."""
        missing_path = tmp_path / "projects" / "prj_nonexistent" / "02_asset_manifest.json"
        with pytest.raises(ManifestNotFoundError):
            load_manifest(missing_path)

    def test_15_corrupt_json_manifest_fails_closed(self, tmp_path):
        """15. Corrupt JSON raises ManifestValidationError(code='INVALID_JSON')."""
        corrupt_file = tmp_path / "02_asset_manifest.json"
        corrupt_file.write_text("{ unclosed json content", encoding="utf-8")
        
        with pytest.raises(ManifestValidationError) as exc_info:
            load_manifest(corrupt_file)
        
        assert exc_info.value.code == "INVALID_JSON"
