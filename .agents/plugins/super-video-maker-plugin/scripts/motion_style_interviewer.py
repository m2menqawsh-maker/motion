import sys
import json
import os

def calculate_motion_style(answers: list[int]) -> dict:
    """يحسب ستايل الحركة بناءً على الإجابات"""
    
    # الإيقاع
    if answers[0] == 1:
        timing = "fast_micro"  # 100-150ms
    elif answers[0] == 2:
        timing = "fast_standard"  # 180-250ms
    elif answers[0] == 3:
        timing = "medium"  # 300-400ms
    else:
        timing = "slow"  # 500ms+
    
    # نوع الحركة
    if answers[1] == 1:
        motion_type = "energetic"
        spring_config = {"mass": 0.8, "stiffness": 220, "damping": 18}
        overshoot = 0.25  # 25%
    elif answers[1] == 2:
        motion_type = "smooth"
        spring_config = {"mass": 1.0, "stiffness": 150, "damping": 20}
        overshoot = 0.10  # 10%
    elif answers[1] == 3:
        motion_type = "cinematic"
        spring_config = {"mass": 1.2, "stiffness": 100, "damping": 25}
        overshoot = 0.05  # 5%
    else:
        motion_type = "minimal"
        spring_config = {"mass": 1.5, "stiffness": 80, "damping": 30}
        overshoot = 0.0  # 0%
    
    return {
        "style_name": f"{motion_type}_{timing}",
        "spring_config": spring_config,
        "overshoot": overshoot,
        "easing": "ease-out-expo" if motion_type == "energetic" else "ease-in-out",
        "timing": {
            "micro": "100ms" if timing == "fast_micro" else "150ms",
            "standard": "180ms" if timing == "fast_standard" else "250ms",
            "scene": "300ms" if timing != "slow" else "500ms",
        },
        "camera": {
            "zoom_max": 1.4 if answers[2] == 1 else 1.2 if answers[2] == 2 else 1.1,
            "pan_speed": "fast" if answers[2] <= 2 else "slow",
        },
        "transitions": {
            "duration": "150ms" if answers[3] == 1 else "250ms" if answers[3] == 2 else "400ms",
            "type": "whip_pan" if answers[3] == 1 else "zoom_through" if answers[3] == 2 else "fade",
        },
        "effects": {
            "intensity": "high" if answers[4] == 1 else "medium" if answers[4] == 2 else "low",
            "neon_glow": answers[4] <= 2,
            "shockwaves": answers[4] == 1,
        },
        "text_animation": {
            "style": "karaoke" if answers[5] == 1 else "spring" if answers[5] == 2 else "fade",
            "overshoot": overshoot,
        },
        "colors": {
            "neon_intensity": "high" if answers[6] == 1 else "medium" if answers[6] == 2 else "low",
            "saturation": 1.2 if answers[6] <= 2 else 0.8,
        },
        "depth": {
            "layers": 5 if answers[7] == 1 else 3 if answers[7] == 2 else 2,
            "parallax": answers[7] <= 2,
        },
        "sfx": {
            "density": "high" if answers[8] == 1 else "medium" if answers[8] == 2 else "low",
            "per_scene": 5 if answers[8] == 1 else 3 if answers[8] == 2 else 1,
        },
        "audience": ["gen_z", "professional", "general", "educational"][answers[9] - 1],
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python motion_style_interviewer.py <project_id>")
        sys.exit(1)
        
    project_id = sys.argv[1]
    
    questions = """🎬 معاينة ستايل الحركة (Motion Style Interview)

السؤال 1: ما الإيقاع العام للفيديو؟
1. سريع جداً (100-150ms للحركات) — إعلانات شبابية
2. سريع (180-250ms) — محتوى ديناميكي
3. متوسط (300-400ms) — محتوى احترافي
4. بطيء (500ms+) — محتوى سينمائي أو تعليمي

السؤال 2: ما نوع الحركة المفضل؟
1. ديناميكية جداً (تسارع + تباطؤ + overshoot)
2. ناعمة وسلسة (ease-in-out)
3. سينمائية (Dolly, Orbit, Crane)
4. ثابتة وهادئة (لا حركة كثيرة)

السؤال 3: ما نوع الكاميرا المفضل؟
1. عميقة جداً (Zoom 1.4x+) + بان ديناميكي
2. متوسطة (Zoom 1.2x) + تحركات لطيفة
3. خفيفة (Zoom 1.1x) + حركات ناعمة
4. ثابتة تماماً (لا زوم)

السؤال 4: ما نوع الانتقالات المفضل؟
1. سريعة وخاطفة (Whip Pan, Flash Cut, 150ms)
2. ديناميكية (Zoom Through, Swish Pan, 250ms)
3. ناعمة (Cross Dissolve, Fade, 400ms)
4. سينمائية (Dissolve بطيء, 800ms+)

السؤال 5: ما قوة التأثيرات البصرية؟
1. قوية جداً (موجات صدمة، انفجارات، نيون مشع)
2. متوسطة (توهج خفيف، particles)
3. خفيفة (shadows بسيطة)
4. لا تأثيرات (نظيف تماماً)

السؤال 6: ما ستايل النصوص والكابشن؟
1. ديناميكي جداً (Karaoke Pop, Word by Word)
2. حيوي (Spring Bounce, Overshoot)
3. ناعم (Fade In, Slide Up)
4. ثابت (لا حركة للنصوص)

السؤال 7: ما قوة الألوان والنيون؟
1. نيون قوي مشع + ألوان فاقعة
2. نيون متوسط + ألوان زاهية
3. ألوان هادئة + نيون خفيف
4. ألوان محايدة (رمادي، أبيض، أسود)

السؤال 8: ما مستوى العمق والطبقات؟
1. عميق جداً (5+ طبقات، Parallax قوي)
2. متوسط (3-4 طبقات، Parallax خفيف)
3. بسيط (2 طبقات، لا Parallax)
4. مسطح تماماً (طبقة واحدة)

السؤال 9: ما كثافة المؤثرات الصوتية (SFX)?
1. كثيفة (SFX لكل حركة + موسيقى قوية)
2. متوسطة (SFX للانتقالات + موسيقى خفيفة)
3. قليلة (SFX للأحداث المهمة فقط)
4. نادرة جداً (موسيقى فقط أو صمت)

السؤال 10: ما الجمهور المستهدف؟
1. شبابي (Gen Z, TikTok, Instagram Reels)
2. مهني (LinkedIn, B2B, Corporate)
3. عام (YouTube, Facebook)
4. تعليمي (دورات، شروحات)

أجب بأرقام فقط مفصولة بفاصلة (مثال: 1, 2, 1, 1, 2, 1, 1, 2, 2, 1)
أو اكتب "افتراضي" لاستخدام Energetic/Dynamic"""

    print(questions)
    
    try:
        user_input = input("\nإجابتك: ").strip().lstrip('\ufeff')
    except EOFError:
        user_input = "افتراضي"

    project_dir = os.path.join("projects", project_id)
    os.makedirs(project_dir, exist_ok=True)
    config_path = os.path.join(project_dir, "motion_style_config.json")
    
    if user_input == "تجاوز المعاينة":
        config = {"style": "skipped"}
    elif user_input == "افتراضي" or user_input == "default":
        # Default Energetic
        answers = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        config = calculate_motion_style(answers)
    else:
        try:
            answers = [int(x.strip()) for x in user_input.split(",")]
            if len(answers) != 10:
                print("يجب إدخال 10 أرقام.")
                sys.exit(1)
            config = calculate_motion_style(answers)
        except ValueError:
            print("إدخال غير صالح. سيتم استخدام الافتراضي.")
            answers = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
            config = calculate_motion_style(answers)
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        
    print(f"\n✅ تم حفظ الستايل بنجاح في: {config_path}")
    
    # Update session state
    state_path = os.path.join(project_dir, ".session_state.json")
    state = {}
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                pass
        
    state["motion_style"] = config.get("style_name", "skipped")
    
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
