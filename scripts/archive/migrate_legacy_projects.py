import json
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone

def generate_timestamp():
    return datetime.now(timezone.utc).isoformat()

def migrate_project(project_dir: Path):
    if not project_dir.is_dir():
        return False
        
    project_id = project_dir.name
    migrated = False

    # 1. Blueprint
    old_bp = project_dir / 'blueprint.json'
    new_bp = project_dir / '05_blueprint.json'
    if old_bp.exists():
        if not new_bp.exists():
            shutil.move(str(old_bp), str(new_bp))
            migrated = True
        else:
            old_bp.rename(old_bp.with_suffix('.json.conflict'))

    # 2. Manifest
    old_manifest = project_dir / 'manifest.json'
    new_manifest = project_dir / '02_asset_manifest.json'
    if old_manifest.exists():
        if not new_manifest.exists():
            shutil.move(str(old_manifest), str(new_manifest))
            migrated = True
        else:
            old_manifest.rename(old_manifest.with_suffix('.json.conflict'))

    # 3. State consolidation
    state_files = ['state.json', '.session_state.json', '.pipeline_checkpoint.json']
    new_state_path = project_dir / '.pipeline_state.json'
    
    # Base canonical state
    merged_state = {
        "project_id": project_id,
        "schema_version": 1,
        "revision": 1,
        "lifecycle_state": "DRAFT",
        "run_metadata": {},
        "approval_metadata": {},
        "structured_errors": [],
        "artifact_records": [],
        "created_at": generate_timestamp(),
        "updated_at": generate_timestamp()
    }
    
    if new_state_path.exists():
        try:
            existing_state = json.loads(new_state_path.read_text(encoding='utf-8'))
            # Merge existing canonical state
            for k, v in existing_state.items():
                merged_state[k] = v
        except:
            pass

    state_migrated = False
    for sf in state_files:
        old_sf = project_dir / sf
        if old_sf.exists():
            try:
                old_data = json.loads(old_sf.read_text(encoding='utf-8'))
                
                # Derive some lifecycle info if possible
                if old_data.get('status') == 'done' or old_data.get('current_stage') == 4:
                    merged_state['lifecycle_state'] = 'COMPLETE'
                elif old_data.get('status') == 'failed':
                    merged_state['lifecycle_state'] = 'FAILED'
                    err = old_data.get('last_error') or old_data.get('error')
                    if err:
                        merged_state['structured_errors'].append({"source": "legacy_migration", "message": str(err)})

                old_sf.rename(old_sf.with_suffix('.json.deprecated'))
                state_migrated = True
            except Exception as e:
                print(f"Error reading {old_sf}: {e}")

    if state_migrated or not new_state_path.exists():
        # Always write canonical state if missing or if migrated
        merged_state['updated_at'] = generate_timestamp()
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
