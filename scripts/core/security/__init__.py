"""Security Core Subsystem Scaffolding Package.

Provides canonical contracts for:
- Principal & Identity (DEC-04)
- Authorization & Permission Matrix
- Command Execution Policy & Subprocess Confinement
- Environment Variables Policy & Classification
- Typed Security Settings Schema
"""

from scripts.core.security.principal import (
    Principal,
    PrincipalType,
    Role,
    create_anonymous_principal,
    create_system_principal,
)
from scripts.core.security.permissions import (
    Action,
    ROLE_PERMISSIONS_MATRIX,
    AuthorizationPolicy,
    AccessDeniedError,
    AuthenticationRequiredError,
)
from scripts.core.security.command_policy import (
    CommandPolicy,
    CommandValidationResult,
    CommandSecurityViolation,
    ALLOWED_PYTHON_SCRIPTS,
    ALLOWED_PYTHON_MODULES,
)
from scripts.core.security.env_policy import (
    EnvCategory,
    EnvVarDefinition,
    ENV_INVENTORY,
    EnvironmentPolicyAuditor,
)
from scripts.core.security.settings import (
    EnvironmentType,
    SecuritySettings,
    get_security_settings,
    set_security_settings,
)

__all__ = [
    "Principal",
    "PrincipalType",
    "Role",
    "create_anonymous_principal",
    "create_system_principal",
    "Action",
    "ROLE_PERMISSIONS_MATRIX",
    "AuthorizationPolicy",
    "AccessDeniedError",
    "AuthenticationRequiredError",
    "CommandPolicy",
    "CommandValidationResult",
    "CommandSecurityViolation",
    "ALLOWED_PYTHON_SCRIPTS",
    "ALLOWED_PYTHON_MODULES",
    "EnvCategory",
    "EnvVarDefinition",
    "ENV_INVENTORY",
    "EnvironmentPolicyAuditor",
    "EnvironmentType",
    "SecuritySettings",
    "get_security_settings",
    "set_security_settings",
]
