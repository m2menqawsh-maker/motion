from fastapi import APIRouter, Depends
from scripts.security.path_security import validate_project_id
from api.services.gate_service import (
    get_status, start_stage, finish_stage, approve_gate, reject_gate
)
from api.schemas import GateResponse, StageStatusResponse, GateName, StageName
from api.core.errors import ProjectNotFoundError
from api.core.auth import require_permission, Principal, Action

router = APIRouter()


@router.get("/{project_id}/status", response_model=StageStatusResponse)
async def status(
    project_id: str,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ))
):
    project_id = validate_project_id(project_id)
    res = await get_status(project_id)
    if not res:
        raise ProjectNotFoundError(project_id)
        
    return StageStatusResponse(state=res)


@router.post("/{project_id}/start/{stage}", response_model=GateResponse)
async def start(
    project_id: str,
    stage: StageName,
    principal: Principal = Depends(require_permission(Action.PROJECT_EDIT))
):
    project_id = validate_project_id(project_id)
    result = await start_stage(project_id, stage.value)
    return GateResponse(status="success", output=result)


@router.post("/{project_id}/finish/{stage}", response_model=GateResponse)
async def finish(
    project_id: str,
    stage: StageName,
    principal: Principal = Depends(require_permission(Action.PROJECT_EDIT))
):
    project_id = validate_project_id(project_id)
    result = await finish_stage(project_id, stage.value)
    return GateResponse(status="success", output=result)


@router.post("/{project_id}/approve/{gate}", response_model=GateResponse)
async def approve(
    project_id: str,
    gate: GateName,
    principal: Principal = Depends(require_permission(Action.REVIEW_APPROVE))
):
    project_id = validate_project_id(project_id)
    # Actor identity is derived strictly from server-verified principal, NEVER from user request
    result = await approve_gate(project_id, gate.value, by=principal.principal_id)
    return GateResponse(status="success", output=result)


@router.post("/{project_id}/reject/{gate}", response_model=GateResponse)
async def reject(
    project_id: str,
    gate: GateName,
    note: str = "",
    principal: Principal = Depends(require_permission(Action.REVIEW_REJECT))
):
    project_id = validate_project_id(project_id)
    # Actor identity is derived strictly from server-verified principal, NEVER from user request
    result = await reject_gate(project_id, gate.value, by=principal.principal_id, note=note)
    return GateResponse(status="success", output=result)
