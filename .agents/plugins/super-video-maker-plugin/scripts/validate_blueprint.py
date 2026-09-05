import argparse
# -*- coding: utf-8 -*-
"""validate_blueprint.py — بوابة عقد الـ Blueprint قبل البناء.
Usage:
  python validate_blueprint.py <blueprint.json>                      # فحص كامل
  python validate_blueprint.py <bp.json> --md <out.md>               # + النسخة البشرية
  python validate_blueprint.py <bp.json> --lock                      # قفل العقد
  python validate_blueprint.py <bp.json> --verify-build <proj_dir>   # الكود المبني == العقد
Exit 0 = PASS."""
from utils.logger import UnifiedLogger
log = UnifiedLogger("validate_blueprint")

import json, re, sys
from pathlib import Path
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
    meta = bp.get("meta", {}); persona = meta.get("motion_personality", "Cinematic")
    approved = (meta.get("approval") or {}).get("blueprint_approved") is True
    for k in ["meta", "spine", "assets", "timeline"]:
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
    # الثانية-بالثانية
    for sec in bp.get("timeline", []):
        s = sec.get("sec", "?"); cov, heroes = 0, 0
        for e in sec.get("elements", []):
            eid = e.get("id", "?"); lay = (e.get("layout") or {}).get("layer")
            if lay not in (1, 2, 3, 4, 5): fail(f"sec {s}/{eid}: طبقة خارج 1-5 ({lay})")
            c = (e.get("layout") or {}).get("coverage_pct", 0)
            if lay in (3, 4):
                cov += c
                if c >= 35: heroes += 1
            if e.get("kind") == "template":
                tmpl_name = e.get("template")
                if tmpl_name not in TEMPLATES:
                    fail(f"sec {s}/{eid}: قالب غير موجود في TEMPLATE_INDEX: {tmpl_name}")
                else:
                    t_type = CATALOG_TYPES.get(tmpl_name)
                    if t_type and e.get("kind") == "template":
                        # Validate that the type in catalog is suitable for a template element
                        if t_type == "effect":
                            t_family = CATALOG_FAMILIES.get(tmpl_name, "")
                            if t_family != "transitions":
                                fail(f"sec {s}/{eid}: القالب '{tmpl_name}' مصنف كـ effect من عائلة '{t_family}' ولا يُستخدم كقالب مباشر")
            if e.get("kind") == "template" and e.get("asset_ref"):
                asset_type = manifest.get(e.get("asset_ref"))
                tmpl = e.get("template")
                req_type = TEMPLATE_ASSET_TYPES.get(tmpl, "any")
                if req_type != "any" and asset_type and asset_type != req_type:
                    fail(f"sec {s}/{eid}: 🛑 توقف إلزامي (HARD FAIL) 🛑 القالب '{tmpl}' مخصص للتعامل مع '{req_type}' حصراً، ولكنك مررت له الأصل '{e.get('asset_ref')}' ونوعه '{asset_type}'. لا تستخدم قوالب صور للفيديو!")
            tf = e.get("taken_from")
            if not tf: fail(f"sec {s}/{eid}: taken_from ناقص (من أين داخل المهارة؟)")
            elif not tf.startswith("mcp:") and not (DST / tf).exists() and not tf.startswith("premium-templates/"):
                fail(f"sec {s}/{eid}: taken_from ليس على القرص: {tf}")
            lk = e.get("lock")
            if lk and lk.get("type") == "word":
                wi = lk.get("word_index")
                if not tp: fail(f"sec {s}/{eid}: lock كلمة بدون meta.timings_path")
                elif words and (wi is None or wi >= len(words)): fail(f"sec {s}/{eid}: word_index خارج timings")
            if e.get("paid") and not approved: fail(f"sec {s}/{eid}: paid=true قبل الموافقة")
        if cov > 70: fail(f"sec {s}: coverage محتوى {cov}% > 70%")
        if heroes > 1: fail(f"sec {s}: {heroes} عناصر hero (>1) — قاعدة الـ focal point")
        sfx = sec.get("sfx", [])
        if len(sfx) > 1: fail(f"sec {s}: {len(sfx)} مؤثرات (>1)")
        for fx in sfx:
            tone = fx.get("tone", "none")
            if not str(fx.get("taken_from", "")).startswith(("assets/", "mcp:")):
                fail(f"sec {s}: SFX بدون مصدر مصرّح")

    total_sfx = sum(len(sec.get("sfx", [])) for sec in bp.get("timeline", []))
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

        secs = sorted({x.get("sec") for x in bp.get("timeline", [])})
        for sc in secs:
            cov = [e for sec2 in bp.get("timeline", []) for e in sec2.get("elements", [])
                   if e.get("template") in AMBIENT and e.get("start_sec", 0) <= sc < e.get("end_sec", 10**9)]
            if not cov: fail(f"الثانية {sc}: بلا طبقة ambient — الذوق إلزامي")
        cues = [c for sec in bp.get("timeline", []) for c in sec.get("sfx", [])]
        last = {}
        cnt = Counter(Path(c.get("asset") or c.get("path") or "").name for c in cues if (c.get("asset") or c.get("path")))
        dur = meta.get("duration_sec") or max([e.get("end_sec", 0) for s2 in bp.get("timeline", []) for e in s2.get("elements", [])] or [30])
        for c in sorted(cues, key=lambda c: c.get("at_ms", 0)):
            if not c.get("processing"): fail("cue بدون سلسلة معالجة (ممنوع المؤثر الخام)")
            if "volume_db" not in c: fail("cue بدون volume_db")
            if c.get("tone") not in tones: fail(f"نبرة {c.get('tone')} غير مسموحة لشخصية {pers}")
            nm = Path(c.get("asset") or c.get("path") or "").name; t = c.get("at_ms", 0)
            if nm in last and t - last[nm] < 8000: fail(f"المؤثر {nm} تكرر خلال أقل من 8 ثوانٍ")
            last[nm] = t
        for nm, n in cnt.items():
            if n > max(1, round(dur / 15)): fail(f"المؤثر {nm} مستخدم {n} مرة — تجاوز حد التنويع")

