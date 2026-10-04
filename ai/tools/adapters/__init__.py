"""
ai/tools/adapters
=================
Authoritative adapter package for capability execution (S28-M03).
"""

from ai.tools.adapters.acquisition import AssetAcquisitionAdapter
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.adapters.domain_service import DomainServiceAdapter
from ai.tools.adapters.mcp import (
    ImplementationSecurityBlockedError,
    MCPToolAdapter,
)
from ai.tools.adapters.native import NativeToolAdapter
from ai.tools.adapters.registry import (
    AdapterRegistry,
    AdapterRegistryError,
    ImplementationUnavailableError,
    get_adapter_registry,
)
from ai.tools.adapters.remote import (
    RemoteAPIAdapter,
    UpstreamProviderUnavailableError,
)
from ai.tools.adapters.worker import WorkerToolAdapter

__all__ = [
    "CapabilityAdapter",
    "AssetAcquisitionAdapter",
    "DomainServiceAdapter",
    "MCPToolAdapter",
    "NativeToolAdapter",
    "RemoteAPIAdapter",
    "WorkerToolAdapter",
    "AdapterRegistry",
    "AdapterRegistryError",
    "ImplementationUnavailableError",
    "ImplementationSecurityBlockedError",
    "UpstreamProviderUnavailableError",
    "get_adapter_registry",
]
