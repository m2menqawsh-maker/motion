#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Orchestrator Pipeline (المنسق الذكي)
يقوم بتتبع حالة المشروع عبر البصمة الرقمية (Hash) ولا يشغل سوى البوابات الضرورية.
الاستخدام: python scripts/pipeline.py <project_id>
"""

import sys
from scripts.path_security import validate_project_id, safe_resolve
import os
import json
import hashlib
import subprocess
from scripts.security import safe_subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def get_file_hash(filepath: Path) -> str:
    if not filepath.exists():
        return None
    hasher = hashlib.sha256()
    hasher.update(filepath.read_bytes())
    return hasher.hexdigest()

def load_state(state_file: Path) -> dict:
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def print_state_marker(state: dict):
    print(f"__PIPELINE_STATE__{json.dumps(state)}__PIPELINE_STATE__")

def run_script(script_name: str, *args) -> bool:
    script_path = Path("scripts") / script_name
    if not script_path.exists():
        print(f"❌ خطأ: لم يتم العثور على السكربت {script_name}")
        return False
        
    cmd = [sys.executable, str(script_path)] + list(args)
    print(f"   ⏳ تشغيل {script_name}...")
    
    result = safe_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"   ❌ فشل في {script_name}")
        print("\n" + "="*40 + " تفاصيل الخطأ " + "="*40)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())
        print("="*94 + "\n")
        return False
        
    print(f"   ✅ نجاح: {script_name}")
    return True

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python scripts/pipeline.py <project_id>")
        sys.exit(1)
        
    project_id = sys.argv[1]
    project_id = validate_project_id(project_id)
    proj_dir = Path("projects") / project_id
    
    if not proj_dir.exists():
        print(f"❌ المشروع {project_id} غير موجود في المجلد projects/")
        sys.exit(1)
        
    state_file = proj_dir / ".pipeline_state.json"
    state = load_state(state_file)
    
    print(f"\n🔍 [المنسق الذكي] جاري تحليل حالة المشروع: {project_id}...")
    
    # ==========================================
    # Phase 1: Asset Gate
    # ==========================================
    print(f"\n➔ المرحلة الأولى (Assets):")
    if not run_script("asset_gate.py", project_id):
        print("🛑 توقف التنفيذ بسبب أخطاء في المرحلة الأولى. أصلح المشاكل وأعد التشغيل.")
        sys.exit(1)

    # ==========================================
    # Phase 2: Plan & Taste
    # ==========================================
    plan_file = proj_dir / "master_plan.md"
    if plan_file.exists():
        current_plan_hash = get_file_hash(plan_file)
        if state.get("master_plan_hash") != current_plan_hash:
            print(f"\n➔ المرحلة الثانية (Plan): تم اكتشاف تعديلات في master_plan.md")
            
            # plan_gate.py expects <project_id>
            if not run_script("plan_gate.py", project_id):
                print("🛑 فشل الفحص! يرجى تصحيح الأخطاء في الخطة ثم إعادة تشغيل المنسق.")
                sys.exit(1)
                
            # taste_gate.py expects <scene_plan.md> path
            if not run_script("taste_gate.py", str(plan_file)):
                print("🛑 فشل الفحص! يرجى تصحيح الأخطاء الفنية (Taste) ثم إعادة تشغيل المنسق.")
                sys.exit(1)
                
            # Both passed, update state
            state["master_plan_hash"] = current_plan_hash
            print_state_marker(state)
        else:
            print(f"\n➔ المرحلة الثانية (Plan): لم يتغير master_plan.md (تخطي ✅)")
    else:
        print(f"\n➔ المرحلة الثانية (Plan): ملف master_plan.md غير موجود بعد.")

    # ==========================================
    # Phase 3: Blueprint & QC
    # ==========================================
    blueprint_file = proj_dir / "05_blueprint.json"
    if blueprint_file.exists():
        current_bp_hash = get_file_hash(blueprint_file)
        if state.get("blueprint_hash") != current_bp_hash:
            print(f"\n➔ المرحلة الثالثة (Blueprint & QC): تم اكتشاف تعديلات في 05_blueprint.json")
            
            # validate_blueprint.py expects path to blueprint
            if not run_script("validate_blueprint.py", str(blueprint_file)):
                print("🛑 توقف التنفيذ. أصلح المشاكل الهيكلية في Blueprint وأعد التشغيل.")
                sys.exit(1)
                
            # motion_validator.py expects path to blueprint
            if not run_script("motion_validator.py", str(blueprint_file)):
                print("🛑 توقف التنفيذ. شخصية الحركة غير مطابقة للشروط.")
                sys.exit(1)
                
            # code_template_gate.py expects <project_id>
            if not run_script("code_template_gate.py", project_id):
                print("🛑 توقف التنفيذ. قوالب الكود بها مشاكل.")
                sys.exit(1)
                
            # probe_qc.py expects <project_id>
            if not run_script("probe_qc.py", project_id):
                print("🛑 توقف التنفيذ. الجودة النهائية (QC) فشلت.")
                sys.exit(1)
                
            # All passed, update state
            state["blueprint_hash"] = current_bp_hash
            print_state_marker(state)
        else:
            print(f"\n➔ المرحلة الثالثة (Blueprint & QC): لم يتغير 05_blueprint.json (تخطي ✅)")
    else:
        print(f"\n➔ المرحلة الثالثة (Blueprint & QC): ملف 05_blueprint.json غير موجود بعد.")

    print("\n🎉 انتهى الفحص بنجاح! جميع ملفاتك وحالتك الحالية سليمة 100%.")

if __name__ == "__main__":
    main()
