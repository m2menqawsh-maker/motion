import os
import sys
from utils.logger import UnifiedLogger
log = UnifiedLogger("batch_builder")
from utils.config import Config
config = Config()

import json
import time
import subprocess
import argparse
import concurrent.futures
from datetime import datetime
from pathlib import Path

def _do_build_scene(project_dir: Path, scene_idx: int) -> dict:
    comp_dir = project_dir / "06_build" / "src" / "compositions"
    comp_dir.mkdir(parents=True, exist_ok=True)
    scene_file = comp_dir / f"Scene{scene_idx}.tsx"
    
    if not scene_file.exists():
        code = f"""import React from 'react';
import {{ AbsoluteFill }} from 'remotion';

export const Scene{scene_idx}: React.FC = () => {{
    return (
        <AbsoluteFill style={{{{ backgroundColor: 'white', justifyContent: 'center', alignItems: 'center' }}}}>
            <h1>مشهد {scene_idx}</h1>
        </AbsoluteFill>
    );
}};
"""
        scene_file.write_text(code, encoding="utf-8")
        
    gate_script = Path(r"c:\video\clean-video-workspace\.agents\plugins\super-video-maker-plugin\scripts\code_template_gate.py")
    
    if gate_script.exists():
        cmd = [sys.executable, str(gate_script), str(scene_file)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=15)
            if result.returncode != 0:
                return {"success": False, "error": result.stdout, "error_type": "logical"}
        except subprocess.TimeoutExpired as e:
            raise e
        except IOError as e:
            raise e
            
    return {"success": True}

def build_scene(project_dir: Path, scene_idx: int) -> dict:
    max_retries = config.get('gates.max_retries', 3)
    delays = config.get('gates.retry_delays', [0.5, 1.0, 2.0])
    
    for attempt in range(max_retries):
        try:
            result = _do_build_scene(project_dir, scene_idx)
            if result["success"]:
                if attempt > 0:
                    log.success(f"المشهد {scene_idx} نجح بعد {attempt + 1} محاولات")
                return {"status": "pass", "scene": scene_idx, "attempts": attempt + 1}
            
            if result.get("error_type") == "logical":
                log.error(f"المشهد {scene_idx}: فشل منطقي، لا retry")
                return {"status": "fail", "scene": scene_idx, "error": result["error"], "error_type": "logical"}
            
        except (IOError, subprocess.TimeoutExpired) as e:
            if attempt < max_retries - 1:
                delay = delays[attempt] if attempt < len(delays) else delays[-1]
                log.info(f"️ المشهد {scene_idx}: خطأ عابر، retry بعد {delay}s...")
                time.sleep(delay)
            else:
                return {
                    "status": "fail",
                    "scene": scene_idx,
                    "error": str(e),
                    "attempts": max_retries,
                    "error_type": "transient"
                }
    
    return {"status": "fail", "scene": scene_idx, "error": "max retries exceeded", "error_type": "transient"}

def get_scene_duration(project_dir: Path, scene_num: int) -> int:
    duration_per_scene = 90
    timings_file = project_dir / "04_timings.json"
    if timings_file.exists():
        try:
            timings = json.loads(timings_file.read_text(encoding="utf-8"))
            sentences = timings.get("sentences", [])
            for s in sentences:
                if s.get("idx") == scene_num or s.get("scene_idx") == scene_num:
                    return s.get("duration_frames", duration_per_scene)
        except Exception:
            pass
    return duration_per_scene

