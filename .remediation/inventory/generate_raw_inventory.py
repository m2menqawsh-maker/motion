import os
import json
from datetime import datetime

IGNORE_DIRS = {'.git', 'node_modules', 'venv', '.venv', '__pycache__', '.pytest_cache', '.remediation'}

def get_inventory(root_dir):
    inventory = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # modify dirnames in-place to ignore certain directories
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
            
            try:
                stat = os.stat(full_path)
                inventory.append({
                    "path": rel_path,
                    "type": os.path.splitext(f)[1][1:] if os.path.splitext(f)[1] else "unknown",
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "directory": os.path.dirname(rel_path)
                })
            except Exception as e:
                print(f"Error reading {full_path}: {e}")
                
    return inventory

if __name__ == "__main__":
    inv = get_inventory('.')
    out_path = '.remediation/inventory/raw-files.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(inv, f, indent=2, ensure_ascii=False)
    print(f"Inventory saved to {out_path}. Total files: {len(inv)}")
