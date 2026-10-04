"""
ai/acquisition/contracts.py
===========================
Canonical contracts for stock media search, normalization, and safe acquisition (S28-M05).

Invariants:
- Strictly provider-neutral core domain models (StockCandidate, StockSearchQuery).
- Explicit provenance and license classifications as first-class citizens.
- No fabricated assumptions: unproven licenses default to UNKNOWN or REQUIRES_REVIEW.
- High-fidelity variant descriptors separating preview, metadata, and acquisition links.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from ai.contracts.base import AIContractModel


class StockMediaType(str, Enum):
    """Supported stock media modalities."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SOUND_EFFECT = "sound_effect"
    ICON = "icon"


class LicenseClassification(str, Enum):
    """Categorized license frameworks for stock assets."""
    PEXELS_LICENSE = "PEXELS_LICENSE"
    PIXABAY_LICENSE = "PIXABAY_LICENSE"
    CC0 = "CC0"
    CC_BY = "CC_BY"
    CC_BY_SA = "CC_BY_SA"
    CC_BY_NC = "CC_BY_NC"
    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    OPEN_SOURCE_ICON = "OPEN_SOURCE_ICON"
    UNKNOWN = "UNKNOWN"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class CommercialUseStatus(str, Enum):
    """Authoritative commercial use eligibility status."""
    ALLOWED = "ALLOWED"
    PROHIBITED = "PROHIBITED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    UNKNOWN = "UNKNOWN"


class DownloadVariant(AIContractModel):
    """A downloadable variant or resolution option of a stock media item."""
    variant_id: str = Field(min_length=1, description="Identifier for this variant (e.g. 'hd', 'original', 'large')")
    url: str = Field(min_length=1, description="Direct remote download URL")
    width: Optional[int] = Field(default=None, ge=1, description="Horizontal pixel dimension if visual")
    height: Optional[int] = Field(default=None, ge=1, description="Vertical pixel dimension if visual")
    quality: Optional[str] = Field(default=None, description="Quality tag (e.g. 'uhd', 'hd', 'sd', 'thumb')")
    fps: Optional[float] = Field(default=None, gt=0.0, description="Frames per second if video")
    format: Optional[str] = Field(default=None, description="File format extension (e.g. 'mp4', 'jpg', 'svg', 'mp3')")
    file_size_bytes: Optional[int] = Field(default=None, ge=0, description="Payload size in bytes if known")
    bitrate_kbps: Optional[int] = Field(default=None, ge=0, description="Bitrate in kbps if audio/video")


class StockCandidate(AIContractModel):
    """Normalized candidate item returned from stock provider queries."""
    candidate_id: str = Field(min_length=1, description="Canonical composite ID (e.g. 'pexels:12345')")
    source: str = Field(min_length=1, description="Origin provider name (e.g. 'pexels', 'pixabay', 'freesound', 'iconify')")
    source_asset_id: str = Field(min_length=1, description="Provider's internal asset ID")
    media_type: StockMediaType = Field(description="Media modality")
    title: Optional[str] = Field(default=None, description="Title or descriptive caption")
    description: Optional[str] = Field(default=None, description="Detailed description or transcription")
    preview_url: Optional[str] = Field(default=None, description="Low-resolution preview or thumbnail URL")
    download_variants: List[DownloadVariant] = Field(default_factory=list, description="Available download variants")
    selected_variant: Optional[DownloadVariant] = Field(default=None, description="Recommended or active download variant")
    width: Optional[int] = Field(default=None, ge=1, description="Primary visual width in pixels")
    height: Optional[int] = Field(default=None, ge=1, description="Primary visual height in pixels")
    duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Playback duration in seconds")
    orientation: Optional[str] = Field(default=None, description="Orientation ('portrait', 'landscape', 'square')")
    aspect_ratio: Optional[float] = Field(default=None, gt=0.0, description="Aspect ratio (width / height)")
    mime_type: Optional[str] = Field(default=None, description="Expected MIME type")
    file_size_bytes: Optional[int] = Field(default=None, ge=0, description="Estimated or known file size in bytes")
    tags: List[str] = Field(default_factory=list, description="Provider or extracted keyword tags")
    license: LicenseClassification = Field(default=LicenseClassification.UNKNOWN, description="License category")
    license_name: Optional[str] = Field(default=None, description="Human-readable license name")
    commercial_use: CommercialUseStatus = Field(default=CommercialUseStatus.UNKNOWN, description="Commercial eligibility")
    attribution_required: bool = Field(default=False, description="Whether author attribution is mandatory")
    creator: Optional[str] = Field(default=None, description="Author or creator name")
    creator_url: Optional[str] = Field(default=None, description="Creator profile URL")
    source_reference: Optional[str] = Field(default=None, description="Origin webpage URL on provider site")
    query: Optional[str] = Field(default=None, description="Search query that surfaced this candidate")
    retrieved_at: str = Field(description="ISO 8601 UTC timestamp of retrieval")
    provenance_evidence: Dict[str, Any] = Field(default_factory=dict, description="Audit evidence dictionary")
    provider_score: Optional[float] = Field(default=None, description="Raw provider popularity/rank score")
    ranking_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Normalized multi-factor rank score")
    ranking_features: Dict[str, float] = Field(default_factory=dict, description="Feature breakdown of ranking score")
    provider_metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw non-normalized provider payload")


