"""
ai/media_processing/staging.py
==============================
Isolated worker execution workspace and asset fetch staging (S28-M06).

Invariants:
- Temporary worker workspace is an execution scratchpad, NEVER persistent source of truth.
- Resolves canonical storage references strictly after tenant and confinement validation.
- All temporary files are guaranteed to be cleaned up upon exit or failure.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Sequence

from ai.media_processing.errors import (
    MediaSourceNotFoundError,
    StorageFetchFailedError,
)
from ai.media_processing.security import (
    assert_safe_local_path,
    format_safe_concat_manifest_content,
    validate_storage_key_confinement,
)
from scripts.core.storage.storage_service import StorageNotFoundError, StorageService

logger = logging.getLogger("ai.media_processing.staging")


class WorkerStagingContext:
    """
    Manages an isolated temporary workspace on the worker filesystem for media processing.
    """

    def __init__(
        self,
        storage_service: StorageService,
        project_id: str,
        base_scratch_dir: Optional[Path] = None,
        workspace_id: Optional[str] = None,
    ):
        self.storage_service = storage_service
        self.project_id = project_id
        self.workspace_id = workspace_id or "ws_default"
        self.base_scratch_dir = base_scratch_dir or Path("scratch/worker_media")
        self.workspace_dir: Optional[Path] = None

    def __enter__(self) -> WorkerStagingContext:
        self.base_scratch_dir.mkdir(parents=True, exist_ok=True)
        unique_id = f"job_{self.project_id}_{uuid.uuid4().hex[:12]}"
        self.workspace_dir = self.base_scratch_dir / unique_id
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Removes the entire temporary worker workspace."""
        if self.workspace_dir and self.workspace_dir.exists():
            try:
                shutil.rmtree(self.workspace_dir, ignore_errors=True)
            except Exception as e:
                logger.warning("Failed to remove worker temp dir %s: %s", self.workspace_dir, e)
            finally:
                self.workspace_dir = None

    def stage_input_asset(self, storage_key: str, local_name: Optional[str] = None) -> Path:
        """
        Validates tenant confinement, fetches the asset from StorageService,
        and materializes it safely into the isolated worker workspace.
        """
        if not self.workspace_dir:
            raise RuntimeError("WorkerStagingContext must be entered before staging assets.")

        # 1. Enforce tenant boundary & safety checks
        validate_storage_key_confinement(storage_key, self.project_id)

        # 2. Derive safe local filename
        filename = local_name or Path(storage_key).name
        if not filename or filename in (".", ".."):
            filename = f"input_{uuid.uuid4().hex[:8]}.bin"

        local_path = self.workspace_dir / filename
        assert_safe_local_path(local_path, self.workspace_dir)

        # 3. Fetch from StorageService
        try:
            data = self.storage_service.get(storage_key)
        except StorageNotFoundError:
            raise MediaSourceNotFoundError(
                f"Source media '{storage_key}' not found in project storage.",
                details={"storage_key": storage_key, "project_id": self.project_id},
            )
        except Exception as e:
            raise StorageFetchFailedError(
                f"Failed to fetch media object '{storage_key}': {e}",
                details={"storage_key": storage_key, "error": str(e)},
            )

        if not data:
            raise MediaSourceNotFoundError(
                f"Source media '{storage_key}' is 0 bytes or empty.",
                details={"storage_key": storage_key},
            )

        # 4. Materialize to worker workspace
        fd = os.open(str(local_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise

        return local_path

    def get_output_path(self, filename: str) -> Path:
        """Returns a verified safe path for staging output inside the worker workspace."""
        if not self.workspace_dir:
            raise RuntimeError("WorkerStagingContext must be entered before allocating output paths.")

        out_path = self.workspace_dir / filename
        return assert_safe_local_path(out_path, self.workspace_dir)

    def create_safe_concat_manifest(
        self,
        file_paths: Sequence[Path | str],
        manifest_name: str = "concat_manifest.txt",
    ) -> Path:
        """
        Generates an internal, safely formatted FFmpeg concat demuxer manifest file
        inside the worker workspace.
        """
        manifest_path = self.get_output_path(manifest_name)
        return build_safe_concat_manifest(file_paths, manifest_path)


def build_safe_concat_manifest(
    file_paths: Sequence[Path | str],
    output_manifest_path: Path,
) -> Path:
    """
    Generates an internal, safely formatted FFmpeg concat demuxer manifest file
    using safe worker staging file descriptor write.
    """
    content = format_safe_concat_manifest_content(file_paths).encode("utf-8")
    fd = os.open(str(output_manifest_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    return output_manifest_path
