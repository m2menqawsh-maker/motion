from fastapi import APIRouter, HTTPException, Body
import json
from pathlib import Path

router = APIRouter()

@router.get("/{project_id}")
async def get_brand(project_id: str):
    filepath = Path(f"projects/{project_id}/brand.json")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Brand not found")
    return json.loads(filepath.read_text(encoding="utf-8"))

@router.post("/{project_id}")
async def update_brand(project_id: str, payload: dict = Body(...)):
    filepath = Path(f"projects/{project_id}/brand.json")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    filepath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "success"}
