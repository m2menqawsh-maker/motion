import os
import json
import re

def find_python_mains(root_dir):
    mains = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in {'.git', 'node_modules', 'venv', '.venv', '__pycache__', '.remediation'}]
        for f in filenames:
            if f.endswith('.py'):
                full_path = os.path.join(dirpath, f)
                rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as file:
                        content = file.read()
                        if 'if __name__ == "__main__":' in content or "if __name__ == '__main__':" in content:
                            mains.append({
                                "type": "python_cli",
                                "source_file": rel_path
                            })
                except Exception:
                    pass
    return mains

def find_fastapi_routes(root_dir):
    routes = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in {'.git', 'node_modules', 'venv', '.venv', '__pycache__', '.remediation'}]
        for f in filenames:
            if f.endswith('.py'):
                full_path = os.path.join(dirpath, f)
                rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as file:
                        content = file.read()
                        matches = re.findall(r'@(?:app|router)\.(get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', content)
                        for method, route in matches:
                            routes.append({
                                "type": "api_route",
                                "method": method.upper(),
                                "route": route,
                                "source_file": rel_path
                            })
                except Exception:
                    pass
    return routes

def find_package_scripts(root_dir):
    scripts = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in {'.git', 'node_modules', 'venv', '.venv', '__pycache__', '.remediation'}]
        if 'package.json' in filenames:
            full_path = os.path.join(dirpath, 'package.json')
            rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
            try:
                with open(full_path, 'r', encoding='utf-8') as file:
                    pkg = json.load(file)
                    if 'scripts' in pkg:
                        for name, cmd in pkg['scripts'].items():
                            scripts.append({
                                "type": "npm_script",
                                "name": name,
                                "command": cmd,
                                "source_file": rel_path
                            })
            except Exception:
                pass
    return scripts

def find_cognitive_entrypoints(root_dir):
    cognitive = []
    target_dirs = ['references', 'commands', 'workflows']
    for t_dir in target_dirs:
        if os.path.exists(os.path.join(root_dir, t_dir)):
            for dirpath, _, filenames in os.walk(os.path.join(root_dir, t_dir)):
                for f in filenames:
                    if f.endswith('.md'):
                        full_path = os.path.join(dirpath, f)
                        rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
                        cognitive.append({
                            "type": "cognitive_agentic",
                            "source_file": rel_path
                        })
    if os.path.exists(os.path.join(root_dir, '.agents', 'AGENTS.md')):
        cognitive.append({
            "type": "cognitive_agentic",
            "source_file": ".agents/AGENTS.md"
        })
    return cognitive

if __name__ == "__main__":
    entrypoints = []
    entrypoints.extend(find_python_mains('.'))
    entrypoints.extend(find_fastapi_routes('.'))
    entrypoints.extend(find_package_scripts('.'))
    entrypoints.extend(find_cognitive_entrypoints('.'))
    
    out_path = '.remediation/inventory/entrypoints.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({"entrypoints": entrypoints}, f, indent=2, ensure_ascii=False)
    print(f"Found {len(entrypoints)} entrypoints. Saved to {out_path}.")
