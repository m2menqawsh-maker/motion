from scripts.path_security import validate_project_id
import subprocess
from scripts.security import safe_subprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from api.services.render_service import render_project_async
from api.websocket import manager
import asyncio

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

@router.post("/{project_id}")
async def render(project_id: str, background_tasks: BackgroundTasks):
    project_id = validate_project_id(project_id)
    background_tasks.add_task(render_project_async, project_id, manager)
    return {"status": "rendering"}
