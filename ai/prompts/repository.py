"""
ai/prompts/repository.py
========================
Abstract repository boundary for prompt persistence (S27.18).

Invariants:
- Abstract interface only; never imports raw DB drivers or executes SQL in ai/* (ADR-004 DEC-01).
- Concrete implementations in scripts/core/ handle SQLite storage, transactions, and unique constraints.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ai.contracts.prompt import PromptContract, PromptStatus


class PromptRepository(ABC):
    """Authoritative storage boundary for versioned prompt entities."""

    @abstractmethod
    def save_prompt(self, prompt: PromptContract) -> PromptContract:
        """
        Persists a new prompt version.
        Raises PromptVersionImmutableError if (prompt_id, version, workspace_id) already exists.
        """
        raise NotImplementedError

    @abstractmethod
    def get_prompt(
        self,
        prompt_id: str,
        version: int,
        workspace_id: Optional[str] = None,
    ) -> Optional[PromptContract]:
        """Retrieves a specific prompt version within tenant boundary (or platform scope)."""
        raise NotImplementedError

    @abstractmethod
    def get_active_production_prompt(
        self,
        prompt_id: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[PromptContract]:
        """Retrieves the currently approved PRODUCTION prompt version."""
        raise NotImplementedError

    @abstractmethod
    def list_versions(
        self,
        prompt_id: str,
        workspace_id: Optional[str] = None,
    ) -> List[PromptContract]:
        """Lists all versions of a prompt, ordered monotonically by version number."""
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self,
        prompt_id: str,
        version: int,
        new_status: PromptStatus,
        workspace_id: Optional[str] = None,
    ) -> PromptContract:
        """Updates the lifecycle status of an existing prompt version."""
        raise NotImplementedError
