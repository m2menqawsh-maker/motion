#!/usr/bin/env python3
"""
Open Studio Wrapper — مع حماية إجبارية
يمنع فتح الاستوديو إلا إذا نجحت الفحوصات الإجبارية
"""
import sys
import os
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from pipeline_guard import PipelineGuard, GuardViolation
except ImportError:
    print("⚠️ PipelineGuard غير موجود — سأتجاوز الفحوصات")
    PipelineGuard = None


def main():
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python open_studio.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]
    
    workspace_root = Path.cwd()
    if (workspace_root / "projects" / project_id).exists():
        project_dir = workspace_root / "projects" / project_id
    elif (workspace_root.parent.parent / "projects" / project_id).exists():
        project_dir = workspace_root.parent.parent / "projects" / project_id
    else:
        project_dir = Path(f"projects/{project_id}").resolve()
        
    build_dir = project_dir / "06_build"

    if not project_dir.exists():
        print(f"❌ المشروع غير موجود: {project_dir}")
        sys.exit(1)

    # ─────────────────────────────────────────────
    # الفحص: Pipeline Guard
    # ─────────────────────────────────────────────
    if PipelineGuard:
        try:
            guard = PipelineGuard(project_id)
            
            print("🔍 [PipelineGuard] فحص الشروط قبل فتح الاستوديو...")
            
            guard.require_probe_qc_genuine()
            print("  ✅ تقرير Probe-QC أصلي")
            
            guard.require_studio_unlocked()
            print("  ✅ ملف .studio_unlocked موجود")
            
            # فحص الجودة الإبداعية (الطبقة الرابعة)
            guard.require_all_sentences_covered()
            print("  ✅ جميع مشاهد التوقيتات مبنية ومغطاة")
            
            guard.require_typescript_clean()
            print("  ✅ الكود نظيف من أخطاء TypeScript")
            
            guard.require_plan_execution_match()
            print("  ✅ الكود يطابق الخطة الموضوعة")
            
            print("✅ [PipelineGuard] الفحوصات نجحت — جاري فتح الاستوديو.\n")
            
        except GuardViolation as e:
            print(f"\n🛑 [GUARDIAN BLOCK]\n{e}\n")
            sys.exit(1)
    else:
        # Fallback: فحص يدوي
        unlock_file = project_dir / ".studio_unlocked"
        if not unlock_file.exists():
            print(f"🛑 ممنوع فتح الاستوديو!")
            print(f"السبب: ملف {unlock_file} غير موجود.")
            print(f"الإجراء: شغّل probe_qc.py أولاً")
            sys.exit(1)

    if not build_dir.exists():
        print(f"❌ مجلد البناء غير موجود: {build_dir}")
        sys.exit(1)

    # ─────────────────────────────────────────────
    # فتح الاستوديو
    # ─────────────────────────────────────────────
    print(f"🚀 [Studio] فتح الاستوديو للمشروع {project_id}...")
    os.chdir(build_dir)
    use_shell = os.name == "nt"
    subprocess.run(["npx", "remotion", "studio"], shell=use_shell)


if __name__ == "__main__":
    main()
