# -*- coding: utf-8 -*-
"""stage_gate.py — بوابات الخط المرحلي: ترفض بدء مرحلة بدون مكتملات سابقتها.
Usage: python stage_gate.py <project_dir> --check <stage> | --report"""
import json, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ORDER = ["00_answers", "01_plan", "02_media_build", "03_probe_qc", "04_studio", "05_render"]
FILES = {
 "00_answers": ["00_answers.md"],
 "01_plan": ["01_plan.md", "01_plan.approved"],
 "02_media_build": [
     "02_asset_manifest.json", "02b_assets_reviewed.approved",
     "03_preprocess_report.json", "04_timings.json",
     "05_blueprint.json", "05_blueprint_human.md", "05_blueprint.approved",
     "06_build/src/media_map.json"
 ],
 "03_probe_qc": ["probe_qc_report.json", "contact_sheet.png", ".studio_unlocked"],
 "04_studio": [],
 "05_render": ["08_qc/ffmpeg_qc_report.json", "08_qc/broll_layout_qc_report.json"]
}
fails = []
def exists(proj, name):
    return (proj / name).exists()

def content_checks(proj, stage):
    if stage == "01_plan":
        if (proj / "01_plan.md").exists():
            txt = (proj / "01_plan.md").read_text(encoding="utf-8")
            personas = {"Cinematic", "Energetic", "Playful", "Technical"}
            has_persona = any(p.lower() in txt.lower() for p in personas)
            has_signature = "signature" in txt.lower()
            if not (has_persona and has_signature):
                fails.append("مرحلة 01_plan: يجب أن تحتوي 01_plan.md على اسم شخصية من الأربع (Cinematic, Energetic, Playful, Technical) + كلمة 'signature'")
            import re
            match = re.search(r"motion_taste_citation\s*[:=-]\s*([\w-]+\.md):(\d+)", txt, re.IGNORECASE)
            if match:
                fname, line_str = match.groups()
                line_num = int(line_str)
                target_file = Path(__file__).resolve().parent.parent / "reference" / "motion-taste" / "director" / fname
                if target_file.exists():
                    lines_count = len(target_file.read_text(encoding="utf-8").splitlines())
                    if not (1 <= line_num <= lines_count):
                        fails.append(f"مرحلة 01_plan: السطر {line_num} غير موجود في {fname} (الملف يحتوي {lines_count} أسطر فقط)")
                else:
                    fails.append(f"مرحلة 01_plan: الملف المقتبس {fname} غير موجود في مجلد الذوق")
            else:
                fails.append("مرحلة 01_plan: مفقود حقل motion_taste_citation أو لا يطابق النمط 'اسم_ملف.md:رقم_السطر'")
    if stage == "02_media_build":
        if (proj / "02_asset_manifest.json").exists():
            import subprocess
            gate_script = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "asset_gate.py"
            if not gate_script.exists():
                gate_script = Path(__file__).resolve().parent / "asset_gate.py" # try local scripts dir
            if not gate_script.exists():
                gate_script = Path("scripts/asset_gate.py")
            gate_res = subprocess.run(
                [sys.executable, str(gate_script), str(proj / "02_asset_manifest.json")],
                capture_output=True, text=True, encoding="utf-8"
            )
            if gate_res.returncode != 0:
                fails.append(f"asset_gate.py مرفوض: {gate_res.stdout.strip()}")

            man = json.loads((proj / "02_asset_manifest.json").read_text(encoding="utf-8"))
            for a in man.get("assets", []):
                pr = " ".join(a.get("processing", [])); t = a.get("type")
                if t == "video" and "video-tools-mcp" not in pr and "all_intra" not in pr: fails.append(f"asset {a.get('asset_id')}: معالجة فيديو بدون video-tools-mcp/all_intra")
                if t == "audio" and "audio-tools-mcp" not in pr: fails.append(f"asset {a.get('asset_id')}: معالجة صوت بدون audio-tools-mcp")
                if t == "image" and "image-tools-mcp" not in pr: fails.append(f"asset {a.get('asset_id')}: معالجة صورة بدون image-tools-mcp")
                if not a.get("source"): fails.append(f"asset {a.get('asset_id')}: بدون source")
        if (proj / "03_preprocess_report.json").exists():
            rep = json.loads((proj / "03_preprocess_report.json").read_text(encoding="utf-8"))
            for v in rep.get("videos", []):
                if v.get("keyframe_mode") != "all_intra" or v.get("gop") != 1:
                    fails.append(f"video {v.get('asset_id')}: ليس All-Intra GOP=1 — قانون المرحلة 3")
                if v.get("verified_by") not in ("get_files_info", "ffprobe"):
                    fails.append(f"video {v.get('asset_id')}: GOP غير موثق بـ get_files_info/ffprobe")
        if (proj / "05_blueprint.json").exists():
            bp5 = json.loads((proj / "05_blueprint.json").read_text(encoding="utf-8"))
            for sec in bp5.get("timeline", []):
                for c in sec.get("sfx", []):
                    miss = [k for k in ("asset", "at_ms", "tone", "volume_db", "processing") if k not in c]
                    if miss: fails.append(f"مرحلة 5: cue في الثانية {sec.get('sec')} ناقص {miss}")
    if stage == "03_probe_qc":
        if (proj / "probe_qc_report.json").exists():
            try:
                rep = json.loads((proj / "probe_qc_report.json").read_text(encoding="utf-8"))
                if rep.get("status") != "pass":
                    fails.append(f"مرحلة 03_probe_qc: حالة التقرير ليست pass ({rep.get('status')})")
            except Exception as e:
                fails.append(f"مرحلة 03_probe_qc: خطأ في قراءة probe_qc_report.json: {e}")
        else:
            fails.append("مرحلة 03_probe_qc: تقرير الفحص البصري مفقود. (يجب تشغيل probe_qc.py والوكيل يقوم بالفحص).")
    if stage == "05_render":
        qc_files = ["ffmpeg_qc_report.json", "broll_layout_qc_report.json"]
        for qf in qc_files:
            q_path = proj / "08_qc" / qf
            if not q_path.exists():
                fails.append(f"مرحلة 05_render: تقرير الجودة {qf} مفقود تماماً!")
            else:
                try:
                    rep = json.loads(q_path.read_text(encoding="utf-8"))
                    if not rep:
                        fails.append(f"مرحلة 05_render: التقرير {qf} فارغ!")
                    elif rep.get("status") not in ("passed", "succeeded", "passed_with_warnings", "warning"):
                        fails.append(f"مرحلة 05_render: التقرير {qf} لم يجتز الفحص بنجاح. (الحالة: {rep.get('status')})")
                except Exception as e:
                    fails.append(f"مرحلة 05_render: خطأ في قراءة {qf}: {e}")

    if stage in ["04_studio", "05_render"]:
        import subprocess
        code_gate = Path(__file__).resolve().parent / "code_template_gate.py"
        if code_gate.exists():
            res = subprocess.run([sys.executable, str(code_gate), str(proj)], capture_output=True, text=True, encoding="utf-8")
            if res.returncode != 0:
                fails.append(f"مرحلة {stage}: code_template_gate.py مرفوض (يرجى إصلاح الكود باستخدام القوالب):\n{res.stdout.strip()}")

    if stage in ["01_plan", "05_render"]:
        import subprocess
        taste_script = Path(__file__).resolve().parent / "taste_gate.py"
        if taste_script.exists():
            scenes_dir = proj / "scenes"
            if scenes_dir.exists():
                for scene_file in scenes_dir.glob("*_plan.md"):
                    res = subprocess.run([sys.executable, str(taste_script), str(scene_file)], capture_output=True, text=True, encoding="utf-8")
                    if res.returncode != 0:
                        fails.append(f"taste_gate.py فشل في {scene_file.name}:\n{res.stdout.strip()}")

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(0)

proj = Path(sys.argv[1])
if "--report" in sys.argv:
    for s in ORDER:
        print(("✅" if all(exists(proj, f) for f in FILES[s]) else "⏳"), s)
    sys.exit(0)

if "--check" not in sys.argv:
    print("يرجى استخدام --check <stage>")
    sys.exit(1)

target = sys.argv[sys.argv.index("--check") + 1]
if target not in ORDER:
    print(f"المرحلة {target} غير موجودة في القائمة: {ORDER}")
    sys.exit(1)

for s in ORDER[:ORDER.index(target)]:
    for f in FILES[s]:
        if not exists(proj, f): fails.append(f"مرحلة {s}: ناقص {f}")
    content_checks(proj, s)

if fails:
    print("❌ STAGE GATE DENIED:"); [print(" -", x) for x in fails]; sys.exit(1)
print(f"✅ STAGE GATE OK: يمكن بدء {target}")
