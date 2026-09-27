import pytest
import re
from pathlib import Path

def test_led_054_docker_local_props_divergence():
    """
    Finding: LED-054
    Owner Package: S17 (Docker Parity)
    Expected correct behavior: Local rendering and Docker rendering must invoke Remotion
    with the exact same payload schema/props structure.
    Actual behavior on current main:
        - Local render passes: render_props.json (wrapped projectData)
        - Docker render passes: 05_blueprint.json (raw Blueprint schema)
    """
    render_script = Path.cwd() / "scripts" / "render_project.py"
    content = render_script.read_text(encoding="utf-8")
    
    # Local passes --props str(props_file_abs) which is render_props.json
    local_props_match = re.search(r'remotion.*render.*--props.*props_file', content)
    assert local_props_match is not None
    
    # Docker passes --props ../projects/{project_id}/05_blueprint.json
    docker_props_match = re.search(r'--props \.\./projects/\{project_id\}/05_blueprint\.json', content)
    assert docker_props_match is not None
    
    # Assertion proving the defect:
    # Correct behavior: Docker must not pass raw blueprint while Local passes combined render_props.json
    # Current behavior on main: They diverge!
    has_props_divergence = (local_props_match is not None) and (docker_props_match is not None)
    assert not has_props_divergence, (
        "DEFECT PROVEN (LED-054): Local render passes 'render_props.json' (projectData wrapper), "
        "while Docker render passes '05_blueprint.json' directly. The render payload contract is split!"
    )
