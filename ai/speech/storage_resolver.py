"""
ai/speech/storage_resolver.py
=============================
Canonical storage input resolution and bounded scratch workspace for S28-M04.

Invariants:
- Strictly rejects arbitrary filesystem paths (e.g. absolute paths, path traversal).
- Enforces tenant and project access boundaries via TrustedToolExecutionContext.
- Resolves audio via canonical StorageService / project storage boundaries.
- Materializes audio inside unique, request-scoped temporary workspace with guaranteed cleanup.
- Zero secret or host absolute path leakage.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import logging
import os
from pathlib import Path
import shutil
import uuid
from typing import AsyncGenerator, Optional, Tuple, Union

from ai.contracts.errors import AIErrorCode
from ai.speech.stt_provider import (
    InvalidAudioError,
    StorageReadError,
    TenantAccessDeniedError,
)
from ai.tools.types import TrustedToolExecutionContext
from scripts.core.storage.storage_service import (
    LocalStorageBackend,
    StorageNotFoundError,
    StorageSecurityError,
    StorageService,
    validate_storage_key,
)

logger = logging.getLogger("clean_video.ai.speech.storage_resolver")

_SAFE_SCRATCH_ROOT = Path("scratch/stt_temp")


def _is_safe_storage_key(key: str) -> bool:
    """Verifies that a storage key does not contain illegal traversal segments or absolute roots."""
    if not key or not isinstance(key, str):
        return False
    if key.startswith("/") or key.startswith("\\"):
        return False
    if ".." in key.split("/") or ".." in key.split("\\"):
        return False
    return True


@asynccontextmanager
async def resolve_and_materialize_audio(
    project_id: str,
    audio_storage_key: str,
    workspace_id: Optional[str] = None,
    context: Optional[TrustedToolExecutionContext] = None,
    storage_service: Optional[StorageService] = None,
    audio_bytes_override: Optional[bytes] = None,
    request_id: Optional[str] = None,
) -> AsyncGenerator[Tuple[Path, str, str], None]:
    """
    Asynchronous context manager that safely resolves canonical audio storage references
    and materializes the payload into a strictly isolated temporary workspace.

    Yields:
        Tuple[temp_file_path: Path, content_hash: str, source_asset_id: str]

    Guarantees:
        Temp files and directories are always deleted upon exit (success, failure, or cancellation).
    """
    req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
    temp_dir: Optional[Path] = None

    try:
        # 1. Enforce Path & Traversal Security
        if not _is_safe_storage_key(audio_storage_key):
            raise TenantAccessDeniedError(
                f"Arbitrary filesystem path or traversal attempt detected in audio_storage_key: '{audio_storage_key}'",
                details={"audio_storage_key": audio_storage_key, "project_id": project_id},
            )

        # 2. Enforce Tenant & Project Confinement
        if context is not None:
            if workspace_id and context.workspace_id and workspace_id != context.workspace_id and not context.is_admin:
                raise TenantAccessDeniedError(
                    f"Cross-workspace access denied: actor workspace '{context.workspace_id}' cannot access '{workspace_id}'.",
                    details={"workspace_id": workspace_id, "actor_workspace": context.workspace_id},
                )
            if not context.can_access_project(project_id):
                raise TenantAccessDeniedError(
                    f"Cross-project access denied: actor '{context.actor_id}' cannot access project '{project_id}'.",
                    details={"project_id": project_id, "actor_id": context.actor_id},
                )

        # 3. Retrieve Audio Bytes
        audio_data: bytes
        source_asset_id = Path(audio_storage_key).name

        if audio_bytes_override is not None:
            audio_data = audio_bytes_override
        elif storage_service is not None:
            try:
                # Look up via StorageService
                clean_key = validate_storage_key(audio_storage_key)
                if not storage_service.exists(clean_key):
                    # Also try project-scoped storage key
                    proj_scoped_key = f"{'projects'}/{project_id}/{clean_key}"
                    if storage_service.exists(proj_scoped_key):
                        clean_key = proj_scoped_key
                    else:
                        raise StorageReadError(
                            f"Audio asset '{audio_storage_key}' not found in StorageService.",
                            details={"key": clean_key, "project_id": project_id},
                        )
                audio_data = storage_service.get(clean_key)
            except (StorageNotFoundError, StorageSecurityError) as se:
                raise StorageReadError(f"Storage error reading audio: {se}", details={"error": str(se)})
        else:
            # Fallback to local project directory resolution
            candidate_paths = [
                Path("projects") / project_id / audio_storage_key,
                Path("assets/incoming/tests") / audio_storage_key,
                Path(audio_storage_key),
            ]
            found_path: Optional[Path] = None
            for cp in candidate_paths:
                if cp.exists() and cp.is_file():
                    # Ensure cp is inside permitted project or test directories
                    resolved = cp.resolve()
                    base_proj = (Path("projects") / project_id).resolve()
                    base_assets = Path("assets").resolve()
                    base_tests = Path("tests").resolve()
                    if (
                        str(resolved).startswith(str(base_proj))
                        or str(resolved).startswith(str(base_assets))
                        or str(resolved).startswith(str(base_tests))
                    ):
                        found_path = cp
                        break

            if found_path is None:
                raise StorageReadError(
                    f"Audio asset '{audio_storage_key}' not found for project '{project_id}'.",
                    details={"project_id": project_id, "audio_storage_key": audio_storage_key},
                )

            try:
                audio_data = found_path.read_bytes()
            except Exception as e:
                raise StorageReadError(f"Failed to read audio file '{found_path}': {e}")

        # 4. Check Non-Empty Content
        if len(audio_data) == 0:
            raise InvalidAudioError(
                f"Audio asset '{audio_storage_key}' is zero bytes (empty file).",
                details={"audio_storage_key": audio_storage_key, "file_size": 0},
            )

        content_hash = hashlib.sha256(audio_data).hexdigest()

        # 5. Create Request-Scoped Temp Workspace
        _SAFE_SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        unique_scope = f"{req_id}_{uuid.uuid4().hex[:8]}"
        temp_dir = _SAFE_SCRATCH_ROOT / unique_scope
        temp_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(audio_storage_key).suffix or ".wav"
        temp_file_path = temp_dir / f"audio_input{suffix}"
        temp_file_path.write_bytes(audio_data)

        yield temp_file_path, content_hash, source_asset_id

    finally:
        # Guaranteed cleanup on exit, failure, timeout, or cancellation
        if temp_dir is not None and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as clean_err:
                logger.warning("Could not cleanly delete temp dir %s: %s", temp_dir, clean_err)
