"""
ai/contracts/prompt.py
======================
Canonical typed contracts for Prompt Management & Lifecycle (S27.18).

Invariants:
- Versioned immutable entities (prompt_id + version + hash).
- Lifecycle states: DRAFT -> TESTING -> PRODUCTION -> RETIRED.
- Direct DRAFT -> PRODUCTION promotion is strictly forbidden.
- AI/model has zero authority to promote prompts.
- No random unbounded strings or dict[str, Any] at boundaries.
"""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, JsonValue, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel, TzAwareDatetime, strict_enum


class PromptStatus(str, Enum):
    """Authoritative lifecycle status for versioned prompts."""
    DRAFT = "DRAFT"
    TESTING = "TESTING"
    PRODUCTION = "PRODUCTION"
    RETIRED = "RETIRED"


PromptStatusEnum = strict_enum(PromptStatus)


class PromptMetadata(AIContractModel):
    """Typed audit metadata for prompt entities."""
    author: Optional[str] = Field(default=None, description="Author identifier or creator role")
    description: Optional[str] = Field(default=None, description="Human-readable description of prompt purpose")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    eval_gate_id: Optional[str] = Field(default=None, description="Eval run/gate approval ID proving quality")
    eval_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Verified benchmark score")


class PromptContract(AIContractModel):
    """
    Authoritative versioned prompt entity.
    Guarantees immutable content hash and strict version progression.
    """
    prompt_id: str = Field(min_length=1, description="Canonical identifier of the prompt template")
    version: int = Field(ge=1, description="Strict monotonic integer version (1, 2, 3...)")
    hash: str = Field(min_length=8, description="Deterministic SHA-256 hash of template + system_prompt")
    status: PromptStatusEnum = Field(description="Current lifecycle state")
    template: str = Field(min_length=1, description="Parameterized prompt template with {var} placeholders")
    system_prompt: Optional[str] = Field(default=None, description="Optional system-level instruction")
    variables: List[str] = Field(default_factory=list, description="Declared variable names expected in template")
    created_at: TzAwareDatetime = Field(description="Creation timestamp of this specific version")
    workspace_id: Optional[str] = Field(
        default=None,
        description="Optional tenant workspace scope. None indicates global platform prompt.",
    )
    metadata: PromptMetadata = Field(default_factory=PromptMetadata, description="Audit & governance metadata")

    @staticmethod
    def compute_content_hash(template: str, system_prompt: Optional[str] = None) -> str:
        """Computes deterministic SHA-256 content hash of prompt content."""
        sys_part = (system_prompt or "").strip()
        tpl_part = template.strip()
        composite = f"sys:{sys_part}|tpl:{tpl_part}"
        return hashlib.sha256(composite.encode("utf-8")).hexdigest()

    @model_validator(mode="after")
    def validate_hash_coherence(self) -> Self:
        expected_hash = self.compute_content_hash(self.template, self.system_prompt)
        if self.hash != expected_hash:
            raise ValueError(
                f"Prompt hash mismatch. Expected '{expected_hash}', got '{self.hash}'"
            )
        return self


class PromptRenderRequest(AIContractModel):
    """
    Request contract to resolve and safely render a versioned prompt.
    """
    prompt_id: str = Field(min_length=1, description="Identifier of the prompt to render")
    version: Optional[int] = Field(default=None, ge=1, description="Target version. If None, resolves active PRODUCTION version.")
    variables: Dict[str, JsonValue] = Field(default_factory=dict, description="Typed variable substitutions")
    workspace_id: Optional[str] = Field(default=None, description="Tenant boundary isolation key")


class PromptRenderResult(AIContractModel):
    """
    Result of resolving and rendering a versioned prompt.
    Provides full auditability (version, hash) to attach to AIRun / AIStep / Cache.
    """
    prompt_id: str = Field(min_length=1, description="Prompt identifier")
    version: int = Field(ge=1, description="Resolved version")
    hash: str = Field(min_length=8, description="Content hash of the rendered prompt version")
    rendered_text: str = Field(min_length=1, description="Final rendered prompt text")
    system_prompt: Optional[str] = Field(default=None, description="Rendered system prompt if applicable")
    status: PromptStatusEnum = Field(description="Status of the resolved prompt version")


class PromptError(Exception):
    """Base exception for prompt management failures."""
    pass


class PromptNotFoundError(PromptError):
    """Raised when prompt_id does not exist."""
    pass


class PromptVersionNotFoundError(PromptError):
    """Raised when a specific version of a prompt does not exist."""
    pass


class PromptVersionImmutableError(PromptError):
    """Raised when an attempt is made to overwrite an existing immutable prompt version."""
    pass


class InvalidPromptLifecycleTransitionError(PromptError):
    """Raised when an illegal lifecycle transition is attempted (e.g., DRAFT -> PRODUCTION)."""
    pass


class UnauthorizedPromptMutationError(PromptError):
    """Raised when an unauthorized entity (e.g. AI model) attempts to mutate or promote a prompt."""
    pass


class MissingPromptVariableError(PromptError):
    """Raised when required prompt variables are missing during rendering."""
    pass


class PromptEvalGateRejectedError(PromptError):
    """Raised when promotion to PRODUCTION is rejected by the evaluation gate."""
    pass
