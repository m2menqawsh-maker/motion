"""
ai/acquisition/providers/pexels.py
==================================
Adapter for Pexels Stock Photos and Videos API (S28-M05).

Invariants:
- Requires PEXELS_API_KEY. Fails with structured ProviderAuthError if missing.
- Strictly bounds HTTP requests with 15s timeout.
- Normalizes photos and videos into canonical StockCandidate contracts.
- Accurately captures Pexels License (Commercial Use Allowed, No Attribution Required).
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


class PexelsAdapter(StockSourceAdapter):
    """Modernized provider adapter for Pexels photo and video APIs."""

    IMAGE_API_URL = "https://api.pexels.com/v1/search"
    VIDEO_API_URL = "https://api.pexels.com/videos/search"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "pexels"

    @property
    def supported_media_types(self) -> Set[StockMediaType]:
        return {StockMediaType.IMAGE, StockMediaType.VIDEO}

    def is_available(self) -> bool:
        return bool(self._api_key or os.environ.get("PEXELS_API_KEY"))

    def _get_api_key(self) -> str:
        key = self._api_key or os.environ.get("PEXELS_API_KEY")
        if not key:
            raise ProviderAuthError(self.name, "PEXELS_API_KEY environment variable is not configured.")
        return key

    async def search(self, query: StockSearchQuery) -> List[StockCandidate]:
        api_key = self._get_api_key()
        headers = {"Authorization": api_key, "User-Agent": "CleanVideoWorkspace/2.0"}

        params: Dict[str, Any] = {
            "query": query.query,
            "page": query.page,
            "per_page": query.per_page,
        }
        if query.orientation:
            params["orientation"] = query.orientation.lower()

        target_url = self.VIDEO_API_URL if query.media_type == StockMediaType.VIDEO else self.IMAGE_API_URL

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(target_url, headers=headers, params=params)
            except httpx.TimeoutException as e:
                raise ProviderUnavailableError(self.name, f"Request timed out: {e}")
            except httpx.RequestError as e:
                raise ProviderUnavailableError(self.name, f"Network error: {e}")

            if response.status_code == 401 or response.status_code == 403:
                raise ProviderAuthError(self.name, f"Invalid API credentials (HTTP {response.status_code}).")
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ProviderRateLimitError(self.name, retry_after_sec=float(retry_after) if retry_after else 60.0)
            elif response.status_code >= 500:
                raise ProviderUnavailableError(self.name, f"Server error HTTP {response.status_code}")
            elif response.status_code != 200:
                raise InvalidProviderResponseError(self.name, f"Unexpected HTTP status {response.status_code}: {response.text[:200]}")

            try:
                data = response.json()
            except Exception as e:
                raise InvalidProviderResponseError(self.name, f"JSON decode failed: {e}")

        now_iso = datetime.now(timezone.utc).isoformat()

        if query.media_type == StockMediaType.VIDEO:
            return self._normalize_videos(data.get("videos", []), query.query, now_iso)
        else:
            return self._normalize_photos(data.get("photos", []), query.query, now_iso)

    def _normalize_photos(self, raw_photos: List[Dict[str, Any]], query: str, timestamp: str) -> List[StockCandidate]:
        candidates: List[StockCandidate] = []
        for p in raw_photos:
            photo_id = str(p.get("id"))
            width = p.get("width")
            height = p.get("height")
            src = p.get("src", {})

            variants: List[DownloadVariant] = []
            for v_name in ("original", "large2x", "large", "medium", "small", "portrait", "landscape"):
                v_url = src.get(v_name)
                if v_url:
                    variants.append(DownloadVariant(
                        variant_id=v_name,
                        url=v_url,
                        quality=v_name,
                        format="jpg",
                    ))

            selected_var = next((v for v in variants if v.variant_id == "large2x"), None)
            if not selected_var and variants:
                selected_var = variants[0]

            orient = "portrait" if (width and height and height > width) else "landscape" if (width and height and width > height) else "square"

            candidates.append(StockCandidate(
                candidate_id=f"pexels:{photo_id}",
                source="pexels",
                source_asset_id=photo_id,
                media_type=StockMediaType.IMAGE,
                title=p.get("alt") or f"Pexels Photo {photo_id}",
                preview_url=src.get("medium") or src.get("tiny"),
                download_variants=variants,
                selected_variant=selected_var,
                width=width,
                height=height,
                orientation=orient,
                aspect_ratio=round(width / height, 2) if (width and height) else None,
                mime_type="image/jpeg",
                tags=[w.strip().lower() for w in (p.get("alt") or "").split() if len(w.strip()) > 3],
                license=LicenseClassification.PEXELS_LICENSE,
                license_name="Pexels Content License",
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                creator=p.get("photographer"),
                creator_url=p.get("photographer_url"),
                source_reference=p.get("url"),
                query=query,
                retrieved_at=timestamp,
                provenance_evidence={
                    "provider": "pexels",
                    "provider_id": photo_id,
                    "photographer": p.get("photographer"),
                    "license": "Pexels Content License",
                    "commercial_use": "ALLOWED",
                    "attribution_required": False,
                },
                provider_score=None,
                provider_metadata={"photographer_id": p.get("photographer_id")},
            ))
        return candidates

    def _normalize_videos(self, raw_videos: List[Dict[str, Any]], query: str, timestamp: str) -> List[StockCandidate]:
        candidates: List[StockCandidate] = []
        for v in raw_videos:
            video_id = str(v.get("id"))
            width = v.get("width")
            height = v.get("height")
            duration = float(v.get("duration", 0.0))

            variants: List[DownloadVariant] = []
            for vf in v.get("video_files", []):
                link = vf.get("link")
                if link:
                    variants.append(DownloadVariant(
                        variant_id=str(vf.get("id", vf.get("quality", "sd"))),
                        url=link,
                        width=vf.get("width"),
                        height=vf.get("height"),
                        quality=vf.get("quality"),
                        fps=float(vf.get("fps")) if vf.get("fps") else None,
                        format="mp4",
                    ))

            # Select 1080p / hd variant if available
            selected_var = next((var for var in variants if var.quality == "hd"), None)
            if not selected_var and variants:
                # Pick variant with highest width
                selected_var = max(variants, key=lambda x: x.width or 0)

            orient = "portrait" if (width and height and height > width) else "landscape" if (width and height and width > height) else "square"

            candidates.append(StockCandidate(
                candidate_id=f"pexels:{video_id}",
                source="pexels",
                source_asset_id=video_id,
                media_type=StockMediaType.VIDEO,
                title=f"Pexels Video {video_id}",
                preview_url=v.get("image"),
                download_variants=variants,
                selected_variant=selected_var,
                width=width,
                height=height,
                duration_seconds=duration,
                orientation=orient,
                aspect_ratio=round(width / height, 2) if (width and height) else None,
                mime_type="video/mp4",
                tags=[],
                license=LicenseClassification.PEXELS_LICENSE,
                license_name="Pexels Content License",
                commercial_use=CommercialUseStatus.ALLOWED,
                attribution_required=False,
                creator=v.get("user", {}).get("name") if isinstance(v.get("user"), dict) else None,
                creator_url=v.get("user", {}).get("url") if isinstance(v.get("user"), dict) else None,
                source_reference=v.get("url"),
                query=query,
                retrieved_at=timestamp,
                provenance_evidence={
                    "provider": "pexels",
                    "provider_id": video_id,
                    "creator": v.get("user", {}).get("name") if isinstance(v.get("user"), dict) else None,
                    "license": "Pexels Content License",
                    "commercial_use": "ALLOWED",
                    "attribution_required": False,
                },
                provider_score=None,
                provider_metadata={"avg_color": v.get("avg_color")},
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
