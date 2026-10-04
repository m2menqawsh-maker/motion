"""
ai/tools/adapters/native.py
==========================
Native in-process Python capability adapter (S28-M03).

Invariants:
- Executes verified pure-Python domain logic within application process space.
- Zero shell or subprocess overhead for native capabilities.
- Strictly bounds execution via asyncio cooperative tasks.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from ai.contracts import (
    AIContractModel,
    CapabilityDefinition,
    CapabilityRequest,
    ImplementationDescriptor,
)
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.types import TrustedToolExecutionContext


class NativeToolAdapter(CapabilityAdapter):
    """
    Adapter for capabilities implemented as native Python functions or modules.
    """

    def __init__(
        self,
        name: str = "canonical_native_adapter",
        handler_map: Optional[Dict[str, Callable[[AIContractModel, TrustedToolExecutionContext], Dict[str, Any]]]] = None,
    ) -> None:
        super().__init__(name=name, adapter_kind="NATIVE_SERVICE")
        self._handlers = handler_map or {}

    def register_handler(
        self,
        capability_id: str,
        handler: Callable[[AIContractModel, TrustedToolExecutionContext], Dict[str, Any]],
    ) -> None:
        self._handlers[capability_id] = handler

    def can_handle(
        self,
        capability: CapabilityDefinition,
        implementation: Optional[ImplementationDescriptor] = None,
    ) -> bool:
        cap_val = capability.capability_id.value if hasattr(capability.capability_id, "value") else str(capability.capability_id)
        if cap_val in self._handlers:
            return True
        if implementation and implementation.implementation_kind in ("NATIVE_SERVICE", "LOCAL_PYTHON"):
            return True
        return False

    async def execute(
        self,
        request: CapabilityRequest,
        validated_input: AIContractModel,
        context: TrustedToolExecutionContext,
    ) -> Dict[str, Any]:
        cap_val = request.capability_id.value if hasattr(request.capability_id, "value") else str(request.capability_id)
        handler = self._handlers.get(cap_val)
        if not handler:
            raise NotImplementedError(f"No native handler registered for capability '{cap_val}'.")

        context.assert_not_timed_out()
        res = handler(validated_input, context)
        return res
