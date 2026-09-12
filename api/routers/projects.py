from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services.scaffold_service import create_project
import json
from pathlib import Path

router = APIRouter()

class ProjectCreate(BaseModel):
    name: str
    aspect: str
    fps: int = 30
    language: str = "ar"

@router.post("/")
async def create(req: ProjectCreate):
    try:
        project_id = create_project(req.name, req.aspect, req.fps, req.language)
        return {"project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def list_projects():
    projects_dir = Path("projects")
    if not projects_dir.exists():
        return {"projects": []}
    dirs = [d.name for d in projects_dir.iterdir() if d.is_dir() and d.name.startswith("prj_")]
    return {"projects": dirs}

@router.get("/{project_id}")
async def get_project(project_id: str):
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    data = {}
    for filename in ["project.json", "state.json", "manifest.json"]:
        filepath = project_dir / filename
        if filepath.exists():
            data[filename.replace(".json", "")] = json.loads(filepath.read_text(encoding="utf-8"))
        else:
            data[filename.replace(".json", "")] = {}
            
    return data
