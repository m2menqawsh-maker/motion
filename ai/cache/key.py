"""
ai/cache/key.py
===============
Canonical deterministic cache key derivation engine (S27.12).

Invariants:
- Deterministic canonical hashing: identical semantic inputs yield identical keys.
- Tenant isolation: workspace_id is strictly embedded into every canonical key.
- All outcome-determining dimensions must be included:
  workspace_id, capability, input_hash, content_hash, settings_hash,
  model, model_version, contract_version, prompt_version, analysis_version.
- Strictly forbidden in logical keys: repr(object), random UUID, request timestamp.
- Server-side derived ONLY: models or external clients never choose cache keys.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from ai.contracts.cache import AICacheKeyParams


def normalize_canonical_json(data: Any) -> str:
    """
    Deterministically serializes any primitive, dict, or list into canonical JSON.
    - Dictionary keys are sorted recursively.
    - Floats are rounded to 8 decimal places or converted to integer if integral,
      eliminating cross-platform floating-point serialization variances.
    - Whitespace and non-canonical separators are stripped.
    - Non-primitive types are normalized by string conversion.
    """
    def _normalize(val: Any) -> Any:
        if isinstance(val, dict):
            return {
                str(k): _normalize(v)
                for k, v in sorted(val.items(), key=lambda item: str(item[0]))
            }
        elif isinstance(val, (list, tuple)):
            return [_normalize(elem) for elem in val]
        elif isinstance(val, float):
            if val.is_integer():
                return int(val)
            return round(val, 8)
        elif isinstance(val, (int, bool, str)):
            return val
        elif val is None:
            return None
        else:
            return str(val)

    normalized = _normalize(data)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def compute_input_hash(
    input_data: Dict[str, Any],
    content_hash: Optional[str] = None,
) -> str:
    """
    Computes a canonical SHA-256 hash across structured input payload
    and optional media/file content hash.
    """
    canonical_input = normalize_canonical_json(input_data)
    ch = content_hash.strip().lower() if content_hash else ""
    combined = f"{canonical_input}::{ch}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def compute_settings_hash(settings: Dict[str, Any]) -> str:
    """
    Computes a canonical SHA-256 hash of model generation parameters and hyperparameters.
    """
    canonical_settings = normalize_canonical_json(settings)
    return hashlib.sha256(canonical_settings.encode("utf-8")).hexdigest()


def derive_canonical_cache_key(params: AICacheKeyParams) -> str:
    """
    Derives an authoritative, deterministic canonical cache key from typed parameters.

    Key dimensions (all strictly bound):
    1. workspace_id (tenant scope)
    2. capability (domain capability identifier)
    3. input_hash (canonical input + content hash)
    4. settings_hash (hyperparameters / options)
    5. model (resolved model or empty)
    6. model_version (model version or empty)
    7. contract_version (SemVer of capability contract)
    8. prompt_version (SemVer or hash of prompt template)
    9. analysis_version (SemVer of analysis post-processing)
    """
    input_hash = compute_input_hash(params.input_data, params.content_hash)
    settings_hash = compute_settings_hash(params.settings)

    model_id = (params.model or "").strip()
    model_version = (params.model_version or "").strip()
    contract_version = params.contract_version.strip()
    prompt_version = params.prompt_version.strip()
    analysis_version = params.analysis_version.strip()

    canonical_parts = [
        f"ws:{params.workspace_id.strip()}",
        f"cap:{params.capability.value}",
        f"in:{input_hash}",
        f"set:{settings_hash}",
        f"mod:{model_id}",
        f"mv:{model_version}",
        f"cv:{contract_version}",
        f"pv:{prompt_version}",
        f"av:{analysis_version}",
    ]
    raw_composite = "|".join(canonical_parts)
    key_hash = hashlib.sha256(raw_composite.encode("utf-8")).hexdigest()
    return f"ck_{key_hash}"
