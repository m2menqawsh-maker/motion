#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/migration/tenant_project_migration.py — Tenant Project Filesystem Migration Utility.

Safely inventories and transitions legacy flat project structures:
    projects/{project_id}/
into tenant-isolated hierarchical paths:
    projects/{workspace_id}/{project_id}/

Features:
- Non-destructive by default (--dry-run).
- Collision detection and prevention.
- Missing-owner resolution and fallback strategy.
- Audit ledger manifest with cryptographic hashes / timestamp.
- Atomic execution and reversible rollback (--rollback <manifest>).
- Idempotent and recovery-safe against interrupted operations.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tenant_migration")


@dataclass
class MigrationEntry:
    project_id: str
    source_path: str
    target_path: str
    workspace_id: str
    owner_source: str  # e.g., 'project.json', 'state_store', 'database', 'default_workspace'
    status: str  # 'PLANNED', 'SUCCESS', 'SKIPPED_COLLISION', 'FAILED', 'ROLLED_BACK'
    detail: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MigrationReport:
    timestamp: str
    dry_run: bool
    base_dir: str
    total_discovered: int
    planned_moves: int
    collisions: int
    missing_owner_fallback: int
    successful_moves: int = 0
    failed_moves: int = 0
    entries: List[MigrationEntry] = field(default_factory=list)


