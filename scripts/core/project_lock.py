"""
Cross-Process Project Execution Lock for S21.

Ensures mutual exclusion across multiple workers, API requests, and CLI executions.
Combines OS-level kernel lock (.pipeline_execution.lock) with durable database lease.
"""

import os
from pathlib import Path
from typing import Optional
from scripts.core.state_lock import StateLock, StateLockTimeoutError
from scripts.core.run_repository import RunRepository
from scripts.security.path_security import (
    validate_project_id,
    validate_workspace_id,
    get_canonical_project_dir,
    check_confinement_and_symlink,
    TenantSecurityError,
    PathSecurityViolation,
)


class ProjectExecutionConflictError(Exception):
    """Raised when a concurrent execution is attempted on an active project."""
    def __init__(self, project_id: str, reason: str = ""):
        self.project_id = project_id
        msg = f"Project '{project_id}' is currently locked for execution by another worker or process."
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class ProjectExecutionLock:
    """
    Guarantees that at most one execution (CLI, Worker, or API) can run on a project at any time.
    """
    EXECUTION_LOCK_FILE = ".pipeline_execution.lock"

    def __init__(
        self,
        project_dir: Path | str,
        owner_id: str = "cli",
        run_id: Optional[str] = None,
        db_path: Optional[Path | str] = None,
        timeout: float = 0.0,
        workspace_id: Optional[str] = None,
        base_dir: Optional[Path | str] = None,
    ):
        self.project_dir = Path(project_dir)
        self.project_id = validate_project_id(self.project_dir.name)
        self.owner_id = owner_id
        self.run_id = run_id or f"direct_{owner_id}"
        self.timeout = timeout
        self.repo = RunRepository(db_path=db_path)
        self._file_lock: Optional[StateLock] = None

        # Resolve trusted base directory (canonical projects root)
        if base_dir:
            self.base_dir = Path(base_dir).resolve()
        else:
            env_root = os.environ.get("MOTION_PROJECTS_ROOT") or os.environ.get("AGY_PROJECTS_ROOT")
            self.base_dir = Path(env_root).resolve() if env_root else Path("projects").resolve()

        self.workspace_id = self._resolve_workspace_id(workspace_id)
        self._verify_canonical_containment()

    def _resolve_workspace_id(self, explicit_ws: Optional[str]) -> str:
        """
        Resolves workspace ownership authoritatively with strict fail-closed security:
        1. Checks database project registration across configured engines:
           - self.repo.db_path (local / worker runs db)
           - get_database_engine() (primary authoritative database)
        2. Verifies canonical projects root confinement against trusted self.base_dir.
        3. Validates explicit workspace against registration and filesystem.
        4. Rejects trusting directory name alone for unregistered projects.
        5. Fails closed with TenantSecurityError on missing, ambiguous, or mismatched identity.
        """
        authoritative_ws: Optional[str] = None

        # 1. Query self.repo database if available
        if getattr(self.repo, "db_path", None):
            try:
                from scripts.core.database import DatabaseEngine, TenantRepository
                engine = DatabaseEngine(f"sqlite:///{self.repo.db_path}")
                tenant_repo = TenantRepository(engine)
                proj_record = tenant_repo.get_project(self.project_id)
                if proj_record and proj_record.workspace_id:
                    authoritative_ws = validate_workspace_id(proj_record.workspace_id)
            except Exception:
                pass

        # 2. Query configured authoritative database engine if not found in repo db
        if not authoritative_ws:
            try:
                from scripts.core.database import get_database_engine, TenantRepository
                engine = get_database_engine()
                tenant_repo = TenantRepository(engine)
                proj_record = tenant_repo.get_project(self.project_id)
                if proj_record and proj_record.workspace_id:
                    authoritative_ws = validate_workspace_id(proj_record.workspace_id)
            except Exception:
                pass

        # 3. Check canonical projects root confinement against trusted self.base_dir
        parent_ws: Optional[str] = None
        is_under_canonical_projects_root = False
        resolved_proj = self.project_dir.resolve()

        try:
            rel_path = resolved_proj.relative_to(self.base_dir)
            if len(rel_path.parts) == 2 and rel_path.parts[1] == self.project_id:
                is_under_canonical_projects_root = True
                try:
                    parent_ws = validate_workspace_id(rel_path.parts[0])
                except ValueError:
                    parent_ws = None
        except (ValueError, Exception):
            is_under_canonical_projects_root = False

        # Fallback to AGY_WORKSPACE_ID environment if explicit_ws is not provided
        effective_explicit_ws = explicit_ws
        if effective_explicit_ws is None:
            env_ws = os.environ.get("AGY_WORKSPACE_ID")
            if env_ws:
                try:
                    effective_explicit_ws = validate_workspace_id(env_ws)
                except ValueError:
                    effective_explicit_ws = None

        # Case 1: Caller provided explicit workspace identifier (or AGY_WORKSPACE_ID)
        if effective_explicit_ws is not None:
            validated_explicit = validate_workspace_id(effective_explicit_ws)
            if authoritative_ws and validated_explicit != authoritative_ws:
                raise TenantSecurityError(
                    f"Workspace ownership mismatch for project '{self.project_id}': "
                    f"explicit workspace '{validated_explicit}' does not match authoritative registration '{authoritative_ws}'."
                )
            if parent_ws and validated_explicit != parent_ws:
                raise TenantSecurityError(
                    f"Workspace ownership mismatch for project '{self.project_id}': "
                    f"explicit workspace '{validated_explicit}' conflicts with filesystem directory '{parent_ws}'."
                )
            if not is_under_canonical_projects_root:
                raise TenantSecurityError(
                    f"Invalid project path for project '{self.project_id}': "
                    f"path '{self.project_dir}' is not verified to reside under trusted canonical projects root '{self.base_dir}'."
                )
            return validated_explicit

        # Case 2: Authoritative registration exists in database
        if authoritative_ws:
            if not is_under_canonical_projects_root:
                raise TenantSecurityError(
                    f"Invalid project path for registered project '{self.project_id}': "
                    f"path '{self.project_dir}' is not verified to reside under trusted canonical projects root '{self.base_dir}'."
                )
            if parent_ws and authoritative_ws != parent_ws:
                raise TenantSecurityError(
                    f"Conflicting workspace identity for project '{self.project_id}': "
                    f"authoritative database registration '{authoritative_ws}' conflicts with filesystem directory '{parent_ws}'."
                )
            return authoritative_ws

        # Case 3: Project is unregistered and no explicit workspace identity was provided
        # A workspace identity CANNOT be trusted solely from a directory name. Fail closed!
        raise TenantSecurityError(
            f"Cannot acquire execution lock: missing or ambiguous workspace identity for project '{self.project_id}'. "
            "Workspace identity cannot be trusted solely from a directory name and must be authoritatively registered in the database or explicitly provided."
        )

    def _verify_canonical_containment(self) -> None:
        """
        Guarantees that self.project_dir is strictly contained within the trusted
        projects root and matches the authoritative canonical path for (workspace_id, project_id).
        """
        canonical_dir = get_canonical_project_dir(
            self.project_id, self.workspace_id, base_dir=self.base_dir
        )
        try:
            check_confinement_and_symlink(self.project_dir, self.base_dir)
        except Exception as e:
            raise TenantSecurityError(
                f"Path confinement violation for project '{self.project_id}': {e}"
            ) from e

        if self.project_dir.resolve() != canonical_dir.resolve():
            raise TenantSecurityError(
                f"Non-canonical project path for project '{self.project_id}': "
                f"'{self.project_dir.resolve()}' does not match canonical location '{canonical_dir.resolve()}'."
            )

    def acquire(self) -> "ProjectExecutionLock":
        # 1. Check persistent database lease authority
        active_lease = self.repo.get_active_project_lease(self.project_id)
        if active_lease and active_lease.get("run_id") != self.run_id:
            raise ProjectExecutionConflictError(
                self.project_id,
                f"Active lease held by worker '{active_lease.get('worker_id')}' for run '{active_lease.get('run_id')}'"
            )

        # 2. Acquire kernel file lock (.pipeline_execution.lock)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self._file_lock = StateLock(self.project_dir, timeout=self.timeout)
        self._file_lock.lock_path = self.project_dir / self.EXECUTION_LOCK_FILE
        try:
            self._file_lock.acquire()
        except StateLockTimeoutError:
            raise ProjectExecutionConflictError(
                self.project_id,
                "OS kernel lock .pipeline_execution.lock is held by another process"
            )

        # 3. Record/acquire lease in database repository if not already claimed by caller
        self._acquired_direct_lease = False
        if not active_lease:
            acquired = self.repo.acquire_direct_project_lease(
                self.project_id,
                owner_id=self.owner_id,
                run_id=self.run_id,
                lease_duration_seconds=300.0,
                workspace_id=self.workspace_id,
            )
            if not acquired:
                self._file_lock.release()
                raise ProjectExecutionConflictError(
                    self.project_id,
                    "Failed to record execution lease in database authority"
                )
            self._acquired_direct_lease = True

        return self

    def release(self) -> None:
        if self._file_lock and self._file_lock.is_locked:
            try:
                self._file_lock.release()
            except Exception:
                pass
        if getattr(self, "_acquired_direct_lease", False):
            try:
                self.repo.release_project_lease(self.project_id, run_id=self.run_id)
            except Exception:
                pass

    def __enter__(self) -> "ProjectExecutionLock":
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
