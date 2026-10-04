"""
ai/tools/types.py
=================
Authoritative domain types, enums, and trusted execution context for AI Tools (S27.9).

Invariants:
- Strict validation policy: unexpected fields forbidden (extra="forbid").
- Strict type checking: coercion of mismatched primitives disabled (strict=True).
- Immutability: models are frozen value objects (frozen=True).
- Structured JSON: no unrestricted dict[str, Any]; typed via JsonValue.
- Provider-neutral: vendor-specific logic or data structures are strictly forbidden.
- Authoritative identity: caller identity originates strictly server-side, never from model.
"""

from __future__ import annotations

from enum import Enum
import threading
import time
from typing import Any, List, Optional
from pydantic import Field, PrivateAttr, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel, strict_enum
from ai.contracts.errors import AIErrorCode, AIErrorCodeEnum


class SideEffectClass(str, Enum):
    """Classification of tool side effects for security and idempotency analysis."""
    READ_ONLY = "READ_ONLY"
    PROJECT_MUTATION = "PROJECT_MUTATION"
    RUN_CONTROL = "RUN_CONTROL"
    EXTERNAL_GENERATION = "EXTERNAL_GENERATION"
    ADMIN = "ADMIN"


class IdempotencyPolicy(str, Enum):
    """Idempotency guarantees for tool execution."""
    IDEMPOTENT_READ = "IDEMPOTENT_READ"
    IDEMPOTENT_BY_KEY = "IDEMPOTENT_BY_KEY"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"
    DOMAIN_MANAGED = "DOMAIN_MANAGED"


class ToolAuditPolicy(str, Enum):
    """Audit policy classification for tracking tool invocation."""
    NONE = "NONE"
    SUMMARY = "SUMMARY"
    VERBOSE = "VERBOSE"


class AuthorizationDecision(str, Enum):
    """Deterministic server-side authorization decisions for tool invocation."""
    ALLOW = "ALLOW"
    DENY_UNAUTHENTICATED = "DENY_UNAUTHENTICATED"
    DENY_TENANT = "DENY_TENANT"
    DENY_PERMISSION = "DENY_PERMISSION"
    DENY_RESOURCE = "DENY_RESOURCE"
    DENY_TOOL_DISABLED = "DENY_TOOL_DISABLED"
    DENY_POLICY = "DENY_POLICY"


# Strict annotated enums for Pydantic models
SideEffectClassEnum = strict_enum(SideEffectClass)
IdempotencyPolicyEnum = strict_enum(IdempotencyPolicy)
ToolAuditPolicyEnum = strict_enum(ToolAuditPolicy)
AuthorizationDecisionEnum = strict_enum(AuthorizationDecision)


