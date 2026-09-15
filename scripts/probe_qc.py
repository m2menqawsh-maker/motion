# -*- coding: utf-8 -*-
"""probe_qc.py — يولد تقرير فحص المشاهد
Usage: python probe_qc.py <project_dir> <comp_id>"""
import json, sys, os, subprocess, hashlib, secrets
import concurrent.futures
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from core.pipeline import UnifiedPipeline as PipelineGuard
from core.gates import GateViolation as GuardViolation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def get_or_create_salt() -> bytes:
    salt_file = Path(".agents/secrets/.qc_salt")
    if not salt_file.exists():
        salt_file.parent.mkdir(parents=True, exist_ok=True)
        salt_file.write_bytes(secrets.token_bytes(32))
    return salt_file.read_bytes()

def verify_seal(report_path: Path) -> bool:
    """تحقق من مطابقة البصمة الرقمية للتقرير لمنع التعديل اليدوي والتزوير"""
    if isinstance(report_path, str):
        report_path = Path(report_path)
    seal_file = report_path.with_suffix(report_path.suffix + ".seal")
    if not seal_file.exists():
        print("🛑 [SECURITY] ملف الختم الرقمي (.seal) لتقرير Probe-QC مفقود!")
        return False
    if not report_path.exists():
        print("🛑 [SECURITY] ملف تقرير Probe-QC غير موجود!")
        return False
    expected = seal_file.read_text(encoding="utf-8").strip()
    
    salt = get_or_create_salt()
    data = report_path.read_bytes() + salt
    actual = hashlib.sha256(data).hexdigest()
    
    if expected != actual:
        print("🛑 [SECURITY] تقرير Probe-QC تم تعديله يدوياً (البصمة الرقمية غير متطابقة - تقرير مزوّر)")
        return False
    return True

if len(sys.argv) >= 2 and sys.argv[1] == "--verify":
    target_dir = Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
    report_file = target_dir / "probe_qc_report.json" if target_dir.is_dir() else target_dir
    if verify_seal(report_file):
        print("✅ تقرير Probe-QC أصلي وموثق بالختم الرقمي")
        sys.exit(0)
    else:
        print("🛑 تقرير Probe-QC تم تعديله يدوياً")
        sys.exit(1)

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

target_arg = Path(sys.argv[1])
if (Path("projects") / target_arg).exists():
    proj_dir = (Path("projects") / target_arg).resolve()
elif target_arg.exists():
    proj_dir = target_arg.resolve()
else:
    proj_dir = target_arg.resolve()

comp_id = sys.argv[2] if len(sys.argv) > 2 else "BlueprintVideo"
bp_path = proj_dir / "05_blueprint.json"
build_dir = proj_dir / "06_build"
probe_dir = proj_dir / "03_probe_qc"

if not bp_path.exists():
    print("❌ لم نجد 05_blueprint.json")
    sys.exit(1)

probe_dir.mkdir(parents=True, exist_ok=True)

# تحضير render_props.json للمحرك المركزي
def safe_load(name, default):
    p = proj_dir / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

combined_props = {
    "projectData": {
        "project": safe_load("project.json", {"fps": 30, "title": "Video"}),
        "blueprint": json.loads(bp_path.read_text(encoding="utf-8")),
        "brand": safe_load("brand.json", {"colors": {}, "fonts": {}}),
        "overrides": safe_load("overrides.json", {"scenes": {}})
    }
}
props_file = proj_dir / "render_props.json"
props_file.write_text(json.dumps(combined_props, ensure_ascii=False), encoding="utf-8")
props_file_abs = props_file.resolve()

workspace_root = Path.cwd().resolve()
engine_dir = workspace_root / "remotion-app"

use_engine = False
if not (build_dir / "src" / "index.ts").exists() and (engine_dir / "src" / "index.ts").exists():
    exec_cwd = str(engine_dir)
    use_engine = True
else:
    if not build_dir.exists():
        print("❌ لم نجد مجلد 06_build. شغّل materialize_project.py أولاً.")
        sys.exit(1)
    exec_cwd = str(build_dir)

bp = json.loads(bp_path.read_text(encoding="utf-8"))
fps = bp.get("meta", {}).get("fps", 30)

# Extract critical moments (in seconds)
critical_secs = {0.0} # Always first frame

for sec in bp.get("timeline", []):
    s = sec.get("sec", 0)
    # Capture slightly after start (1.0s) to allow entrance animations to finish, 
    # ensuring the component is fully visible in the contact sheet.
    critical_secs.add(float(s) + 1.0)
    
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

# Convert to frames and clamp within valid composition range
total_duration_frames = sum(s.get("durationFrames", 0) for s in bp.get("scenes", []))
if not total_duration_frames:
    total_duration_frames = int(round(fps * bp.get("meta", {}).get("duration_sec", 18)))
