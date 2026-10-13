"""
Domain Service for Projects and Canonical Lifecycle Projection (S22 - LED-069, LED-070, LED-071).

Provides:
- Non-blocking project creation via asyncio.to_thread
- Scoped project listing respecting Principal authorization
- Canonical LifecycleDTO projection combining StateStore, ReviewService, RunRepository, and ArtifactService
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("clean_video.api.project_service")

from api.core.errors import APIError, ProjectNotFoundError
from api.schemas.lifecycle import LifecycleDTO
from api.schemas.run import RunResponse
from api.services.scaffold_service import create_project as sync_scaffold_create
from scripts.core.database import TenantSecurityError
from scripts.core.review_service import ReviewService
from scripts.core.run_repository import RunRepository
from scripts.core.security.principal import Principal
from scripts.core.state_model import LifecycleState, ProjectState
from scripts.core.state_store import StateCorruptedError, StateStore
from scripts.security.path_security import validate_project_id


class ProjectService:
    """Domain service for project creation, queries, and lifecycle projection."""

    @classmethod
    def _get_project_dir(cls, project_id: str, workspace_id: Optional[str] = None) -> Path:
        from scripts.security.path_security import resolve_project_dir
        if not workspace_id:
            try:
                workspace_id = cls.get_project_workspace_id(project_id)
            except Exception:
                pass
        from scripts.security.path_security import TenantSecurityError
        try:
            proj_dir = resolve_project_dir(project_id, workspace_id=workspace_id)
        except TenantSecurityError as e:
            if "workspace_id is strictly required" in str(e):
                raise ProjectNotFoundError(project_id)
            raise
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        return proj_dir

    @classmethod
    async def create_project_async(
        cls,
        name: str,
        language: str,
        workspace_id: Optional[str] = None,
        created_by: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> str:
        """
        Creates a new project without blocking the asyncio event loop (LED-070).
        """
        # Execute synchronous scaffolding subprocess in worker thread pool
        res_project_id = await asyncio.to_thread(
            sync_scaffold_create, name, language, workspace_id, created_by, project_id
        )
        return res_project_id

    @classmethod
    async def create_managed_project(
        cls,
        name: str,
        language: str,
        principal: Principal,
        requested_workspace_id: Optional[str] = None,
    ) -> str:
        """
        Manages end-to-end multi-tenant project creation, filesystem scaffolding,
        relational database registration, and state synchronization.
        """
        from fastapi import HTTPException, status
        import uuid
        import shutil
        from scripts.core.database import get_database_engine, TenantRepository
        from scripts.core.security.permissions import ROLE_PERMISSIONS_MATRIX, AccessDeniedError, Action

        try:
            repo = TenantRepository(get_database_engine())
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable."
            )

        if requested_workspace_id:
            try:
                membership = repo.get_membership(requested_workspace_id, principal.principal_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service temporarily unavailable during workspace verification."
                )
            if not membership and not (principal.is_admin and principal.auth_method == "INTERNAL_SYSTEM"):
                raise AccessDeniedError(
                    principal_id=principal.principal_id,
                    action=Action.PROJECT_CREATE,
                    project_id=None,
                    reason=f"Principal '{principal.principal_id}' is not an active member of workspace '{requested_workspace_id}'."
                )
            if membership and Action.PROJECT_CREATE not in ROLE_PERMISSIONS_MATRIX.get(membership.role, set()):
                raise AccessDeniedError(
                    principal_id=principal.principal_id,
                    action=Action.PROJECT_CREATE,
                    project_id=None,
                    reason=f"Role '{membership.role.value}' does not grant 'project:create'."
                )
            target_workspace_id = requested_workspace_id
        else:
            # Resolve from user's active workspaces
            try:
                user_workspaces = repo.list_user_workspaces(principal.principal_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service temporarily unavailable during workspace lookup."
                )
            valid_workspaces = [
                (ws, role) for ws, role in user_workspaces
                if Action.PROJECT_CREATE in ROLE_PERMISSIONS_MATRIX.get(role, set())
            ]
            if len(valid_workspaces) == 1:
                target_workspace_id = valid_workspaces[0][0].id
            elif len(valid_workspaces) > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ambiguous workspace selection. Multiple eligible workspaces found; please specify 'X-Workspace-ID' header."
                )
            else:
                raise AccessDeniedError(
                    principal_id=principal.principal_id,
                    action=Action.PROJECT_CREATE,
                    project_id=None,
                    reason=f"Principal '{principal.principal_id}' is not an active member of any workspace with project creation permissions. Unmanaged project creation via HTTP API is prohibited."
                )

        from scripts.security.path_security import resolve_project_dir
        project_id = f"prj_{uuid.uuid4().hex[:8]}"
        project_dir = resolve_project_dir(project_id, workspace_id=target_workspace_id, create=False)

        # 1. Scaffolding project filesystem
        try:
            await cls.create_project_async(
                name,
                language,
                workspace_id=target_workspace_id,
                created_by=principal.principal_id,
                project_id=project_id,
            )
        except Exception as scaffold_exc:
            if project_dir.exists() and project_dir.name == project_id and project_id.startswith("prj_"):
                shutil.rmtree(project_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to scaffold project filesystem: {scaffold_exc}"
            )

        # 2. Database registration in parent process
        try:
            repo.create_project(
                project_id=project_id,
                workspace_id=target_workspace_id,
                name=name,
                created_by=principal.principal_id,
            )
        except Exception:
            if project_dir.exists() and project_dir.name == project_id and project_id.startswith("prj_"):
                shutil.rmtree(project_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable during project registration."
            )

        # 3. State sync in parent process
        try:
            state = StateStore.load(project_dir)
            if state:
                StateStore._sync_to_db(state)
        except Exception:
            try:
                repo.delete_project(project_id)
            except Exception:
                pass
            if project_dir.exists() and project_dir.name == project_id and project_id.startswith("prj_"):
                shutil.rmtree(project_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable during project state synchronization."
            )

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

        # Also inspect on-disk projects under tenant workspaces
        projects_dir = Path("projects")
        if projects_dir.exists():
            for ws_id in user_workspace_ids:
                ws_dir = projects_dir / ws_id
                if ws_dir.exists() and ws_dir.is_dir():
                    for d in ws_dir.iterdir():
                        if d.is_dir() and d.name.startswith("prj_"):
                            accessible_projects.add(d.name)
            if principal.is_admin:
                for ws_dir in projects_dir.iterdir():
                    if ws_dir.is_dir() and not ws_dir.name.startswith("."):
                        for d in ws_dir.iterdir():
                            if d.is_dir() and d.name.startswith("prj_"):
                                accessible_projects.add(d.name)

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

        # Check tenant directories on disk
        projects_dir = Path("projects")
        if projects_dir.exists():
            for ws_dir in projects_dir.iterdir():
                if ws_dir.is_dir() and not ws_dir.name.startswith("."):
                    cand = ws_dir / project_id
                    if cand.exists() and cand.is_dir():
                        return ws_dir.name

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
        validate_project_id(project_id)
        ws_id = cls.get_project_workspace_id(project_id)
        proj_dir: Optional[Path] = None
        state: Optional[ProjectState] = None
        try:
            if ws_id:
                proj_dir = cls._get_project_dir(project_id, workspace_id=ws_id)
            else:
                proj_dir = cls._get_project_dir(project_id)
            if proj_dir and proj_dir.exists():
                state = StateStore.load(proj_dir)
        except (ProjectNotFoundError, TenantSecurityError):
            proj_dir = None
            state = None

        # In multi-tenant environments, check database for authoritative state
        try:
            from scripts.core.database import get_database_engine
            engine = get_database_engine()
            if engine:
                with engine.get_connection() as conn:
                    cur = conn.execute(
                        "SELECT revision, lifecycle_state, state_json, workspace_id FROM project_states WHERE project_id = ?",
                        (project_id,)
                    )
                    row = cur.fetchone()
                    if row:
                        db_rev, db_lc, db_state_json, db_ws_id = row[0], row[1], row[2], row[3]
                        # Security: If disk state has a workspace_id, DB workspace_id must match to prevent cross-tenant state pollution
                        if state and getattr(state, "workspace_id", None) and db_ws_id and state.workspace_id != db_ws_id:
                            logger.error(
                                f"Tenant mismatch for project '{project_id}': disk={state.workspace_id}, db={db_ws_id}"
                            )
                            raise TenantSecurityError(
                                f"Tenant mismatch for project '{project_id}': disk='{state.workspace_id}', db='{db_ws_id}'"
                            )

                        if not state or db_rev > state.revision:
                            db_state: Optional[ProjectState] = None
                            if db_state_json:
                                try:
                                    db_data = json.loads(db_state_json)
                                    db_data["revision"] = db_rev
                                    db_data["lifecycle_state"] = db_lc
                                    if db_ws_id and not db_data.get("workspace_id"):
                                        db_data["workspace_id"] = db_ws_id
                                    db_state = ProjectState.model_validate(db_data)
                                except Exception as val_err:
                                    logger.error(f"Failed to parse DB state_json for project '{project_id}': {val_err}")
                                    if not state:
                                        raise StateCorruptedError(
                                            proj_dir,
                                            reason=f"Authoritative database state is corrupted: {val_err}"
                                        ) from val_err
                            if db_state:
                                state = db_state
                            elif not state:
                                state = ProjectState(
                                    project_id=project_id,
                                    revision=db_rev,
                                    lifecycle_state=LifecycleState(db_lc),
                                    workspace_id=db_ws_id,
                                )
        except (TenantSecurityError, StateCorruptedError):
            raise
        except Exception as exc:
            logger.error(f"Database error in get_lifecycle_dto for project '{project_id}': {exc}")
            if not state:
                raise APIError(f"Database error loading project '{project_id}': {exc}", status_code=500) from exc

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
            artifacts_status[rec.path] = rec.status.value if hasattr(rec.status, "value") else str(rec.status)

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
