"""
ai/mcp/adapters/parity.py
=========================
Automated parity verification between legacy MCP functions and new domain/adapters (S27.10).

Invariants:
- Verifies behavior parity on representative fixtures.
- Proves domain service replacements preserve required capabilities without regressions.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


def verify_cache_check_parity(
    legacy_fn: Any,
    domain_fn: Any,
    asset_id: str,
    specs_hash: str,
    cache_dir: str,
    project_id: str,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Compares cache check behavior between legacy common-tools-mcp check_cache
    and canonical AssetService.check_asset_cache.
    """
    legacy_res = legacy_fn(asset_id=asset_id, specs_hash=specs_hash, cache_dir=cache_dir)
    domain_res = domain_fn(project_id=project_id, asset_id=asset_id, specs_hash=specs_hash)

    # Parity semantic: both hit or both miss
    legacy_hit = legacy_res is not None
    domain_hit = domain_res is not None
    parity_ok = (legacy_hit == domain_hit)

    return parity_ok, {
        "legacy_hit": legacy_hit,
        "domain_hit": domain_hit,
        "legacy_result": legacy_res,
        "domain_result": domain_res,
    }


def verify_asset_status_parity(
    domain_result: Dict[str, Any],
    expected_status: str,
    expected_asset_id: str,
) -> bool:
    """
    Verifies that the new AssetService.update_asset_status output satisfies
    the contract previously managed by media-sources-mcp change_asset_status.
    """
    if domain_result.get("asset_id") != expected_asset_id:
        return False
    if domain_result.get("status") != expected_status:
        return False
    return True


def verify_save_cache_parity(
    domain_saved_path: str,
    asset_id: str,
    specs_hash: str,
) -> bool:
    """
    Verifies that the new AssetService.save_asset_to_cache output conforms to
    the naming and storage semantics of legacy save_to_cache.
    """
    from pathlib import Path
    p = Path(domain_saved_path)
    if not p.exists():
        return False
    # Verify filename format: {asset_id}_{specs_hash}.ext
    expected_prefix = f"{asset_id}_{specs_hash}"
    if not p.name.startswith(expected_prefix):
        return False
    return True

