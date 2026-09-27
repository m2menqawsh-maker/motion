import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Body, Depends
from scripts.security.path_security import validate_project_id
from api.core.auth import require_permission, Principal, Action

router = APIRouter()


@router.get("/{project_id}")
async def get_brand(
    project_id: str,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ))
):
    project_id = validate_project_id(project_id)
    filepath = Path(f"projects/{project_id}/brand.json")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Brand not found")
    return json.loads(filepath.read_text(encoding="utf-8"))


@router.post("/{project_id}")
async def update_brand(
    project_id: str,
    payload: dict = Body(...),
    principal: Principal = Depends(require_permission(Action.PROJECT_EDIT))
):
    project_id = validate_project_id(project_id)
    filepath = Path(f"projects/{project_id}/brand.json")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "success"}
