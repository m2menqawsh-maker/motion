# -*- coding: utf-8 -*-
"""probe_qc.py — يولد تقرير فحص المشاهد
Usage: python probe_qc.py <project_dir> <comp_id>"""
import json, sys, os, subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from pipeline_guard import PipelineGuard, GuardViolation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

proj_dir = Path(sys.argv[1]).resolve()
comp_id = sys.argv[2]
bp_path = proj_dir / "05_blueprint.json"
build_dir = proj_dir / "06_build"
probe_dir = proj_dir / "03_probe_qc"

if not bp_path.exists():
    print("❌ لم نجد 05_blueprint.json")
    sys.exit(1)

if not build_dir.exists():
    print("❌ لم نجد مجلد 06_build. شغّل materialize_project.py أولاً.")
    sys.exit(1)

probe_dir.mkdir(parents=True, exist_ok=True)

bp = json.loads(bp_path.read_text(encoding="utf-8"))
fps = bp.get("meta", {}).get("fps", 30)

# Extract critical moments (in seconds)
critical_secs = {0.0} # Always first frame

for sec in bp.get("timeline", []):
    s = sec.get("sec", 0)
    critical_secs.add(float(s))
    
    for e in sec.get("elements", []):
        # Captions or text
        if e.get("kind") in ["caption", "text"]:
            critical_secs.add(float(e.get("start_sec", s)) + 0.5) # A bit after it appears
            
        # Peak motion (midpoint of duration)
        if "motion" in e and e.get("motion", {}).get("duration_ms"):
            duration_s = e["motion"]["duration_ms"] / 1000.0
            peak = float(e.get("start_sec", s)) + duration_s
            critical_secs.add(peak)

# Add last frame
max_sec = max([e.get("end_sec", 0) for sec in bp.get("timeline", []) for e in sec.get("elements", [])] or [0])
if max_sec > 0:
    critical_secs.add(float(max_sec) - 0.1)

# Convert to frames
critical_frames = sorted(list({int(round(s * fps)) for s in critical_secs}))

print(f"🎬 جاري فحص {len(critical_frames)} لقطات مهمة لفحص الجودة...")

rendered_files = []
# Run remotion still for each frame
for i, f in enumerate(critical_frames):
    out_file = probe_dir / f"probe_{i:02d}_f{f}.png"
    # Execute npx remotion still
    cmd = [
        "npx", "remotion", "still", "src/index.ts", comp_id, 
        str(out_file.absolute()), 
        f"--frame={f}", 
        "--timeout=120000"
    ]
    print(f"📸 توليد اللقطة {i:02d} (إطار {f})...")
    res = subprocess.run(cmd, cwd=str(build_dir), shell=True)
    if res.returncode != 0:
        print(f"❌ فشل توليد اللقطة {i:02d}")
    else:
        rendered_files.append(str(out_file.absolute()))

# Create contact sheet
contact_sheet_sh = Path(__file__).resolve().parent / "verify" / "contact-sheet.sh"
out_sheet = probe_dir / "contact_sheet.png"

if rendered_files and contact_sheet_sh.exists():
    print("🎞️ إنشاء Contact Sheet...")
    # Bash script might need bash executable on Windows
    sh_cmd = ["bash", str(contact_sheet_sh), str(out_sheet)] + rendered_files
    subprocess.run(sh_cmd, shell=True)

# Generate pending report template for the agent
report = {
    "status": "pending",
    "probes": [
        {"frame": f, "file": f"probe_{i:02d}_f{f}.png", "check": "يرجى الفحص", "status": "pending"}
        for i, f in enumerate(critical_frames)
    ],
    "contact_sheet": "contact_sheet.png",
    "errors": [
        "تعليمات: افتح صور contact_sheet.png وافحصها. status يجب pass فقط إذا كان كل شيء سليم: نصوص مقروءة، أبعاد صحيحة، ألوان سليمة."
    ],
    "timestamp": datetime.now().isoformat()
}

import inspect

# فحص: هل تم استدعاء السكريبت من سطر الأوامر أم من كود آخر؟
try:
    caller = inspect.stack()[1]
    if "pipeline_guard" in caller.filename or "write_to_file" in str(caller):
        print("🛑 [SECURITY] محاولة كتابة تقرير QC من مصدر غير مصرح به")
        sys.exit(1)
except IndexError:
    pass # السكريبت شُغل مباشرة

report_path = proj_dir / "probe_qc_report.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

# الختم الرقمي — يمنع أي تعديل يدوي لاحق
PipelineGuard.seal_report(report_path)
print(f"🔏 تم ختم التقرير ببصمة رقمية — أي تعديل يدوي سيُكتشف")

# إنشاء ملف الفتح فقط إذا نجح الفحص
if report.get("status") == "pass":
    unlock_file = proj_dir / ".studio_unlocked"
    unlock_file.write_text(f"unlocked_at={datetime.now().isoformat()}", encoding="utf-8")
    print(f"🔓 تم إنشاء {unlock_file}")
