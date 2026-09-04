#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
from pathlib import Path

def create_project(template_name: str, project_id: str):
    """إنشاء مشروع جديد من قالب"""
    templates_dir = Path(".agents/project_templates")
    template_path = templates_dir / template_name
    
    if not template_path.exists():
        print(f"❌ القالب '{template_name}' غير موجود.")
        print(f"القوالب المتاحة: {[d.name for d in templates_dir.iterdir() if d.is_dir()]}")
        return False
        
    project_path = Path(f"projects/{project_id}")
    if project_path.exists():
        print(f"❌ المشروع '{project_id}' موجود بالفعل.")
        return False
        
    try:
        shutil.copytree(template_path, project_path)
        print(f"✅ تم إنشاء المشروع '{project_id}' بنجاح من القالب '{template_name}'")
        return True
    except Exception as e:
        print(f"⚠️ فشل استنساخ القالب: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("الاستخدام: python create_from_template.py <template_name> <project_id>")
        sys.exit(1)
        
    create_project(sys.argv[1], sys.argv[2])
