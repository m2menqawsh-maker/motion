import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any
from scripts.security import safe_subprocess
from scripts.path_security import validate_project_id

class PipelineAlreadyRunningException(Exception):
    pass

class InvalidGateException(Exception):
    pass

class PipelineService:
    # Tracking running pipelines
    _active_pipelines: Dict[str, asyncio.Lock] = {}
    
    VALID_GATES = {"asset_gate", "plan_gate", "taste_gate", "qc_gate"}
    
    @classmethod
    def _get_state_path(cls, project_id: str) -> Path:
        validate_project_id(project_id)
        return Path(f"projects/{project_id}/.pipeline_state.json")
        
    @classmethod
    def _load_state(cls, project_id: str) -> dict:
        path = cls._get_state_path(project_id)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}
        
    @classmethod
    def _save_state(cls, project_id: str, state: dict):
        path = cls._get_state_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    async def scaffold_project(cls, project_id: str) -> dict:
        """Initializes a new project's pipeline state."""
        state = cls._load_state(project_id)
        if "legacy_gui_state" not in state:
            state["legacy_gui_state"] = {
                "current_stage": "asset_gate",
                "status": "started",
                "approved_by": None,
                "timestamp": datetime.utcnow().isoformat()
            }
            cls._save_state(project_id, state)
        return {"status": "success", "message": f"Project {project_id} pipeline initialized"}

    @classmethod
    async def get_status(cls, project_id: str) -> dict:
        """Returns the status from the legacy_gui_state adapter for GUI clients."""
        state = cls._load_state(project_id)
        legacy = state.get("legacy_gui_state", {})
        if not legacy:
            # Fallback for uninitialized projects
            legacy = {
                "current_stage": "asset_gate",
                "status": "pending",
                "approved_by": None,
                "timestamp": None
            }
        return legacy

    @classmethod
    async def start_stage(cls, project_id: str, stage: str) -> dict:
        """Updates legacy adapter state to 'started'."""
        if stage not in cls.VALID_GATES:
            # Fallback adapter if GUI sends "1", "2", "3"
            gate_mapping = {"0": "asset_gate", "1": "plan_gate", "2": "taste_gate", "3": "qc_gate"}
            if str(stage) in gate_mapping:
                stage = gate_mapping[str(stage)]
            else:
                raise InvalidGateException(f"Invalid gate: {stage}")
                
        state = cls._load_state(project_id)
        legacy = state.get("legacy_gui_state", {})
        legacy["current_stage"] = stage
        legacy["status"] = "started"
        legacy["timestamp"] = datetime.utcnow().isoformat()
        state["legacy_gui_state"] = legacy
        
        cls._save_state(project_id, state)
        return legacy

    @classmethod
    async def finish_stage(cls, project_id: str, stage: str) -> dict:
        """Updates legacy adapter state to 'finished'."""
        if stage not in cls.VALID_GATES:
            gate_mapping = {"0": "asset_gate", "1": "plan_gate", "2": "taste_gate", "3": "qc_gate"}
            if str(stage) in gate_mapping:
                stage = gate_mapping[str(stage)]
            else:
                raise InvalidGateException(f"Invalid gate: {stage}")
                
        state = cls._load_state(project_id)
        legacy = state.get("legacy_gui_state", {})
        legacy["current_stage"] = stage
        legacy["status"] = "finished"
        legacy["timestamp"] = datetime.utcnow().isoformat()
        state["legacy_gui_state"] = legacy
        
        cls._save_state(project_id, state)
        return legacy

    @classmethod
    async def approve_gate(cls, project_id: str, gate: str, approved_by: str = None) -> dict:
        """Updates legacy adapter state to record human approval."""
        if gate not in cls.VALID_GATES:
            gate_mapping = {"0": "asset_gate", "1": "plan_gate", "2": "taste_gate", "3": "qc_gate"}
            if str(gate) in gate_mapping:
                gate = gate_mapping[str(gate)]
            else:
                raise InvalidGateException(f"Invalid gate: {gate}")
                
        state = cls._load_state(project_id)
        legacy = state.get("legacy_gui_state", {})
        legacy["current_stage"] = gate
        legacy["status"] = "locked"  # Legacy convention used 'locked' when approved
        legacy["approved_by"] = approved_by
        legacy["timestamp"] = datetime.utcnow().isoformat()
        state["legacy_gui_state"] = legacy
        
        cls._save_state(project_id, state)
        return legacy

    @classmethod
    async def run_pipeline(cls, project_id: str) -> dict:
        """Runs the official pipeline (scripts/pipeline.py) as a subprocess.
        Updates .pipeline_state.json hashes ONLY."""
        validate_project_id(project_id)
        
        if project_id not in cls._active_pipelines:
            cls._active_pipelines[project_id] = asyncio.Lock()
            
        lock = cls._active_pipelines[project_id]
        
        if lock.locked():
            raise PipelineAlreadyRunningException(f"Pipeline is already running for {project_id}")
            
        async with lock:
            # Execute pipeline in a thread to avoid blocking the event loop
            import functools
            func = functools.partial(safe_subprocess, ["python", "scripts/pipeline.py", project_id], capture_output=True, text=True)
            result = await asyncio.to_thread(func)
            
            new_hashes = {}
            if result.stdout:
                for line in result.stdout.splitlines():
                    if line.startswith("__PIPELINE_STATE__") and line.endswith("__PIPELINE_STATE__"):
                        json_str = line.replace("__PIPELINE_STATE__", "")
                        try:
                            new_hashes = json.loads(json_str)
                        except json.JSONDecodeError:
                            pass
                            
            # Merge hashes back into state, preserving legacy_gui_state
            state = cls._load_state(project_id)
            state.update(new_hashes)
            cls._save_state(project_id, state)
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "state": state
            }

    @classmethod
    async def cancel_pipeline(cls, project_id: str) -> dict:
        """
        Attempt to cancel a running pipeline.
        Note: Cancellation depends on subprocess management, which may require
        expanding safe_subprocess capabilities in the future.
        """
        # For now, it just checks lock status
        if project_id in cls._active_pipelines and cls._active_pipelines[project_id].locked():
            return {"status": "error", "message": "Cancellation not natively supported yet. Kill process manually."}
        return {"status": "idle", "message": "No active pipeline to cancel."}
