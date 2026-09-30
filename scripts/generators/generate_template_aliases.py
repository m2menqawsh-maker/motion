#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_template_aliases.py — Adapter delegating to single authority template contract generator.

Derived from single authority: registry/template-registry-data.json
Zero regex source-code parsing. Zero manual maintenance.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generators.generate_template_contract import (
    build_template_contract,
    serialize_aliases_ts,
    OUTPUT_ALIASES,
)


def generate_aliases():
    contract, aliases = build_template_contract()
    content = serialize_aliases_ts(aliases)
    return content, len(contract["templates"]), len(aliases)


def main():
    check_mode = "--check" in sys.argv

    content, active_count, alias_count = generate_aliases()

    if check_mode:
        if not OUTPUT_ALIASES.exists():
            print(f"FAIL: {OUTPUT_ALIASES} does not exist.")
            sys.exit(1)
        current = OUTPUT_ALIASES.read_text(encoding="utf-8")
        if current.strip() != content.strip():
            print(f"FAIL: {OUTPUT_ALIASES} is out of date. Run scripts/generators/generate_template_contract.py to update.")
            sys.exit(1)
        print(f"PASS: {OUTPUT_ALIASES} is up-to-date ({active_count} active templates, {alias_count} aliases).")
        sys.exit(0)

    OUTPUT_ALIASES.write_text(content, encoding="utf-8")
    print(f"Generated {OUTPUT_ALIASES.relative_to(ROOT)} ({active_count} active templates, {alias_count} aliases).")


if __name__ == "__main__":
    main()

