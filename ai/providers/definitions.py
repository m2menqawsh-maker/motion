"""
ai/providers/definitions.py
===========================
Canonical provider definitions for S27.

Represents supported upstream execution targets:
- OpenAI
- Google Gemini
- Anthropic Claude
- ElevenLabs
- Fal.ai
- Replicate
- Local (on-premise / local models)
- MCP (Model Context Protocol tool execution)
"""

from __future__ import annotations

from typing import List
from ai.contracts.common import ExecutionClass, PrivacyRequirement
from ai.providers.base import ProviderDefinition

CANONICAL_PROVIDERS: List[ProviderDefinition] = [
    ProviderDefinition(
        provider_id="openai",
        display_name="OpenAI",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
        privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
        enabled=True,
        description="Public frontier model provider offering GPT-4o, o1, Whisper, and DALL-E series",
    ),
    ProviderDefinition(
        provider_id="gemini",
        display_name="Google Gemini",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
        privacy_compliance=PrivacyRequirement.PUBLIC_ALLOWED,
        enabled=True,
        description="Google DeepMind multi-modal foundation models with native audio/video context",
    ),
    ProviderDefinition(
        provider_id="anthropic",
        display_name="Anthropic",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
        privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
        enabled=True,
        description="Anthropic Claude reasoning and code generation models",
    ),
    ProviderDefinition(
        provider_id="elevenlabs",
        display_name="ElevenLabs",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
        privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
        enabled=True,
        description="Neural speech synthesis, voice cloning, and audio sound effect synthesis",
    ),
    ProviderDefinition(
        provider_id="fal",
        display_name="Fal.ai",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
        privacy_compliance=PrivacyRequirement.PUBLIC_ALLOWED,
        enabled=True,
        description="Fast media generation cloud for video, diffusion, and avatar generation",
    ),
    ProviderDefinition(
        provider_id="replicate",
        display_name="Replicate",
        supported_execution_modes=[ExecutionClass.BATCH, ExecutionClass.BACKGROUND],
        privacy_compliance=PrivacyRequirement.PUBLIC_ALLOWED,
        enabled=True,
        description="Open-source model hosting platform for specialized vision and video pipelines",
    ),
    ProviderDefinition(
        provider_id="local",
        display_name="Local Compute Engine",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BACKGROUND],
        privacy_compliance=PrivacyRequirement.INTERNAL_ONLY,
        enabled=True,
        description="Local on-premise hardware execution (e.g. FFmpeg, local Whisper, PyTorch)",
    ),
    ProviderDefinition(
        provider_id="mcp",
        display_name="Model Context Protocol Gateway",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
        privacy_compliance=PrivacyRequirement.INTERNAL_ONLY,
        enabled=True,
        description="Mediated tool execution and resource provider gateway via MCP servers",
    ),
    ProviderDefinition(
        provider_id="openrouter",
        display_name="OpenRouter (Development Gateway)",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
        privacy_compliance=PrivacyRequirement.PUBLIC_ALLOWED,
        enabled=True,
        environment="development",
        production_default=False,
        adapter_class="ai.providers.openrouter.OpenRouterProvider",
        description="Development gateway for S28. Production provider selection will happen after S28 benchmarks.",
    ),
]
