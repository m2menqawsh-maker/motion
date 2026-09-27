"""Principal and Identity Data Contracts.

In accordance with DEC-04, this module defines the server-verified Principal abstraction
which acts as the single source of truth for the authenticated caller identity.
Domain logic must consume this Principal and never read identity directly from
untrusted request bodies, query parameters, or raw headers.
"""

from enum import Enum
from typing import Dict, Set, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class PrincipalType(str, Enum):
    """Classification of the security principal."""
    HUMAN = "HUMAN"
    SERVICE = "SERVICE"
    SYSTEM_WORKER = "SYSTEM_WORKER"
    ANONYMOUS = "ANONYMOUS"


class Role(str, Enum):
    """Canonical role definitions."""
    VIEWER = "viewer"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class Principal(BaseModel):
    """Server-verified identity context."""
    model_config = ConfigDict(extra='forbid', frozen=True)

    principal_id: str = Field(description="Unique persistent identifier for the principal")
    principal_type: PrincipalType = Field(description="Classification of principal (HUMAN, SERVICE, etc.)")
    roles: Set[Role] = Field(default_factory=set, description="Global roles assigned to the principal")
    project_scopes: Dict[str, Set[Role]] = Field(
        default_factory=dict,
        description="Project-specific role mappings: {project_id: {roles...}}"
    )
    auth_method: str = Field(default="INTERNAL", description="Method used to authenticate the principal")
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the identity was authenticated/issued"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the principal session expires"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional verified claims (email, display name, client IP, etc.)"
    )

    @property
    def is_authenticated(self) -> bool:
        """Return True if the principal is not anonymous and not expired."""
        if self.principal_type == PrincipalType.ANONYMOUS:
            return False
        if self.expires_at is not None:
            now = datetime.now(timezone.utc)
            if now > self.expires_at:
                return False
        return True

    @property
    def is_human(self) -> bool:
        return self.principal_type == PrincipalType.HUMAN

    @property
    def is_service(self) -> bool:
        return self.principal_type in (PrincipalType.SERVICE, PrincipalType.SYSTEM_WORKER)

    @property
    def is_admin(self) -> bool:
        return Role.ADMIN in self.roles

    def get_roles_for_project(self, project_id: Optional[str]) -> Set[Role]:
        """Compute the effective set of roles for a given project.
        
        Global roles apply across all projects. Project-specific roles are added.
        If the principal is a global admin, all roles are implicitly granted.
        """
        if self.is_admin:
            return set(Role)

        effective_roles = set(self.roles)
        if project_id and project_id in self.project_scopes:
            effective_roles.update(self.project_scopes[project_id])
            
        # Support wildcard project scope
        if "*" in self.project_scopes:
            effective_roles.update(self.project_scopes["*"])

        return effective_roles

    def has_role(self, role: Role, project_id: Optional[str] = None) -> bool:
        """Check whether the principal possesses a specific role in scope."""
        if not self.is_authenticated:
            return False
        return role in self.get_roles_for_project(project_id)


def create_anonymous_principal() -> Principal:
    """Helper to generate an unauthenticated anonymous principal."""
    return Principal(
        principal_id="anonymous",
        principal_type=PrincipalType.ANONYMOUS,
        roles=set(),
        project_scopes={},
        auth_method="NONE"
    )


def create_system_principal(name: str = "system-worker") -> Principal:
    """Helper to generate an internal system principal for background workers."""
    return Principal(
        principal_id=f"sys_{name}",
        principal_type=PrincipalType.SYSTEM_WORKER,
        roles={Role.ADMIN, Role.OPERATOR},
        project_scopes={"*": {Role.ADMIN, Role.OPERATOR}},
        auth_method="INTERNAL_SYSTEM"
    )
