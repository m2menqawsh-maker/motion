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


class StateCorruptedError(StateStoreError):
    """
    Raised when a state file exists on disk but cannot be decoded or parsed
    (e.g., malformed JSON syntax, invalid schema, truncated payload).
    """
    def __init__(self, project_dir: Path | str, reason: str, raw_content: Optional[str] = None):
        self.project_dir = Path(project_dir)
        self.reason = reason
        self.raw_content = raw_content
        super().__init__(f"State file in '{self.project_dir}' is corrupted: {reason}")


class StateIOError(StateStoreError):
    """
    Raised when accessing the state file fails due to an OS/permission I/O error.
    """
    def __init__(self, project_dir: Path | str, reason: str):
        self.project_dir = Path(project_dir)
        self.reason = reason
        super().__init__(f"I/O failure accessing state file in '{self.project_dir}': {reason}")


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
    def create_artifact_record(
        project_dir: Path,
        rel_path: str,
        validation: ValidationLevel,
        logical_name: Optional[str] = None,
        stage: Optional[str] = None,
        produced_at_revision: Optional[int] = None,
        generation_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ArtifactRecord:
        """
        Creates an ArtifactRecord for the given file relative to project_dir.
        Calculates size and sha256 according to validation level.
        """
        full_path = project_dir / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Cannot create artifact record, file missing: {rel_path}")

        record = ArtifactRecord(
            path=rel_path,
            validation=validation,
            logical_name=logical_name,
            stage=stage,
            produced_at_revision=produced_at_revision,
            generation_id=generation_id,
            metadata=metadata or {},
        )

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

        # Sync state to relational database (PostgreSQL / SQLite) (S24.5)
        cls._sync_to_db(state)

    @classmethod
    def _sync_to_db(cls, state: ProjectState, expected_revision: Optional[int] = None) -> None:
        """Internal helper to reflect ProjectState into the relational database engine."""
        try:
            from scripts.core.database import get_database_engine
            engine = get_database_engine()
            with engine.transaction() as conn:
                cur = conn.execute("SELECT workspace_id FROM projects WHERE id = ?", (state.project_id,))
                row = cur.fetchone()
                ws_id = row[0] if row else state.workspace_id
                if not ws_id:
                    ws_id = "ws_default"
                    conn.execute(
                        "INSERT OR IGNORE INTO users (id, email, status, created_at) VALUES ('usr_system', 'system@motion.local', 'active', ?)",
                        (state.created_at,)
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO workspaces (id, name, created_by, created_at) VALUES ('ws_default', 'Default Workspace', 'usr_system', ?)",
                        (state.created_at,)
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO workspace_members (workspace_id, user_id, role, created_at) VALUES ('ws_default', 'usr_system', 'admin', ?)",
                        (state.created_at,)
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO projects (id, workspace_id, created_by, name, created_at, updated_at) VALUES (?, 'ws_default', 'usr_system', ?, ?, ?)",
                        (state.project_id, state.project_id, state.created_at, state.updated_at)
                    )

                state.workspace_id = ws_id
                state_json = state.model_dump_json()

                cur = conn.execute("SELECT revision FROM project_states WHERE project_id = ?", (state.project_id,))
                state_row = cur.fetchone()
                if not state_row:
                    conn.execute(
                        "INSERT INTO project_states (project_id, workspace_id, revision, lifecycle_state, state_json, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (state.project_id, ws_id, state.revision, state.lifecycle_state.value, state_json, state.updated_at)
                    )
                else:
                    curr_rev = state_row[0]
                    if expected_revision is not None and curr_rev != expected_revision:
                        raise StateConflictError(expected_revision, curr_rev, f"DB CAS mismatch for project '{state.project_id}'")
                    conn.execute(
                        "UPDATE project_states SET revision = ?, lifecycle_state = ?, state_json = ?, updated_at = ? WHERE project_id = ?",
                        (state.revision, state.lifecycle_state.value, state_json, state.updated_at, state.project_id)
                    )
        except Exception as e:
            if isinstance(e, StateConflictError):
                raise
            # Non-fatal if database is unconfigured during low-level isolated unit tests
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

            # Invariant (S06): Cumulative evidence retention across updates
            from scripts.core.evidence_matrix import merge_artifact_records
            working_copy.artifact_records = merge_artifact_records(
                current_state.artifact_records,
                working_copy.artifact_records
            )

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

            # Invariant (S06): Cumulative evidence retention across state saves
            from scripts.core.evidence_matrix import merge_artifact_records
            state.artifact_records = merge_artifact_records(
                current_disk.artifact_records,
                state.artifact_records
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

        Returns:
            ProjectState if file exists and is valid.
            None ONLY if the state file does not exist on disk.

        Raises:
            StateIOError: If reading the file encounters an OS/permission I/O error.
            StateCorruptedError: If file exists but contains invalid JSON or violates ProjectState schema.
        """
        pdir = Path(project_dir)
        state_file = pdir / cls.STATE_FILE
        if not state_file.exists():
            return None

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            return None
        except PermissionError as e:
            raise StateIOError(pdir, f"Permission denied reading state file '{state_file}': {e}")
        except OSError as e:
            raise StateIOError(pdir, f"I/O error reading state file '{state_file}': {e}")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise StateCorruptedError(pdir, f"Invalid JSON syntax in state file: {e}", raw_content=content)

        if not isinstance(data, dict):
            raise StateCorruptedError(pdir, f"Root element in state file must be an object, got {type(data).__name__}", raw_content=content)

        try:
            state = ProjectState.model_validate(data)
        except Exception as e:
            raise StateCorruptedError(pdir, f"Schema validation failed for state file: {e}", raw_content=content)

        state._loaded_revision = state.revision
        return state

    @classmethod
    def quarantine_corrupt_state(
        cls,
        project_dir: Path | str,
        reason: str = "Corrupted state file",
        quarantine_id: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Safely quarantines a corrupted state file by renaming it to .pipeline_state.corrupt.<id>.json.
        Preserves original bytes for forensics without leaving the corrupted file in the active path.
        """
        pdir = Path(project_dir)
        state_file = pdir / cls.STATE_FILE
        if not state_file.exists():
            return None

        qid = quarantine_id or f"{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:6]}"
        quarantine_file = pdir / f".pipeline_state.corrupt.{qid}.json"

        try:
            os.replace(state_file, quarantine_file)
            return quarantine_file
        except OSError as e:
            raise StateIOError(pdir, f"Failed to quarantine corrupted state file: {e}")

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

    @classmethod
    def load_by_id(cls, project_id: str) -> Optional[ProjectState]:
        """Loads ProjectState directly from the relational database engine."""
        from scripts.core.database import get_database_engine, TenantStateRepository
        engine = get_database_engine()
        repo = TenantStateRepository(engine)
        return repo.load_state(project_id)

    @classmethod
    def atomic_update_by_id(
        cls,
        project_id: str,
        workspace_id: str,
        expected_revision: int,
        mutator: Callable[[ProjectState], None],
    ) -> ProjectState:
        """
        Atomically updates ProjectState directly in the relational database engine using CAS.
        """
        from scripts.core.database import get_database_engine, TenantStateRepository
        from scripts.core.evidence_matrix import merge_artifact_records
        engine = get_database_engine()
        repo = TenantStateRepository(engine)
        current = repo.load_state(project_id)
        if current is None:
            raise StateNotFoundError(Path(f"projects/{project_id}"))
        if current.revision != expected_revision:
            raise StateConflictError(expected_revision, current.revision)

        working_copy = current.model_copy(deep=True)
        working_copy._loaded_revision = current.revision
        mutator(working_copy)

        working_copy.artifact_records = merge_artifact_records(
            current.artifact_records,
            working_copy.artifact_records
        )
        return repo.update_state_cas(project_id, workspace_id, expected_revision, working_copy)

