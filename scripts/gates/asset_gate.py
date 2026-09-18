import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import subprocess
from scripts.security.security import safe_subprocess
import json
from scripts.security.path_security import validate_project_id, safe_resolve

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def get_base_name(filename):
    name = Path(filename).stem
    suffixes_to_remove = ["_norm", "_normalized", "_final", "_raw", "_processed"]
    for s in suffixes_to_remove:
        name = name.replace(s, "")
    return name

def run_gate(manifest_path_str):
    manifest_path = Path(manifest_path_str)
    if (Path("projects") / manifest_path / "02_asset_manifest.json").exists():
        manifest_path = Path("projects") / manifest_path / "02_asset_manifest.json"
    elif manifest_path.is_dir() and (manifest_path / "02_asset_manifest.json").exists():
        manifest_path = manifest_path / "02_asset_manifest.json"

    if not manifest_path.exists():
        return True, "No manifest found, passing."

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception as e:
        return False, f"Failed to read manifest: {e}"

    repo_root = Path(__file__).resolve().parent.parent.parent
    index_path = repo_root / "ground-truth" / "ASSET_INDEX.json"
    index = []
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

    items = manifest.get("assets", []) if isinstance(manifest, dict) else manifest
    for item in items:
        source = item.get("source")
        if source == "user_upload":
            continue
            
        if source == "mcp_fetch":
            # 1. Check cache_checked
            if item.get("cache_checked") is not True:
                return False, f"FAIL: Asset {item.get('id', 'unknown')} has source 'mcp_fetch' but cache_checked is not true."
                
            # 2. Check if ASSET_INDEX has a match
            item_type = item.get("type")
            item_path = item.get("path", "")
            item_base = get_base_name(item_path) if item_path else ""
            item_hash = item.get("hash")
            
            for index_entry in index:
                if index_entry.get("state") == "ready":
                    match_found = False
                    
                    if index_entry.get("type") == item_type:
                        if index_entry.get("base") == item_base and item_base != "":
                            match_found = True
                        elif item_hash and index_entry.get("hash") == item_hash:
                            match_found = True
                            
                    if match_found:
                        return False, f"أصل معالج موجود مسبقاً: {index_entry.get('path')} — استخدمه بدل الجلب"

    return True, "PASS"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python asset_gate.py <manifest_path>")
        sys.exit(1)
        
    manifest_path = sys.argv[1]
    success, msg = run_gate(manifest_path)
    print(msg)
    if not success:
        sys.exit(1)
