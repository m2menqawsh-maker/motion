#!/usr/bin/env python3
"""
Pipeline Guard — الحارس المركزي لخط الإنتاج
يوفر دوال فحص إجبارية تُستدعى من كل سكريبت أساسي.
الهدف: جعل المخالفات مستحيلة تقنياً، وليس فقط ممنوعة نصياً.

الاستخدام في أي سكريبت:
    from pipeline_guard import PipelineGuard
    guard = PipelineGuard("tech_world")
    guard.require_stage_complete("assets")  # يرمي خطأ إذا لم تكتمل المرحلة
"""

import sys
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class GuardViolation(Exception):
    """استثناء يُرمى عند مخالفة قاعدة من قواعد خط الإنتاج"""
    def __init__(self, rule: str, reason: str, fix: str):
        self.rule = rule
        self.reason = reason
        self.fix = fix
        super().__init__(f"[{rule}] {reason}\n🔧 الإصلاح: {fix}")


class PipelineGuard:
    """الحارس المركزي — كل الفحوصات الإجبارية في مكان واحد"""

    PLUGIN_ROOT = Path(".agents/plugins/super-video-maker-plugin")
    SCRIPTS_DIR = PLUGIN_ROOT / "scripts"

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = Path(f"projects/{project_id}")
        self.build_dir = self.project_dir / "06_build"

        if not self.project_dir.exists():
            raise GuardViolation(
                "PROJECT_NOT_FOUND",
                f"المشروع '{project_id}' غير موجود",
                f"أنشئ المشروع أولاً في projects/{project_id}/"
            )

    # ─────────────────────────────────────────────
    # 1) فحص اكتمال المراحل (تمنع تخطي المراحل)
    # ─────────────────────────────────────────────
    STAGE_FILES = {
        "audio_analysis": "04_timings.json",
        "plan": "01_plan.md",
        "initial_assets": "02_initial_assets.json",
        "blueprint": "05_blueprint.json",
    }

    def require_stage_complete(self, stage: str):
        """يرمي خطأ إذا لم تكتمل المرحلة المطلوبة"""
        if stage not in self.STAGE_FILES:
            raise GuardViolation(
                "UNKNOWN_STAGE",
                f"مرحلة غير معروفة: {stage}",
                f"المراحل المتاحة: {', '.join(self.STAGE_FILES.keys())}"
            )

        required_file = self.project_dir / self.STAGE_FILES[stage]
        if not required_file.exists():
            raise GuardViolation(
                "STAGE_INCOMPLETE",
                f"المرحلة '{stage}' غير مكتملة — الملف {self.STAGE_FILES[stage]} غير موجود",
                f"أكمل المرحلة '{stage}' أولاً قبل المتابعة"
            )

        # فحص إضافي: الملف يجب ألا يكون فارغاً
        if required_file.stat().st_size == 0:
            raise GuardViolation(
                "EMPTY_STAGE_FILE",
                f"ملف المرحلة '{stage}' فارغ",
                "أعد توليد الملف بمحتوى فعلي"
            )

    # ─────────────────────────────────────────────
    # 2) تشغيل سكريبت فحص خارجي (مثل motion_validator)
    # ─────────────────────────────────────────────
    def require_script_pass(self, script_name: str, *args) -> str:
        """يشغل سكريبت فحص ويرمي خطأ إذا فشل"""
        script_path = self.SCRIPTS_DIR / script_name
        if not script_path.exists():
            raise GuardViolation(
                "VALIDATOR_MISSING",
                f"سكريبت الفحص '{script_name}' غير موجود",
                "تأكد من وجود السكريبت في مجلد scripts/"
            )

        cmd = [sys.executable, str(script_path), *map(str, args)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

        if result.returncode != 0:
            raise GuardViolation(
                "VALIDATOR_FAILED",
                f"سكريبت '{script_name}' رفض الملف:\n{result.stdout}\n{result.stderr}",
                "أصلح المخالفات المذكورة أعلاه ثم أعد المحاولة"
            )
        return result.stdout

    # ─────────────────────────────────────────────
    # 3) فحص motion_validator (التنوع + الـ SFX)
    # ─────────────────────────────────────────────
    def require_motion_valid(self):
        """يفحص الـ Blueprint عبر motion_validator.py"""
        blueprint = self.project_dir / "05_blueprint.json"
        if not blueprint.exists():
            raise GuardViolation(
                "NO_BLUEPRINT",
                "لا يوجد 05_blueprint.json",
                "ولّد الـ Blueprint أولاً قبل البناء"
            )
        self.require_script_pass("motion_validator.py", str(blueprint))

    # ─────────────────────────────────────────────
    # 4) فحص code_template_gate (منع الارتجال خارج القوالب)
    # ─────────────────────────────────────────────
    def require_templates_compliant(self):
        """يفحص كل ملفات المشاهد عبر code_template_gate.py"""
        compositions_dir = self.build_dir / "src" / "compositions"
        if not compositions_dir.exists():
            return  # لا يوجد ملفات بعد، لا شيء ليفحص

        scene_files = list(compositions_dir.glob("Scene*.tsx"))
        if not scene_files:
            return

        for scene_file in scene_files:
            self.require_script_pass("code_template_gate.py", str(scene_file))

    # ─────────────────────────────────────────────
    # 5) فحص القفل الميكانيكي (للاستوديو)
    # ─────────────────────────────────────────────
    def require_studio_unlocked(self):
        """يمنع فتح الاستوديو قبل نجاح Probe-QC"""
        unlock_file = self.project_dir / ".studio_unlocked"
        qc_report = self.project_dir / "probe_qc_report.json"

        if not unlock_file.exists():
            # تحقق: هل يوجد تقرير QC ناجح؟
            if qc_report.exists():
                try:
                    report = json.loads(qc_report.read_text(encoding="utf-8"))
                    if report.get("status") == "pass":
                        raise GuardViolation(
                            "UNLOCK_FILE_MISSING",
                            "تقرير QC ناجح لكن ملف .studio_unlocked مفقود",
                            "شغّل probe_qc.py مجدداً لإنشاء ملف الفتح تلقائياً"
                        )
                except (json.JSONDecodeError, KeyError):
                    pass

            raise GuardViolation(
                "STUDIO_LOCKED",
                "الاستوديو مقفل — لم ينجح Probe-QC بعد",
                "شغّل: python scripts/probe_qc.py <project_id> وانتظر نجاحه"
            )

    # ─────────────────────────────────────────────
    # 6) فحص موافقة المستخدم (للرندر)
    # ─────────────────────────────────────────────
    def require_user_approval(self):
        """يمنع الرندر قبل موافقة المستخدم الصريحة"""
        approval_file = self.project_dir / ".studio_approved"

        if not approval_file.exists():
            raise GuardViolation(
                "NO_USER_APPROVAL",
                "ممنوع الرندر — لم تتم الموافقة في الاستوديو",
                "افتح الاستوديو، راجع الفيديو، ثم اطلب من المستخدم إنشاء ملف .studio_approved"
            )

        # فحص: هل الموافقة قديمة أو مزورة آلياً؟
        # نقارن وقت الموافقة بوقت آخر فحص QC (فك القفل)
        unlock_file = self.project_dir / ".studio_unlocked"
        if unlock_file.exists():
            unlock_time = unlock_file.stat().st_mtime
            approval_time = approval_file.stat().st_mtime
            
            # 1. الموافقة تمت قبل الفحص الأخير (موافقة بايتة/قديمة)
            if approval_time <= unlock_time:
                raise GuardViolation(
                    "STALE_APPROVAL",
                    "⚠️ ملف .studio_approved قديم (أُنشئ قبل آخر فحص QC).",
                    "احذف ملف الموافقة القديم، عاين التعديلات الجديدة في الاستوديو، ثم أنشئ ملفاً جديداً."
                )
                
            # 2. الموافقة تمت بسرعة خيالية (أقل من 15 ثانية) - تزوير من الوكيل!
            if (approval_time - unlock_time) < 15:
                raise GuardViolation(
                    "FORGED_APPROVAL",
                    "⚠️ تمت الموافقة بسرعة غير بشرية (أقل من 15 ثانية من الفحص) — تزوير آلي مكتشف!",
                    "المعاينة البشرية تستغرق وقتاً. راجع الفيديو فعلياً في الاستوديو قبل إنشاء ملف الموافقة."
                )

    # ─────────────────────────────────────────────
    # 7) منع التزوير: التحقق من سلامة التقارير (Checksum)
    # ─────────────────────────────────────────────
    @staticmethod
    def seal_report(report_path: Path):
        """يختم تقريراً بصمة رقمية بعد إنشائه — يمنع التعديل اليدوي"""
        if not report_path.exists():
            return
        content = report_path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        seal_file = report_path.with_suffix(report_path.suffix + ".seal")
        seal_file.write_text(checksum, encoding="utf-8")

    @staticmethod
    def verify_report_seal(report_path: Path) -> bool:
        """يتحقق من أن التقرير لم يُعدّل يدوياً بعد ختمه"""
        seal_file = report_path.with_suffix(report_path.suffix + ".seal")
        if not seal_file.exists():
            return True  # لا يوجد ختم، لا يمكن التحقق (تقبل لأول مرة)
        if not report_path.exists():
            return False

        expected = seal_file.read_text(encoding="utf-8").strip()
        actual = hashlib.sha256(report_path.read_bytes()).hexdigest()
        return expected == actual

    def require_probe_qc_genuine(self):
        """يتحقق أن تقرير Probe-QC أصلي ولم يُزوّر يدوياً"""
        qc_report = self.project_dir / "probe_qc_report.json"
        if not qc_report.exists():
            raise GuardViolation(
                "NO_QC_REPORT",
                "لا يوجد تقرير Probe-QC",
                "شغّل: python scripts/probe_qc.py <project_id>"
            )

        if not self.verify_report_seal(qc_report):
            raise GuardViolation(
                "REPORT_TAMPERED",
                "⚠️ تقرير Probe-QC تم تعديله يدوياً بعد إنشائه! (البصمة الرقمية لا تتطابق)",
                "أعد تشغيل: python scripts/probe_qc.py <project_id> — التزوير ممنوع"
            )

    # ─────────────────────────────────────────────
    # 8) فحص بوابة الميديا (منع النسخ اليدوي)
    # ─────────────────────────────────────────────
    def require_media_in_build(self):
        """يتحقق أن الميديا في 06_build جاءت عبر materialize وليس نسخاً يدوياً"""
        media_manifest = self.build_dir / "media_map.json"
        media_dir = self.build_dir / "public" / "media"

        if media_dir.exists() and not media_manifest.exists():
            raise GuardViolation(
                "MANUAL_MEDIA_COPY",
                "يوجد ميديا في 06_build بدون media_map.json — هذا يعني نسخاً يدوياً",
                "استخدم: python scripts/materialize_project.py <project_id> فقط"
            )

    # ─────────────────────────────────────────────
    # 9) حراس الجودة الإبداعية (Creative Quality Guards)
    # ─────────────────────────────────────────────
    def require_all_sentences_covered(self):
        """يتأكد أن كل جملة في الصوت لها مشهد مقابل لمنع (Creative Amnesia)"""
        timings_file = self.project_dir / "04_timings.json"
        if not timings_file.exists():
            return
            
        try:
            import json
            timings = json.loads(timings_file.read_text(encoding="utf-8"))
            total_sentences = len(timings.get("sentences", []))
            
            scenes_dir = self.build_dir / "src" / "compositions"
            if not scenes_dir.exists():
                return
                
            built_scenes = len(list(scenes_dir.glob("Scene*.tsx")))
            
            if built_scenes < total_sentences:
                raise GuardViolation(
                    "MISSING_SCENES",
                    f"⚠️ ناقص مشاهد! الصوت يحتوي على {total_sentences} جمل، لكن تم بناء {built_scenes} مشهد فقط.",
                    "راجع 04_timings.json وابنِ المشاهد المتبقية لتغطي كل الجمل الصوتية."
                )
        except (json.JSONDecodeError, KeyError):
            pass

    def require_typescript_clean(self):
        """يمنع المضي قدماً إذا كان الكود يحتوي على أخطاء TypeScript (منع Sloppy Coding)"""
        import subprocess
        import os
        
        if not self.build_dir.exists():
            return
            
        print("🔍 [PipelineGuard] فحص الكود (TypeScript Check)...")
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=str(self.build_dir),
            capture_output=True,
            text=True,
            shell=(os.name == "nt")
        )
        
        if result.returncode != 0:
            raise GuardViolation(
                "TYPESCRIPT_ERRORS",
                f"❌ الكود يحتوي على أخطاء TypeScript لا يمكن تجاهلها:\n{result.stdout[:500]}...",
                "أصلح أخطاء الـ imports والـ types قبل فتح الاستوديو أو الرندر."
            )

    def require_plan_execution_match(self):
        """يقارن بين خطة المشهد والكود المكتوب لمنع (Hallucinated Execution)"""
        blueprint_file = self.project_dir / "05_blueprint.json"
        if not blueprint_file.exists():
            return
            
        try:
            import json
            bp = json.loads(blueprint_file.read_text(encoding="utf-8"))
            scenes_dir = self.build_dir / "src" / "compositions"
            
            for i, scene in enumerate(bp.get("timeline", [])):
                scene_idx = i + 1
                scene_file = scenes_dir / f"Scene{scene_idx}.tsx"
                if not scene_file.exists():
                    continue
                    
                code = scene_file.read_text(encoding="utf-8").lower()
                for el in scene.get("elements", []):
                    template = el.get("template", "").lower()
                    if template and template not in code:
                        raise GuardViolation(
                            "PLAN_MISMATCH",
                            f"⚠️ المشهد رقم {scene_idx} يوعد باستخدام قالب '{el.get('template')}' لكنه غير موجود في الكود!",
                            "التزم بالخطة المكتوبة أو عدّل الخطة لتطابق ما كتبته."
                        )
        except (json.JSONDecodeError, KeyError):
            pass

    # ─────────────────────────────────────────────
    # 10) دالة شاملة: فحص قبل البناء (تُستدعى من materialize)
    # ─────────────────────────────────────────────
    def pre_build_check(self):
        """فحص شامل قبل أي عملية بناء — يجمع كل الفحوصات"""
        print("🔍 [PipelineGuard] بدء الفحوصات الإجبارية قبل البناء...")

        checks = [
            ("اكتمال تحليل الصوت", lambda: self.require_stage_complete("audio_analysis")),
            ("اكتمال الخطة", lambda: self.require_stage_complete("plan")),
            ("صحة الـ Blueprint", lambda: self.require_stage_complete("blueprint")),
            ("التنوع والـ SFX", self.require_motion_valid),
            ("الكود المخصص", self.require_custom_code_valid),
        ]

        for name, check in checks:
            try:
                check()
                print(f"  ✅ {name}")
            except GuardViolation as e:
                print(f"\n🛑 [PipelineGuard] تم إيقاف البناء!\n{e}\n")
                raise

        print("✅ [PipelineGuard] جميع الفحوصات نجحت — يمكن البدء بالبناء.\n")

    def require_custom_code_valid(self):
        """يفحص الكود المخصص عبر custom_code_validator.py"""
        custom_dir = self.project_dir / "custom"
        if not custom_dir.exists():
            return  # لا يوجد كود مخصص

        self.require_script_pass("custom_code_validator.py", self.project_id)



