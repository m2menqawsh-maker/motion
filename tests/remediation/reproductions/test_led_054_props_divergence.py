import pytest
import re
from pathlib import Path

def test_led_054_docker_local_props_divergence():
    """
    Finding: LED-054 (CLOSED in S17)
    Evolution: Evolved from S00 Expected-RED reproduction to S17 GREEN regression proof.
    Expected correct behavior: Local rendering and Docker rendering must invoke Remotion
    with the exact same payload schema/props structure (render_props.json).
    """
    render_script = Path.cwd() / "scripts" / "render_project.py"
    content = render_script.read_text(encoding="utf-8")
    
    # Local passes --props str(props_file_abs) which is render_props.json
    local_props_match = re.search(r'remotion.*render.*--props.*props_file', content)
    assert local_props_match is not None, "Local render must pass props_file (render_props.json)"
    
    # Docker must pass render_props.json
    docker_props_match = re.search(r'--props \.\./projects/\{project_id\}/render_props\.json', content)
    assert docker_props_match is not None, "Docker render must pass render_props.json"
    
    # Raw 05_blueprint.json must NOT be passed as props to Remotion
    raw_bp_match = re.search(r'--props \.\./projects/\{project_id\}/05_blueprint\.json', content)
    assert raw_bp_match is None, "Docker must not pass raw 05_blueprint.json directly"
    
    # Studio script must also have parity
    studio_script = Path.cwd() / "scripts" / "open_studio.py"
    studio_content = studio_script.read_text(encoding="utf-8")
    assert re.search(r'--props.*render_props\.json', studio_content) is not None, (
        "Studio in Docker mode must pass render_props.json"
    )
    assert "--props ../projects/{project_id}/05_blueprint.json" not in studio_content, (
        "Studio must not pass raw 05_blueprint.json"
    )
