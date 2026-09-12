import subprocess
import asyncio
from api.websocket import ConnectionManager
from pathlib import Path

async def render_project_async(project_id: str, manager: ConnectionManager):
    project_dir = Path(f"projects/{project_id}")
    cmd = ["npx", "tsx", "scripts/dev_render_blueprint.ts", str(project_dir)]
    
    # Run process asynchronously
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    if process.stdout:
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode('utf-8').strip()
            if text:
                await manager.broadcast(text, project_id)

    if process.stderr:
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            text = line.decode('utf-8').strip()
            if text:
                await manager.broadcast(f"ERROR: {text}", project_id)

    await process.wait()
    await manager.broadcast(f"DONE: exited with code {process.returncode}", project_id)
