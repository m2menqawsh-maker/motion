"""
Version Compatibility Matrix Verification (S11 Closure).
Verifies exact Python behavior for:
- '2.0.0' -> ACCEPTED
- '2.0' -> ACCEPTED
- '3.0.0' -> REJECTED (UNSUPPORTED_VERSION)
- manifest without version -> REJECTED (LEGACY_VERSION_NOT_MIGRATED) under strict mode
"""

import pytest
from scripts.core.manifest_loader import validate_manifest_dict
from scripts.core.manifest_errors import ManifestValidationError


def base_manifest_payload(version=None):
    payload = {
        "project_id": "prj_version_test",
        "created_at": "2026-09-28T12:00:00Z",
        "assets": [
            {
                "asset_id": "ast_vtest",
                "kind": "video",
                "provenance": "user_upload",
                "status": "ready",
                "processed_path": "assets/ready/v.mp4"
            }
        ]
    }
    if version is not None:
        payload["manifest_version"] = version
    return payload


def test_version_2_0_0_accepted():
    payload = base_manifest_payload("2.0.0")
    manifest = validate_manifest_dict(payload)
    assert manifest.manifest_version == "2.0.0"


def test_version_2_0_accepted():
    payload = base_manifest_payload("2.0")
    manifest = validate_manifest_dict(payload)
    assert manifest.manifest_version == "2.0"


def test_version_3_0_0_rejected():
    payload = base_manifest_payload("3.0.0")
    with pytest.raises(ManifestValidationError) as exc_info:
        validate_manifest_dict(payload)
    assert exc_info.value.code == "UNSUPPORTED_VERSION"
    assert "3.0.0" in str(exc_info.value)


def test_unversioned_manifest_rejected_under_strict_mode():
    payload = base_manifest_payload(None)
    with pytest.raises(ManifestValidationError) as exc_info:
        validate_manifest_dict(payload, allow_migrate=False)
    assert exc_info.value.code == "LEGACY_VERSION_NOT_MIGRATED"
