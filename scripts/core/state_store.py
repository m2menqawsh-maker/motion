import os
import json
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime, timezone

from scripts.core.state_model import ProjectState, ArtifactRecord, ValidationLevel, LifecycleState
from scripts.core.state_lock import StateLock, StateLockError, StateLockTimeoutError


class StateStoreError(Exception):
    """Base exception for all StateStore errors."""
    pass


class StateConflictError(StateStoreError):
    """
    Raised when a write fails CAS (Compare-And-Swap) verification.
    Occurs when the caller's expected revision does not match the actual on-disk revision.
    """
    def __init__(self, expected_revision: Optional[int], actual_revision: Optional[int], message: Optional[str] = None):
        self.expected_revision = expected_revision
        self.actual_revision = actual_revision
        if not message:
            message = (
                f"State conflict: expected revision {expected_revision}, "
                f"but found actual revision {actual_revision} on disk."
            )
        super().__init__(message)


class StateExistsError(StateConflictError):
    """Raised when attempting to create a state file that already exists."""
    def __init__(self, project_dir: Path, message: Optional[str] = None):
        if not message:
            message = f"State file already exists in '{project_dir}'."
        super().__init__(expected_revision=0, actual_revision=None, message=message)


class StateNotFoundError(StateStoreError):
    """Raised when attempting an atomic update on a project with no state file."""
    def __init__(self, project_dir: Path):
        super().__init__(f"No state file found in '{project_dir}'.")


