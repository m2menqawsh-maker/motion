#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
from datetime import datetime
from pathlib import Path

def create_backup(project_id: str, stage_name: str):
    """إنشاء نسخة احتياطية من المشروع قبل مرحلة معينة"""
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        return False
        
    backup_dir = project_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{stage_name}_{timestamp}"
    
    try:
        # نقوم بنسخ الملفات الهامة فقط (الخطة، التوقيتات، الإعدادات) وليس الميديا
        backup_path.mkdir()
        for f in ["01_plan.md", "04_timings.json", "05_blueprint.json"]:
            src = project_dir / f
            if src.exists():
                shutil.copy2(src, backup_path / f)
        return True
    except Exception as e:
        print(f"⚠️ فشل النسخ الاحتياطي: {e}")
        return False
