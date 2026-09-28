"""
Cross-Process Project Execution Lock for S21.

Ensures mutual exclusion across multiple workers, API requests, and CLI executions.
Combines OS-level kernel lock (.pipeline_execution.lock) with durable database lease.
"""

from pathlib import Path
from typing import Optional
from scripts.core.state_lock import StateLock, StateLockTimeoutError
from scripts.core.run_repository import RunRepository


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
    ):
        self.project_dir = Path(project_dir)
        self.project_id = self.project_dir.name
        self.owner_id = owner_id
        self.run_id = run_id or f"direct_{owner_id}"
        self.timeout = timeout
        self.repo = RunRepository(db_path=db_path)
        self._file_lock: Optional[StateLock] = None

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
                lease_duration_seconds=300.0
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
