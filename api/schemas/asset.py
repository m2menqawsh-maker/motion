"""
API Schemas for Asset Domain (S22 - LED-063).
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AssetResponse(BaseModel):
    """Canonical DTO for an individual media asset in Manifest v2."""
    asset_id: str
    kind: str
    provenance: str
    status: str
    source_path: Optional[str] = None
    processed_path: Optional[str] = None
    content_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetListResponse(BaseModel):
    """List response for project assets."""
    project_id: str
    assets: List[AssetResponse]
    total: int


class AssetUploadResponse(BaseModel):
    """Response returned upon uploading or importing an asset."""
    status: str = "success"
    asset: AssetResponse
    message: str = "Asset uploaded and registered in manifest"
