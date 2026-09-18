from scripts.path_security import validate_project_id
from fastapi import APIRouter
from pydantic import BaseModel
from api.services.scaffold_service import create_project
import json
from pathlib import Path
from api.services.pipeline_service import PipelineService
from api.schemas import ProjectCreateRequest, ProjectCreateResponse, ProjectListResponse, ProjectResponse
from api.core.errors import ProjectNotFoundError

router = APIRouter()

@router.post("/", response_model=ProjectCreateResponse)
async def create(req: ProjectCreateRequest):
    project_id = create_project(req.name, req.language)
    return ProjectCreateResponse(project_id=project_id)

@router.get("/", response_model=ProjectListResponse)
async def list_projects():
    projects_dir = Path("projects")
    if not projects_dir.exists():
        return ProjectListResponse(projects=[])
    dirs = [d.name for d in projects_dir.iterdir() if d.is_dir() and d.name.startswith("prj_")]
    return ProjectListResponse(projects=dirs)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    project_id = validate_project_id(project_id)
    project_dir = Path(f"projects/{project_id}")
    
    if not project_dir.exists():
        raise ProjectNotFoundError(project_id)
    
    data = {}
    for filename in ["project.json", "02_asset_manifest.json"]:
        filepath = project_dir / filename
        if filepath.exists():
            data[filename.replace(".json", "")] = json.loads(filepath.read_text(encoding="utf-8"))
        else:
            data[filename.replace(".json", "")] = {}
            
    state_dict = await PipelineService.get_status(project_id)
            
    return ProjectResponse(
        project=data.get("project", {}),
        manifest=data.get("02_asset_manifest", {}),
        state=state_dict
    )

