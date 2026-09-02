# -*- coding: utf-8 -*-
"""motion_validator.py — مدقق شخصية الحركة المبني ديناميكياً على motion-personality.md"""
import re, json, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def parse_personality(file_path):
    txt = Path(file_path).read_text(encoding="utf-8")
    
    # خريطة الأسماء لتطابق ما هو متوقع (Premium -> Cinematic, Corporate -> Technical)
    name_map = {
        "premium": "Cinematic",
        "luxury": "Cinematic",
        "corporate": "Technical",
        "professional": "Technical",
        "energetic": "Energetic",
        "dynamic": "Energetic",
        "playful": "Playful"
    }
    
    rules = {}
    current_arch = None
    
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("### "):
            raw_name = line.replace("### ", "").strip().lower()
            arch_name = None
            for key, val in name_map.items():
                if key in raw_name:
                    arch_name = val
                    break
            if arch_name:
                current_arch = arch_name
                rules[current_arch] = {"duration_min": 0, "duration_max": 0, "easing": "", "overshoot": []}
                
        if current_arch and line.startswith("| Duration |"):
            match = re.search(r"(\d+)-(\d+)ms", line)
            if match:
                rules[current_arch]["duration_min"] = int(match.group(1))
                rules[current_arch]["duration_max"] = int(match.group(2))
                
        if current_arch and line.startswith("| Easing |"):
            ease = line.split("|")[2].strip()
            # استخراج اسم الدالة فقط بدون كلام إضافي
            if "cubic-bezier" in ease:
                rules[current_arch]["easing"] = re.search(r"cubic-bezier\([^)]+\)", ease).group(0)
            elif "ease-out-expo" in ease:
                rules[current_arch]["easing"] = "ease-out-expo"
            elif "ease-out-back" in ease:
                rules[current_arch]["easing"] = "ease-out-back"
            else:
                rules[current_arch]["easing"] = ease.split(" ")[0]
                
        if current_arch and line.startswith("| Overshoot |"):
            os_val = line.split("|")[2].strip()
            if "-" in os_val:
                # 15-30%
                m = re.search(r"(\d+)-(\d+)%", os_val)
                if m:
                    rules[current_arch]["overshoot"] = [f"{i}%" for i in range(int(m.group(1)), int(m.group(2))+1)]
            else:
                rules[current_arch]["overshoot"] = [os_val]
    
    # Fallback to defaults if parsing fails for any reason
    if "Cinematic" not in rules or not rules["Cinematic"]["duration_min"]:
        rules["Cinematic"] = {"duration_min": 350, "duration_max": 600, "easing": "cubic-bezier(0.4, 0, 0.2, 1)", "overshoot": ["0%"]}
    if "Energetic" not in rules or not rules["Energetic"]["duration_min"]:
        rules["Energetic"] = {"duration_min": 100, "duration_max": 250, "easing": "ease-out-expo", "overshoot": [f"{i}%" for i in range(15, 31)]}
    if "Playful" not in rules or not rules["Playful"]["duration_min"]:
        rules["Playful"] = {"duration_min": 150, "duration_max": 300, "easing": "ease-out-back", "overshoot": [f"{i}%" for i in range(10, 21)]}
    if "Technical" not in rules or not rules["Technical"]["duration_min"]:
        rules["Technical"] = {"duration_min": 200, "duration_max": 400, "easing": "cubic-bezier(0.2, 0, 0, 1)", "overshoot": [f"{i}%" for i in range(0, 4)]}
        
    return rules

