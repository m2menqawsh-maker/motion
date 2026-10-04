"""
ai/skills/__init__.py
=====================
Canonical Skills Platform package for Creative Intelligence (S28-02).

Guarantees:
- Skill = How the system handles a task type (Skill ≠ Permission, Skill ≠ Tool).
- Strict separation of responsibilities:
  * SkillRegistry: in-memory versioned catalog of valid skills.
  * SkillLoader: schema validation and disk/markdown parsing.
  * SkillRouter: dynamic two-stage routing (eligibility gate + ranking).
  * SkillContext: bounded execution preparation.
  * SkillExecutor: ToolAuthorizationPolicy enforcement.
"""

from __future__ import annotations

from ai.skills.contracts import (
    SkillCandidate,
    SkillContext,
    SkillRoutingContext,
    SkillRoutingResult,
)
from ai.skills.context import (
    SkillContextBuilder,
    SkillExecutionError,
    SkillExecutor,
    ToolAuthorizationDeniedError,
    ToolUndeclaredError,
)
from ai.skills.loader import (
    SkillLoader,
    SkillLoaderError,
    SkillSourceNotFoundError,
    SkillValidationError,
)
from ai.skills.registry import (
    DuplicateSkillError,
    SkillNotFoundError,
    SkillRegistry,
    SkillRegistryError,
)
from ai.skills.router import (
    SkillRouter,
)

__all__ = [
    # Contracts
    "SkillRoutingContext",
    "SkillCandidate",
    "SkillRoutingResult",
    "SkillContext",
    # Registry
    "SkillRegistry",
    "SkillRegistryError",
    "DuplicateSkillError",
    "SkillNotFoundError",
    # Loader
    "SkillLoader",
    "SkillLoaderError",
    "SkillValidationError",
    "SkillSourceNotFoundError",
    # Router
    "SkillRouter",
    # Context & Executor
    "SkillContextBuilder",
    "SkillExecutor",
    "SkillExecutionError",
    "ToolUndeclaredError",
    "ToolAuthorizationDeniedError",
]
