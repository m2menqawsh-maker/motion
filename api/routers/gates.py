from scripts.security.path_security import validate_project_id
from fastapi import APIRouter
from api.services.gate_service import (
    get_status, start_stage, finish_stage, approve_gate, reject_gate
)
from api.schemas import GateResponse, StageStatusResponse
from api.core.errors import ProjectNotFoundError

router = APIRouter()

@router.get("/{project_id}/status", response_model=StageStatusResponse)
async def status(project_id: str):
    project_id = validate_project_id(project_id)
    res = await get_status(project_id)
    if not res:
        raise ProjectNotFoundError(project_id)
        
    return StageStatusResponse(state=res)

@router.post("/{project_id}/start/{stage}", response_model=GateResponse)
async def start(project_id: str, stage: str):
    project_id = validate_project_id(project_id)
    result = await start_stage(project_id, stage)
    return GateResponse(status="success", output=result)

@router.post("/{project_id}/finish/{stage}", response_model=GateResponse)
async def finish(project_id: str, stage: str):
    project_id = validate_project_id(project_id)
    result = await finish_stage(project_id, stage)
    return GateResponse(status="success", output=result)

@router.post("/{project_id}/approve/{gate}", response_model=GateResponse)
async def approve(project_id: str, gate: str, by: str = "gui"):
    project_id = validate_project_id(project_id)
    result = await approve_gate(project_id, gate, by)
    return GateResponse(status="success", output=result)

@router.post("/{project_id}/reject/{gate}", response_model=GateResponse)
async def reject(project_id: str, gate: str, by: str, note: str):
    project_id = validate_project_id(project_id)
    result = await reject_gate(project_id, gate, by, note)
    return GateResponse(status="success", output=result)