def validate(bp, file_path):
    fails = []
    meta = bp.get("meta", {})
    pers = meta.get("motion_personality") or meta.get("personality")
    
    if not pers:
        return ["شخصية الحركة ناقصة/مجهولة في الـ Blueprint"]
        
    rules = parse_personality(file_path)
    if pers not in rules:
        return [f"الشخصية {pers} غير معروفة في motion-personality.md"]
        
    rule = rules[pers]
    
    for sec in bp.get("timeline", []):
        for e in sec.get("elements", []):
            if e.get("kind") == "template" or "motion" in e:
                mot = e.get("motion", {})
                notes = str(e.get("notes", "")).strip()
                # يجب وجود استشهاد صريح في الملاحظات أو الخطة
                # الاستشهاد يُفحص أساساً في stage_gate، لكننا نتأكد من التبرير هنا
                valid_notes = len(notes) >= 15
                
                if not mot:
                    continue # Some elements don't have motion
                
                d = mot.get("duration_ms")
                easing = mot.get("easing")
                overshoot = mot.get("overshoot")
                
                if d is None:
                    fails.append(f"عنصر {e.get('id')}: duration_ms مفقود من كتلة motion")
                elif not (rule["duration_min"] <= d <= rule["duration_max"]) and not valid_notes:
                    fails.append(f"عنصر {e.get('id')}: duration {d}ms خارج النطاق {rule['duration_min']}-{rule['duration_max']} ولم يتم تبريره")
                    
                if easing is None:
                    fails.append(f"عنصر {e.get('id')}: easing مفقود من كتلة motion")
                elif easing != rule["easing"] and not valid_notes:
                    fails.append(f"عنصر {e.get('id')}: easing {easing} مخالف للقاعدة {rule['easing']}")
                    
                if overshoot is None:
                    fails.append(f"عنصر {e.get('id')}: overshoot مفقود من كتلة motion")
                elif overshoot not in rule["overshoot"] and not valid_notes:
                    allowed_os = ", ".join(rule["overshoot"]) if len(rule["overshoot"]) < 5 else f"{rule['overshoot'][0]}-{rule['overshoot'][-1]}"
                    fails.append(f"عنصر {e.get('id')}: overshoot {overshoot} مخالف للمسموح ({allowed_os})")
                    
    return fails


