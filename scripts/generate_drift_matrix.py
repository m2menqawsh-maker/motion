#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_drift_matrix.py — Generates .remediation/phase-9/template-runtime-drift.json.

Audits every active production template across ground truth, validators, and runtime registry.
Ensures Unknown = 0.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "ground-truth" / "template_catalog.json"
TI_PATH = ROOT / "ground-truth" / "TEMPLATE_INDEX.md"
REGISTRY_FILE = ROOT / "registry" / "template-registry.tsx"
OUT_FILE = ROOT / ".remediation" / "phase-9" / "template-runtime-drift.json"


def build_matrix():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    ti_text = TI_PATH.read_text(encoding="utf-8")
    ti_templates = set(re.findall(r"\| `([\w-]+)` \|", ti_text))

    reg_text = REGISTRY_FILE.read_text(encoding="utf-8")
    direct_entries = dict(re.findall(r'["\']([a-zA-Z0-9_-]+)["\']:\s*\{.*?component:\s*(\w+)', reg_text, re.DOTALL))
    comp_to_canonical = {comp: key for key, comp in direct_entries.items()}

    # Check template-aliases.ts
    aliases_file = ROOT / "registry" / "template-aliases.ts"
    aliases = {}
    if aliases_file.exists():
        for line in aliases_file.read_text(encoding="utf-8").splitlines():
            m = re.search(r'["\']([^"\']+)["\']:\s*["\']([^"\']+)["\']', line)
            if m:
                aliases[m.group(1)] = m.group(2)

    active_templates = [
        c for c in catalog
        if c.get("path", "").startswith("templates/")
        and c.get("path") != "templates/brand-resolver.ts"
        and not c.get("path", "").endswith(".d.ts")
    ]

    records = []
    for item in sorted(active_templates, key=lambda x: x["name"].lower()):
        name = item["name"]
        stem = Path(item["path"]).stem
        impl_path = ROOT / item["path"]
        impl_exists = impl_path.exists()
        val_accepts = name in ti_templates
        canonical_target = comp_to_canonical.get(stem)

        resolves = bool(
            canonical_target and (
                name in direct_entries or
                name in aliases or
                canonical_target in direct_entries
            )
        )

        if not impl_exists:
            status = "MISSING_IMPLEMENTATION"
        elif not val_accepts:
            status = "VALIDATOR_DRIFT"
        elif not resolves or not canonical_target:
            status = "MISSING_RUNTIME_REGISTRATION"
        else:
            status = "CONSISTENT"

        records.append({
            "name": name,
            "stem": stem,
            "ground_truth_active": True,
            "validator_accepts": val_accepts,
            "implementation_exists": impl_exists,
            "runtime_registry_resolves": resolves,
            "runtime_target": canonical_target,
            "status": status
        })

    summary = {
        "metadata": {
            "total_active_production_templates": len(records),
            "consistent_count": sum(1 for r in records if r["status"] == "CONSISTENT"),
            "missing_runtime_registration_count": sum(1 for r in records if r["status"] == "MISSING_RUNTIME_REGISTRATION"),
            "missing_implementation_count": sum(1 for r in records if r["status"] == "MISSING_IMPLEMENTATION"),
            "validator_drift_count": sum(1 for r in records if r["status"] == "VALIDATOR_DRIFT"),
            "unknown_count": 0
        },
        "templates": records
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote drift matrix to {OUT_FILE.relative_to(ROOT)}:")
    print(f"  Active templates: {len(records)}")
    print(f"  Consistent: {summary['metadata']['consistent_count']}")
    print(f"  Missing runtime registration: {summary['metadata']['missing_runtime_registration_count']}")
    print(f"  Unknown: 0")


if __name__ == "__main__":
    build_matrix()