class StateStore:
    STATE_FILE = ".pipeline_state.json"
    LOCK_FILE = ".pipeline_state.lock"

    @classmethod
    def lock(cls, project_dir: Path | str, timeout: Optional[float] = 10.0) -> StateLock:
        """Returns a cross-process StateLock context manager for the project."""
        return StateLock(project_dir, timeout=timeout)

    @staticmethod
    def _compute_sha256(path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def create_artifact_record(project_dir: Path, rel_path: str, validation: ValidationLevel) -> ArtifactRecord:
        """
        Creates an ArtifactRecord for the given file relative to project_dir.
        Calculates size and sha256 according to validation level.
        """
        full_path = project_dir / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Cannot create artifact record, file missing: {rel_path}")

        record = ArtifactRecord(path=rel_path, validation=validation)

        if validation in (ValidationLevel.SIZE, ValidationLevel.SHA256):
            record.size_bytes = full_path.stat().st_size

        if validation == ValidationLevel.SHA256:
            record.sha256 = StateStore._compute_sha256(full_path)

        return record

    @classmethod
    def _persist_atomic(cls, project_dir: Path, state: ProjectState) -> None:
        """
        Internal: Atomically persists state to project_dir using a unique temp file in the same directory.
        Performs full serialization validation before os.replace.
        """
        if hasattr(state, "model_dump"):
            data = state.model_dump(mode='json')
        else:
            data = state.dict()

        # Serialization validation: ensure model parses cleanly
        ProjectState.model_validate(data)
        serialized = json.dumps(data, ensure_ascii=False, indent=2)

        state_file = project_dir / cls.STATE_FILE
        unique_suffix = f"{os.getpid()}.{uuid.uuid4().hex}"
        tmp_file = project_dir / f".pipeline_state.{unique_suffix}.tmp"

        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(serialized)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_file, state_file)

            # Sync directory entry on POSIX platforms
            if os.name != "nt":
                try:
                    dir_fd = os.open(str(project_dir), os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                except OSError:
                    pass
        finally:
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    @classmethod
    def atomic_update(
        cls,
        project_dir: Path | str,
        expected_revision: int,
        mutator: Callable[[ProjectState], None],
        timeout: Optional[float] = 10.0,
    ) -> ProjectState:
        """
        Atomically updates project state with CAS and cross-process locking.

        1. Acquires cross-process lock on project_dir / '.pipeline_state.lock'.
        2. Authoritatively re-reads current on-disk state.
        3. Enforces CAS: actual_revision == expected_revision.
           If mismatched: raises StateConflictError (zero disk mutation).
        4. Clones a working copy (copy-on-write).
        5. Calls mutator(working_copy). If mutator raises, zero disk mutation.
        6. Increments revision exactly once (actual_revision + 1).
        7. Updates updated_at timestamp.
        8. Serializes, validates, and atomically commits via unique temp file.
        9. Releases lock.
        10. Returns the committed ProjectState.
        """
        if expected_revision is None or not isinstance(expected_revision, int):
            raise ValueError(f"expected_revision must be an integer, got: {type(expected_revision).__name__}")

        pdir = Path(project_dir)
        with cls.lock(pdir, timeout=timeout):
            current_state = cls.load(pdir)
            if current_state is None:
                raise StateNotFoundError(pdir)

            if current_state.revision != expected_revision:
                raise StateConflictError(
                    expected_revision=expected_revision,
                    actual_revision=current_state.revision
                )

            # Copy-on-write clone
            working_copy = current_state.model_copy(deep=True)
            working_copy._loaded_revision = current_state.revision

            # Apply domain mutator
            mutator(working_copy)

            # Storage authority increments revision and updates timestamp
            working_copy.revision = current_state.revision + 1
            working_copy.updated_at = datetime.now(timezone.utc).isoformat()

            # Atomic persistence
            cls._persist_atomic(pdir, working_copy)
            working_copy._loaded_revision = working_copy.revision
            return working_copy

    @classmethod
    def save(
        cls,
        project_dir: Path | str,
        state: ProjectState,
        expected_revision: Optional[int] = None,
        timeout: Optional[float] = 10.0,
    ) -> None:
        """
        Saves the state record to the project directory under cross-process lock with CAS validation.
        """
        pdir = Path(project_dir)
        with cls.lock(pdir, timeout=timeout):
            current_disk = cls.load(pdir)
            if current_disk is None:
                if expected_revision is not None and expected_revision not in (0, 1):
                    raise StateConflictError(expected_revision=expected_revision, actual_revision=None)
                cls._persist_atomic(pdir, state)
                state._loaded_revision = state.revision
                return

            if expected_revision is not None:
                exp = expected_revision
            elif getattr(state, "_loaded_revision", None) is not None:
                exp = state._loaded_revision
            else:
                # Fail closed: updating an existing state requires explicit expected_revision
                # or a trusted _loaded_revision from StateStore.load().
                # Never silently derive overwrite authority from an untracked state.revision value.
                raise StateConflictError(
                    expected_revision=None,
                    actual_revision=current_disk.revision,
                    message=(
                        f"Cannot update existing state in '{pdir}': state object was not loaded from "
                        f"StateStore and no explicit expected_revision was provided (actual revision: {current_disk.revision})."
                    ),
                )

            if exp != current_disk.revision:
                raise StateConflictError(
                    expected_revision=exp,
                    actual_revision=current_disk.revision
                )

            # Enforce monotonic revision increment (actual_revision + 1)
            state.revision = current_disk.revision + 1

            state.updated_at = datetime.now(timezone.utc).isoformat()
            cls._persist_atomic(pdir, state)
            state._loaded_revision = state.revision

    @classmethod
    def load(cls, project_dir: Path | str) -> Optional[ProjectState]:
        """
        Loads the state record from the project directory if it exists.
        Records _loaded_revision for CAS tracking.
        """
        pdir = Path(project_dir)
        state_file = pdir / cls.STATE_FILE
        if not state_file.exists():
            return None

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = ProjectState(**data)
            state._loaded_revision = state.revision
            return state
        except Exception:
            return None

    @classmethod
    def create(
        cls,
        project_dir: Path | str,
        project_id: str,
        initial_lifecycle: LifecycleState = LifecycleState.DRAFT,
        timeout: Optional[float] = 10.0,
    ) -> ProjectState:
        """
        Atomically creates a new ProjectState record in project_dir.
        Fails closed if the state file already exists.
        """
        pdir = Path(project_dir)
        pdir.mkdir(parents=True, exist_ok=True)
        state_file = pdir / cls.STATE_FILE

        with cls.lock(pdir, timeout=timeout):
            if state_file.exists():
                current_state = cls.load(pdir)
                curr_rev = current_state.revision if current_state else None
                raise StateExistsError(
                    pdir,
                    message=f"Cannot create state in '{pdir}': state file already exists (revision {curr_rev})."
                )

            state = ProjectState(
                project_id=project_id,
                revision=1,
                lifecycle_state=initial_lifecycle,
            )
            cls._persist_atomic(pdir, state)
            state._loaded_revision = 1
            return state
