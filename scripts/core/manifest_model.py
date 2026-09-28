"""
Manifest v2 Canonical Data Models (S11).
Authoritative representation for asset manifests across clean-video-workspace.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator

from scripts.core.manifest_errors import ManifestValidationError


class AssetKind(str, Enum):
    """
    Canonical vocabulary for media and resource asset kinds.
    Prevents fragmentation across manifests, blueprints, and engine bridges.
    """
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SFX = "sfx"
    MUSIC = "music"
    VO = "vo"
    LOGO = "logo"
    ICON = "icon"
    FONT = "font"
    JSON = "json"
    OTHER = "other"

    @classmethod
    def from_string(cls, val: str, asset_id: Optional[str] = None) -> AssetKind:
        if not isinstance(val, str):
            raise ManifestValidationError(
                code="INVALID_ASSET_KIND",
                message=f"Asset kind must be a string, got {type(val).__name__}",
                asset_id=asset_id,
            )
        val_clean = val.strip().lower()
        # Direct enum value match
        for member in cls:
            if member.value == val_clean:
                return member

        # Deterministic legacy aliases
        alias_map = {
            "voiceover": cls.VO,
            "voice": cls.VO,
            "sound_effect": cls.SFX,
            "bgm": cls.MUSIC,
            "background_music": cls.MUSIC,
            "graphic": cls.IMAGE,
            "picture": cls.IMAGE,
        }
        if val_clean in alias_map:
            return alias_map[val_clean]

        raise ManifestValidationError(
            code="INVALID_ASSET_KIND",
            message=f"Unsupported asset kind '{val}'. Allowed values: {[m.value for m in cls]}",
            asset_id=asset_id,
        )


class Provenance(str, Enum):
    """
    Canonical vocabulary for asset acquisition and creation origin.
    Strictly distinct from operational status/location.
    """
    USER_UPLOAD = "user_upload"
    MCP_FETCH = "mcp_fetch"
    GENERATED = "generated"
    CACHE_REUSE = "cache_reuse"

    @classmethod
    def from_string(cls, val: str, asset_id: Optional[str] = None) -> Provenance:
        if not isinstance(val, str):
            raise ManifestValidationError(
                code="INVALID_PROVENANCE",
                message=f"Provenance must be a string, got {type(val).__name__}",
                asset_id=asset_id,
            )
        val_clean = val.strip().lower()
        for member in cls:
            if member.value == val_clean:
                return member

        # Deterministic legacy aliases
        alias_map = {
            "user": cls.USER_UPLOAD,
            "upload": cls.USER_UPLOAD,
            "pixabay": cls.MCP_FETCH,
            "pexels": cls.MCP_FETCH,
            "icons": cls.MCP_FETCH,
            "mcp": cls.MCP_FETCH,
            "cache": cls.CACHE_REUSE,
            "cached": cls.CACHE_REUSE,
        }
        if val_clean in alias_map:
            return alias_map[val_clean]

        raise ManifestValidationError(
            code="INVALID_PROVENANCE",
            message=f"Unsupported provenance '{val}'. Allowed values: {[m.value for m in cls]}",
            asset_id=asset_id,
        )


class AssetStatus(str, Enum):
    """
    Canonical vocabulary for asset lifecycle and storage states.
    Strictly distinct from acquisition provenance.
    """
    INCOMING = "incoming"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

    @classmethod
    def from_string(cls, val: str, asset_id: Optional[str] = None) -> AssetStatus:
        if not isinstance(val, str):
            raise ManifestValidationError(
                code="INVALID_STATUS",
                message=f"Status must be a string, got {type(val).__name__}",
                asset_id=asset_id,
            )
        val_clean = val.strip().lower()
        for member in cls:
            if member.value == val_clean:
                return member

        raise ManifestValidationError(
            code="INVALID_STATUS",
            message=f"Unsupported asset status '{val}'. Allowed values: {[m.value for m in cls]}",
            asset_id=asset_id,
        )


class AssetV2(BaseModel):
    """
    Canonical individual asset representation in Manifest v2.
    """
    model_config = ConfigDict(extra='ignore', use_enum_values=True)

    asset_id: str
    kind: AssetKind
    provenance: Provenance
    status: AssetStatus
    source_path: Optional[str] = None
    processed_path: Optional[str] = None
    content_hash: Optional[str] = None
    processing_spec_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id_format(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ManifestValidationError(code="INVALID_ASSET_ID", message="asset_id cannot be empty")
        v = v.strip()
        # Accept ast_xxx or alphanumeric with underscores/hyphens
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", v):
            raise ManifestValidationError(
                code="INVALID_ASSET_ID",
                message=f"asset_id '{v}' contains illegal characters",
                asset_id=v
            )
        return v


class ManifestV2(BaseModel):
    """
    Authoritative Manifest v2 container.
    """
    model_config = ConfigDict(extra='ignore')

    manifest_version: str = "2.0.0"
    project_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None
    assets: List[AssetV2] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("manifest_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v not in ("2.0.0", "2.0"):
            raise ManifestValidationError(
                code="UNSUPPORTED_VERSION",
                message=f"Manifest version '{v}' is unsupported. Only '2.0.0' or '2.0' are accepted.",
                manifest_version=v
            )
        return v

    @field_validator("project_id")
    @classmethod
    def validate_project_id_format(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ManifestValidationError(code="INVALID_PROJECT_ID", message="project_id cannot be empty")
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ManifestValidationError(
                code="INVALID_PROJECT_ID",
                message=f"project_id '{v}' contains illegal characters"
            )
        return v

    def get_asset(self, asset_id: str) -> Optional[AssetV2]:
        for a in self.assets:
            if a.asset_id == asset_id:
                return a
        return None

    def asset_ids(self) -> List[str]:
        return [a.asset_id for a in self.assets]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