def validate_creative_rules(scene_plan, previous_scene_plan=None, project_blueprint=None):
    """
    فحص إبداعي إلزامي يمنع التكرار، يفرض الـ SFX، ويضمن الكثافة البصرية.
    يُستدعى بعد توليد كل scene_N_plan.md وقبل materialize_project.py
    """
    errors = []
    warnings = []
    
    # استخراج القوالب المستخدمة في المشهد الحالي
    current_templates = extract_templates_from_plan(scene_plan)
    
    # 1. فحص التنوع (Diversity Gate)
    if previous_scene_plan:
        previous_templates = extract_templates_from_plan(previous_scene_plan)
        repetitive_templates = {'Typewriter', 'BounceText', 'TextReveal', 'GlitchText'}
        
        # منع تكرار القوالب المتكررة في مشاهد متتالية
        overlap = set(current_templates) & set(previous_templates) & repetitive_templates
        if overlap:
            errors.append(f"❌ Diversity Violation: القوالب {overlap} مستخدمة في مشهدين متتاليين. استخدم قالباً من عائلة مختلفة.")
        
        # منع استخدام نفس العائلة في مشاهد متتالية
        current_family = get_template_family(current_templates)
        previous_family = get_template_family(previous_templates)
        if current_family == previous_family and current_family in ['Typography', 'Basic Text']:
            errors.append(f"❌ Family Repetition: المشهدان المتتاليان يستخدمان نفس العائلة ({current_family}). انتقل إلى عائلة مختلفة (Data, Motion Effects, UI Layouts).")
    
    # 2. فحص الـ SFX (Auto-SFX Injection Gate)
    sfx_count = count_sfx_in_plan(scene_plan)
    visual_gestures = count_visual_gestures(scene_plan)
    
    if visual_gestures > 0 and sfx_count < visual_gestures:
        errors.append(f"❌ Missing SFX: تم العثور على {visual_gestures} إيماءة بصرية ولكن فقط {sfx_count} SFX. أضف SFX من SFX_BINDING_MATRIX.md.")
    
    # 3. فحص الكثافة البصرية (Visual Density Gate)
    elements_count = count_visual_elements(scene_plan)
    if elements_count < 3 and isinstance(scene_plan, dict) and 'shots' in scene_plan:
        errors.append(f"❌ Low Visual Density: المشهد يحتوي على {elements_count} عناصر فقط. يجب أن يحتوي على 3+ عناصر (خلفية + عنصر متوسط + overlay).")
    
    # 4. فحص التنوع الكلي للفيديو (Global Diversity)
    if project_blueprint:
        all_templates = extract_all_templates(project_blueprint)
        template_counts = count_template_usage(all_templates)
        
        # منع تكرار Typewriter أكثر من مرتين
        if template_counts.get('Typewriter', 0) > 2:
            errors.append(f"❌ Typewriter Overuse: تم استخدام Typewriter {template_counts['Typewriter']} مرات (الحد الأقصى: 2). استبدل إحدى الاستخدامات بقالب آخر.")
        
        # فحص عدد العائلات المستخدمة
        families_used = get_unique_families(all_templates)
        if len(families_used) < 3 and len(all_templates) > 5:
            errors.append(f"❌ Low Family Diversity: تم استخدام {len(families_used)} عائلات فقط. يجب استخدام 3+ عائلات مختلفة.")
    
    # 5. فحص الذوق (Taste Gate)
    UGLY_TEMPLATES = {"SplitScreen", "BasicText", "SimpleFade", "iconify"}
    for tpl in current_templates:
        if tpl in UGLY_TEMPLATES:
            errors.append(f"❌ Taste Violation: القالب '{tpl}' يعتبر بدائياً/قبيحاً — استخدم قالباً أكثر تطوراً من TEMPLATE_INDEX.md (مثل DeviceMockupZoom).")

    # طباعة النتائج
    if errors:
        print("❌ Creative Validation Failed:")
        for err in errors:
            print(f"  {err}")
        return False
    else:
        print("✅ Creative Validation Passed:")
        print(f"  - التنوع: {len(current_templates)} قوالب من عائلات مختلفة")
        print(f"  - الـ SFX: {sfx_count} مؤثرات صوتية لـ {visual_gestures} إيماءات بصرية")
        print(f"  - الكثافة: {elements_count} عناصر بصرية")
        return True

# دوال مساعدة (Helper Functions)
def extract_templates_from_plan(scene_plan):
    """يستخرج أسماء القوالب من خطة المشهد"""
    if isinstance(scene_plan, str):
        p = Path(scene_plan)
        text = p.read_text(encoding="utf-8") if p.exists() else scene_plan
        return re.findall(r"`([A-Za-z0-9_-]+)`", text)
    templates = []
    if isinstance(scene_plan, dict):
        if 'shots' in scene_plan:
            for shot in scene_plan['shots']:
                if 'template' in shot:
                    templates.append(shot['template'])
        if 'elements' in scene_plan:
            for el in scene_plan['elements']:
                if 'template' in el:
                    templates.append(el['template'])
    return templates

def get_template_family(templates):
    """يحدد العائلة التي ينتمي إليها القالب"""
    family_map = {
        'Typewriter': 'Typography',
        'BounceText': 'Typography',
        'TextReveal': 'Typography',
        'GlitchText': 'Typography',
        'BlurReveal': 'Typography',
        'TrackingIn': 'Typography',
        'StatCounter': 'Data & Stats',
        'ChartAnimation': 'Data & Stats',
        'AreaChart': 'Data & Stats',
        'CardFlip': 'UI & Layouts',
        'ParallaxPan': 'Motion Effects',
        'ParticleExplosion': 'Motion Effects',
        'MatrixRain': 'Full Scenes & Hooks',
        'ZoomThrough': 'Full Scenes & Hooks'
    }
    families = set()
    for tpl in templates:
        families.add(family_map.get(tpl, 'Unknown'))
    if len(families) == 1:
        return next(iter(families))
    return 'Mixed' if families else 'Unknown'


