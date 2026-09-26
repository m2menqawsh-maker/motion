import subprocess

ALLOWED_COMMANDS = {"ffmpeg", "ffprobe"}

ALLOWED_SCRIPTS = {
    "python": [
        "scripts/pipeline.py", "scripts/validators/validate_schemas.py", "scripts/render_project.py", 
        "scripts/maintenance/scene_compiler.py", ".agents/guardian/post_executor.py", 
        "scripts/scaffold_project.py", "scripts/archive/migrate_state.py",
        "scripts/validators/template_lint.py", "scripts/metrics/benchmark_guards.py",
        "scripts/gates/asset_gate.py", "scripts/gates/plan_gate.py", "scripts/gates/taste_gate.py",
        "scripts/gates/validate_blueprint.py", "scripts/gates/motion_validator.py",
        "scripts/gates/code_template_gate.py", "scripts/generators/materialize_project.py", "scripts/gates/probe_qc.py", "scripts/gates/final_qc.py"
    ],
    "npm": ["run", "build"], 
    "docker": ["info", "run"],
    "npx": ["remotion"],
    "npx.cmd": ["remotion"]
}

def safe_subprocess(cmd_list, **kwargs):
    if isinstance(cmd_list, str):
        cmd_list = cmd_list.split()

    if not cmd_list:
        raise PermissionError("Empty command")

    cmd = cmd_list[0]
    
    # Strip path from python/npm/docker just in case they are absolute
    if "python" in cmd: cmd = "python"
    elif "npm" in cmd: cmd = "npm"
    elif "docker" in cmd: cmd = "docker"
    elif "npx.cmd" in cmd: cmd = "npx.cmd"
    elif "npx" in cmd: cmd = "npx"

    if cmd not in ALLOWED_COMMANDS:
        if cmd in ALLOWED_SCRIPTS:
                if len(cmd_list) >= 2:
                    # Normalize slashes for Windows
                    normalized_script = cmd_list[1].replace("\\", "/")
                else:
                    normalized_script = ""
                
                is_allowed = False
                if len(cmd_list) >= 2:
                    for allowed in ALLOWED_SCRIPTS[cmd]:
                        if normalized_script == allowed or normalized_script.endswith("/" + allowed):
                            is_allowed = True
                            break
                            
                if not is_allowed:
                    # Allow npm run build specifically
                    if cmd == "npm" and len(cmd_list) >= 3 and cmd_list[1] == "run" and cmd_list[2] == "build":
                        pass # Valid
                    elif cmd == "docker":
                        pass # Valid for run and info
                    else:
                        raise PermissionError(f"Command not allowed: {' '.join(cmd_list)}")
        else:
            raise PermissionError(f"Command not allowed: {cmd}")
            
    # Force safe defaults
    kwargs["shell"] = False
    if "timeout" not in kwargs:
        kwargs["timeout"] = 900
        
    return subprocess.run(cmd_list, **kwargs)
