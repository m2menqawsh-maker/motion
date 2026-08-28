import os
import json
import hashlib
from pathlib import Path

def get_file_hash(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except:
        return None

def get_base_name(filename):
    name = Path(filename).stem
    suffixes_to_remove = ["_norm", "_normalized", "_final", "_raw", "_processed"]
    for s in suffixes_to_remove:
        name = name.replace(s, "")
    return name

def determine_type(filepath):
    path_str = str(filepath).lower()
    if path_str.endswith(".svg") or path_str.endswith(".png") or path_str.endswith(".jpg"):
        return "icon" if "icon" in path_str else "image"
    if path_str.endswith(".mp4") or path_str.endswith(".mov") or path_str.endswith(".webm"):
        return "video"
    if "sfx" in path_str:
        return "sfx"
    if "vo" in path_str or "voice" in path_str:
        return "vo"
    if "music" in path_str:
        return "music"
    if path_str.endswith(".wav") or path_str.endswith(".mp3"):
        return "audio"
    return "other"

def main():
    dirs = {
        "assets/ready": "ready",
        "assets/cache": "cache-raw",
        "assets/incoming": "incoming"
    }
    
    index = []
    
    for dir_path_str, state in dirs.items():
        dir_path = Path(dir_path_str)
        if not dir_path.exists():
            continue
            
        VALID_EXTS = {".wav", ".mp3", ".mp4", ".mov", ".svg", ".png", ".jpg", ".jpeg", ".webp"}
        for root, _, files in os.walk(dir_path):
            for file in files:
                filepath = Path(root) / file
                if filepath.suffix.lower() not in VALID_EXTS:
                    continue
                    
                # Use forward slashes for cross-platform consistency in JSON
                rel_path = filepath.as_posix()
                
                # Try to extract lufs if applicable (mock logic, as we don't parse wav metadata here without ffmpeg)
                lufs = -16 if ("vo" in str(filepath) and "_norm" in file) else (-24 if ("sfx" in str(filepath) and "_norm" in file) else None)
                
                entry = {
                    "name": file,
                    "base": get_base_name(file),
                    "type": determine_type(filepath),
                    "state": state,
                    "path": rel_path,
                    "hash": get_file_hash(filepath),
                    "lufs": lufs
                }
                index.append(entry)
                
    output_path1 = Path(".agents/plugins/super-video-maker-plugin/ground-truth/ASSET_INDEX.json")
    output_path1.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path1, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        
    print(f"Generated ASSET_INDEX.json with {len(index)} entries.")
    
    # Print first 10 entries as requested
    print(json.dumps(index[:10], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
