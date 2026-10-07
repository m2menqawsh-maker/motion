"""
ai/image_processing/cache.py
============================
Content-addressed cache manager for ImageProcessingService (S28-M08).

Invariants:
- Cache key is strictly: sha256(source_hash + ":" + normalized_operation_spec + ":" + processor_version).
- normalized_operation_spec is deterministic (JSON with sorted keys and compact separators).
- Cache entries are strictly confined under project-scoped storage paths (no cross-tenant leakage).
- Missing, zero-byte, or corrupted cached payloads fail closed as cache misses.
- Processor version changes deterministically invalidate cached artifacts.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple

from ai.image_processing.security import validate_storage_key_confinement
from ai.image_processing.validator import validate_image_output
from scripts.core.storage.storage_service import StorageService

logger = logging.getLogger("ai.image_processing.cache")

PROCESSOR_VERSION: str = "img_proc_v1.0.0"


def compute_source_hash(data: bytes) -> str:
    """Computes SHA-256 hash of raw input image bytes."""
    return hashlib.sha256(data).hexdigest()


def normalize_operation_spec(spec: Dict[str, Any]) -> str:
    """Generates deterministic, compact JSON representation of transformation parameters."""
    # Filter out non-semantic volatile keys (like project_id, timestamp, job_id)
    filtered = {
        k: v for k, v in spec.items()
        if k not in ("project_id", "image_storage_key", "asset_id", "timestamp") and v is not None
    }
    return json.dumps(filtered, sort_keys=True, separators=(",", ":"))


def build_cache_key(source_hash: str, operation_spec: Dict[str, Any], processor_version: str = PROCESSOR_VERSION) -> str:
    """Computes authoritative content-addressed cache key."""
    norm_spec = normalize_operation_spec(operation_spec)
    payload = f"{source_hash}:{norm_spec}:{processor_version}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_cache_storage_key(project_id: str, cache_key: str, extension: str) -> str:
    """Constructs canonical project-confined cache storage key."""
    clean_ext = extension.lstrip(".").lower()
    if clean_ext == "jpeg":
        clean_ext = "jpg"
    prefix = "/".join(["projects", project_id, "assets", "cache"])
    rel_key = f"{prefix}/img_{cache_key}.{clean_ext}"
    return validate_storage_key_confinement(project_id, rel_key)


class ImageCacheManager:
    """
    Manages deterministic, tenant-safe content-addressed caching for image operations.
    """

    def __init__(self, storage: StorageService, processor_version: str = PROCESSOR_VERSION) -> None:
        self.storage = storage
        self.processor_version = processor_version

    def lookup(
        self,
        project_id: str,
        source_bytes: bytes,
        operation_spec: Dict[str, Any],
        extension: str,
    ) -> Optional[Tuple[str, bytes]]:
        """
        Looks up cached transformation in project-scoped storage.
        Returns: (cache_storage_key, cached_bytes) on hit, or None on miss.
        """
        source_hash = compute_source_hash(source_bytes)
        cache_key = build_cache_key(source_hash, operation_spec, self.processor_version)
        cache_storage_key = build_cache_storage_key(project_id, cache_key, extension)

        try:
            if not self.storage.exists(cache_storage_key):
                return None

            cached_data = self.storage.get(cache_storage_key)
            if not cached_data or len(cached_data) == 0:
                logger.warning(f"Cache entry '{cache_storage_key}' is empty; treating as cache miss.")
                return None

            # Verify integrity of cached artifact
            validate_image_output(cached_data)
            return cache_storage_key, cached_data
        except Exception as e:
            logger.warning(f"Failed to read/verify cache entry '{cache_storage_key}': {e}; treating as cache miss.")
            return None

    def store(
        self,
        project_id: str,
        source_bytes: bytes,
        operation_spec: Dict[str, Any],
        output_bytes: bytes,
        extension: str,
    ) -> str:
        """
        Stores validated processed artifact into content-addressed cache.
        Returns: canonical cache_storage_key.
        """
        # Validate output before storing
        validate_image_output(output_bytes)
        source_hash = compute_source_hash(source_bytes)
        cache_key = build_cache_key(source_hash, operation_spec, self.processor_version)
        cache_storage_key = build_cache_storage_key(project_id, cache_key, extension)

        self.storage.put(cache_storage_key, output_bytes)
        return cache_storage_key
