#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migrate Legacy Projects
يبحث في مجلد projects عن أي مشروع قديم يعتمد على التسميات القديمة
ويعيد تسميتها إلى التسميات القياسية لبروتوكول v4.0.
- 01_plan.md -> master_plan.md
- blueprint.json -> 05_blueprint.json
"""
import os
import shutil
from pathlib import Path

def migrate_projects():
    projects_dir = Path("projects")
    if not projects_dir.exists():
        print("No projects directory found.")
        return

    migrated_count = 0
    for proj in projects_dir.iterdir():
        if not proj.is_dir():
            continue
            
        migrated_something = False
        
        # Migrate 01_plan.md -> master_plan.md
        old_plan = proj / "01_plan.md"
        new_plan = proj / "master_plan.md"
        if old_plan.exists() and not new_plan.exists():
            print(f"Renaming {old_plan} -> {new_plan}")
            shutil.move(str(old_plan), str(new_plan))
            migrated_something = True
            
        # Migrate blueprint.json -> 05_blueprint.json
        old_bp = proj / "blueprint.json"
        new_bp = proj / "05_blueprint.json"
        if old_bp.exists() and not new_bp.exists():
            print(f"Renaming {old_bp} -> {new_bp}")
            shutil.move(str(old_bp), str(new_bp))
            migrated_something = True
            
        if migrated_something:
            migrated_count += 1
            
    print(f"Migration completed. {migrated_count} projects migrated.")

if __name__ == "__main__":
    migrate_projects()
