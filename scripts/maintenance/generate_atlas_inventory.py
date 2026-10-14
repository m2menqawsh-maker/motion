#!/usr/bin/env python3
"""
scripts/maintenance/generate_atlas_inventory.py
===============================================
Programmatic repository file inventory generator for the MOTION Architecture Atlas.
Enumerates all 2,600+ git-tracked files, classifies each file by subsystem and role,
extracts line counts and file sizes, detects production-critical files, and produces:
  1. documentation/architecture/atlas/03_FILE_INVENTORY.json
  2. documentation/architecture/atlas/03_FILE_INVENTORY.md
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from scripts.security.security import safe_subprocess


def get_git_tracked_files() -> List[str]:
    result = safe_subprocess(
        ["git", "-c", "core.quotepath=false", "ls-files"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def classify_subsystem_and_role(path_str: str) -> Tuple[str, str, bool, str]:
    """
    Returns (subsystem, role, is_critical, description).
    Roles:
      - ACTIVE_RUNTIME: Code directly executed in production requests, workers, or rendering.
      - DEV_TOOLING: Developer scripts, maintenance, linters, code generators.
      - TEST_SUITE: Automated tests (pytest, Vitest, integration, e2e).
      - CONTRACT_SCHEMA: Pydantic schemas, TypeScript types, validation contracts.
      - GENERATED: Machine-generated artifacts, lockfiles, compiled outputs.
      - LEGACY_AGENT: Agent plugins, legacy directives, skills, archived guides.
      - ARCHIVAL_DOC: Documentation, ADRs, playbooks, Arabic learning records.
    """
    p = path_str.lower()
    
    # 1. Tests
    if p.startswith("tests/") or p.endswith(".test.ts") or p.endswith(".test.tsx") or p.endswith(".spec.ts"):
        return ("tests_verification", "TEST_SUITE", False, "Automated test suite verification")

    # 2. HTTP Transport
    if p.startswith("api/routers/") or p in ["api/main.py", "api/dependencies.py"]:
        is_crit = True
        return ("http_transport", "ACTIVE_RUNTIME", is_crit, "FastAPI endpoint routing and HTTP protocol handling")

    # 3. Auth & Tenancy
    if p.startswith("api/auth/") or p.startswith("api/middleware/") or p.startswith("scripts/core/security/"):
        is_crit = True
        return ("auth_tenancy", "ACTIVE_RUNTIME", is_crit, "Authentication, tenant scoping, and cryptographic security guards")

    # 4. Canonical Document Store & Project State
    if (
        p in ["api/services/canonical_document_service.py", "api/services/project_service.py"]
        or p.startswith("scripts/core/models/")
    ):
        is_crit = True
        return ("canonical_documents", "ACTIVE_RUNTIME", is_crit, "Canonical project state, revision CAS, and document authority")

    # 5. Storage & Distribution
    if p in ["api/services/storage_service.py", "api/services/asset_service.py"]:
        is_crit = True
        return ("storage_distribution", "ACTIVE_RUNTIME", is_crit, "Content-addressable storage, asset delivery, and tenant-scoped media distribution")

    # 6. Review & Governance
    if p.startswith("api/services/review_service.py") or p.startswith("creative_governance/") or p.startswith("contracts/governance/"):
        is_crit = True
        return ("review_governance", "ACTIVE_RUNTIME", is_crit, "Human approval gates, review bundle generation, and cryptographic seals")

    # 7. Durable Execution & Worker Engine
    if p in [
        "api/services/run_service.py",
        "scripts/core/worker.py",
        "scripts/core/run_repository.py",
        "scripts/core/project_lock.py",
        "scripts/pipeline.py",
        "api/services/pipeline_service.py",
    ] or p.startswith("scripts/core/execution/"):
        is_crit = True
        return ("durable_execution", "ACTIVE_RUNTIME", is_crit, "Durable run management, worker lease fencing, and pipeline orchestration")

    # 7. AI Creative Intelligence & Narrative Planning
    if (
        p.startswith("ai/creative/")
        or p.startswith("ai/narrative/")
        or p.startswith("ai/composition/")
        or p.startswith("ai/recipes/")
        or p.startswith("ai/taste/")
        or p.startswith("ai/orchestration/")
        or p.startswith("recipes/")
    ):
        is_crit = True
        return ("ai_creative", "ACTIVE_RUNTIME", is_crit, "Creative intelligence, narrative structuring, recipe selection, and blueprint compilation")

    # 8. Context, Knowledge, Skills & Tool Gateway
    if (
        p.startswith("ai/context/")
        or p.startswith("ai/knowledge/")
        or p.startswith("ai/skills/")
        or p.startswith("ai/tools/")
        or p.startswith("scripts/core/routing/")
    ):
        is_crit = True
        return ("context_knowledge_skills", "ACTIVE_RUNTIME", is_crit, "Context assembly, knowledge catalog, skill execution, and capability routing")

    # 9. Remotion & FFmpeg Video Rendering Subsystem
    if (
        p in ["scripts/render_project.py"]
        or p.startswith("scripts/generators/")
        or p.startswith("remotion-app/")
        or p.startswith("templates/")
    ):
        is_crit = any(p.endswith(ext) for ext in [".ts", ".tsx", ".py"])
        return ("rendering_engine", "ACTIVE_RUNTIME", is_crit, "React/Remotion canvas, template engine bridge, and FFmpeg video rendering")

    # 10. Quality Control & Gates
    if p.startswith("scripts/gates/") or p.startswith("scripts/validators/"):
        is_crit = True
        return ("quality_control", "ACTIVE_RUNTIME", is_crit, "Automated technical QC, Probe QC, Final QC, and structural gate verification")

    # 11. Storage & Distribution
    if p in ["api/services/storage_service.py", "api/services/asset_service.py"] or p in ["api/routers/artifacts.py", "api/routers/assets.py"]:
        is_crit = True
        return ("storage_distribution", "ACTIVE_RUNTIME", is_crit, "Content-addressable storage, asset delivery, and tenant-scoped media distribution")

    # 12. Schemas & Contracts
    if p.startswith("schemas/") or p.startswith("contracts/") or p.startswith("ai/contracts/"):
        is_crit = True
        return ("contracts_schemas", "CONTRACT_SCHEMA", is_crit, "Pydantic models, JSON schemas, and architectural interface contracts")

    # 13. API Services supporting
    if p.startswith("api/services/"):
        return ("api_services", "ACTIVE_RUNTIME", True, "Domain service implementation for backend orchestration")

    # 14. Dev & Maintenance Tooling
    if p.startswith("scripts/maintenance/") or p.startswith("scripts/dev/") or p.startswith("scripts/ci/"):
        return ("dev_maintenance", "DEV_TOOLING", False, "Developer automation, repository maintenance, and CI helper scripts")

    # 15. Other scripts
    if p.startswith("scripts/"):
        return ("dev_maintenance", "DEV_TOOLING", False, "Operational script or pipeline utility")

    # 16. Legacy & Agent Tooling
    if p.startswith(".agents/") or p.startswith("archive/") or p.startswith("ground-truth/"):
        return ("agent_legacy", "LEGACY_AGENT", False, "Legacy agent directives, MCP configurations, skills, or archived reference data")

    # 17. Documentation & References
    if p.startswith("documentation/") or p.startswith("references/") or p.startswith("التعلم/") or p.startswith("docs/") or p.endswith(".md"):
        return ("documentation_knowledge", "ARCHIVAL_DOC", False, "Architectural specifications, user guides, playbooks, or learning logs")

    # 18. Build / Configuration / Root files
    if p in [
        "pyproject.toml",
        "package.json",
        "tsconfig.json",
        "vitest.config.ts",
        "requirements.txt",
        "requirements-dev.txt",
        ".env.example",
        ".gitignore",
        "dockerfile",
        "license",
    ]:
        return ("configuration", "DEV_TOOLING", False, "Root build, package, lint, or runtime configuration")

    return ("miscellaneous", "SUPPORTING", False, "Supporting asset or configuration file")


def inspect_file(rel_path: str) -> Dict[str, Any]:
    full_path = WORKSPACE_ROOT / rel_path
    subsystem, role, is_critical, desc = classify_subsystem_and_role(rel_path)
    
    size_bytes = 0
    line_count = 0
    ext = full_path.suffix.lstrip(".").lower() or "none"
    
    if full_path.exists() and full_path.is_file():
        try:
            size_bytes = full_path.stat().st_size
            # Only count lines for text files
            if ext in ["py", "ts", "tsx", "js", "json", "md", "toml", "yaml", "yml", "txt", "sh", "sql"]:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)
        except Exception:
            pass

    return {
        "path": rel_path,
        "subsystem": subsystem,
        "role": role,
        "is_production_critical": is_critical,
        "extension": ext,
        "line_count": line_count,
        "size_bytes": size_bytes,
        "description": desc,
    }


def main():
    print("Collecting git-tracked files...")
    files = get_git_tracked_files()
    print(f"Total files: {len(files)}")

    inventory = []
    subsystem_stats = defaultdict(lambda: {"count": 0, "lines": 0, "bytes": 0, "critical": 0})
    role_stats = defaultdict(lambda: {"count": 0, "lines": 0, "critical": 0})

    for f in files:
        item = inspect_file(f)
        inventory.append(item)
        sub = item["subsystem"]
        role = item["role"]
        subsystem_stats[sub]["count"] += 1
        subsystem_stats[sub]["lines"] += item["line_count"]
        subsystem_stats[sub]["bytes"] += item["size_bytes"]
        if item["is_production_critical"]:
            subsystem_stats[sub]["critical"] += 1
        role_stats[role]["count"] += 1
        role_stats[role]["lines"] += item["line_count"]
        if item["is_production_critical"]:
            role_stats[role]["critical"] += 1

    # Output JSON
    output_dir = WORKSPACE_ROOT / "documentation" / "architecture" / "atlas"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "03_FILE_INVENTORY.json"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_tracked_files": len(inventory),
                "subsystems": dict(subsystem_stats),
                "roles": dict(role_stats),
                "files": inventory,
            },
            f,
            indent=2,
        )
    print(f"Wrote JSON inventory to {json_path}")

    # Output Markdown
    md_path = output_dir / "03_FILE_INVENTORY.md"
    critical_files = [item for item in inventory if item["is_production_critical"]]
    critical_files.sort(key=lambda x: (x["subsystem"], x["path"]))

    md_lines = [
        "# MOTION Repository File Inventory",
        "",
        "## 1. Executive Summary & Repository Metrics",
        "",
        f"- **Total Git-Tracked Files:** {len(inventory):,}",
        f"- **Total Lines of Tracked Code/Text:** {sum(item['line_count'] for item in inventory):,}",
        f"- **Production-Critical Files:** {len(critical_files):,}",
        "",
        "### Metrics by Subsystem",
        "",
        "| Subsystem Key | Files | Lines of Code | Critical Files | Description |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    subsystem_names = {
        "http_transport": "HTTP Transport & Ingestion",
        "auth_tenancy": "Multi-Tenancy, Auth & Security",
        "ai_creative": "AI Creative Intelligence & Narrative",
        "context_knowledge_skills": "Context, Knowledge, Skills & Tools",
        "canonical_documents": "Canonical Documents & Project State",
        "review_governance": "Review, Governance & Approvals",
        "durable_execution": "Durable Execution & Worker Engine",
        "rendering_engine": "Remotion & FFmpeg Video Renderer",
        "quality_control": "Quality Control & Automated Gates",
        "storage_distribution": "Storage & Artifact Distribution",
        "contracts_schemas": "Contracts & Pydantic Schemas",
        "api_services": "Core Domain Services",
        "tests_verification": "Test Suites & E2E Verification",
        "dev_maintenance": "Developer & Maintenance Tooling",
        "agent_legacy": "Agent Directives, Plugins & Legacy",
        "documentation_knowledge": "Architecture Documentation & ADRs",
        "configuration": "Root Build & Project Configuration",
        "miscellaneous": "Supporting Assets & Data",
    }

    for sub_key, stats in sorted(subsystem_stats.items(), key=lambda x: x[1]["count"], reverse=True):
        name = subsystem_names.get(sub_key, sub_key)
        md_lines.append(
            f"| `{sub_key}` | {stats['count']:,} | {stats['lines']:,} | {stats['critical']:,} | {name} |"
        )

    md_lines.extend([
        "",
        "### Metrics by Role Classification",
        "",
        "| Role Classification | File Count | Lines of Code | Critical Files | Operational Purpose |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| `ACTIVE_RUNTIME` | {role_stats['ACTIVE_RUNTIME']['count']:,} | {role_stats['ACTIVE_RUNTIME']['lines']:,} | {role_stats['ACTIVE_RUNTIME']['critical']:,} | Code directly executed during HTTP requests, workers, or rendering |",
        f"| `CONTRACT_SCHEMA` | {role_stats['CONTRACT_SCHEMA']['count']:,} | {role_stats['CONTRACT_SCHEMA']['lines']:,} | {role_stats['CONTRACT_SCHEMA']['critical']:,} | Canonical schemas, Pydantic models, and strict interface contracts |",
        f"| `TEST_SUITE` | {role_stats['TEST_SUITE']['count']:,} | {role_stats['TEST_SUITE']['lines']:,} | {role_stats['TEST_SUITE']['critical']:,} | Automated unit, integration, and E2E verification test suites |",
        f"| `DEV_TOOLING` | {role_stats['DEV_TOOLING']['count']:,} | {role_stats['DEV_TOOLING']['lines']:,} | {role_stats['DEV_TOOLING']['critical']:,} | Maintenance scripts, migrations, code generators, and dev tooling |",
        f"| `ARCHIVAL_DOC` | {role_stats['ARCHIVAL_DOC']['count']:,} | {role_stats['ARCHIVAL_DOC']['lines']:,} | {role_stats['ARCHIVAL_DOC']['critical']:,} | Technical documentation, ADRs, playbooks, and architecture atlas |",
        f"| `LEGACY_AGENT` | {role_stats['LEGACY_AGENT']['count']:,} | {role_stats['LEGACY_AGENT']['lines']:,} | {role_stats['LEGACY_AGENT']['critical']:,} | Legacy agent directives, MCP plugin configurations, and reference data |",
        f"| `SUPPORTING` | {role_stats['SUPPORTING']['count']:,} | {role_stats['SUPPORTING']['lines']:,} | {role_stats['SUPPORTING']['critical']:,} | Supporting media assets, icons, audio samples, and data fixtures |",
        f"| **Total** | **{sum(r['count'] for r in role_stats.values()):,}** | **{sum(r['lines'] for r in role_stats.values()):,}** | **{sum(r['critical'] for r in role_stats.values()):,}** | Fully reconciled repository file inventory |",
        "",
        "---",
        "",
        "## 2. Production-Critical Files Deep-Dive",
        "",
        "Every file in this section represents an active, mission-critical component of MOTION. Failure or drift in any of these files directly halts or corrupts the production video generation pipeline.",
        "",
        "| File Path | Subsystem | LOC | Role | Architectural Responsibility |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    for item in critical_files:
        md_lines.append(
            f"| [`{item['path']}`](file:///{WORKSPACE_ROOT / item['path']}) | `{item['subsystem']}` | {item['line_count']:,} | `{item['role']}` | {item['description']} |"
        )

    md_lines.extend([
        "",
        "---",
        "",
        "## 3. Subsystem File Directory Maps",
        "",
    ])

    # Group inventory by subsystem
    grouped = defaultdict(list)
    for item in inventory:
        grouped[item["subsystem"]].append(item)

    for sub_key, items in sorted(grouped.items()):
        name = subsystem_names.get(sub_key, sub_key)
        md_lines.extend([
            f"### Subsystem: {name} (`{sub_key}`)",
            f"- **File Count:** {len(items):,}",
            f"- **Lines of Code:** {sum(i['line_count'] for i in items):,}",
            f"- **Critical Files:** {sum(1 for i in items if i['is_production_critical']):,}",
            "",
            "<details>",
            f"<summary>Click to expand all {len(items)} files in {sub_key}</summary>",
            "",
            "| Relative File Path | Role | Lines | Size (Bytes) |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for it in sorted(items, key=lambda x: x["path"]):
            md_lines.append(f"| `{it['path']}` | `{it['role']}` | {it['line_count']:,} | {it['size_bytes']:,} |")
        md_lines.extend([
            "",
            "</details>",
            "",
        ])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"Wrote Markdown inventory to {md_path}")


if __name__ == "__main__":
    main()
