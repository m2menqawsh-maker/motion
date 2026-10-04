"""
ai/acquisition/providers/freesound.py
=====================================
Adapter for Freesound Sound Effects and Audio Library (S28-M05).

Invariants:
- Requires FREESOUND_API_KEY. Fails with structured ProviderAuthError if missing.
- Strictly parses Creative Commons licenses (CC0, CC-BY, CC-BY-NC).
- CC-BY-NC sounds are explicitly classified as commercial_use=PROHIBITED.
- Download variants provide high-quality MP3/OGG streams.
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


class FreesoundAdapter(StockSourceAdapter):
    """Modernized provider adapter for Freesound audio and sound effects API."""

    API_URL = "https://freesound.org/apiv2/search/text/"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "freesound"

    @property
    def supported_media_types(self) -> Set[StockMediaType]:
        return {StockMediaType.AUDIO, StockMediaType.SOUND_EFFECT}

    def is_available(self) -> bool:
        return bool(self._api_key or os.environ.get("FREESOUND_API_KEY"))

    def _get_api_key(self) -> str:
        key = self._api_key or os.environ.get("FREESOUND_API_KEY")
        if not key:
            raise ProviderAuthError(self.name, "FREESOUND_API_KEY environment variable is not configured.")
        return key

    async def search(self, query: StockSearchQuery) -> List[StockCandidate]:
        api_key = self._get_api_key()

        params: Dict[str, Any] = {
            "token": api_key,
            "query": query.query,
            "page": query.page,
            "page_size": query.per_page,
            "fields": "id,name,previews,tags,description,duration,license,username,url",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(self.API_URL, params=params)
            except httpx.TimeoutException as e:
                raise ProviderUnavailableError(self.name, f"Request timed out: {e}")
            except httpx.RequestError as e:
                raise ProviderUnavailableError(self.name, f"Network error: {e}")

            if response.status_code == 401 or response.status_code == 403:
                raise ProviderAuthError(self.name, f"Invalid Freesound token (HTTP {response.status_code}).")
            elif response.status_code == 429:
                raise ProviderRateLimitError(self.name)
            elif response.status_code >= 500:
                raise ProviderUnavailableError(self.name, f"Server error HTTP {response.status_code}")
            elif response.status_code != 200:
                raise InvalidProviderResponseError(self.name, f"HTTP status {response.status_code}: {response.text[:200]}")

            try:
                data = response.json()
            except Exception as e:
                raise InvalidProviderResponseError(self.name, f"JSON decode failed: {e}")

        now_iso = datetime.now(timezone.utc).isoformat()
        results = data.get("results", [])
        return self._normalize_sounds(results, query.query, now_iso)

    def _normalize_sounds(self, raw_sounds: List[Dict[str, Any]], query: str, timestamp: str) -> List[StockCandidate]:
        candidates: List[StockCandidate] = []
        for s in raw_sounds:
            sound_id = str(s.get("id"))
            name = s.get("name") or f"Freesound {sound_id}"
            duration = float(s.get("duration", 0.0))
            previews = s.get("previews", {})

            variants: List[DownloadVariant] = []
            if previews.get("preview-hq-mp3"):
                variants.append(DownloadVariant(
                    variant_id="preview-hq-mp3",
                    url=previews["preview-hq-mp3"],
                    quality="hq",
                    format="mp3",
                ))
            if previews.get("preview-lq-mp3"):
                variants.append(DownloadVariant(
                    variant_id="preview-lq-mp3",
                    url=previews["preview-lq-mp3"],
                    quality="lq",
                    format="mp3",
                ))
            if previews.get("preview-hq-ogg"):
                variants.append(DownloadVariant(
                    variant_id="preview-hq-ogg",
                    url=previews["preview-hq-ogg"],
                    quality="hq",
                    format="ogg",
                ))

            selected_var = variants[0] if variants else None

            # Parse Creative Commons license
            raw_license = (s.get("license") or "").lower()
            if not raw_license:
                license_cls = LicenseClassification.UNKNOWN
                commercial = CommercialUseStatus.REQUIRES_REVIEW
                attrib = True
            elif "zero" in raw_license or "cc0" in raw_license or "publicdomain" in raw_license:
                license_cls = LicenseClassification.CC0
                commercial = CommercialUseStatus.ALLOWED
                attrib = False
            elif "by-nc" in raw_license or "noncommercial" in raw_license:
                license_cls = LicenseClassification.CC_BY_NC
                commercial = CommercialUseStatus.PROHIBITED
                attrib = True
            elif "by-sa" in raw_license or "sharealike" in raw_license:
                license_cls = LicenseClassification.CC_BY
                commercial = CommercialUseStatus.REQUIRES_REVIEW
                attrib = True
            elif "by" in raw_license:
                license_cls = LicenseClassification.CC_BY
                commercial = CommercialUseStatus.ALLOWED
                attrib = True
            else:
                license_cls = LicenseClassification.UNKNOWN
                commercial = CommercialUseStatus.REQUIRES_REVIEW
                attrib = True

            candidates.append(StockCandidate(
                candidate_id=f"freesound:{sound_id}",
                source="freesound",
                source_asset_id=sound_id,
                media_type=StockMediaType.SOUND_EFFECT,
                title=name,
                description=s.get("description"),
                preview_url=previews.get("preview-lq-mp3"),
                download_variants=variants,
                selected_variant=selected_var,
                duration_seconds=duration,
                mime_type="audio/mpeg",
                tags=s.get("tags", []),
                license=license_cls,
                license_name=s.get("license"),
                commercial_use=commercial,
                attribution_required=attrib,
                creator=s.get("username"),
                source_reference=s.get("url") or f"https://freesound.org/people/{s.get('username')}/sounds/{sound_id}/",
                query=query,
                retrieved_at=timestamp,
                provenance_evidence={
                    "provider": "freesound",
                    "provider_id": sound_id,
                    "author": s.get("username"),
                    "license_url": s.get("license"),
                    "commercial_use": commercial.value,
                    "attribution_required": attrib,
                },
                provider_score=None,
                provider_metadata={"original_license": s.get("license")},
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
            raise InvalidProviderResponseError(self.name, f"No download URL available for candidate '{candidate.candidate_id}'.")

        return AcquisitionDescriptor(
            candidate_id=candidate.candidate_id,
            source=candidate.source,
            source_asset_id=candidate.source_asset_id,
            download_url=target_variant.url,
            media_type=candidate.media_type,
            variant_id=target_variant.variant_id,
            expected_mime_type="audio/mpeg",
            expected_format=".mp3",
            provenance=candidate.provenance_evidence,
        )
