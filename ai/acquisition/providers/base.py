"""
ai/acquisition/providers/base.py
================================
Abstract base class for external stock media source adapters (S28-M05).

Invariants:
- All provider adapters normalize external payloads to canonical StockCandidate models.
- Adapters report honest availability status based on configured environment secrets.
- Missing credentials or provider unavailability fail in a structured, observable manner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Set

from ai.acquisition.contracts import (
    AcquisitionDescriptor,
    StockCandidate,
    StockMediaType,
    StockSearchQuery,
)


class StockSourceAdapter(ABC):
    """Authoritative contract for stock provider adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'pexels', 'pixabay', 'freesound', 'iconify')."""
        pass

    @property
    @abstractmethod
    def supported_media_types(self) -> Set[StockMediaType]:
        """Set of media modalities supported by this provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is operational and credentials are configured."""
        pass

    @abstractmethod
    async def search(self, query: StockSearchQuery) -> List[StockCandidate]:
        """
        Executes a search against the provider API and returns normalized candidates.
        """
        pass

    @abstractmethod
    def resolve_acquisition(
        self,
        candidate: StockCandidate,
        requested_variant_id: Optional[str] = None,
    ) -> AcquisitionDescriptor:
        """
        Constructs a safe acquisition descriptor specifying the download URL and metadata.
        """
        pass
