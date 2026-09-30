"""
Assets API Router (S22 - LED-063).

Canonical endpoints for managing media assets within project boundaries:
- GET    /projects/{project_id}/assets -> Lists assets
- GET    /projects/{project_id}/assets/{asset_id} -> Gets asset details
- POST   /projects/{project_id}/assets -> Uploads or imports an asset
- DELETE /projects/{project_id}/assets/{asset_id} -> Removes an asset
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Form, status
from api.core.auth import require_permission, Principal, Action
from api.schemas.asset import AssetResponse, AssetListResponse, AssetUploadResponse
from api.services.asset_service import AssetService

router = APIRouter()


@router.get(
    "/{project_id}/assets",
    response_model=AssetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List project assets",
)
async def list_assets(
    project_id: str,
    principal: Principal = Depends(require_permission(Action.ASSET_READ)),
):
    assets_raw = AssetService.list_assets(project_id)
    dto_list = [AssetResponse(**a) for a in assets_raw]
    return AssetListResponse(project_id=project_id, assets=dto_list, total=len(dto_list))


@router.get(
    "/{project_id}/assets/{asset_id}",
    response_model=AssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get asset details",
)
async def get_asset(
    project_id: str,
    asset_id: str,
    principal: Principal = Depends(require_permission(Action.ASSET_READ)),
):
    asset_raw = AssetService.get_asset(project_id=project_id, asset_id=asset_id)
    return AssetResponse(**asset_raw)


@router.post(
    "/{project_id}/assets",
    response_model=AssetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or register an asset",
)
async def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    asset_id: Optional[str] = Form(None),
    kind: Optional[str] = Form(None),
    principal: Principal = Depends(require_permission(Action.ASSET_UPLOAD)),
):
    content = await file.read()
    raw_record = AssetService.upload_asset(
        project_id=project_id,
        content=content,
        filename=file.filename or "upload.bin",
        asset_id=asset_id,
        kind=kind,
    )
    return AssetUploadResponse(
        status="success",
        asset=AssetResponse(**raw_record),
        message=f"Asset '{raw_record['asset_id']}' uploaded and registered in manifest",
    )


@router.delete(
    "/{project_id}/assets/{asset_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an asset",
)
async def delete_asset(
    project_id: str,
    asset_id: str,
    principal: Principal = Depends(require_permission(Action.ASSET_DELETE)),
):
    AssetService.delete_asset(project_id=project_id, asset_id=asset_id)
    return {"status": "success", "message": f"Asset '{asset_id}' deleted"}
