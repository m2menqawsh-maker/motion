import os
import shutil
from pathlib import Path
import hashlib

def get_base_name(filename):
    name = Path(filename).stem
    name = name.replace("_norm", "").replace("_normalized", "")
    return name

def get_quality_score(filepath):
    # wav normalized is best, then wav, then mp3/mp4 etc.
    score = 0
    path_str = str(filepath).lower()
    if path_str.endswith(".wav"):
        score += 10
    if "_norm" in path_str or "_normalized" in path_str:
        score += 20
    if path_str.endswith(".mp4"):
        score += 10 # Video quality is high
    if path_str.endswith(".svg"):
        score += 10 # Icon quality
    return score

def determine_type(filepath):
    path_str = str(filepath).lower()
    if path_str.endswith(".svg"):
        return "icons"
    if path_str.endswith(".mp4") or path_str.endswith(".mov") or path_str.endswith(".webm"):
        return "video"
    if "sfx" in path_str:
        return "sfx"
    if "vo" in path_str or "voice" in path_str:
        return "vo"
    if "music" in path_str:
        return "music"
    if path_str.endswith(".wav") or path_str.endswith(".mp3"):
        # default audio to audio/ if unknown
        return "audio"
    return "other"

def main():
    dirs_to_check = ["processed", "storage"]
    ready_dir = Path("assets/ready")
    
    # Create structure
    for t in ["audio", "sfx", "music", "vo", "video", "icons", "other"]:
        (ready_dir / t).mkdir(parents=True, exist_ok=True)

    # Track best files: { "base_name": {"score": X, "path": Path} }
    best_files = {}

    for d in dirs_to_check:
        dir_path = Path(d)
        if not dir_path.exists():
            continue
            
        for root, _, files in os.walk(dir_path):
            for file in files:
                filepath = Path(root) / file
                base = get_base_name(file)
                score = get_quality_score(filepath)
                
                # Use base name + type as key to avoid grouping vo with video if they happen to have same base name
                file_type = determine_type(filepath)
                key = f"{base}_{file_type}"
                
                if key not in best_files or score > best_files[key]["score"]:
                    best_files[key] = {"score": score, "path": filepath, "type": file_type}

    print(f"Found {len(best_files)} unique assets to migrate.")

    # Copy files
    for key, data in best_files.items():
        src = data["path"]
        file_type = data["type"]
        dest = ready_dir / file_type / src.name
        
        if not dest.exists():
            shutil.copy2(src, dest)
            print(f"Copied {src} -> {dest}")

if __name__ == "__main__":
    main()
