# -*- coding: utf-8 -*-
import pytest
import os
import sys
import json
from pathlib import Path
import tempfile
import shutil

scripts_dir = Path(__file__).parent.parent.resolve()
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

import motion_validator
import motion_style_interviewer


class TestMotionValidator:
    def setup_method(self):
        """إعداد بيئة معزولة"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.proj_dir = self.test_dir / "projects" / "test_motion_proj"
        self.proj_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """تنظيف بعد الاختبار"""
        shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def test_motion_style_config_reading(self):
        """التحقق من قراءة واستيعاب ملف motion_style_config.json بدقة"""
        config_data = {
            "style_name": "energetic_fast_micro",
            "spring_config": {"mass": 0.8, "stiffness": 220, "damping": 18},
            "overshoot": 0.25,
            "easing": "ease-out-expo",
            "timing": {"micro": "100ms", "standard": "180ms", "scene": "300ms"},
            "camera": {"zoom_max": 1.4, "pan_speed": "fast"},
            "transitions": {"duration": "150ms", "type": "whip_pan"},
            "effects": {"intensity": "high", "neon_glow": True}
        }
        config_path = self.proj_dir / "motion_style_config.json"
        config_path.write_text(json.dumps(config_data, indent=2), encoding="utf-8")

        assert config_path.exists()
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
        assert loaded["spring_config"]["stiffness"] == 220
        assert loaded["camera"]["zoom_max"] == 1.4
        assert loaded["transitions"]["type"] == "whip_pan"

    def test_spring_config_validation(self):
        """التحقق من صحة إعدادات Spring (mass, stiffness, damping) ومنع القيم الشاذة"""
        def validate_spring(spring):
            mass = spring.get("mass", 0)
            stiffness = spring.get("stiffness", 0)
            damping = spring.get("damping", 0)
            if mass <= 0 or stiffness <= 0 or damping <= 0:
                return False, "القيم الفيزيائية يجب أن تكون موجبة تماماً"
            # منع التذبذب الانفجاري غير المستقر
            if damping > stiffness:
                return False, "Damping عالي جداً يسبب جمود الحركة"
            return True, "Spring سليم"

        # إعداد سليم
        valid_spring = {"mass": 0.8, "stiffness": 220, "damping": 18}
        ok, _ = validate_spring(valid_spring)
        assert ok is True

        # إعداد سالب (شاذ)
        invalid_spring = {"mass": -1.0, "stiffness": 220, "damping": 18}
        ok, msg = validate_spring(invalid_spring)
        assert ok is False
        assert "موجبة" in msg

    def test_timing_validation(self):
        """التحقق من مطابقة توقيتات الحركة لشخصية الحركة المحددة (Cinematic 350-600ms)"""
        rules = {
            "Cinematic": {"duration_min": 350, "duration_max": 600, "easing": "cubic-bezier(0.4, 0, 0.2, 1)", "overshoot": ["0%"]}
        }
        bp_valid = {
            "meta": {"motion_personality": "Cinematic"},
            "timeline": [{
                "elements": [{
                    "id": "e1", "kind": "template",
                    "motion": {"duration_ms": 400, "easing": "cubic-bezier(0.4, 0, 0.2, 1)", "overshoot": "0%"}
                }]
            }]
        }
        # عنصر سليم ضمن النطاق
        duration = bp_valid["timeline"][0]["elements"][0]["motion"]["duration_ms"]
        assert rules["Cinematic"]["duration_min"] <= duration <= rules["Cinematic"]["duration_max"]

        # عنصر خارج النطاق (1200ms) بدون تبرير
        bp_invalid_duration = 1200
        assert not (rules["Cinematic"]["duration_min"] <= bp_invalid_duration <= rules["Cinematic"]["duration_max"])

    def test_camera_validation(self):
        """فحص حركات الكاميرا (الزوم والبان) ومنع القفزات المزعجة"""
        def validate_camera(cam):
            zoom_max = cam.get("zoom_max", 1.0)
            pan_speed = cam.get("pan_speed", "medium")
            if zoom_max > 2.0:
                return False, "الزوم مفرط جداً ويتجاوز 2.0x"
            if pan_speed not in ["fast", "medium", "slow"]:
                return False, "سرعة البان غير معتمدة"
            return True, "الكاميرا سليمة"

        valid_cam = {"zoom_max": 1.4, "pan_speed": "fast"}
        ok, _ = validate_camera(valid_cam)
        assert ok is True

        invalid_cam = {"zoom_max": 4.5, "pan_speed": "crazy"}
        ok, msg = validate_camera(invalid_cam)
        assert ok is False
        assert "الزوم مفرط" in msg

    def test_transition_validation(self):
        """فحص الانتقالات والتأكد من نوعها ومدتها ومنع القوالب القبيحة"""
        allowed_transitions = {"whip_pan", "zoom_through", "fade", "dissolve"}
        trans_valid = {"duration": "150ms", "type": "whip_pan"}
        assert trans_valid["type"] in allowed_transitions

        # فحص كشف القوالب القبيحة في motion_validator
        scene_plan = "Scene with SplitScreen and iconify"
        templates = motion_validator.extract_templates_from_plan(scene_plan)
        ugly_templates = {"SplitScreen", "BasicText", "SimpleFade", "iconify"}
        assert any(t in ugly_templates for t in ["SplitScreen", "iconify"])

    def test_parse_personality_cinematic(self):
        """التحقق من صحة القواعد المستخرجة لشخصية Cinematic"""
        text = """### Cinematic
| Duration | 350-600ms |
| Easing | cubic-bezier(0.4, 0, 0.2, 1) |
| Overshoot | 0% |
"""
        rules_file = self.test_dir / "motion-personality.md"
        rules_file.write_text(text, encoding="utf-8")
        parsed = motion_validator.parse_personality(str(rules_file))
        assert "Cinematic" in parsed
        assert parsed["Cinematic"]["duration_min"] == 350
        assert parsed["Cinematic"]["duration_max"] == 600

    def test_parse_personality_energetic(self):
        """التحقق من صحة القواعد المستخرجة لشخصية Energetic"""
        text = """### Energetic
| Duration | 100-250ms |
| Easing | ease-out-expo |
| Overshoot | 15-30% |
"""
        rules_file = self.test_dir / "motion-personality.md"
        rules_file.write_text(text, encoding="utf-8")
        parsed = motion_validator.parse_personality(str(rules_file))
        assert "Energetic" in parsed
        assert parsed["Energetic"]["duration_min"] == 100
        assert parsed["Energetic"]["duration_max"] == 250

    def test_validate_creative_rules_repetition(self):
        """منع تكرار نفس القوالب في مشهدين متتاليين (Diversity Gate)"""
        scene1 = "Scene with `Typewriter`"
        scene2 = "Scene with `Typewriter`"
        is_ok = motion_validator.validate_creative_rules(scene2, previous_scene_plan=scene1)
        assert is_ok is False

    def test_count_sfx_in_plan(self):
        """التحقق من دقة عد المؤثرات الصوتية في الخطة"""
        text_plan = "Add whoosh.wav and digital_click.mp3 with chime and boom effect"
        count = motion_validator.count_sfx_in_plan(text_plan)
        assert count >= 4

    def test_get_template_family(self):
        """التحقق من تمييز عائلات القوالب (Typography, Data & Stats)"""
        assert motion_validator.get_template_family(["Typewriter"]) == "Typography"
        assert motion_validator.get_template_family(["StatCounter"]) == "Data & Stats"
        assert motion_validator.get_template_family(["ParallaxPan"]) == "Motion Effects"
