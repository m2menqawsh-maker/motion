"""
Cross-Process Lock Abstraction for StateStore.

Supports POSIX (fcntl.flock) and Windows (msvcrt.locking).
Ensures serialization across CLI processes, API workers, and subprocesses.
Locks are held on a dedicated, stable file: .pipeline_state.lock.
The lock file is NEVER deleted on release to preserve inode/handle continuity.
OS automatically releases kernel locks if a process dies or is killed.
"""

import os
import time
from pathlib import Path
from typing import Optional


class StateLockError(Exception):
    """Base exception for StateLock errors."""
    pass


class StateLockTimeoutError(StateLockError):
    """Raised when acquiring a cross-process state lock times out."""
    pass


class StateLock:
    """
    Cross-process file lock using kernel-level locks.
    Never unlinks the lock file on release to prevent inode recycling races.
    """
    LOCK_FILE = ".pipeline_state.lock"

    def __init__(
        self,
        project_dir: Path | str,
        timeout: Optional[float] = 10.0,
        poll_interval: float = 0.01,
    ):
        self.project_dir = Path(project_dir)
        self.lock_path = self.project_dir / self.LOCK_FILE
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._fd: Optional[int] = None

    def acquire(self) -> "StateLock":
        self.project_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.lock_path), os.O_RDWR | os.O_CREAT, 0o666)
        start_time = time.monotonic()

        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                self._fd = fd
                return self
            except (BlockingIOError, OSError):
                if self.timeout is not None and (time.monotonic() - start_time) >= self.timeout:
                    os.close(fd)
                    raise StateLockTimeoutError(
                        f"Timed out after {self.timeout}s waiting for state lock at {self.lock_path}"
                    )
                time.sleep(self.poll_interval)

    def release(self) -> None:
        if self._fd is not None:
            try:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(self._fd, 0, os.SEEK_SET)
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
            # Deliberately NEVER unlink self.lock_path to avoid race conditions with other processes

    def __enter__(self) -> "StateLock":
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    @property
    def is_locked(self) -> bool:
        return self._fd is not None
