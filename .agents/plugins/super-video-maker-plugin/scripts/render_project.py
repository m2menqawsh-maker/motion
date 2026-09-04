#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_project.py — سكريبت وسيط لرندر المشروع بأمان
"""
import sys
import os
import subprocess
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

def main():
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python render_project.py <project_id> [composition_name]")
        sys.exit(1)

    project_id = sys.argv[1]
    composition_name = sys.argv[2] if len(sys.argv) > 2 else "MainComposition"

    workspace_root = Path.cwd()
    if (workspace_root / "projects" / project_id).exists():
        proj_dir = workspace_root / "projects" / project_id
    elif (workspace_root.parent / "projects" / project_id).exists():
        proj_dir = workspace_root.parent / "projects" / project_id
    else:
        proj_dir = Path(f"projects/{project_id}").resolve()

    build_dir = proj_dir / "06_build"
    approval_file = proj_dir / ".studio_approved"
    unlock_file = proj_dir / ".studio_unlocked"

    print("=" * 60)
    print(f"🎬 رندر المشروع: {project_id}")
    print(f"🎞️ الـ Composition: {composition_name}")
    print("=" * 60)

    if not proj_dir.exists():
        print(f"❌ المشروع غير موجود: {proj_dir}")
        sys.exit(1)

    if not build_dir.exists():
        print(f"❌ مجلد البناء غير موجود: {build_dir}")
        sys.exit(1)
        
    # فحص كشف الموافقة المزوّرة
    if approval_file.exists() and unlock_file.exists():
        approval_mtime = approval_file.stat().st_mtime
        unlock_mtime = unlock_file.stat().st_mtime
        time_diff = approval_mtime - unlock_mtime
        if time_diff < 10:
            print("\n🛑 [GUARDIAN BLOCK] الموافقة مشبوهة - أُنشئت بسرعة كبيرة!")
            print(f"السبب: ملف .studio_approved أُنشئ بعد {time_diff:.1f} ثانية فقط من فتح الاستوديو (أقل من 10 ثوانٍ)")
            print("طريقة الإصلاح: يجب معاينة الفيديو فعلياً في الاستوديو قبل الموافقة، ثم إنشاء ملف .studio_approved يدوياً.")
            sys.exit(1)

    try:
        scripts_dir = Path(__file__).parent.resolve()
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
            
        from pipeline_guard import PipelineGuard, GuardViolation
        
        guard = PipelineGuard(project_id)
        
        print("🔍 [PipelineGuard] جاري الفحص...")
        guard.require_probe_qc_genuine()
        print("  ✅ تقرير Probe-QC أصلي ومختوم رقمياً")
        guard.require_studio_unlocked()
        print("  ✅ القفل الميكانيكي مفتوح (.studio_unlocked)")
        guard.require_user_approval()
        print("  ✅ موافقة المستخدم صحيحة (.studio_approved)")
        guard.require_all_sentences_covered()
        print("  ✅ جميع الجمل الصوتية مغطاة بمشاهد")
        guard.require_typescript_clean()
        print("  ✅ الكود خالٍ من أخطاء TypeScript")
        guard.require_motion_valid()
        print("  ✅ تنوع القوالب والـ SFX مقبول")
        guard.require_smart_qc_passed()
        print("  ✅ فحص Smart QC تم بنجاح")
        
    except ImportError as e:
        print(f"⚠️ خطأ في استيراد PipelineGuard: {e}")
        sys.exit(1)
    except GuardViolation as e:
        print(f"\n🛑 فشل فحص الأمان والجودة [PipelineGuard]:")
        print(f"القاعدة المخالفة: {e.rule}")
        print(f"السبب: {e.reason}")
        print(f"🔧 طريقة الإصلاح: {e.fix}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n🛑 [GUARDIAN BLOCK] حدث خطأ غير متوقع: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ جميع الفحوصات نجحت — جاري الرندر...")
    print("=" * 60)
    
    out_dir = build_dir / "out"
    out_dir.mkdir(exist_ok=True, parents=True)
    output_file = out_dir / f"{project_id}_final.mp4"
    
    os.chdir(str(build_dir))
    use_shell = os.name == "nt"
    
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
    
    print("\n" + "=" * 60)
    print(f"🎉 تم الرندر بنجاح!")
    print(f"📹 الملف: {output_file}")
    print("=" * 60)
    
    # تشغيل Final QC تلقائياً بعد الرندر
    print("\n🔍 تشغيل الفحص النهائي (Final QC)...")
    final_qc_script = scripts_dir / "final_qc.py"
    if final_qc_script.exists():
        subprocess.run([sys.executable, str(final_qc_script), project_id], check=False)
        
    # استدعاء الحارس للتأكد من نجاح الفحص
    try:
        guard.require_final_qc_passed()
        print("✅ الفحص النهائي (Final QC) اجتاز بنجاح!")
    except GuardViolation as e:
        print(f"\n🛑 فشل الفحص النهائي للرندر:\n{e.reason}\n🔧 الإصلاح: {e.fix}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
