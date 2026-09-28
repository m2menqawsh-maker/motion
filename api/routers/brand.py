"""
Brand API Router (S22 - LED-066, LED-068, LED-069).

HTTP transport layer for project visual brand identity:
- Delegated completely to BrandService domain authority
- Zero direct filesystem access or serialization in router
- Optimistic concurrency control via ETag and If-Match headers
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Body, Depends, Header, Response, status
from api.core.auth import require_permission, Principal, Action
from api.services.brand_service import BrandService

router = APIRouter()


@router.get("/{project_id}", summary="Get project visual brand kit")
async def get_brand(
    project_id: str,
    response: Response,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    brand_data, revision = BrandService.get_brand(project_id)
    response.headers["ETag"] = f'"{revision}"'
    return brand_data


@router.post("/{project_id}", summary="Update project visual brand kit")
@router.put("/{project_id}", summary="Update project visual brand kit")
async def update_brand(
    project_id: str,
    response: Response,
    payload: Dict[str, Any] = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    principal: Principal = Depends(require_permission(Action.PROJECT_EDIT)),
):
    expected_rev: Optional[int] = None
    if if_match is not None:
        clean_match = if_match.strip().strip('"').strip("'")
        if clean_match.startswith("rev_"):
            clean_match = clean_match[4:]
        if clean_match.isdigit():
            expected_rev = int(clean_match)
        else:
            from api.core.errors import RevisionConflictError
            raise RevisionConflictError(
                message=f"If-Match header '{if_match}' does not match current state",
                current_revision=-1,
                expected_revision=-1,
            )

    updated_data, new_revision = BrandService.update_brand(
        project_id=project_id,
        payload=payload,
        expected_revision=expected_rev,
    )
    response.headers["ETag"] = f'"{new_revision}"'
    return {"status": "success", "revision": new_revision, "brand": updated_data}
