"""
ai/knowledge/catalog_service.py
================================
Production Knowledge Catalog Service managing lifecycle, idempotent indexing,
observability, and readiness probing (REALITY-008).

Guarantees:
- Idempotent catalog loading and semantic indexing.
- Thread-safe singleton access.
- Safe failure handling with clear diagnostic error reporting.
- Explicit readiness inspection for health and runtime gating.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ai.knowledge.router import KnowledgeRouter

logger = logging.getLogger("clean_video.knowledge_catalog")


class KnowledgeCatalogService:
    """
    Manages initialization lifecycle and readiness state of the Canonical Knowledge Catalog.
    """

    def __init__(self, router: Optional[KnowledgeRouter] = None) -> None:
        self._router = router or KnowledgeRouter()
        self._lock = threading.Lock()
        self._is_ready: bool = False
        self._status: str = "UNINITIALIZED"
        self._total_chunks: int = 0
        self._last_error: Optional[str] = None

    @property
    def router(self) -> KnowledgeRouter:
        return self._router

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @property
    def status(self) -> str:
        return self._status

    @property
    def total_chunks(self) -> int:
        return self._total_chunks

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def initialize_catalog(self, verify_hash: bool = True, force: bool = False) -> int:
        """
        Idempotently loads and indexes the canonical knowledge catalog from references/.
        Returns the total number of indexed semantic chunks.
        """
        with self._lock:
            if self._is_ready and not force:
                logger.debug(
                    "Knowledge catalog already initialized (%d chunks ready). Skipping re-init.",
                    self._total_chunks,
                )
                return self._total_chunks

            try:
                logger.info("Initializing canonical knowledge catalog...")
                chunks_indexed = self._router.initialize_canonical_catalog(verify_hash=verify_hash)
                self._total_chunks = chunks_indexed
                self._is_ready = True
                self._status = "READY"
                self._last_error = None
                logger.info(
                    "Canonical knowledge catalog successfully initialized (%d chunks indexed).",
                    chunks_indexed,
                )
                return chunks_indexed
            except Exception as exc:
                self._is_ready = False
                self._status = "FAILED"
                self._last_error = str(exc)
                logger.error(
                    "Failed to initialize canonical knowledge catalog: %s",
                    exc,
                    exc_info=True,
                )
                raise

    def get_readiness(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Returns structured readiness status for health check probes.
        """
        with self._lock:
            details: Dict[str, Any] = {
                "status": self._status,
                "total_chunks": self._total_chunks,
                "error": self._last_error,
            }
            return self._is_ready, details


_singleton_catalog_service: Optional[KnowledgeCatalogService] = None
_singleton_lock = threading.Lock()


def get_knowledge_catalog_service() -> KnowledgeCatalogService:
    """
    Returns the process-level singleton KnowledgeCatalogService.
    """
    global _singleton_catalog_service
    if _singleton_catalog_service is None:
        with _singleton_lock:
            if _singleton_catalog_service is None:
                _singleton_catalog_service = KnowledgeCatalogService()
    return _singleton_catalog_service
