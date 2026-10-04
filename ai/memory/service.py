"""
ai/memory/service.py
====================
Core orchestrator for Memory persistence, semantic retrieval, and tenant boundary enforcement (S27.6, S27.7).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional
from pydantic import JsonValue

if TYPE_CHECKING:
    from ai.memory.policy import MemoryPolicy

from ai.memory.embeddings import EmbeddingProvider
from ai.memory.models import (
    Clock,
    EmbeddingRecord,
    MemoryCandidate,
    MemoryEntry,
    MemoryFilter,
    MemorySearchResult,
    MemoryWriteDecision,
    SystemClock,
    TrustedTenantContext,
)
from ai.memory.normalization import ContentNormalizer
from ai.memory.repository import MemoryRepository
from ai.memory.types import (
    ConfidenceLevel,
    EpistemicStatus,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
    WriteDecisionType,
    confidence_to_level,
)


class TenantAuthorizationError(PermissionError):
    """Raised when an operation attempts to cross tenant or project isolation boundaries."""
    pass


class MemoryService:
    """
    Authoritative coordinator for tenant-isolated memory storage and retrieval.
    """

    MAX_RETRIEVAL_LIMIT = 100

    def __init__(
        self,
        repository: MemoryRepository,
        embedding_provider: EmbeddingProvider,
        clock: Optional[Clock] = None,
        policy: Optional[MemoryPolicy] = None,  # Injected MemoryPolicy for S27.7
    ):
        self.repository = repository
        self.embedding_provider = embedding_provider
        self.clock: Clock = clock or SystemClock()
        self.policy = policy

    def store_memory(
        self,
        context: TrustedTenantContext,
        content: str,
        memory_type: MemoryType,
        scope: MemoryScope,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source_type: SourceType = SourceType.USER_STATEMENT,
        source_id: Optional[str] = None,
        confidence: float = 0.9,
        epistemic_status: EpistemicStatus = EpistemicStatus.EXPLICIT,
        expires_at: Optional[datetime] = None,
        storage_ref: Optional[str] = None,
        structured_payload: Optional[Dict[str, JsonValue]] = None,
        metadata: Optional[Dict[str, JsonValue]] = None,
    ) -> MemoryEntry:
        """
        Persists a validated memory entry and indexes its vector embedding.
        """
        # 1. Validate tenant permissions
        self._validate_tenant_access(context, project_id=project_id, user_id=user_id, scope=scope)

        now = self.clock.now_utc()
        norm_content = ContentNormalizer.normalize_text(content)
        content_hash = ContentNormalizer.compute_content_hash(norm_content, structured_payload)
        conf_level = confidence_to_level(confidence)

        entry = MemoryEntry(
            id=f"mem_{uuid.uuid4().hex[:16]}",
            workspace_id=context.workspace_id,
            user_id=user_id or context.user_id,
            project_id=project_id,
            session_id=session_id,
            memory_type=memory_type,
            scope=scope,
            content=norm_content,
            structured_payload=structured_payload,
            source_type=source_type,
            source_id=source_id,
            confidence=confidence,
            confidence_level=conf_level,
            epistemic_status=epistemic_status,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            version=1,
            content_hash=content_hash,
            storage_ref=storage_ref,
            metadata=metadata or {},
        )

        # 2. Persist canonical entry
        persisted = self.repository.create(entry)

        # 3. Generate and store vector embedding
        vector = self.embedding_provider.embed_text(norm_content)
        emb_record = EmbeddingRecord(
            id=f"emb_{uuid.uuid4().hex[:16]}",
            memory_id=persisted.id,
            workspace_id=context.workspace_id,
            project_id=project_id,
            memory_type=memory_type,
            embedding=vector,
            embedding_model=self.embedding_provider.get_model_name(),
            embedding_version=self.embedding_provider.get_version(),
            dimension=self.embedding_provider.get_dimension(),
            created_at=now,
        )
        self.repository.save_embedding(emb_record)

        return persisted

    def get_memory(self, context: TrustedTenantContext, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieves a single memory entry within the caller's authoritative workspace."""
        entry = self.repository.get(memory_id, context.workspace_id)
        if not entry:
            return None

        # Verify project permission if project-scoped
        if entry.project_id and not context.can_access_project(entry.project_id):
            return None

        return entry

    def delete_memory(self, context: TrustedTenantContext, memory_id: str, hard_delete: bool = False) -> bool:
        """Deletes a memory entry within the caller's authoritative workspace."""
        # Ensure item exists in workspace before delete
        existing = self.repository.get(memory_id, context.workspace_id)
        if not existing:
            return False

        if existing.project_id and not context.can_access_project(existing.project_id):
            raise TenantAuthorizationError(f"Access denied to delete memory in project '{existing.project_id}'.")

        return self.repository.delete(memory_id, context.workspace_id, hard_delete=hard_delete)

    def query_structured(
        self,
        context: TrustedTenantContext,
        filter_req: MemoryFilter,
    ) -> List[MemoryEntry]:
        """
        Executes structured filtering with guaranteed tenant boundary enforcement.
        """
        # Ensure query strictly targets the trusted workspace
        if filter_req.workspace_id != context.workspace_id:
            raise TenantAuthorizationError(
                f"Cross-tenant query rejected: Context workspace '{context.workspace_id}' "
                f"cannot query requested workspace '{filter_req.workspace_id}'."
            )

        # Validate project permissions
        if filter_req.project_id and not context.can_access_project(filter_req.project_id):
            return []

        # Bound the query limit safely
        safe_limit = max(1, min(filter_req.limit, self.MAX_RETRIEVAL_LIMIT))
        bounded_filter = filter_req.model_copy(update={"limit": safe_limit})

        entries = self.repository.query_structured(bounded_filter)

        # Post-filter out project records if caller has restricted project access list
        if context.accessible_projects is not None:
            entries = [e for e in entries if e.project_id is None or context.can_access_project(e.project_id)]

        return entries

    def query_semantic(
        self,
        context: TrustedTenantContext,
        query_text: str,
        filter_req: Optional[MemoryFilter] = None,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> List[MemorySearchResult]:
        """
        Executes tenant-isolated vector semantic search.
        
        Guarantees:
        - workspace_id is enforced directly before vector similarity calculation.
        - Results are ordered deterministically by (similarity DESC, confidence DESC, updated_at DESC, id ASC).
        """
        norm_query = ContentNormalizer.normalize_text(query_text)
        query_vector = self.embedding_provider.embed_text(norm_query)

        # Ensure filter aligns with context workspace
        if filter_req:
            if filter_req.workspace_id != context.workspace_id:
                raise TenantAuthorizationError("Cross-tenant semantic query rejected.")
            if filter_req.project_id and not context.can_access_project(filter_req.project_id):
                return []
        else:
            filter_req = MemoryFilter(workspace_id=context.workspace_id)

        safe_limit = max(1, min(limit, self.MAX_RETRIEVAL_LIMIT))

        matches = self.repository.query_semantic(
            workspace_id=context.workspace_id,
            query_vector=query_vector,
            filter=filter_req,
            limit=safe_limit,
            min_similarity=min_similarity,
        )

        # Filter out unauthorized projects if restricted
        if context.accessible_projects is not None:
            matches = [m for m in matches if m.entry.project_id is None or context.can_access_project(m.entry.project_id)]

        return matches

    def supersede_memory(
        self,
        context: TrustedTenantContext,
        old_id: str,
        new_content: str,
        confidence: float = 0.9,
        source_type: SourceType = SourceType.USER_STATEMENT,
        metadata: Optional[Dict[str, JsonValue]] = None,
        structured_payload: Optional[Dict[str, JsonValue]] = None,
    ) -> MemoryEntry:
        """
        Supersedes an existing active memory with a newer revision.
        """
        existing = self.repository.get(old_id, context.workspace_id)
        if not existing:
            raise KeyError(f"Memory '{old_id}' not found in workspace '{context.workspace_id}'.")

        self._validate_tenant_access(context, project_id=existing.project_id, user_id=existing.user_id, scope=existing.scope)

        now = self.clock.now_utc()
        norm_content = ContentNormalizer.normalize_text(new_content)
        target_payload = structured_payload if structured_payload is not None else existing.structured_payload
        content_hash = ContentNormalizer.compute_content_hash(norm_content, target_payload)

        new_entry = MemoryEntry(
            id=f"mem_{uuid.uuid4().hex[:16]}",
            workspace_id=context.workspace_id,
            user_id=existing.user_id,
            project_id=existing.project_id,
            session_id=existing.session_id,
            memory_type=existing.memory_type,
            scope=existing.scope,
            content=norm_content,
            structured_payload=target_payload,
            source_type=source_type,
            source_id=existing.source_id,
            confidence=confidence,
            confidence_level=confidence_to_level(confidence),
            epistemic_status=existing.epistemic_status,
            status=MemoryStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            expires_at=existing.expires_at,
            version=existing.version + 1,
            content_hash=content_hash,
            supersedes_id=old_id,
            storage_ref=existing.storage_ref,
            metadata=metadata or existing.metadata,
        )

        superseded = self.repository.supersede(old_id, new_entry)

        # Update embedding for the new entry
        vector = self.embedding_provider.embed_text(norm_content)
        emb_record = EmbeddingRecord(
            id=f"emb_{uuid.uuid4().hex[:16]}",
            memory_id=superseded.id,
            workspace_id=context.workspace_id,
            project_id=existing.project_id,
            memory_type=existing.memory_type,
            embedding=vector,
            embedding_model=self.embedding_provider.get_model_name(),
            embedding_version=self.embedding_provider.get_version(),
            dimension=self.embedding_provider.get_dimension(),
            created_at=now,
        )
        self.repository.save_embedding(emb_record)

        return superseded

    def propose_candidate(
        self,
        context: TrustedTenantContext,
        candidate: MemoryCandidate,
    ) -> MemoryWriteDecision:
        """
        S27.7 Entrypoint: Evaluates an AI or domain candidate through MemoryPolicy.
        Only persists when the policy decision permits.
        """
        if self.policy is None:
            raise RuntimeError("MemoryPolicy is not configured on MemoryService.")

        decision = self.policy.evaluate_candidate(context, candidate, repository=self.repository)

        if decision.decision_type == WriteDecisionType.STORE:
            created = self.store_memory(
                context=context,
                content=decision.normalized_content or candidate.content,
                memory_type=decision.final_type or candidate.proposed_type,
                scope=decision.final_scope or candidate.proposed_scope,
                project_id=candidate.project_id,
                session_id=candidate.session_id,
                user_id=candidate.user_id,
                source_type=candidate.source_type,
                source_id=candidate.source_id,
                confidence=decision.final_confidence or candidate.suggested_confidence or 0.8,
                epistemic_status=decision.epistemic_status or EpistemicStatus.EXPLICIT,
                expires_at=decision.expires_at,
                storage_ref=candidate.storage_ref,
                structured_payload=candidate.structured_payload,
                metadata=candidate.metadata,
            )
            decision.target_entry_id = created.id

        elif decision.decision_type == WriteDecisionType.SUPERSEDE:
            if decision.supersedes_id:
                superseded = self.supersede_memory(
                    context=context,
                    old_id=decision.supersedes_id,
                    new_content=decision.normalized_content or candidate.content,
                    confidence=decision.final_confidence or 0.9,
                    source_type=candidate.source_type,
                    metadata=candidate.metadata,
                    structured_payload=candidate.structured_payload,
                )
                decision.target_entry_id = superseded.id

        elif decision.decision_type == WriteDecisionType.MERGE:
            if decision.target_entry_id:
                existing = self.repository.get(decision.target_entry_id, context.workspace_id)
                if existing:
                    # Reinforce evidence count and confidence
                    ev_count = existing.metadata.get("evidence_count", 1) + 1
                    existing.metadata["evidence_count"] = ev_count
                    if decision.final_confidence is not None:
                        existing.confidence = decision.final_confidence
                        existing.confidence_level = confidence_to_level(decision.final_confidence)
                    self.repository.update(existing)

        return decision

    def _validate_tenant_access(
        self,
        context: TrustedTenantContext,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        scope: Optional[MemoryScope] = None,
    ) -> None:
        """Validates that context has authoritative authorization for the requested boundaries."""
        if scope == MemoryScope.GLOBAL:
            if context.workspace_id not in ("global", "system", "shared") and not context.is_admin:
                raise TenantAuthorizationError(
                    f"Workspace '{context.workspace_id}' cannot write to GLOBAL scope."
                )

        if project_id and not context.can_access_project(project_id):
            raise TenantAuthorizationError(
                f"Actor '{context.user_id}' does not have access to project '{project_id}'."
            )

        if user_id and not context.can_access_user(user_id):
            raise TenantAuthorizationError(
                f"Actor '{context.user_id}' cannot write memory for user '{user_id}'."
            )
