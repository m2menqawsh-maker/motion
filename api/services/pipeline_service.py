import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from scripts.security import safe_subprocess
from scripts.path_security import validate_project_id
from scripts.state_store import StateStore
from scripts.state_model import ProjectState, LifecycleState

from api.core.errors import InvalidGateError, PipelineRunningError

class PipelineService:
    # Tracking running pipelines
    _active_pipelines: Dict[str, asyncio.Lock] = {}
    
    VALID_GATES = {"asset_gate", "plan_gate", "taste_gate", "qc_gate"}
    
    STAGE_TO_LIFECYCLE = {
        "0": LifecycleState.ASSETS_READY,
        "1": LifecycleState.PLAN_READY,
        "2": LifecycleState.BLUEPRINT_READY,
        "3": LifecycleState.RENDERED
    }
    
    GATE_TO_LIFECYCLE = {
        "gate_1": LifecycleState.ASSETS_READY,
        "gate_2": LifecycleState.PLAN_READY,
        "gate_3": LifecycleState.BLUEPRINT_READY,
        "gate_4": LifecycleState.REVIEW_APPROVED
    }

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        return Path(f"projects/{project_id}")
    
    @classmethod
    def _format_legacy_state(cls, state: ProjectState) -> dict:
        # Simulate legacy format for the frontend
        # LifecycleState -> current_stage string
        
        lifecycle_to_stage_name = {
            LifecycleState.DRAFT: "asset_gate",
            LifecycleState.ASSETS_READY: "plan_gate",
            LifecycleState.PLAN_READY: "taste_gate",
            LifecycleState.BLUEPRINT_READY: "qc_gate",
            LifecycleState.MATERIALIZED: "qc_gate",
            LifecycleState.PROBE_PASSED: "qc_gate",
            LifecycleState.AWAITING_REVIEW: "qc_gate",
            LifecycleState.REVIEW_APPROVED: "qc_gate",
            LifecycleState.RENDERED: "qc_gate",
            LifecycleState.FINAL_QC_PASSED: "qc_gate",
            LifecycleState.COMPLETE: "qc_gate",
            LifecycleState.FAILED: "asset_gate",
            LifecycleState.CANCELLED: "asset_gate"
        }
        
        current_stage_name = lifecycle_to_stage_name.get(state.lifecycle_state, "asset_gate")
        
        status = "started"
        if state.lifecycle_state in [LifecycleState.FAILED]:
            status = "failed"
        elif state.lifecycle_state in [LifecycleState.REVIEW_APPROVED, LifecycleState.COMPLETE]:
            status = "locked"

        res = {
            "status": status,
            "current_stage": current_stage_name
        }
        
        if state.approval_metadata.get("approved_by"):
            res["approved_by"] = state.approval_metadata["approved_by"]
            
        res["state"] = state.model_dump(mode='json') if hasattr(state, "model_dump") else state.dict()
        return res

    @classmethod
    async def scaffold_project(cls, project_id: str) -> dict:
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id, lifecycle_state=LifecycleState.DRAFT)
            StateStore.save(project_dir, state)
        
        res = cls._format_legacy_state(state)
        return {"status": "success", "message": f"Project {project_id} pipeline initialized", "state": res}

    @classmethod
    async def get_status(cls, project_id: str) -> dict:
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
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        state.updated_at = datetime.now(timezone.utc).isoformat()
        StateStore.save(project_dir, state)
        return cls._format_legacy_state(state)

    @classmethod
    async def finish_stage(cls, project_id: str, stage: str) -> dict:
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        
        state = StateStore.load(project_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        # Very rough mapping to move the lifecycle state forward
        if str(stage) in cls.STAGE_TO_LIFECYCLE:
            state.lifecycle_state = cls.STAGE_TO_LIFECYCLE[str(stage)]
            
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
        
        async with cls._get_lock(project_id):
            state = StateStore.load(project_dir)
            if not state:
                state = ProjectState(project_id=project_id)
            
            if str(gate) in cls.GATE_TO_LIFECYCLE:
                state.lifecycle_state = cls.GATE_TO_LIFECYCLE[str(gate)]
            
            state.approval_metadata["approved_by"] = approved_by
            state.approval_metadata["approved_at"] = datetime.now(timezone.utc).isoformat()
            state.updated_at = datetime.now(timezone.utc).isoformat()
            
            StateStore.save(project_dir, state)
        return cls._format_legacy_state(state)

    @classmethod
    async def run_pipeline(cls, project_id: str) -> dict:
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
            
            state = StateStore.load(project_dir)
            res = cls._format_legacy_state(state) if state else {}
            
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
        if project_id in cls._active_pipelines and cls._active_pipelines[project_id].locked():
            return {"status": "error", "message": "Cancellation not natively supported yet. Kill process manually."}
        return {"status": "idle", "message": "No active pipeline to cancel."}