def generate_main_composition(project_dir: Path, total_scenes: int, successful_scenes: list):
    if not successful_scenes:
        raise Exception("❌ لا يوجد أي مشهد ناجح — لا يمكن توليد MainComposition")
    
    expected = set(range(1, total_scenes + 1))
    missing = expected - set(successful_scenes)
    if missing:
        log.info(f"️ تحذير: المشاهد {sorted(missing)} فشلت")
        log.info("MainComposition سيحتوي على المشاهد الناجحة فقط")
    
    comp_dir = project_dir / "06_build" / "src"
    main_file = comp_dir / "MainComposition.tsx"
    
    imports = []
    sequences = []
    current_frame = 0
    
    for scene_num in sorted(successful_scenes):
        imports.append(f"import {{ Scene{scene_num} }} from './compositions/Scene{scene_num}';")
        duration = get_scene_duration(project_dir, scene_num)
        sequences.append(f"""
        <Sequence from={{{current_frame}}} durationInFrames={{{duration}}}>
            <Scene{scene_num} />
        </Sequence>""")
        current_frame += duration
        
    code = f"""import React from 'react';
import {{ AbsoluteFill, Sequence }} from 'remotion';
{chr(10).join(imports)}

export const MainComposition: React.FC = () => {{
    return (
        <AbsoluteFill>
            {''.join(sequences)}
        </AbsoluteFill>
    );
}};
"""
    main_file.write_text(code, encoding="utf-8")

def check_typescript(project_dir: Path):
    build_dir = project_dir / "06_build"
    if not build_dir.exists():
        return False, "مجلد البناء غير موجود"
        
    use_shell = os.name == "nt"
    cmd = ["npx", "tsc", "--noEmit"]
    
    log.debug(f"فحص TypeScript...")
    result = subprocess.run(cmd, cwd=str(build_dir), capture_output=True, text=True, shell=use_shell)
    
    if result.returncode != 0:
        return False, result.stdout
    return True, "الكود نظيف"

def main():
    parser = argparse.ArgumentParser(description="بناء المشاهد على دفعات (Batch Builder)")
    parser.add_argument("project_id", help="معرف المشروع")
    args = parser.parse_args()
    
    project_id = args.project_id
    global log
    log = UnifiedLogger("batch_builder", project_id)
    project_dir = Path(f"projects/{project_id}")
    
    if not project_dir.exists():
        log.error(f"المشروع {project_id} غير موجود.")
        sys.exit(1)
        
    timings_file = project_dir / "04_timings.json"
    num_scenes = 1
    if timings_file.exists():
        try:
            timings = json.loads(timings_file.read_text(encoding="utf-8"))
            num_scenes = len(timings.get("sentences", [{"idx": 1}]))
        except Exception as e:
            log.info(f"️ فشل قراءة 04_timings.json: {e}")
            
    log.info(f"️ بناء {num_scenes} مشاهد بالتوازي...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(build_scene, project_dir, i): i for i in range(1, num_scenes + 1)}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            if res["status"] == "pass":
                if res.get("attempts", 1) == 1:
                    log.success(f"المشهد {res['scene']} مبني")
            else:
                log.error(f"المشهد {res['scene']} فشل: {res.get('error', '')}")
                
    successful_scenes = [r["scene"] for r in results if r["status"] == "pass"]
    failed_scenes = [r["scene"] for r in results if r["status"] == "fail"]
    
    total_retries = sum([r.get("attempts", 1) - 1 for r in results if r.get("attempts", 1) > 1])
    scenes_with_retries = sum([1 for r in results if r.get("attempts", 1) > 1])
    
    log.info("تجميع المشاهد في MainComposition...")
    try:
        generate_main_composition(project_dir, num_scenes, successful_scenes)
    except Exception as e:
        print(str(e))
        sys.exit(1)
    
    tsc_pass, tsc_msg = check_typescript(project_dir)
    if not tsc_pass:
        log.error(f"فشل فحص TypeScript:\n{tsc_msg}")
    else:
        log.success("TypeScript نظيف.")
        
    build_report = {
        "project_id": project_id,
        "timestamp": datetime.now().isoformat(),
        "total_scenes": num_scenes,
        "successful": successful_scenes,
        "failed": failed_scenes,
        "retry_stats": {
            "total_retries": total_retries,
            "scenes_with_retries": scenes_with_retries
        }
    }
    
    report_path = project_dir / "batch_build_report.json"
    report_path.write_text(json.dumps(build_report, indent=2, ensure_ascii=False), encoding='utf-8')
    log.info(f"تقرير البناء: {report_path}")
    
    if len(failed_scenes) > 0 or not tsc_pass:
        sys.exit(1)
    else:
        log.success("اكتمل البناء المتوازي بنجاح.")
        sys.exit(0)

if __name__ == "__main__":
    main()
