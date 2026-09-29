"""Authorization Policy and Canonical Permission Matrix.

In accordance with DEC-04 and the Trust Model, this module defines the explicit
mapping between Roles and Actions, enforcing the Project Isolation Contract:
"Can Principal X perform Action Y on Project Z?"
"""

from enum import Enum
from typing import Set, Dict, Optional
from scripts.core.security.principal import Principal, Role


class Action(str, Enum):
    """Canonical system operations requiring authorization."""
    # Project lifecycle
    PROJECT_READ = "project:read"
    PROJECT_CREATE = "project:create"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"

    # Assets
    ASSET_READ = "asset:read"
    ASSET_UPLOAD = "asset:upload"
    ASSET_DELETE = "asset:delete"

    # Blueprint
    BLUEPRINT_READ = "blueprint:read"
    BLUEPRINT_EDIT = "blueprint:edit"

    # Pipeline execution
    RUN_EXECUTE = "run:execute"
    RUN_CANCEL = "run:cancel"

    # Quality Control
    QC_VIEW = "qc:view"
    QC_EXECUTE = "qc:execute"

    # Formal Review Decisions (Gate approval/rejection)
    REVIEW_APPROVE = "review:approve"
    REVIEW_REJECT = "review:reject"

    # Rendering
    RENDER_TRIGGER = "render:trigger"
    RENDER_READ = "render:read"

    # System administration
    SYSTEM_ADMIN = "system:admin"


class AccessDeniedError(Exception):
    """Raised when a principal is denied access to an action or project."""
    def __init__(self, principal_id: str, action: Action, project_id: Optional[str] = None, reason: str = ""):
        self.principal_id = principal_id
        self.action = action
        self.project_id = project_id
        self.reason = reason
        proj_str = f" on project '{project_id}'" if project_id else ""
        msg = f"Principal '{principal_id}' denied permission '{action.value}'{proj_str}."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg)


class AuthenticationRequiredError(Exception):
    """Raised when an unauthenticated caller attempts a protected operation."""
    def __init__(self, action: Action, project_id: Optional[str] = None):
        proj_str = f" on project '{project_id}'" if project_id else ""
        super().__init__(f"Authentication required to perform '{action.value}'{proj_str}.")


# Canonical Permission Matrix
ROLE_PERMISSIONS_MATRIX: Dict[Role, Set[Action]] = {
    Role.VIEWER: {
        Action.PROJECT_READ,
        Action.ASSET_READ,
        Action.BLUEPRINT_READ,
        Action.QC_VIEW,
        Action.RENDER_READ,
    },
    Role.EDITOR: {
        Action.PROJECT_READ,
        Action.PROJECT_CREATE,
        Action.PROJECT_EDIT,
        Action.ASSET_READ,
        Action.ASSET_UPLOAD,
        Action.ASSET_DELETE,
        Action.BLUEPRINT_READ,
        Action.BLUEPRINT_EDIT,
        Action.QC_VIEW,
        Action.RENDER_READ,
    },
    Role.REVIEWER: {
        Action.PROJECT_READ,
        Action.ASSET_READ,
        Action.BLUEPRINT_READ,
        Action.QC_VIEW,
        Action.RENDER_READ,
        # Independent reviewer privileges
        Action.REVIEW_APPROVE,
        Action.REVIEW_REJECT,
    },
    Role.OPERATOR: {
        Action.PROJECT_READ,
        Action.ASSET_READ,
        Action.BLUEPRINT_READ,
        Action.RUN_EXECUTE,
        Action.RUN_CANCEL,
        Action.QC_VIEW,
        Action.QC_EXECUTE,
        Action.RENDER_TRIGGER,
        Action.RENDER_READ,
    },
    Role.ADMIN: set(Action),  # Full permissions
}


class AuthorizationPolicy:
    """Canonical evaluator for access control decisions."""

    @classmethod
    def is_authorized(
        cls,
        principal: Principal,
        action: Action,
        project_id: Optional[str] = None
    ) -> bool:
        """Evaluate if the principal is authorized to perform action on project_id."""
        if not principal.is_authenticated:
            return False

        # Global admin always authorized
        if principal.is_admin:
            return True

        # System administrative actions require global ADMIN
        if action == Action.SYSTEM_ADMIN:
            return principal.is_admin

        # Check database multi-tenant ownership if project_id is provided (S24.5)
        if project_id:
            try:
                from scripts.core.database import get_database_engine, TenantRepository
                engine = get_database_engine()
                repo = TenantRepository(engine)
                project_record = repo.get_project(project_id)
                if project_record is not None:
                    # Multi-tenant project registered in DB
                    membership = repo.get_membership(project_record.workspace_id, principal.principal_id)
                    if membership is None:
                        # User is NOT a member of the workspace owning this project -> Hard Reject
                        return False
                    granted_actions = ROLE_PERMISSIONS_MATRIX.get(membership.role, set())
                    return action in granted_actions
            except Exception:
                pass

        # Compute effective roles for the targeted project
        effective_roles = principal.get_roles_for_project(project_id)
        if not effective_roles:
            return False

        # Check if any effective role grants the requested action
        for role in effective_roles:
            granted_actions = ROLE_PERMISSIONS_MATRIX.get(role, set())
            if action in granted_actions:
                return True

        return False

    @classmethod
    def enforce(
        cls,
        principal: Principal,
        action: Action,
        project_id: Optional[str] = None
    ) -> None:
        """Enforce authorization, raising an appropriate exception if denied."""
        if not principal.is_authenticated:
            raise AuthenticationRequiredError(action=action, project_id=project_id)

        if not cls.is_authorized(principal, action, project_id):
            effective_roles = [r.value for r in principal.get_roles_for_project(project_id)]
            reason = f"Effective roles {effective_roles} do not grant '{action.value}'"
            raise AccessDeniedError(
                principal_id=principal.principal_id,
                action=action,
                project_id=project_id,
                reason=reason
            )
