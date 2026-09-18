import json
import shutil
import sys
from pathlib import Path

def migrate_project(project_dir: Path):
    if not project_dir.is_dir():
        return False
    
    migrated = False

    # 1. Blueprint
    old_bp = project_dir / 'blueprint.json'
    new_bp = project_dir / '05_blueprint.json'
    if old_bp.exists() and not new_bp.exists():
        shutil.move(str(old_bp), str(new_bp))
        migrated = True

    # 2. Manifest
    old_manifest = project_dir / 'manifest.json'
    new_manifest = project_dir / '02_asset_manifest.json'
    if old_manifest.exists() and not new_manifest.exists():
        shutil.move(str(old_manifest), str(new_manifest))
        migrated = True

    # 3. State consolidation
    state_files = ['state.json', '.session_state.json', '.pipeline_checkpoint.json']
    new_state_path = project_dir / '.pipeline_state.json'
    
    merged_state = {}
    if new_state_path.exists():
        try:
            merged_state = json.loads(new_state_path.read_text(encoding='utf-8'))
        except:
            pass

    state_migrated = False
    for sf in state_files:
        old_sf = project_dir / sf
        if old_sf.exists():
            try:
                old_data = json.loads(old_sf.read_text(encoding='utf-8'))
                # Very basic merge logic for legacy to new
                if 'current_stage' in old_data and 'legacy_gui_state' not in merged_state:
                    merged_state['legacy_gui_state'] = {
                        'current_stage': str(old_data['current_stage']),
                        'status': old_data.get('status', 'started')
                    }
                old_sf.rename(old_sf.with_suffix('.json.deprecated'))
                state_migrated = True
            except Exception as e:
                print(f"Error reading {old_sf}: {e}")

    if state_migrated:
        new_state_path.write_text(json.dumps(merged_state, indent=2, ensure_ascii=False), encoding='utf-8')
        migrated = True

    return migrated

def main():
    projects_dir = Path('projects')
    if not projects_dir.exists():
        print("No projects directory found.")
        return

    count = 0
    for proj in projects_dir.iterdir():
        if migrate_project(proj):
            print(f"Migrated {proj.name}")
            count += 1
            
    print(f"Migration completed. {count} projects migrated.")

if __name__ == '__main__':
    main()
