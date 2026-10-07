"""
ai/media/repository.py
======================
Abstract repository boundary for Media Intelligence persistence (S27.13 / S27.14).

Invariants:
- Abstract interface only; never imports raw DB drivers or executes SQL in ai/* (ADR-004 DEC-01).
- Concrete implementations in scripts/core/ handle SQL transactions and atomic persistence.
- Guarantees strict multi-tenant isolation across all index lookups and storage references.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class MediaIntelligenceIndexRecord:
    """
    Lightweight index record linking an asset and version to its canonical StorageService report.
    Persisted in relational storage for fast metadata queries.
    """
    workspace_id: str
    asset_id: str
    content_hash: str
    analysis_version: str
    storage_key: str
    report_hash: str
    created_at: datetime


class MediaIntelligenceRepository(ABC):
    """
    Authoritative persistence boundary for Media Intelligence index records.
    """

    @abstractmethod
    def save_index(self, record: MediaIntelligenceIndexRecord) -> None:
        """
        Saves or updates an asset's media intelligence index record.
        Strictly scopes persistence to the record's workspace_id.
        """
        raise NotImplementedError

    @abstractmethod
    def get_index(
        self,
        workspace_id: str,
        asset_id: str,
        content_hash: str,
        analysis_version: str,
    ) -> Optional[MediaIntelligenceIndexRecord]:
        """
        Retrieves a media intelligence index record by exact workspace, asset, content hash,
        and analysis version. Returns None if not found or belongs to another workspace.
        """
        raise NotImplementedError

    @abstractmethod
    def list_indices(
        self,
        workspace_id: str,
        asset_id: str,
    ) -> List[MediaIntelligenceIndexRecord]:
        """
        Lists all analysis index records for a given asset within a workspace.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_index(
        self,
        workspace_id: str,
        asset_id: str,
        analysis_version: str,
    ) -> bool:
        """
        Deletes a media intelligence index record for a specific version.
        Returns True if deleted, False if not found.
        """
        raise NotImplementedError
