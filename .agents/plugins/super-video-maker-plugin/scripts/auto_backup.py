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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="إنشاء نسخة احتياطية للمشروع")
    parser.add_argument("project_id", help="معرف المشروع (مثال: system_validation_test)")
    parser.add_argument("stage_name", nargs="?", default="manual", help="اسم المرحلة للنسخ الاحتياطي (مثال: init)")
    args = parser.parse_args()
    
    success = create_backup(args.project_id, args.stage_name)
    if success:
        print(f"✅ تم إنشاء النسخة الاحتياطية بنجاح للمشروع {args.project_id} (المرحلة: {args.stage_name})")
    else:
        print(f"❌ فشل النسخ الاحتياطي للمشروع {args.project_id}")
        import sys
        sys.exit(1)
