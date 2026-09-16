import subprocess

ALLOWED_COMMANDS = {"ffmpeg", "ffprobe"}

ALLOWED_SCRIPTS = {
    "python": [
        "scripts/pipeline.py", "scripts/validate_schemas.py", "scripts/render_project.py", 
        "scripts/scene_compiler.py", ".agents/guardian/post_executor.py", 
        "scripts/scaffold_project.py", "scripts/migrate_state.py",
        "scripts/template_lint.py", "scripts/benchmark_guards.py",
        "scripts/asset_gate.py", "scripts/plan_gate.py", "scripts/taste_gate.py",
        "scripts/validate_blueprint.py", "scripts/motion_validator.py",
        "scripts/code_template_gate.py", "scripts/materialize_project.py", "scripts/probe_qc.py"
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
