"""
scripts/core/render_input.py — Canonical Render Input Builder & Single Authority (S17 - LED-054).

Single authoritative entrypoint in Python responsible for assembling, validating,
and writing the canonical render envelope for all execution environments:
- Local Render (scripts/render_project.py)
- Docker Render (scripts/render_project.py --docker)
- Studio (scripts/open_studio.py, local and docker)
- Probe QC (scripts/gates/probe_qc.py)

Guarantees 100% payload parity across all consumers, matching what
parseRenderInput() in contracts/render-input.ts expects before pre-mount merge.
"""
from __future__ import annotations

import json
import os
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, Union

from scripts.security.path_security import validate_project_id
from scripts.core.blueprint_loader import load_blueprint
from scripts.core.blueprint_model import BlueprintV2
from scripts.core.blueprint_errors import BlueprintError, BlueprintNotFoundError
from scripts.core.manifest_loader import load_manifest
from scripts.core.manifest_model import ManifestV2
from scripts.core.manifest_errors import ManifestError
from scripts.core.asset_resolution import (
    load_required_media_map,
    validate_asset_refs_against_media_map,
    AssetResolutionError,
)

# Canonical Default Brand Kit matching DEFAULT_BRAND_KIT in contracts/render-input.ts
DEFAULT_BRAND_KIT: Dict[str, Any] = {
    "brandName": "Default",
    "logoSrc": None,
    "colors": {
        "primary": "#00F5FF",
        "accent": "#FFD700",
        "background": "#1a2238",
        "text": "#FFFFFF",
    },
    "fonts": {
        "display": "Cairo",
        "body": "IBMPlexSansArabic",
    },
}

RENDER_PROPS_FILENAME = "render_props.json"


# ─── Error Taxonomy ────────────────────────────────────────────────────────────

