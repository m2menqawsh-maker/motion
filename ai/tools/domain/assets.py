"""
ai/tools/domain/assets.py
========================
Domain tool adapter for project media asset inspection (S27.9).

Invariants:
- Zero raw filesystem or direct DB access.
- Delegates completely to canonical AssetService.
- Returns verified media asset inventory.
"""

from __future__ import annotations

from api.services.asset_service import AssetService
from ai.tools.contracts import (
    AssetSummaryItem,
    CheckAssetCacheInput,
    CheckAssetCacheOutput,
    ListAssetsInput,
    ListAssetsOutput,
    SaveAssetCacheInput,
    SaveAssetCacheOutput,
    UpdateAssetStatusInput,
    UpdateAssetStatusOutput,
)
from ai.tools.types import TrustedToolExecutionContext


def list_assets_adapter(
    input_data: ListAssetsInput,
    context: TrustedToolExecutionContext,
) -> ListAssetsOutput:
    """
    Retrieves registered asset records for a project via AssetService.
    """
    raw_assets = AssetService.list_assets(input_data.project_id)

    items = []
    for a in raw_assets:
        meta = a.get("metadata") or {}
        items.append(
            AssetSummaryItem(
                asset_id=str(a.get("asset_id", "")),
                kind=str(a.get("kind", "unknown")),
                status=str(a.get("status", "unknown")),
                filename=meta.get("original_filename"),
                size_bytes=meta.get("size_bytes"),
                location=str(a.get("processed_path") or a.get("source_path") or ""),
            )
        )

    return ListAssetsOutput(
        project_id=input_data.project_id,
        total_count=len(items),
        assets=items,
    )


def update_asset_status_adapter(
    input_data: UpdateAssetStatusInput,
    context: TrustedToolExecutionContext,
) -> UpdateAssetStatusOutput:
    """
    Updates the status of an asset via AssetService (S27.10 Domain Migration).
    """
    res = AssetService.update_asset_status(
        project_id=input_data.project_id,
        asset_id=input_data.asset_id,
        new_status=input_data.new_status,
    )
    return UpdateAssetStatusOutput(
        project_id=input_data.project_id,
        asset_id=str(res.get("asset_id", input_data.asset_id)),
        status=str(res.get("status", input_data.new_status)),
        kind=str(res.get("kind", "unknown")),
    )


def check_asset_cache_adapter(
    input_data: CheckAssetCacheInput,
    context: TrustedToolExecutionContext,
) -> CheckAssetCacheOutput:
    """
    Checks asset cache existence via AssetService (S27.10 Domain Migration).
    """
    cached_path = AssetService.check_asset_cache(
        project_id=input_data.project_id,
        asset_id=input_data.asset_id,
        specs_hash=input_data.specs_hash,
    )
    return CheckAssetCacheOutput(
        project_id=input_data.project_id,
        asset_id=input_data.asset_id,
        hit=cached_path is not None,
        cached_location=cached_path,
    )


def save_asset_cache_adapter(
    input_data: SaveAssetCacheInput,
    context: TrustedToolExecutionContext,
) -> SaveAssetCacheOutput:
    """
    Saves asset variant to cache via AssetService (S27.10 Domain Migration).
    """
    dest_path = AssetService.save_asset_to_cache(
        project_id=input_data.project_id,
        asset_id=input_data.asset_id,
        file_path=input_data.file_path,
        specs_hash=input_data.specs_hash,
    )
    return SaveAssetCacheOutput(
        project_id=input_data.project_id,
        asset_id=input_data.asset_id,
        cached_location=dest_path,
    )


