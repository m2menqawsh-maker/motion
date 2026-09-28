import json
import shutil
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.security.path_security import validate_project_id
from scripts.core.project_identity import validate_project_identity
from scripts.core.manifest_errors import ManifestError, ProjectIdentityMismatchError
from scripts.core.blueprint_errors import BlueprintError, BlueprintValidationError
from scripts.core.materializer import (
    materialize_project_atomic,
    MaterializationPreflightError,
    MaterializationError,
)

if len(sys.argv) < 2:
    print("Usage: python materialize_project.py <project_dir>")
    sys.exit(1)

proj = Path(sys.argv[1]).resolve()
try:
    project_id = validate_project_id(proj.name)
except Exception as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py: معرف المشروع غير صالح: {e}")
    print(f"{'='*60}")
    sys.exit(1)

try:
    res = materialize_project_atomic(proj, workspace_root=REPO_ROOT)
    print(f"✅ MATERIALIZED: {res['assets_count']} assets, {res['templates_count']} templates")
    sys.exit(0)
except ProjectIdentityMismatchError as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py: خطأ في هوية المشروع")
    print(f"{'='*60}")
    print(e)
    sys.exit(1)
except ManifestError as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py: بيان الأصول غير صالح")
    print(f"{'='*60}")
    print(e)
    sys.exit(1)
except BlueprintValidationError as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py")
    print(f"{'='*60}")
    for err in e.errors:
        if "referenced media_ref" in err and "not found in manifest" in err:
            ref = err.split("referenced media_ref '")[1].split("' not found")[0]
            print(f"عنصر يشير لأصل غير مهيأ: {ref}")
        elif "referenced sfx_ref" in err and "not found in manifest" in err:
            ref = err.split("referenced sfx_ref '")[1].split("' not found")[0]
            print(f"عنصر يشير لمؤثر صوتي غير مهيأ: {ref}")
    print(e)
    sys.exit(1)
except MaterializationPreflightError as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py")
    print(f"{'='*60}")
    print("❌ MATERIALIZE FAIL:")
    for x in e.errors:
        if "Scene references unmaterialized asset: '" in x:
            ref = x.split("Scene references unmaterialized asset: '")[1].rstrip("'")
            print(f"عنصر يشير لأصل غير مهيأ: {ref}")
        elif "Scene references unmaterialized SFX: '" in x:
            ref = x.split("Scene references unmaterialized SFX: '")[1].rstrip("'")
            print(f"عنصر يشير لمؤثر صوتي غير مهيأ: {ref}")
        print(" -", x)
    sys.exit(1)
except Exception as e:
    print(f"\n{'='*60}")
    print(f"🛑 تم إيقاف materialize_project.py: {e}")
    print(f"{'='*60}")
    sys.exit(1)
