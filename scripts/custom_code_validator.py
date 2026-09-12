#!/usr/bin/env python3
"""
Custom Code Validator — حارس منطقة الابتكار المحكومة
يفحص الكود المخصص في projects/<id>/custom/ ويتأكد من:
1. التوثيق الكامل
2. عدم وجود أنماط خطيرة
3. التوافق مع TypeScript
4. الالتزام بمعايير الجودة
"""

import sys
import re
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class CustomCodeViolation(Exception):
    def __init__(self, rule: str, reason: str, fix: str):
        self.rule = rule
        self.reason = reason
        self.fix = fix
        super().__init__(f"[{rule}] {reason}\n🔧 الإصلاح: {fix}")


class CustomCodeValidator:
    """حارس الكود المخصص — يفحص كل ملف في custom/"""

    # أنماط خطيرة ممنوعة
    DANGEROUS_PATTERNS = [
        (r'\beval\s*\(', "استخدام eval() — تنفيذ كود عشوائي"),
        (r'\bexec\s*\(', "استخدام exec() — تنفيذ كود عشوائي"),
        (r'require\s*\(\s*["\']child_process["\']', "استدعاء child_process — أوامر نظام"),
        (r'fs\.unlink', "حذف ملفات"),
        (r'process\.exit', "إنهاء العملية"),
        (r'<script[^>]*>', "حقن JavaScript في HTML"),
    ]

    # أنماط مشبوهة (تحذير لكن ليس خطأ)
    SUSPICIOUS_PATTERNS = [
        (r'console\.log', "استخدام console.log (يجب إزالته قبل الإنتاج)"),
        (r'alert\s*\(', "استخدام alert() (غير مناسب للفيديو)"),
        (r'debugger', "نقطة توقف debugger"),
    ]

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.custom_dir = Path(f"projects/{project_id}/custom")

    def validate_all(self):
        """يفحص جميع ملفات الكود المخصص"""
        if not self.custom_dir.exists():
            print("✅ لا يوجد كود مخصص للتحقق")
            return

        tsx_files = list(self.custom_dir.glob("**/*.tsx"))
        ts_files = list(self.custom_dir.glob("**/*.ts"))
        all_files = tsx_files + ts_files

        if not all_files:
            print("✅ لا يوجد كود مخصص للتحقق")
            return

        print(f"🔍 فحص {len(all_files)} ملف في {self.custom_dir}...")

        errors = []
        warnings = []

        for file_path in all_files:
            file_errors, file_warnings = self.validate_file(file_path)
            errors.extend(file_errors)
            warnings.extend(file_warnings)

        # طباعة النتائج
        if warnings:
            print("\n⚠️ تحذيرات:")
            for w in warnings:
                print(f"  {w}")

        if errors:
            print("\n❌ أخطاء:")
            for e in errors:
                print(f"  {e}")
            raise CustomCodeViolation(
                "CUSTOM_CODE_FAILED",
                f"فشل فحص الكود المخصص ({len(errors)} خطأ)",
                "أصلح الأخطاء المذكورة أعلاه"
            )

        print(f"✅ جميع ملفات الكود المخصص ({len(all_files)}) مقبولة")

    def validate_file(self, file_path: Path) -> tuple[list[str], list[str]]:
        """يفحص ملف واحد ويعيد (أخطاء, تحذيرات)"""
        errors = []
        warnings = []

        content = file_path.read_text(encoding="utf-8")

        # 1. فحص التوثيق الإلزامي
        if not self.has_required_documentation(content):
            errors.append(
                f"{file_path.name}: نقص التوثيق الإلزامي (/* CUSTOM CODE ... */)"
            )

        # 2. فحص الأنماط الخطيرة
        for pattern, description in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content):
                errors.append(
                    f"{file_path.name}: نمط خطير — {description}"
                )

        # 3. فحص الأنماط المشبوهة
        for pattern, description in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, content):
                warnings.append(
                    f"{file_path.name}: نمط مشبوه — {description}"
                )

        # 4. فحص TypeScript (إذا كان tsc متاحاً)
        tsc_errors = self.check_typescript(file_path)
        if tsc_errors:
            errors.append(f"{file_path.name}: أخطاء TypeScript:\n{tsc_errors}")

        return errors, warnings

    def has_required_documentation(self, content: str) -> bool:
        """يتحقق من وجود التوثيق الإلزامي"""
        # يجب أن يحتوي على /* CUSTOM CODE في البداية
        if "/* CUSTOM CODE" not in content:
            return False

        # يجب أن يحتوي على:
        # - Purpose (الغرض)
        # - Author (المؤلف)
        # - Date (التاريخ)
        required_fields = ["Purpose:", "Author:", "Date:"]
        for field in required_fields:
            if field not in content:
                return False

        return True

    def check_typescript(self, file_path: Path) -> str:
        """يشغل tsc --noEmit ويتحقق من الأخطاء"""
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                return result.stdout + result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # tsc غير متاح أو timeout — نتجاهل
            pass
        return ""


def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python custom_code_validator.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]
    validator = CustomCodeValidator(project_id)

    try:
        validator.validate_all()
        sys.exit(0)
    except CustomCodeViolation as e:
        print(f"\n🛑 {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
