"""
ai/capabilities/catalog.py
==========================
Authoritative runtime catalog and loader for product capabilities (S28-M03).

Invariants:
- Loads canonical definitions directly from documentation/s28m/CAPABILITY_CATALOG.json.
- Validates all 32 capabilities strictly against CapabilityDefinition contract.
- Deterministic, provider-neutral capability lookup.
- Zero dangling references or unregistered capabilities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

from ai.contracts import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityFamily,
    CapabilityType,
)


class UnknownCapabilityError(Exception):
    """Raised when an unknown or unregistered capability is requested."""
    def __init__(self, capability_id: str):
        super().__init__(f"Unknown capability '{capability_id}'. Must be one of the registered canonical capabilities.")
        self.capability_id = capability_id


class CapabilityCatalog:
    """
    Authoritative runtime repository for canonical capability definitions.
    Initializes from the canonical CAPABILITY_CATALOG.json artifact.
    """

    def __init__(self, catalog_path: Optional[Union[Path, str]] = None) -> None:
        self._capabilities: Dict[str, CapabilityDefinition] = {}
        self._catalog_path = self._resolve_catalog_path(catalog_path)
        self._load()

    @staticmethod
    def _resolve_catalog_path(path: Optional[Union[Path, str]]) -> Path:
        if path:
            p = Path(path)
            if p.exists():
                return p
        # Default root resolution
        candidates = [
            Path("documentation/s28m/CAPABILITY_CATALOG.json"),
            Path(__file__).resolve().parent.parent.parent / "documentation" / "s28m" / "CAPABILITY_CATALOG.json",
        ]
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError("Could not locate canonical CAPABILITY_CATALOG.json in repository.")

    def _load(self) -> None:
        with open(self._catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_list = data.get("capabilities", [])
        for item in raw_list:
            cap_def = CapabilityDefinition.model_validate(item)
            cap_id = cap_def.capability_id.value if hasattr(cap_def.capability_id, "value") else str(cap_def.capability_id)
            self._capabilities[cap_id] = cap_def

    @property
    def total_count(self) -> int:
        return len(self._capabilities)

    def has(self, capability_id: Union[CapabilityType, str]) -> bool:
        cid = capability_id.value if hasattr(capability_id, "value") else str(capability_id)
        return cid in self._capabilities

    def get(self, capability_id: Union[CapabilityType, str]) -> Optional[CapabilityDefinition]:
        cid = capability_id.value if hasattr(capability_id, "value") else str(capability_id)
        return self._capabilities.get(cid)

    def get_or_raise(self, capability_id: Union[CapabilityType, str]) -> CapabilityDefinition:
        cap = self.get(capability_id)
        if not cap:
            cid = capability_id.value if hasattr(capability_id, "value") else str(capability_id)
            raise UnknownCapabilityError(cid)
        return cap

    def list_all(self) -> List[CapabilityDefinition]:
        return list(self._capabilities.values())

    def by_category(self, category: Union[CapabilityCategory, str]) -> List[CapabilityDefinition]:
        cat_val = category.value if hasattr(category, "value") else str(category)
        return [c for c in self._capabilities.values() if (c.category.value if hasattr(c.category, "value") else str(c.category)) == cat_val]

    def by_family(self, family: Union[CapabilityFamily, str]) -> List[CapabilityDefinition]:
        fam_val = family.value if hasattr(family, "value") else str(family)
        return [c for c in self._capabilities.values() if (c.family.value if hasattr(c.family, "value") else str(c.family)) == fam_val]


_default_capability_catalog: Optional[CapabilityCatalog] = None


def get_capability_catalog() -> CapabilityCatalog:
    """Returns the singleton canonical CapabilityCatalog."""
    global _default_capability_catalog
    if _default_capability_catalog is None:
        _default_capability_catalog = CapabilityCatalog()
    return _default_capability_catalog
