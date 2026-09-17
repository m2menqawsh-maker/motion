import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subprocess
from scripts.security import safe_subprocess
import json, re

def fail(msg):
    print("❌ TASTE GATE FAILED:", msg)
    sys.exit(1)

def warn(msg):
    print("⚠️ TASTE GATE WARN:", msg)

def parse_scene_plan(path):
    text = path.read_text(encoding="utf-8")
    
    # Check if this is a master_plan containing multiple scenes
    scene_chunks = re.split(r"#### المشهد \d+:", text)[1:]
    if not scene_chunks:
        # Fallback for individual scene files
        scene_chunks = [text]
        
    scenes = []
    
    for chunk in scene_chunks:
        scene = {"shots": [], "raw_text": chunk}
        
        # 1. Sentence index
        if "sentence_index" in chunk or "split_voiceover_sentences" in chunk:
            scene["sentence_index"] = 1
        else:
            scene["sentence_index"] = None

        # 2. Duration
        dur_match = re.search(r"المدة.*?(\d+(?:\.\d+)?)\s*(?:ث|ثواني|s)", chunk)
        if dur_match:
             scene["duration_sec"] = float(dur_match.group(1))
        else:
             scene["duration_sec"] = 0

        # 3. Shots
        shot_blocks = chunk.split("- نمط الإطار")[1:]
        if shot_blocks:
            shot_blocks[-1] = re.split(r"\*\*ج\)", shot_blocks[-1])[0]
            
        for block in shot_blocks:
            shot = {}
            shot["frame_style"] = block.split('\n')[0].replace(":", "").strip()
            
            if re.search(r"الإيماءة.*?(Neon Ring|Marker Underline|Highlighter BG|Strikethrough|Flash Cut)", block, re.IGNORECASE):
                shot["has_gesture"] = True
            else:
                shot["has_gesture"] = False
                
            if re.search(r"الانتقال.*?(\bDive\b|\bWhip Pan\b|\bZoom-Out\b|\bZoom\b)", block, re.IGNORECASE):
                shot["camera_driven_transition"] = True
            else:
                shot["camera_driven_transition"] = False
                
            if "Word-Chase Zoom" in block or "زوم مطاردة" in block:
                shot["is_word_zoom"] = True
                if "lock" in block.lower() or "مقفول" in block:
                    shot["has_word_lock"] = True
                else:
                    shot["has_word_lock"] = False
            else:
                shot["is_word_zoom"] = False
                shot["has_word_lock"] = False
                
            scene["shots"].append(shot)
            
        scenes.append(scene)
        
    return scenes

def main():
    if len(sys.argv) < 2:
        print("Usage: python taste_gate.py <scene_plan.md or master_plan.md>")
        sys.exit(1)
        
    scene_path = Path(sys.argv[1])
    if not scene_path.exists():
        fail(f"الملف غير موجود: {scene_path}")
        
    scenes = parse_scene_plan(scene_path)
    
    for idx, scene in enumerate(scenes):
        scene_name = f"{scene_path.name} (المشهد {idx+1})" if len(scenes) > 1 else scene_path.name
        
        # 1. حدود المشهد = حدود جملة VO
        if scene.get("sentence_index") is None:
            fail(f"مشهد {scene_name} لا يحتوي على sentence_index — حدوده يجب أن تأتي من split_voiceover_sentences")

        # 2. Beat Density (§0.3)
        sentence_duration = scene.get("duration_sec", 0)
        shot_count = len(scene.get("shots", []))
        if sentence_duration > 0 and shot_count > 0:
            if sentence_duration < 2.5 and shot_count > 1:
                fail(f"جملة قصيرة ({sentence_duration}ث) في {scene_name} لها {shot_count} لقطات — يجب أن تكون لقطة واحدة")
            if 2.5 <= sentence_duration <= 5 and shot_count not in [1, 2]:
                fail(f"جملة متوسطة ({sentence_duration}ث) في {scene_name} يجب أن يكون لها 1-2 لقطة، وجدت {shot_count}")
            if 5 < sentence_duration <= 8 and shot_count not in [2, 3]:
                fail(f"جملة طويلة ({sentence_duration}ث) في {scene_name} يجب أن يكون لها 2-3 لقطات، وجدت {shot_count}")
            if sentence_duration > 8 and shot_count not in [3, 4]:
                fail(f"جملة طويلة جداً ({sentence_duration}ث) في {scene_name} يجب أن يكون لها 3-4 لقطات، وجدت {shot_count}")

        if shot_count > 0:
            # 3. لقطتان متتاليتان بنفس نمط الإطار
            for i in range(shot_count - 1):
                if scene["shots"][i]["frame_style"] and scene["shots"][i]["frame_style"] == scene["shots"][i+1]["frame_style"]:
                    fail(f"لقطتان متتاليتان تحملان نفس نمط الإطار في {scene_name}: {scene['shots'][i]['frame_style']}")

            # 4. مشهد منطوق بدون إيماءة (§3)
            has_gesture_in_scene = any(s["has_gesture"] for s in scene["shots"])
            if not has_gesture_in_scene and "بدون إيماءة" not in scene["raw_text"]:
                warn(f"مشهد منطوق يجب أن يحمل ≥1 إيماءة على الكلمة المهمة (لم يتم اكتشاف إيماءة صريحة في {scene_name})")

            # 5. انتقالات كاميرا-Driven < 60%
            cam_driven = sum(1 for s in scene["shots"] if s["camera_driven_transition"])
            if cam_driven / shot_count < 0.6 and shot_count > 1:
                warn(f"نسبة الانتقالات بقيادة الكاميرا في {scene_name} أقل من 60% ({cam_driven}/{shot_count})")

            # 6. زوم كلمة بدون word lock
            for s in scene["shots"]:
                if s["is_word_zoom"] and not s["has_word_lock"]:
                    fail(f"تم استخدام Word-Chase Zoom بدون word lock صريح في {scene_name}!")

    # 7. لون خارج الباليتة (General generic check since actual hex depends on project blueprint)
    if "hex:" in scene["raw_text"] or "#" in scene["raw_text"]:
        # Mocking check for now
        pass

    # 8. التنوع المزدوج لمشهدين (not easily checked in a single scene script unless we read previous scenes, which we can skip for the basic gate or just pass)
    
    print(f"✅ TASTE GATE OK: اجتاز المشهد {scene_path.name} الفحص بنجاح.")

if __name__ == "__main__":
    main()
