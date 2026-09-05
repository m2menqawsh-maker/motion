#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
from pathlib import Path
from collections import Counter

def detect_sequential_repetition(lines: list) -> dict:
    """يكشف التكرار المتسلسل للسطور (حشو من نوع جديد)"""
    
    # تجاهل السطور الفارغة وخطوط الفصل وعناوين اللقطات
    import re
    content_lines = [l.strip() for l in lines if l.strip() and not re.match(r'^[-_*]{3,}$', l.strip()) and not l.strip().startswith('**اللقطة')]
    
    # إزالة الأرقام المتسلسلة من السطور للمقارنة
    def normalize_line(line: str) -> str:
        """يزيل الأرقام المتسلسلة لمقارنة المحتوى الفعلي"""
        import re
        # إزالة الأرقام في بداية السطر أو داخله
        normalized = re.sub(r'\d+', 'N', line)
        # إزالة الشرطات والنقاط في البداية
        normalized = re.sub(r'^[-*•\s]+', '', normalized)
        return normalized.strip()
    
    # حساب التكرار
    normalized = [normalize_line(l) for l in content_lines]
    counts = Counter(normalized)
    
    # أي سطر مكرر أكثر من 5 مرات = حشو
    repeated = {line: count for line, count in counts.items() if count > 5}
    
    return {
        "has_repetition": len(repeated) > 0,
        "repeated_lines": repeated,
        "total_repeated": sum(repeated.values())
    }


def validate_plan_quality(plan_content: str) -> dict:
    """يفحص جودة الخطة ولا يكترث لعدد الأسطر"""
    
    lines = plan_content.split('\n')
    
    checks = {
        "no_padding": True,
        "no_generic_media": True,
        "scenes_have_word_timings": True,
        "template_diversity": True,
        "sfx_diversity": True,
        "has_citations": True,
        "no_sequential_repetition": True
    }
    
    errors = []
    
    # فحص التكرار المتسلسل للحشو
    repetition_check = detect_sequential_repetition(lines)
    if repetition_check["has_repetition"]:
        checks["no_sequential_repetition"] = False
        errors.append("❌ PLAN REJECTED: تم اكتشاف حشو متسلسل (جمل مكررة مع تغيير الأرقام).")
        for line, count in repetition_check["repeated_lines"].items():
            errors.append(f"   - الجملة '{line}' تكررت {count} مرات.")
        errors.append("   إذا نفد المحتوى الحقيقي، توقف ولا تملأ الفراغ بجمل مكررة.")
    
    # استخراج القوالب والـ SFX والمشاهد
    templates = set()
    sfxs = set()
    scenes = []
    current_scene = None
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # 1. فحص الحشو (Padding)
        if "<!-- padding" in line_lower or "final padding" in line_lower:
            checks["no_padding"] = False
            errors.append(f"❌ PLAN REJECTED: تم العثور على حشو (<!-- Padding -->) في السطر {i+1}. החشو ممنوع — كل سطر يجب أن يضيف قيمة إنتاجية. قم بحذف الحشو وإعادة كتابة المحتوى الحقيقي.")
            
        # 2. العبارات العامة
        if "خلفية عامة" in line or "أصل 1" in line or "لقطة مهمة" in line:
            checks["no_generic_media"] = False
            errors.append(f"❌ PLAN REJECTED: تم العثور على عبارة عامة ('خلفية عامة' أو ما شابه) في السطر {i+1}. يجب استخدام أوصاف دقيقة ومحددة.")
            
        # استخراج الاستشهادات
        if "motion_taste_citation" in line_lower or "treatment_citation" in line_lower:
            checks["has_citations"] = True
            
        # تقسيم المشاهد
        scene_match = re.search(r'#### المشهد\s*(\d+)', line)
        if scene_match:
            if current_scene:
                scenes.append(current_scene)
            current_scene = {"id": scene_match.group(1), "lines": []}
            
        if current_scene:
            current_scene["lines"].append(line)
            
        # استخراج القوالب
        template_match = re.search(r'-\s*القالب:\s*(.+)', line)
        if template_match:
            template_name = template_match.group(1).strip()
            if template_name and not template_name.startswith("["):
                templates.add(template_name.lower())
                
        # استخراج SFX
        sfx_match = re.search(r'-\s*SFX:\s*(.+)', line)
        if sfx_match:
            sfx_name = sfx_match.group(1).strip()
            if sfx_name and not sfx_name.startswith("["):
                sfxs.add(sfx_name.lower())

    if current_scene:
        scenes.append(current_scene)
        
    # فحص تنوع القوالب
    if len(templates) < 3 and len(scenes) >= 3:
        checks["template_diversity"] = False
        errors.append(f"❌ PLAN REJECTED: تم استخدام {len(templates)} قوالب فقط. يجب استخدام ≥ 3 قوالب مختلفة من TEMPLATE_INDEX.md.")
        
    # فحص جداول الكلمات وعدد المؤثرات الصوتية في كل مشهد
    for scene in scenes:
        scene_text = "\n".join(scene["lines"])
        if "| الكلمة" not in scene_text and "جدول الكلمات" not in scene_text:
            checks["scenes_have_word_timings"] = False
            errors.append(f"❌ PLAN REJECTED: المشهد {scene['id']} لا يحتوي على جدول كلمات. كل مشهد يجب أن يحتوي على جدول كلمات مع توقيتات دقيقة.")
            
        # فحص عدد المؤثرات الصوتية في المشهد
        sfx_count = scene_text.lower().count(".wav")
        if sfx_count > 4:  # السماح بـ 2-3 وربما 4 كحد أقصى في المشهد بأكمله
            checks["sfx_diversity"] = False
            errors.append(f"❌ PLAN REJECTED: المشهد {scene['id']} يحتوي على {sfx_count} مؤثرات صوتية (.wav). القاعدة تنص على: حظر المؤثرات العشوائية لكل كلمة، وقصرها على 2-3 ضربات مفصلية للمشهد ككل.")
            
    # التحقق من وجود الاستشهادات إذا لم نجدها
    if "motion_taste_citation" not in plan_content.lower() or "treatment_citation" not in plan_content.lower():
        checks["has_citations"] = False
        errors.append("❌ PLAN REJECTED: الخطة لا تحتوي على الاستشهادات الإلزامية (motion_taste_citation و treatment_citation).")

    is_valid = len(errors) == 0
    return is_valid, errors

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python plan_gate.py <project_id>")
        sys.exit(1)
        
    project_id = sys.argv[1]
    project_dir = Path(f"projects/{project_id}")
    plan_file = project_dir / "master_plan.md"
    
    if not plan_file.exists():
        print(f"❌ الخطة غير موجودة في المسار: {plan_file}")
        print("تأكد أن الوكيل قام بإنشاء master_plan.md بالفعل.")
        sys.exit(1)
        
    content = plan_file.read_text(encoding="utf-8")
    
    print(f"🔍 فحص جودة الخطة للمشروع {project_id}...")
    is_valid, errors = validate_plan_quality(content)
    
    if not is_valid:
        print("\n".join(errors))
        sys.exit(1)
        
    print("✅ PLAN VALID: الخطة مطابقة لمعايير الجودة والتفاصيل الدقيقة. لا يوجد حشو وتم التحقق من التنوع.")
    sys.exit(0)

if __name__ == "__main__":
    main()
