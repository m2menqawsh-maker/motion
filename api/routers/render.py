"""
Legacy Render Router (Deprecated Adapter).

Maintained temporarily for backward compatibility.
Calls canonical RunService to persist a durable Run record instead of executing
untracked BackgroundTasks.

Canonical endpoint: POST /projects/{project_id}/runs
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Response
from scripts.security.path_security import validate_project_id
from api.websocket import manager
from api.schemas import StandardResponse
from api.core.auth import require_permission, Principal, Action
from api.services.run_service import RunService

router = APIRouter()


@router.websocket("/{project_id}/ws")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    project_id = validate_project_id(project_id)
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)


@router.post(
    "/{project_id}",
    response_model=StandardResponse,
    deprecated=True,
    summary="Trigger pipeline run (Deprecated)",
    description="Deprecated adapter. Dispatches a durable Run via RunService. Use POST /projects/{project_id}/runs instead.",
)
async def render(
    project_id: str,
    response: Response,
    principal: Principal = Depends(require_permission(Action.RENDER_TRIGGER)),
):
    project_id = validate_project_id(project_id)

    # Enqueue canonical durable Run record through RunService (No BackgroundTasks)
    run_record, _ = RunService.create_run(project_id)

    response.headers["Deprecation"] = "@deprecated: Use POST /projects/{project_id}/runs"
    response.headers["X-Run-ID"] = run_record.run_id

    return StandardResponse(
        status="rendering",
        message="Render job queued (deprecated: use POST /projects/{project_id}/runs)"
    )
