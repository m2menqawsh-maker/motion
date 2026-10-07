"""
ai/orchestration/worker.py
===========================
Autonomous durable worker executing leased AI steps (S27.11).

Invariants:
- Worker claims steps atomically; multiple workers cannot steal the same work.
- Long-running execution periodically heartbeats to maintain lease validity.
- Stale workers whose leases expired are prevented from committing results.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional, Tuple

from ai.contracts.errors import AIError
from ai.contracts.run import AIStep
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.service import AIRunService

logger = logging.getLogger("ai.orchestration.worker")


class AIDurableWorker:
    """
    Autonomous worker node polling, claiming, and executing discreet AIStep tasks.
    """

    def __init__(
        self,
        worker_id: str,
        service: AIRunService,
        workspace_id: Optional[str] = None,
        lease_duration_seconds: float = 30.0,
        heartbeat_interval_seconds: float = 10.0,
    ):
        self.worker_id = worker_id
        self.service = service
        self.workspace_id = workspace_id
        self.lease_duration_seconds = lease_duration_seconds
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Signals the worker to cease processing new steps."""
        self._stop_event.set()

    def execute_claimed_step(
        self,
        step: AIStep,
        handler: Callable[[AIStep], Tuple[Optional[str], Optional[UsageRecord], Optional[CostEstimate]]],
    ) -> AIStep:
        """
        Executes a claimed step while running a background heartbeat thread to keep lease alive.
        """
        lease_token = step.lease_token
        if not lease_token:
            raise ValueError(f"Step '{step.step_id}' does not have an active lease_token.")

        heartbeat_stop = threading.Event()

        def heartbeat_loop() -> None:
            while not heartbeat_stop.wait(self.heartbeat_interval_seconds):
                try:
                    renewed = self.service.heartbeat_step(
                        step_id=step.step_id,
                        worker_id=self.worker_id,
                        lease_token=lease_token,
                        lease_duration_seconds=self.lease_duration_seconds,
                    )
                    if not renewed:
                        logger.warning(
                            "Failed to renew lease for step %s (worker: %s)",
                            step.step_id,
                            self.worker_id,
                        )
                        break
                except Exception as exc:
                    logger.warning("Heartbeat error for step %s: %s", step.step_id, exc)
                    break

        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        hb_thread.start()

        try:
            output_ref, usage, cost = handler(step)
            return self.service.complete_step(
                step_id=step.step_id,
                worker_id=self.worker_id,
                lease_token=lease_token,
                output_ref=output_ref,
                usage=usage,
                cost=cost,
            )
        except Exception as exc:
            if isinstance(exc, AIError):
                ai_err = exc
            else:
                ai_err = AIError.internal_error(
                    message=f"Step execution threw unhandled exception: {str(exc)}",
                    details={"exception_type": type(exc).__name__},
                )
            return self.service.fail_step(
                step_id=step.step_id,
                worker_id=self.worker_id,
                lease_token=lease_token,
                error=ai_err,
            )
        finally:
            heartbeat_stop.set()
            hb_thread.join(timeout=1.0)

    def process_one(
        self,
        handler: Callable[[AIStep], Tuple[Optional[str], Optional[UsageRecord], Optional[CostEstimate]]],
    ) -> Optional[AIStep]:
        """
        Polls for the next available runnable step, claims it, and executes it.
        Returns the completed/failed step, or None if no runnable work was found.
        """
        if self._stop_event.is_set():
            return None

        claimed = self.service.claim_next_runnable_step(
            worker_id=self.worker_id,
            workspace_id=self.workspace_id,
            lease_duration_seconds=self.lease_duration_seconds,
        )
        if not claimed:
            return None

        return self.execute_claimed_step(claimed, handler)