class RenderInputError(Exception):
    """Base error for render input assembly and validation domain."""
    def __init__(self, message: str, code: str = "RENDER_INPUT_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class RenderInputMissingArtifactError(RenderInputError):
    """Raised when a mandatory project artifact is missing (e.g. blueprint, media map)."""
    def __init__(self, artifact_name: str, path: str, project_id: Optional[str] = None):
        msg = f"Mandatory artifact '{artifact_name}' missing at '{path}' (project: {project_id or 'unknown'})"
        super().__init__(msg, code="RENDER_INPUT_MISSING_ARTIFACT", details={
            "artifact_name": artifact_name,
            "path": path,
            "project_id": project_id,
        })


class RenderInputValidationError(RenderInputError):
    """Raised when an artifact has invalid schema or content."""
    def __init__(self, artifact_name: str, message: str, project_id: Optional[str] = None):
        super().__init__(f"Validation failed for '{artifact_name}': {message}", code="RENDER_INPUT_VALIDATION_ERROR", details={
            "artifact_name": artifact_name,
            "project_id": project_id,
        })


class RenderInputProjectMismatchError(RenderInputError):
    """Raised when an artifact has an incompatible project_id."""
    def __init__(self, expected: str, actual: str, artifact_name: str):
        super().__init__(
            f"Project ID mismatch in '{artifact_name}': expected '{expected}', found '{actual}'",
            code="RENDER_INPUT_PROJECT_MISMATCH",
            details={"expected": expected, "actual": actual, "artifact_name": artifact_name}
        )


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _validate_brand_local_relative_path(val: Any, field_desc: str, project_id: Optional[str] = None) -> None:
    """
    Validates that a path provided in brand.json (logoSrc or fonts) is strictly a local relative path.
    Rejects:
    - Non-string types (if not None)
    - Control characters (< 0x20, 0x7f) anywhere in the raw string
    - Non-ASCII spaces, formatting, and control characters (Unicode categories Cc, Cf, Cs, Co, Cn, and Zs != ' ')
    - Percent-encoded traversal sequences (%2e, %2f, %5c)
    - Absolute paths starting with '/' or '\'
    - Windows UNC or protocol-relative paths (starting with '\\' or '//')
    - Directory traversal sequences ('..')
    - Any URI scheme (presence of ':' before the first '/' or '\', or any colon if no separator exists)
    """
    if val is None:
        return
    if not isinstance(val, str):
        raise RenderInputValidationError(
            "brand.json",
            f"Expected string path for {field_desc}, got {type(val).__name__}",
            project_id=project_id,
        )

    # 1. C0 control characters and Unicode formatting/whitespace check on the RAW value
    for ch in val:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            raise RenderInputValidationError(
                "brand.json",
                f"Control character {hex(code)} in path '{val}' in {field_desc} rejected.",
                project_id=project_id,
            )
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Cf", "Cs", "Co", "Cn") or (cat == "Zs" and ch != " "):
            raise RenderInputValidationError(
                "brand.json",
                f"Invalid Unicode character '{ch}' (category {cat}) in path '{val}' in {field_desc} rejected.",
                project_id=project_id,
            )

    # 2. Check for percent-encoded evasion (case-insensitive %2e, %2f, %5c)
    lower_val = val.lower()
    if "%2e" in lower_val or "%2f" in lower_val or "%5c" in lower_val:
        raise RenderInputValidationError(
            "brand.json",
            f"Percent-encoded traversal or separator sequence in path '{val}' in {field_desc} rejected.",
            project_id=project_id,
        )

    # 3. Check raw value and cleaned value for leading separators / protocol-relative / UNC paths
    if val.startswith("/") or val.startswith("\\"):
        raise RenderInputValidationError(
            "brand.json",
            f"Non-local asset path or External URL '{val}' in {field_desc} rejected. Remotion requires local relative paths only.",
            project_id=project_id,
        )

    cleaned = val.strip()
    if not cleaned:
        return

    if cleaned.startswith("/") or cleaned.startswith("\\"):
        raise RenderInputValidationError(
            "brand.json",
            f"Non-local asset path or External URL '{val}' in {field_desc} rejected. Remotion requires local relative paths only.",
            project_id=project_id,
        )

    # 4. Check for directory traversal
    if ".." in cleaned or ".." in urllib.parse.unquote(val):
        raise RenderInputValidationError(
            "brand.json",
            f"Directory traversal in path '{val}' in {field_desc} rejected.",
            project_id=project_id,
        )

    # 5. Check for URI schemes or drives: any ':' before first '/' or '\', or colon when no slash exists
    seps = [i for i in [cleaned.find("/"), cleaned.find("\\")] if i != -1]
    first_sep = min(seps) if seps else -1
    colon_idx = cleaned.find(":")
    if colon_idx != -1:
        if first_sep == -1 or colon_idx < first_sep:
            raise RenderInputValidationError(
                "brand.json",
                f"Non-local asset path or External URL scheme in '{val}' for {field_desc} rejected. Remotion requires local materialized assets only.",
                project_id=project_id,
            )


def resolve_project_dir(
    project_dir_or_id: Union[Path, str],
    workspace_root: Optional[Union[Path, str]] = None,
) -> Path:
    """Resolves and validates the project directory path securely."""
    ws = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
    
    p = Path(project_dir_or_id)
    if p.is_dir() and p.exists():
        project_dir = p.resolve()
        validate_project_id(project_dir.name)
        return project_dir

    project_id = validate_project_id(str(project_dir_or_id))
    from scripts.security.path_security import resolve_project_dir as sec_resolve_project_dir
    ws_id = os.environ.get("AGY_WORKSPACE_ID")
    base = ws / "projects" if ws.name != "projects" else ws
    return sec_resolve_project_dir(project_id, workspace_id=ws_id, base_dir=base)


def get_render_props_path(
    project_dir_or_id: Union[Path, str],
    workspace_root: Optional[Union[Path, str]] = None,
) -> Path:
    """Returns the canonical path for render_props.json for a project."""
    project_dir = resolve_project_dir(project_dir_or_id, workspace_root=workspace_root)
    return project_dir / RENDER_PROPS_FILENAME


# ─── Canonical Builder ────────────────────────────────────────────────────────

def build_render_input(
    project_dir_or_id: Union[Path, str],
    workspace_root: Optional[Union[Path, str]] = None,
    verify_files_on_disk: bool = True,
    write_to_disk: bool = True,
) -> Dict[str, Any]:
    """
    Builds the single canonical render envelope for a given project.
    
    All execution environments (Local, Docker, Studio, Probe) MUST call this
    function to construct Remotion render props.
    
    Structure of the returned envelope:
    {
        "projectData": {
            "project": { "title": ..., "fps": ..., "project_id": ... },
            "blueprint": { ... },
            "brand": { ... },
            "overrides": { "scenes": { ... } },
            "media_map": { ... },
            "asset_manifest": { ... } (optional)
        }
    }
    
    Fails closed immediately on missing mandatory artifacts, schema breaches,
    unresolved media references, or project ID mismatches.
    """
    ws = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
    project_dir = resolve_project_dir(project_dir_or_id, workspace_root=ws)
    project_id = project_dir.name

    if not project_dir.exists():
        raise RenderInputMissingArtifactError("project_directory", str(project_dir), project_id=project_id)

    # 1. Manifest Loading (Canonical S11)
    manifest: Optional[ManifestV2] = None
    manifest_file = project_dir / "02_asset_manifest.json"
    if manifest_file.exists():
        try:
            manifest = load_manifest(project_dir, expected_project_id=project_id, allow_migrate=True)
        except ManifestError as e:
            raise RenderInputValidationError("02_asset_manifest.json", str(e), project_id=project_id) from e

    # 2. Blueprint Loading (Canonical S12)
    bp_file = project_dir / "05_blueprint.json"
    if not bp_file.exists():
        raise RenderInputMissingArtifactError("05_blueprint.json", str(bp_file), project_id=project_id)

    try:
        bp_v2: BlueprintV2 = load_blueprint(
            bp_file,
            expected_project_id=project_id,
            manifest=manifest,
            allow_migrate=True,
        )
    except BlueprintNotFoundError as e:
        raise RenderInputMissingArtifactError("05_blueprint.json", str(bp_file), project_id=project_id) from e
    except BlueprintError as e:
        raise RenderInputValidationError("05_blueprint.json", str(e), project_id=project_id) from e

    bp_dict = bp_v2.to_dict()

    # 3. Media Map Loading & Asset Resolution (Canonical S13/S14)
    try:
        media_map = load_required_media_map(
            project_dir,
            verify_files_on_disk=verify_files_on_disk,
            workspace_root=ws,
        )
    except AssetResolutionError as e:
        raise RenderInputValidationError("media_map.json", str(e), project_id=project_id) from e
    except Exception as e:
        raise RenderInputValidationError("media_map.json", f"Failed to load media map: {e}", project_id=project_id) from e

    # Validate asset references in the blueprint against media_map
    media_ref_errors = validate_asset_refs_against_media_map(bp_v2, media_map, project_id=project_id)
    if media_ref_errors:
        raise RenderInputValidationError(
            "media_map.json",
            f"Unresolved media references in blueprint: {'; '.join(media_ref_errors)}",
            project_id=project_id,
        )

    # SEC-009 / Part 2 Item 2: External URLs must be downloaded and materialized locally.
    # Remotion receives local files only and must never receive raw external URLs.
    from scripts.core.asset_resolution import collect_asset_references
    all_occurrences = collect_asset_references(bp_dict)
    for occ in all_occurrences:
        if occ.is_url:
            url_str = occ.parsed.url or (occ.raw_ref.get("url") if isinstance(occ.raw_ref, dict) else str(occ.raw_ref))
            raise RenderInputValidationError(
                "blueprint",
                f"External URL '{url_str}' reached render path without local acquisition. Remotion requires local materialized assets only.",
                project_id=project_id,
            )

    # 4. Project Metadata Loading
    project_json_file = project_dir / "project.json"
    if project_json_file.exists():
        try:
            raw_text = project_json_file.read_text(encoding="utf-8")
            proj_data = json.loads(raw_text)
        except Exception as e:
            raise RenderInputValidationError("project.json", f"Corrupt JSON: {e}", project_id=project_id) from e

        if not isinstance(proj_data, dict):
            raise RenderInputValidationError("project.json", "Must contain a JSON object", project_id=project_id)

        if "project_id" in proj_data and proj_data["project_id"] != project_id:
            raise RenderInputProjectMismatchError(expected=project_id, actual=proj_data["project_id"], artifact_name="project.json")

        project_meta = dict(proj_data)
        project_meta.setdefault("project_id", project_id)
        project_meta.setdefault("title", "Untitled")
        project_meta.setdefault("fps", bp_v2.fps)
    else:
        project_meta = {
            "title": "Untitled",
            "fps": bp_v2.fps,
            "project_id": project_id,
        }

    # 5. Brand Kit Loading
    brand_json_file = project_dir / "brand.json"
    if brand_json_file.exists():
        try:
            raw_text = brand_json_file.read_text(encoding="utf-8")
            brand_data_raw = json.loads(raw_text)
        except Exception as e:
            raise RenderInputValidationError("brand.json", f"Corrupt JSON: {e}", project_id=project_id) from e

        if not isinstance(brand_data_raw, dict):
            raise RenderInputValidationError("brand.json", "Must contain a JSON object", project_id=project_id)

        brand_data = dict(brand_data_raw)
        brand_data.setdefault("brandName", "Default")
        brand_data.setdefault("logoSrc", None)

        # Ensure mandatory colors & fonts exist
        colors = brand_data.get("colors")
        if not isinstance(colors, dict):
            brand_data["colors"] = dict(DEFAULT_BRAND_KIT["colors"])
        else:
            for k, v in DEFAULT_BRAND_KIT["colors"].items():
                colors.setdefault(k, v)

        fonts = brand_data.get("fonts")
        if not isinstance(fonts, dict):
            brand_data["fonts"] = dict(DEFAULT_BRAND_KIT["fonts"])
        else:
            for k, v in DEFAULT_BRAND_KIT["fonts"].items():
                fonts.setdefault(k, v)

        # SEC-009 / Part 2 Item 2 & Round 3 Blocker 2: Whitelist brand.json local relative paths
        logo_src = brand_data.get("logoSrc")
        if logo_src is not None:
            _validate_brand_local_relative_path(logo_src, "brand logoSrc", project_id=project_id)

        fonts = brand_data.get("fonts")
        if isinstance(fonts, dict):
            for font_key, font_val in fonts.items():
                if font_val is not None:
                    _validate_brand_local_relative_path(font_val, f"brand fonts ('{font_key}')", project_id=project_id)
    else:
        brand_data = {
            "brandName": DEFAULT_BRAND_KIT["brandName"],
            "logoSrc": DEFAULT_BRAND_KIT["logoSrc"],
            "colors": dict(DEFAULT_BRAND_KIT["colors"]),
            "fonts": dict(DEFAULT_BRAND_KIT["fonts"]),
        }

    # 6. Overrides Loading
    overrides_json_file = project_dir / "overrides.json"
    if overrides_json_file.exists():
        try:
            raw_text = overrides_json_file.read_text(encoding="utf-8")
            ov_data_raw = json.loads(raw_text)
        except Exception as e:
            raise RenderInputValidationError("overrides.json", f"Corrupt JSON: {e}", project_id=project_id) from e

        if not isinstance(ov_data_raw, dict):
            raise RenderInputValidationError("overrides.json", "Must contain a JSON object", project_id=project_id)

        overrides_data = dict(ov_data_raw)
        scenes_val = overrides_data.get("scenes", {})
        if isinstance(scenes_val, list):
            # Normalize list format (e.g. from scaffold) to mapping scene_id -> SceneOverride
            normalized_scenes: Dict[str, Any] = {}
            for item in scenes_val:
                if isinstance(item, dict) and "scene_id" in item:
                    sid = str(item["scene_id"])
                    normalized_scenes[sid] = {k: v for k, v in item.items() if k != "scene_id"}
            overrides_data["scenes"] = normalized_scenes
        elif isinstance(scenes_val, dict):
            overrides_data["scenes"] = scenes_val
        else:
            raise RenderInputValidationError("overrides.json", "'scenes' must be a dict or list", project_id=project_id)
    else:
        overrides_data = {"scenes": {}}

    # 7. Assemble Canonical Envelope ({ "projectData": { ... } })
    envelope: Dict[str, Any] = {
        "projectData": {
            "project": project_meta,
            "blueprint": bp_dict,
            "brand": brand_data,
            "overrides": overrides_data,
            "media_map": media_map,
        }
    }

    if manifest is not None:
        envelope["projectData"]["asset_manifest"] = manifest.to_dict()

    # 8. Write to Disk
    if write_to_disk:
        out_file = project_dir / RENDER_PROPS_FILENAME
        out_file.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

    return envelope
