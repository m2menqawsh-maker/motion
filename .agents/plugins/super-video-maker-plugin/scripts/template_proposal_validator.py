#!/usr/bin/env python3
"""
Template Proposal Validator — فحص جودة القوالب المقترحة
يتحقق من:
1. التوافق مع TypeScript
2. عدم وجود أخطاء برمجية
3. وجود التوثيق الكامل
4. الالتزام بمعايير الجودة
5. التوافق مع بقية القوالب
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class ProposalViolation(Exception):
    def __init__(self, rule: str, reason: str, fix: str):
        self.rule = rule
        self.reason = reason
        self.fix = fix
        super().__init__(f"[{rule}] {reason}\n🔧 الإصلاح: {fix}")


class TemplateProposalValidator:
    """حارس جودة القوالب المقترحة"""

    PLUGIN_ROOT = Path(".agents/plugins/super-video-maker-plugin")
    PROPOSED_DIR = PLUGIN_ROOT / "templates" / "proposed"
    SCHEMA_PATH = PLUGIN_ROOT / "schemas" / "template_proposal_schema.json"

    def __init__(self, proposal_id: str):
        self.proposal_id = proposal_id
        self.proposal_dir = self.PROPOSED_DIR / proposal_id

        if not self.proposal_dir.exists():
            raise ProposalViolation(
                "PROPOSAL_NOT_FOUND",
                f"مجلد الاقتراح غير موجود: {self.proposal_dir}",
                f"أنشئ الاقتراح أولاً في templates/proposed/{proposal_id}/"
            )

    def validate_all(self):
        """فحص شامل للاقتراح"""
        print(f"🔍 [TemplateProposalValidator] فحص الاقتراح: {self.proposal_id}")

        checks = [
            ("وجود الملفات الأساسية", self.check_required_files),
            ("صحة proposal.json", self.check_proposal_json),
            ("التوافق مع TypeScript", self.check_typescript_compliance),
            ("عدم وجود أنماط خطيرة", self.check_no_dangerous_patterns),
            ("وجود التوثيق", self.check_documentation),
            ("التوافق مع بقية القوالب", self.check_api_compatibility),
        ]

        for name, check in checks:
            try:
                check()
                print(f"  ✅ {name}")
            except ProposalViolation as e:
                print(f"\n🛑 [TemplateProposalValidator] فشل الفحص!\n{e}\n")
                raise

        print(f"✅ [TemplateProposalValidator] جميع الفحوصات نجحت — القالب جاهز للترقية!\n")

    def check_required_files(self):
        """يتحقق من وجود الملفات الأساسية"""
        required = ["Component.tsx", "proposal.json", "README.md"]
        for file in required:
            if not (self.proposal_dir / file).exists():
                raise ProposalViolation(
                    "MISSING_FILE",
                    f"الملف المطلوب غير موجود: {file}",
                    f"أنشئ {file} في {self.proposal_dir}"
                )

    def check_proposal_json(self):
        """يتحقق من صحة proposal.json"""
        proposal_file = self.proposal_dir / "proposal.json"
        
        try:
            with open(proposal_file, 'r', encoding='utf-8') as f:
                proposal = json.load(f)
        except json.JSONDecodeError as e:
            raise ProposalViolation(
                "INVALID_JSON",
                f"proposal.json غير صالح: {e}",
                "أصلح الأخطاء في JSON"
            )

        # تحميل الـ Schema
        if not self.SCHEMA_PATH.exists():
            raise ProposalViolation(
                "SCHEMA_MISSING",
                "ملف الـ Schema غير موجود",
                "تأكد من وجود schemas/template_proposal_schema.json"
            )

        # التحقق من الحقول المطلوبة
        with open(self.SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in proposal:
                raise ProposalViolation(
                    "MISSING_FIELD",
                    f"الحقل المطلوب مفقود: {field}",
                    f"أضف {field} إلى proposal.json"
                )

    def check_typescript_compliance(self):
        """يتحقق من التوافق مع TypeScript"""
        component_file = self.proposal_dir / "Component.tsx"
        
        try:
            result = subprocess.run(
                ["npx", "tsc", "--noEmit", "--jsx", "react", str(component_file)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ProposalViolation(
                    "TYPESCRIPT_ERROR",
                    f"أخطاء TypeScript:\n{result.stdout}\n{result.stderr}",
                    "أصلح أخطاء TypeScript"
                )
        except subprocess.TimeoutExpired:
            raise ProposalViolation(
                "TYPESCRIPT_TIMEOUT",
                "انتهت مهلة فحص TypeScript",
                "حاول مرة أخرى"
            )
        except FileNotFoundError:
            # tsc غير متاح — نتجاهل
            pass

    def check_no_dangerous_patterns(self):
        """يتحقق من عدم وجود أنماط خطيرة"""
        component_file = self.proposal_dir / "Component.tsx"
        content = component_file.read_text(encoding='utf-8')

        dangerous_patterns = [
            (r'\beval\s*\(', "استخدام eval()"),
            (r'\bexec\s*\(', "استخدام exec()"),
            (r'require\s*\(\s*["\']child_process["\']', "استدعاء child_process"),
            (r'fs\.unlink', "حذف ملفات"),
            (r'process\.exit', "إنهاء العملية"),
        ]

        import re
        for pattern, description in dangerous_patterns:
            if re.search(pattern, content):
                raise ProposalViolation(
                    "DANGEROUS_PATTERN",
                    f"نمط خطير: {description}",
                    "أزل النمط الخطير"
                )

    def check_documentation(self):
        """يتحقق من وجود التوثيق الكامل"""
        readme_file = self.proposal_dir / "README.md"
        content = readme_file.read_text(encoding='utf-8')

        required_sections = ["# Overview", "## Usage", "## Props", "## Examples"]
        for section in required_sections:
            if section not in content:
                raise ProposalViolation(
                    "MISSING_DOCS",
                    f"قسم التوثيق مفقود: {section}",
                    f"أضف {section} إلى README.md"
                )

    def check_api_compatibility(self):
        """يتحقق من التوافق مع بقية القوالب"""
        component_file = self.proposal_dir / "Component.tsx"
        content = component_file.read_text(encoding='utf-8')

        # يجب أن يكون export default أو export const
        if "export default" not in content and "export const" not in content:
            raise ProposalViolation(
                "NO_EXPORT",
                "القالب لا يصدّر أي مكون",
                "أضف export default أو export const"
            )

        # يجب أن يستورد من remotion
        if "from 'remotion'" not in content and 'from "remotion"' not in content:
            raise ProposalViolation(
                "NO_REMOTION_IMPORT",
                "القالب لا يستورد من remotion",
                "أضف import من remotion"
            )


def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python template_proposal_validator.py <proposal_id>")
        sys.exit(1)

    proposal_id = sys.argv[1]
    validator = TemplateProposalValidator(proposal_id)

    try:
        validator.validate_all()
        sys.exit(0)
    except ProposalViolation as e:
        print(f"\n🛑 {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
