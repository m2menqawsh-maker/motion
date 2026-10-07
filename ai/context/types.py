"""
ai/context/types.py
===================
Canonical types, enums, and data contracts for Context Builder (S27.8).

Invariants:
- Strict validation policy: unexpected fields forbidden (extra="forbid").
- Strict type checking: coercion of mismatched primitives disabled (strict=True).
- Immutability: models are frozen value objects (frozen=True).
- Structured JSON: no unrestricted dict[str, Any]; typed via JsonValue.
- Provider-neutral: no vendor-specific logic or data structures.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from pydantic import ConfigDict, Field, JsonValue

from ai.contracts.base import AIContractModel, StrictDecimal, TzAwareDatetime, strict_enum
from ai.contracts.common import CapabilityType, CapabilityTypeEnum
from ai.memory.models import TrustedTenantContext


class ContextSection(str, Enum):
    """Canonical context sections in authoritative prefix ordering."""
    SYSTEM = "SYSTEM"
    TOOLS = "TOOLS"
    SHARED = "SHARED"
    PROJECT = "PROJECT"
    MEMORY = "MEMORY"
    KNOWLEDGE = "KNOWLEDGE"
    CONVERSATION = "CONVERSATION"
    MEDIA = "MEDIA"
    REQUEST = "REQUEST"


class ContextAuthority(str, Enum):
    """
    Authoritative classification of context provenance.
    Ordered by epistemic precedence:
    SYSTEM_AUTHORITY (6) > DOMAIN_SOURCE_OF_TRUTH (5) > HUMAN_CONFIRMED (4) >
    EXPLICIT_USER (3) > DERIVED (2) > INFERRED (1)
    """
    SYSTEM_AUTHORITY = "SYSTEM_AUTHORITY"
    DOMAIN_SOURCE_OF_TRUTH = "DOMAIN_SOURCE_OF_TRUTH"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    EXPLICIT_USER = "EXPLICIT_USER"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"


class ContextSourceType(str, Enum):
    """Origin of a candidate context item."""
    SYSTEM_POLICY = "SYSTEM_POLICY"
    TOOL_SCHEMA = "TOOL_SCHEMA"
    SHARED_CONFIG = "SHARED_CONFIG"
    DOMAIN_SERVICE = "DOMAIN_SERVICE"
    MEMORY = "MEMORY"
    KNOWLEDGE = "KNOWLEDGE"
    CONVERSATION_HISTORY = "CONVERSATION_HISTORY"
    MEDIA_INTEL = "MEDIA_INTEL"
    REQUEST_PAYLOAD = "REQUEST_PAYLOAD"


class ExclusionReason(str, Enum):
    """Exclusion reason codes for context audit diagnostics."""
    IRRELEVANT = "IRRELEVANT"
    DUPLICATE = "DUPLICATE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    EXPIRED = "EXPIRED"
    WRONG_SCOPE = "WRONG_SCOPE"
    WRONG_TENANT = "WRONG_TENANT"
    AUTHORITY_CONFLICT = "AUTHORITY_CONFLICT"
    TOKEN_BUDGET = "TOKEN_BUDGET"
    SUPERSEDED = "SUPERSEDED"
    SECRET_DETECTED = "SECRET_DETECTED"
    PROJECT_ACCESS_DENIED = "PROJECT_ACCESS_DENIED"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"


# Strict annotated enum types for model fields
ContextSectionEnum = strict_enum(ContextSection)
ContextAuthorityEnum = strict_enum(ContextAuthority)
ContextSourceTypeEnum = strict_enum(ContextSourceType)
ExclusionReasonEnum = strict_enum(ExclusionReason)

# Numerical authority precedence mapping
AUTHORITY_PRECEDENCE: Dict[ContextAuthority, int] = {
    ContextAuthority.SYSTEM_AUTHORITY: 6,
    ContextAuthority.DOMAIN_SOURCE_OF_TRUTH: 5,
    ContextAuthority.HUMAN_CONFIRMED: 4,
    ContextAuthority.EXPLICIT_USER: 3,
    ContextAuthority.DERIVED: 2,
    ContextAuthority.INFERRED: 1,
}


class ContextBuilderError(Exception):
    """Base exception for Context Builder operations."""
    pass


class ProjectAccessDeniedError(PermissionError, ContextBuilderError):
    """Raised when actor attempts to access a project without authorization."""
    pass


class ProjectNotFoundError(LookupError, ContextBuilderError):
    """Raised when the requested project does not exist or was deleted."""
    pass


class BudgetExceededError(ContextBuilderError):
    """Raised when non-evictable items exceed available input budget."""
    pass


class ContextItem(AIContractModel):
    """
    An individual candidate or assembled item within a context section.
    
    Guarantees:
    - Full provenance tracking (source_type, source_id, authority, content_hash).
    - Canonical key support for semantic deduplication and conflict resolution.
    - Immutability enforced via AIContractModel.
    """
    id: str = Field(min_length=1, description="Unique item identifier")
    section: ContextSectionEnum = Field(description="Target context section")
    content: str = Field(min_length=1, description="Textual payload")
    source_type: ContextSourceTypeEnum = Field(description="Originating source subsystem")
    source_id: Optional[str] = Field(default=None, description="Identifier of source record if applicable")
    authority: ContextAuthorityEnum = Field(description="Epistemic authority tier")
    canonical_key: Optional[str] = Field(
        default=None,
        description="Semantic key for deduplication and conflict resolution (e.g. 'fact:project:status')"
    )
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Task relevance score")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence metric of context")
    recency_timestamp: Optional[TzAwareDatetime] = Field(default=None, description="Timezone-aware timestamp")
    estimated_tokens: int = Field(default=0, ge=0, description="Estimated token count")
    content_hash: str = Field(min_length=1, description="SHA-256 hash of item content")
    compressed: bool = Field(default=False, description="Whether item was compressed/trimmed to fit budget")
    metadata: Dict[str, JsonValue] = Field(default_factory=dict, description="Typed metadata")

    @classmethod
    def compute_content_hash(cls, content: str) -> str:
        """Computes deterministic SHA-256 hash of content."""
        return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


class ContextExclusion(AIContractModel):
    """Audit record for a rejected or dropped context candidate."""
    candidate_id: str = Field(min_length=1, description="Candidate identifier")
    section: ContextSectionEnum = Field(description="Target context section")
    reason: ExclusionReasonEnum = Field(description="Exclusion reason code")
    details: str = Field(min_length=1, description="Human-readable explanation")
    source_type: ContextSourceTypeEnum = Field(description="Source of candidate")


class ContextDiagnostics(AIContractModel):
    """Diagnostic metrics and exclusion log for a context build run."""
    total_candidates_retrieved: int = Field(default=0, ge=0)
    total_items_included: int = Field(default=0, ge=0)
    total_items_excluded: int = Field(default=0, ge=0)
    items_compressed: int = Field(default=0, ge=0)
    tokens_by_section: Dict[str, int] = Field(default_factory=dict)
    total_estimated_tokens: int = Field(default=0, ge=0)
    output_reserve: int = Field(default=0, ge=0)
    budget_ceiling: int = Field(default=0, ge=0)
    remaining_budget: int = Field(default=0, ge=0)
    exclusions: List[ContextExclusion] = Field(default_factory=list)


class ContextSectionPackage(AIContractModel):
    """A bounded, sorted set of context items belonging to a single section."""
    section: ContextSectionEnum = Field(description="Section classification")
    items: List[ContextItem] = Field(default_factory=list, description="Ordered items in section")
    estimated_tokens: int = Field(default=0, ge=0, description="Total tokens in section")


class ContextRequest(AIContractModel):
    """
    Canonical request contract for building prompt-ready context.
    
    Guarantees:
    - Server-side trusted tenant context (trusted_context) cannot be forged by model.
    - Provider-neutral: capability and task specify requirements.
    """
    request_id: str = Field(min_length=1, description="Unique request identifier")
    trusted_context: TrustedTenantContext = Field(description="Authoritative server-side tenant boundary")
    capability: CapabilityTypeEnum = Field(description="Requested domain capability")
    intent: Optional[str] = Field(default=None, description="Optional intent or task description")
    project_id: Optional[str] = Field(default=None, description="Optional associated project identifier")
    session_id: Optional[str] = Field(default=None, description="Optional conversation session identifier")
    query_text: Optional[str] = Field(default=None, description="Current user query or prompt string")
    input_data: Dict[str, JsonValue] = Field(default_factory=dict, description="Structured request inputs")
    recipe_ref: Optional[str] = Field(default=None, description="Optional reference to approved recipe")
    token_budget: Optional[int] = Field(default=None, ge=1, description="Optional override for total token budget")
    output_reserve: Optional[int] = Field(default=None, ge=0, description="Optional override for output reserve")
    metadata: Dict[str, JsonValue] = Field(default_factory=dict, description="Constrained request metadata")
    created_at: TzAwareDatetime = Field(description="Timezone-aware request creation timestamp")


class ContextPackage(AIContractModel):
    """
    Canonical assembled, bounded, deterministic context package (S27.8).
    
    Prompt-ready output comprising all 9 canonical sections, context hash,
    and build diagnostics.
    """
    request_id: str = Field(min_length=1, description="Originating request ID")
    context_hash: str = Field(min_length=1, description="Canonical deterministic SHA-256 hash of assembled context")
    system_policy: ContextSectionPackage = Field(description="Authoritative system directives and taste gates")
    tool_schema_context: ContextSectionPackage = Field(description="Tool definitions placeholder (S27.9)")
    shared_context: ContextSectionPackage = Field(description="Shared workspace configurations and brand kits")
    project_context: ContextSectionPackage = Field(description="Canonical project facts from domain services")
    memory_context: ContextSectionPackage = Field(description="Relevant learned preferences and decisions")
    knowledge_context: ContextSectionPackage = Field(description="Relevant playbooks, playbooks, and documentation")
    conversation_context: ContextSectionPackage = Field(description="Recent conversation turns and summaries")
    media_context: ContextSectionPackage = Field(description="Media asset metadata and intelligence refs")
    current_request: ContextSectionPackage = Field(description="Current request inputs and user prompt")
    diagnostics: ContextDiagnostics = Field(description="Build diagnostics and exclusions")

    def all_items(self) -> List[ContextItem]:
        """Returns all items in strict canonical prefix order."""
        return (
            self.system_policy.items
            + self.tool_schema_context.items
            + self.shared_context.items
            + self.project_context.items
            + self.memory_context.items
            + self.knowledge_context.items
            + self.conversation_context.items
            + self.media_context.items
            + self.current_request.items
        )

    def get_section_package(self, section: ContextSection) -> ContextSectionPackage:
        """Retrieves section package by enum."""
        mapping = {
            ContextSection.SYSTEM: self.system_policy,
            ContextSection.TOOLS: self.tool_schema_context,
            ContextSection.SHARED: self.shared_context,
            ContextSection.PROJECT: self.project_context,
            ContextSection.MEMORY: self.memory_context,
            ContextSection.KNOWLEDGE: self.knowledge_context,
            ContextSection.CONVERSATION: self.conversation_context,
            ContextSection.MEDIA: self.media_context,
            ContextSection.REQUEST: self.current_request,
        }
        return mapping[section]

    def to_prompt_text(self) -> str:
        """Renders assembled context as prompt-ready text with strict structural boundaries."""
        parts: List[str] = []

        if self.system_policy.items:
            parts.append("=== SYSTEM POLICY & DIRECTIVES ===")
            for item in self.system_policy.items:
                parts.append(item.content)

        if self.shared_context.items:
            parts.append("\n=== SHARED WORKSPACE CONFIGURATION ===")
            for item in self.shared_context.items:
                parts.append(item.content)

        if self.project_context.items:
            parts.append("\n=== CANONICAL PROJECT FACTS (AUTHORITATIVE) ===")
            for item in self.project_context.items:
                parts.append(item.content)

        if self.media_context.items:
            parts.append("\n=== MEDIA CONTEXT & ASSETS ===")
            for item in self.media_context.items:
                parts.append(item.content)

        if self.knowledge_context.items:
            parts.append("\n=== RELEVANT KNOWLEDGE & PLAYBOOKS ===")
            for item in self.knowledge_context.items:
                parts.append(item.content)

        if self.memory_context.items:
            parts.append("\n=== DATA: RELEVANT MEMORY (UNTRUSTED USER CONTEXT) ===")
            for item in self.memory_context.items:
                parts.append(item.content)

        if self.conversation_context.items:
            parts.append("\n=== RECENT CONVERSATION HISTORY ===")
            for item in self.conversation_context.items:
                parts.append(item.content)

        if self.current_request.items:
            parts.append("\n=== CURRENT REQUEST ===")
            for item in self.current_request.items:
                parts.append(item.content)

        return "\n".join(parts)

    def to_messages(self) -> List[Dict[str, str]]:
        """Renders assembled context as canonical provider-neutral messages."""
        messages: List[Dict[str, str]] = []

        # System message containing authoritative policy & shared config
        system_content_parts: List[str] = []
        for it in self.system_policy.items:
            system_content_parts.append(it.content)
        for it in self.shared_context.items:
            system_content_parts.append(it.content)

        if system_content_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_content_parts)})

        # User message containing contextual data and current request
        user_content_parts: List[str] = []

        if self.project_context.items:
            user_content_parts.append("--- CANONICAL PROJECT FACTS ---\n" + "\n".join(it.content for it in self.project_context.items))

        if self.media_context.items:
            user_content_parts.append("--- MEDIA CONTEXT ---\n" + "\n".join(it.content for it in self.media_context.items))

        if self.knowledge_context.items:
            user_content_parts.append("--- RELEVANT KNOWLEDGE ---\n" + "\n".join(it.content for it in self.knowledge_context.items))

        if self.memory_context.items:
            user_content_parts.append("--- RELEVANT MEMORY DATA (DATA ONLY) ---\n" + "\n".join(it.content for it in self.memory_context.items))

        if self.conversation_context.items:
            user_content_parts.append("--- CONVERSATION HISTORY ---\n" + "\n".join(it.content for it in self.conversation_context.items))

        if self.current_request.items:
            user_content_parts.append("--- REQUEST ---\n" + "\n".join(it.content for it in self.current_request.items))

        if user_content_parts:
            messages.append({"role": "user", "content": "\n\n".join(user_content_parts)})

        return messages
