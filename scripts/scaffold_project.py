import argparse
import sys
import uuid
import json
import datetime
from pathlib import Path

def generate_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

def main():
    parser = argparse.ArgumentParser(description="Scaffold a new Clean Video Workspace project")
    parser.add_argument("--name", required=True)
    parser.add_argument("--aspect", required=True)
    parser.add_argument("--fps", type=int, required=True)
    parser.add_argument("--language", required=True)
    
    args = parser.parse_args()

    project_id = f"prj_{uuid.uuid4().hex[:8]}"
    project_dir = Path(f"projects/{project_id}")
    
    try:
        # Create directories
        for sub in ["assets/incoming", "assets/cache", "assets/ready", "06_build"]:
            (project_dir / sub).mkdir(parents=True, exist_ok=True)
            
        timestamp = generate_timestamp()
        
        # project.json
        project_data = {
            "project_id": project_id,
            "name": args.name,
            "aspect": args.aspect,
            "fps": args.fps,
            "language": args.language,
            "voiceover": {"mode": "none"},
            "created_at": timestamp
        }
        (project_dir / "project.json").write_text(json.dumps(project_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # state.json
        state_data = {
            "project_id": project_id,
            "current_stage": 0,
            "updated_at": timestamp,
            "stages": {
                "0": {"status": "pending", "started_at": timestamp, "finished_at": None},
                "1": {"status": "pending", "started_at": None, "finished_at": None},
                "2": {"status": "pending", "started_at": None, "finished_at": None},
                "3": {"status": "pending", "started_at": None, "finished_at": None}
            },
            "gates": {
                "gate_1": {"status": "locked", "approved_at": None, "approved_by": None},
                "gate_2": {"status": "locked", "approved_at": None, "approved_by": None},
                "gate_3": {"status": "locked", "approved_at": None, "approved_by": None}
            }
        }
        (project_dir / "state.json").write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # brand.json
        brand_data = {
            "brandName": "Default Brand",
            "fonts": {
                "display": "Cairo",
                "body": "IBMPlexSansArabic"
            },
            "colors": {
                "primary": "#FF5733",
                "accent": "#33FF57",
                "background": "#111111",
                "text": "#EAEAEA"
            }
        }
        (project_dir / "brand.json").write_text(json.dumps(brand_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # overrides.json
        overrides_data = {
            "project_id": project_id,
            "scenes": []
        }
        (project_dir / "overrides.json").write_text(json.dumps(overrides_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # manifest.json
        manifest_data = {
            "project_id": project_id,
            "generated_at": timestamp,
            "assets": []
        }
        (project_dir / "manifest.json").write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # .studio_approved
        (project_dir / ".studio_approved").write_text("", encoding="utf-8")
        
        print(project_id)
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
