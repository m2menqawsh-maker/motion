import json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import subprocess
from scripts.security.security import safe_subprocess
import asyncio
from api.services.pipeline_service import PipelineService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent.parent
WS = DST
PLUGIN_DIR = WS / ".agents" / "plugins" / "super-video-maker-plugin"
proj = Path(sys.argv[1]).resolve()
man = json.loads((proj / "02_asset_manifest.json").read_text(encoding="utf-8"))

project_id = proj.name

# ─── الفحص الإجباري قبل أي بناء ───
try:
    status = PipelineService.get_status(project_id)
    has_plan = (proj / "master_plan.md").exists() or (proj / "01_plan.md").exists()
    if not (proj / "05_blueprint.json").exists() or not has_plan:
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

for sec in bp.get("scenes", []):
    name = sec.get("template")
    if name:
        used.add(name)
        # Checking template existence
        if not list((DST / "remotion-app" / "src" / "templates").rglob(f"{name}.tsx")) and not list((DST / "remotion-app" / "src" / "engine").rglob(f"{name}.tsx")):
            fails.append(f"template {name} غير موجود على القرص (في أي طبقة)")
    
    # Check media_refs, sfx_ref, captions_ref
    for ref in sec.get("media_refs", []):
        if ref not in media_map: fails.append(f"عنصر يشير لأصل غير مهيأ: {ref}")
    if sec.get("sfx_ref") and sec.get("sfx_ref") not in media_map:
        fails.append(f"عنصر يشير لمؤثر صوتي غير مهيأ: {sec.get('sfx_ref')}")
    
    props = sec.get("props", {})
    # No arbitrary deep path checks are needed anymore because paths are resolved at runtime via media_map.json.

(proj / "media_map.json").write_text(
    json.dumps(media_map, indent=2, ensure_ascii=False), encoding="utf-8")
if fails:
    print("❌ MATERIALIZE FAIL:"); [print(" -", x) for x in fails]; sys.exit(1)

# ─── تم النقل: الـ Hashing أصبح من مسؤولية pipeline.py ───
print(f"✅ MATERIALIZED: {len(media_map)} assets, {len(used)} templates")
