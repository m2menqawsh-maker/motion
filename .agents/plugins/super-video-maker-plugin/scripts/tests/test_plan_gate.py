# -*- coding: utf-8 -*-
import pytest
import os
import sys
from pathlib import Path
import tempfile
import shutil

scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from plan_gate import validate_plan_quality, detect_sequential_repetition


class TestPlanGate:
    def _create_valid_plan(self) -> str:
        """توليد نص خطة نموذجية مستوفية لجميع الشروط"""
        return """# الخطة الرئيسية للمشروع

## الاستشهادات الإلزامية
- motion_taste_citation: "Cinematic, smooth camera tracking with 300ms transitions"
- treatment_citation: "High contrast tech visual style"

#### المشهد 1
- القالب: KineticTitle
- SFX: whoosh_fast.wav
- المؤثر البصري: Zoom in
| الكلمة | البداية | النهاية |
| مرحبا | 0.0s | 0.5s |
| بكم | 0.5s | 1.0s |

#### المشهد 2
- القالب: DeviceMockup
- SFX: digital_click.wav
- المؤثر البصري: Pan right
| الكلمة | البداية | النهاية |
| في | 1.0s | 1.3s |
| عالم | 1.3s | 1.8s |

#### المشهد 3
- القالب: StatCounter
- SFX: chime_success.wav
- المؤثر البصري: Scale up
| الكلمة | البداية | النهاية |
| التقنية | 1.8s | 2.5s |
"""

    def test_valid_plan_acceptance(self):
        """قبول خطة صحيحة مستوفية للشروط"""
        plan = self._create_valid_plan()
        is_valid, errors = validate_plan_quality(plan)
        assert is_valid is True
        assert len(errors) == 0

    def test_padding_detection(self):
        """رفض الحشو <!-- Padding -->"""
        plan = self._create_valid_plan()
        plan_with_padding = plan + "\n<!-- Padding for line count requirements -->"
        is_valid, errors = validate_plan_quality(plan_with_padding)
        assert is_valid is False
        assert any("Padding" in e for e in errors)

    def test_generic_media_rejection(self):
        """رفض العبارات العامة مثل 'خلفية عامة' أو 'أصل 1'"""
        plan = self._create_valid_plan().replace("Zoom in", "خلفية عامة في المنتصف")
        is_valid, errors = validate_plan_quality(plan)
        assert is_valid is False
        assert any("خلفية عامة" in e for e in errors)

    def test_template_diversity_check(self):
        """اشتراط ≥ 3 قوالب مختلفة للمشاريع ذات 3 مشاهد فأكثر"""
        # نكرر نفس القالب في المشاهد الثلاثة
        plan = self._create_valid_plan()
        plan = plan.replace("DeviceMockup", "KineticTitle").replace("StatCounter", "KineticTitle")
        is_valid, errors = validate_plan_quality(plan)
        assert is_valid is False
        assert any("template_diversity" in e.lower() or "قوالب" in e for e in errors)

    def test_sfx_diversity_check(self):
        """اشتراط عدم الإفراط في المؤثرات الصوتية العشوائية داخل نفس المشهد"""
        # إضافة أكثر من 4 ملفات .wav في المشهد الأول
        excessive_sfx = (
            "- SFX: whoosh.wav, pop.wav, click.wav, hit.wav, chime.wav\n"
        )
        plan = self._create_valid_plan().replace("- SFX: whoosh_fast.wav\n", excessive_sfx)
        is_valid, errors = validate_plan_quality(plan)
        assert is_valid is False
        assert any(".wav" in e for e in errors)

    def test_word_timings_required(self):
        """اشتراط وجود جدول كلمات وتوقيتات لكل مشهد"""
        # نزيل جدول الكلمات من المشهد 2
        plan = self._create_valid_plan().replace("| في | 1.0s | 1.3s |\n| عالم | 1.3s | 1.8s |", "")
        plan = plan.replace("| الكلمة | البداية | النهاية |\n", "", 1)  # إزالة رأس الجدول من أحد المشاهد
        is_valid, errors = validate_plan_quality(plan)
        assert is_valid is False
        assert any("جدول كلمات" in e for e in errors)

    def test_citations_required(self):
        """اشتراط وجود الاستشهادات الإلزامية (motion_taste_citation و treatment_citation)"""
        plan = self._create_valid_plan().replace("motion_taste_citation", "unrelated_citation")
        is_valid, errors = validate_plan_quality(plan)
        assert is_valid is False
        assert any("الاستشهادات الإلزامية" in e for e in errors)

    def test_sequential_repetition_detection(self):
        """كشف التكرار المتسلسل للسطور لمنع التحايل وملء الفراغ"""
        repeated_lines = [
            f"- لقطة رقم {i}: حركة سريعة للعنصر" for i in range(1, 10)
        ]
        result = detect_sequential_repetition(repeated_lines)
        assert result["has_repetition"] is True

        # فحص داخل validate_plan_quality
        plan = self._create_valid_plan() + "\n" + "\n".join(repeated_lines)
        is_valid, errors = validate_plan_quality(plan)
        assert is_valid is False
        assert any("حشو متسلسل" in e for e in errors)

    def test_empty_plan_fails(self):
        """رفض الخطة الفارغة تماماً"""
        is_valid, errors = validate_plan_quality("")
        assert is_valid is False
        assert len(errors) > 0

    def test_single_scene_plan_diversity_not_enforced(self):
        """عدم إلزام شرط الـ 3 قوالب للمشاريع ذات المشهد الواحد أو المشهدين"""
        plan_single = """# الخطة
- motion_taste_citation: A
- treatment_citation: B
#### المشهد 1
- القالب: KineticTitle
- SFX: whoosh.wav
| الكلمة | البداية | النهاية |
| كلمة | 0.0s | 1.0s |
"""
        is_valid, errors = validate_plan_quality(plan_single)
        assert is_valid is True
        assert not any("template_diversity" in e.lower() for e in errors)

    def test_scene_sfx_balanced_passes(self):
        """قبول الخطة عندما تكون المؤثرات الصوتية متوازنة (2-3 لكل مشهد)"""
        plan = self._create_valid_plan()
        is_valid, errors = validate_plan_quality(plan)
        assert is_valid is True

    def test_missing_master_plan_file_cli(self):
        """فحص سلوك plan_gate عند غياب ملف master_plan.md"""
        non_existent_proj = "non_existent_proj_xyz"
        import subprocess
        plan_gate_script = scripts_dir / "plan_gate.py"
        res = subprocess.run([sys.executable, str(plan_gate_script), non_existent_proj], capture_output=True, text=True)
        assert res.returncode == 1
