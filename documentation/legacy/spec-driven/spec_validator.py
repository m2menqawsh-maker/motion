import json
import sys
from utils.logger import UnifiedLogger
log = UnifiedLogger("spec_validator")

import os
import argparse

# مجرد كتالوج افتراضي لاختبار القاعدة، يمكن ربطه بـ TEMPLATE_INDEX.md لاحقاً
CATALOG = ["TitleScene", "BulletList", "HighlightCard", "CodeReveal", "SplitScreen", "CallToAction", "NeonCyberCard", "GlassmorphismPill"]

def validate_spec(spec_path):
    if not os.path.exists(spec_path):
        log.info(f"FAIL: Spec file not found at {spec_path}")
        sys.exit(1)

    with open(spec_path, 'r', encoding='utf-8') as f:
        try:
            spec = json.load(f)
        except json.JSONDecodeError:
            log.info("FAIL: Spec file is not valid JSON")
            sys.exit(1)

    project_dir = os.path.dirname(spec_path)
    asset_index_path = os.path.join(project_dir, "ASSET_INDEX.json")
    
    asset_index = []
    if os.path.exists(asset_index_path):
        with open(asset_index_path, 'r', encoding='utf-8') as f:
            try:
                asset_index = json.load(f)
            except:
                pass

    violations = []
    
    palette = spec.get("palette", [])
    global_audio = spec.get("global_audio", {})
    vo_info = global_audio.get("vo", {})
    
    vo_track = vo_info.get("track", "")
    vo_words = [w.get("word", "") for w in vo_info.get("words", [])]

    if vo_track != "global":
        violations.append(f"Global VO track is not 'global', found: '{vo_track}'")

    scenes = spec.get("scenes", [])
    for i, scene in enumerate(scenes):
        scene_id = i + 1
        
        # 1. template مش بالكتالوج
        template = scene.get("template")
        if template not in CATALOG:
            violations.append(f"Scene {scene_id}: Template '{template}' is not in the recognized catalog.")

        # 2. إيماءة بدون SFX مطابق
        for g in scene.get("gestures", []):
            if not g.get("sfx"):
                violations.append(f"Scene {scene_id}: Gesture '{g.get('type')}' has no matching SFX.")

        # 3. نص خارج كلمات الـ VO
        text = scene.get("text", "")
        if text:
            words_in_text = text.split()
            for w in words_in_text:
                # تنظيف بسيط للكلمات للمقارنة
                clean_w = "".join(c for c in w if c.isalnum())
                clean_vo_words = ["".join(c for c in vw if c.isalnum()) for vw in vo_words]
                if clean_w and clean_w not in clean_vo_words:
                    violations.append(f"Scene {scene_id}: Text word '{w}' is outside the VO words.")

        # 4. لون خارج الباليتة
        for color in scene.get("colors", []):
            if color not in palette:
                violations.append(f"Scene {scene_id}: Color '{color}' is outside the global palette.")

        # 5. asset_base مش بـ ASSET_INDEX.json
        for asset in scene.get("assets", []):
            asset_base = asset.get("asset_base")
            if asset_base and asset_index:
                # نفترض أن ASSET_INDEX هو قائمة من المسارات أو القواميس
                # هذا فحص مبسط
                if not any(asset_base in str(item) for item in asset_index):
                    violations.append(f"Scene {scene_id}: Asset base '{asset_base}' not found in ASSET_INDEX.json.")

    if violations:
        log.info("FAIL")
        for v in violations:
            log.info(f"- {v}")
        sys.exit(1)
    else:
        log.info("PASS")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="التحقق من صحة ملف الفيديو (Spec Validator)")
    parser.add_argument("target_spec", nargs="?", default="projects/test_taste/video_spec.json", help="مسار ملف الفيديو")
    args = parser.parse_args()
    
    validate_spec(args.target_spec)

if __name__ == "__main__":
    main()
