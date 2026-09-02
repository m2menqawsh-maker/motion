#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_project.py — سكريبت وسيط لرندر المشروع بأمان
مع حماية شاملة عبر PipelineGuard + فحص التزوير والموافقة
"""
import sys
import os
import subprocess
import json
import time
import hashlib
from pathlib import Path

# ترميز UTF-8 للنوافذ
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def verify_report_seal(project_dir: Path) -> bool:
    """يتحقق من أن تقرير Probe-QC أصلي وغير مزوّر"""
    report_path = project_dir / "probe_qc_report.json"
    seal_path = report_path.with_suffix(".json.seal")
    
    if not seal_path.exists():
        return True  # تقرير قديم
    
    if not report_path.exists():
        return False
    
    expected = seal_path.read_text(encoding="utf-8").strip()
    actual = hashlib.sha256(report_path.read_bytes()).hexdigest()
    return expected == actual


def main():
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python render_project.py <project_id> [composition_name]")
        sys.exit(1)

    project_id = sys.argv[1]
    composition_name = sys.argv[2] if len(sys.argv) > 2 else "MainComposition"

    # تحديد مسار المشروع
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
    qc_report = proj_dir / "probe_qc_report.json"

    print("=" * 60)
    print(f"🎬 رندر المشروع: {project_id}")
    print(f"🎞️ الـ Composition: {composition_name}")
    print("=" * 60)

    # ─────────────────────────────────────────────
    # الفحص 1: وجود المشروع ومجلد البناء
    # ─────────────────────────────────────────────
    if not proj_dir.exists():
        print(f"❌ المشروع غير موجود: {proj_dir}")
        sys.exit(1)

    if not build_dir.exists():
        print(f"❌ مجلد البناء غير موجود: {build_dir}")
        sys.exit(1)
    print("✅ المشروع ومجلد البناء موجودان")

    # ─────────────────────────────────────────────
    # الفحص 2: القفل الميكانيكي (.studio_unlocked)
    # ─────────────────────────────────────────────
    if not unlock_file.exists():
        print("\n🛑 [GUARDIAN BLOCK] القفل الميكانيكي لم يُفتح!")
        print("الإجراء: شغّل probe_qc.py وانتظر نجاحه")
        sys.exit(1)
    print("✅ القفل الميكانيكي مفتوح")

    # ─────────────────────────────────────────────
    # الفحص 3: تقرير Probe-QC غير مزوّر
    # ─────────────────────────────────────────────
    if qc_report.exists() and not verify_report_seal(proj_dir):
        print("\n🛑 [GUARDIAN BLOCK] تقرير Probe-QC مزوّر!")
        print("السبب: البصمة الرقمية لا تتطابق مع التقرير")
        print("الإجراء: شغّل probe_qc.py مجدداً لإنشاء تقرير أصلي")
        sys.exit(1)
    print("✅ تقرير Probe-QC أصلي")

    # ─────────────────────────────────────────────
    # الفحص 4: موافقة المستخدم موجودة
    # ─────────────────────────────────────────────
    if not approval_file.exists():
        print("\n🛑 [GUARDIAN BLOCK] لا توجد موافقة من المستخدم!")
        print("الإجراء: افتح الاستوديو، راجع الفيديو، ثم أنشئ ملف .studio_approved")
        sys.exit(1)
    print("✅ ملف الموافقة موجود")

    # ─────────────────────────────────────────────
    # الفحص 5: كشف الموافقة المزوّرة (فحص الوقت)
    # ─────────────────────────────────────────────
    approval_mtime = approval_file.stat().st_mtime
    unlock_mtime = unlock_file.stat().st_mtime if unlock_file.exists() else 0
    
    # إذا أُنشئ ملف الموافقة قبل أقل من 5 ثوانٍ من ملف الفتح، فهي مزوّرة
    # (لأن المستخدم يحتاج وقتاً للمعاينة الفعلية)
    time_diff = approval_mtime - unlock_mtime
    
    if time_diff < 10:  # أقل من 10 ثوانٍ بين الفتح والموافقة
        print("\n🛑 [GUARDIAN BLOCK] الموافقة مشبوهة!")
        print(f"السبب: ملف .studio_approved أُنشئ بعد {time_diff:.1f} ثانية فقط من فتح الاستوديو")
        print("الإجراء: يجب أن تعاين الفيديو فعلياً في الاستوديو قبل الموافقة")
        print("         (أعد حذف .studio_approved، راجع الفيديو، ثم أنشئه مجدداً)")
        sys.exit(1)
    
    print(f"✅ الموافقة صحيحة (بعد {time_diff:.1f} ثانية من فتح الاستوديو)")

    # ─────────────────────────────────────────────
    # الفحص 6: Pipeline Guard المتقدم (اختياري)
    # ─────────────────────────────────────────────
    try:
        scripts_dir = Path(__file__).parent.parent / "plugins" / "super-video-maker-plugin" / "scripts"
        if scripts_dir.exists():
            sys.path.insert(0, str(scripts_dir))
            from pipeline_guard import PipelineGuard, GuardViolation
            
            guard = PipelineGuard(project_id)
            
            print("\n🔍 [PipelineGuard] فحوصات متقدمة:")
            
            # فحص اكتمال الجمل
            guard.require_all_sentences_covered()
            print("  ✅ جميع الجمل الصوتية لها مشاهد مقابلة")
            
            # فحص صحة TypeScript
            guard.require_typescript_clean()
            print("  ✅ الكود خالٍ من أخطاء TypeScript")
            
            # فحص تنوع القوالب
            guard.require_motion_valid()
            print("  ✅ تنوع القوالب والـ SFX مقبول")
            
    except ImportError:
        print("\n⚠️ Pipeline Guard غير متاح — تخطي الفحوصات المتقدمة")
    except Exception as e:
        print(f"\n🛑 [GUARDIAN BLOCK] {e}")
        sys.exit(1)

    # ─────────────────────────────────────────────
    # بدء الرندر
    # ─────────────────────────────────────────────
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
    print(f"📊 الحجم: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
