#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_template_contract.py — Generates deterministic template-runtime-contract.json.

Single Authority:
  registry/template-registry-data.json is the SOLE manually maintained machine-readable
  authority for template identity, aliases, categories, component bindings, and availability.

Guarantees:
  - ZERO regex or source-code parsing: loads registry/template-registry-data.json via native json.load().
  - ZERO filesystem scanning: runtime_available is determined strictly by registry truth.
  - 100% deterministic output (sorted keys, stable formatting, atomic write).
  - Enforces canonical ID naming rule (^[a-z0-9]+(-[a-z0-9]+)*$).
  - Prevents alias collisions (1 input identity -> exactly <= 1 canonical template).
  - Generates contracts/template-runtime-contract.json.
  - Generates registry/template-aliases.ts as a derived artifact.
  - Supports --check mode for CI staleness detection.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
AUTHORITY_FILE = ROOT / "registry" / "template-registry-data.json"
OUTPUT_CONTRACT = ROOT / "contracts" / "template-runtime-contract.json"
OUTPUT_ALIASES = ROOT / "registry" / "template-aliases.ts"

CANONICAL_ID_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class TemplateContractGenerationError(Exception):
    """Raised when validation fails during contract generation."""
    pass


def load_authority_metadata(authority_path: Path = AUTHORITY_FILE) -> Dict[str, Any]:
    """
    Loads template identity records directly from the single authority JSON file.
    Native JSON loading with zero regex or source-code parsing.
    """
    if not authority_path.exists():
        raise FileNotFoundError(f"Missing authoritative template registry file: {authority_path}")

    try:
        data = json.loads(authority_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise TemplateContractGenerationError(f"Failed to parse {authority_path}: {e}")

    if "templates" not in data or not isinstance(data["templates"], dict):
        raise TemplateContractGenerationError(f"Invalid format in {authority_path}: missing 'templates' dictionary")

    return data


def build_template_contract(authority_path: Path = AUTHORITY_FILE) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Constructs and rigorously validates the full template runtime contract from the single authority.
    Returns (contract_dict, aliases_dict).
    """
    data = load_authority_metadata(authority_path)
    raw_templates = data["templates"]

    canonical_set: Set[str] = set()
    aliases_map: Dict[str, str] = {}
    templates_dict: Dict[str, Any] = {}

    # 1. Enforce Canonical ID naming rule & build canonical set
    for cid, entry in raw_templates.items():
        if cid != entry.get("canonical_id"):
            raise TemplateContractGenerationError(
                f"Entry key '{cid}' does not match canonical_id '{entry.get('canonical_id')}'"
            )

        if not CANONICAL_ID_REGEX.match(cid):
            raise TemplateContractGenerationError(
                f"Canonical template ID '{cid}' violates naming rule regex '{CANONICAL_ID_REGEX.pattern}'. "
                f"Canonical IDs must be strictly lowercase kebab-case."
            )

        if cid in canonical_set:
            raise TemplateContractGenerationError(f"Duplicate canonical template ID: '{cid}'")
        canonical_set.add(cid)

    # 2. Validate Aliases integrity and collision rules (LED-039, LED-042)
    # Invariant: input identity -> exactly zero or one canonical template
    for cid, entry in raw_templates.items():
        raw_aliases = entry.get("aliases", [])
        if not isinstance(raw_aliases, list):
            raise TemplateContractGenerationError(f"Template '{cid}': 'aliases' must be a list")

        for alias in raw_aliases:
            if not isinstance(alias, str) or not alias.strip():
                raise TemplateContractGenerationError(f"Template '{cid}': invalid alias '{alias}'")

            # Alias cannot collide with another canonical ID
            if alias in canonical_set and alias != cid:
                raise TemplateContractGenerationError(
                    f"Alias collision: alias '{alias}' of '{cid}' is itself a canonical ID for another template"
                )

            # Duplicate conflicting alias
            if alias in aliases_map and aliases_map[alias] != cid:
                raise TemplateContractGenerationError(
                    f"Duplicate alias '{alias}' maps to conflicting targets: '{aliases_map[alias]}' vs '{cid}'"
                )

            aliases_map[alias] = cid

    # 3. Assemble validated template records
    for cid in sorted(raw_templates.keys()):
        entry = raw_templates[cid]
        # Availability is taken strictly from registry truth (not disk scanning!)
        available = bool(entry.get("runtime_available", True))
        aliases_list = sorted(list(set(entry.get("aliases", []))))

        templates_dict[cid] = {
            "canonical_id": cid,
            "category": entry.get("category", "composition"),
            "component_name": entry.get("component_name", ""),
            "default_duration_frames": entry.get("default_duration_frames", 150),
            "runtime_available": available,
            "aliases": aliases_list,
        }

    sorted_aliases = {k: aliases_map[k] for k in sorted(aliases_map.keys())}

    contract = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "contract_version": "1.0.0",
        "generated_by": "scripts/generators/generate_template_contract.py",
        "single_authority": "registry/template-registry-data.json",
        "naming_rule": {
            "canonical_id_regex": CANONICAL_ID_REGEX.pattern,
            "description": "Canonical template IDs must be lowercase kebab-case alphanumeric",
        },
        "stats": {
            "canonical_count": len(templates_dict),
            "alias_count": len(sorted_aliases),
            "total_identities": len(templates_dict) + len(sorted_aliases),
        },
        "templates": templates_dict,
        "aliases": sorted_aliases,
    }

    return contract, sorted_aliases


def serialize_aliases_ts(aliases: Dict[str, str]) -> str:
    """
    Serializes aliases dictionary to a deterministic TypeScript file.
    """
    lines = [
        "// AUTO-GENERATED by scripts/generators/generate_template_contract.py — DO NOT EDIT BY HAND",
        "// Derived from single authority: registry/template-registry-data.json",
        "",
        "export const TEMPLATE_ALIASES: Record<string, string> = {"
    ]
    for alias in sorted(aliases.keys()):
        lines.append(f'  "{alias}": "{aliases[alias]}",')
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def serialize_contract_deterministic(contract: Dict[str, Any]) -> str:
    """
    Serializes contract to a strictly deterministic JSON string with a single trailing newline.
    """
    return json.dumps(contract, indent=2, ensure_ascii=False) + "\n"


def write_file_atomic(content: str, output_path: Path) -> None:
    """
    Atomically writes content using a temporary file and atomic replace.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = output_path.with_name(f".{output_path.name}.tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())

    temp_file.replace(output_path)


def check_staleness(
    expected_contract_json: str,
    expected_aliases_ts: str,
    contract_path: Path = OUTPUT_CONTRACT,
    aliases_path: Path = OUTPUT_ALIASES,
) -> Tuple[bool, str]:
    """
    Compares the expected in-memory outputs with on-disk files.
    Returns (is_up_to_date, message).
    """
    if not contract_path.exists():
        return False, f"Contract file does not exist: {contract_path}"
    if not aliases_path.exists():
        return False, f"Aliases file does not exist: {aliases_path}"

    curr_contract = contract_path.read_text(encoding="utf-8")
    if curr_contract != expected_contract_json:
        return False, (
            f"STALE: {contract_path} does not match single authority (registry/template-registry-data.json)!\n"
            "Run `python scripts/generators/generate_template_contract.py` to regenerate."
        )

    curr_aliases = aliases_path.read_text(encoding="utf-8")
    if curr_aliases.strip() != expected_aliases_ts.strip():
        return False, (
            f"STALE: {aliases_path} does not match single authority (registry/template-registry-data.json)!\n"
            "Run `python scripts/generators/generate_template_contract.py` to regenerate."
        )

    return True, "OK: contracts/template-runtime-contract.json and registry/template-aliases.ts are up-to-date."


def main() -> int:
    check_mode = "--check" in sys.argv

    try:
        contract, aliases = build_template_contract()
        contract_json = serialize_contract_deterministic(contract)
        aliases_ts = serialize_aliases_ts(aliases)
    except Exception as e:
        print(f"❌ CONTRACT GENERATION FAILED: {e}", file=sys.stderr)
        return 1

    if check_mode:
        up_to_date, msg = check_staleness(contract_json, aliases_ts)
        if up_to_date:
            print(f"✅ {msg}")
            return 0
        else:
            print(f"❌ {msg}", file=sys.stderr)
            return 1

    write_file_atomic(contract_json, OUTPUT_CONTRACT)
    write_file_atomic(aliases_ts, OUTPUT_ALIASES)
    stats = contract["stats"]
    print(
        f"✅ GENERATED from single authority (registry/template-registry-data.json):\n"
        f"   - {OUTPUT_CONTRACT.relative_to(ROOT)} ({stats['canonical_count']} canonical templates, {stats['alias_count']} aliases)\n"
        f"   - {OUTPUT_ALIASES.relative_to(ROOT)} ({stats['alias_count']} aliases)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
