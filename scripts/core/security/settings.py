"""Typed Security and System Settings Schema.

In accordance with Section 11 of the Trust Model (SEC-DOC-001), this module defines
canonical typed settings models to replace unstructured environment reading.
Invariants:
In PRODUCTION mode, anonymous access is forbidden and QC/approval bypasses are strictly disallowed.
"""

import sys
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict


class EnvironmentType(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"
    TEST = "test"


class SecuritySettings(BaseModel):
    """Canonical typed security configuration."""
    model_config = ConfigDict(extra='forbid')

    env: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT,
        description="Target deployment environment tier"
    )
    storage_root: Path = Field(
        default_factory=lambda: Path.cwd() / "projects",
        description="Base storage directory for project files"
    )
    workspace_root: Path = Field(
        default_factory=lambda: Path.cwd(),
        description="Root workspace directory"
    )
    python_interpreter: Path = Field(
        default_factory=lambda: Path(sys.executable).resolve(),
        description="Canonical path to the running Python interpreter"
    )

    # Core Security Invariants
    allow_anonymous: bool = Field(
        default=False,
        description="Whether unauthenticated requests are permitted read access"
    )
    enforce_strict_qc: bool = Field(
        default=True,
        description="Whether QC gate failures act as hard pipeline blockers"
    )
    enforce_studio_approval: bool = Field(
        default=True,
        description="Whether .studio_approved is strictly mandatory before rendering"
    )

    # Subprocess execution limits
    max_subprocess_timeout_seconds: int = Field(
        default=900,
        ge=5,
        le=1800,
        description="Maximum execution timeout in seconds for child processes"
    )
    max_output_bytes: int = Field(
        default=50 * 1024 * 1024,
        description="Maximum buffered stdout/stderr in bytes"
    )

    # Cryptographic secrets
    auth_secret_key: Optional[str] = Field(
        default_factory=lambda: __import__("os").environ.get("AUTH_SECRET_KEY"),
        description="Secret key used for HMAC-SHA256 signing of authentication tokens"
    )
    jwt_secret_key: Optional[str] = Field(
        default=None,
        description="Secret key used for signing and verifying JWT tokens"
    )
    session_secret_key: Optional[str] = Field(
        default=None,
        description="Secret key for signing HTTP session cookies"
    )

    @model_validator(mode="after")
    def validate_production_invariants(self) -> 'SecuritySettings':
        """Enforce strict security requirements when operating in production."""
        if self.env == EnvironmentType.PRODUCTION:
            if self.allow_anonymous:
                raise ValueError("Security Violation: allow_anonymous cannot be True in PRODUCTION environment.")

            if not self.enforce_strict_qc:
                raise ValueError("Security Violation: enforce_strict_qc cannot be disabled in PRODUCTION environment.")

            if not self.enforce_studio_approval:
                raise ValueError("Security Violation: enforce_studio_approval cannot be disabled in PRODUCTION environment.")

            if self.auth_secret_key is not None and len(self.auth_secret_key) < 32:
                raise ValueError("Security Violation: auth_secret_key must be at least 32 characters in PRODUCTION environment.")

        # Ensure python interpreter is a valid executable path
        if not self.python_interpreter.is_absolute():
            object.__setattr__(self, 'python_interpreter', self.python_interpreter.resolve())

        return self


_global_settings: Optional[SecuritySettings] = None


def get_security_settings() -> SecuritySettings:
    """Singleton getter for active security settings."""
    global _global_settings
    if _global_settings is None:
        _global_settings = SecuritySettings()
    return _global_settings


def set_security_settings(settings: SecuritySettings) -> None:
    """Explicitly override global security settings (useful for tests)."""
    global _global_settings
    _global_settings = settings
