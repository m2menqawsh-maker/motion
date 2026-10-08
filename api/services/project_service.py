"""
Domain Service for Projects and Canonical Lifecycle Projection (S22 - LED-069, LED-070, LED-071).

Provides:
- Non-blocking project creation via asyncio.to_thread
- Scoped project listing respecting Principal authorization
- Canonical LifecycleDTO projection combining StateStore, ReviewService, RunRepository, and ArtifactService
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from api.core.errors import ProjectNotFoundError
from api.schemas.lifecycle import LifecycleDTO
from api.schemas.run import RunResponse
from api.services.scaffold_service import create_project as sync_scaffold_create
from scripts.core.review_service import ReviewService
from scripts.core.run_repository import RunRepository
from scripts.core.security.principal import Principal
from scripts.core.state_model import LifecycleState
from scripts.core.state_store import StateStore
from scripts.security.path_security import validate_project_id


class ProjectService:
    """Domain service for project creation, queries, and lifecycle projection."""

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        validate_project_id(project_id)
        proj_dir = Path(f"projects/{project_id}")
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        return proj_dir

    @classmethod
    async def create_project_async(cls, name: str, language: str) -> str:
        """
        Creates a new project without blocking the asyncio event loop (LED-070).
        """
        # Execute synchronous scaffolding subprocess in worker thread pool
        project_id = await asyncio.to_thread(sync_scaffold_create, name, language)
        return project_id

    @classmethod
    def list_projects(cls, principal: Principal, workspace_id: Optional[str] = None) -> List[str]:
        """Lists projects accessible to the given principal under tenant confinement."""
        user_workspace_ids = set()
        if workspace_id:
            user_workspace_ids.add(workspace_id)
        else:
            try:
                from scripts.core.database import get_database_engine, TenantRepository
                repo = TenantRepository(get_database_engine())
                workspaces = repo.list_user_workspaces(principal.principal_id)
                for ws, role in workspaces:
                    user_workspace_ids.add(ws.id)
            except Exception:
                pass

        accessible_projects = set()

        # If user has workspaces in DB, query DB registered projects for those workspaces
        if user_workspace_ids:
            try:
                from scripts.core.database import get_database_engine, TenantRepository
                repo = TenantRepository(get_database_engine())
                for ws_id in user_workspace_ids:
                    records = repo.list_projects_for_workspace(ws_id)
                    for r in records:
                        accessible_projects.add(r.id)
            except Exception:
                pass

        # Also inspect on-disk projects
        projects_dir = Path("projects")
        if projects_dir.exists():
            for d in projects_dir.iterdir():
                if d.is_dir() and d.name.startswith("prj_"):
                    p_id = d.name
                    owner_ws = cls.get_project_workspace_id(p_id)
                    if owner_ws:
                        if owner_ws in user_workspace_ids:
                            accessible_projects.add(p_id)
                    else:
                        # Truly unmanaged standalone project
                        if principal.is_admin:
                            accessible_projects.add(p_id)
                        elif principal.project_scopes and (p_id in principal.project_scopes or "*" in principal.project_scopes):
                            accessible_projects.add(p_id)

        # Filter by project_scopes if defined and not wildcard
        if principal.project_scopes and "*" not in principal.project_scopes:
            accessible_projects = {p for p in accessible_projects if p in principal.project_scopes}

        return sorted(list(accessible_projects))

    @classmethod
    def get_project_workspace_id(cls, project_id: str) -> Optional[str]:
        """Domain resolution of the workspace owning a project (S24.5 / S27.9)."""
        validate_project_id(project_id)
        # Check relational database tenant registry first
        try:
            from scripts.core.database import get_database_engine, TenantRepository
            repo = TenantRepository(get_database_engine())
            proj_rec = repo.get_project(project_id)
            if proj_rec:
                return proj_rec.workspace_id
        except Exception:
            pass

        # Check local state store if project directory exists
        try:
            proj_dir = cls._get_project_dir(project_id)
            state = StateStore.load(proj_dir)
            if state and getattr(state, "workspace_id", None):
                return state.workspace_id
        except Exception:
            pass

        return None

    @classmethod
    def is_project_accessible_by_tenant(
        cls,
        project_id: str,
        workspace_id: str,
        is_admin: bool = False,
        actor_id: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Domain boundary verifying if a project belongs to or is accessible by the tenant/actor.
        Returns (is_accessible, rejection_reason).
        """
        validate_project_id(project_id)

        owner_ws = cls.get_project_workspace_id(project_id)
        if owner_ws is not None:
            if owner_ws != workspace_id:
                return False, (
                    f"Cross-tenant access violation: Target project '{project_id}' belongs to "
                    f"workspace '{owner_ws}', but caller belongs to '{workspace_id}'."
                )

            if actor_id is not None:
                try:
                    from scripts.core.database import get_database_engine, TenantRepository
                    repo = TenantRepository(get_database_engine())
                    membership = repo.get_membership(owner_ws, actor_id)
                    if membership is None:
                        return False, f"Actor '{actor_id}' is not an active member of workspace '{owner_ws}'."
                except Exception as e:
                    return False, f"Database error verifying workspace membership: {e}"

            return True, None

        # If project has no known workspace (unregistered or unmanaged), fail closed in tenant context
        return False, f"Project '{project_id}' does not belong to a verified workspace."

    @classmethod
    def get_lifecycle_dto(cls, project_id: str, db_path: Optional[Path | str] = None) -> LifecycleDTO:
        """
        Derives the canonical, un-degraded LifecycleDTO projection (LED-071).
        """
        proj_dir = cls._get_project_dir(project_id)
        state = StateStore.load(proj_dir)
        if not state:
            raise ProjectNotFoundError(project_id)

        # 1. Review status projection
        review_dto = ReviewService.get_review_status(project_id)

        # 2. Latest run projection
        repo = RunRepository(db_path=db_path)
        recent_runs = repo.list_runs(project_id=project_id, limit=1)
        latest_run_dict = None
        if recent_runs:
            latest_run_dict = RunResponse.from_record(recent_runs[0]).model_dump()

        # 3. Artifact records mapping
        artifacts_status = {}
        for rec in state.artifact_records:
            artifacts_status[rec.path] = rec.status.value

        # 4. Derivation of allowed actions
        lstate = state.lifecycle_state
        allowed_actions = []

        if lstate == LifecycleState.DRAFT:
            allowed_actions = ["asset:upload", "project:edit", "blueprint:edit"]
        elif lstate == LifecycleState.ASSETS_READY:
            allowed_actions = ["asset:upload", "blueprint:edit", "run:execute"]
        elif lstate in (LifecycleState.PLAN_READY, LifecycleState.BLUEPRINT_READY, LifecycleState.MATERIALIZED, LifecycleState.PROBE_PASSED):
            allowed_actions = ["blueprint:edit", "run:execute", "qc:view"]
        elif lstate == LifecycleState.AWAITING_REVIEW:
            allowed_actions = ["review:approve", "review:reject", "qc:view"]
        elif lstate == LifecycleState.REVIEW_APPROVED:
            allowed_actions = ["render:trigger", "run:execute", "render:read"]
        elif lstate in (LifecycleState.RENDERED, LifecycleState.FINAL_QC_PASSED, LifecycleState.COMPLETE):
            allowed_actions = ["render:read", "qc:view", "project:read"]
        elif lstate == LifecycleState.FAILED:
            allowed_actions = ["run:execute", "blueprint:edit", "asset:upload"]

        # 5. Derivation of blocking reason
        blocked_reason = None
        lease = repo.get_active_project_lease(project_id)
        if lease:
            blocked_reason = f"Project is currently executing run '{lease.get('run_id')}'. Execution lock active."
        elif lstate == LifecycleState.AWAITING_REVIEW:
            blocked_reason = "Awaiting formal human review decision before rendering can be authorized."
        elif lstate == LifecycleState.FAILED:
            blocked_reason = "Project pipeline reached FAILED state. Remediation or retry required."

        return LifecycleDTO(
            project_id=project_id,
            lifecycle_state=lstate.value if hasattr(lstate, "value") else str(lstate),
            revision=state.revision,
            allowed_actions=allowed_actions,
            blocked_reason=blocked_reason,
            review=review_dto.model_dump(),
            latest_run=latest_run_dict,
            artifacts_status=artifacts_status,
        )
