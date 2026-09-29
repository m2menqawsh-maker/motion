import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from scripts.security.security import safe_subprocess
from scripts.security.path_security import validate_project_id
from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState, LifecycleState

from api.core.errors import (
    InvalidGateError,
    InvalidStageError,
    UnsupportedGateOperationError,
    PipelineRunningError,
    ProjectNotFoundError,
)
from scripts.core.lifecycle_service import LifecyclePreconditionFailedError

class PipelineService:
    # Tracking running pipelines
    _active_pipelines: Dict[str, asyncio.Lock] = {}
    
    VALID_GATES = {"asset_gate", "plan_gate", "taste_gate", "qc_gate"}
    VALID_STAGES = {"asset_gate", "plan_gate", "taste_gate", "qc_gate"}

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
            state = StateStore.create(project_dir, project_id)
        
        res = cls._format_legacy_state(state)
        return {"status": "success", "message": f"Project {project_id} pipeline initialized", "state": res}

    @classmethod
    async def get_status(cls, project_id: str) -> dict:
        validate_project_id(project_id)
        project_dir = cls._get_project_dir(project_id)
        from scripts.core.state_store import StateCorruptedError
        try:
            state = StateStore.load(project_dir)
        except StateCorruptedError as e:
            # Check for legacy GUI state adapter fallback
            state_file = Path(project_dir) / StateStore.STATE_FILE
            if state_file.exists():
                try:
                    content = state_file.read_text(encoding="utf-8")
                    raw = json.loads(content)
                    if "legacy_gui_state" in raw and isinstance(raw["legacy_gui_state"], dict):
                        return raw["legacy_gui_state"]
                except Exception:
                    pass
            raise

        if not state:
            return {"status": "pending", "current_stage": "asset_gate"}
            
        return cls._format_legacy_state(state)

    @classmethod
    async def start_stage(cls, project_id: str, stage: str) -> dict:
        validate_project_id(project_id)
        if stage not in cls.VALID_STAGES:
            raise InvalidStageError(stage)

        project_dir = cls._get_project_dir(project_id)
        state = StateStore.load(project_dir)
        if not state:
            raise ProjectNotFoundError(project_id)

        raise UnsupportedGateOperationError(
            operation="start_stage",
            reason=(
                f"Direct stage triggering for '{stage}' via legacy start endpoint is not supported. "
                "Stages are executed automatically via pipeline runs."
            )
        )

    @classmethod
    async def finish_stage(cls, project_id: str, stage: str) -> dict:
        validate_project_id(project_id)
        if stage not in cls.VALID_STAGES:
            raise InvalidStageError(stage)

        project_dir = cls._get_project_dir(project_id)
        state = StateStore.load(project_dir)
        if not state:
            raise ProjectNotFoundError(project_id)

        # Direct stage completion via API without gate execution evidence is forbidden.
        # S03 Rule: No proof -> no lifecycle advancement.
        raise LifecyclePreconditionFailedError(
            target_state=f"stage_{stage}",
            reason=f"Direct completion of stage '{stage}' via API is forbidden. Lifecycle advancement requires verified gate execution evidence."
        )

    @classmethod
    def _get_lock(cls, project_id: str) -> asyncio.Lock:
        if project_id not in cls._active_pipelines:
            cls._active_pipelines[project_id] = asyncio.Lock()
        return cls._active_pipelines[project_id]

    @classmethod
    async def approve_gate(cls, project_id: str, gate: str, approved_by: str = None, principal: Any = None) -> dict:
        validate_project_id(project_id)
        if gate not in cls.VALID_GATES:
            raise InvalidGateError(gate)

        project_dir = cls._get_project_dir(project_id)
        state = StateStore.load(project_dir)
        if not state:
            raise ProjectNotFoundError(project_id)

        if gate == "qc_gate":
            from scripts.core.review_service import ReviewService, create_local_trusted_principal
            from scripts.core.security.principal import Principal
            eff_principal = principal if isinstance(principal, Principal) else create_local_trusted_principal(approved_by or "api_reviewer")
            active_bundle = state.get_active_review_bundle()
            if not active_bundle or active_bundle.status != "ACTIVE":
                active_bundle = ReviewService.create_review_bundle(project_dir)
            decision = ReviewService.approve(project_dir, active_bundle.review_bundle_id, principal=eff_principal)
            return {
                "decision_id": decision.decision_id,
                "review_bundle_id": decision.review_bundle_id,
                "decision": decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision),
                "actor_id": decision.actor_id,
                "decided_at": decision.decided_at,
            }

        # Legacy fake approval eliminated (S04 Final Closure).
        raise UnsupportedGateOperationError(
            operation="approve_gate",
            reason="Gate approval is unsupported via legacy Gate API. Durable review decisions require ReviewService (S09)."
        )

    @classmethod
    async def reject_gate(cls, project_id: str, gate: str, by: str = None, note: str = "", principal: Any = None) -> dict:
        validate_project_id(project_id)
        if gate not in cls.VALID_GATES:
            raise InvalidGateError(gate)

        project_dir = cls._get_project_dir(project_id)
        state = StateStore.load(project_dir)
        if not state:
            raise ProjectNotFoundError(project_id)

        if gate == "qc_gate":
            from scripts.core.review_service import ReviewService, create_local_trusted_principal
            from scripts.core.security.principal import Principal
            eff_principal = principal if isinstance(principal, Principal) else create_local_trusted_principal(by or "api_reviewer")
            active_bundle = state.get_active_review_bundle()
            if not active_bundle or active_bundle.status != "ACTIVE":
                active_bundle = ReviewService.create_review_bundle(project_dir)
            decision = ReviewService.reject(project_dir, active_bundle.review_bundle_id, principal=eff_principal, reason=note or "Rejected via API")
            return {
                "decision_id": decision.decision_id,
                "review_bundle_id": decision.review_bundle_id,
                "decision": decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision),
                "actor_id": decision.actor_id,
                "reason": decision.reason,
            }

        raise UnsupportedGateOperationError(
            operation="reject_gate",
            reason="Gate rejection is not supported. Durable review decisions require ReviewService (S09)."
        )

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
            from scripts.core.project_lock import ProjectExecutionLock, ProjectExecutionConflictError
            
            run_id = str(uuid.uuid4())
            execution_lock = ProjectExecutionLock(project_dir, owner_id="api", run_id=run_id)
            try:
                execution_lock.acquire()
            except ProjectExecutionConflictError:
                raise PipelineRunningError(project_id)

            try:
                env = os.environ.copy()
                env["AGY_RUN_ID"] = run_id
                env["AGY_IS_MANAGED"] = "1"

                func = functools.partial(
                    safe_subprocess,
                    [sys.executable, "scripts/pipeline.py", project_id],
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
            finally:
                execution_lock.release()

    @classmethod
    async def cancel_pipeline(cls, project_id: str) -> dict:
        if project_id in cls._active_pipelines and cls._active_pipelines[project_id].locked():
            return {"status": "error", "message": "Cancellation not natively supported yet. Kill process manually."}
        return {"status": "idle", "message": "No active pipeline to cancel."}

    @classmethod
    def mutate_blueprint(cls, project_id: str, payload: dict, actor_id: str = "api_user") -> None:
        project_dir = Path(f"projects/{project_id}")
        if not project_dir.exists():
            project_dir = cls._get_project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)

        from scripts.core.artifact_service import ArtifactService
        from scripts.core.dependency_graph import ArtifactKind

        state_file = project_dir / ".pipeline_state.json"
        content_str = json.dumps(payload, ensure_ascii=False, indent=2)
        if state_file.exists():
            ArtifactService.mutate_artifact(
                project_dir=project_dir,
                artifact_kind=ArtifactKind.BLUEPRINT,
                new_content=content_str,
                reason=f"Blueprint updated via API by {actor_id}",
            )
        else:
            filepath = project_dir / "05_blueprint.json"
            filepath.write_text(content_str, encoding="utf-8")

    @classmethod
    def get_manifest(cls, project_id: str) -> Optional[Dict[str, Any]]:
        project_dir = cls._get_project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)
        manifest_path = project_dir / "02_asset_manifest.json"
        if not manifest_path.exists():
            return None
        from scripts.core.manifest_loader import load_manifest
        mf = load_manifest(manifest_path, expected_project_id=project_id, allow_migrate=True)
        return mf.to_dict()

    @classmethod
    def get_blueprint(cls, project_id: str) -> Optional[Dict[str, Any]]:
        project_dir = Path(f"projects/{project_id}")
        if not project_dir.exists():
            project_dir = cls._get_project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)
        blueprint_path = project_dir / "05_blueprint.json"
        if not blueprint_path.exists():
            return None
        from scripts.core.blueprint_loader import load_blueprint
        bp = load_blueprint(blueprint_path, expected_project_id=project_id, allow_migrate=True)
        return bp.to_dict()

    @classmethod
    def validate_blueprint_payload(cls, project_id: str, payload: dict) -> tuple[bool, list[str]]:
        project_dir = Path(f"projects/{project_id}")
        if not project_dir.exists():
            project_dir = cls._get_project_dir(project_id)
        if not project_dir.exists():
            raise ProjectNotFoundError(project_id)
        from scripts.core.blueprint_validator import validate_blueprint_v2
        from scripts.core.blueprint_migration import is_legacy_blueprint_v1, migrate_blueprint_to_v2
        from scripts.core.manifest_loader import load_manifest
        man = None
        manifest_path = project_dir / "02_asset_manifest.json"
        if manifest_path.exists():
            try:
                man = load_manifest(manifest_path, expected_project_id=project_id, allow_migrate=True)
            except Exception:
                pass
        migrated = payload
        if is_legacy_blueprint_v1(payload):
            migrated = migrate_blueprint_to_v2(payload, project_id=project_id)
        v_res = validate_blueprint_v2(migrated, expected_project_id=project_id, manifest=man)
        return v_res.ok, v_res.errors


