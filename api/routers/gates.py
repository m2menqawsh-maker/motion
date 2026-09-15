from scripts.path_security import validate_project_id
import subprocess
from scripts.security import safe_subprocess
from fastapi import APIRouter, HTTPException
from api.services.gate_service import (
    get_status, start_stage, finish_stage, approve_gate, reject_gate
)

router = APIRouter()

@router.get("/{project_id}/status")
async def status(project_id: str):
    project_id = validate_project_id(project_id)
    res = await get_status(project_id)
    if not res:
        raise HTTPException(status_code=404, detail="Project state not found")
    return res

@router.post("/{project_id}/start/{stage}")
async def start(project_id: str, stage: int):
    project_id = validate_project_id(project_id)
    result = await start_stage(project_id, str(stage))
    return {"status": "success", "output": result}

@router.post("/{project_id}/finish/{stage}")
async def finish(project_id: str, stage: int):
    project_id = validate_project_id(project_id)
    result = await finish_stage(project_id, str(stage))
    return {"status": "success", "output": result}

@router.post("/{project_id}/approve/{gate}")
async def approve(project_id: str, gate: int, by: str = "gui"):
    project_id = validate_project_id(project_id)
    result = await approve_gate(project_id, str(gate), by)
    return {"status": "success", "output": result}

@router.post("/{project_id}/reject/{gate}")
async def reject(project_id: str, gate: int, by: str, note: str):
    project_id = validate_project_id(project_id)
    result = await reject_gate(project_id, str(gate), by, note)
    return {"status": "success", "output": result}
