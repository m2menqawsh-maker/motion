import subprocess
from scripts.security import safe_subprocess
#!/usr/bin/env python3
import sys
from scripts.path_security import validate_project_id, safe_resolve
import os
import shutil
from pathlib import Path

def main():
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    
    workspace = Path(__file__).resolve().parents[1]
    assets_dir = workspace / "assets"
    
    dirs_to_clean = [
        assets_dir / "processing",
        assets_dir / "incoming"
    ]
    
    archive_dir = assets_dir / "archive"
    
    if not archive_dir.exists():
        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created archive directory: {archive_dir}")
        else:
            print(f"[DRY-RUN] Would create archive directory: {archive_dir}")
            
    files_to_move = []
    
    for d in dirs_to_clean:
        if d.exists():
            for root, _, files in os.walk(d):
                for file in files:
                    if file == ".gitkeep":
                        continue
                    files_to_move.append(Path(root) / file)
                    
    if not files_to_move:
        print("✅ No files found to clean up.")
        return
        
    print(f"Found {len(files_to_move)} files to clean up:")
    for f in files_to_move:
        try:
            print(f" - {f.relative_to(assets_dir)}")
        except ValueError:
            print(f" - {f}")
        
    if dry_run:
        print("\n[DRY-RUN] This was a dry run. No files were moved.")
        return
        
    if not force:
        confirm = input(f"\nAre you sure you want to move {len(files_to_move)} files to {archive_dir}? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return
        
    moved_count = 0
    for f in files_to_move:
        try:
            rel_path = f.relative_to(assets_dir)
            dest = archive_dir / rel_path
        except ValueError:
            dest = archive_dir / f.name
            
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(f), str(dest))
            moved_count += 1
        except Exception as e:
            print(f"❌ Failed to move {f.name}: {e}")
            
    print(f"✅ Successfully moved {moved_count} files to {archive_dir}.")

if __name__ == "__main__":
    main()
