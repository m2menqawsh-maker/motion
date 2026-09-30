"""FastAPI Authentication and Authorization Boundary.

In accordance with TRUST_MODEL.md, DEC-04, and S02 Security Enforcement:
- Sensitive operations require an authentic, server-verified Principal.
- Bearer tokens are cryptographically verified using HMAC-SHA256 signatures (Option B).
- "Client-provided claims are not trusted claims." Signatures are verified BEFORE trusting any claim.
- Identity is NEVER derived from request body, query params (?by=, approved_by, actor),
  or untrusted custom headers in production.
- Authentication failure returns HTTP 401 Unauthorized.
- Authorization failure returns HTTP 403 Forbidden.
"""

import os
import base64
import hmac
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Set, Dict, Any
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


def get_auth_secret(is_production: bool = False) -> str:
    """Retrieve canonical secret key for HMAC token signing."""
    settings = get_security_settings()
    secret = (
        settings.auth_secret_key
        or os.environ.get("AUTH_SECRET_KEY")
        or settings.jwt_secret_key
        or os.environ.get("JWT_SECRET_KEY")
    )
    if is_production:
        if not secret or len(secret) < 32:
            raise AuthenticationRequiredError(Action.PROJECT_READ)
        return secret
    return secret or "dev-insecure-secret-key-minimum-32-chars-long!"


def create_signed_token(
    principal: Principal,
    secret: Optional[str] = None,
    expires_in_seconds: Optional[int] = 3600,
) -> str:
    """Generate an authentic HMAC-SHA256 signed bearer token."""
    if secret is None:
        secret = get_auth_secret(is_production=False)

    now = datetime.now(timezone.utc)
    roles_payload = [r.value if isinstance(r, Role) else str(r) for r in principal.roles]
    scopes_payload = {
        p_id: [r.value if isinstance(r, Role) else str(r) for r in roles_set]
        for p_id, roles_set in principal.project_scopes.items()
    }

    payload: Dict[str, Any] = {
        "sub": principal.principal_id,
        "type": principal.principal_type.value if hasattr(principal.principal_type, "value") else str(principal.principal_type),
        "roles": roles_payload,
        "scopes": scopes_payload,
        "iat": int(now.timestamp()),
        "iss": "clean-video-engine",
    }

    if expires_in_seconds is not None:
        exp = now + timedelta(seconds=expires_in_seconds)
        payload["exp"] = int(exp.timestamp())
    elif principal.expires_at is not None:
        payload["exp"] = int(principal.expires_at.timestamp())

    payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")

    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")

    return f"{payload_b64}.{sig_b64}"


