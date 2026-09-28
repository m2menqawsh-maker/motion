"""
Blueprint & Overrides API Router (S22 - LED-067, LED-068, LED-069).

HTTP transport layer for blueprint queries, mutations, and scene overrides:
- Delegated completely to PipelineService and OverrideService
- Zero direct filesystem access or serialization in router
- Optimistic concurrency control via ETag and If-Match headers
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Body, Depends, Header, Response, status
from api.schemas import BlueprintResponse, StandardResponse
from api.core.errors import APIError
from api.core.auth import require_permission, Principal, Action
from api.services.pipeline_service import PipelineService
from api.services.override_service import OverrideService

router = APIRouter()


@router.get("/{project_id}", response_model=BlueprintResponse, summary="Get project blueprint and overrides")
async def get_blueprint(
    project_id: str,
    response: Response,
    principal: Principal = Depends(require_permission(Action.BLUEPRINT_READ)),
):
    data = {}
    bp_dict = PipelineService.get_blueprint(project_id)
    if bp_dict is not None:
        data["blueprint"] = bp_dict

    overrides_dict, rev = OverrideService.get_overrides(project_id)
    if overrides_dict:
        data["overrides"] = overrides_dict

    if not data:
        raise APIError(message="Blueprint/Overrides not found", status_code=404)

    response.headers["ETag"] = f'"{rev}"'
    return BlueprintResponse(**data)


@router.post("/{project_id}/blueprint", response_model=StandardResponse, summary="Mutate project blueprint")
async def update_blueprint(
    project_id: str,
    payload: Dict[str, Any] = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    principal: Principal = Depends(require_permission(Action.BLUEPRINT_EDIT)),
):
    ok, errors = PipelineService.validate_blueprint_payload(project_id, payload)
    if not ok:
        raise APIError(message=f"Invalid blueprint: {'; '.join(errors)}", status_code=400)

    actor = getattr(principal, "principal_id", "api_user")
    PipelineService.mutate_blueprint(project_id, payload, actor_id=actor)

    return StandardResponse(status="success", message="Blueprint updated successfully")


@router.post("/{project_id}/overrides", response_model=StandardResponse, summary="Update scene overrides")
@router.put("/{project_id}/overrides", response_model=StandardResponse, summary="Update scene overrides")
async def update_overrides(
    project_id: str,
    response: Response,
    payload: Dict[str, Any] = Body(...),
    if_match: Optional[str] = Header(None, alias="If-Match"),
    principal: Principal = Depends(require_permission(Action.BLUEPRINT_EDIT)),
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

    _, new_revision = OverrideService.update_overrides(
        project_id=project_id,
        payload=payload,
        expected_revision=expected_rev,
    )

    response.headers["ETag"] = f'"{new_revision}"'
    return StandardResponse(status="success", message="Overrides updated successfully")
