"""
ai/providers
============
Provider integration and adapter infrastructure for S27.
"""

from ai.providers.base import AIProvider, ProviderDefinition
from ai.providers.definitions import CANONICAL_PROVIDERS
from ai.providers.registry import (
    DuplicateProviderError,
    ProviderRegistry,
    ProviderRegistryError,
    UnknownProviderError,
    create_empty_provider_registry,
    get_provider_registry,
)
from ai.providers.fake import FakeProvider, FakeScenario
from ai.providers.openrouter import (
    OpenRouterConfigurationError,
    OpenRouterProvider,
    get_openrouter_provider_definition,
)

__all__ = [
    "AIProvider",
    "ProviderDefinition",
    "CANONICAL_PROVIDERS",
    "DuplicateProviderError",
    "ProviderRegistry",
    "ProviderRegistryError",
    "UnknownProviderError",
    "create_empty_provider_registry",
    "get_provider_registry",
    "FakeProvider",
    "FakeScenario",
    "OpenRouterProvider",
    "OpenRouterConfigurationError",
    "get_openrouter_provider_definition",
]
