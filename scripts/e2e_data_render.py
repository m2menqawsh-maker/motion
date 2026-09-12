#!/usr/bin/env python3
"""
E2E Pipeline Test — المشروع المرجعي
يختبر كامل خط الإنتاج من scaffold إلى render.

استخدام:
  python scripts/e2e_data_render.py

المخرج:
  ✅ E2E PASS + mp4 file path
  ❌ E2E FAIL + error message
"""
import subprocess, json, shutil, sys
from pathlib import Path

def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"❌ فشل: {cmd}")
        print(result.stderr)
        sys.exit(1)
    return result

def main():
    # 1. scaffold مشروع جديد
    result = run(["python", "scripts/scaffold_project.py", "--name", "E2E Demo", "--aspect", "9:16", "--fps", "30", "--language", "ar"])
    project_id = result.stdout.strip()
    project_dir = Path(f"projects/{project_id}")
    
    # 2. نسخ الأصول من demo_brand
    shutil.copytree("projects/demo_brand/assets/ready", project_dir / "assets/ready", dirs_exist_ok=True)
    shutil.copy("projects/demo_brand/brand.json", project_dir / "brand.json")
    shutil.copy("projects/demo_brand/blueprint.json", project_dir / "blueprint.json")
    shutil.copy("projects/demo_brand/overrides.json", project_dir / "overrides.json")
    shutil.copy("projects/demo_brand/manifest.json", project_dir / "manifest.json")
    shutil.copy("projects/demo_brand/04_timings.json", project_dir / "04_timings.json")
    
    # 3. تحديث project_id في كل الملفات
    for f in ["blueprint.json", "overrides.json", "manifest.json"]:
        data = json.loads((project_dir / f).read_text(encoding="utf-8"))
        data["project_id"] = project_id
        (project_dir / f).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # 4. تشغيل stage_gate.py (happy path)
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "0"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "0"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "1", "e2e_test"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "1"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "1"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "2", "e2e_test"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "2"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "finish", "2"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "approve", "3", "e2e_test"])
    run(["python", "scripts/gates/stage_gate.py", str(project_dir), "start", "3"])
    
    # 5. تشغيل dev_render_blueprint.ts
    out_path = Path("out") / f"{project_id}.mp4"
    npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
    run([npx_cmd, "tsx", "scripts/dev_render_blueprint.ts", str(project_dir), str(out_path)])
    
    # 6. التحقق من حجم الملف
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"✅ E2E PASS — {out_path} ({out_path.stat().st_size} bytes)")
        return 0
    else:
        print(f"❌ E2E FAIL — {out_path} غير موجود أو فارغ")
        return 1

if __name__ == "__main__":
    sys.exit(main())