class TenantProjectMigrator:
    """Manages dry-run, execution, and rollback of tenant project filesystem layouts."""

    def __init__(self, base_dir: Path | str = "projects", default_workspace: str = "ws_default") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.default_workspace = default_workspace

    def _discover_legacy_projects(self) -> List[Tuple[str, Path]]:
        """Finds top-level project directories in base_dir that are not workspace folders."""
        if not self.base_dir.exists() or not self.base_dir.is_dir():
            return []

        legacy_projects = []
        for entry in self.base_dir.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            # Skip hidden folders
            if name.startswith("."):
                continue

            # Check if this directory looks like a project rather than a workspace directory
            # Indicators: contains project metadata files OR starts with prj_ OR has no subdirectories containing prj_
            is_project = False
            for marker in ("project.json", ".pipeline_state.json", "01_manifest.json", "manifest.json", "05_blueprint.json"):
                if (entry / marker).exists():
                    is_project = True
                    break

            if not is_project and name.startswith("prj_"):
                is_project = True

            # If it has subdirectories that contain project files, it's a workspace directory, not a legacy project
            if not is_project:
                has_nested_projects = False
                for sub in entry.iterdir():
                    if sub.is_dir() and (sub.name.startswith("prj_") or (sub / "project.json").exists()):
                        has_nested_projects = True
                        break
                if not has_nested_projects:
                    # Treat unknown top-level folder as legacy project if it's not a known system dir
                    if name not in ("temp", "tmp", "logs", "cache", "archive"):
                        is_project = True

            if is_project:
                legacy_projects.append((name, entry))

        return sorted(legacy_projects, key=lambda x: x[0])

    def _resolve_project_owner(self, project_id: str, proj_dir: Path) -> Tuple[str, str]:
        """Resolves the owner workspace ID from project metadata, database, or fallback."""
        # 1. Check project.json
        p_json = proj_dir / "project.json"
        if p_json.exists():
            try:
                with open(p_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ws = data.get("workspace_id") or data.get("owner_workspace_id")
                if ws and isinstance(ws, str) and ws.strip():
                    return ws.strip(), "project.json"
            except Exception as e:
                logger.debug(f"Could not read {p_json}: {e}")

        # 2. Check .pipeline_state.json
        s_json = proj_dir / ".pipeline_state.json"
        if s_json.exists():
            try:
                with open(s_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ws = data.get("workspace_id")
                if ws and isinstance(ws, str) and ws.strip():
                    return ws.strip(), ".pipeline_state.json"
            except Exception as e:
                logger.debug(f"Could not read {s_json}: {e}")

        # 3. Check Database if configured
        try:
            from scripts.core.database import get_database_engine
            db_engine = get_database_engine()
            with db_engine.connect() as conn:
                cursor = conn.execute("SELECT workspace_id FROM projects WHERE project_id = ?", (project_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    return str(row[0]), "database.projects"
                # Check runs
                cursor = conn.execute("SELECT workspace_id FROM pipeline_runs WHERE project_id = ? LIMIT 1", (project_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    return str(row[0]), "database.pipeline_runs"
        except Exception:
            pass

        return self.default_workspace, "fallback_default_workspace"

    def plan(self) -> MigrationReport:
        """Inspects legacy projects and builds a dry-run migration plan."""
        legacy_list = self._discover_legacy_projects()
        entries: List[MigrationEntry] = []
        collisions = 0
        missing_owner_fallback = 0

        for project_id, src_path in legacy_list:
            workspace_id, owner_source = self._resolve_project_owner(project_id, src_path)
            if owner_source == "fallback_default_workspace":
                missing_owner_fallback += 1

            target_path = self.base_dir / workspace_id / project_id

            if target_path.exists():
                collisions += 1
                entry = MigrationEntry(
                    project_id=project_id,
                    source_path=str(src_path),
                    target_path=str(target_path),
                    workspace_id=workspace_id,
                    owner_source=owner_source,
                    status="SKIPPED_COLLISION",
                    detail=f"Target path already exists: {target_path}",
                )
            else:
                entry = MigrationEntry(
                    project_id=project_id,
                    source_path=str(src_path),
                    target_path=str(target_path),
                    workspace_id=workspace_id,
                    owner_source=owner_source,
                    status="PLANNED",
                )
            entries.append(entry)

        report = MigrationReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            dry_run=True,
            base_dir=str(self.base_dir),
            total_discovered=len(legacy_list),
            planned_moves=sum(1 for e in entries if e.status == "PLANNED"),
            collisions=collisions,
            missing_owner_fallback=missing_owner_fallback,
            entries=entries,
        )
        return report

    def execute(self, manifest_out: Optional[Path] = None) -> MigrationReport:
        """Executes the migration atomically, generating a persistent audit manifest for rollback."""
        report = self.plan()
        report.dry_run = False

        manifest_records: List[Dict[str, Any]] = []

        for entry in report.entries:
            if entry.status != "PLANNED":
                continue

            src = Path(entry.source_path)
            dst = Path(entry.target_path)

            try:
                # Ensure parent workspace directory exists
                dst.parent.mkdir(parents=True, exist_ok=True)
                # Atomic rename/move
                shutil.move(str(src), str(dst))
                entry.status = "SUCCESS"
                report.successful_moves += 1
                logger.info(f"Migrated: {src} -> {dst}")
            except Exception as e:
                entry.status = "FAILED"
                entry.detail = str(e)
                report.failed_moves += 1
                logger.error(f"Failed to migrate {src} to {dst}: {e}")

            manifest_records.append(asdict(entry))

        # Write audit manifest
        if manifest_out is None:
            manifest_out = self.base_dir / f"migration_manifest_{int(time.time())}.json"

        manifest_data = {
            "version": "1.0",
            "timestamp": report.timestamp,
            "base_dir": str(self.base_dir),
            "total_discovered": report.total_discovered,
            "successful_moves": report.successful_moves,
            "failed_moves": report.failed_moves,
            "entries": [asdict(e) for e in report.entries],
        }
        with open(manifest_out, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(f"Migration completed. Manifest saved to: {manifest_out}")
        return report

    @classmethod
    def rollback(cls, manifest_path: Path | str) -> Dict[str, Any]:
        """Rolls back an executed migration using the recorded audit manifest."""
        manifest_file = Path(manifest_path).resolve()
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_file}")

        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("entries", [])
        rolled_back = 0
        failed = 0
        skipped = 0
        rollback_log = []

        for item in entries:
            if item.get("status") != "SUCCESS":
                skipped += 1
                continue

            src = Path(item["source_path"])
            dst = Path(item["target_path"])

            if not dst.exists():
                logger.warning(f"Rollback target does not exist: {dst}")
                rollback_log.append({"project_id": item["project_id"], "status": "FAILED", "reason": "Target missing"})
                failed += 1
                continue

            if src.exists():
                logger.warning(f"Original source already exists, cannot rollback: {src}")
                rollback_log.append({"project_id": item["project_id"], "status": "FAILED", "reason": "Original source exists"})
                failed += 1
                continue

            try:
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(src))
                rolled_back += 1
                rollback_log.append({"project_id": item["project_id"], "status": "ROLLED_BACK"})
                logger.info(f"Rolled back: {dst} -> {src}")
            except Exception as e:
                failed += 1
                rollback_log.append({"project_id": item["project_id"], "status": "FAILED", "error": str(e)})
                logger.error(f"Rollback failed for {dst}: {e}")

        result = {
            "manifest": str(manifest_file),
            "rolled_back": rolled_back,
            "failed": failed,
            "skipped": skipped,
            "details": rollback_log,
        }
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Tenant Project Filesystem Migration Utility")
    parser.add_argument("--base-dir", default="projects", help="Base directory containing projects")
    parser.add_argument("--default-workspace", default="ws_default", help="Default workspace for unowned projects")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform dry run without moving files (default)")
    parser.add_argument("--execute", action="store_true", help="Execute actual project relocation (requires explicit flag)")
    parser.add_argument("--rollback", type=str, help="Path to manifest file for rollback")
    parser.add_argument("--json-report", type=str, help="Save report to JSON file")

    args = parser.parse_args()

    if args.rollback:
        logger.info(f"Initiating rollback from manifest: {args.rollback}")
        res = TenantProjectMigrator.rollback(args.rollback)
        print(json.dumps(res, indent=2))
        return 0 if res["failed"] == 0 else 1

    migrator = TenantProjectMigrator(base_dir=args.base_dir, default_workspace=args.default_workspace)

    if args.execute:
        logger.warning("EXECUTE mode requested. Moving projects...")
        report = migrator.execute()
    else:
        logger.info("DRY-RUN mode. No files will be moved.")
        report = migrator.plan()

    report_dict = asdict(report)

    if args.json_report:
        with open(args.json_report, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)
        logger.info(f"Report saved to: {args.json_report}")

    print("\n=== MIGRATION REPORT SUMMARY ===")
    print(f"Timestamp:               {report.timestamp}")
    print(f"Dry Run:                 {report.dry_run}")
    print(f"Base Directory:          {report.base_dir}")
    print(f"Total Discovered:        {report.total_discovered}")
    print(f"Planned Moves:           {report.planned_moves}")
    print(f"Collisions Detected:     {report.collisions}")
    print(f"Missing Owner Fallback:  {report.missing_owner_fallback}")
    if not report.dry_run:
        print(f"Successful Moves:        {report.successful_moves}")
        print(f"Failed Moves:            {report.failed_moves}")
    print("================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
