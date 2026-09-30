"""
scripts/core/asset_resolution.py — Canonical AssetRef Discovery & Fail-Closed Resolution Authority (S14).

Authoritative implementation for:
- AssetRef vocabulary (Logical vs External literal)
- Declarative Media Reference Surfaces (ASSET-005)
- Fail-Closed Media Resolution (ASSET-012)
- Mandatory Media Map Lifecycle Enforcement & Integrity (LED-033)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set
from urllib.parse import urlparse

from scripts.core.failure_model import FailureCode
from scripts.core.state_model import LifecycleState, ProjectState
from scripts.core.security.path_policy import resolve_safe_path


ASSET_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


# ─── 1. Error Taxonomy ────────────────────────────────────────────────────────

class AssetResolutionError(Exception):
    """Base error for asset resolution domain."""
    def __init__(self, message: str, code: str = "ASSET_RESOLUTION_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class UnknownAssetReferenceError(AssetResolutionError):
    """Raised when a logical asset reference cannot be found in media_map.json (ASSET-012)."""
    def __init__(
        self,
        asset_id: str,
        field_path: Optional[str] = None,
        scene_id: Optional[str] = None,
        project_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        loc = f"scene='{scene_id}' field='{field_path or 'unknown'}'" if scene_id else f"field='{field_path or 'unknown'}'"
        proj = f" project='{project_id}'" if project_id else ""
        msg = message or f"Logical asset '{asset_id}' not found in media_map ({loc}{proj})"
        super().__init__(msg, code="UNKNOWN_ASSET_REFERENCE", details={
            "asset_id": asset_id,
            "field_path": field_path,
            "scene_id": scene_id,
            "project_id": project_id,
        })
        self.asset_id = asset_id
        self.field_path = field_path
        self.scene_id = scene_id
        self.project_id = project_id


class MalformedAssetRefError(AssetResolutionError):
    """Raised when an asset reference is invalid, empty, or an unclassified raw URL/path."""
    def __init__(
        self,
        raw_ref: Any,
        reason: str,
        field_path: Optional[str] = None,
        scene_id: Optional[str] = None,
    ):
        loc = f" in scene '{scene_id}'" if scene_id else ""
        at_field = f" at '{field_path}'" if field_path else ""
        msg = f"Malformed asset reference '{raw_ref}'{loc}{at_field}: {reason}"
        super().__init__(msg, code="MALFORMED_ASSET_REF", details={
            "raw_ref": str(raw_ref),
            "reason": reason,
            "field_path": field_path,
            "scene_id": scene_id,
        })
        self.raw_ref = raw_ref
        self.reason = reason
        self.field_path = field_path
        self.scene_id = scene_id


class RequiredArtifactMissingError(AssetResolutionError):
    """Raised when media_map.json is missing in a lifecycle state where it is mandatory (LED-033)."""
    def __init__(self, artifact_name: str, project_dir: Union[Path, str], lifecycle_state: Optional[str] = None):
        state_str = f" for lifecycle state '{lifecycle_state}'" if lifecycle_state else ""
        msg = f"Mandatory artifact '{artifact_name}' is missing in project '{Path(project_dir).name}'{state_str}."
        super().__init__(msg, code="REQUIRED_ARTIFACT_MISSING", details={
            "artifact_name": artifact_name,
            "project_dir": str(project_dir),
            "lifecycle_state": lifecycle_state,
            "failure_code": FailureCode.ARTIFACT_MISSING.value,
        })
        self.artifact_name = artifact_name
        self.project_dir = Path(project_dir)
        self.state_name = lifecycle_state


class ArtifactCorruptedError(AssetResolutionError):
    """Raised when media_map.json is malformed JSON, not an object, or contains invalid entries (LED-033)."""
    def __init__(self, artifact_name: str, reason: str, project_dir: Optional[Union[Path, str]] = None):
        proj_str = f" in project '{Path(project_dir).name}'" if project_dir else ""
        msg = f"Artifact '{artifact_name}'{proj_str} is corrupted: {reason}"
        super().__init__(msg, code="ARTIFACT_CORRUPTED", details={
            "artifact_name": artifact_name,
            "reason": reason,
            "project_dir": str(project_dir) if project_dir else None,
            "failure_code": FailureCode.ARTIFACT_CORRUPTED.value,
        })
        self.artifact_name = artifact_name
        self.reason = reason
        self.project_dir = Path(project_dir) if project_dir else None


class IncompatibleAssetKindError(AssetResolutionError):
    """Raised when an asset reference points to an asset with an unexpected kind."""
    def __init__(self, asset_id: str, found_kind: str, expected_kinds: List[str], field_path: Optional[str] = None):
        msg = f"Asset '{asset_id}' has kind '{found_kind}', expected one of {expected_kinds} (field: '{field_path or 'unknown'}')"
        super().__init__(msg, code="INCOMPATIBLE_ASSET_KIND", details={
            "asset_id": asset_id,
            "found_kind": found_kind,
            "expected_kinds": expected_kinds,
            "field_path": field_path,
        })
        self.asset_id = asset_id
        self.found_kind = found_kind
        self.expected_kinds = expected_kinds
        self.field_path = field_path


# ─── 2. Canonical AssetRef Vocabulary ─────────────────────────────────────────

class AssetRefKind(str, Enum):
    ASSET = "asset"
    URL = "url"


@dataclass(frozen=True)
class ParsedAssetRef:
    ref_kind: AssetRefKind
    asset_id: Optional[str]
    url: Optional[str]
    raw_ref: Any

    @property
    def is_logical(self) -> bool:
        return self.ref_kind == AssetRefKind.ASSET

    @property
    def is_url(self) -> bool:
        return self.ref_kind == AssetRefKind.URL


def parse_asset_ref(
    val: Any,
    field_path: str = "",
    scene_id: Optional[str] = None
) -> ParsedAssetRef:
    """
    Authoritative parser for Asset References.
    Strictly distinguishes logical references from literal external resources.
    Disallows guessing URLs or filesystem paths from bare strings.
    """
    if val is None:
        raise MalformedAssetRefError(val, "Reference cannot be null", field_path, scene_id)

    # 1. String format: Must be logical asset ID
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            raise MalformedAssetRefError(val, "Asset reference string cannot be empty", field_path, scene_id)

        # Ban guessing URLs from strings
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            raise MalformedAssetRefError(
                val,
                "String reference looks like a URL. External URLs must use tagged format: {'kind': 'url', 'url': '...'}",
                field_path,
                scene_id
            )

        # Ban guessing filesystem paths from strings
        if cleaned.startswith("/") or cleaned.startswith("./") or cleaned.startswith("../") or "\\" in cleaned:
            raise MalformedAssetRefError(
                val,
                "String reference looks like a filesystem path. Logical references must be asset IDs, not local paths",
                field_path,
                scene_id
            )

        if not ASSET_ID_REGEX.match(cleaned):
            raise MalformedAssetRefError(
                val,
                f"Asset ID '{cleaned}' contains invalid characters (must match ^[a-zA-Z0-9_\\-\\.]+$)",
                field_path,
                scene_id
            )

        return ParsedAssetRef(ref_kind=AssetRefKind.ASSET, asset_id=cleaned, url=None, raw_ref=val)

    # 2. Tagged Dict format
    if isinstance(val, dict):
        kind = val.get("kind")
        if not kind:
            raise MalformedAssetRefError(val, "Missing required 'kind' property in tagged asset reference", field_path, scene_id)

        if kind == AssetRefKind.ASSET.value:
            aid = val.get("asset_id")
            if not isinstance(aid, str) or not aid.strip():
                raise MalformedAssetRefError(val, "Tagged asset reference must contain non-empty string 'asset_id'", field_path, scene_id)
            aid_clean = aid.strip()
            if not ASSET_ID_REGEX.match(aid_clean):
                raise MalformedAssetRefError(val, f"asset_id '{aid_clean}' contains invalid characters", field_path, scene_id)
            return ParsedAssetRef(ref_kind=AssetRefKind.ASSET, asset_id=aid_clean, url=None, raw_ref=val)

        elif kind == AssetRefKind.URL.value:
            url_val = val.get("url")
            if not isinstance(url_val, str) or not url_val.strip():
                raise MalformedAssetRefError(val, "Tagged url reference must contain non-empty string 'url'", field_path, scene_id)
            url_clean = url_val.strip()
            parsed = urlparse(url_clean)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise MalformedAssetRefError(val, f"Invalid external URL '{url_clean}' (must be valid http/https URL)", field_path, scene_id)
            return ParsedAssetRef(ref_kind=AssetRefKind.URL, asset_id=None, url=url_clean, raw_ref=val)

        else:
            raise MalformedAssetRefError(val, f"Unsupported asset reference kind: '{kind}'. Expected 'asset' or 'url'", field_path, scene_id)

    raise MalformedAssetRefError(val, f"Unsupported asset reference type: {type(val).__name__}", field_path, scene_id)


# ─── 3. Declarative Media Reference Surfaces (ASSET-005) ─────────────────────

@dataclass(frozen=True)
class MediaFieldDescriptor:
    slot: str
    expected_kinds: List[str]
    is_array: bool


MEDIA_FIELD_DESCRIPTORS: List[MediaFieldDescriptor] = [
    # AudioPlan tracks
    MediaFieldDescriptor(slot="audio.voiceover", expected_kinds=["vo", "audio"], is_array=False),
    MediaFieldDescriptor(slot="audio.music", expected_kinds=["music", "audio"], is_array=False),
    MediaFieldDescriptor(slot="audio.global_sfx", expected_kinds=["sfx", "audio"], is_array=True),
    # Scene-level surfaces
    MediaFieldDescriptor(slot="scenes.media_refs", expected_kinds=["image", "video"], is_array=True),
    MediaFieldDescriptor(slot="scenes.sfx_ref", expected_kinds=["sfx", "audio"], is_array=False),
    MediaFieldDescriptor(slot="scenes.captions_ref", expected_kinds=["json", "other"], is_array=False),
    MediaFieldDescriptor(slot="scenes.surface.logoSrc", expected_kinds=["logo", "image"], is_array=False),
    # Content-level surfaces
    MediaFieldDescriptor(slot="scenes.content.images", expected_kinds=["image"], is_array=True),
    MediaFieldDescriptor(slot="scenes.content.screen", expected_kinds=["image", "video"], is_array=False),
    MediaFieldDescriptor(slot="scenes.content.icons", expected_kinds=["icon", "image"], is_array=True),
    MediaFieldDescriptor(slot="scenes.content.audioRef", expected_kinds=["audio", "vo", "music", "sfx"], is_array=False),
    MediaFieldDescriptor(slot="scenes.content.path", expected_kinds=["image", "video", "other"], is_array=False),
]


@dataclass
class AssetReferenceOccurrence:
    raw_ref: Any
    parsed: ParsedAssetRef
    field_path: str
    slot: str
    scene_id: Optional[str] = None
    expected_kinds: Optional[List[str]] = None

    @property
    def asset_id(self) -> Optional[str]:
        return self.parsed.asset_id

    @property
    def is_logical(self) -> bool:
        return self.parsed.is_logical

    @property
    def is_url(self) -> bool:
        return self.parsed.is_url


def collect_asset_references(blueprint: Union[Dict[str, Any], Any]) -> List[AssetReferenceOccurrence]:
    """
    Single Authority for discovering ALL asset reference occurrences across a Blueprint.
    Covers AudioPlan, scenes, surfaces, and content fields declaratively.
    """
    bp = blueprint.to_dict() if hasattr(blueprint, "to_dict") else (
        blueprint.model_dump() if hasattr(blueprint, "model_dump") else blueprint
    )
    if not isinstance(bp, dict):
        return []

    occurrences: List[AssetReferenceOccurrence] = []

    # 1. AudioPlan tracks
    audio = bp.get("audio")
    if isinstance(audio, dict):
        # Voiceover
        vo = audio.get("voiceover")
        if isinstance(vo, dict) and "asset_ref" in vo and vo["asset_ref"]:
            p = parse_asset_ref(vo["asset_ref"], field_path="audio.voiceover.asset_ref")
            occurrences.append(AssetReferenceOccurrence(
                raw_ref=vo["asset_ref"],
                parsed=p,
                field_path="audio.voiceover.asset_ref",
                slot="audio.voiceover",
                expected_kinds=["vo", "audio"],
            ))

        # Music
        bgm = audio.get("music")
        if isinstance(bgm, dict) and "asset_ref" in bgm and bgm["asset_ref"]:
            p = parse_asset_ref(bgm["asset_ref"], field_path="audio.music.asset_ref")
            occurrences.append(AssetReferenceOccurrence(
                raw_ref=bgm["asset_ref"],
                parsed=p,
                field_path="audio.music.asset_ref",
                slot="audio.music",
                expected_kinds=["music", "audio"],
            ))

        # Global SFX
        sfx_list = audio.get("global_sfx", [])
        if isinstance(sfx_list, list):
            for idx, sfx in enumerate(sfx_list):
                if isinstance(sfx, dict) and "asset_ref" in sfx and sfx["asset_ref"]:
                    path_str = f"audio.global_sfx[{idx}].asset_ref"
                    p = parse_asset_ref(sfx["asset_ref"], field_path=path_str)
                    occurrences.append(AssetReferenceOccurrence(
                        raw_ref=sfx["asset_ref"],
                        parsed=p,
                        field_path=path_str,
                        slot="audio.global_sfx",
                        expected_kinds=["sfx", "audio"],
                    ))

    # 2. Scenes
    scenes = bp.get("scenes", [])
    if isinstance(scenes, list):
        for s_idx, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                continue
            scene_id = scene.get("scene_id", f"scene_{s_idx}")

            # media_refs
            media_refs = scene.get("media_refs")
            if isinstance(media_refs, list):
                for m_idx, m_ref in enumerate(media_refs):
                    if m_ref is not None:
                        path_str = f"scenes[{s_idx}].media_refs[{m_idx}]"
                        p = parse_asset_ref(m_ref, field_path=path_str, scene_id=scene_id)
                        occurrences.append(AssetReferenceOccurrence(
                            raw_ref=m_ref,
                            parsed=p,
                            field_path=path_str,
                            slot="scenes.media_refs",
                            scene_id=scene_id,
                            expected_kinds=["image", "video"],
                        ))

            # sfx_ref
            sfx_ref = scene.get("sfx_ref")
            if sfx_ref:
                path_str = f"scenes[{s_idx}].sfx_ref"
                p = parse_asset_ref(sfx_ref, field_path=path_str, scene_id=scene_id)
                occurrences.append(AssetReferenceOccurrence(
                    raw_ref=sfx_ref,
                    parsed=p,
                    field_path=path_str,
                    slot="scenes.sfx_ref",
                    scene_id=scene_id,
                    expected_kinds=["sfx", "audio"],
                ))

            # captions_ref
            captions_ref = scene.get("captions_ref")
            if captions_ref:
                path_str = f"scenes[{s_idx}].captions_ref"
                p = parse_asset_ref(captions_ref, field_path=path_str, scene_id=scene_id)
                occurrences.append(AssetReferenceOccurrence(
                    raw_ref=captions_ref,
                    parsed=p,
                    field_path=path_str,
                    slot="scenes.captions_ref",
                    scene_id=scene_id,
                    expected_kinds=["json", "other"],
                ))

            # surface.logoSrc
            surface = scene.get("surface")
            if isinstance(surface, dict):
                logo_src = surface.get("logoSrc")
                if logo_src:
                    path_str = f"scenes[{s_idx}].surface.logoSrc"
                    p = parse_asset_ref(logo_src, field_path=path_str, scene_id=scene_id)
                    occurrences.append(AssetReferenceOccurrence(
                        raw_ref=logo_src,
                        parsed=p,
                        field_path=path_str,
                        slot="scenes.surface.logoSrc",
                        scene_id=scene_id,
                        expected_kinds=["logo", "image"],
                    ))

            # content
            content = scene.get("content")
            if isinstance(content, dict):
                # content.images
                c_images = content.get("images")
                if isinstance(c_images, list):
                    for img_idx, img_ref in enumerate(c_images):
                        if img_ref is not None:
                            path_str = f"scenes[{s_idx}].content.images[{img_idx}]"
                            p = parse_asset_ref(img_ref, field_path=path_str, scene_id=scene_id)
                            occurrences.append(AssetReferenceOccurrence(
                                raw_ref=img_ref,
                                parsed=p,
                                field_path=path_str,
                                slot="scenes.content.images",
                                scene_id=scene_id,
                                expected_kinds=["image"],
                            ))

                # content.screen
                c_screen = content.get("screen")
                if c_screen:
                    path_str = f"scenes[{s_idx}].content.screen"
                    p = parse_asset_ref(c_screen, field_path=path_str, scene_id=scene_id)
                    occurrences.append(AssetReferenceOccurrence(
                        raw_ref=c_screen,
                        parsed=p,
                        field_path=path_str,
                        slot="scenes.content.screen",
                        scene_id=scene_id,
                        expected_kinds=["image", "video"],
                    ))

                # content.icons
                c_icons = content.get("icons")
                if isinstance(c_icons, list):
                    for icon_idx, icon_ref in enumerate(c_icons):
                        if icon_ref is not None:
                            path_str = f"scenes[{s_idx}].content.icons[{icon_idx}]"
                            p = parse_asset_ref(icon_ref, field_path=path_str, scene_id=scene_id)
                            occurrences.append(AssetReferenceOccurrence(
                                raw_ref=icon_ref,
                                parsed=p,
                                field_path=path_str,
                                slot="scenes.content.icons",
                                scene_id=scene_id,
                                expected_kinds=["icon", "image"],
                            ))

                # content.audioRef
                c_audio = content.get("audioRef")
                if c_audio:
                    path_str = f"scenes[{s_idx}].content.audioRef"
                    p = parse_asset_ref(c_audio, field_path=path_str, scene_id=scene_id)
                    occurrences.append(AssetReferenceOccurrence(
                        raw_ref=c_audio,
                        parsed=p,
                        field_path=path_str,
                        slot="scenes.content.audioRef",
                        scene_id=scene_id,
                        expected_kinds=["audio", "vo", "music", "sfx"],
                    ))

                # content.path (only if non-empty string that parses as asset ref)
                c_path = content.get("path")
                if c_path and isinstance(c_path, str) and not c_path.startswith("M") and not c_path.startswith("m"):
                    # Check if it looks like an asset reference rather than an SVG path data string
                    if ASSET_ID_REGEX.match(c_path):
                        path_str = f"scenes[{s_idx}].content.path"
                        p = parse_asset_ref(c_path, field_path=path_str, scene_id=scene_id)
                        occurrences.append(AssetReferenceOccurrence(
                            raw_ref=c_path,
                            parsed=p,
                            field_path=path_str,
                            slot="scenes.content.path",
                            scene_id=scene_id,
                            expected_kinds=["image", "video", "other"],
                        ))

    return occurrences


# ─── 4. Fail-Closed Resolver Authority (ASSET-012) ───────────────────────────

def resolve_asset_reference(
    ref: Any,
    media_map: Dict[str, str],
    field_path: str = "",
    scene_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    """
    Fail-closed resolver for a single AssetRef.
    - If literal URL: returns the URL string.
    - If logical asset ID: resolves strictly against media_map.
    - If missing from media_map: raises UnknownAssetReferenceError. NEVER returns raw string!
    """
    parsed = parse_asset_ref(ref, field_path=field_path, scene_id=scene_id)

    if parsed.is_url:
        return parsed.url  # type: ignore

    aid = parsed.asset_id
    assert aid is not None

    if aid in media_map:
        return media_map[aid]

    raise UnknownAssetReferenceError(
        asset_id=aid,
        field_path=field_path,
        scene_id=scene_id,
        project_id=project_id,
    )


def validate_asset_refs_against_media_map(
    blueprint: Union[Dict[str, Any], Any],
    media_map: Dict[str, str],
    project_id: Optional[str] = None,
) -> List[str]:
    """
    Validates all logical asset references in a blueprint against media_map.
    Returns a list of error messages (empty if all valid).
    """
    errors: List[str] = []
    occurrences = collect_asset_references(blueprint)
    for occ in occurrences:
        if occ.is_logical:
            aid = occ.asset_id
            if aid not in media_map:
                loc = f"scene='{occ.scene_id}' field='{occ.field_path}'" if occ.scene_id else f"field='{occ.field_path}'"
                errors.append(f"UNKNOWN_ASSET_REFERENCE: Logical asset '{aid}' not found in media_map ({loc})")
    return errors


# ─── 5. Mandatory Media Map Loader & Validator (LED-033) ─────────────────────

def load_required_media_map(
    project_dir_or_id: Union[Path, str],
    state: Optional[Union[ProjectState, LifecycleState, str]] = None,
    verify_files_on_disk: bool = True,
    workspace_root: Optional[Union[Path, str]] = None,
) -> Dict[str, str]:
    """
    Authoritative canonical loader for media_map.json (LED-033).
    Guarantees:
    - Fails hard with RequiredArtifactMissingError if missing in mandatory state according to S06 RequiredEvidencePolicy.
    - Validates JSON parse and object structure.
    - Validates key/value contracts (no path traversal, valid IDs).
    - Optionally verifies that referenced generation files actually exist on disk.
    - Disallows empty dictionary defaults in post-materialization states.
    """
    ws = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
    
    p = Path(project_dir_or_id)
    if not p.is_dir() and not p.exists() and not str(p).startswith("projects/"):
        cand = ws / "projects" / str(project_dir_or_id)
        if cand.exists():
            p = cand
    pdir = p.resolve()
    project_id = pdir.name

    # Determine project lifecycle state
    current_state_enum: Optional[LifecycleState] = None
    if isinstance(state, LifecycleState):
        current_state_enum = state
    elif isinstance(state, str):
        try:
            current_state_enum = LifecycleState(state)
        except ValueError:
            current_state_enum = None
    elif isinstance(state, ProjectState):
        current_state_enum = LifecycleState(state.lifecycle_state)
    else:
        # Load from state file on disk if available
        state_file = pdir / ".pipeline_state.json"
        if state_file.exists():
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8"))
                current_state_enum = LifecycleState(state_data.get("lifecycle_state"))
            except Exception:
                current_state_enum = None

    # Derive mandatory requirement from the single authoritative S06 policy (RequiredEvidencePolicy)
    from scripts.core.evidence_matrix import RequiredEvidencePolicy
    if current_state_enum is not None:
        is_mandatory = RequiredEvidencePolicy.is_artifact_required(current_state_enum, "media_map")
    else:
        is_mandatory = True

    map_path = pdir / "media_map.json"

    # 1. File existence check
    if not map_path.exists():
        if is_mandatory:
            raise RequiredArtifactMissingError(
                artifact_name="media_map.json",
                project_dir=pdir,
                lifecycle_state=current_state_enum.value if current_state_enum else "UNKNOWN",
            )
        # Not yet materialized (e.g. DRAFT or BLUEPRINT_READY)
        return {}

    # 2. JSON parsing
    try:
        raw_text = map_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ArtifactCorruptedError("media_map.json", f"Malformed JSON: {e}", pdir)
    except Exception as e:
        raise ArtifactCorruptedError("media_map.json", f"Read error: {e}", pdir)

    # 3. Object type validation
    if not isinstance(data, dict):
        raise ArtifactCorruptedError(
            "media_map.json",
            f"media_map must be a JSON object, got {type(data).__name__}",
            pdir
        )

    # 4. Entry validation
    public_root = (ws / "remotion-app" / "public").resolve()
    validated_map: Dict[str, str] = {}

    for key, val in data.items():
        if not isinstance(key, str) or not key.strip() or not ASSET_ID_REGEX.match(key):
            raise ArtifactCorruptedError(
                "media_map.json",
                f"Invalid asset key '{key}' in media_map: must match ^[a-zA-Z0-9_\\-\\.]+$",
                pdir
            )

        if not isinstance(val, str) or not val.strip():
            raise ArtifactCorruptedError(
                "media_map.json",
                f"Value for asset '{key}' must be a non-empty string path, got {type(val).__name__}",
                pdir
            )

        val_clean = val.strip()

        # Reject path traversal and absolute paths in relative URLs
        if val_clean.startswith("/") or ".." in val_clean or "\\" in val_clean:
            raise ArtifactCorruptedError(
                "media_map.json",
                f"Path traversal detected in media_map path for asset '{key}': '{val_clean}'",
                pdir
            )

        # Invariant: Generation path format
        # Expected: projects/<project_id>/generations/<gen_id>/<file>
        if not val_clean.startswith(f"projects/{project_id}/"):
            # Allow projects/<project_id>/...
            if not val_clean.startswith("projects/"):
                raise ArtifactCorruptedError(
                    "media_map.json",
                    f"Asset '{key}' path '{val_clean}' must be confined within projects/{project_id}/",
                    pdir
                )

        # 5. Disk existence verification
        if verify_files_on_disk and public_root.exists():
            target_file = (public_root / val_clean).resolve()
            # Verify containment under public_root
            try:
                target_file.relative_to(public_root)
            except ValueError:
                raise ArtifactCorruptedError(
                    "media_map.json",
                    f"Asset '{key}' path '{val_clean}' escapes public directory root",
                    pdir
                )

            if not target_file.exists():
                raise ArtifactCorruptedError(
                    "media_map.json",
                    f"Asset '{key}' references missing generation file on disk: '{val_clean}'",
                    pdir
                )

        validated_map[key] = val_clean

    return validated_map
