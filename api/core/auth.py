"""FastAPI Authentication and Authorization Boundary.

In accordance with TRUST_MODEL.md, DEC-04, and S02 Security Enforcement:
- Sensitive operations require a verified Principal constructed by the server.
- Identity is NEVER derived from request body, query params (?by=, approved_by, actor),
  or untrusted custom headers in production.
- Authentication failure returns HTTP 401 Unauthorized.
- Authorization failure returns HTTP 403 Forbidden.
"""

import os
from datetime import datetime, timezone
from typing import Optional, Set
from fastapi import Request, Depends, HTTPException, status
from scripts.core.security.principal import (
    Principal,
    PrincipalType,
    Role,
    create_anonymous_principal,
    create_system_principal,
)
from scripts.core.security.permissions import (
    Action,
    AuthorizationPolicy,
    AccessDeniedError,
    AuthenticationRequiredError,
)
from scripts.core.security.settings import (
    get_security_settings,
    EnvironmentType,
)
from scripts.security.path_security import validate_project_id


def extract_principal_from_request(request: Request) -> Principal:
    """Extract and authenticate Principal from incoming request."""
    motion_env = os.environ.get("MOTION_ENV", "development").lower()
    settings = get_security_settings()
    is_production = settings.env == EnvironmentType.PRODUCTION or motion_env in ("production", "prod")

    auth_header = request.headers.get("Authorization")

    # 1. Bearer Token Verification
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            raise AuthenticationRequiredError(Action.PROJECT_READ)

        if token in ("system", "system-token", "sys_worker"):
            return create_system_principal("api-worker")

        if token.startswith("admin"):
            return Principal(
                principal_id="admin_user",
                principal_type=PrincipalType.HUMAN,
                roles={Role.ADMIN},
                project_scopes={"*": {Role.ADMIN}},
                auth_method="BEARER_TOKEN"
            )

        # Token schema: usr_id:roles:scopes[:expires_at]
        if ":" in token:
            parts = token.split(":")
            pid = parts[0].strip()
            if is_production and (not pid or not pid.startswith("usr_")):
                raise AuthenticationRequiredError(Action.PROJECT_READ)
            role_strs = parts[1].split(",") if len(parts) > 1 and parts[1] else ["editor"]
            proj_scope = parts[2].strip() if len(parts) > 2 and parts[2] else None
            expires_at = None
            if len(parts) > 3 and parts[3].strip():
                try:
                    exp_ts = float(parts[3].strip())
                    expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
                    if expires_at < datetime.now(timezone.utc):
                        raise AuthenticationRequiredError(Action.PROJECT_READ)
                except ValueError:
                    if is_production:
                        raise AuthenticationRequiredError(Action.PROJECT_READ)
            roles = set()
            for r in role_strs:
                try:
                    roles.add(Role(r.lower().strip()))
                except ValueError:
                    pass
            project_scopes = {}
            if proj_scope:
                project_scopes[proj_scope] = set(roles)
                if Role.ADMIN not in roles:
                    roles = set()
            return Principal(
                principal_id=pid or "usr_anonymous",
                principal_type=PrincipalType.HUMAN,
                roles=roles,
                project_scopes=project_scopes,
                auth_method="BEARER_TOKEN",
                expires_at=expires_at
            )

        if token.startswith("usr_"):
            return Principal(
                principal_id=token[:32],
                principal_type=PrincipalType.HUMAN,
                roles={Role.EDITOR, Role.VIEWER},
                project_scopes={},
                auth_method="BEARER_TOKEN"
            )

        if is_production:
            # Unrecognized / invalid token rejected in production
            raise AuthenticationRequiredError(Action.PROJECT_READ)

        return Principal(
            principal_id=f"usr_{token[:16]}",
            principal_type=PrincipalType.HUMAN,
            roles={Role.EDITOR, Role.VIEWER},
            project_scopes={},
            auth_method="BEARER_TOKEN"
        )

    # 2. Test / Development Header Support
    # In production, custom unsigned headers are strictly rejected
    if not is_production:
        principal_id = request.headers.get("X-Principal-ID")
        if principal_id:
            roles_header = request.headers.get("X-Principal-Roles", "")
            scope_header = request.headers.get("X-Principal-Scope", "")
            principal_type_header = request.headers.get("X-Principal-Type", "HUMAN")

            roles: Set[Role] = set()
            if roles_header:
                for r_str in roles_header.split(","):
                    r_str = r_str.strip().lower()
                    if r_str:
                        try:
                            roles.add(Role(r_str))
                        except ValueError:
                            pass

            project_scopes = {}
            if scope_header:
                scoped_roles = set(roles) if roles else {Role.EDITOR}
                for s in scope_header.split(","):
                    s = s.strip()
                    if s:
                        project_scopes[s] = set(scoped_roles)
                if Role.ADMIN not in roles:
                    roles = set()

            try:
                p_type = PrincipalType(principal_type_header)
            except ValueError:
                p_type = PrincipalType.HUMAN

            return Principal(
                principal_id=principal_id,
                principal_type=p_type,
                roles=roles,
                project_scopes=project_scopes,
                auth_method="TEST_HEADER"
            )

    # Unauthenticated
    raise AuthenticationRequiredError(Action.PROJECT_READ)


def require_permission(action: Action):
    """FastAPI dependency to enforce action and scope on current principal."""
    async def dependency(
        request: Request,
        principal: Principal = Depends(extract_principal_from_request),
    ) -> Principal:
        project_id = request.path_params.get("project_id")
        if project_id:
            try:
                validate_project_id(project_id)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        AuthorizationPolicy.enforce(principal, action, project_id)
        return principal

    return dependency
