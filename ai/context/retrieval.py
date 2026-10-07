"""
ai/context/retrieval.py
=======================
Candidate context retrieval orchestrator (S27.8).

Retrieves canonical domain facts, tenant-isolated memory records,
approved playbooks/recipes (knowledge), system policies, and request payloads.

Invariants:
- Canonical project state comes strictly from Domain Services (ProjectService, AssetService, etc.).
- AI Memory holds only derived insights, user preferences, and decisions.
- Direct repository access is strictly forbidden; coordinates via MemoryService.
- Multi-tenant boundary: workspace_id and project access are strictly enforced.
- Secret sanitization: prevents credential and key leakage into context candidates.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol, Tuple
from pydantic import JsonValue

from ai.contracts.base import TzAwareDatetime
from ai.contracts.common import CapabilityType
from ai.contracts.memory import MemoryType
from ai.context.needs import ContextNeeds
from ai.context.types import (
    ContextAuthority,
    ContextExclusion,
    ContextItem,
    ContextRequest,
    ContextSection,
    ContextSourceType,
    ExclusionReason,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
)
from ai.memory.models import MemoryEntry, MemoryFilter, MemorySearchResult, TrustedTenantContext
from ai.memory.service import MemoryService
from ai.memory.types import EpistemicStatus, MemoryStatus, SourceType

# Secret detection patterns for defense-in-depth sanitization
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+(?:RSA|EC|OPENSSH|PGP)?\s*PRIVATE\s+KEY-----", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
]


def contains_secret(text: str) -> bool:
    """Verifies whether text contains credentials, private keys, or API tokens."""
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return True
    return False


class KnowledgeRetriever(Protocol):
    """Protocol for abstracting knowledge retrieval without filesystem crawls."""
    def retrieve_knowledge(
        self,
        context: TrustedTenantContext,
        tags: List[str],
        query: Optional[str] = None,
        recipe_ref: Optional[str] = None,
        limit: int = 10,
    ) -> List[ContextItem]:
        ...


class KnowledgeDocument:
    """An approved, structured knowledge asset (playbook, reference, recipe)."""
    def __init__(
        self,
        doc_id: str,
        title: str,
        content: str,
        tags: List[str],
        workspace_id: Optional[str] = None,  # None means system global
        authority: ContextAuthority = ContextAuthority.SYSTEM_AUTHORITY,
    ):
        self.doc_id = doc_id
        self.title = title
        self.content = content
        self.tags = [t.lower() for t in tags]
        self.workspace_id = workspace_id
        self.authority = authority


class DeterministicKnowledgeRetriever:
    """
    In-memory canonical knowledge retriever for playbooks, references, and recipes.
    
    Guarantees:
    - Enforces tenant isolation: workspace-specific knowledge never leaks across workspaces.
    - System global knowledge (workspace_id=None) is available safely to all tenants.
    """
    def __init__(self, documents: Optional[List[KnowledgeDocument]] = None):
        self._documents: Dict[str, KnowledgeDocument] = {}
        if documents:
            for doc in documents:
                self.register_document(doc)

    def register_document(self, doc: KnowledgeDocument) -> None:
        self._documents[doc.doc_id] = doc

    def retrieve_knowledge(
        self,
        context: TrustedTenantContext,
        tags: List[str],
        query: Optional[str] = None,
        recipe_ref: Optional[str] = None,
        limit: int = 10,
    ) -> List[ContextItem]:
        results: List[ContextItem] = []
        normalized_tags = {t.lower() for t in tags}
        q_lower = query.lower() if query else ""

        for doc in self._documents.values():
            # Strict tenant safety: workspace-scoped docs must match caller workspace
            if doc.workspace_id is not None and doc.workspace_id != context.workspace_id:
                continue

            # Recipe hook match
            is_recipe_match = recipe_ref and (doc.doc_id == recipe_ref or doc.doc_id.endswith(recipe_ref))

            # Tag match or query text match
            tag_overlap = bool(normalized_tags.intersection(set(doc.tags)))
            query_match = bool(q_lower and (q_lower in doc.title.lower() or q_lower in doc.content.lower()))

            if is_recipe_match or tag_overlap or query_match:
                item_content = f"[{doc.title}]\n{doc.content}"
                if contains_secret(item_content):
                    continue

                rel_score = 1.0 if is_recipe_match else (0.85 if tag_overlap else 0.70)
                results.append(
                    ContextItem(
                        id=f"know_{doc.doc_id}",
                        section=ContextSection.KNOWLEDGE,
                        content=item_content,
                        source_type=ContextSourceType.KNOWLEDGE,
                        source_id=doc.doc_id,
                        authority=doc.authority,
                        canonical_key=f"knowledge:{doc.doc_id}",
                        relevance_score=rel_score,
                        confidence=0.95,
                        content_hash=ContextItem.compute_content_hash(item_content),
                    )
                )
                if len(results) >= limit:
                    break

        return results


class ProjectFactRetriever:
    """
    Retrieves authoritative project state facts strictly from Domain Services.
    """
    def __init__(
        self,
        project_service: Optional[object] = None,
        asset_service: Optional[object] = None,
        review_service: Optional[object] = None,
    ):
        self._project_service = project_service
        self._asset_service = asset_service
        self._review_service = review_service

    def retrieve_project_facts(
        self,
        context: TrustedTenantContext,
        project_id: str,
        needs: ContextNeeds,
    ) -> List[ContextItem]:
        # 1. Authoritative access check
        if not context.can_access_project(project_id):
            raise ProjectAccessDeniedError(
                f"Actor '{context.user_id}' denied access to project '{project_id}'."
            )

        facts: List[ContextItem] = []

        # 2. Lifecycle DTO retrieval from ProjectService
        ps = self._project_service
        if ps is None:
            try:
                from api.services.project_service import ProjectService
                ps = ProjectService
            except ImportError:
                ps = None

        if ps is not None:
            try:
                dto = ps.get_lifecycle_dto(project_id)
                if dto is None:
                    raise ProjectNotFoundError(f"Project '{project_id}' not found.")
            except ProjectNotFoundError:
                raise
            except Exception as exc:
                if "not found" in str(exc).lower():
                    raise ProjectNotFoundError(f"Project '{project_id}' not found: {exc}")
                raise ProjectNotFoundError(f"Failed to retrieve project '{project_id}': {exc}")

            # Extract authoritative facts
            lstate_val = getattr(dto, "lifecycle_state", None) or "UNKNOWN"
            revision_val = getattr(dto, "revision", 1)
            actions = getattr(dto, "allowed_actions", []) or []
            blocked = getattr(dto, "blocked_reason", None)

            # Fact: Lifecycle State
            status_content = f"Project status: {lstate_val}"
            facts.append(
                ContextItem(
                    id=f"fact_proj_status_{project_id}",
                    section=ContextSection.PROJECT,
                    content=status_content,
                    source_type=ContextSourceType.DOMAIN_SERVICE,
                    source_id=f"project:{project_id}:status",
                    authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
                    canonical_key="fact:project:status",
                    relevance_score=1.0,
                    confidence=1.0,
                    content_hash=ContextItem.compute_content_hash(status_content),
                )
            )

            # Fact: Revision
            rev_content = f"Project revision: {revision_val}"
            facts.append(
                ContextItem(
                    id=f"fact_proj_rev_{project_id}",
                    section=ContextSection.PROJECT,
                    content=rev_content,
                    source_type=ContextSourceType.DOMAIN_SERVICE,
                    source_id=f"project:{project_id}:revision",
                    authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
                    canonical_key="fact:project:revision",
                    relevance_score=1.0,
                    confidence=1.0,
                    content_hash=ContextItem.compute_content_hash(rev_content),
                )
            )

            # Fact: Allowed actions
            if actions:
                acts_content = f"Allowed actions: {', '.join(actions)}"
                facts.append(
                    ContextItem(
                        id=f"fact_proj_acts_{project_id}",
                        section=ContextSection.PROJECT,
                        content=acts_content,
                        source_type=ContextSourceType.DOMAIN_SERVICE,
                        source_id=f"project:{project_id}:allowed_actions",
                        authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
                        canonical_key="fact:project:allowed_actions",
                        relevance_score=0.9,
                        confidence=1.0,
                        content_hash=ContextItem.compute_content_hash(acts_content),
                    )
                )

            # Fact: Blocked reason
            if blocked:
                block_content = f"Blocked reason: {blocked}"
                facts.append(
                    ContextItem(
                        id=f"fact_proj_blocked_{project_id}",
                        section=ContextSection.PROJECT,
                        content=block_content,
                        source_type=ContextSourceType.DOMAIN_SERVICE,
                        source_id=f"project:{project_id}:blocked_reason",
                        authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
                        canonical_key="fact:project:blocked_reason",
                        relevance_score=0.95,
                        confidence=1.0,
                        content_hash=ContextItem.compute_content_hash(block_content),
                    )
                )

        # 3. Review status from ReviewService
        if needs.needs_review_status:
            rs = self._review_service
            if rs is None:
                try:
                    from scripts.core.review_service import ReviewService
                    rs = ReviewService
                except ImportError:
                    rs = None

            if rs is not None:
                try:
                    rev_status = rs.get_review_status(project_id)
                    rev_content = (
                        f"Review state: {rev_status.lifecycle_state}, "
                        f"decision: {rev_status.active_decision or 'NONE'}, "
                        f"stale: {rev_status.is_stale}"
                    )
                    facts.append(
                        ContextItem(
                            id=f"fact_proj_review_{project_id}",
                            section=ContextSection.PROJECT,
                            content=rev_content,
                            source_type=ContextSourceType.DOMAIN_SERVICE,
                            source_id=f"project:{project_id}:review",
                            authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
                            canonical_key="fact:project:review_status",
                            relevance_score=0.95,
                            confidence=1.0,
                            content_hash=ContextItem.compute_content_hash(rev_content),
                        )
                    )
                except Exception:
                    pass

        # 4. Assets from AssetService
        if needs.needs_assets:
            ast_svc = self._asset_service
            if ast_svc is None:
                try:
                    from api.services.asset_service import AssetService
                    ast_svc = AssetService
                except ImportError:
                    ast_svc = None

            if ast_svc is not None:
                try:
                    assets_list = ast_svc.list_assets(project_id)
                    for a in assets_list:
                        ast_id = a.get("asset_id", "")
                        kind = a.get("kind", "")
                        fname = a.get("filename", "")
                        status = a.get("status", "")
                        ast_content = f"Asset {ast_id}: {fname} (kind={kind}, status={status})"
                        facts.append(
                            ContextItem(
                                id=f"fact_asset_{ast_id}",
                                section=ContextSection.MEDIA,
                                content=ast_content,
                                source_type=ContextSourceType.DOMAIN_SERVICE,
                                source_id=f"asset:{ast_id}",
                                authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
                                canonical_key=f"fact:asset:{ast_id}",
                                relevance_score=0.85,
                                confidence=1.0,
                                content_hash=ContextItem.compute_content_hash(ast_content),
                            )
                        )
                except Exception:
                    pass

        return facts


class MemoryRetriever:
    """
    Retrieves tenant-isolated, active, unexpired memory items via MemoryService.
    
    Guarantees:
    - Never accesses MemoryRepository directly.
    - Strictly filters out wrong-tenant and expired records.
    - Excludes irrelevant preference domains (e.g. font preferences during audio workflows).
    """
    def __init__(self, memory_service: Optional[MemoryService] = None):
        self._memory_service = memory_service

    def retrieve_memories(
        self,
        context: TrustedTenantContext,
        request: ContextRequest,
        needs: ContextNeeds,
        now: Optional[datetime] = None,
    ) -> Tuple[List[ContextItem], List[ContextExclusion]]:
        if self._memory_service is None:
            return [], []

        now_dt = now or datetime.now(timezone.utc)
        items: List[ContextItem] = []
        exclusions: List[ContextExclusion] = []

        for mtype_str in needs.allowed_memory_types:
            try:
                from ai.memory.types import MemoryType as DomainMemoryType
                mtype = DomainMemoryType(mtype_str)
            except ValueError:
                continue

            is_project_scoped = mtype in (DomainMemoryType.PROJECT, DomainMemoryType.DECISION)
            filter_req = MemoryFilter(
                workspace_id=context.workspace_id,
                project_id=request.project_id if is_project_scoped else None,
                memory_type=mtype,
                include_inactive=True,
                limit=100,
            )

            try:
                entries: List[MemoryEntry] = self._memory_service.query_structured(context, filter_req)
            except Exception as exc:
                continue

            for entry in entries:
                # 1. Tenant boundary enforcement
                if entry.workspace_id != context.workspace_id:
                    exclusions.append(
                        ContextExclusion(
                            candidate_id=entry.id,
                            section=ContextSection.MEMORY,
                            reason=ExclusionReason.WRONG_TENANT,
                            details=f"Entry workspace '{entry.workspace_id}' != trusted workspace '{context.workspace_id}'.",
                            source_type=ContextSourceType.MEMORY,
                        )
                    )
                    continue

                # 2. Expiration check
                if entry.expires_at is not None:
                    exp = entry.expires_at
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if exp <= now_dt:
                        exclusions.append(
                            ContextExclusion(
                                candidate_id=entry.id,
                                section=ContextSection.MEMORY,
                                reason=ExclusionReason.EXPIRED,
                                details=f"Entry expired at {exp.isoformat()}.",
                                source_type=ContextSourceType.MEMORY,
                            )
                        )
                        continue

                # 3. Low confidence check
                if entry.confidence < 0.2:
                    exclusions.append(
                        ContextExclusion(
                            candidate_id=entry.id,
                            section=ContextSection.MEMORY,
                            reason=ExclusionReason.LOW_CONFIDENCE,
                            details=f"Confidence {entry.confidence} is below minimum retrieval threshold (0.2).",
                            source_type=ContextSourceType.MEMORY,
                        )
                    )
                    continue

                # 4. Secret check
                if contains_secret(entry.content):
                    exclusions.append(
                        ContextExclusion(
                            candidate_id=entry.id,
                            section=ContextSection.MEMORY,
                            reason=ExclusionReason.SECRET_DETECTED,
                            details="Memory candidate contains confidential token or secret.",
                            source_type=ContextSourceType.MEMORY,
                        )
                    )
                    continue

                # 5. Preference domain relevance check
                if entry.memory_type == DomainMemoryType.USER_PREFERENCE:
                    entry_domain = ""
                    if entry.metadata:
                        entry_domain = str(entry.metadata.get("domain", "")).lower()
                    
                    # Inspect content keywords if domain metadata is missing
                    content_lower = entry.content.lower()
                    is_visual = any(w in content_lower for w in ["font", "serif", "color", "aspect", "theme", "layout", "visual"])
                    is_audio = any(w in content_lower for w in ["voice", "pitch", "audio", "mic", "speech", "loudness", "sfx"])

                    is_relevant = False
                    for pd in needs.preference_domains:
                        pd_lower = pd.lower()
                        if entry_domain and pd_lower in entry_domain:
                            is_relevant = True
                            break
                        if is_audio and pd_lower in ["audio", "speech", "voice", "music"]:
                            is_relevant = True
                            break
                        if is_visual and pd_lower in ["visual", "video", "style", "aspect_ratio", "format"]:
                            is_relevant = True
                            break

                    if not is_relevant and (is_visual or is_audio or entry_domain):
                        exclusions.append(
                            ContextExclusion(
                                candidate_id=entry.id,
                                section=ContextSection.MEMORY,
                                reason=ExclusionReason.IRRELEVANT,
                                details=f"User preference '{entry.content[:40]}' is irrelevant to capability {request.capability.value}.",
                                source_type=ContextSourceType.MEMORY,
                            )
                        )
                        continue

                # 6. Epistemic authority mapping
                if entry.source_type == SourceType.USER_STATEMENT or entry.epistemic_status == EpistemicStatus.EXPLICIT:
                    authority = ContextAuthority.HUMAN_CONFIRMED
                elif entry.memory_type == DomainMemoryType.USER_PREFERENCE:
                    authority = ContextAuthority.EXPLICIT_USER
                elif entry.epistemic_status == EpistemicStatus.INFERRED or entry.confidence < 0.6:
                    authority = ContextAuthority.INFERRED
                else:
                    authority = ContextAuthority.DERIVED

                # Determine target section
                if entry.memory_type == DomainMemoryType.CONVERSATION:
                    sec = ContextSection.CONVERSATION
                elif entry.memory_type == DomainMemoryType.MEDIA_INTELLIGENCE:
                    sec = ContextSection.MEDIA
                else:
                    sec = ContextSection.MEMORY

                canonical_key = None
                if entry.metadata and "canonical_key" in entry.metadata:
                    canonical_key = str(entry.metadata["canonical_key"])

                created_tz = entry.created_at
                if created_tz.tzinfo is None:
                    created_tz = created_tz.replace(tzinfo=timezone.utc)

                items.append(
                    ContextItem(
                        id=f"mem_{entry.id}",
                        section=sec,
                        content=entry.content,
                        source_type=ContextSourceType.MEMORY,
                        source_id=entry.id,
                        authority=authority,
                        canonical_key=canonical_key,
                        relevance_score=0.85,
                        confidence=entry.confidence,
                        recency_timestamp=created_tz,
                        content_hash=entry.content_hash,
                    )
                )

        return items, exclusions


class SystemPolicyRetriever:
    """Retrieves authoritative baseline directives, taste gates, and security rules."""
    def retrieve_policies(self) -> List[ContextItem]:
        directives = (
            "System Directives: Clean Video Workspace. Enforce Taste Gates strictly. "
            "Text must never overlap. Maintain modern typography, cinematic zooms, and precise symmetry. "
            "Follow strict lifecycle gating. State transitions must pass through authorized Domain Services."
        )
        return [
            ContextItem(
                id="sys_taste_directives",
                section=ContextSection.SYSTEM,
                content=directives,
                source_type=ContextSourceType.SYSTEM_POLICY,
                source_id="policy:taste_gates",
                authority=ContextAuthority.SYSTEM_AUTHORITY,
                canonical_key="system:policy:taste_gates",
                relevance_score=1.0,
                confidence=1.0,
                content_hash=ContextItem.compute_content_hash(directives),
            )
        ]


class SharedConfigRetriever:
    """Retrieves shared tenant configuration and brand standards."""
    def retrieve_shared_config(self, context: TrustedTenantContext) -> List[ContextItem]:
        config_text = f"Workspace '{context.workspace_id}' baseline video standards: 1080x1920 (9:16) portrait default, 30 fps."
        return [
            ContextItem(
                id=f"shared_cfg_{context.workspace_id}",
                section=ContextSection.SHARED,
                content=config_text,
                source_type=ContextSourceType.SHARED_CONFIG,
                source_id=f"workspace:{context.workspace_id}:config",
                authority=ContextAuthority.SYSTEM_AUTHORITY,
                canonical_key="shared:config:standards",
                relevance_score=0.8,
                confidence=1.0,
                content_hash=ContextItem.compute_content_hash(config_text),
            )
        ]


class RequestRetriever:
    """Extracts ContextItem for current user prompt and structured payload."""
    def retrieve_request_item(self, request: ContextRequest) -> List[ContextItem]:
        items: List[ContextItem] = []
        payload_parts: List[str] = []

        if request.query_text:
            payload_parts.append(f"User Prompt: {request.query_text.strip()}")

        if request.intent:
            payload_parts.append(f"Intent: {request.intent.strip()}")

        if request.input_data:
            import json
            payload_parts.append(f"Input Data: {json.dumps(request.input_data, sort_keys=True)}")

        if not payload_parts:
            payload_parts.append(f"Execute capability: {request.capability.value}")

        content = "\n".join(payload_parts)
        items.append(
            ContextItem(
                id=f"req_{request.request_id}",
                section=ContextSection.REQUEST,
                content=content,
                source_type=ContextSourceType.REQUEST_PAYLOAD,
                source_id=request.request_id,
                authority=ContextAuthority.EXPLICIT_USER,
                canonical_key="request:payload",
                relevance_score=1.0,
                confidence=1.0,
                recency_timestamp=request.created_at,
                content_hash=ContextItem.compute_content_hash(content),
            )
        )
        return items
