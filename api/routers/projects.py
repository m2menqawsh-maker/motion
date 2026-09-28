"""
Projects API Router (S22 - LED-069, LED-070, LED-071).

HTTP transport layer for project lifecycle, creation, listing, and state query:
- Non-blocking project creation via ProjectService.create_project_async
- Canonical LifecycleDTO projection endpoint: GET /projects/{project_id}/state
- Zero raw file reads or subprocess invocations inside router functions
"""

from fastapi import APIRouter, Depends, HTTPException, status
from api.core.auth import require_permission, Principal, Action
from api.schemas import (
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectListResponse,
    ProjectResponse,
)
from api.schemas.lifecycle import LifecycleDTO
from api.services.project_service import ProjectService
from api.services.pipeline_service import PipelineService
from scripts.security.path_security import validate_project_id

router = APIRouter()


@router.post("/", response_model=ProjectCreateResponse, status_code=status.HTTP_200_OK, summary="Create a new project")
async def create(
    req: ProjectCreateRequest,
    principal: Principal = Depends(require_permission(Action.PROJECT_CREATE)),
):
    project_id = await ProjectService.create_project_async(req.name, req.language)
    return ProjectCreateResponse(project_id=project_id)


@router.get("/", response_model=ProjectListResponse, summary="List accessible projects")
async def list_projects(
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    projects_list = ProjectService.list_projects(principal)
    return ProjectListResponse(projects=projects_list)


@router.get("/{project_id}/state", response_model=LifecycleDTO, summary="Get canonical lifecycle state DTO")
async def get_project_state(
    project_id: str,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    """
    Returns the canonical, un-degraded LifecycleDTO projection (LED-071).
    """
    return ProjectService.get_lifecycle_dto(project_id)


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project summary and legacy status")
async def get_project(
    project_id: str,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    validate_project_id(project_id)
    manifest_dict = PipelineService.get_manifest(project_id)

    # Use pipeline service get_status
    state_dict = await PipelineService.get_status(project_id)

    # Fetch project.json metadata safely
    from scripts.core.state_store import StateStore
    proj_dir = ProjectService._get_project_dir(project_id)
    project_json_path = proj_dir / "project.json"
    project_dict = {}
    if project_json_path.exists():
        import json
        try:
            project_dict = json.loads(project_json_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return ProjectResponse(
        project=project_dict,
        manifest=manifest_dict,
        state=state_dict,
    )