def render_md(bp, out):
    srcs = {a.get("asset_id"): a.get("source", "?") for a in bp.get("assets", [])}
    L = ["# Blueprint — النسخة البشرية", "",
         f"**مشروع:** {bp.get('meta',{}).get('project_id')} | **شخصية:** {bp.get('meta',{}).get('motion_personality')} | **مدة:** {bp.get('meta',{}).get('duration_sec')}s", "",
         "| الثانية | السرد | العناصر (نوع:قالب/أصل) | المصادر |", "|---|---|---|---|"]
    for sec in bp.get("timeline", []):
        els = " ؛ ".join(f"{e.get('kind')}:{e.get('template') or e.get('asset_ref') or e.get('id')}" for e in sec.get("elements", []))
        raw_srcs = [str(srcs[e["asset_ref"]]) for e in sec.get("elements", []) if e.get("asset_ref") in srcs and srcs.get(e.get("asset_ref"))]
        src = " ، ".join(sorted(set(raw_srcs)) if raw_srcs else ["قوالب محلية"])
        L.append(f"| {sec.get('sec')} | {sec.get('narration','')} | {els} | {src} |")
    Path(out).write_text("\n".join(L), encoding="utf-8")

def lock(bp):
    used = sorted({str(e["template"]) for sec in bp.get("timeline", []) for e in sec.get("elements", []) if e.get("kind") == "template" and e.get("template")})
    (DST / ".blueprint_lock.json").write_text(json.dumps({"templates": used}, indent=2), encoding="utf-8")

def verify_build(bp, proj):
    used = {str(e["template"]) for sec in bp.get("timeline", []) for e in sec.get("elements", []) if e.get("kind") == "template" and e.get("template")}
    built = set()
    for f in Path(proj).rglob("*.tsx"):
        built |= set(re.findall(r"from\s+['\"][^'\"]*(?:templates|premium-templates|cinematic-engine)/([\w-]+)['\"]", f.read_text(encoding="utf-8")))
    extra = built - used
    if extra: fail(f"خرق عقد: قوالب بالكود خارج الـ Blueprint: {sorted(extra)}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Blueprint validator")
    parser.add_argument("blueprint_path", help="مسار ملف blueprint.json")
    parser.add_argument("--md", help="مسار ملف markdown للتوليد")
    parser.add_argument("--lock", action="store_true", help="قفل الـ Blueprint")
    parser.add_argument("--verify-build", dest="verify_build", help="مسار المشروع للتحقق من بناء الكود")
    args = parser.parse_args()

    bp = json.loads(Path(args.blueprint_path).read_text(encoding="utf-8"))
    check(bp, args.blueprint_path)
    if args.md: render_md(bp, args.md)
    if args.lock: lock(bp)
    if args.verify_build: verify_build(bp, args.verify_build)
    for w in warns: print("⚠️", w)
    if fails:
        log.error("BLUEPRINT FAIL:"); [print(" -", x) for x in fails]; sys.exit(1)
    log.success("BLUEPRINT PASS")

if __name__ == '__main__':
    main()
