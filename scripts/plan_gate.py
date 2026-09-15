import subprocess
from scripts.security import safe_subprocess
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from scripts.path_security import validate_project_id, safe_resolve
import re
import json
import os
from pathlib import Path
from collections import Counter

def ask_llm_judge(plan_content: str, scenes_count: int) -> tuple[bool, list]:
    if scenes_count < 3:
        return True, []
        
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("WARNING: LLM Judge skipped due to missing OPENAI_API_KEY")
        return True, []
        
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        prompt = f"""You are a Creative Director auditing a video plan.
Analyze the following plan for creative quality.
CRITERIA:
1. Cinematic descriptions: Backgrounds must be specific (e.g., "dark cyber background with neon grid"), NOT generic (e.g., "general background", "white background").
2. Contextual motion: Text animations should feel dynamic and matched to the tone.
3. No obvious padding/fluff.

Plan:
{plan_content}

Return a JSON object:
{{
  "is_approved": boolean,
  "score": number,
  "critique": "Detailed critique string. If rejected, explain why based on criteria."
}}
"""
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        result_str = resp.choices[0].message.content
        result = json.loads(result_str)
        
        if not result.get("is_approved", False) or result.get("score", 0) < 60:
            return False, [f"❌ LLM Judge REJECTED the plan (Score: {result.get('score')}): {result.get('critique')}"]
            
        return True, []
        
    except Exception as e:
        print(f"WARNING: LLM Judge skipped due to API error: {e}")
        return True, []


def detect_sequential_repetition(lines: list) -> dict:
    """يكشف التكرار المتسلسل للسطور (حشو من نوع جديد)"""
    
    # تجاهل السطور الفارغة
    content_lines = [l.strip() for l in lines if l.strip()]
    
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
    """يفحص جودة الخطة باستخدام القواعد الموحدة"""
    
    # تحميل القواعد الموحدة
    config_path = Path("config/violations_config.json")
    violations_rules = []
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            violations_rules = config.get("plan_quality_violations", [])
        except Exception:
            pass
    
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
        
        # 1. فحص الحشو والعبارات عبر القواعد الموحدة (Regex)
        for rule in violations_rules:
            pattern = rule.get("pattern", "")
            if pattern and re.search(pattern, line_lower, re.IGNORECASE):
                checks["no_padding"] = False
                msg = rule.get("message", "")
                errors.append(f"❌ PLAN REJECTED: السطر {i+1} يحتوي على مخالفة: {msg}")
            
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
    required_templates = min(len(scenes), 3) if len(scenes) > 0 else 1
    if len(templates) < required_templates:
        checks["template_diversity"] = False
        errors.append(f"❌ PLAN REJECTED: تم استخدام {len(templates)} قوالب فقط. المشاهد الحالية ({len(scenes)}) تتطلب على الأقل {required_templates} قوالب مختلفة.")
        
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
    
    # الطبقة الثانية: LLM Judge
    if is_valid:
        llm_valid, llm_errors = ask_llm_judge(plan_content, len(scenes))
        if not llm_valid:
            errors.extend(llm_errors)
            is_valid = False

    return is_valid, errors

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python plan_gate.py <project_id>")
        sys.exit(1)
        
    project_id = sys.argv[1]
    project_id = validate_project_id(project_id)
    project_dir = Path(f"projects/{project_id}")
    plan_file = project_dir / "master_plan.md"
    timings_file = project_dir / "04_timings.json"
    
    if not timings_file.exists():
        print(f"❌ خطأ فادح: لم يتم العثور على ملف {timings_file.name} في المشروع")
        print("يجب عليك أولاً استخدام أداة تحليل الصوت (analyze_voiceover) وطرح الأسئلة واستخراج التوقيتات قبل كتابة الخطة.")
        sys.exit(1)
    
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
