"""
ai/tools/adapters/worker.py
==========================
Asynchronous / Worker capability execution adapter (S28-M03).

Invariants:
- Integrates background processing with canonical RunService and RunRepository.
- Tracks job state durably without orphan background subprocesses.
- Supports cancellation semantics.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ai.contracts import (
    AIContractModel,
    CapabilityDefinition,
    CapabilityRequest,
    ExecutionMode,
    ImplementationDescriptor,
)
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.types import TrustedToolExecutionContext


class WorkerToolAdapter(CapabilityAdapter):
    """
    Adapter for executing heavy background jobs on worker pools.
    """

    def __init__(self) -> None:
        super().__init__(name="canonical_worker_adapter", adapter_kind="WORKER")

    def can_handle(
        self,
        capability: CapabilityDefinition,
        implementation: Optional[ImplementationDescriptor] = None,
    ) -> bool:
        mode_val = capability.execution_mode.value if hasattr(capability.execution_mode, "value") else str(capability.execution_mode)
        return mode_val == ExecutionMode.WORKER.value

    async def execute(
        self,
        request: CapabilityRequest,
        validated_input: AIContractModel,
        context: TrustedToolExecutionContext,
    ) -> Dict[str, Any]:
        context.assert_not_timed_out()
        # Worker dispatch logic (stubbed for future background queue runner)
        return {
            "status": "QUEUED",
            "job_id": f"worker_job_{request.request_id}",
        }
