#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import subprocess
import concurrent.futures
from pathlib import Path

def build_scene(project_dir: Path, scene_idx: int):
    """بناء مشهد محدد عبر استدعاء سكريبت البناء (أو إنشاء الكود الافتراضي كنموذج)"""
    comp_dir = project_dir / "06_build" / "src" / "compositions"
    comp_dir.mkdir(parents=True, exist_ok=True)
    
    scene_file = comp_dir / f"Scene{scene_idx}.tsx"
    
    # محاكاة بناء المشهد بناءً على القوالب
    # (في النظام الحقيقي، هنا نستدعي materialize_project أو code generator)
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
        
    # فحص code_template_gate
    gate_script = Path(__file__).parent / "code_template_gate.py"
    if gate_script.exists():
        cmd = [sys.executable, str(gate_script), str(scene_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if result.returncode != 0:
            return {"status": "fail", "scene": scene_idx, "error": result.stdout}
            
    return {"status": "pass", "scene": scene_idx}

def generate_main_composition(project_dir: Path, num_scenes: int):
    """توليد MainComposition.tsx لجمع جميع المشاهد بـ Sequence"""
    comp_dir = project_dir / "06_build" / "src"
    main_file = comp_dir / "MainComposition.tsx"
    
    imports = []
    sequences = []
    
    duration_per_scene = 90 # افتراضي 3 ثواني للإطار (30FPS)
    
    for i in range(1, num_scenes + 1):
        imports.append(f"import {{ Scene{i} }} from './compositions/Scene{i}';")
        sequences.append(f"""
        <Sequence from={{{(i-1)*duration_per_scene}}} durationInFrames={{{duration_per_scene}}}>
            <Scene{i} />
        </Sequence>""")
        
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
    """تشغيل npx tsc --noEmit"""
    build_dir = project_dir / "06_build"
    if not build_dir.exists():
        return False, "مجلد البناء غير موجود"
        
    use_shell = os.name == "nt"
    cmd = ["npx", "tsc", "--noEmit"]
    
    print(f"🔍 فحص TypeScript...")
    result = subprocess.run(cmd, cwd=str(build_dir), capture_output=True, text=True, shell=use_shell)
    
    if result.returncode != 0:
        return False, result.stdout
    return True, "الكود نظيف"

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python batch_builder.py <project_id>")
        sys.exit(1)
        
    project_id = sys.argv[1]
    project_dir = Path(f"projects/{project_id}")
    
    if not project_dir.exists():
        print(f"❌ المشروع {project_id} غير موجود.")
        sys.exit(1)
        
    timings_file = project_dir / "04_timings.json"
    num_scenes = 1
    if timings_file.exists():
        try:
            timings = json.loads(timings_file.read_text(encoding="utf-8"))
            num_scenes = len(timings.get("sentences", [{"idx": 1}]))
        except Exception as e:
            print(f"⚠️ فشل قراءة 04_timings.json: {e}")
            
    print(f"🏗️ بناء {num_scenes} مشاهد بالتوازي...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(build_scene, project_dir, i): i for i in range(1, num_scenes + 1)}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append(res)
            if res["status"] == "pass":
                print(f"✅ المشهد {res['scene']} مبني")
            else:
                print(f"❌ المشهد {res['scene']} فشل: {res.get('error', '')}")
                
    # توليد التجميع
    print("🔄 تجميع المشاهد في MainComposition...")
    generate_main_composition(project_dir, num_scenes)
    
    # فحص TypeScript
    tsc_pass, tsc_msg = check_typescript(project_dir)
    if not tsc_pass:
        print(f"❌ فشل فحص TypeScript:\n{tsc_msg}")
    else:
        print("✅ TypeScript نظيف.")
        
    # إعداد التقرير
    report = {
        "total_scenes": num_scenes,
        "built_scenes": sum(1 for r in results if r["status"] == "pass"),
        "failed_scenes": sum(1 for r in results if r["status"] == "fail"),
        "tsc_passed": tsc_pass,
        "errors": [r for r in results if r["status"] == "fail"]
    }
    
    report_file = project_dir / "batch_build_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    
    if report["failed_scenes"] > 0 or not tsc_pass:
        sys.exit(1)
    else:
        print("🎉 اكتمل البناء المتوازي بنجاح.")
        sys.exit(0)

if __name__ == "__main__":
    main()
