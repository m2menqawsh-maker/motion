import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
from scripts.security import safe_subprocess
from scripts.path_security import validate_project_id
from scripts.state_store import StateStore
from scripts.state_model import ProjectState, StageStatus, GateStatus

from api.core.errors import InvalidGateError, PipelineRunningError

class PipelineService:
    # Tracking running pipelines
    _active_pipelines: Dict[str, asyncio.Lock] = {}
    
    GATE_MAPPING = {
        "gate_1": "gate_1", "asset_gate": "gate_1", "plan_gate": "gate_1",
        "gate_2": "gate_2", "taste_gate": "gate_2",
        "gate_3": "gate_3", "qc_gate": "gate_3", "approval_gate": "gate_3"
    }

    STAGE_MAPPING = {
        "0": "0", "assets": "0",
        "1": "1", "plan": "1",
        "2": "2", "blueprint": "2",
        "3": "3", "render": "3", "qc": "3"
    }
    
    @classmethod
    def scaffold_project(cls, project_id: str) -> dict:
        """Initializes a new project's pipeline state."""
        validate_project_id(project_id)
        project_dir = Path(f"projects/{project_id}")
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            StateStore.save(project_dir, state)
        # Using model_dump to convert the Pydantic model to a dict, handling enum values correctly.
        return {"status": "success", "message": f"Project {project_id} pipeline initialized", "state": state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()}

    @classmethod
    def get_status(cls, project_id: str) -> dict:
        """Returns the current state of the project."""
        validate_project_id(project_id)
        project_dir = Path(f"projects/{project_id}")
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        return state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()

    @classmethod
    async def start_stage(cls, project_id: str, stage: str) -> dict:
        validate_project_id(project_id)
        project_dir = Path(f"projects/{project_id}")
        
        if str(stage) not in cls.STAGE_MAPPING:
            raise InvalidGateException(f"Invalid stage: {stage}")
            
        stage_key = cls.STAGE_MAPPING[str(stage)]
        
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        state.current_stage = int(stage_key)
        state.stages[stage_key].status = StageStatus.RUNNING
        state.stages[stage_key].started_at = datetime.utcnow().isoformat()
        state.updated_at = datetime.utcnow().isoformat()
        
        StateStore.save(project_dir, state)
        return state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()

    @classmethod
    async def finish_stage(cls, project_id: str, stage: str) -> dict:
        validate_project_id(project_id)
        project_dir = Path(f"projects/{project_id}")
        
        if str(stage) not in cls.STAGE_MAPPING:
            raise InvalidGateError(f"Invalid stage: {stage}")
            
        stage_key = cls.STAGE_MAPPING[str(stage)]
        
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        state.current_stage = int(stage_key)
        state.stages[stage_key].status = StageStatus.DONE
        state.stages[stage_key].finished_at = datetime.utcnow().isoformat()
        state.updated_at = datetime.utcnow().isoformat()
        
        StateStore.save(project_dir, state)
        return state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()

    @classmethod
    async def approve_gate(cls, project_id: str, gate: str, approved_by: str = None) -> dict:
        validate_project_id(project_id)
        project_dir = Path(f"projects/{project_id}")
        
        if str(gate) not in cls.GATE_MAPPING:
            raise InvalidGateError(f"Invalid gate: {gate}")
            
        gate_key = cls.GATE_MAPPING[str(gate)]
        
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        state.gates[gate_key].status = GateStatus.APPROVED
        state.gates[gate_key].approved_by = approved_by
        state.gates[gate_key].approved_at = datetime.utcnow().isoformat()
        state.updated_at = datetime.utcnow().isoformat()
        
        StateStore.save(project_dir, state)
        return state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()

    @classmethod
    async def run_pipeline(cls, project_id: str) -> dict:
        """Runs the official pipeline (scripts/pipeline.py) as a subprocess.
        The pipeline script will automatically update .pipeline_state.json directly."""
        validate_project_id(project_id)
        project_dir = Path(f"projects/{project_id}")
        
        if project_id not in cls._active_pipelines:
            cls._active_pipelines[project_id] = asyncio.Lock()
            
        lock = cls._active_pipelines[project_id]
        
        if lock.locked():
            raise PipelineRunningError(project_id)
            
        async with lock:
            import functools
            import uuid
            
            run_id = str(uuid.uuid4())
            env = os.environ.copy()
            env["AGY_RUN_ID"] = run_id
            env["AGY_IS_MANAGED"] = "1"
            
            func = functools.partial(
                safe_subprocess, 
                ["python", "scripts/pipeline.py", project_id], 
                capture_output=True, 
                text=True,
                env=env
            )
            result = await asyncio.to_thread(func)
            
            # State is updated directly by the subprocess, so just reload it
            state = StateStore.load(project_dir)
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "state": state.model_dump(mode='json') if (state and hasattr(state, "model_dump")) else (state.dict() if state else None)
            }

    @classmethod
    async def cancel_pipeline(cls, project_id: str) -> dict:
        """
        Attempt to cancel a running pipeline.
        Note: Cancellation depends on subprocess management, which may require
        expanding safe_subprocess capabilities in the future.
        """
        if project_id in cls._active_pipelines and cls._active_pipelines[project_id].locked():
            return {"status": "error", "message": "Cancellation not natively supported yet. Kill process manually."}
        return {"status": "idle", "message": "No active pipeline to cancel."}
