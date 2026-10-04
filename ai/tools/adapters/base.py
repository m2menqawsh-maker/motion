"""
ai/tools/adapters/base.py
=========================
Authoritative abstract base class and interfaces for capability adapters (S28-M03).

Invariants:
- Adapters DO NOT make authorization decisions (delegated to ToolGateway).
- Adapters DO NOT determine tenant boundary or ownership (enforced by ToolGateway).
- Adapters receive validated, strongly-typed domain contracts.
- Adapters produce raw dictionaries conforming to target canonical output contracts.
- Adapters support cooperative cancellation and timeout handling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ai.contracts import (
    AIContractModel,
    CapabilityDefinition,
    CapabilityRequest,
    ImplementationDescriptor,
)
from ai.tools.types import TrustedToolExecutionContext


class CapabilityAdapter(ABC):
    """
    Abstract interface for capability execution adapters.
    Connects canonical capability requests to concrete execution mechanisms
    (Legacy MCP, Canonical Domain Services, Native Python, Worker Queues, or Remote APIs).
    """

    def __init__(self, name: str, adapter_kind: str) -> None:
        self.name = name
        self.adapter_kind = adapter_kind

    @abstractmethod
    def can_handle(
        self,
        capability: CapabilityDefinition,
        implementation: Optional[ImplementationDescriptor] = None,
    ) -> bool:
        """Determines if this adapter can execute the given capability and implementation."""
        pass

    @abstractmethod
    async def execute(
        self,
        request: CapabilityRequest,
        validated_input: AIContractModel,
        context: TrustedToolExecutionContext,
    ) -> Dict[str, Any]:
        """
        Executes the capability using the bound implementation.
        Returns a dictionary that conforms to the capability's output_contract.
        
        Raises:
            Exception: On execution failure, timeout, or upstream provider error.
        """
        pass

    def cancel(self, request_id: str) -> None:
        """Cooperatively cancels an in-flight execution if supported by adapter."""
        pass

    def get_health(self) -> Dict[str, Any]:
        """Returns runtime availability and health diagnostics of this adapter."""
        return {
            "adapter_name": self.name,
            "adapter_kind": self.adapter_kind,
            "status": "HEALTHY",
        }
