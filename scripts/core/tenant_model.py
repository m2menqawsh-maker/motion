"""
scripts/core/tenant_model.py — SaaS Identity & Multi-Tenant Domain Models (S24.5 - ADR-003).

Provides:
- User domain model
- Workspace domain model
- WorkspaceMember domain model with canonical roles (viewer, editor, reviewer, admin)
- ProjectRecord domain model with mandatory NOT NULL workspace_id
- TenantContext server-verified operational context
"""

from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Set, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from scripts.core.security.principal import Role, Principal


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class User(BaseModel):
    """SaaS User representation."""
    model_config = ConfigDict(extra='forbid', frozen=True)

    id: str = Field(description="Unique persistent user identifier (e.g. usr_123)")
    email: str = Field(description="Primary user email address")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="Account lifecycle status")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 registration timestamp"
    )


class Workspace(BaseModel):
    """SaaS Tenant Workspace."""
    model_config = ConfigDict(extra='forbid', frozen=True)

    id: str = Field(description="Unique persistent workspace identifier (e.g. ws_123)")
    name: str = Field(description="Human-readable workspace name")
    created_by: str = Field(description="User ID of the workspace creator")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp"
    )


class WorkspaceMember(BaseModel):
    """Membership binding between a User and a Workspace with an authoritative Role."""
    model_config = ConfigDict(extra='forbid', frozen=True)

    workspace_id: str = Field(description="Workspace identifier")
    user_id: str = Field(description="User identifier")
    role: Role = Field(description="Authoritative membership role (viewer, editor, reviewer, admin)")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 membership joined timestamp"
    )


class ProjectRecord(BaseModel):
    """Authoritative relational record of a Project belonging to a Workspace."""
    model_config = ConfigDict(extra='forbid', frozen=True)

    id: str = Field(description="Unique persistent project identifier (e.g. prj_123)")
    workspace_id: str = Field(description="MANDATORY workspace identifier (NOT NULL)")
    created_by: str = Field(description="User ID of creator")
    name: str = Field(description="Project name")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 creation timestamp"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 update timestamp"
    )


class TenantContext(BaseModel):
    """
    Server-verified operational context passed into Domain Services.
    Derived strictly from the server-authenticated Principal and DB workspace membership.
    Never trusted from client request body or query parameters.
    """
    model_config = ConfigDict(extra='forbid', frozen=True)

    workspace_id: str = Field(description="Active workspace ID")
    user_id: str = Field(description="Authenticated user ID")
    role: Role = Field(description="Effective workspace role for this session")
    principal: Principal = Field(description="Underlying cryptographic principal")

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN or self.principal.is_admin

    @property
    def is_editor(self) -> bool:
        return self.role in (Role.EDITOR, Role.ADMIN) or self.principal.is_admin

    @property
    def is_reviewer(self) -> bool:
        return self.role in (Role.REVIEWER, Role.ADMIN) or self.principal.is_admin

    @property
    def is_viewer(self) -> bool:
        return True


class UsageEventType(str, Enum):
    RENDER_SECONDS = "render_seconds"
    STORAGE_BYTES = "storage_bytes"
    AI_TOKENS = "ai_tokens"
    AI_REQUESTS = "ai_requests"


class UsageEvent(BaseModel):
    """Usage accounting record for multi-tenant metering."""
    model_config = ConfigDict(extra='forbid', frozen=True)

    id: str = Field(description="Unique event UUID")
    workspace_id: str = Field(description="Workspace identifier")
    project_id: Optional[str] = Field(default=None, description="Optional project identifier")
    user_id: Optional[str] = Field(default=None, description="Optional actor user ID")
    event_type: UsageEventType = Field(description="Type of resource consumed")
    quantity: float = Field(description="Measured quantity of consumption")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp"
    )
