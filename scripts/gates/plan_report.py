import os
import sys
import json
from pathlib import Path

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_report(project_dir: str, out_file: str):
    p = Path(project_dir)
    out_path = p / out_file if out_file else p / "master_plan.md"
    
    project = _load_json(p / "project.json")
    blueprint = _load_json(p / "blueprint.json")
    brand = _load_json(p / "brand.json")
    manifest = _load_json(p / "manifest.json")
    state = _load_json(p / "state.json")
    
    lines = []
    lines.append("# Master Plan\n")
    
    # 1. Metadata Table
    lines.append("## Project Metadata\n")
    lines.append("| ID | Aspect Ratio | FPS | Language | Brand |")
    lines.append("|---|---|---|---|---|")
    pid = project.get("id", "N/A")
    aspect = project.get("aspectRatio", "N/A")
    fps = project.get("fps", "N/A")
    lang = project.get("language", "N/A")
    bname = brand.get("brandName", "N/A")
    lines.append(f"| {pid} | {aspect} | {fps} | {lang} | {bname} |\n")
    
    # 2. Brand Summary
    lines.append("## Brand Summary\n")
    if brand:
        colors = brand.get("colors", {})
        fonts = brand.get("fonts", {})
        lines.append(f"- **Primary Color**: {colors.get('primary')}")
        lines.append(f"- **Accent Color**: {colors.get('accent')}")
        lines.append(f"- **Background**: {colors.get('background')}")
        lines.append(f"- **Text Color**: {colors.get('text')}")
        lines.append(f"- **Display Font**: {fonts.get('display')}")
        lines.append(f"- **Body Font**: {fonts.get('body')}\n")
    else:
        lines.append("*No brand information available.*\n")
        
    # 3. Scenes Table
    lines.append("## Scenes\n")
    lines.append("| Scene | Template | Frames | Seconds | Text Extract |")
    lines.append("|---|---|---|---|---|")
    scenes = blueprint.get("scenes", [])
    if scenes:
        for i, s in enumerate(scenes):
            template = s.get("template", "N/A")
            start = s.get("startFrame", 0)
            dur = s.get("durationFrames", 0)
            end = start + dur
            fps_val = project.get("fps", 30)
            secs = f"{dur / fps_val:.1f}s" if fps_val else "N/A"
            
            # extract text snippet
            props = s.get("props", {})
            text_extract = str(props.get("title", props.get("text", "")))[:30]
            if not text_extract:
                text_extract = "-"
            lines.append(f"| {i+1} | {template} | {start} - {end} | {secs} | {text_extract} |")
    else:
        lines.append("| - | - | - | - | - |")
    lines.append("\n")
    
    # 4. Assets Table
    lines.append("## Assets\n")
    lines.append("| ID | Type | Status (Approved) | Path |")
    lines.append("|---|---|---|---|")
    assets = manifest.get("assets", [])
    if assets:
        for a in assets:
            aid = a.get("id", "N/A")
            atype = a.get("type", "N/A")
            appr = "✅ Yes" if a.get("approved") else "❌ No"
            filepath = a.get("filepath", "N/A")
            lines.append(f"| {aid} | {atype} | {appr} | {filepath} |")
    else:
        lines.append("| - | - | - | - |")
    lines.append("\n")
        
    # 5. Gates Status
    lines.append("## Gates Status\n")
    lines.append("| Gate | Status | Approved By |")
    lines.append("|---|---|---|")
    gates = state.get("gates", {})
    for g in ["gate_1", "gate_2", "gate_3"]:
        gv = gates.get(g, {})
        if isinstance(gv, dict):
            status = gv.get("status", "locked")
            by = gv.get("approved_by", "-")
        else:
            status = gv
            by = "-"
        lines.append(f"| {g} | {status} | {by} |")
    lines.append("\n")
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
        
    print(f"✅ تم توليد {out_path} بنجاح.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plan_report.py <project_dir> [out_file]")
        sys.exit(1)
        
    pdir = sys.argv[1]
    ofile = sys.argv[2] if len(sys.argv) > 2 else "master_plan.md"
    generate_report(pdir, ofile)
