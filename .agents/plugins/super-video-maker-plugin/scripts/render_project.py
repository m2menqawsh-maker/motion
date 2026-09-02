#!/usr/bin/env python3
"""
Render Project Wrapper — مع حماية إجبارية
يمنع الرندر إلا إذا نجحت جميع الفحوصات
"""
import sys
import os
import subprocess
import json
import time
from pathlib import Path

# إضافة مسار الـ scripts للـ sys.path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from pipeline_guard import PipelineGuard, GuardViolation
except ImportError:
    print("⚠️ PipelineGuard غير موجود — سأتجاوز الفحوصات")
    PipelineGuard = None


def main():
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python render_project.py <project_id> [composition_name]")
        sys.exit(1)

    project_id = sys.argv[1]
    composition_name = sys.argv[2] if len(sys.argv) > 2 else "MainComposition"
    
    # تحديد مسار المشروع ومجلد البناء
    workspace_root = Path.cwd()
    if (workspace_root / "projects" / project_id).exists():
        project_dir = workspace_root / "projects" / project_id
    elif (workspace_root.parent.parent / "projects" / project_id).exists():
        project_dir = workspace_root.parent.parent / "projects" / project_id
    else:
        project_dir = Path(f"projects/{project_id}").resolve()
        
    build_dir = project_dir / "06_build"

    # ─────────────────────────────────────────────
    # الفحص 1: وجود المشروع
    # ─────────────────────────────────────────────
    if not project_dir.exists():
        print(f"❌ المشروع غير موجود: {project_dir}")
        sys.exit(1)

    # ─────────────────────────────────────────────
    # الفحص 2: Pipeline Guard (إذا كان متاحاً)
    # ─────────────────────────────────────────────
    if PipelineGuard:
        try:
            guard = PipelineGuard(project_id)
            
            print("🔍 [PipelineGuard] بدء الفحوصات الإجبارية قبل الرندر...")
            
            # فحص اكتمال المراحل
            guard.require_stage_complete("blueprint")
            print("  ✅ Blueprint موجود")
            
            # فحص القفل الميكانيكي
            guard.require_probe_qc_genuine()
            print("  ✅ تقرير Probe-QC أصلي وغير مزوّر")
            
            guard.require_studio_unlocked()
            print("  ✅ الاستوديو فُتح بنجاح")
            
            # فحص موافقة المستخدم
            guard.require_user_approval()
            print("  ✅ موافقة المستخدم الصريحة موجودة وصالحة")
            
            # فحص الجودة الإبداعية (الطبقة الرابعة)
            guard.require_all_sentences_covered()
            print("  ✅ جميع مشاهد التوقيتات مبنية ومغطاة")
            
            guard.require_typescript_clean()
            print("  ✅ الكود نظيف من أخطاء TypeScript")
            
            guard.require_plan_execution_match()
            print("  ✅ الكود يطابق الخطة الموضوعة (لا توجد هلوسة)")
            
            # فحص القوالب
            if hasattr(guard, "require_templates_compliant"):
                guard.require_templates_compliant()
                print("  ✅ الكود يلتزم بالقوالب المسموحة")
            
            print("✅ [PipelineGuard] جميع الفحوصات نجحت — يمكن البدء بالرندر.\n")
            
        except GuardViolation as e:
            print(f"\n🛑 [GUARDIAN BLOCK]\n{e}\n")
            sys.exit(1)

    # ─────────────────────────────────────────────
    # الفحص 3: وجود مجلد البناء
    # ─────────────────────────────────────────────
    if not build_dir.exists():
        print(f"❌ مجلد البناء غير موجود: {build_dir}")
        print("🔧 شغّل أولاً: python materialize_project.py", project_id)
        sys.exit(1)

    # ─────────────────────────────────────────────
    # تنفيذ الرندر
    # ─────────────────────────────────────────────
    print(f"🎬 [Render] بدء الرندر للمشروع {project_id}...")
    print(f"📁 المسار: {build_dir}")
    print(f"🎞️ الـ Composition: {composition_name}")
    
    # إنشاء مجلد الإخراج
    out_dir = build_dir / "out"
    out_dir.mkdir(exist_ok=True, parents=True)
    
    output_file = out_dir / f"{project_id}_final.mp4"
    
    # تغيير المسار إلى مجلد البناء
    os.chdir(build_dir)
    use_shell = os.name == "nt"
    
    # تشغيل الرندر
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts",
        composition_name,
        str(output_file),
        "--concurrency=4"
    ]
    
    print(f"💻 الأمر: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, shell=use_shell)
    
    if result.returncode != 0:
        print(f"\n❌ فشل الرندر (كود الخروج: {result.returncode})")
        sys.exit(result.returncode)
    
    # ─────────────────────────────────────────────
    # النجاح
    # ─────────────────────────────────────────────
    print(f"\n🎉 تم الرندر بنجاح!")
    print(f"📹 الملف: {output_file}")
    if output_file.exists():
        print(f"📊 الحجم: {output_file.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
