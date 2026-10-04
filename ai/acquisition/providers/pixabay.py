"""
ai/acquisition/providers/pixabay.py
===================================
Adapter for Pixabay Stock Images, Videos, and Audio (S28-M05).

Invariants:
- Requires PIXABAY_API_KEY for official REST API (images, videos).
- Captures Pixabay Content License (free commercial use, no attribution required).
- Accurately captures views/likes/downloads in provider metrics.
- Audio scraping gracefully fails closed with structured ProviderUnavailableError if unconfigured or blocked.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional, Set
import httpx

from ai.acquisition.contracts import (
    AcquisitionDescriptor,
    CommercialUseStatus,
    DownloadVariant,
    LicenseClassification,
    StockCandidate,
    StockMediaType,
    StockSearchQuery,
)
from ai.acquisition.errors import (
    InvalidProviderResponseError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from ai.acquisition.providers.base import StockSourceAdapter


class PixabayAdapter(StockSourceAdapter):
    """Modernized provider adapter for Pixabay images, videos, and audio."""

    IMAGE_API_URL = "https://pixabay.com/api/"
    VIDEO_API_URL = "https://pixabay.com/api/videos/"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "pixabay"

    @property
    def supported_media_types(self) -> Set[StockMediaType]:
        # Pixabay official REST API supports Photos and Videos.
        # Audio scraping is classified as BROKEN_LEGACY_SCRAPER (COMPATIBILITY_ONLY).
        return {StockMediaType.IMAGE, StockMediaType.VIDEO}

    def is_available(self) -> bool:
        return bool(self._api_key or os.environ.get("PIXABAY_API_KEY"))

    def _get_api_key(self) -> str:
        key = self._api_key or os.environ.get("PIXABAY_API_KEY")
        if not key:
            raise ProviderAuthError(self.name, "PIXABAY_API_KEY environment variable is not configured.")
        return key

    async def search(self, query: StockSearchQuery) -> List[StockCandidate]:
        if query.media_type in (StockMediaType.AUDIO, StockMediaType.SOUND_EFFECT):
            # Pixabay audio has no public official REST endpoint.
            # Legacy scraper was audited BROKEN in M01 due to missing Playwright Chromium binaries and Cloudflare 403.
            # Platform capability SEARCH_STOCK_AUDIO is canonically fulfilled by FreesoundAdapter.
            raise ProviderUnavailableError(
                self.name,
                "Pixabay audio scraping is classified as BROKEN_LEGACY_SCRAPER (COMPATIBILITY_ONLY). "
                "Official Pixabay REST API supports images and videos only. Use Freesound for sound acquisition."
            )

        api_key = self._get_api_key()

        params: Dict[str, Any] = {
            "key": api_key,
            "q": query.query,
            "page": query.page,
            "per_page": query.per_page,
        }

        if query.media_type == StockMediaType.VIDEO:
            target_url = self.VIDEO_API_URL
        else:
            target_url = self.IMAGE_API_URL
            params["image_type"] = "photo"
            if query.orientation:
                orient = query.orientation.lower()
                params["orientation"] = "vertical" if orient == "portrait" else "horizontal" if orient == "landscape" else "all"

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(target_url, params=params)
            except httpx.TimeoutException as e:
                raise ProviderUnavailableError(self.name, f"Request timed out: {e}")
            except httpx.RequestError as e:
                raise ProviderUnavailableError(self.name, f"Network error: {e}")

            if response.status_code == 400 and "Invalid key" in response.text:
                raise ProviderAuthError(self.name, "PIXABAY_API_KEY rejected by provider.")
            elif response.status_code == 429:
                raise ProviderRateLimitError(self.name)
            elif response.status_code >= 500:
                raise ProviderUnavailableError(self.name, f"Server error HTTP {response.status_code}")
            elif response.status_code != 200:
                raise InvalidProviderResponseError(self.name, f"HTTP status {response.status_code}: {response.text[:200]}")

            try:
                data = response.json()
            except Exception as e:
                raise InvalidProviderResponseError(self.name, f"JSON decode error: {e}")

        now_iso = datetime.now(timezone.utc).isoformat()
        hits = data.get("hits", [])

        if query.media_type == StockMediaType.VIDEO:
            return self._normalize_videos(hits, query.query, now_iso)
        else:
            return self._normalize_images(hits, query.query, now_iso)

    def _normalize_images(self, hits: List[Dict[str, Any]], query: str, timestamp: str) -> List[StockCandidate]:
        candidates: List[StockCandidate] = []
        for h in hits:
            hit_id = str(h.get("id"))
            width = h.get("imageWidth")
            height = h.get("imageHeight")

            variants: List[DownloadVariant] = []
            if h.get("largeImageURL"):
                variants.append(DownloadVariant(
                    variant_id="large",
                    url=h["largeImageURL"],
                    width=width,
                    height=height,
                    quality="large",
                    format="jpg",
                    file_size_bytes=h.get("imageSize"),
                ))
            if h.get("webformatURL"):
                variants.append(DownloadVariant(
                    variant_id="webformat",
                    url=h["webformatURL"],
                    width=h.get("webformatWidth"),
                    height=h.get("webformatHeight"),
                    quality="webformat",
                    format="jpg",
                ))

            selected_var = variants[0] if variants else None
            orient = "portrait" if (width and height and height > width) else "landscape" if (width and height and width > height) else "square"

            tags = [t.strip().lower() for t in (h.get("tags") or "").split(",") if t.strip()]

            candidates.append(StockCandidate(
                candidate_id=f"pixabay:{hit_id}",
                source="pixabay",
                source_asset_id=hit_id,
                media_type=StockMediaType.IMAGE,
                title=f"Pixabay Photo {hit_id} ({', '.join(tags[:3]) if tags else 'photo'})",
                preview_url=h.get("previewURL"),
                download_variants=variants,
                selected_variant=selected_var,
                width=width,
                height=height,
                orientation=orient,
                aspect_ratio=round(width / height, 2) if (width and height) else None,
                mime_type="image/jpeg",
                tags=tags,
                license=LicenseClassification.PIXABAY_LICENSE,
                license_name="Pixabay Content License",
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                creator=h.get("user"),
                source_reference=h.get("pageURL"),
                query=query,
                retrieved_at=timestamp,
                provenance_evidence={
                    "provider": "pixabay",
                    "provider_id": hit_id,
                    "author": h.get("user"),
                    "license": "Pixabay Content License",
                    "commercial_use": "ALLOWED",
                    "attribution_required": False,
                },
                provider_score=float(h.get("likes", 0)),
                provider_metadata={
                    "views": h.get("views"),
                    "downloads": h.get("downloads"),
                    "likes": h.get("likes"),
                },
            ))
        return candidates

    def _normalize_videos(self, hits: List[Dict[str, Any]], query: str, timestamp: str) -> List[StockCandidate]:
        candidates: List[StockCandidate] = []
        for h in hits:
            hit_id = str(h.get("id"))
            duration = float(h.get("duration", 0.0))
            raw_videos = h.get("videos", {})

            variants: List[DownloadVariant] = []
            for v_tier in ("large", "medium", "small", "tiny"):
                v_data = raw_videos.get(v_tier)
                if isinstance(v_data, dict) and v_data.get("url"):
                    variants.append(DownloadVariant(
                        variant_id=v_tier,
                        url=v_data["url"],
                        width=v_data.get("width"),
                        height=v_data.get("height"),
                        quality=v_tier,
                        format="mp4",
                        file_size_bytes=v_data.get("size"),
                    ))

            selected_var = next((v for v in variants if v.variant_id == "large"), None)
            if not selected_var and variants:
                selected_var = variants[0]

            width = selected_var.width if selected_var else None
            height = selected_var.height if selected_var else None
            orient = "portrait" if (width and height and height > width) else "landscape" if (width and height and width > height) else "square"

            tags = [t.strip().lower() for t in (h.get("tags") or "").split(",") if t.strip()]

            candidates.append(StockCandidate(
                candidate_id=f"pixabay:{hit_id}",
                source="pixabay",
                source_asset_id=hit_id,
                media_type=StockMediaType.VIDEO,
                title=f"Pixabay Video {hit_id} ({', '.join(tags[:3]) if tags else 'clip'})",
                preview_url=h.get("picture_id"),
                download_variants=variants,
                selected_variant=selected_var,
                width=width,
                height=height,
                duration_seconds=duration,
                orientation=orient,
                aspect_ratio=round(width / height, 2) if (width and height) else None,
                mime_type="video/mp4",
                tags=tags,
                license=LicenseClassification.PIXABAY_LICENSE,
                license_name="Pixabay Content License",
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                creator=h.get("user"),
                source_reference=h.get("pageURL"),
                query=query,
                retrieved_at=timestamp,
                provenance_evidence={
                    "provider": "pixabay",
                    "provider_id": hit_id,
                    "author": h.get("user"),
                    "license": "Pixabay Content License",
                    "commercial_use": "ALLOWED",
                    "attribution_required": False,
                },
                provider_score=float(h.get("likes", 0)),
                provider_metadata={
                    "views": h.get("views"),
                    "downloads": h.get("downloads"),
                    "likes": h.get("likes"),
                },
            ))
        return candidates

    def resolve_acquisition(
        self,
        candidate: StockCandidate,
        requested_variant_id: Optional[str] = None,
    ) -> AcquisitionDescriptor:
        target_variant = None
        if requested_variant_id:
            target_variant = next((v for v in candidate.download_variants if v.variant_id == requested_variant_id), None)
        if not target_variant:
            target_variant = candidate.selected_variant or (candidate.download_variants[0] if candidate.download_variants else None)

        if not target_variant or not target_variant.url:
            raise InvalidProviderResponseError(self.name, f"No valid download URL available for candidate '{candidate.candidate_id}'.")

        return AcquisitionDescriptor(
            candidate_id=candidate.candidate_id,
            source=candidate.source,
            source_asset_id=candidate.source_asset_id,
            download_url=target_variant.url,
            media_type=candidate.media_type,
            variant_id=target_variant.variant_id,
            expected_mime_type=candidate.mime_type or ("video/mp4" if candidate.media_type == StockMediaType.VIDEO else "image/jpeg"),
            expected_format=".mp4" if candidate.media_type == StockMediaType.VIDEO else ".jpg",
            provenance=candidate.provenance_evidence,
        )
