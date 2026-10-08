"""
Projects API Router (S22 - LED-069, LED-070, LED-071).

HTTP transport layer for project lifecycle, creation, listing, and state query:
- Non-blocking project creation via ProjectService.create_project_async
- Canonical LifecycleDTO projection endpoint: GET /projects/{project_id}/state
- Zero raw file reads or subprocess invocations inside router functions
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    request: Request,
    req: ProjectCreateRequest,
    principal: Principal = Depends(require_permission(Action.PROJECT_CREATE)),
):
    ws_id = request.headers.get("X-Workspace-ID")
    target_workspace_id = None

    from scripts.core.database import get_database_engine, TenantRepository
    from scripts.core.security.permissions import ROLE_PERMISSIONS_MATRIX, AccessDeniedError
    try:
        repo = TenantRepository(get_database_engine())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable."
        )

    if ws_id:
        try:
            membership = repo.get_membership(ws_id, principal.principal_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable during workspace verification."
            )
        if not membership and not (principal.is_admin and principal.auth_method == "INTERNAL_SYSTEM"):
            raise AccessDeniedError(
                principal_id=principal.principal_id,
                action=Action.PROJECT_CREATE,
                project_id=None,
                reason=f"Principal '{principal.principal_id}' is not an active member of workspace '{ws_id}'."
            )
        if membership and Action.PROJECT_CREATE not in ROLE_PERMISSIONS_MATRIX.get(membership.role, set()):
            raise AccessDeniedError(
                principal_id=principal.principal_id,
                action=Action.PROJECT_CREATE,
                project_id=None,
                reason=f"Role '{membership.role.value}' does not grant 'project:create'."
            )
        target_workspace_id = ws_id
    else:
        # Resolve from user's active workspaces
        try:
            user_workspaces = repo.list_user_workspaces(principal.principal_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable during workspace lookup."
            )
        valid_workspaces = [
            (ws, role) for ws, role in user_workspaces
            if Action.PROJECT_CREATE in ROLE_PERMISSIONS_MATRIX.get(role, set())
        ]
        if len(valid_workspaces) == 1:
            target_workspace_id = valid_workspaces[0][0].id
        elif len(valid_workspaces) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ambiguous workspace selection. Multiple eligible workspaces found; please specify 'X-Workspace-ID' header."
            )
        else:
            raise AccessDeniedError(
                principal_id=principal.principal_id,
                action=Action.PROJECT_CREATE,
                project_id=None,
                reason=f"Principal '{principal.principal_id}' is not an active member of any workspace with project creation permissions. Unmanaged project creation via HTTP API is prohibited."
            )

    import uuid
    import shutil
    from pathlib import Path
    from scripts.core.state_store import StateStore

    project_id = f"prj_{uuid.uuid4().hex[:8]}"
    project_dir = Path(f"projects/{project_id}")

    # 1. Scaffolding project filesystem
    try:
        await ProjectService.create_project_async(
            req.name,
            req.language,
            workspace_id=target_workspace_id,
            created_by=principal.principal_id,
            project_id=project_id,
        )
    except Exception as scaffold_exc:
        if project_dir.exists() and project_dir.name == project_id and project_id.startswith("prj_"):
            shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scaffold project filesystem: {scaffold_exc}"
        )

    # 2. Database registration in parent process
    try:
        repo.create_project(
            project_id=project_id,
            workspace_id=target_workspace_id,
            name=req.name,
            created_by=principal.principal_id,
        )
    except Exception:
        if project_dir.exists() and project_dir.name == project_id and project_id.startswith("prj_"):
            shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable during project registration."
        )

    # 3. State sync in parent process
    try:
        state = StateStore.load(project_dir)
        if state:
            StateStore._sync_to_db(state)
    except Exception:
        try:
            repo.delete_project(project_id)
        except Exception:
            pass
        if project_dir.exists() and project_dir.name == project_id and project_id.startswith("prj_"):
            shutil.rmtree(project_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service temporarily unavailable during project state synchronization."
        )

    return ProjectCreateResponse(project_id=project_id)


@router.get("/", response_model=ProjectListResponse, summary="List accessible projects")
async def list_projects(
    request: Request,
    principal: Principal = Depends(require_permission(Action.PROJECT_READ)),
):
    ws_id = request.headers.get("X-Workspace-ID")
    projects_list = ProjectService.list_projects(principal, workspace_id=ws_id)
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
