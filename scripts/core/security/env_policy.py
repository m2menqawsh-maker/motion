"""Environment Variables Policy and Classification Registry.

In accordance with Section 10 of the Trust Model (SEC-DOC-001), this module defines
the canonical classification and audit policy for all environment variables:
- Configuration
- Secret
- Test-only
- Forbidden in production
- Deprecated

Core Invariant:
An environment variable must never grant authorization or convert a Hard Failure to Success.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EnvCategory(str, Enum):
    CONFIGURATION = "CONFIGURATION"
    SECRET = "SECRET"
    TEST_ONLY = "TEST_ONLY"
    FORBIDDEN_IN_PRODUCTION = "FORBIDDEN_IN_PRODUCTION"
    DEPRECATED = "DEPRECATED"


class EnvVarDefinition(BaseModel):
    name: str
    category: EnvCategory
    description: str
    allowed_in_production: bool = True
    default: Optional[str] = None
    sensitive: bool = False


# Canonical inventory of all environment variables recognized by the system
ENV_INVENTORY: Dict[str, EnvVarDefinition] = {
    # Bypass / Dangerous flags
    "SKIP_STRICT_QC": EnvVarDefinition(
        name="SKIP_STRICT_QC",
        category=EnvCategory.FORBIDDEN_IN_PRODUCTION,
        description="Bypasses Final QC failures in scripts/gates/final_qc.py. Strictly forbidden in production.",
        allowed_in_production=False
    ),
    "AGY_IS_MANAGED": EnvVarDefinition(
        name="AGY_IS_MANAGED",
        category=EnvCategory.FORBIDDEN_IN_PRODUCTION,
        description="Bypasses .studio_approved requirement in scripts/render_project.py. Strictly forbidden in production.",
        allowed_in_production=False
    ),

    # Test-only variables
    "TESTING": EnvVarDefinition(
        name="TESTING",
        category=EnvCategory.TEST_ONLY,
        description="Flags running under pytest test suite.",
        allowed_in_production=False
    ),
    "AGY_FAILURE_INJECTION_ENABLED": EnvVarDefinition(
        name="AGY_FAILURE_INJECTION_ENABLED",
        category=EnvCategory.TEST_ONLY,
        description="Enables fault injection engine for chaos testing.",
        allowed_in_production=False
    ),
    "AGY_INJECT_FAILURE": EnvVarDefinition(
        name="AGY_INJECT_FAILURE",
        category=EnvCategory.TEST_ONLY,
        description="Payload specification for injected fault.",
        allowed_in_production=False
    ),

    # Secrets
    "OPENAI_API_KEY": EnvVarDefinition(
        name="OPENAI_API_KEY",
        category=EnvCategory.SECRET,
        description="API key for OpenAI GPT models.",
        sensitive=True
    ),
    "ELEVENLABS_API_KEY": EnvVarDefinition(
        name="ELEVENLABS_API_KEY",
        category=EnvCategory.SECRET,
        description="API key for ElevenLabs voice generation.",
        sensitive=True
    ),
    "HEYGEN_API_KEY": EnvVarDefinition(
        name="HEYGEN_API_KEY",
        category=EnvCategory.SECRET,
        description="API key for HeyGen avatar synthesis.",
        sensitive=True
    ),
    "FAL_KEY": EnvVarDefinition(
        name="FAL_KEY",
        category=EnvCategory.SECRET,
        description="API key for Fal.ai video generation.",
        sensitive=True
    ),
    "FALAI_API_KEY": EnvVarDefinition(
        name="FALAI_API_KEY",
        category=EnvCategory.SECRET,
        description="Alternative key for Fal.ai.",
        sensitive=True
    ),
    "REPLICATE_API_TOKEN": EnvVarDefinition(
        name="REPLICATE_API_TOKEN",
        category=EnvCategory.SECRET,
        description="API token for Replicate models.",
        sensitive=True
    ),
    "PEXELS_API_KEY": EnvVarDefinition(
        name="PEXELS_API_KEY",
        category=EnvCategory.SECRET,
        description="API key for Pexels stock video provider.",
        sensitive=True
    ),
    "PIXABAY_API_KEY": EnvVarDefinition(
        name="PIXABAY_API_KEY",
        category=EnvCategory.SECRET,
        description="API key for Pixabay stock provider.",
        sensitive=True
    ),
    "FREESOUND_API_KEY": EnvVarDefinition(
        name="FREESOUND_API_KEY",
        category=EnvCategory.SECRET,
        description="API key for Freesound audio provider.",
        sensitive=True
    ),
    "OPENROUTER_API_KEY": EnvVarDefinition(
        name="OPENROUTER_API_KEY",
        category=EnvCategory.SECRET,
        description="API key for OpenRouter development AI gateway.",
        sensitive=True,
        allowed_in_production=False
    ),

    # Runtime tracing & Context
    "AGY_RUN_ID": EnvVarDefinition(
        name="AGY_RUN_ID",
        category=EnvCategory.CONFIGURATION,
        description="Unique run correlation identifier for structured logging."
    ),
    "AGY_SPAN_ID": EnvVarDefinition(
        name="AGY_SPAN_ID",
        category=EnvCategory.CONFIGURATION,
        description="Current span identifier for hierarchical logging."
    ),
    "AGY_ATTEMPT": EnvVarDefinition(
        name="AGY_ATTEMPT",
        category=EnvCategory.CONFIGURATION,
        description="Execution retry attempt index."
    ),
    "AGY_PROJECT_ID": EnvVarDefinition(
        name="AGY_PROJECT_ID",
        category=EnvCategory.CONFIGURATION,
        description="Active project identifier propagated to child processes."
    ),

    # Configuration
    "MOTION_ENV": EnvVarDefinition(
        name="MOTION_ENV",
        category=EnvCategory.CONFIGURATION,
        description="Target deployment environment ('production', 'staging', 'development', 'test').",
        default="development"
    ),
    "MOTION_HOST": EnvVarDefinition(
        name="MOTION_HOST",
        category=EnvCategory.CONFIGURATION,
        description="API binding host interface.",
        default="127.0.0.1"
    ),
    "MOTION_PORT": EnvVarDefinition(
        name="MOTION_PORT",
        category=EnvCategory.CONFIGURATION,
        description="API listening port.",
        default="8000"
    ),
    "SVM_DATA_DIR": EnvVarDefinition(
        name="SVM_DATA_DIR",
        category=EnvCategory.CONFIGURATION,
        description="Root storage path for media tools cache."
    ),
    "SVM_PLUGIN_ROOT": EnvVarDefinition(
        name="SVM_PLUGIN_ROOT",
        category=EnvCategory.CONFIGURATION,
        description="Root path for plugin discovery."
    ),
    "WHISPER_DEVICE": EnvVarDefinition(
        name="WHISPER_DEVICE",
        category=EnvCategory.CONFIGURATION,
        description="Execution device for Whisper voice recognition ('cpu', 'cuda').",
        default="cpu"
    ),
    "DISPLAY": EnvVarDefinition(
        name="DISPLAY",
        category=EnvCategory.CONFIGURATION,
        description="X11 display target for virtual framebuffer recording."
    ),
}


class EnvironmentPolicyAuditor:
    """Audits active environment variables against target security posture."""

    @classmethod
    def audit_environment(
        cls,
        env: Dict[str, str],
        target_env: str = "production"
    ) -> List[str]:
        """Audit environment dictionary and return list of security violations."""
        violations: List[str] = []
        is_production = target_env.lower() in ("production", "prod")

        for key, value in env.items():
            defn = ENV_INVENTORY.get(key)
            if defn is None:
                continue

            if is_production and not defn.allowed_in_production:
                # Check if it has an enabling/active value
                if value and value.strip() not in ("0", "false", "no", "off"):
                    violations.append(
                        f"Variable '{key}' is categorized as {defn.category.value} and is FORBIDDEN in production. "
                        f"Found value: '{value}'"
                    )

        return violations
