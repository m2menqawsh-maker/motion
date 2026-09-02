# -*- coding: utf-8 -*-
"""audit_skill.py — ????? ????? ???????: ????? ?????? ????? ?????
???? AUDIT_REPORT.md ?exit 1 ??? ?? ???."""
import re, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent
R = DST / "references" / "deep"
SKIP = {"node_modules", ".git", "__pycache__", ".venv"}
allf = [p for p in sorted(DST.rglob("*")) if p.is_file() and not (SKIP & set(p.parts))]
stem_map = {p.stem: p.resolve() for p in allf}
name_map = {p.name: p.resolve() for p in allf}

# Legacy alias
if (R / "legacy" / "REFERENCE_legacy.md").exists():
    name_map["REFERENCE.md"] = (R / "legacy" / "REFERENCE_legacy.md").resolve()

# Dynamic or illustrative placeholders in docs
IGNORED_TOKENS = {
    "${row.id}.json", "plan.json", "character_card.json", "job_state.json",
    "openai_image_tool.py", "content.ts", "input.mp4", "output.mp4",
    "storyboard.json", "chunks.json", "overlay_schedule.json", "receipts.json",
    "motionUtils.ts", "config.ts", "timestamps.json", "FeatureNameMockup.tsx",
    "DistribbExplainer.tsx", "generate_voiceover.py", "broll_manifest.claude-seo-tutorial.json",
    "build_master_captions_v2.py", "build_cards.py", "render_broll.py",
    "render_kenburns_broll.py", "compose_master_v4.py", "build_disclosure_badge.py",
    "whisper_transcribe_v2.py", "build_outro_card.py", "build_proof_kenburns.py",
    "compose_master_v2.py", "render_v4_photos.py", "build_v4_kenburns.py",
    "variant_matrix.json", "understand_ad_video.py", "quality_gate_report.json",
    "character_card.json", "pexels_search.py", "pixabay_search.py",
    "tailwind.config.js", "tailwind.config.ts", "templates/x.tsx", "x.tsx",
    "00_answers.md", "01_plan.md", "02_asset_manifest.json", "03_preprocess_report.json",
    "04_timings.json", "08_qc_report.json", "media_map.json",
    "probe_qc_report.json", "%APPDATA%/Claude/claude_desktop_config.json",
    "references/plain-register-reference.whisper.json", "plain-register-reference.whisper.json",
    "05_blueprint.json", "02_initial_assets.json", "scene_N_plan.md", "sceneN_qc_report.json"
}

IGNORED_PREFIXES = (
    "src/", "packages/", ".claude/", "assets/character/", "reviews/",
    "public/", "components/", "remotion-videos/"
)

def resolve(base, tok):
    tok_clean = tok.strip()
    if (tok_clean in IGNORED_TOKENS or
        tok_clean.startswith("${") or
        tok_clean.startswith(IGNORED_PREFIXES) or
        " " in tok_clean or
        "{" in tok_clean or
        "*" in tok_clean):
        return True
    
    candidates = [
        base / tok_clean,
        base / tok_clean.replace("references/", ""),
        base / tok_clean.replace("scripts/", ""),
        DST / tok_clean,
        R / tok_clean,
        R / "ground-truth" / tok_clean,
        R / "cinematic" / tok_clean,
        R / "patterns" / tok_clean,
        R / "motion-taste" / tok_clean,
        R / "ad-spine" / tok_clean,
        R / "remotion" / tok_clean,
        R / "legacy" / tok_clean,
        DST / "cinematic-engine" / tok_clean,
        DST / "tools" / tok_clean,
        DST / "templates" / tok_clean,
        DST / "recipes" / tok_clean,
        DST / "commands" / tok_clean,
        DST / "workflows" / tok_clean,
        DST / "scripts" / "verify" / tok_clean,
    ]
    for x in candidates:
        if x.exists(): return x.resolve()
    
    if "ad-spine" in base.parts:
        for x in (R / "ad-spine").rglob(Path(tok_clean).name):
            if x.exists(): return x.resolve()
            
    if tok_clean in name_map:
        return name_map[tok_clean]
        
    pname = Path(tok_clean).name
    if pname in name_map:
        return name_map[pname]
        
    return stem_map.get(tok_clean.split(".")[0])

