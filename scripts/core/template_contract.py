"""
scripts/core/template_contract.py — Shared Template Registry Contract Loader and Resolver (S15).

Sole Authority:
  Runtime Template Registry via generated artifact `contracts/template-runtime-contract.json`.

Enforces:
  - Strict bijection between Canonical Registry and Contract
  - Fail-closed resolution semantics:
    - Canonical ID -> resolves to itself
    - Alias -> resolves to canonical ID
    - Unknown ID -> fail-closed (returns None / raises UnknownTemplateError)
    - Metadata name -> fail-closed
    - Malformed / whitespace -> fail-closed
  - Zero tolerance for substring, fuzzy, or implicit case-insensitive matching
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

DEFAULT_CONTRACT_PATH = Path(__file__).resolve().parent.parent.parent / "contracts" / "template-runtime-contract.json"


class TemplateContractError(Exception):
    """Base error for template contract operations."""
    pass


class UnknownTemplateError(TemplateContractError):
    """Raised when a template ID is not recognized in the canonical contract."""
    def __init__(
        self,
        template_id: str,
        scene_id: Optional[str] = None,
        project_id: Optional[str] = None,
        error_code: str = "UNKNOWN_TEMPLATE_ID",
    ):
        self.template_id = template_id
        self.scene_id = scene_id
        self.project_id = project_id
        self.error_code = error_code
        
        ctx_parts = []
        if project_id:
            ctx_parts.append(f"project='{project_id}'")
        if scene_id:
            ctx_parts.append(f"scene='{scene_id}'")
        ctx_str = f" ({', '.join(ctx_parts)})" if ctx_parts else ""
        
        super().__init__(
            f"Unknown or unregistered template '{template_id}'{ctx_str} [{error_code}]"
        )


@dataclass(frozen=True)
class TemplateContractEntry:
    """Metadata representing an authoritative template in the contract."""
    canonical_id: str
    category: str
    component_name: str
    default_duration_frames: int
    runtime_available: bool
    aliases: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "category": self.category,
            "component_name": self.component_name,
            "default_duration_frames": self.default_duration_frames,
            "runtime_available": self.runtime_available,
            "aliases": list(self.aliases),
        }


class TemplateRegistryContract:
    """
    In-memory representation of the generated template runtime contract.
    Provides deterministic identity resolution across all pipeline stages.
    """
    def __init__(self, contract_path: Path = DEFAULT_CONTRACT_PATH):
        self.contract_path = Path(contract_path)
        self.version: str = "1.0.0"
        self.canonical_regex: str = "^[a-z0-9]+(-[a-z0-9]+)*$"
        self.templates: Dict[str, TemplateContractEntry] = {}
        self.aliases: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.contract_path.exists():
            raise FileNotFoundError(
                f"Generated template contract not found: {self.contract_path}. "
                "Run `python scripts/generators/generate_template_contract.py`."
            )

        data = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.version = data.get("contract_version", "1.0.0")
        self.canonical_regex = data.get("naming_rule", {}).get("canonical_id_regex", "^[a-z0-9]+(-[a-z0-9]+)*$")
        
        # Load aliases
        self.aliases = {str(k): str(v) for k, v in data.get("aliases", {}).items()}
        
        # Load templates
        raw_templates = data.get("templates", {})
        self.templates = {}
        for cid, tdata in raw_templates.items():
            self.templates[cid] = TemplateContractEntry(
                canonical_id=tdata["canonical_id"],
                category=tdata.get("category", "composition"),
                component_name=tdata.get("component_name", ""),
                default_duration_frames=tdata.get("default_duration_frames", 150),
                runtime_available=tdata.get("runtime_available", True),
                aliases=tdata.get("aliases", []),
            )

    def resolve(self, template_id: Any) -> Optional[TemplateContractEntry]:
        """
        Resolves a given template identifier (canonical ID or alias) to its canonical entry.
        Fails closed (returns None) for unknown IDs, metadata names, or malformed strings.
        Strict: no strip(), no lowercase normalization, no substring matching.
        """
        if not isinstance(template_id, str) or not template_id:
            return None

        # Fail closed on whitespace padding or unexpected whitespace
        if template_id.strip() != template_id:
            return None

        # 1. Direct canonical hit
        if template_id in self.templates:
            return self.templates[template_id]

        # 2. Authoritative alias hit
        if template_id in self.aliases:
            target_canonical = self.aliases[template_id]
            return self.templates.get(target_canonical)

        # 3. Fail closed
        return None

    def is_valid(self, template_id: Any) -> bool:
        """
        Returns True if the identifier resolves to a registered, runtime-available template.
        """
        entry = self.resolve(template_id)
        return entry is not None and entry.runtime_available

    def canonicalize(
        self,
        template_id: Any,
        scene_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> str:
        """
        Resolves the template identifier and returns its canonical template ID.
        Raises UnknownTemplateError if not valid or unavailable.
        """
        entry = self.resolve(template_id)
        if entry is None or not entry.runtime_available:
            raise UnknownTemplateError(
                template_id=str(template_id),
                scene_id=scene_id,
                project_id=project_id,
            )
        return entry.canonical_id

    def get_entry(self, template_id: Any) -> Optional[TemplateContractEntry]:
        """Alias for resolve."""
        return self.resolve(template_id)

    def list_canonical_ids(self) -> List[str]:
        """Returns sorted list of all canonical template IDs."""
        return sorted(list(self.templates.keys()))

    def list_aliases(self) -> Dict[str, str]:
        """Returns dictionary of alias -> canonical_id."""
        return dict(self.aliases)


_CONTRACT_INSTANCE: Optional[TemplateRegistryContract] = None


def get_template_contract(contract_path: Optional[Path] = None, reload: bool = False) -> TemplateRegistryContract:
    """Singleton provider for TemplateRegistryContract."""
    global _CONTRACT_INSTANCE
    if reload or _CONTRACT_INSTANCE is None or contract_path is not None:
        path = contract_path or DEFAULT_CONTRACT_PATH
        _CONTRACT_INSTANCE = TemplateRegistryContract(contract_path=path)
    return _CONTRACT_INSTANCE
