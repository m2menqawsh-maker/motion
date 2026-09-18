# -*- coding: utf-8 -*-
"""validate_blueprint.py — بوابة عقد الـ Blueprint قبل البناء.
Usage:
  python validate_blueprint.py <blueprint.json>                      # فحص كامل
  python validate_blueprint.py <bp.json> --md <out.md>               # + النسخة البشرية
  python validate_blueprint.py <bp.json> --lock                      # قفل العقد
  python validate_blueprint.py <bp.json> --verify-build <proj_dir>   # الكود المبني == العقد
Exit 0 = PASS."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subprocess
from scripts.security import safe_subprocess
import json, re
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent
GT = DST / "ground-truth"
TEMPLATES = set(re.findall(r"\| `([\w-]+)` \|", (GT / "TEMPLATE_INDEX.md").read_text(encoding="utf-8")) if (GT / "TEMPLATE_INDEX.md").exists() else set())

CATALOG_TYPES = {}
CATALOG_FAMILIES = {}
if (GT / "template_catalog.json").exists():
    for item in json.loads((GT / "template_catalog.json").read_text(encoding="utf-8")):
        # We key by just the template name (e.g. BlurReveal) to match what blueprint has
        CATALOG_TYPES[item["name"]] = item.get("type", "misc")
        CATALOG_FAMILIES[item["name"]] = item.get("family", "unknown")

PERSONA = {
 "Cinematic": (350, 500, 800, {"soft", "deep", "none"}),
 "Energetic": (100, 180, 300, {"punchy", "soft", "whoosh", "none"}),
 "Playful":   (150, 250, 400, {"pop", "soft", "whoosh", "none"}),
 "Technical": (200, 300, 450, {"click", "soft", "none"}),
}
PERSONA_EXACT = {
    "Cinematic": {"duration_min": 350, "duration_max": 600, "easing": "cubic-bezier(0.4,0,0.2,1)", "overshoot": ["0%"]},
    "Energetic": {"duration_min": 100, "duration_max": 250, "easing": "ease-out-expo", "overshoot": ["15%", "30%"]},
    "Playful":   {"duration_min": 150, "duration_max": 300, "easing": "ease-out-back", "overshoot": ["10%", "20%"]},
    "Technical": {"duration_min": 200, "duration_max": 400, "easing": "cubic-bezier(0.2,0,0,1)", "overshoot": ["0%", "3%"]}
}
AMBIENT = {"noise-grain","vignette-pulse","gradient-shift","bokeh-circles","film-burn","starfield","geometric-patterns","liquid-wave","matrix-rain"}

TEMPLATE_ASSET_TYPES = {
    "ken-burns": "image",
    "parallax-pan": "image",
    "zoom-pulse": "image",
    "image-carousel": "image",
    "image-zoom-reveal": "image",
    "photo-stack": "image",
    "polaroid-frame": "image",
    "gallery-grid": "image",
    "masonry-gallery": "image",
    "picture-in-picture": "any",
    "split-screen": "any",
}

fails, warns = [], []
def fail(m): fails.append(m)
def warn(m): warns.append(m)

def check(bp, bp_path=None):
    # 1. JSON Schema validation first
    import jsonschema
    schema_path = DST / "schemas" / "blueprint.schema.json"
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            jsonschema.validate(instance=bp, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            fail(f"JSON Schema Validation Failed: {e.message} at path {list(e.path)}")
            return
            
    meta = bp.get("meta", {}); persona = meta.get("motion_personality", "Cinematic")
    approved = False # Approvals are now managed strictly in .pipeline_state.json
    
    for k in ["meta", "assets", "scenes"]:
        if k not in bp: fail(f"قسم ناقص: {k}")
    words, tp = [], (meta or {}).get("timings_path")
    if tp:
        p = Path(tp)
        if not p.exists(): warn(f"timings_path غير موجود بعد: {tp}")
        else:
            t = json.loads(p.read_text(encoding="utf-8"))
            words = t.get("words") or (t.get("timings") or {}).get("words") or []
    # الأصول: مصدر مصرّح + fallback + قفل المدفوع
    manifest = {}
    if bp_path:
        proj_dir = Path(bp_path).parent
        if (proj_dir / "02_asset_manifest.json").exists():
            man = json.loads((proj_dir / "02_asset_manifest.json").read_text(encoding="utf-8"))
            for a in man.get("assets", []):
                manifest[a.get("asset_id")] = a.get("type")

    for a in bp.get("assets", []):
        aid = a.get("asset_id", "?"); src = a.get("source")
        if src not in {"user_upload", "cache", "mcp_fetch", "generated"}:
            fail(f"asset {aid}: مصدر غير مصرّح ({src})")
        if src == "mcp_fetch" and not a.get("fallback"): fail(f"asset {aid}: mcp_fetch بدون fallback")
        if src == "user_upload" and not a.get("path"): fail(f"asset {aid}: user_upload بدون path")
        if a.get("paid") and not approved: fail(f"asset {aid}: paid=true قبل الموافقة")
    
    # Validation per scene
    total_sfx = 0
    for scene in bp.get("scenes", []):
        s_id = scene.get("scene_id", "?")
        tmpl_name = scene.get("template")
        
        if not tmpl_name:
            fail(f"scene {s_id}: قالب غير محدد")
        elif tmpl_name not in TEMPLATES:
            fail(f"scene {s_id}: قالب غير موجود في TEMPLATE_INDEX: {tmpl_name}")
        else:
            t_type = CATALOG_TYPES.get(tmpl_name)
            if t_type == "effect":
                t_family = CATALOG_FAMILIES.get(tmpl_name, "")
                if t_family != "transitions":
                    fail(f"scene {s_id}: القالب '{tmpl_name}' مصنف كـ effect من عائلة '{t_family}' ولا يُستخدم كقالب مباشر")

        if scene.get("sfx_ref"):
            total_sfx += 1

    if total_sfx == 0 and not meta.get("silence_requested"):
        fail("صفر SFX في الفيديو كله — أضف مؤثرات مطابقة للشخصية من assets/sfx/ أو silence_requested:true بموافقة المستخدم")

    # فحص الذوق وشخصية الحركة والمؤثرات الصوتية المعالجة
    pers = meta.get("motion_personality") or meta.get("personality")
    if pers not in PERSONA: fail("شخصية الحركة ناقصة/مجهولة في الـ Blueprint")
    else:
        q, s, sl, tones = PERSONA[pers]
        # استخدام المدقق الديناميكي الجديد
        import motion_validator
        motion_taste_file = DST / "references" / "deep" / "motion-taste" / "director" / "motion-personality.md"
        if not motion_taste_file.exists():
            motion_taste_file = DST / "references" / "motion-taste" / "director" / "motion-personality.md"
            
        mv_fails = motion_validator.validate(bp, motion_taste_file)
        if mv_fails:
            for m_fail in mv_fails:
                fail(m_fail)

        # Replace ambient, coverage and cues checking for scenes
        cues = []
        for s in bp.get("scenes", []):
            sfx = s.get("sfx_ref")
            if sfx:
                cues.append({"asset": sfx})
                
        fps = bp.get("fps", 30)
        dur = meta.get("duration_sec") or max([s.get("startFrame", 0)/fps + s.get("durationFrames", 0)/fps for s in bp.get("scenes", [])] or [fps])
        last = {}
        cnt = Counter(Path(c.get("asset") or "").name for c in cues if c.get("asset"))
        
        for c in cues:
            nm = Path(c.get("asset") or "").name
            # In V1 schema, we just use sfx_ref strings, so we don't track at_ms, tone, processing here
            pass
            
        for nm, n in cnt.items():
            if n > max(1, round(dur / 15)): fail(f"المؤثر {nm} مستخدم {n} مرة — تجاوز حد التنويع")

def render_md(bp, out):
    srcs = {a.get("asset_id"): a.get("source", "?") for a in bp.get("assets", [])}
    L = ["# Blueprint — النسخة البشرية", "",
         f"**مشروع:** {bp.get('meta',{}).get('project_id')} | **شخصية:** {bp.get('meta',{}).get('motion_personality')} | **مدة:** {bp.get('meta',{}).get('duration_sec')}s", "",
         "| الثانية | السرد | العناصر (نوع:قالب/أصل) | المصادر |", "|---|---|---|---|"]
    for scene in bp.get("scenes", []):
        tmpl = scene.get("template", "")
        s_id = scene.get("scene_id", "?")
        src = "قوالب محلية"
        L.append(f"| {s_id} | | {tmpl} | {src} |")
    Path(out).write_text("\n".join(L), encoding="utf-8")

def lock(bp):
    used = sorted({str(s["template"]) for s in bp.get("scenes", []) if s.get("template")})
    (DST / ".blueprint_lock.json").write_text(json.dumps({"templates": used}, indent=2), encoding="utf-8")

def verify_build(bp, proj):
    used = {str(s["template"]) for s in bp.get("scenes", []) if s.get("template")}
    built = set()
    for f in Path(proj).rglob("*.tsx"):
        built |= set(re.findall(r"from\s+['\"][^'\"]*(?:templates|premium-templates|cinematic-engine)/([\w-]+)['\"]", f.read_text(encoding="utf-8")))
    extra = built - used
    if extra: fail(f"خرق عقد: قوالب بالكود خارج الـ Blueprint: {sorted(extra)}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: print(__doc__); sys.exit(0)
    bp = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    check(bp, args[0])
    if "--md" in args: render_md(bp, args[args.index("--md") + 1])
    if "--lock" in args: lock(bp)
    if "--verify-build" in args: verify_build(bp, args[args.index("--verify-build") + 1])
    for w in warns: print("⚠️", w)
    if fails:
        print("❌ BLUEPRINT FAIL:"); [print(" -", x) for x in fails]; sys.exit(1)
    print("✅ BLUEPRINT PASS")
