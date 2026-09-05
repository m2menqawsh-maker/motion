# -*- coding: utf-8 -*-
import pytest
import os
import sys
import json
import hashlib
from pathlib import Path
import tempfile
import shutil

scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from code_template_gate import run_gate


class TestCodeTemplateGate:
    def setup_method(self):
        """إعداد بيئة اختبار معزولة"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.proj_dir = self.test_dir / "projects" / "test_proj"
        self.comps_dir = self.proj_dir / "06_build" / "src" / "compositions"
        self.comps_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def _create_generated_scene(self, filename: str, code_body: str) -> Path:
        gen_dir = self.comps_dir / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        file_path = gen_dir / filename
        content_hash = hashlib.md5(code_body.encode("utf-8")).hexdigest()
        full_content = f"// GENERATED — DO NOT EDIT\n// Hash: {content_hash}\n{code_body}"
        file_path.write_text(full_content, encoding="utf-8")
        return file_path

    def test_valid_template_import(self):
        """قبول ملف مشهد يستورد بشكل صحيح من @templates"""
        code = (
            "import React from 'react';\n"
            "import { KineticText } from '@templates/KineticText';\n"
            "export const Scene1 = () => <KineticText />;\n"
        )
        self._create_generated_scene("Scene1.tsx", code)

        # يجب أن يجتاز الفحص دون استدعاء sys.exit(1)
        run_gate(str(self.proj_dir))

    def test_invalid_spring_usage(self, capsys):
        """رفض استخدام spring() المباشر في ملف المشهد"""
        code = (
            "import React from 'react';\n"
            "import { KineticText } from '@templates/KineticText';\n"
            "const val = spring({ frame: 1 });\n"
            "export const Scene1 = () => <div />;\n"
        )
        self._create_generated_scene("Scene1.tsx", code)

        with pytest.raises(SystemExit) as exc:
            run_gate(str(self.proj_dir))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "spring(" in captured.out

    def test_invalid_interpolate_usage(self, capsys):
        """رفض استخدام interpolate() المباشر في ملف المشهد"""
        code = (
            "import React from 'react';\n"
            "import { KineticText } from '@templates/KineticText';\n"
            "const val = interpolate(10, [0, 100], [0, 1]);\n"
            "export const Scene1 = () => <div />;\n"
        )
        self._create_generated_scene("Scene1.tsx", code)

        with pytest.raises(SystemExit) as exc:
            run_gate(str(self.proj_dir))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "interpolate(" in captured.out

    def test_md5_header_verification(self, capsys):
        """التحقق من بصمة MD5 وكشف التعديل اليدوي"""
        gen_dir = self.comps_dir / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        file_path = gen_dir / "Scene1.tsx"

        # كتابة ترويسة بها هاش غير متطابق
        invalid_content = (
            "// GENERATED — DO NOT EDIT\n"
            "// Hash: 1234567890abcdef1234567890abcdef\n"
            "import React from 'react';\n"
            "import { KineticText } from '@templates/KineticText';\n"
            "export const Scene1 = () => <KineticText />;\n"
        )
        file_path.write_text(invalid_content, encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            run_gate(str(self.proj_dir))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "Hash mismatch" in captured.out

    def test_custom_template_with_approval(self):
        """قبول الكود المخصص داخل custom/ والموثق بـ /* CUSTOM CODE ... */"""
        custom_dir = self.comps_dir / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)
        file_path = custom_dir / "CustomScene.tsx"

        code = (
            "/* CUSTOM CODE — Approved by User for Scene 4 */\n"
            "import React from 'react';\n"
            "export const CustomScene = () => <div>Custom</div>;\n"
        )
        file_path.write_text(code, encoding="utf-8")

        # يجب أن يجتاز الفحص
        run_gate(str(self.proj_dir))

    def test_custom_template_without_approval(self, capsys):
        """رفض الكود المخصص داخل custom/ إذا لم يحتوي على توثيق الاعتماد"""
        custom_dir = self.comps_dir / "custom"
        custom_dir.mkdir(parents=True, exist_ok=True)
        file_path = custom_dir / "CustomScene.tsx"

        code = (
            "import React from 'react';\n"
            "export const CustomScene = () => <div>Custom without docs</div>;\n"
        )
        file_path.write_text(code, encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            run_gate(str(self.proj_dir))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "CUSTOM CODE" in captured.out

    def test_generated_folder_acceptance(self):
        """قبول ملفات المشاهد عندما تكون داخل compositions/generated/"""
        code = (
            "import React from 'react';\n"
            "import { KineticText } from '@templates/KineticText';\n"
            "export const Scene2 = () => <KineticText />;\n"
        )
        self._create_generated_scene("Scene2.tsx", code)
        run_gate(str(self.proj_dir))

    def test_root_compositions_rejection(self, capsys):
        """رفض ملفات المشاهد المتواجدة في جذر compositions/ مباشرة بدون مجلد generated/"""
        file_path = self.comps_dir / "Scene1.tsx"
        code = (
            "import React from 'react';\n"
            "import { KineticText } from '@templates/KineticText';\n"
            "export const Scene1 = () => <KineticText />;\n"
        )
        file_path.write_text(code, encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            run_gate(str(self.proj_dir))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "خارج مجلد generated/" in captured.out

    def test_forbidden_directory_snapcn(self, capsys):
        """رفض المجلدات المحلية المحظورة مثل snap-cn داخل 06_build/src"""
        forbidden_dir = self.proj_dir / "06_build" / "src" / "components" / "snap-cn"
        forbidden_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(SystemExit) as exc:
            run_gate(str(self.proj_dir))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "مجلد components/snap-cn محلي" in captured.out

    def test_missing_generated_header(self, capsys):
        """رفض الملفات داخل generated/ إذا كانت تفتقد لترويسة GENERATED"""
        gen_dir = self.comps_dir / "generated"
        gen_dir.mkdir(parents=True, exist_ok=True)
        (gen_dir / "Scene1.tsx").write_text("export const Scene1 = () => null;\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc:
            run_gate(str(self.proj_dir))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "مفقود ترويسة GENERATED" in captured.out

    def test_blueprint_template_not_imported(self, capsys):
        """رفض إذا كان قالب الـ Blueprint غير مستورد في أي ملف مشهد"""
        bp_file = self.proj_dir / "05_blueprint.json"
        bp_file.write_text(json.dumps({
            "timeline": [{"elements": [{"kind": "template", "template": "MissingInCodeTemplate"}]}]
        }), encoding="utf-8")

        code = (
            "import React from 'react';\n"
            "import { KineticText } from '@templates/KineticText';\n"
            "export const Scene1 = () => <KineticText />;\n"
        )
        self._create_generated_scene("Scene1.tsx", code)

        with pytest.raises(SystemExit) as exc:
            run_gate(str(self.proj_dir))
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "MissingInCodeTemplate" in captured.out

    def test_scene_imports_more_than_three_templates_warns(self, capsys):
        """إصدار تحذير (WARN) عندما يستورد المشهد أكثر من 3 قوالب"""
        code = (
            "import React from 'react';\n"
            "import { T1 } from '@templates/T1';\n"
            "import { T2 } from '@templates/T2';\n"
            "import { T3 } from '@templates/T3';\n"
            "import { T4 } from '@templates/T4';\n"
            "export const Scene1 = () => <div />;\n"
        )
        self._create_generated_scene("Scene1.tsx", code)
        run_gate(str(self.proj_dir))
        captured = capsys.readouterr()
        assert "WARN: مشهد يستورد أكثر من 3 قوالب" in captured.out
