"""
API Configuration and Typed Settings (S22 - LED-072).

Provides typed settings for FastAPI application, including:
- Environment-aware CORS configuration
- Safe parsing of origins from environment variables (MOTION_CORS_ALLOWED_ORIGINS)
- Prevention of insecure wildcard ('*') when credentials are enabled
- Strict separation between development defaults and production requirements
"""

import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


class APISettings(BaseModel):
    """Canonical API Settings model."""
    env: str = Field(default_factory=lambda: os.environ.get("MOTION_ENV", "development").lower())
    cors_allowed_origins: List[str] = Field(default_factory=list)
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: List[str] = Field(default_factory=lambda: ["*"])

    @model_validator(mode="before")
    @classmethod
    def populate_cors_origins(cls, values: dict) -> dict:
        """Populate and parse cors_allowed_origins from env if not explicitly provided."""
        env = values.get("env") or os.environ.get("MOTION_ENV", "development").lower()
        origins = values.get("cors_allowed_origins")

        if not origins:
            env_val = os.environ.get("MOTION_CORS_ALLOWED_ORIGINS") or os.environ.get("CORS_ALLOWED_ORIGINS")
            if env_val:
                env_val = env_val.strip()
                if env_val.startswith("[") and env_val.endswith("]"):
                    try:
                        parsed = json.loads(env_val)
                        if isinstance(parsed, list):
                            origins = [str(item).strip() for item in parsed if str(item).strip()]
                    except Exception:
                        origins = [part.strip() for part in env_val.split(",") if part.strip()]
                else:
                    origins = [part.strip() for part in env_val.split(",") if part.strip()]
            else:
                # Environment-dependent defaults
                if env in ("production", "prod"):
                    # Production must never default to implicit localhost
                    origins = []
                else:
                    origins = list(DEFAULT_DEV_ORIGINS)

        values["cors_allowed_origins"] = origins or []
        values["env"] = env
        return values

    @model_validator(mode="after")
    def validate_cors_safety(self) -> "APISettings":
        """Validate CORS safety invariants."""
        # Wildcard '*' is strictly forbidden when credentials are true
        if self.cors_allow_credentials and "*" in self.cors_allowed_origins:
            if self.env in ("production", "prod"):
                raise ValueError("Insecure CORS: Wildcard '*' origin cannot be combined with credentials in production.")
            # In non-production, sanitize by removing wildcard to prevent browser CORS failure
            self.cors_allowed_origins = [o for o in self.cors_allowed_origins if o != "*"]

        return self


_settings: Optional[APISettings] = None


def get_api_settings() -> APISettings:
    """Singleton getter for active APISettings."""
    global _settings
    if _settings is None:
        _settings = APISettings()
    return _settings


def set_api_settings(settings: Optional[APISettings]) -> None:
    """Override settings (useful for tests)."""
    global _settings
    _settings = settings


from starlette.middleware.cors import CORSMiddleware


class DynamicCORSMiddleware(CORSMiddleware):
    """CORS middleware that dynamically queries APISettings for allowed origins."""

    def is_allowed_origin(self, origin: str) -> bool:
        settings = APISettings()
        if origin in settings.cors_allowed_origins:
            return True
        return False
