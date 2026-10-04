"""
ai/planning/errors.py
=====================
Domain error hierarchy for S28-05 Creative Planning and Blueprint Compilation.

Guarantees:
- Granular, structured exceptions for every failure mode.
- Explicit fail-closed semantics before Core delivery.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class PlanningError(Exception):
    """Base error for creative planning domain."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class UnresolvedCreativeConflictError(PlanningError):
    """Raised when CreativePlanner is invoked with unresolved creative conflicts."""
    pass


class InvalidCreativeBriefError(PlanningError):
    """Raised when a brief violates planning prerequisites."""
    pass


class DurationPlanningError(PlanningError):
    """Raised when scene or project durations violate bounds or tolerance."""
    pass


class AudioPolicyViolationError(PlanningError):
    """Raised when an audio operation contradicts the active AudioMode."""
    pass


class CapabilitySafetyError(PlanningError):
    """Raised when a forbidden or unavailable capability is requested."""
    pass


class CompilerError(Exception):
    """Base error for Blueprint Compiler domain."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class UnknownTemplateCompilerError(CompilerError):
    """Raised when a template decision references an unregistered or unknown template."""
    pass


class UnknownAssetCompilerError(CompilerError):
    """Raised when an asset reference is not found in the authoritative Manifest."""
    pass


class TimingCompilerError(CompilerError):
    """Raised when timing calculations yield invalid durations, negative frames, or impossible overlaps."""
    pass


class MissingRequiredSceneCompilerError(CompilerError):
    """Raised when a required narrative beat or scene purpose is missing from the plan."""
    pass


class ForbiddenCapabilityCompilerError(CompilerError):
    """Raised when a plan demands capabilities barred by system policy or audio mode."""
    pass


class CompilerValidationError(CompilerError):
    """Raised when compiled Blueprint fails canonical Core validation."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message, details={"errors": errors or []})
        self.errors = errors or []


class NeedsCreateEscalationCompilerError(CompilerError):
    """Raised when compilation is attempted on a scene that requires CREATE escalation."""
    pass


class TemplateRegistryUnavailableError(PlanningError):
    """Raised when Template Registry is unreadable, corrupted, or unavailable, preventing tier evaluation."""
    pass

