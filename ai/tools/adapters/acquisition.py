"""
ai/tools/adapters/acquisition.py
================================
Canonical execution adapter for Stock Media & Acquisition capabilities (S28-M05).

Invariants:
- Integrates with AssetAcquisitionService for search, ranking, filtering, and safe download.
- Routes all 8 MEDIA_ACQUISITION capabilities through authoritative domain boundaries.
- Replaces unmanaged legacy direct-to-disk downloads with AssetService/StorageService persistence.
- Preserves structured error mapping to AIError.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ai.acquisition.contracts import (
    StockCandidate,
    StockMediaType,
    StockSearchQuery,
)
from ai.acquisition.errors import AcquisitionError
from ai.acquisition.service import (
    AssetAcquisitionService,
    get_asset_acquisition_service,
)
from ai.contracts import (
    AIContractModel,
    CapabilityDefinition,
    CapabilityRequest,
    CapabilityType,
    ImplementationDescriptor,
)
from ai.contracts.media_ops import (
    DownloadIconInput,
    DownloadRemoteMediaInput,
    ExtractMediaPageInput,
    IconSearchResultItem,
    SearchIconsInput,
    SearchSoundEffectsInput,
    SearchStockAudioInput,
    SearchStockImagesInput,
    SearchStockVideosInput,
    StockMediaItem,
)
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.types import TrustedToolExecutionContext


def _candidate_to_stock_media_item(c: StockCandidate) -> Dict[str, Any]:
    """Converts internal StockCandidate model to canonical StockMediaItem dictionary."""
    download_url = None
    if c.selected_variant:
        download_url = c.selected_variant.url
    elif c.download_variants:
        download_url = c.download_variants[0].url

    return {
        "media_id": c.candidate_id,
        "media_type": c.media_type.value,
        "title": c.title,
        "preview_url": c.preview_url,
        "download_url": download_url,
        "width": c.width,
        "height": c.height,
        "duration_seconds": c.duration_seconds,
        "license": c.license.value,
    }


class AssetAcquisitionAdapter(CapabilityAdapter):
    """
    Adapter bridging validated canonical MEDIA_ACQUISITION capabilities
    to the AssetAcquisitionService domain pipeline.
    """

    SUPPORTED_CAPABILITIES = {
        CapabilityType.SEARCH_STOCK_IMAGES.value,
        CapabilityType.SEARCH_STOCK_VIDEOS.value,
        CapabilityType.SEARCH_STOCK_AUDIO.value,
        CapabilityType.SEARCH_SOUND_EFFECTS.value,
        CapabilityType.SEARCH_ICONS.value,
        CapabilityType.DOWNLOAD_ICON.value,
        CapabilityType.DOWNLOAD_REMOTE_MEDIA.value,
        CapabilityType.EXTRACT_MEDIA_PAGE.value,
    }

    def __init__(self, service: Optional[AssetAcquisitionService] = None) -> None:
        super().__init__(name="canonical_acquisition_adapter", adapter_kind="DOMAIN_SERVICE")
        self.service = service or get_asset_acquisition_service()

    def can_handle(
        self,
        capability: CapabilityDefinition,
        implementation: Optional[ImplementationDescriptor] = None,
    ) -> bool:
        cap_val = capability.capability_id.value if hasattr(capability.capability_id, "value") else str(capability.capability_id)
        return cap_val in self.SUPPORTED_CAPABILITIES

    async def execute(
        self,
        request: CapabilityRequest,
        validated_input: AIContractModel,
        context: TrustedToolExecutionContext,
    ) -> Dict[str, Any]:
        cap_val = request.capability_id.value if hasattr(request.capability_id, "value") else str(request.capability_id)

        try:
            if cap_val == CapabilityType.SEARCH_STOCK_IMAGES.value:
                return await self._execute_search_stock_images(validated_input, context)
            elif cap_val == CapabilityType.SEARCH_STOCK_VIDEOS.value:
                return await self._execute_search_stock_videos(validated_input, context)
            elif cap_val == CapabilityType.SEARCH_STOCK_AUDIO.value:
                return await self._execute_search_stock_audio(validated_input, context)
            elif cap_val == CapabilityType.SEARCH_SOUND_EFFECTS.value:
                return await self._execute_search_sound_effects(validated_input, context)
            elif cap_val == CapabilityType.SEARCH_ICONS.value:
                return await self._execute_search_icons(validated_input, context)
            elif cap_val == CapabilityType.DOWNLOAD_ICON.value:
                return await self._execute_download_icon(validated_input, context)
            elif cap_val == CapabilityType.DOWNLOAD_REMOTE_MEDIA.value:
                return await self._execute_download_remote_media(validated_input, context)
            elif cap_val == CapabilityType.EXTRACT_MEDIA_PAGE.value:
                return await self._execute_extract_media_page(validated_input, context)
            else:
                raise NotImplementedError(f"Capability '{cap_val}' not handled by AssetAcquisitionAdapter.")
        except AcquisitionError:
            # Let domain acquisition errors bubble up to ToolGateway for structured to_ai_error mapping
            raise

    async def _execute_search_stock_images(self, inp: AIContractModel, ctx: TrustedToolExecutionContext) -> Dict[str, Any]:
        assert isinstance(inp, SearchStockImagesInput)
        query = StockSearchQuery(
            query=inp.query,
            media_type=StockMediaType.IMAGE,
            orientation=inp.orientation,
            page=inp.page,
            per_page=inp.per_page,
            commercial_use_required=True,
        )
        candidates = await self.service.search_stock(query, context=ctx)
        return {
            "query": inp.query,
            "images": [_candidate_to_stock_media_item(c) for c in candidates],
            "page": inp.page,
            "total_results": len(candidates),
        }

    async def _execute_search_stock_videos(self, inp: AIContractModel, ctx: TrustedToolExecutionContext) -> Dict[str, Any]:
        assert isinstance(inp, SearchStockVideosInput)
        query = StockSearchQuery(
            query=inp.query,
            media_type=StockMediaType.VIDEO,
            orientation=inp.orientation,
            page=inp.page,
            per_page=inp.per_page,
            commercial_use_required=True,
        )
        candidates = await self.service.search_stock(query, context=ctx)
        return {
            "query": inp.query,
            "videos": [_candidate_to_stock_media_item(c) for c in candidates],
            "page": inp.page,
            "total_results": len(candidates),
        }

    async def _execute_search_stock_audio(self, inp: AIContractModel, ctx: TrustedToolExecutionContext) -> Dict[str, Any]:
        assert isinstance(inp, SearchStockAudioInput)
        query = StockSearchQuery(
            query=inp.query,
            media_type=StockMediaType.AUDIO,
            page=inp.page,
            per_page=inp.per_page,
            commercial_use_required=True,
        )
        candidates = await self.service.search_stock(query, context=ctx)
        return {
            "query": inp.query,
            "audio_tracks": [_candidate_to_stock_media_item(c) for c in candidates],
            "page": inp.page,
            "total_results": len(candidates),
        }

    async def _execute_search_sound_effects(self, inp: AIContractModel, ctx: TrustedToolExecutionContext) -> Dict[str, Any]:
        assert isinstance(inp, SearchSoundEffectsInput)
        min_dur = inp.duration_range[0] if inp.duration_range else None
        max_dur = inp.duration_range[1] if inp.duration_range else None
        query = StockSearchQuery(
            query=inp.query,
            media_type=StockMediaType.SOUND_EFFECT,
            min_duration=min_dur,
            max_duration=max_dur,
            page=inp.page,
            per_page=inp.per_page,
            commercial_use_required=True,
        )
        candidates = await self.service.search_stock(query, context=ctx)
        return {
            "query": inp.query,
            "sound_effects": [_candidate_to_stock_media_item(c) for c in candidates],
            "page": inp.page,
            "total_results": len(candidates),
        }

    async def _execute_search_icons(self, inp: AIContractModel, ctx: TrustedToolExecutionContext) -> Dict[str, Any]:
        assert isinstance(inp, SearchIconsInput)
        query = StockSearchQuery(
            query=inp.query,
            media_type=StockMediaType.ICON,
            per_page=inp.limit,
            allowed_providers=["iconify"],
        )
        candidates = await self.service.search_stock(query, context=ctx)
        icons: List[Dict[str, Any]] = []
        for c in candidates:
            prefix, name = c.source_asset_id.split(":", 1) if ":" in c.source_asset_id else ("icon", c.source_asset_id)
            icons.append({
                "icon_name": c.source_asset_id,
                "collection": prefix,
                "name": name,
                "svg_preview": c.preview_url,
            })
        return {
            "query": inp.query,
            "icons": icons,
            "total_found": len(icons),
        }

    async def _execute_download_icon(self, inp: AIContractModel, ctx: TrustedToolExecutionContext) -> Dict[str, Any]:
        assert isinstance(inp, DownloadIconInput)
        res = await self.service.download_icon(
            project_id=inp.project_id,
            icon_name=inp.icon_name,
            color=inp.color,
            size=inp.size,
            workspace_id=ctx.workspace_id,
            context=ctx,
        )
        return {
            "project_id": res.project_id,
            "asset_id": res.asset_id,
            "storage_key": res.storage_key,
            "format": "svg",
        }

    async def _execute_download_remote_media(self, inp: AIContractModel, ctx: TrustedToolExecutionContext) -> Dict[str, Any]:
        assert isinstance(inp, DownloadRemoteMediaInput)
        res = await self.service.download_remote_media(
            project_id=inp.project_id,
            url=inp.url,
            media_type=inp.media_type,
            destination_asset_id=inp.destination_asset_id,
            workspace_id=ctx.workspace_id,
            context=ctx,
        )
        return {
            "project_id": res.project_id,
            "asset_id": res.asset_id,
            "storage_key": res.storage_key,
            "file_size_bytes": res.file_size_bytes,
            "content_type": res.content_type,
        }

    async def _execute_extract_media_page(self, inp: AIContractModel, ctx: TrustedToolExecutionContext) -> Dict[str, Any]:
        assert isinstance(inp, ExtractMediaPageInput)
        # Bounded download via safe HTTP pipeline
        res = await self.service.download_remote_media(
            project_id=inp.project_id,
            url=inp.page_url,
            media_type=inp.media_type,
            workspace_id=ctx.workspace_id,
            context=ctx,
        )
        return {
            "project_id": res.project_id,
            "extracted_assets": [
                {
                    "asset_id": res.asset_id,
                    "storage_key": res.storage_key,
                    "source_url": inp.page_url,
                    "content_type": res.content_type,
                    "file_size_bytes": res.file_size_bytes,
                }
            ],
            "total_extracted": 1,
        }