# ???? ??????: ????? ??????? + ??????? + ?????? cinematic (????? ???????? ??????? ??? ?????)
scope = [f for f in allf if f.suffix == ".md"
         or f.is_relative_to(DST/"templates") or f.is_relative_to(DST/"cinematic-engine")]
referenced, broken = set(), []
tok_re = re.compile(r"`([^`\n|<>*]+)`")

for md in [f for f in allf if f.suffix == ".md"]:
    for m in tok_re.finditer(md.read_text(encoding="utf-8")):
        tok = m.group(1).strip()
        t = resolve(md.parent, tok)
        if t is True:
            continue
        elif t:
            referenced.add(t)
        elif tok.endswith((".md", ".py", ".tsx", ".ts", ".sh", ".json")):
            broken.append(f"{md.relative_to(DST)} -> {tok}")

ENTRY = {
    "SKILL.md", "ROUTER.md", "README.md", "AUDIT_REPORT.md", "package.json",
    "requirements.txt", ".env.example", "index.ts", "LOCAL.md",
    "ARCHITECTURE.md", "CHANGELOG.md", "DISTRIBUTION_CHECKLIST.md",
    "INSTALLATION.md", "INDEX.md", "USAGE.md"
}
orphans = [str(f.relative_to(DST)) for f in scope if f.resolve() not in referenced and f.name not in ENTRY]

rep, ok = [], True
def gate(t, c, d=""):
    global ok
    ok &= bool(c); rep.append(f"{'?' if c else '?'} {t}" + (f" — {d}" if d else ""))

gate("?? ????? ????? ?????", not orphans, "? ".join(orphans[:12]))
gate("?? ????? ??????", not broken, "? ".join(broken[:12]))
sk = (DST/"skills"/"super-video-maker"/"SKILL.md").read_text(encoding="utf-8"); rt = (DST/"references"/"ROUTER.md").read_text(encoding="utf-8")
gate("??????? ???51 ??????? ???????", (R/"legacy"/"SKILL_51_RULES.md").exists() and "SKILL_51_RULES" in sk)
gate("SKILL ???? ??????? ?????????", "??????? ????????? ???????" in sk)
gate("ROUTER §9 ?????", "§9 ??? ???????" in rt)
PBS = ["FFMPEG_PLAYBOOK.md","VIDEO_COPY_PLAYBOOK.md","SPOKEN_VO_HUMANIZER.md","HOOK_PLAYBOOK_ARTICLE_SPRINT.md",
       "LIVING_CANVAS_PLAYBOOK.md","TABLETOP_EXPLAINER_PLAYBOOK.md","MOTION_COLLAGE_STYLE.md","HYPERREALISTIC_IMAGE_SOP.md",
       "REVIEW_VIDEO_PLAYBOOK.md","SEEDANCE_AVATAR_ROI.md","REMOTION_VIDEO_GUIDE.md","WORKFLOW_EXAMPLES.md"]
for pb in PBS:
    f = DST / "references" / pb
    if not f.exists(): f = DST / pb
    gate(pb, f.exists() and pb in rt and "??? ??????? ???????" in f.read_text(encoding="utf-8"))
for idx, mk in [("patterns","?? ????????"),("ad-spine","?? ????????"),("cinematic","?? ????????"),("remotion","???? ???????")]:
    gate(f"{idx}/INDEX ????", mk in (R/idx/"INDEX.md").read_text(encoding="utf-8"))
n = len(re.findall(r"\| `[\w-]+` \|", (R/"ground-truth"/"TEMPLATE_INDEX.md").read_text(encoding="utf-8")))
gate("81 ?????? ???????", n == 81, str(n))
gate("18 ???? + schema", len(list((DST/"recipes").glob("*.json"))) == 19)
for s in ["media-sources-mcp","audio-tools-mcp","video-tools-mcp","image-tools-mcp","common-tools-mcp","ffmpeg-mcp-server","Video_Editor_MCP"]:
    gate(f"{s} ?? ROUTER", s in rt)
(DST/"AUDIT_REPORT.md").write_text("# AUDIT_REPORT\n> ????? ????? ?????? audit_skill.py\n\n" + "\n".join(rep)
    + f"\n\n**???????: {'PASS' if ok else 'FAIL'}**\n", encoding="utf-8")
print("\n".join(rep)); print("AUDIT:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
