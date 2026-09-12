import os
import json
from pathlib import Path
from typing import Dict, List, Any

def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_gate_1(project_dir: str) -> Dict[str, Any]:
    """
    يفحص Gate 1:
    - وجود manifest.json
    - كل مراجع الميديا في الـ blueprint موجودة في الـ manifest بحالة approved=true
    - ملفات الميديا موجودة على القرص
    - ملف الشعار في brand.json موجود إن وجد
    """
    p = Path(project_dir)
    errors = []
    
    manifest_path = p / "manifest.json"
    blueprint_path = p / "blueprint.json"
    brand_path = p / "brand.json"
    
    manifest = _load_json(manifest_path)
    blueprint = _load_json(blueprint_path)
    brand = _load_json(brand_path)
    
    if manifest is None:
        return {"ok": False, "errors": ["manifest.json is missing"]}
        
    required_refs = []
    if blueprint:
        audio = blueprint.get("audio", {})
        if audio.get("voiceover_ref"):
            required_refs.append(("voiceover", audio.get("voiceover_ref")))
        if audio.get("music_ref"):
            required_refs.append(("music", audio.get("music_ref")))
            
        for scene in blueprint.get("scenes", []):
            if scene.get("media_refs"):
                for m in scene.get("media_refs"):
                    required_refs.append(("media", m))
            if scene.get("sfx_ref"):
                required_refs.append(("sfx", scene.get("sfx_ref")))
            if scene.get("captions_ref"):
                required_refs.append(("captions", scene.get("captions_ref")))
    
    for ref_type, ref_id in required_refs:
        found = False
        assets = manifest.get("assets", [])
        for asset in assets:
            if asset.get("asset_id") == ref_id:
                found = True
                if not asset.get("approved", False):
                    errors.append(f"Asset '{ref_id}' is not approved in manifest")
                
                filepath = asset.get("path")
                if filepath:
                    full_path = p / filepath
                    if not full_path.exists():
                        errors.append(f"Asset '{ref_id}' file not found: {filepath}")
                else:
                    errors.append(f"Asset '{ref_id}' missing path in manifest")
                break
        
        if not found:
            errors.append(f"Asset '{ref_id}' from blueprint not found in manifest")

    if brand and brand.get("logoSrc"):
        logo_path = p / brand.get("logoSrc")
        if not logo_path.exists():
            errors.append(f"Brand logo file not found: {brand.get('logoSrc')}")

    return {"ok": len(errors) == 0, "errors": errors}

def check_gate_2(project_dir: str) -> Dict[str, Any]:
    """
    يفحص Gate 2:
    - كل scene.template موجود في registry/ids.json
    - المشاهد مرتبة تصاعدياً بدون تداخل
    - إذا كان الصوت != none، يجب أن يكون totalDurationFrames >= مدة الـ VO
    """
    p = Path(project_dir)
    errors = []
    
    blueprint = _load_json(p / "blueprint.json")
    if blueprint is None:
        return {"ok": False, "errors": ["blueprint.json is missing"]}
        
    ids_json = _load_json(Path("registry/ids.json"))
    valid_ids = ids_json.get("ids", []) if ids_json else []
    if not valid_ids:
        errors.append("registry/ids.json is missing or empty")

    scenes = blueprint.get("scenes", [])
    last_end = 0
    for i, scene in enumerate(scenes):
        template = scene.get("template")
        if template not in valid_ids:
            errors.append(f"Scene {i+1} has unknown template '{template}'")
            
        start = scene.get("startFrame", 0)
        duration = scene.get("durationFrames", 0)
        
        if start < last_end:
            errors.append(f"Scene {i+1} overlaps with previous scene. Start: {start}, Previous End: {last_end}")
            
        last_end = start + duration

    project = _load_json(p / "project.json")
    if project:
        vo_mode = project.get("voiceover", {}).get("mode", "none")
        if vo_mode != "none":
            manifest = _load_json(p / "manifest.json")
            if manifest:
                vo_ref = blueprint.get("audio", {}).get("voiceover_ref")
                vo_frames = 0
                for asset in manifest.get("assets", []):
                    if asset.get("asset_id") == vo_ref:
                        if "durationFrames" in asset:
                            vo_frames = asset["durationFrames"]
                        break
                
                total_duration = blueprint.get("totalDurationFrames", 0)
                if vo_frames > 0 and total_duration < vo_frames:
                    errors.append(f"totalDurationFrames ({total_duration}) is less than voiceover duration ({vo_frames})")

    return {"ok": len(errors) == 0, "errors": errors}

def check_gate_3(project_dir: str) -> Dict[str, Any]:
    """
    يفحص Gate 3:
    - gate_1 و gate_2 بحالة approved
    """
    state = _load_json(Path(project_dir) / "state.json")
    errors = []
    if state is None:
        return {"ok": False, "errors": ["state.json is missing"]}
        
    g1 = state.get("gates", {}).get("gate_1", {"status": "locked"})
    g2 = state.get("gates", {}).get("gate_2", {"status": "locked"})
    
    g1_status = g1.get("status") if isinstance(g1, dict) else g1
    g2_status = g2.get("status") if isinstance(g2, dict) else g2
    
    if g1_status != "approved":
        errors.append(f"Gate 1 is not approved (current: {g1_status})")
    if g2_status != "approved":
        errors.append(f"Gate 2 is not approved (current: {g2_status})")
        
    return {"ok": len(errors) == 0, "errors": errors}