def verify_signed_token(
    token: str,
    secret: Optional[str] = None,
    is_production: bool = False,
) -> Principal:
    """Verify an authentic HMAC-SHA256 signed bearer token and return the verified Principal.
    
    In accordance with TRUST_MODEL:
    1. Signature is cryptographically verified before any claim is parsed or trusted.
    2. Expiration, sub format, roles, and project scopes are validated.
    """
    if not token or not isinstance(token, str) or token.count(".") != 1:
        raise AuthenticationRequiredError(Action.PROJECT_READ)

    payload_b64, sig_b64 = token.split(".", 1)
    if not payload_b64 or not sig_b64:
        raise AuthenticationRequiredError(Action.PROJECT_READ)

    if secret is None:
        secret = get_auth_secret(is_production=is_production)

    # 1. Cryptographic HMAC-SHA256 Verification (executed BEFORE reading or trusting any claims)
    try:
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
    except Exception:
        raise AuthenticationRequiredError(Action.PROJECT_READ)

    if not hmac.compare_digest(sig_b64, expected_sig):
        # Tampered or invalid signature -> reject immediately
        raise AuthenticationRequiredError(Action.PROJECT_READ)

    # 2. Decode and parse claims payload
    try:
        pad_len = len(payload_b64) % 4
        padded = payload_b64 + ("=" * (4 - pad_len) if pad_len else "")
        raw_json = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        claims = json.loads(raw_json)
        if not isinstance(claims, dict):
            raise AuthenticationRequiredError(Action.PROJECT_READ)
    except Exception:
        raise AuthenticationRequiredError(Action.PROJECT_READ)

    # 3. Expiration validation
    exp_dt = None
    if "exp" in claims:
        try:
            exp_ts = float(claims["exp"])
            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            if datetime.now(timezone.utc) > exp_dt:
                raise AuthenticationRequiredError(Action.PROJECT_READ)
        except Exception:
            raise AuthenticationRequiredError(Action.PROJECT_READ)

    # 4. Identity validation (sub)
    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise AuthenticationRequiredError(Action.PROJECT_READ)
    sub = sub.strip()
    if is_production and not (sub.startswith("usr_") or sub.startswith("sys_")):
        raise AuthenticationRequiredError(Action.PROJECT_READ)

    # 5. Roles validation
    roles_raw = claims.get("roles", [])
    if not isinstance(roles_raw, list):
        raise AuthenticationRequiredError(Action.PROJECT_READ)
    roles: Set[Role] = set()
    for r in roles_raw:
        if not isinstance(r, str):
            raise AuthenticationRequiredError(Action.PROJECT_READ)
        try:
            roles.add(Role(r.lower().strip()))
        except ValueError:
            raise AuthenticationRequiredError(Action.PROJECT_READ)

    # 6. Scopes validation
    scopes_raw = claims.get("scopes", {})
    if not isinstance(scopes_raw, dict):
        raise AuthenticationRequiredError(Action.PROJECT_READ)
    project_scopes: Dict[str, Set[Role]] = {}
    for p_id, p_roles in scopes_raw.items():
        if not isinstance(p_id, str) or not isinstance(p_roles, list):
            raise AuthenticationRequiredError(Action.PROJECT_READ)
        try:
            validate_project_id(p_id)
        except ValueError:
            if p_id != "*":
                raise AuthenticationRequiredError(Action.PROJECT_READ)
        parsed_scope_roles = set()
        for pr in p_roles:
            if not isinstance(pr, str):
                raise AuthenticationRequiredError(Action.PROJECT_READ)
            try:
                parsed_scope_roles.add(Role(pr.lower().strip()))
            except ValueError:
                raise AuthenticationRequiredError(Action.PROJECT_READ)
        project_scopes[p_id] = parsed_scope_roles

    # 7. Principal Type validation
    p_type_raw = claims.get("type", "HUMAN")
    try:
        p_type = PrincipalType(p_type_raw)
    except ValueError:
        p_type = PrincipalType.HUMAN

    return Principal(
        principal_id=sub,
        principal_type=p_type,
        roles=roles,
        project_scopes=project_scopes,
        auth_method="SIGNED_BEARER_TOKEN",
        expires_at=exp_dt,
    )


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

        # In production: ALL Bearer tokens MUST be cryptographically verified signed tokens.
        # Absolutely NO client-asserted claim strings or hardcoded token values are accepted.
        if is_production:
            return verify_signed_token(token, is_production=True)

        # Non-production (dev/test):
        # First attempt signed token verification if token contains '.'
        if "." in token:
            return verify_signed_token(token, is_production=False)

        # Development/Test convenience fallbacks (non-production only)
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

        if token.startswith("usr_"):
            return Principal(
                principal_id=token[:32],
                principal_type=PrincipalType.HUMAN,
                roles={Role.EDITOR, Role.VIEWER},
                project_scopes={},
                auth_method="BEARER_TOKEN"
            )

        raise AuthenticationRequiredError(Action.PROJECT_READ)

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

            project_scopes: Dict[str, Set[Role]] = {}
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

        # Attach TenantContext if project_id is present (S24.5)
        if project_id:
            try:
                from scripts.core.database import get_database_engine, TenantRepository
                from scripts.core.tenant_model import TenantContext
                engine = get_database_engine()
                repo = TenantRepository(engine)
                project_record = repo.get_project(project_id)
                if project_record:
                    membership = repo.get_membership(project_record.workspace_id, principal.principal_id)
                    effective_role = Role.ADMIN if principal.is_admin else (membership.role if membership else Role.VIEWER)
                    request.state.tenant_context = TenantContext(
                        workspace_id=project_record.workspace_id,
                        user_id=principal.principal_id,
                        role=effective_role,
                        principal=principal,
                    )
            except Exception:
                pass

        return principal

    return dependency


def require_tenant_context(action: Action):
    """FastAPI dependency returning the server-verified TenantContext (S24.5)."""
    async def dependency(
        request: Request,
        principal: Principal = Depends(require_permission(action)),
    ) -> Any:
        ctx = getattr(request.state, "tenant_context", None)
        if ctx is not None:
            return ctx

        # Derive tenant context when no project_id is in the path
        workspace_id = request.headers.get("X-Workspace-ID")
        from scripts.core.database import get_database_engine, TenantRepository
        from scripts.core.tenant_model import TenantContext
        engine = get_database_engine()
        repo = TenantRepository(engine)

        if not workspace_id:
            workspaces = repo.list_user_workspaces(principal.principal_id)
            if workspaces:
                workspace_id = workspaces[0][0].id

        if not workspace_id:
            workspace_id = f"ws_{principal.principal_id}"
            try:
                repo.create_workspace(workspace_id, "Personal Workspace", created_by=principal.principal_id)
            except Exception:
                pass

        membership = repo.get_membership(workspace_id, principal.principal_id)
        if membership is None and principal.principal_type not in (PrincipalType.SERVICE, PrincipalType.SYSTEM_WORKER):
            raise AccessDeniedError(
                principal_id=principal.principal_id,
                action=action,
                project_id=None,
                reason=f"Principal '{principal.principal_id}' is not a member of workspace '{workspace_id}'"
            )

        effective_role = membership.role if membership else (Role.ADMIN if principal.is_admin else Role.VIEWER)

        ctx = TenantContext(
            workspace_id=workspace_id,
            user_id=principal.principal_id,
            role=effective_role,
            principal=principal,
        )
        request.state.tenant_context = ctx
        return ctx

    return dependency