max_allowed_frame = max(0, total_duration_frames - 1)

critical_frames = sorted(list({min(max_allowed_frame, max(0, int(round(s * fps)))) for s in critical_secs}))

print(f"🎬 جاري فحص {len(critical_frames)} لقطات مهمة لفحص الجودة...")

rendered_files = []

def render_frame(args):
    i, f = args
    out_file = probe_dir / f"probe_{i:02d}_f{f}.png"
    # Execute npx remotion still
    cmd = [
        "npx", "remotion", "still", "src/index.ts", comp_id, 
        str(out_file.absolute()), 
        f"--frame={f}", 
        "--timeout=120000"
    ]
    if use_engine:
        cmd.extend(["--props", str(props_file_abs)])
    print(f"📸 توليد اللقطة {i:02d} (إطار {f})...")
    res = subprocess.run(cmd, cwd=exec_cwd, shell=True, capture_output=True)
    if res.returncode != 0:
        print(f"❌ فشل توليد اللقطة {i:02d}")
        return None
    else:
        return str(out_file.absolute())

# Run remotion still for each frame in parallel (max 5 concurrent browsers)
print("🚀 تشغيل المعالجة المتوازية (Multi-threading) لتسريع الفحص...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(render_frame, enumerate(critical_frames))
    for res in results:
        if res:
            rendered_files.append(res)

# Create contact sheet
contact_sheet_sh = Path(__file__).resolve().parent / "verify" / "contact-sheet.sh"
out_sheet = probe_dir / "contact_sheet.png"

if rendered_files:
    print("🎞️ إنشاء Contact Sheet...")
    # Sample up to 6 key frames across timeline for contact sheet
    sampled = rendered_files if len(rendered_files) <= 6 else [
        rendered_files[0],
        rendered_files[len(rendered_files) // 5],
        rendered_files[2 * len(rendered_files) // 5],
        rendered_files[3 * len(rendered_files) // 5],
        rendered_files[4 * len(rendered_files) // 5],
        rendered_files[-1]
    ]
    ff_cmd = ["ffmpeg", "-y"]
    for f in sampled:
        ff_cmd.extend(["-i", f])
    ff_cmd.extend(["-filter_complex", f"hstack=inputs={len(sampled)}", "-loglevel", "error", str(out_sheet)])
    res_cs = subprocess.run(ff_cmd)
    if res_cs.returncode == 0 and out_sheet.exists():
        import shutil
        shutil.copy2(str(out_sheet), str(proj_dir / "contact_sheet.png"))
        print(f"  ✓ contact sheet ({len(sampled)} frame(s)) → {out_sheet}")

# تقييم حالة الفحص بناءً على اكتمال وسلامة جميع اللقطات
is_passed = (len(rendered_files) == len(critical_frames)) and (len(critical_frames) > 0)
report = {
    "status": "pass" if is_passed else "fail",
    "probes": [
        {
            "frame": f,
            "file": f"probe_{i:02d}_f{f}.png",
            "check": "سليم ومكتمل" if str((probe_dir / f"probe_{i:02d}_f{f}.png").absolute()) in rendered_files else "فشل الرندر",
            "status": "pass" if str((probe_dir / f"probe_{i:02d}_f{f}.png").absolute()) in rendered_files else "fail"
        }
        for i, f in enumerate(critical_frames)
    ],
    "contact_sheet": "contact_sheet.png",
    "errors": [] if is_passed else ["فشل رندر بعض الإطارات الحرجة."],
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

# الختم الرقمي — يمنع أي تعديل يدوي لاحق عبر حفظ بصمة SHA-256 + Salt
seal_file = report_path.with_suffix(report_path.suffix + ".seal")
salt = get_or_create_salt()
data = report_path.read_bytes() + salt
checksum = hashlib.sha256(data).hexdigest()
seal_file.write_text(checksum, encoding="utf-8")
print(f"🔏 تم ختم التقرير ببصمة رقمية معماة SHA-256 ({checksum[:12]}...) — أي محاولة تزوير ستفشل.")

# التحقق من الختم قبل السماح بأي إجراء
if not verify_seal(report_path):
    print("🛑 تقرير Probe-QC تم تعديله يدوياً")
    sys.exit(1)

# إنشاء ملف الفتح فقط إذا نجح الفحص وكان الختم سليماً
if report.get("status") == "pass":
    unlock_file = proj_dir / ".studio_unlocked"
    unlock_file.write_text(f"unlocked_at={datetime.now().isoformat()}", encoding="utf-8")
    print(f"🔓 تم إنشاء {unlock_file}")
