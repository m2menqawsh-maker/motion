"""
ai/acquisition/providers/iconify.py
===================================
Adapter for Iconify Open-Source Icon Registry (S28-M05).

Invariants:
- Public open-source API (zero required commercial secrets).
- Normalizes icons to canonical StockCandidate contracts (media_type=ICON).
- Resolves SVG download vectors with customizable styling (color, width, height).
- Preserves collection license metadata and open-source provenance.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
    ProviderUnavailableError,
)
from ai.acquisition.providers.base import StockSourceAdapter


class IconifyAdapter(StockSourceAdapter):
    """Modernized provider adapter for Iconify vector icon API."""

    SEARCH_URL = "https://api.iconify.design/search"
    DOWNLOAD_TEMPLATE = "https://api.iconify.design/{prefix}/{name}.svg"

    @property
    def name(self) -> str:
        return "iconify"

    @property
    def supported_media_types(self) -> Set[StockMediaType]:
        return {StockMediaType.ICON}

    def is_available(self) -> bool:
        return True  # Public API without credentials

    async def search(self, query: StockSearchQuery) -> List[StockCandidate]:
        params = {
            "query": query.query,
            "limit": query.per_page,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(self.SEARCH_URL, params=params)
            except httpx.TimeoutException as e:
                raise ProviderUnavailableError(self.name, f"Request timed out: {e}")
            except httpx.RequestError as e:
                raise ProviderUnavailableError(self.name, f"Network error: {e}")

            if response.status_code >= 500:
                raise ProviderUnavailableError(self.name, f"Server error HTTP {response.status_code}")
            elif response.status_code != 200:
                raise InvalidProviderResponseError(self.name, f"HTTP status {response.status_code}")

            try:
                data = response.json()
            except Exception as e:
                raise InvalidProviderResponseError(self.name, f"JSON parse error: {e}")

        now_iso = datetime.now(timezone.utc).isoformat()
        icons = data.get("icons", [])
        collections = data.get("collections", {})

        candidates: List[StockCandidate] = []
        for icon_str in icons:
            if ":" in icon_str:
                prefix, icon_name = icon_str.split(":", 1)
            else:
                prefix, icon_name = "icon", icon_str

            col_meta = collections.get(prefix, {})
            candidates.append(self._normalize_icon(prefix, icon_name, query.query, now_iso, col_meta))

        return candidates

    def _normalize_icon(
        self,
        prefix: str,
        icon_name: str,
        query: str,
        timestamp: str,
        col_meta: Optional[Dict[str, Any]] = None,
    ) -> StockCandidate:
        col_meta = col_meta or {}
        svg_url = self.DOWNLOAD_TEMPLATE.format(prefix=prefix, name=icon_name)
        col_license = col_meta.get("license", {})
        license_title = col_license.get("title") if isinstance(col_license, dict) else (str(col_license) if col_license else None)
        spdx = col_license.get("spdx") if isinstance(col_license, dict) else None

        # Parse license truth
        lic_str = f"{license_title or ''} {spdx or ''}".lower().strip()
        if not lic_str or not license_title:
            license_cls = LicenseClassification.UNKNOWN
            license_name = "Unknown / Missing License"
            commercial_use = CommercialUseStatus.REQUIRES_REVIEW
            attribution_required = True
        elif any(nc in lic_str for nc in ("noncommercial", "non-commercial", "by-nc")):
            license_cls = LicenseClassification.CC_BY_NC
            license_name = license_title
            commercial_use = CommercialUseStatus.PROHIBITED
            attribution_required = True
        elif any(cl in lic_str for cl in ("gpl", "agpl", "lgpl", "by-sa", "sharealike")):
            license_cls = LicenseClassification.OPEN_SOURCE_ICON
            license_name = license_title
            commercial_use = CommercialUseStatus.REQUIRES_REVIEW
            attribution_required = True
        elif any(perm in lic_str for perm in ("mit", "apache", "cc0", "sil ofl", "bsd", "unlicense", "isc")):
            license_cls = LicenseClassification.OPEN_SOURCE_ICON
            license_name = license_title
            commercial_use = CommercialUseStatus.ALLOWED
            attribution_required = False if any(z in lic_str for z in ("cc0", "unlicense")) else True
        else:
            license_cls = LicenseClassification.UNKNOWN
            license_name = license_title or "Unclassified License"
            commercial_use = CommercialUseStatus.REQUIRES_REVIEW
            attribution_required = True

        category_tags = col_meta.get("category", "").split() if col_meta.get("category") else []

        return StockCandidate(
            candidate_id=f"iconify:{prefix}:{icon_name}",
            source="iconify",
            source_asset_id=f"{prefix}:{icon_name}",
            media_type=StockMediaType.ICON,
            title=f"{col_meta.get('name', prefix)} / {icon_name}",
            preview_url=svg_url,
            download_variants=[
                DownloadVariant(
                    variant_id="svg_vector",
                    url=svg_url,
                    format="svg",
                    quality="vector",
                )
            ],
            selected_variant=DownloadVariant(
                variant_id="svg_vector",
                url=svg_url,
                format="svg",
                quality="vector",
            ),
            width=None,
            height=None,
            mime_type="image/svg+xml",
            tags=[prefix, icon_name, *category_tags],
            license=license_cls,
            license_name=license_name,
            commercial_use=commercial_use,
            attribution_required=attribution_required,
            creator=col_meta.get("author", {}).get("name") if isinstance(col_meta.get("author"), dict) else None,
            source_reference=f"https://icon-sets.iconify.design/{prefix}/{icon_name}/",
            query=query,
            retrieved_at=timestamp,
            provenance_evidence={
                "provider": "iconify",
                "collection": prefix,
                "icon_name": icon_name,
                "license": license_name,
                "commercial_use": commercial_use.value,
                "attribution_required": attribution_required,
            },
            provider_score=None,
            provider_metadata={"collection": prefix},
        )

    def resolve_acquisition(
        self,
        candidate: StockCandidate,
        requested_variant_id: Optional[str] = None,
        color: Optional[str] = None,
        size: Optional[int] = None,
    ) -> AcquisitionDescriptor:
        prefix, icon_name = candidate.source_asset_id.split(":", 1) if ":" in candidate.source_asset_id else ("icon", candidate.source_asset_id)
        url = self.DOWNLOAD_TEMPLATE.format(prefix=prefix, name=icon_name)

        query_params = []
        if color:
            clean_color = color.replace("#", "%23")
            query_params.append(f"color={clean_color}")
        if size:
            query_params.append(f"width={size}&height={size}")

        if query_params:
            url = f"{url}?{'&'.join(query_params)}"

        return AcquisitionDescriptor(
            candidate_id=candidate.candidate_id,
            source=candidate.source,
            source_asset_id=candidate.source_asset_id,
            download_url=url,
            media_type=StockMediaType.ICON,
            variant_id="svg_vector",
            expected_mime_type="image/svg+xml",
            expected_format=".svg",
            provenance=candidate.provenance_evidence,
        )
