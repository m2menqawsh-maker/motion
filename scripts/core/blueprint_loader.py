"""
scripts/core/blueprint_loader.py — Canonical Blueprint Loader & Saver (S12).
Single authoritative entry point for reading, parsing, migrating, and persisting Blueprint files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Union, Optional, Dict, Any

from scripts.core.blueprint_model import BlueprintV2
from scripts.core.blueprint_validator import validate_blueprint_v2
from scripts.core.blueprint_migration import is_legacy_blueprint_v1, migrate_blueprint_to_v2
from scripts.core.blueprint_errors import (
    BlueprintError,
    BlueprintNotFoundError,
    BlueprintParseError,
    BlueprintValidationError,
    BlueprintProjectMismatchError,
)
from scripts.core.manifest_model import ManifestV2


def load_blueprint(
    path_or_dir: Union[str, Path],
    expected_project_id: Optional[str] = None,
    manifest: Optional[ManifestV2] = None,
    allow_migrate: bool = True,
) -> BlueprintV2:
    """
    Authoritative Blueprint Loader.
    Loads 05_blueprint.json, applies centralized migration if legacy,
    and strictly validates against Blueprint v2 contract.
    Fails closed on any corruption, missing file, or contract breach.
    """
    target = Path(path_or_dir)
    if target.is_dir():
        bp_file = target / "05_blueprint.json"
    else:
        bp_file = target

    if not bp_file.exists():
        raise BlueprintNotFoundError(str(bp_file))

    try:
        raw_text = bp_file.read_text(encoding="utf-8")
        if not raw_text.strip():
            raise BlueprintParseError(str(bp_file), "Blueprint file is empty")
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise BlueprintParseError(str(bp_file), str(e))
    except Exception as e:
        if isinstance(e, BlueprintError):
            raise
        raise BlueprintParseError(str(bp_file), str(e))

    if not isinstance(raw_data, dict):
        raise BlueprintValidationError(["Blueprint root content must be a JSON object"])

    # Centralized Migration Adapter
    if allow_migrate and is_legacy_blueprint_v1(raw_data):
        raw_data = migrate_blueprint_to_v2(raw_data, project_id=expected_project_id)

    # Validate against Canonical Blueprint V2
    result = validate_blueprint_v2(
        data=raw_data,
        expected_project_id=expected_project_id,
        manifest=manifest,
    )

    if not result.ok or result.blueprint is None:
        # Check if project mismatch specifically
        if expected_project_id and raw_data.get("project_id") != expected_project_id:
            raise BlueprintProjectMismatchError(
                blueprint_id=str(raw_data.get("project_id")),
                expected_id=expected_project_id,
            )
        raise BlueprintValidationError(result.errors)

    return result.blueprint


def save_blueprint(
    blueprint: Union[BlueprintV2, Dict[str, Any]],
    target_path: Union[str, Path],
) -> None:
    """
    Persists a Blueprint to disk in canonical formatted JSON.
    """
    p = Path(target_path)
    if p.is_dir():
        p = p / "05_blueprint.json"
    p.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(blueprint, BlueprintV2):
        data = blueprint.to_dict()
    else:
        data = blueprint

    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
