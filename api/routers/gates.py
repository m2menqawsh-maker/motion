from fastapi import APIRouter, HTTPException
from api.services.gate_service import (
    get_status, start_stage, finish_stage, approve_gate, reject_gate
)

router = APIRouter()

@router.get("/{project_id}/status")
async def status(project_id: str):
    res = get_status(project_id)
    if not res:
        raise HTTPException(status_code=404, detail="Project state not found")
    return res

@router.post("/{project_id}/start/{stage}")
async def start(project_id: str, stage: int):
    result = start_stage(project_id, stage)
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=result["stderr"] or result["stdout"])
    return {"status": "success", "output": result["stdout"]}

@router.post("/{project_id}/finish/{stage}")
async def finish(project_id: str, stage: int):
    result = finish_stage(project_id, stage)
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=result["stderr"] or result["stdout"])
    return {"status": "success", "output": result["stdout"]}

@router.post("/{project_id}/approve/{gate}")
async def approve(project_id: str, gate: int, by: str = "gui"):
    result = approve_gate(project_id, gate, by)
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=result["stderr"] or result["stdout"])
    return {"status": "success", "output": result["stdout"]}

@router.post("/{project_id}/reject/{gate}")
async def reject(project_id: str, gate: int, by: str, note: str):
    result = reject_gate(project_id, gate, by, note)
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=result["stderr"] or result["stdout"])
    return {"status": "success", "output": result["stdout"]}
