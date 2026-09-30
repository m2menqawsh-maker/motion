"""
Canonical Asset Cache Identity & Deduplication Subsystem (S13 - ASSET-007).

Authoritative rules:
1. Cache identity is strictly content-addressed and depends on:
   source_content_hash + normalized_processing_spec_hash + processor_version.
2. asset_id alone is NEVER used as the cache identity.
3. Spec serialization is canonical and deterministic (key-order invariant).
4. Semantic equivalence produces a cache hit; parameter/content/version changes produce a cache miss.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union


DEFAULT_PROCESSOR_VERSION = "1.0.0"


def normalize_processing_spec(spec: Optional[Dict[str, Any]]) -> str:
    """
    Deterministically normalizes a processing specification into a canonical JSON string.
    Keys are sorted recursively, whitespace is stripped, and numbers/strings are normalized.
    """
    if not spec:
        return "{}"

    def _canonicalize(val: Any) -> Any:
        if isinstance(val, dict):
            return {str(k): _canonicalize(v) for k, v in sorted(val.items(), key=lambda item: str(item[0]))}
        elif isinstance(val, list):
            return [_canonicalize(elem) for elem in val]
        elif isinstance(val, float):
            # Normalize float representation to eliminate trailing zeros or precision artifacts
            if val.is_integer():
                return int(val)
            return round(val, 6)
        elif isinstance(val, (int, bool, str)):
            return val
        elif val is None:
            return None
        else:
            return str(val)

    canonical_obj = _canonicalize(spec)
    return json.dumps(canonical_obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def compute_content_hash(source: Union[str, Path, bytes]) -> str:
    """
    Computes SHA-256 hash of a file's content or bytes in lowercase hex.
    """
    hasher = hashlib.sha256()
    if isinstance(source, bytes):
        hasher.update(source)
    else:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Source file for hashing not found: {path}")
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
    return hasher.hexdigest()


def compute_processing_spec_hash(spec: Optional[Dict[str, Any]]) -> str:
    """
    Computes SHA-256 hash of normalized processing specification.
    """
    normalized = normalize_processing_spec(spec)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_cache_identity(
    source_content_hash: str,
    processing_spec_hash: Optional[str] = None,
    processor_version: str = DEFAULT_PROCESSOR_VERSION,
) -> str:
    """
    Produces the authoritative cache key identity combining:
    source_content_hash + normalized_processing_spec_hash + processor_version.
    """
    if not source_content_hash:
        raise ValueError("source_content_hash cannot be empty")
    
    spec_h = processing_spec_hash or compute_processing_spec_hash(None)
    combined = f"{source_content_hash.strip().lower()}:{spec_h.strip().lower()}:{processor_version.strip()}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AssetCacheKey:
    """Structured representation of an asset's cache key identity."""
    content_hash: str
    processing_spec_hash: str
    processor_version: str
    cache_key: str

    @classmethod
    def from_inputs(
        cls,
        source: Union[str, Path, bytes],
        spec: Optional[Dict[str, Any]] = None,
        processor_version: str = DEFAULT_PROCESSOR_VERSION,
    ) -> AssetCacheKey:
        content_hash = compute_content_hash(source)
        spec_hash = compute_processing_spec_hash(spec)
        cache_key = compute_cache_identity(content_hash, spec_hash, processor_version)
        return cls(
            content_hash=content_hash,
            processing_spec_hash=spec_hash,
            processor_version=processor_version,
            cache_key=cache_key,
        )
