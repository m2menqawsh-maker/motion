import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from scripts.security import safe_subprocess
from scripts.path_security import validate_project_id
from scripts.state_store import StateStore
from scripts.state_model import ProjectState, StageStatus, GateStatus

from api.core.errors import InvalidGateError, PipelineRunningError

class PipelineService:
    # Tracking running pipelines
    _active_pipelines: Dict[str, asyncio.Lock] = {}
    
    VALID_GATES = {"asset_gate", "plan_gate", "taste_gate", "qc_gate"}
    
    GATE_MAPPING = {
        "0": "gate_1", "gate_1": "gate_1", "asset_gate": "gate_1",
        "1": "gate_2", "gate_2": "gate_2", "plan_gate": "gate_2",
        "2": "gate_3", "gate_3": "gate_3", "taste_gate": "gate_3",
        "3": "gate_4", "gate_4": "gate_4", "qc_gate": "gate_4", "approval_gate": "gate_4"
    }

    STAGE_MAPPING = {
        "0": "0", "assets": "0",
        "1": "1", "plan": "1",
        "2": "2", "blueprint": "2",
        "3": "3", "render": "3", "qc": "3"
    }
    
    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        """Returns the project directory path. Can be overridden in tests."""
        return Path(f"projects/{project_id}")
    
    @classmethod
    def _format_legacy_state(cls, state: ProjectState) -> dict:
        stage_names = ["asset_gate", "plan_gate", "taste_gate", "qc_gate"]
        current = state.current_stage
        current_stage_name = stage_names[current] if 0 <= current < len(stage_names) else "asset_gate"
        
        status = "started"
        stage_status = state.stages.get(str(current))
        if stage_status and stage_status.status.value == "running":
            status = "started"
            
        gate_status = state.gates.get(f"gate_{current + 1}")
        approved_by = None
        if gate_status and gate_status.status.value == "approved":
            status = "locked"
            approved_by = gate_status.approved_by
            
        res = {
            "status": status,
            "current_stage": current_stage_name
        }
        if approved_by:
            res["approved_by"] = approved_by
            
        # Add actual state for full lifecycle test which expects state hash checks
        res["state"] = state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()
        return res

    @classmethod
    async def scaffold_project(cls, project_id: str) -> dict:
        """Initializes a new project's pipeline state."""
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            StateStore.save(project_dir, state)
        
        res = cls._format_legacy_state(state)
        return {"status": "success", "message": f"Project {project_id} pipeline initialized", "state": res}

    @classmethod
    async def get_status(cls, project_id: str) -> dict:
        """Returns the current state of the project."""
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        state = StateStore.load(project_dir)
        if not state:
            return {"status": "pending", "current_stage": "asset_gate"}
            
        return cls._format_legacy_state(state)

    @classmethod
    async def start_stage(cls, project_id: str, stage: str) -> dict:
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        
        if str(stage) not in cls.STAGE_MAPPING:
            raise InvalidGateError(f"Invalid stage: {stage}")
            
        stage_key = cls.STAGE_MAPPING[str(stage)]
        
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        state.current_stage = int(stage_key)
        state.stages[stage_key].status = StageStatus.RUNNING
        state.stages[stage_key].started_at = datetime.now(timezone.utc).isoformat()
        state.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Update current stage
        state.current_stage = int(stage_key)
        
        StateStore.save(project_dir, state)
        return cls._format_legacy_state(state)

    @classmethod
    async def finish_stage(cls, project_id: str, stage: str) -> dict:
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        
        if str(stage) not in cls.STAGE_MAPPING:
            raise InvalidGateError(f"Invalid stage: {stage}")
            
        stage_key = cls.STAGE_MAPPING[str(stage)]
        
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        state.current_stage = int(stage_key)
        state.stages[stage_key].status = StageStatus.DONE
        state.stages[stage_key].finished_at = datetime.now(timezone.utc).isoformat()
        state.updated_at = datetime.now(timezone.utc).isoformat()
        
        StateStore.save(project_dir, state)
        return cls._format_legacy_state(state)

    @classmethod
    def _get_lock(cls, project_id: str) -> asyncio.Lock:
        if project_id not in cls._active_pipelines:
            cls._active_pipelines[project_id] = asyncio.Lock()
        return cls._active_pipelines[project_id]

    @classmethod
    async def approve_gate(cls, project_id: str, gate: str, approved_by: str = None) -> dict:
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        
        if str(gate) not in cls.GATE_MAPPING:
            raise InvalidGateError(f"Invalid gate: {gate}")
            
        gate_key = cls.GATE_MAPPING[str(gate)]
        
        async with cls._get_lock(project_id):
            state = StateStore.load(project_dir)
            if not state:
                state = ProjectState(project_id=project_id)
            
            state.gates[gate_key].status = GateStatus.APPROVED
            state.gates[gate_key].approved_by = approved_by
            state.gates[gate_key].approved_at = datetime.now(timezone.utc).isoformat()
            state.updated_at = datetime.now(timezone.utc).isoformat()
            
            # Set current stage to match the approved gate
            gate_num = int(gate_key.split('_')[1])
            state.current_stage = gate_num - 1
            
            StateStore.save(project_dir, state)
        return cls._format_legacy_state(state)

    @classmethod
    async def run_pipeline(cls, project_id: str) -> dict:
        """Runs the official pipeline (scripts/pipeline.py) as a subprocess.
        The pipeline script will automatically update .pipeline_state.json directly."""
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        
        lock = cls._get_lock(project_id)
        
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
            
            res = cls._format_legacy_state(state) if state else {}
            
            # Legacy compatibility: parse state from stdout if present
            import re
            import json
            match = re.search(r"__PIPELINE_STATE__(.*?)__PIPELINE_STATE__", result.stdout, re.DOTALL)
            if match:
                try:
                    stdout_state = json.loads(match.group(1))
                    if isinstance(stdout_state, dict):
                        if "state" not in res:
                            res["state"] = {}
                        res["state"].update(stdout_state)
                except Exception:
                    pass
            
            res.update({
                "status": "success" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            })
            return res

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
