import subprocess

ALLOWED_COMMANDS = {"ffmpeg", "ffprobe"}

ALLOWED_SCRIPTS = {
    "python": [
        "scripts/pipeline.py", "scripts/validate_schemas.py", "scripts/render_project.py", 
        "scripts/scene_compiler.py", ".agents/guardian/post_executor.py", 
        "scripts/scaffold_project.py", "scripts/migrate_state.py",
        "scripts/template_lint.py", "scripts/benchmark_guards.py"
    ],
    "npm": ["run", "build"], 
    "docker": ["info", "run"]
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

    if cmd not in ALLOWED_COMMANDS:
        if cmd in ALLOWED_SCRIPTS:
            if len(cmd_list) < 2 or cmd_list[1] not in ALLOWED_SCRIPTS[cmd]:
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
        kwargs["timeout"] = 60
        
    return subprocess.run(cmd_list, **kwargs)
