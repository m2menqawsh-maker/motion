import json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import subprocess
from scripts.security.security import safe_subprocess
from scripts.security.path_security import (
    validate_project_id,
    validate_asset_id,
    resolve_safe_path,
    validate_source_asset,
    PathSecurityViolation,
)
import asyncio
from api.services.pipeline_service import PipelineService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent.parent
WS = DST
PLUGIN_DIR = WS / ".agents" / "plugins" / "super-video-maker-plugin"
from scripts.core.project_identity import validate_project_identity
from scripts.core.manifest_loader import load_manifest
from scripts.core.manifest_errors import ManifestError, ProjectIdentityMismatchError
from scripts.core.blueprint_loader import load_blueprint
from scripts.core.blueprint_errors import BlueprintError, BlueprintValidationError

proj = Path(sys.argv[1]).resolve()
project_id = validate_project_id(proj.name)

# ─── فحص الهوية والمانيفست القانوني ───
try:
    validate_project_identity(proj, expected_project_id=project_id)
except ProjectIdentityMismatchError as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py: خطأ في هوية المشروع")
    print(f"{'='*60}")
    print(e)
    sys.exit(1)

try:
    man = load_manifest(proj / "02_asset_manifest.json", expected_project_id=project_id, allow_migrate=True)
except ManifestError as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py: بيان الأصول غير صالح")
    print(f"{'='*60}")
    print(e)
    sys.exit(1)

# ─── الفحص الإجباري قبل أي بناء ───
try:
    status = PipelineService.get_status(project_id)
    has_plan = (proj / "master_plan.md").exists() or (proj / "01_plan.md").exists()
    if not (proj / "05_blueprint.json").exists() or not has_plan:
        raise Exception("Missing plan or blueprint")
    bp_v2 = load_blueprint(proj / "05_blueprint.json", expected_project_id=project_id, manifest=man, allow_migrate=True)
    bp = bp_v2.to_dict()
except Exception as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py")
    print(f"{'='*60}")
    if isinstance(e, BlueprintValidationError):
        for err in e.errors:
            if "referenced media_ref" in err and "not found in manifest" in err:
                ref = err.split("referenced media_ref '")[1].split("' not found")[0]
                print(f"عنصر يشير لأصل غير مهيأ: {ref}")
            elif "referenced sfx_ref" in err and "not found in manifest" in err:
                ref = err.split("referenced sfx_ref '")[1].split("' not found")[0]
                print(f"عنصر يشير لمؤثر صوتي غير مهيأ: {ref}")
    print(e)
    sys.exit(1)

pub_media = WS / "remotion-app" / "public" / "projects" / project_id / "media"

fails, planned_copies, media_map, used = [], [], {}, set()

def canon(p):
    p = Path(p)
    return p if p.is_absolute() else (WS / p)

# ─── PHASE 1: PRE-VALIDATION (Zero Side Effects) ───
# Any security violation, path traversal, or symlink escape MUST fail before copying/writing.
for a in man.assets:
    aid = a.asset_id
    
    # 1. Asset ID Confinement Validation
    try:
        validate_asset_id(aid)
    except ValueError as e:
        fails.append(f"asset '{aid}': {e}")
        continue

    if aid in media_map:
        fails.append(f"duplicate asset_id '{aid}'")
        continue

    raw_path = a.processed_path or a.source_path or ""
    if not raw_path:
        fails.append(f"asset {aid}: missing path")
        continue

    src = canon(raw_path)

    # 2. Source Asset & Symlink Confinement Validation
    try:
        real_src = validate_source_asset(src, allowed_roots=[WS], forbidden_roots=[PLUGIN_DIR])
    except (PathSecurityViolation, FileNotFoundError, OSError) as e:
        fails.append(f"asset {aid}: {e}")
        continue

    # 3. Destination Confinement Validation
    candidate_out = pub_media / f"{aid}{src.suffix}"
    try:
        # Candidate out must resolve inside pub_media
        cand_resolved = candidate_out.resolve()
        pub_resolved = pub_media.resolve()
        cand_resolved.relative_to(pub_resolved)
    except (ValueError, Exception) as e:
        fails.append(f"asset {aid}: destination escape detected: {candidate_out}")
        continue

    planned_copies.append((src, candidate_out, aid))
    media_map[aid] = f"projects/{project_id}/media/{candidate_out.name}"

# Validate blueprint scenes and template references
for sec in bp.get("scenes", []):
    name = sec.get("template")
    if name:
        used.add(name)
        # Checking template existence (case-insensitive for Linux CI)
        found = False
        for search_dir in [DST / "remotion-app" / "src" / "templates", DST / "remotion-app" / "src" / "engine"]:
            if any(f.name.lower() == f"{name.lower()}.tsx" for f in search_dir.rglob("*.tsx")):
                found = True
                break
        
        if not found:
            fails.append(f"template {name} غير موجود على القرص (في أي طبقة)")
    
    # Check media_refs, sfx_ref, captions_ref
    for ref in sec.get("media_refs", []):
        if ref not in media_map:
            fails.append(f"عنصر يشير لأصل غير مهيأ: {ref}")
    if sec.get("sfx_ref") and sec.get("sfx_ref") not in media_map:
        fails.append(f"عنصر يشير لمؤثر صوتي غير مهيأ: {sec.get('sfx_ref')}")

# If ANY validation fails, reject immediately with zero filesystem mutations
if fails:
    print("❌ MATERIALIZE FAIL:")
    for x in fails:
        print(" -", x)
    sys.exit(1)

# ─── PHASE 2: EXECUTION PASS (Safe Materialization) ───
pub_media.mkdir(parents=True, exist_ok=True)

for src, out, aid in planned_copies:
    shutil.copy2(src, out)

(proj / "media_map.json").write_text(
    json.dumps(media_map, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"✅ MATERIALIZED: {len(media_map)} assets, {len(used)} templates")
