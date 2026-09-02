# -*- coding: utf-8 -*-
"""template_lint.py — بوابة الحوكمة قبل أي رندر.
Usage: python template_lint.py <tsx-or-dir> [--timings-required] [--verify-build <project_dir>]
Exit 0 = pass | 1 = fail"""
import re, sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT = Path(__file__).resolve()
DST = SCRIPT.parent.parent
ALLOWED = [DST / "templates", DST / "cinematic-engine", DST / "workflows", DST / "remotion-app"]

def load_registry():
    reg = set()
    ti = DST / "reference" / "ground-truth" / "TEMPLATE_INDEX.md"
    if ti.exists():
        for m in re.finditer(r"\| `([\w-]+)` \|", ti.read_text(encoding="utf-8")):
            reg.add(m.group(1))
    ci = DST / "reference" / "ground-truth" / "CINEMATIC_INDEX.md"
    if ci.exists():
        for m in re.finditer(r"\| `([\w\-./]+)` \|", ci.read_text(encoding="utf-8")):
            reg.add(m.group(1).split("/")[-1].split(".")[0])
    ce = DST / "cinematic-engine"
    if ce.exists():
        for p in ce.rglob("*.tsx"):
            reg.add(p.stem)
    return reg

REG = load_registry()
fails = []
def fail(msg):
    fails.append(msg)

arg = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else DST / "templates"
targets = sorted(arg.rglob("*.tsx")) if arg.is_dir() else [arg]

for f in targets:
    src = f.read_text(encoding="utf-8")
    # فحص 1: كل import نسبي موجود على القرص أو في الفهرس
    for m in re.finditer(r"""from\s+['"](\.{1,2}/[^'"]+)['"]""", src):
        spec = m.group(1)
        base = spec.split("/")[-1]
        r1 = (f.parent / spec).with_suffix(".tsx")
        r2 = (f.parent / spec).with_suffix(".ts")
        if not r1.exists() and not r2.exists() and base not in REG:
            fail(f"{f.name}: import غير موجود على القرص ولا بالفهرس: {spec}")
    # فحص 2: ممنوع spring/interpolate يدوي خارج المكتبات
    if not any(f.is_relative_to(d) for d in ALLOWED):
        if re.search(r"\bspring\(", src) or re.search(r"\binterpolate\(", src):
            fail(f"{f.name}: spring()/interpolate() يدوي خارج المكتبات المسموحة")
    # فحص 3: Sequence مقفل على صوت يجب أن يشير لـ timings
    if "--timings-required" in sys.argv and re.search(r"<Sequence", src) and not re.search(r"timings|words\[|voiceover", src):
        fail(f"{f.name}: Sequence صوتي بدون مرجع timings")
    # فحص 4: منع الكود غير الحتمي (Non-deterministic) لأنه يكسر محرك Remotion
    bad_patterns = [r"Math\.random\(", r"Date\.now\(", r"setTimeout\(", r"setInterval\(", r"requestAnimationFrame\("]
    for p in bad_patterns:
        if re.search(p, src):
            fail(f"{f.name}: كود غير حتمي مرفوض ({p})")

if "--verify-build" in sys.argv:
    import json as _j
    proj = Path(sys.argv[sys.argv.index("--verify-build") + 1]).resolve()
    bp = _j.loads((proj / "05_blueprint.json").read_text(encoding="utf-8"))
    planned = {e.get("template") for s in bp.get("timeline", []) for e in s.get("elements", []) if e.get("kind") == "template"}
    imported = set()
    for f in (proj / "06_build" / "src").rglob("*.tsx"):
        imported |= set(re.findall(r"from\s+['\"][^'\"]*templates/([\w-]+)['\"]", f.read_text(encoding="utf-8")))
    if planned - imported: fail(f"قوالب Blueprint غير مستوردة بالكود (الوكيل لم يستخدم القوالب): {sorted(planned - imported)}")
    if imported - planned: fail(f"استيرادات خارج عقد الـ Blueprint: {sorted(imported - planned)}")

if fails:
    print("❌ LINT FAIL:")
    [print(" -", x) for x in fails]
    sys.exit(1)
print(f"✅ LINT PASS: {len(targets)} file(s) checked")