# ─────────────────────────────────────────────
# دالة مساعدة للاستخدام السريع من سطر الأوامر
# ─────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print("الاستخدام: python pipeline_guard.py <project_id> <check_name>")
        print("الفحوصات المتاحة: pre_build, studio, render, probe_genuine")
        sys.exit(1)

    project_id = sys.argv[1]
    check_name = sys.argv[2]

    guard = PipelineGuard(project_id)

    try:
        if check_name == "pre_build":
            guard.pre_build_check()
        elif check_name == "studio":
            guard.require_probe_qc_genuine()
            guard.require_studio_unlocked()
            guard.require_all_sentences_covered()
            guard.require_typescript_clean()
            guard.require_plan_execution_match()
            print("✅ الاستوديو مسموح")
        elif check_name == "render":
            guard.require_probe_qc_genuine()
            guard.require_studio_unlocked()
            guard.require_user_approval()
            guard.require_all_sentences_covered()
            guard.require_typescript_clean()
            guard.require_plan_execution_match()
            print("✅ الرندر مسموح")
        elif check_name == "probe_genuine":
            guard.require_probe_qc_genuine()
            print("✅ التقرير أصلي")
        else:
            print(f"فحص غير معروف: {check_name}")
            sys.exit(1)
    except GuardViolation as e:
        print(f"\n🛑 {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
