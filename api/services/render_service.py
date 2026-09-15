from scripts.path_security import validate_project_id
import asyncio
from api.websocket import ConnectionManager
from api.services.pipeline_service import PipelineService
from pathlib import Path

async def render_project_async(project_id: str, manager: ConnectionManager):
    project_id = validate_project_id(project_id)
    
    await manager.broadcast(f"STARTING PIPELINE FOR: {project_id}", project_id)
    
    try:
        result = await PipelineService.run_pipeline(project_id)
        
        # Broadcast stdout
        if result.get("stdout"):
            for line in result["stdout"].splitlines():
                if line.strip():
                    await manager.broadcast(line, project_id)
                    
        # Broadcast stderr if any
        if result.get("stderr"):
            for line in result["stderr"].splitlines():
                if line.strip():
                    await manager.broadcast(f"ERROR: {line}", project_id)
                    
        await manager.broadcast(f"DONE: exited with code {result.get('return_code')}", project_id)
    except Exception as e:
        await manager.broadcast(f"ERROR: {str(e)}", project_id)
