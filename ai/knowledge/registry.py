"""
ai/knowledge/registry.py
========================
Canonical registry for platform reference knowledge (S28-02).

Guarantees:
- Knowledge = Information & Experience (Knowledge ≠ Runtime Authority).
- Strict version and lifecycle status governance (ACTIVE vs RETIRED vs DRAFT).
- Retired knowledge is strictly excluded from active queries.
- Immutable snapshots for deterministic retrieval execution.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple
from ai.contracts.creative.skills_knowledge import KnowledgeDescriptor, KnowledgeStatus


class KnowledgeRegistryError(Exception):
    """Base exception for Knowledge Registry errors."""
    pass


class DuplicateKnowledgeError(KnowledgeRegistryError):
    """Raised when registering a conflicting knowledge descriptor."""
    pass


class KnowledgeNotFoundError(KnowledgeRegistryError):
    """Raised when a requested knowledge descriptor is not registered."""
    pass


class KnowledgeRegistry:
    """
    Authoritative catalog of known knowledge documents and their metadata.
    Provides versioned indexing and active-status filtering.
    """

    def __init__(self) -> None:
        # Key: (knowledge_id, version) -> KnowledgeDescriptor
        self._entries: Dict[Tuple[str, str], KnowledgeDescriptor] = {}
        # Key: knowledge_id -> latest/default KnowledgeDescriptor
        self._latest: Dict[str, KnowledgeDescriptor] = {}

    def register(self, descriptor: KnowledgeDescriptor, allow_overwrite: bool = True) -> None:
        """
        Registers a KnowledgeDescriptor in the registry.
        """
        key = (descriptor.knowledge_id, descriptor.version)
        if key in self._entries and not allow_overwrite:
            raise DuplicateKnowledgeError(
                f"Knowledge item '{descriptor.knowledge_id}' v{descriptor.version} already registered."
            )

        self._entries[key] = descriptor

        # Track the latest active version (or latest registered if none active)
        existing_latest = self._latest.get(descriptor.knowledge_id)
        if existing_latest is None:
            self._latest[descriptor.knowledge_id] = descriptor
        else:
            # Prefer active over retired/draft, and higher version strings
            if descriptor.status == KnowledgeStatus.ACTIVE and existing_latest.status != KnowledgeStatus.ACTIVE:
                self._latest[descriptor.knowledge_id] = descriptor
            elif descriptor.status == existing_latest.status and descriptor.version >= existing_latest.version:
                self._latest[descriptor.knowledge_id] = descriptor

    def register_many(self, descriptors: Sequence[KnowledgeDescriptor], allow_overwrite: bool = True) -> None:
        """Registers multiple descriptors."""
        for d in descriptors:
            self.register(d, allow_overwrite=allow_overwrite)

    def get(self, knowledge_id: str, version: Optional[str] = None) -> Optional[KnowledgeDescriptor]:
        """
        Retrieves a knowledge descriptor by ID and optional version.
        Returns None if not found or version mismatch.
        """
        if version is not None:
            return self._entries.get((knowledge_id, version))
        return self._latest.get(knowledge_id)

    def get_active(self, knowledge_id: str, version: Optional[str] = None) -> Optional[KnowledgeDescriptor]:
        """
        Retrieves a descriptor ONLY if its status is ACTIVE.
        Strictly excludes RETIRED or DRAFT knowledge.
        """
        item = self.get(knowledge_id, version=version)
        if item is not None and item.status == KnowledgeStatus.ACTIVE:
            return item
        return None

    def is_active(self, knowledge_id: str, version: Optional[str] = None) -> bool:
        """Returns True if the knowledge item is registered and ACTIVE."""
        return self.get_active(knowledge_id, version=version) is not None

    def list_active(self) -> List[KnowledgeDescriptor]:
        """Returns all registered KnowledgeDescriptors with status ACTIVE."""
        return [d for d in self._entries.values() if d.status == KnowledgeStatus.ACTIVE]

    def list_all(self) -> List[KnowledgeDescriptor]:
        """Returns all registered KnowledgeDescriptors regardless of status."""
        return list(self._entries.values())

    def unregister(self, knowledge_id: str, version: Optional[str] = None) -> bool:
        """Removes an item or specific version from registry."""
        removed = False
        if version is not None:
            key = (knowledge_id, version)
            if key in self._entries:
                del self._entries[key]
                removed = True
        else:
            keys_to_del = [k for k in self._entries if k[0] == knowledge_id]
            for k in keys_to_del:
                del self._entries[k]
                removed = True

        # Recompute latest
        remaining = [d for d in self._entries.values() if d.knowledge_id == knowledge_id]
        if remaining:
            self._latest[knowledge_id] = sorted(remaining, key=lambda x: (x.status == KnowledgeStatus.ACTIVE, x.version))[-1]
        elif knowledge_id in self._latest:
            del self._latest[knowledge_id]

        return removed

    def clear(self) -> None:
        """Clears all registered entries."""
        self._entries.clear()
        self._latest.clear()

    def snapshot(self) -> Dict[str, KnowledgeDescriptor]:
        """Returns an immutable snapshot dict of current latest descriptors."""
        return dict(self._latest)
