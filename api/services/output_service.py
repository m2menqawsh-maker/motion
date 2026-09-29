"""
Domain Service for Video Delivery & Output Media (S22 - LED-065).

Provides:
- Safe project confinement verification
- HTTP Range calculation and chunk streaming
- Content-Range / Accept-Ranges header generation
- Zero leak of physical filesystem paths
"""

import os
from pathlib import Path
from typing import Tuple, Generator, Optional

from api.core.errors import ProjectNotFoundError, APIError, InvalidRangeError
from scripts.security.path_security import validate_project_id, resolve_safe_path


class OutputService:
    """Domain authority for output media streaming and delivery."""

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        validate_project_id(project_id)
        proj_dir = Path(f"projects/{project_id}")
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        return proj_dir

    @classmethod
    def get_output_path(cls, project_id: str, output_id: str) -> Path:
        """Resolves output file within strict project confinement."""
        proj_dir = cls._get_project_dir(project_id)
        # Prevent traversal
        clean_id = Path(output_id).name
        if clean_id != output_id or ".." in output_id:
            raise APIError("Invalid output identifier", status_code=400)

        out_path = resolve_safe_path(proj_dir, clean_id)
        if not (out_path.exists() and out_path.is_file()):
            outputs_sub = resolve_safe_path(proj_dir / "outputs", clean_id)
            if outputs_sub.exists() and outputs_sub.is_file():
                out_path = outputs_sub
            else:
                # Check StorageService (S24.5 - Heavy object persistence)
                try:
                    from scripts.core.database import get_database_engine, TenantRepository
                    from scripts.core.storage import get_storage_service
                    storage = get_storage_service()
                    repo = TenantRepository(get_database_engine())
                    prj_rec = repo.get_project(project_id)
                    ws_id = prj_rec.workspace_id if prj_rec else "ws_default"

                    candidate_keys = [
                        f"workspaces/{ws_id}/projects/{project_id}/outputs/{output_id}",
                    ]
                    from scripts.core.run_repository import RunRepository
                    runs = RunRepository().list_runs(project_id, limit=10)
                    for r in runs:
                        if r.result_reference and isinstance(r.result_reference, dict):
                            out_key = r.result_reference.get("output_storage_key")
                            if out_key and out_key.endswith(clean_id):
                                candidate_keys.append(out_key)

                    for key in candidate_keys:
                        if storage.exists(key):
                            if hasattr(storage, "_resolve_path"):
                                return storage._resolve_path(key)
                            else:
                                cached_dest = outputs_sub
                                cached_dest.parent.mkdir(parents=True, exist_ok=True)
                                cached_dest.write_bytes(storage.get(key))
                                return cached_dest
                except Exception:
                    pass

                raise APIError("Output media not found", status_code=404)

        return out_path

    @classmethod
    def parse_range_header(
        cls,
        range_header: Optional[str],
        file_size: int,
    ) -> Optional[Tuple[int, int]]:
        """
        Parses 'Range: bytes=start-end' header.
        Returns: (start, end) inclusive, or None if no Range header.
        Raises InvalidRangeError on malformed or unsatisfiable range.
        """
        if not range_header or not range_header.startswith("bytes="):
            return None

        range_val = range_header.replace("bytes=", "").strip()
        parts = range_val.split("-")
        if len(parts) != 2:
            raise InvalidRangeError(range_header, file_size)

        start_str, end_str = parts[0].strip(), parts[1].strip()

        try:
            if start_str and end_str:
                start = int(start_str)
                end = int(end_str)
            elif start_str and not end_str:
                start = int(start_str)
                end = file_size - 1
            elif not start_str and end_str:
                # Suffix byte range
                length = int(end_str)
                start = max(0, file_size - length)
                end = file_size - 1
            else:
                raise InvalidRangeError(range_header, file_size)
        except ValueError:
            raise InvalidRangeError(range_header, file_size)

        if start < 0 or start >= file_size or end < start or end >= file_size:
            raise InvalidRangeError(range_header, file_size)

        return start, end

    @classmethod
    def open_byte_range_stream(
        cls,
        file_path: Path,
        start: int,
        end: int,
        chunk_size: int = 64 * 1024,
    ) -> Generator[bytes, None, None]:
        """Streams byte range [start, end] inclusive from disk."""
        bytes_to_read = end - start + 1
        with open(file_path, "rb") as f:
            f.seek(start)
            while bytes_to_read > 0:
                current_chunk = min(bytes_to_read, chunk_size)
                data = f.read(current_chunk)
                if not data:
                    break
                bytes_to_read -= len(data)
                yield data
