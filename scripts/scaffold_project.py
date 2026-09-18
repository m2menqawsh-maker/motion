import subprocess
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.security import safe_subprocess
from scripts.path_security import validate_project_id, safe_resolve
import uuid
import json
import datetime
from pathlib import Path
import asyncio
from api.services.pipeline_service import PipelineService

def generate_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

def main():
    parser = argparse.ArgumentParser(description="Scaffold a new Clean Video Workspace project")
    parser.add_argument("--name", required=True)
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
            "language": args.language,
            "voiceover": {"mode": "none"},
            "created_at": timestamp
        }
        (project_dir / "project.json").write_text(json.dumps(project_data, ensure_ascii=False, indent=2), encoding="utf-8")
        # .pipeline_state.json
        asyncio.run(PipelineService.scaffold_project(project_id))

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
        
        # 02_asset_manifest.json
        manifest_data = {
            "project_id": project_id,
            "generated_at": timestamp,
            "assets": []
        }
        (project_dir / "02_asset_manifest.json").write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # .studio_approved MUST NOT be created automatically. The user creates it after Probe QC.
        
        print(project_id)
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
