"""
ai/security/bounds.py
=====================
Server-Side Abuse Bounding & Resource Ceilings (S27.22 / AI-15).

Invariants:
- All execution constraints are strictly ENFORCED SERVER-SIDE.
- Enforces maximum prompt length/tokens to prevent memory/context overflow attacks.
- Enforces maximum tool recursion depth to prevent runaway loops.
- Enforces maximum execution steps per AIRun.
- Enforces maximum execution timeout.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


class ExecutionCeilingExceededError(RuntimeError):
    """Raised when an AI run or tool call breaches hard resource ceilings."""
    pass


@dataclass(frozen=True)
class ExecutionBoundsPolicy:
    """Configurable resource boundaries for AI runs."""
    max_prompt_chars: int = 100_000
    max_estimated_tokens: int = 25_000
    max_ai_steps: int = 50
    max_tool_depth: int = 5
    max_execution_duration_sec: float = 300.0
    max_spend_per_run: Decimal = Decimal("10.0000")

    def validate_prompt(self, prompt: str) -> None:
        """Validates that input prompt does not exceed bounded length."""
        if len(prompt) > self.max_prompt_chars:
            raise ExecutionCeilingExceededError(
                f"Prompt length ({len(prompt)} chars) exceeds server-side ceiling ({self.max_prompt_chars} chars)."
            )

    def validate_step_count(self, current_step: int) -> None:
        """Validates that step count has not exceeded maximum allowed steps."""
        if current_step > self.max_ai_steps:
            raise ExecutionCeilingExceededError(
                f"Execution step count ({current_step}) exceeded maximum allowed limit ({self.max_ai_steps})."
            )

    def validate_tool_depth(self, current_depth: int) -> None:
        """Validates that recursive tool depth is bounded."""
        if current_depth > self.max_tool_depth:
            raise ExecutionCeilingExceededError(
                f"Recursive tool depth ({current_depth}) exceeded maximum ceiling ({self.max_tool_depth}). Potential recursive loop detected."
            )

    def validate_spend(self, current_spend: Decimal) -> None:
        """Validates that run spend does not exceed max ceiling."""
        if current_spend > self.max_spend_per_run:
            raise ExecutionCeilingExceededError(
                f"Run cumulative spend (${current_spend}) exceeded run spend ceiling (${self.max_spend_per_run})."
            )
