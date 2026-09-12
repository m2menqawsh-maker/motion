from fastapi import APIRouter, HTTPException, Body
import json
from pathlib import Path

router = APIRouter()

@router.get("/{project_id}")
async def get_blueprint(project_id: str):
    blueprint_path = Path(f"projects/{project_id}/blueprint.json")
    overrides_path = Path(f"projects/{project_id}/overrides.json")
    
    data = {}
    if blueprint_path.exists():
        data["blueprint"] = json.loads(blueprint_path.read_text(encoding="utf-8"))
    if overrides_path.exists():
        data["overrides"] = json.loads(overrides_path.read_text(encoding="utf-8"))
        
    if not data:
        raise HTTPException(status_code=404, detail="Blueprint/Overrides not found")
    return data

@router.post("/{project_id}/blueprint")
async def update_blueprint(project_id: str, payload: dict = Body(...)):
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    filepath = project_dir / "blueprint.json"
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "success"}

@router.post("/{project_id}/overrides")
async def update_overrides(project_id: str, payload: dict = Body(...)):
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    filepath = project_dir / "overrides.json"
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "success"}
