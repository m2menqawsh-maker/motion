import json
import sys
from utils.logger import UnifiedLogger
log = UnifiedLogger("scene_compiler")

import os
import subprocess
import argparse

def compile_scenes(spec_path):
    if not os.path.exists(spec_path):
        log.info(f"Error: Spec file not found at {spec_path}")
        sys.exit(1)

    with open(spec_path, 'r', encoding='utf-8') as f:
        try:
            spec = json.load(f)
        except json.JSONDecodeError:
            log.info("Error: Spec file is not valid JSON")
            sys.exit(1)

    project_dir = os.path.dirname(spec_path)
    output_dir = os.path.join(project_dir, "06_build", "src", "compositions", "generated")
    os.makedirs(output_dir, exist_ok=True)

    scenes = spec.get("scenes", [])
    
    # الحصول على مسار الـ VO للاستخدام كـ Global Audio إذا لزم الأمر في الـ Scene
    global_vo_src = spec.get("global_audio", {}).get("vo", {}).get("src", "global_vo.mp3")

    for i, scene in enumerate(scenes):
        scene_idx = i + 1
        template = scene.get("template", "BaseTemplate")
        
        sfx_elements = []
        gestures = scene.get("gestures", [])
        for g_idx, g in enumerate(gestures):
            sfx = g.get("sfx")
            # إغلاق الـ SFX على إطارات الكلمات
            # نفترض أن كل إيماءة تمتلك إطار بداية frame بناءً على الكلمة المرتبطة
            frame = g.get("frame", 0) 
            if sfx:
                sfx_elements.append(f"""
      {{/* SFX {g_idx} locked to word frame {frame} */}}
      <Sequence from={{{frame}}}>
        <Audio src={{staticFile("media/sfx/{sfx}")}} />
      </Sequence>""")

        tsx_content = f"""// GENERATED — DO NOT EDIT
import React from 'react';
import {{ AbsoluteFill, Sequence, Audio, staticFile }} from 'remotion';
import {{ {template} }} from '@templates/{template}';
import {{ ZoomCarryBackground }} from '@engine/transitions/ZoomCarryBackground';

export const Scene{scene_idx}: React.FC = () => {{
  return (
    <AbsoluteFill>
      {{/* Audio global واحد للـ VO */}}
      <Audio src={{staticFile("media/vo/{global_vo_src}")}} />

      {{/* خلفية مستمرة بـ zoom_carry */}}
      <ZoomCarryBackground />

      {{/* مكون المشهد الأساسي */}}
      <Sequence from={{0}}>
        <{template} />
      </Sequence>

      {{/* SFX Sequences */}}
      {''.join(sfx_elements)}
    </AbsoluteFill>
  );
}};
"""
        out_file = os.path.join(output_dir, f"Scene{scene_idx}.tsx")
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(tsx_content)
        
        log.info(f"Generated {out_file}")

    log.info("\nRunning tsc --noEmit...")
    build_dir = os.path.join(project_dir, "06_build")
    if os.path.exists(build_dir):
        try:
            # نستخدم shell=True لأننا على Windows
            subprocess.run(["npx", "tsc", "--noEmit"], cwd=build_dir, shell=True, check=True)
            log.info("tsc --noEmit passed successfully.")
        except subprocess.CalledProcessError as e:
            log.info(f"tsc --noEmit failed with exit code {e.returncode}")
            sys.exit(1)
    else:
        log.info(f"Warning: Build directory {build_dir} not found. Skipping tsc.")

def main():
    parser = argparse.ArgumentParser(description="تجميع المشاهد")
    parser.add_argument("target_spec", nargs="?", default="projects/test_taste/video_spec.json", help="مسار ملف الفيديو")
    args = parser.parse_args()
    
    compile_scenes(args.target_spec)

if __name__ == "__main__":
    main()
