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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import subprocess
from scripts.security.security import safe_subprocess
import json, re
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent.parent
from scripts.core.template_contract import get_template_contract, UnknownTemplateError

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
    # 1. Canonical Blueprint v2 validation
    from scripts.core.blueprint_validator import validate_blueprint_v2
    from scripts.core.blueprint_migration import is_legacy_blueprint_v1, migrate_blueprint_to_v2
    from scripts.core.manifest_loader import load_manifest

    proj_dir = Path(bp_path).parent if bp_path else None
    project_id = bp.get("project_id") or (proj_dir.name if proj_dir and proj_dir.name.startswith("prj_") else None)

    man = None
    if proj_dir and (proj_dir / "02_asset_manifest.json").exists():
        try:
            man = load_manifest(proj_dir / "02_asset_manifest.json", expected_project_id=project_id, allow_migrate=True)
        except Exception as e:
            fail(f"02_asset_manifest.json غير صالح: {e}")

    raw_bp = bp
    if is_legacy_blueprint_v1(raw_bp):
        raw_bp = migrate_blueprint_to_v2(raw_bp, project_id=project_id)

    v_res = validate_blueprint_v2(raw_bp, expected_project_id=project_id, manifest=man)
    if not v_res.ok:
        for err in v_res.errors:
            fail(f"خرق عقد المخطط: {err}")
        return
    bp_v2 = v_res.blueprint
    bp = bp_v2.to_dict()

    meta = bp.get("meta", {}); persona = meta.get("motion_personality", "Cinematic")
    approved = False # Approvals are now managed strictly in .pipeline_state.json
    
    words, tp = [], (meta or {}).get("timings_path")
    if tp:
        p = Path(tp)
        if not p.exists(): warn(f"timings_path غير موجود بعد: {tp}")
        else:
            t = json.loads(p.read_text(encoding="utf-8"))
            words = t.get("words") or (t.get("timings") or {}).get("words") or []

    # Validation per scene via authoritative template contract (S15)
    contract = get_template_contract()
    total_sfx = 0
    for scene in bp.get("scenes", []):
        s_id = scene.get("scene_id", "?")
        tmpl_name = scene.get("template")
        
        if not tmpl_name:
            fail(f"scene {s_id}: قالب غير محدد")
        else:
            entry = contract.resolve(tmpl_name)
            if entry is None or not entry.runtime_available:
                fail(f"scene {s_id}: معرف القالب غير معروف في سجل القوالب: '{tmpl_name}' [UNKNOWN_TEMPLATE_ID]")
            elif entry.category == "effect":
                fail(f"scene {s_id}: القالب '{tmpl_name}' مصنف كـ effect ولا يُستخدم كقالب مشهد مباشر")

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
        motion_taste_file = DST / "references" / "4_taste_engine" / "motion-personality.md"
        if not motion_taste_file.exists():
            motion_taste_file = DST / "references" / "4_taste_engine" / "motion-personality.md"
            
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
                
        fps = bp_v2.fps
        dur = bp_v2.total_duration_seconds
        last = {}
        cnt = Counter(Path(c.get("asset") or "").name for c in cues if c.get("asset"))
        
        for c in cues:
            nm = Path(c.get("asset") or "").name
            # In V1 schema, we just use sfx_ref strings, so we don't track at_ms, tone, processing here
            pass
            
        for nm, n in cnt.items():
            if n > max(1, round(dur / 15)): fail(f"المؤثر {nm} مستخدم {n} مرة — تجاوز حد التنويع")

def render_md(bp, out):
    fps = bp.get("fps", 30)
    dur = round(max([s.get("startFrame", 0)/fps + s.get("durationFrames", 0)/fps for s in bp.get("scenes", [])] or [0]), 1)
    L = ["# Blueprint — النسخة البشرية", "",
         f"**مشروع:** {bp.get('project_id')} | **شخصية:** {bp.get('meta',{}).get('motion_personality')} | **مدة:** {dur}s", "",
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
