import argparse
# -*- coding: utf-8 -*-
"""materialize_project.py — البوابة الوحيدة لنقل الميديا والقوالب إلى البناء.
Usage: python materialize_project.py <project_dir>"""
from utils.logger import UnifiedLogger
log = UnifiedLogger("materialize_project")

import json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pipeline_guard import PipelineGuard, GuardViolation
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="البوابة الوحيدة لنقل الميديا والقوالب إلى البناء")
    parser.add_argument("project_id", help="معرف المشروع (أو مسار المشروع)")
    args = parser.parse_args()

    DST = Path(__file__).resolve().parent.parent
    WS = DST.parent.parent.parent
    proj = Path(args.project_id).resolve()
    man = json.loads((proj / "02_asset_manifest.json").read_text(encoding="utf-8"))
    bp = json.loads((proj / "05_blueprint.json").read_text(encoding="utf-8"))

    project_id = proj.name

    # ─── الفحص الإجباري قبل أي بناء ───
    guard = PipelineGuard(project_id)
    try:
        guard.pre_build_check()
    except GuardViolation as e:
        log.info(f"\n{'='*60}")
        log.error(f"تم إيقاف materialize_project.py")
        log.info(f"{'='*60}")
        print(e)
        sys.exit(1)

    pub_media = proj / "06_build" / "public" / "media"
    src_tpl = proj / "06_build" / "src" / "templates"
    src_eng = proj / "06_build" / "src" / "engine"
    pub_media.mkdir(parents=True, exist_ok=True)

    # 1) Full Copy
    copied_tpl = copied_eng = 0
    if (DST / "templates").exists():
        shutil.copytree(DST / "templates", src_tpl, dirs_exist_ok=True)
        copied_tpl = len(list(src_tpl.rglob("*.*")))
    if (DST / "engine").exists():
        shutil.copytree(DST / "engine", src_eng, dirs_exist_ok=True)
        copied_eng = len(list(src_eng.rglob("*.*")))
    log.info(f"تم نسخ القوالب: {copied_tpl} ملف من templates، و {copied_eng} ملف من engine.")

    # 2) tsconfig.json Alias Injection
    tsconfig_path = proj / "06_build" / "tsconfig.json"
    if tsconfig_path.exists():
        try:
            ts_data = json.loads(tsconfig_path.read_text(encoding="utf-8"))
            if "compilerOptions" not in ts_data: ts_data["compilerOptions"] = {}
            if "paths" not in ts_data["compilerOptions"]: ts_data["compilerOptions"]["paths"] = {}
            ts_data["compilerOptions"]["paths"]["@templates/*"] = ["src/templates/*"]
            ts_data["compilerOptions"]["paths"]["@engine/*"] = ["src/engine/*"]
            tsconfig_path.write_text(json.dumps(ts_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log.info(f"️ فشل تحديث tsconfig.json: {e}")

    # 3) remotion.config.ts Alias Injection
    remotion_config_path = proj / "06_build" / "remotion.config.ts"
    if remotion_config_path.exists():
        try:
            content = remotion_config_path.read_text(encoding="utf-8")
            if '"@templates":' not in content and "'@templates':" not in content:
                target1 = '"@": path.join(process.cwd(), "src"),'
                rep1 = '"@": path.join(process.cwd(), "src"),\n        "@templates": path.join(process.cwd(), "src", "templates"),\n        "@engine": path.join(process.cwd(), "src", "engine"),'
                content = content.replace(target1, rep1)
            
                target2 = "'@': path.join(process.cwd(), 'src'),"
                rep2 = "'@': path.join(process.cwd(), 'src'),\n        '@templates': path.join(process.cwd(), 'src', 'templates'),\n        '@engine': path.join(process.cwd(), 'src', 'engine'),"
                content = content.replace(target2, rep2)
            
                target3 = '"@": path.join(process.cwd(), "src")'
                rep3 = '"@": path.join(process.cwd(), "src"),\n        "@templates": path.join(process.cwd(), "src", "templates"),\n        "@engine": path.join(process.cwd(), "src", "engine")'
                if rep1 not in content and rep2 not in content:
                    content = content.replace(target3, rep3)

                remotion_config_path.write_text(content, encoding="utf-8")
        except Exception as e:
            log.info(f"️ فشل تحديث remotion.config.ts: {e}")

    fails, media_map, used = [], {}, set()
    def canon(p):
        p = Path(p); return p if p.is_absolute() else (WS / p)

    for a in man.get("assets", []):
        aid = a["asset_id"]
        src = canon(a.get("processed_path") or a.get("path", ""))
        if not src.exists(): fails.append(f"asset {aid}: missing {src}"); continue
        if DST in src.parents: fails.append(f"asset {aid}: مصدر داخل مجلد المهارة (ممنوع): {src}"); continue
        out = pub_media / f"{aid}{src.suffix}"
        shutil.copy2(src, out); media_map[aid] = f"media/{out.name}"

    for sec in bp.get("timeline", []):
        for e in sec.get("elements", []):
            tf = e.get("taken_from", "")
            if e.get("kind") == "template":
                name = e.get("template"); used.add(name)
                if not list(src_tpl.rglob(f"{name}.tsx")) and not list(src_eng.rglob(f"{name}.tsx")):
                    fails.append(f"template {name} غير موجود على القرص (في أي طبقة)")
            elif tf.startswith("cinematic-engine/"):
                s = DST / tf
                if s.exists(): shutil.copy2(s, src_tpl / s.name)
                else: fails.append(f"cinematic missing: {tf}")
            ref = e.get("asset_ref")
            if ref and ref not in media_map: fails.append(f"عنصر {e.get('id')} يشير لأصل غير مهيأ: {ref}")
        
            # تحقق من أن أي src داخل الـ props يعود للـ media_map الفعلي لمنع الأوهام
            props = e.get("props", {})
            for k, v in props.items():
                if k in ("src", "url", "asset") and isinstance(v, str):
                    if v.startswith("media/"):
                        aid = v.replace("media/", "").split(".")[0]
                        if aid not in media_map:
                            fails.append(f"عنصر {e.get('id')} يستخدم {k} وهمي لا يوجد في manifest: {v}")
                    elif not v.startswith("http"): # إذا لم يكن رابط خارجي ولم يبدأ بـ media/
                        fails.append(f"عنصر {e.get('id')} يستخدم مسار ميديا غير معتمد (يجب أن يبدأ بـ media/): {v}")

    (proj / "06_build" / "src" / "media_map.json").write_text(
        json.dumps(media_map, indent=2, ensure_ascii=False), encoding="utf-8")
    if fails:
        log.error("MATERIALIZE FAIL:"); [print(" -", x) for x in fails]; sys.exit(1)

    # ─── ختم الناتج لمنع النسخ اليدوي اللاحق ───
    PipelineGuard.seal_report(Path(f"projects/{project_id}/06_build/media_map.json"))

    # إنشاء القفل المادي
    lock_path = proj / ".materialized.lock"
    lock_path.write_text(json.dumps({"status": "locked", "assets_count": len(media_map)}), encoding="utf-8")

    log.success(f"MATERIALIZED: {len(media_map)} assets, {len(used)} templates")
    log.info(f"🔒 تم إغلاق القفل: {lock_path.name}")


if __name__ == '__main__':
    main()