class StockSearchQuery(AIContractModel):
    """Structured query for cross-provider stock media retrieval."""
    query: str = Field(min_length=1, description="Keyword search prompt")
    media_type: StockMediaType = Field(description="Requested media modality")
    orientation: Optional[str] = Field(default=None, description="Desired orientation ('portrait', 'landscape', 'square')")
    min_width: Optional[int] = Field(default=None, ge=1, description="Minimum horizontal resolution")
    min_height: Optional[int] = Field(default=None, ge=1, description="Minimum vertical resolution")
    min_duration: Optional[float] = Field(default=None, ge=0.0, description="Minimum duration in seconds")
    max_duration: Optional[float] = Field(default=None, ge=0.0, description="Maximum duration in seconds")
    page: int = Field(default=1, ge=1, description="Pagination index (1-based)")
    per_page: int = Field(default=15, ge=1, le=100, description="Page size limit")
    commercial_use_required: bool = Field(default=True, description="Enforce commercial use authorization")
    require_no_attribution: bool = Field(default=False, description="Enforce no-attribution requirement")
    allowed_providers: Optional[List[str]] = Field(default=None, description="Explicit provider whitelist if restricted")


class AcquisitionDescriptor(AIContractModel):
    """Specification of an asset verified for bounded retrieval."""
    candidate_id: str = Field(min_length=1, description="Target candidate identifier")
    source: str = Field(min_length=1, description="Provider name")
    source_asset_id: str = Field(min_length=1, description="Provider internal ID")
    download_url: str = Field(min_length=1, description="Validated remote URL to stream from")
    media_type: StockMediaType = Field(description="Media modality")
    variant_id: Optional[str] = Field(default=None, description="Selected variant ID")
    expected_mime_type: Optional[str] = Field(default=None, description="Expected content type")
    expected_format: Optional[str] = Field(default=None, description="Expected extension (e.g. '.mp4')")
    max_bytes: int = Field(default=50 * 1024 * 1024, ge=1024, description="Maximum acceptable download bytes")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Provenance evidence dictionary")


class AcquiredAssetResult(AIContractModel):
    """Result of safe acquisition and AssetService canonical import."""
    project_id: str = Field(min_length=1, description="Target project identifier")
    asset_id: str = Field(min_length=1, description="Canonical Asset identifier created or reused")
    storage_key: str = Field(min_length=1, description="StorageService canonical storage key")
    content_hash: str = Field(min_length=1, description="Cryptographic SHA-256 payload digest")
    media_type: StockMediaType = Field(description="Media modality")
    file_size_bytes: int = Field(ge=0, description="Stored payload size in bytes")
    content_type: str = Field(min_length=1, description="Verified MIME type")
    provenance_evidence: Dict[str, Any] = Field(default_factory=dict, description="Attached canonical provenance data")
    is_reused_existing: bool = Field(default=False, description="True if matched existing project asset via content hash")
