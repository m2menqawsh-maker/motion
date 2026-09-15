import subprocess
from scripts.security import safe_subprocess
# -*- coding: utf-8 -*-
"""materialize_project.py — البوابة الوحيدة لنقل الميديا والقوالب إلى البناء.
Usage: python materialize_project.py <project_dir>"""
import json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import asyncio
from api.services.pipeline_service import PipelineService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent
WS = DST
PLUGIN_DIR = WS / ".agents" / "plugins" / "super-video-maker-plugin"
proj = Path(sys.argv[1]).resolve()
man = json.loads((proj / "02_asset_manifest.json").read_text(encoding="utf-8"))

project_id = proj.name

# ─── الفحص الإجباري قبل أي بناء ───
try:
    status = asyncio.run(PipelineService.get_status(project_id))
    if not (proj / "05_blueprint.json").exists() or not (proj / "01_plan.md").exists():
        raise Exception("Missing plan or blueprint")
    bp = json.loads((proj / "05_blueprint.json").read_text(encoding="utf-8"))
except Exception as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py")
    print(f"{'='*60}")
    print(e)
    sys.exit(1)

pub_media = WS / "remotion-app" / "public" / "projects" / project_id / "media"
pub_media.mkdir(parents=True, exist_ok=True)

fails, media_map, used = [], {}, set()
def canon(p):
    p = Path(p); return p if p.is_absolute() else (WS / p)

for a in man.get("assets", []):
    aid = a["asset_id"]
    src = canon(a.get("processed_path") or a.get("path", ""))
    if not src.exists(): fails.append(f"asset {aid}: missing {src}"); continue
    if PLUGIN_DIR in src.parents: fails.append(f"asset {aid}: مصدر داخل مجلد المهارة (ممنوع): {src}"); continue
    out = pub_media / f"{aid}{src.suffix}"
    shutil.copy2(src, out)
    media_map[aid] = f"projects/{project_id}/media/{out.name}"

for sec in bp.get("timeline", []):
    for e in sec.get("elements", []):
        if e.get("kind") == "template":
            name = e.get("template"); used.add(name)
            if not list((DST / "templates").rglob(f"{name}.tsx")) and not list((DST / "engine").rglob(f"{name}.tsx")):
                fails.append(f"template {name} غير موجود على القرص (في أي طبقة)")
        
        ref = e.get("asset_ref")
        if ref and ref not in media_map: fails.append(f"عنصر {e.get('id')} يشير لأصل غير مهيأ: {ref}")
        
        # تحقق من أن أي src داخل الـ props يعود للـ media_map الفعلي لمنع الأوهام
        props = e.get("props", {})
        for k, v in props.items():
            if k in ("src", "url", "asset") and isinstance(v, str):
                if v.startswith(f"projects/{project_id}/media/"):
                    aid = v.replace(f"projects/{project_id}/media/", "").split(".")[0]
                    if aid not in media_map:
                        fails.append(f"عنصر {e.get('id')} يستخدم {k} وهمي لا يوجد في manifest: {v}")
                elif not v.startswith("http"): # إذا لم يكن رابط خارجي
                    fails.append(f"عنصر {e.get('id')} يستخدم مسار ميديا غير معتمد: {v}")

(proj / "media_map.json").write_text(
    json.dumps(media_map, indent=2, ensure_ascii=False), encoding="utf-8")
if fails:
    print("❌ MATERIALIZE FAIL:"); [print(" -", x) for x in fails]; sys.exit(1)

# ─── تم النقل: الـ Hashing أصبح من مسؤولية pipeline.py ───
print(f"✅ MATERIALIZED: {len(media_map)} assets, {len(used)} templates")