class TrustedToolExecutionContext(AIContractModel):
    """
    Authoritative server-verified operational context for tool execution.
    
    Originates strictly from authenticated sessions/requests.
    Untrusted model outputs and ToolCall parameters CANNOT forge or override
    any fields in this context (ADR-004 DEC-06.6).
    """
    workspace_id: str = Field(min_length=1, description="Authoritative workspace/tenant boundary")
    actor_id: str = Field(min_length=1, description="Authenticated actor (user or service) identifier")
    roles: List[str] = Field(default_factory=list, description="Authoritative roles assigned to actor")
    permissions: List[str] = Field(default_factory=list, description="Authoritative permission actions granted")
    is_admin: bool = Field(default=False, description="Whether actor holds system-wide administrative authority")
    accessible_projects: Optional[List[str]] = Field(
        default=None,
        description="Explicit project IDs accessible to the actor, or None for all in workspace"
    )
    correlation_id: Optional[str] = Field(default=None, description="Request/trace correlation identifier")
    deadline_monotonic: Optional[float] = Field(
        default=None,
        description="Monotonic timestamp after which execution must abort"
    )
    _cancel_event: threading.Event = PrivateAttr(default_factory=threading.Event)

    def with_timeout(self, timeout_seconds: float) -> TrustedToolExecutionContext:
        """Returns a scoped copy of this context bounded by a monotonic deadline and dedicated cancel event."""
        new_ctx = self.model_copy(update={"deadline_monotonic": time.monotonic() + timeout_seconds})
        object.__setattr__(new_ctx, "_cancel_event", threading.Event())
        return new_ctx

    def cancel(self) -> None:
        """Signals cancellation to all cooperative domain adapters executing under this context."""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """Checks if cancellation has been signalled."""
        return self._cancel_event.is_set()

    def is_timed_out(self) -> bool:
        """Checks if execution deadline has expired or cancellation was requested."""
        if self._cancel_event.is_set():
            return True
        if self.deadline_monotonic is not None:
            return time.monotonic() > self.deadline_monotonic
        return False

    def assert_not_timed_out(self) -> None:
        """
        Cooperative cancellation checkpoint.
        Must be checked by mutating adapters BEFORE performing state mutations or committing side-effects.
        """
        if self.is_timed_out():
            from ai.tools.errors import ToolTimeoutError
            raise ToolTimeoutError("operation", 0.0)

    def can_access_project(self, project_id: Optional[str]) -> bool:
        """Verifies if the tenant context is authorized to access the given project."""
        if project_id is None:
            return True
        if self.is_admin:
            return True
        if self.accessible_projects is None:
            return True
        return project_id in self.accessible_projects

    def has_permission(self, action: str, project_id: Optional[str] = None) -> bool:
        """Evaluates whether the caller possesses the required permission action."""
        if self.is_admin:
            return True
        if "admin" in self.roles:
            return True
        if action in self.permissions:
            return True

        # Check canonical role permissions if imported from domain security
        try:
            from scripts.core.security.permissions import ROLE_PERMISSIONS_MATRIX, Action
            from scripts.core.security.principal import Role
            for r_str in self.roles:
                try:
                    r_enum = Role(r_str.lower().strip())
                    actions = ROLE_PERMISSIONS_MATRIX.get(r_enum, set())
                    if any(a.value == action or a == action for a in actions):
                        return True
                except ValueError:
                    pass
        except Exception:
            pass

        return False

    @classmethod
    def from_principal(
        cls,
        principal: Any,
        workspace_id: str,
        correlation_id: Optional[str] = None,
    ) -> TrustedToolExecutionContext:
        """Constructs trusted context from a server-verified Principal."""
        roles = [r.value if hasattr(r, "value") else str(r) for r in getattr(principal, "roles", set())]
        is_admin = getattr(principal, "is_admin", False) or "admin" in roles
        actor_id = getattr(principal, "principal_id", "anonymous")
        
        # Scopes
        scopes = getattr(principal, "project_scopes", {})
        accessible_projects = None
        if scopes and "*" not in scopes:
            accessible_projects = list(scopes.keys())

        # Derive permissions from roles
        permissions: List[str] = []
        try:
            from scripts.core.security.permissions import ROLE_PERMISSIONS_MATRIX, Role
            for r_str in roles:
                try:
                    r_enum = Role(r_str.lower().strip())
                    acts = ROLE_PERMISSIONS_MATRIX.get(r_enum, set())
                    for act in acts:
                        val = act.value if hasattr(act, "value") else str(act)
                        if val not in permissions:
                            permissions.append(val)
                except ValueError:
                    pass
        except Exception:
            pass

        return cls(
            workspace_id=workspace_id,
            actor_id=actor_id,
            roles=roles,
            permissions=permissions,
            is_admin=is_admin,
            accessible_projects=accessible_projects,
            correlation_id=correlation_id,
        )

    @classmethod
    def from_tenant_context(
        cls,
        ctx: Any,
        correlation_id: Optional[str] = None,
    ) -> TrustedToolExecutionContext:
        """Constructs trusted context from a server-verified TenantContext."""
        principal = getattr(ctx, "principal", None)
        ws_id = getattr(ctx, "workspace_id", "ws_default")
        if principal:
            return cls.from_principal(principal, workspace_id=ws_id, correlation_id=correlation_id)
        
        user_id = getattr(ctx, "user_id", "anonymous")
        role = getattr(ctx, "role", "viewer")
        role_str = role.value if hasattr(role, "value") else str(role)
        is_admin = getattr(ctx, "is_admin", False) or role_str == "admin"

        # Derive permissions from role
        permissions: List[str] = []
        try:
            from scripts.core.security.permissions import ROLE_PERMISSIONS_MATRIX, Role
            try:
                r_enum = Role(role_str.lower().strip())
                acts = ROLE_PERMISSIONS_MATRIX.get(r_enum, set())
                for act in acts:
                    val = act.value if hasattr(act, "value") else str(act)
                    if val not in permissions:
                        permissions.append(val)
            except ValueError:
                pass
        except Exception:
            pass

        return cls(
            workspace_id=ws_id,
            actor_id=user_id,
            roles=[role_str],
            permissions=permissions,
            is_admin=is_admin,
            accessible_projects=None,
            correlation_id=correlation_id,
        )

    @classmethod
    def from_trusted_tenant_context(
        cls,
        ctx: Any,
        correlation_id: Optional[str] = None,
    ) -> TrustedToolExecutionContext:
        """Constructs trusted context from Memory subsystem's TrustedTenantContext."""
        return cls(
            workspace_id=ctx.workspace_id,
            actor_id=ctx.user_id or "anonymous",
            roles=list(ctx.roles),
            permissions=[],
            is_admin=ctx.is_admin,
            accessible_projects=list(ctx.accessible_projects) if ctx.accessible_projects is not None else None,
            correlation_id=correlation_id,
        )


class ToolAuthorizationResult(AIContractModel):
    """Structured authorization assessment result produced before tool execution."""
    decision: AuthorizationDecisionEnum = Field(description="Canonical decision code")
    allowed: bool = Field(description="Whether tool execution is permitted")
    reason: Optional[str] = Field(default=None, description="Human/audit reason for decision")
    error_code: Optional[AIErrorCodeEnum] = Field(
        default=None,
        description="Mapped AIErrorCode if decision is a denial"
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if self.allowed and self.decision != AuthorizationDecision.ALLOW:
            raise ValueError(f"Inconsistent result: allowed=True but decision={self.decision}")
        if not self.allowed and self.decision == AuthorizationDecision.ALLOW:
            raise ValueError("Inconsistent result: allowed=False but decision=ALLOW")
        if not self.allowed and self.error_code is None:
            raise ValueError("Denied authorization result must provide an error_code")
        return self
