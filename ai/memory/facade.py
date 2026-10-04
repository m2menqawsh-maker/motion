"""
ai/memory/facade.py
===================
Project Memory Facade & Storage Service Integration Boundary (S27.6).

Architectural Invariants (ADR-004 DEC-06.4):
1. Project Memory is NOT a shadow copy of the Project database.
   - Authoritative project facts remain in domain services (ProjectService, AssetService, etc.).
   - Memory holds only derived insights, decisions, user preferences, and semantic indexes.
2. Large Artifact Storage:
   - Heavy blobs (video, raw audio, huge transcripts) are stored via StorageService.
   - Memory records hold only authoritative `storage_ref`, summaries, and content hashes.
3. Access Authorization:
   - Memory access strictly enforces current authorization (checks accessible_projects).
   - If a project is deleted or permissions are revoked, stale memories are never exposed.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Dict, List, Optional
from pydantic import JsonValue

if TYPE_CHECKING:
    from ai.memory.service import MemoryService

from ai.memory.models import MemoryEntry, MemoryFilter, TrustedTenantContext
from ai.memory.types import MemoryScope, MemoryType
from scripts.core.storage.storage_service import (
    StorageMetadata,
    StorageService,
    build_storage_key,
)


class ProjectAccessDeniedError(PermissionError):
    """Raised when an actor attempts to access memory for a project without permission."""
    pass


class ProjectNotFoundError(LookupError):
    """Raised when requested project does not exist or has been deleted."""
    pass


class ProjectMemoryFacade:
    """
    Unified facade coordinating domain facts, derived AI memories, and heavy artifact storage.
    """

    def __init__(
        self,
        memory_service: MemoryService,
        storage_service: Optional[StorageService] = None,
        project_service: Optional[object] = None,
    ):
        self.memory_service = memory_service
        self.storage_service = storage_service
        self.project_service = project_service

    def get_project_context(
        self,
        context: TrustedTenantContext,
        project_id: str,
        include_decisions: bool = True,
        include_preferences: bool = True,
    ) -> Dict[str, JsonValue]:
        """
        Retrieves canonical project facts from Domain Services alongside learned AI memories.
        
        Strictly verifies that context has active access to project_id.
        """
        # 1. Authoritative permission check
        if not context.can_access_project(project_id):
            raise ProjectAccessDeniedError(
                f"Actor '{context.user_id}' does not have access to project '{project_id}' in workspace '{context.workspace_id}'."
            )

        # 2. Check project existence in domain service if available
        domain_facts: Dict[str, JsonValue] = {}
        if self.project_service is not None:
            try:
                # E.g. ProjectService.get_lifecycle_dto(project_id)
                dto = self.project_service.get_lifecycle_dto(project_id)
                if dto is None:
                    raise ProjectNotFoundError(f"Project '{project_id}' was not found or has been deleted.")
                domain_facts = dto.model_dump() if hasattr(dto, "model_dump") else (dto if isinstance(dto, dict) else {})
            except ProjectNotFoundError:
                raise
            except Exception as exc:
                # If project lookup fails with not found
                if "not found" in str(exc).lower():
                    raise ProjectNotFoundError(f"Project '{project_id}' does not exist: {exc}")
                domain_facts = {"error": str(exc)}

        # 3. Retrieve learned decisions and memories from MemoryService
        learned_memories: List[MemoryEntry] = []
        types_to_fetch = [MemoryType.PROJECT]
        if include_decisions:
            types_to_fetch.append(MemoryType.DECISION)
        if include_preferences:
            types_to_fetch.append(MemoryType.USER_PREFERENCE)

        filter_req = MemoryFilter(
            workspace_id=context.workspace_id,
            project_id=project_id,
            memory_types=types_to_fetch,
            limit=50,
        )
        memories = self.memory_service.query_structured(context, filter_req)

        return {
            "workspace_id": context.workspace_id,
            "project_id": project_id,
            "domain_facts": domain_facts,
            "learned_memories": [m.model_dump() for m in memories],
        }

    def store_heavy_artifact_memory(
        self,
        context: TrustedTenantContext,
        project_id: str,
        category: str,
        item_id: str,
        filename: str,
        content_bytes: bytes,
        content_type: str,
        summary: str,
        memory_type: MemoryType = MemoryType.MEDIA_INTELLIGENCE,
        metadata: Optional[Dict[str, JsonValue]] = None,
    ) -> MemoryEntry:
        """
        Stores heavy payload in StorageService, then registers canonical reference in MemoryService.
        """
        if not context.can_access_project(project_id):
            raise ProjectAccessDeniedError(f"Access denied to project '{project_id}'.")

        storage_key: Optional[str] = None
        sha256_hash = ""

        # 1. Store heavy bytes in StorageService
        if self.storage_service is not None:
            storage_key = build_storage_key(
                workspace_id=context.workspace_id,
                project_id=project_id,
                category=category,
                item_id=item_id,
                filename=filename,
            )
            stored_meta = self.storage_service.put(
                key=storage_key,
                data=content_bytes,
                content_type=content_type,
            )
            sha256_hash = stored_meta.sha256 or ""

        # 2. Create structured MemoryEntry referencing the artifact
        meta = metadata or {}
        meta.update({
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(content_bytes),
            "sha256": sha256_hash,
        })

        return self.memory_service.store_memory(
            context=context,
            content=summary,
            memory_type=memory_type,
            scope=MemoryScope.PROJECT,
            project_id=project_id,
            storage_ref=storage_key,
            metadata=meta,
        )