def count_sfx_in_plan(scene_plan):
    """يعدّ عدد الـ SFX في خطة المشهد"""
    if isinstance(scene_plan, str):
        p = Path(scene_plan)
        text = p.read_text(encoding="utf-8") if p.exists() else scene_plan
        return len(re.findall(r"\.wav|\.mp3|sfx|whoosh|chime|boom|pop|click|swish", text, re.IGNORECASE))
    count = 0
    if isinstance(scene_plan, dict):
        if 'shots' in scene_plan:
            for shot in scene_plan['shots']:
                if 'sfx' in shot:
                    count += 1
        if 'sfx' in scene_plan:
            count += len(scene_plan['sfx'])
    return count

def count_visual_gestures(scene_plan):
    """يعدّ عدد الإيماءات البصرية في خطة المشهد"""
    if isinstance(scene_plan, str):
        p = Path(scene_plan)
        text = p.read_text(encoding="utf-8") if p.exists() else scene_plan
        return len(re.findall(r"Neon Ring|Marker Underline|Highlighter|Strikethrough|Flash Cut|Shock Zoom", text, re.IGNORECASE))
    count = 0
    if isinstance(scene_plan, dict) and 'shots' in scene_plan:
        for shot in scene_plan['shots']:
            if 'emphasis' in shot or 'gesture' in shot:
                count += 1
    return count

def count_visual_elements(scene_plan):
    """يعدّ عدد العناصر البصرية في خطة المشهد"""
    if isinstance(scene_plan, str):
        p = Path(scene_plan)
        text = p.read_text(encoding="utf-8") if p.exists() else scene_plan
        rows = re.findall(r"\|.*\|", text)
        return max(len(rows) - 2, 3) if len(rows) > 2 else 3
    count = 0
    if isinstance(scene_plan, dict):
        if 'shots' in scene_plan:
            for shot in scene_plan['shots']:
                count += len(shot.get('elements', []))
        if 'elements' in scene_plan:
            count += len(scene_plan['elements'])
    return count

def extract_all_templates(project_blueprint):
    """يستخرج كل القوالب من الـ Blueprint الكامل"""
    templates = []
    if isinstance(project_blueprint, str):
        p = Path(project_blueprint)
        if p.exists():
            project_blueprint = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(project_blueprint, dict) and 'timeline' in project_blueprint:
        for scene in project_blueprint['timeline']:
            for el in scene.get('elements', []):
                if 'template' in el:
                    templates.append(el['template'])
    return templates

def count_template_usage(templates):
    """يعدّ استخدام كل قالب"""
    counts = {}
    for tpl in templates:
        counts[tpl] = counts.get(tpl, 0) + 1
    return counts

def get_unique_families(templates):
    """يحصل على العائلات الفريدة المستخدمة"""
    families = set()
    for tpl in templates:
        f = get_template_family([tpl])
        if f != 'Unknown' and f != 'Mixed':
            families.add(f)
        elif isinstance(f, set):
            families.update(f)
    return families


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
        if target_path.suffix == ".json":
            bp = json.loads(target_path.read_text(encoding="utf-8"))
            motion_taste_file = Path(__file__).resolve().parent.parent / "references" / "deep" / "motion-taste" / "director" / "motion-personality.md"
            if not motion_taste_file.exists():
                motion_taste_file = Path(__file__).resolve().parent.parent / "references" / "motion-taste" / "director" / "motion-personality.md"
            fails = validate(bp, motion_taste_file)
            if fails:
                print("❌ MOTION VALIDATION FAIL:")
                for f in fails:
                    print(" -", f)
                sys.exit(1)
            print("✅ MOTION VALIDATION PASS")
            
            # Run creative rules validation if provided
            prev_plan = sys.argv[2] if len(sys.argv) > 2 else None
            if not validate_creative_rules(bp, prev_plan, bp):
                print("\n🛑 Creative Validation Failed. Cannot proceed to materialize_project.py")
                print("عدّل خطة المشهد وأعد التشغيل.")
                sys.exit(1)

