"""
ai/memory/types.py
==================
Canonical type definitions, enums, and categorization for AI Memory Subsystem (S27.6, S27.7).
"""

from __future__ import annotations

from enum import Enum

# Canonical shared contract types imported from foundational contracts (Layer 0)
from ai.contracts.memory import (
    EpistemicStatus,
    MemoryScope,
    MemoryType,
    SourceType,
)


class MemoryStatus(str, Enum):
    """Lifecycle state of an individual memory record."""
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"
    REJECTED = "REJECTED"


class ConfidenceLevel(str, Enum):
    """Categorical confidence classification."""
    LOW = "LOW"        # [0.0, 0.5)
    MEDIUM = "MEDIUM"  # [0.5, 0.8)
    HIGH = "HIGH"      # [0.8, 1.0]


def confidence_to_level(score: float) -> ConfidenceLevel:
    """Maps a numeric confidence score (0.0 - 1.0) to its canonical ConfidenceLevel."""
    if score < 0.5:
        return ConfidenceLevel.LOW
    elif score < 0.8:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.HIGH


def level_to_min_confidence(level: ConfidenceLevel) -> float:
    """Returns the lower bound threshold for a given ConfidenceLevel."""
    if level == ConfidenceLevel.HIGH:
        return 0.8
    elif level == ConfidenceLevel.MEDIUM:
        return 0.5
    return 0.0





class WriteDecisionType(str, Enum):
    """Outcome decision emitted by MemoryPolicy when evaluating a candidate."""
    STORE = "STORE"
    MERGE = "MERGE"
    UPDATE = "UPDATE"
    SUPERSEDE = "SUPERSEDE"
    REJECT = "REJECT"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
