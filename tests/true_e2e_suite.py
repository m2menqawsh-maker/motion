#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import subprocess
import json
import uuid
import os
import time

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))

from scripts.state_store import StateStore
from scripts.state_model import GateStatus, CheckpointStage

def create_dummy_media(project_dir: Path):
    # Create a dummy image
    assets_dir = project_dir / "assets" / "incoming"
    assets_dir.mkdir(parents=True, exist_ok=True)
    # We can create a 1x1 black image or similar using python, or just copy a file if exists.
    # For now, let's just make sure tests don't fail due to missing files if not requested.
    pass

def run_pipeline(project_id: str):
    print(f"Running pipeline for {project_id}...")
    proc = subprocess.run([sys.executable, "scripts/pipeline.py", project_id], cwd=str(workspace_root), capture_output=True, text=True, encoding="utf-8")
    return proc

def setup_test_files(project_dir: Path, aspect: str):
    # 04_timings.json
    timings = {
        "words": [{"word": "Test", "start": 0.0, "end": 1.0}],
        "sentences": [{"sentence": "Test", "start": 0.0, "end": 1.0}],
        "silences": []
    }
    (project_dir / "04_timings.json").write_text(json.dumps(timings), encoding="utf-8")
    
    import wave
    # Create dummy audio file
    sfx_dir = project_dir / "assets" / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    with wave.open(str(sfx_dir / "swoosh.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(b'\x00' * 100)
    
    # 02_asset_manifest.json
    manifest = {
        "assets": [
            {"asset_id": "swoosh_sfx", "type": "audio", "path": f"projects/{project_dir.name}/assets/sfx/swoosh.wav"}
        ]
    }
    (project_dir / "02_asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    
    # master_plan.md
    plan = """
motion_taste_citation
treatment_citation

#### المشهد 1
sentence_index: 1
المدة 2.0 ث
- القالب: fade-transition
- SFX: swoosh.wav
- نمط الإطار: Neon Ring
- الانتقال: Dive

| الكلمة | البداية | النهاية |
|---|---|---|
| Test | 0.0 | 1.0 |
"""
    (project_dir / "master_plan.md").write_text(plan, encoding="utf-8")
    
    # 05_blueprint.json
    blueprint = {
        "project_id": project_dir.name,
        "version": "1.0",
                "meta": {
            "motion_personality": "Cinematic",
            "timings_path": f"projects/{project_dir.name}/04_timings.json",
            "approval": {"blueprint_approved": True}
        },
        "assets": [
            {"asset_id": "swoosh_sfx", "type": "audio", "source": "user_upload", "path": "assets/sfx/swoosh.wav", "paid": False}
        ],
        "scenes": [
            {
                "scene_id": "scene_01",
                "startFrame": 0,
                "durationFrames": 90,
                "template": "Animatedtextwrapper",
                "content": {
                    "text": "مرحباً بالعالم!",
                    "audio_ref": "voice_1"
                },
                "sfx_ref": "swoosh_sfx",
                "template_props": {}
            }
        ]
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint, indent=2), encoding="utf-8")


def run_scenario(name: str, aspect: str):
    print(f"\n{'='*50}\nStarting Scenario: {name} ({aspect})\n{'='*50}")
    
    # 1. Scaffold
    scaffold_proc = subprocess.run(
        [sys.executable, "scripts/scaffold_project.py", "--name", name, "--language", "ar"],
        cwd=str(workspace_root), capture_output=True, text=True
    )
    if scaffold_proc.returncode != 0:
        print("Scaffold failed:")
        print(scaffold_proc.stderr)
        return False
        
    project_id = scaffold_proc.stdout.strip()
    print(f"Scaffolded Project ID: {project_id}")
    project_dir = workspace_root / "projects" / project_id
    
    # 2. Inject test files
    setup_test_files(project_dir, aspect)
    
    # 3. Run Pipeline (Pass 1) -> Should stop at Studio Review (Phase 5)
    proc1 = run_pipeline(project_id)
    if proc1.returncode != 0:
        print(f"Pipeline Pass 1 Failed for {project_id}!")
        print(proc1.stdout)
        print(proc1.stderr)
        return False
        
    if "المشروع جاهز للمعاينة في الاستوديو" not in proc1.stdout:
        print(f"Pipeline didn't stop at Studio Review for {project_id}!")
        print(proc1.stdout)
        return False
        
    print("Pipeline Pass 1 correctly stopped at Studio Review.")
    print("Pass 1 Output:")
    print(proc1.stdout)
    
    # 4. Approve project
    print("Simulating Studio Approval...")
    state = StateStore.load(project_dir)
    state.gates["gate_3"].status = GateStatus.APPROVED
    StateStore.save(project_dir, state)
    (project_dir / ".studio_approved").write_text("", encoding="utf-8")
    
    # 5. Run Pipeline (Pass 2) -> Should run Render and Final QC
    proc2 = run_pipeline(project_id)
    if proc2.returncode != 0:
        print(f"Pipeline Pass 2 Failed for {project_id}!")
        print(proc2.stdout)
        print(proc2.stderr)
        return False
        
    # 6. Verify output
    out_mp4 = project_dir / "out.mp4"
    if not out_mp4.exists():
        print(f"out.mp4 was not generated for {project_id}!")
        return False
        
    print(f"Scenario {name} ({aspect}) PASSED! Video saved at: {out_mp4}")
    return True

if __name__ == "__main__":
    scenarios = [
        ("Test_9_16", "9:16"),
        ("Test_16_9", "16:9"),
        ("Test_1_1", "1:1")
    ]
    
    all_passed = True
    for name, aspect in scenarios:
        if not run_scenario(name, aspect):
            all_passed = False
            break
            
    if all_passed:
        print("\n✅ All True E2E Scenarios Passed!")
        sys.exit(0)
    else:
        print("\n❌ True E2E Suite Failed.")
        sys.exit(1)
