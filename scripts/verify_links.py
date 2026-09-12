# -*- coding: utf-8 -*-
"""verify_links.py — ????? ?? ?? ???? ????? ???? ?? ??????? ???????? ????? ??? ?????."""
import re, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent
missing, checked = [], 0
targets = [DST / "SKILL.md", DST / "ROUTER.md"] + sorted((DST / "reference").rglob("INDEX.md"))

search_dirs = [
    DST,
    DST / "reference",
    DST / "reference" / "ground-truth",
    DST / "reference" / "cinematic",
    DST / "reference" / "patterns",
    DST / "reference" / "motion-taste",
    DST / "reference" / "ad-spine",
    DST / "reference" / "remotion",
    DST / "reference" / "remotion" / "markup",
    DST / "reference" / "remotion" / "captions",
    DST / "reference" / "remotion" / "create",
    DST / "reference" / "remotion" / "render",
    DST / "reference" / "remotion" / "multimedia",
    DST / "reference" / "remotion" / "studio",
    DST / "reference" / "motion-taste" / "director",
    DST / "reference" / "motion-taste" / "patterns",
    DST / "reference" / "motion-taste" / "reference",
    DST / "reference" / "ad-spine" / "ad-creative",
    DST / "reference" / "ad-spine" / "launch",
    DST / "reference" / "ad-spine" / "testimonial",
    DST / "tools",
    DST / "scripts",
    DST / "scripts" / "verify",
    DST / "templates",
    DST / "recipes",
]

IGNORED = {
    "Blueprint.json", "blueprint.json", "blueprint_human.md", "templates/x.tsx", "x.tsx",
    "00_answers.md", "01_plan.md", "02_asset_manifest.json", "03_preprocess_report.json", "02_initial_assets.json", "scene_N_plan.md", "sceneN_qc_report.json",
    "04_timings.json", "08_qc_report.json", "media_map.json", "05_blueprint.json", "probe_qc_report.json"
}

for md in targets:
    if md.name == "SKILL.md":
        # Handle the fact that SKILL.md is inside skills/super-video-maker/
        # Check if the path actually exists, if not maybe we are iterating over a bad path
        pass
    try:
        text = md.read_text(encoding="utf-8")
    except FileNotFoundError:
        continue
    base = md.parent
    for m in re.finditer(r"(?:`|[\s|(\[])([a-zA-Z0-9_/\\-]+\.(?:md|py|tsx|ts|sh|json))(?:`|[\s|),\]])", text):
        raw_p = m.group(1).strip()
        if raw_p in IGNORED or Path(raw_p).name in IGNORED:
            continue
        p = raw_p.replace("/", "\\")
        name = Path(p).name
        checked += 1
        found = (base / p).exists() or (DST / p).exists() or any((d / p).exists() or (d / name).exists() for d in search_dirs)
        if not found:
            missing.append(f"{md.name} -> {raw_p}")

if missing:
    print("? LINKS FAIL:")
    for x in missing:
        print(" -", x)
    sys.exit(1)
print(f"? LINKS PASS: {checked} reference(s) verified")
