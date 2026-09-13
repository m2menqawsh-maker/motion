import os, json
from pathlib import Path

plugin_dir = Path(__file__).resolve().parent
workspace = plugin_dir.parents[2]

errors = []
warnings = []

# 1. Check plugin.json
try:
    with open(plugin_dir / 'plugin.json') as f:
        manifest = json.load(f)
    assert manifest['$schema'] == 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
    assert manifest['name'] == 'super-video-maker'
    print('PASS plugin.json valid')
except Exception as e:
    errors.append(f'plugin.json: {e}')

# 2. Check mcp_config.json
try:
    with open(plugin_dir / 'mcp_config.json') as f:
        mcp = json.load(f)
    assert len(mcp['mcpServers']) == 7
    print('PASS mcp_config.json valid (7 servers)')
except Exception as e:
    errors.append(f'mcp_config.json: {e}')

# 3. Check critical paths in WORKSPACE
critical_workspace = [
    'templates', 'engine', 'scripts', 'assets', 'projects',
    'documentation', 'config', '.agents',
    'scripts/core', 'scripts/render_project.py'
]
missing_ws = [p for p in critical_workspace if not (workspace / p).exists()]
if missing_ws:
    errors.append(f'Missing in workspace: {missing_ws}')
else:
    print(f'PASS All {len(critical_workspace)} critical workspace paths exist')

# 3.5 Check critical paths in PLUGIN
critical_plugin = [
    'skills/remocn/SKILL.md',
    'skills/snapcn/SKILL.md',
    'tools/mcp-servers',
    'commands', 'workflows'
]
missing_plugin = [p for p in critical_plugin if not (plugin_dir / p).exists()]
if missing_plugin:
    errors.append(f'Missing in plugin: {missing_plugin}')
else:
    print(f'PASS All {len(critical_plugin)} critical plugin paths exist')

# 4. Count templates
template_count = len([f for f in (workspace / 'templates').iterdir() if f.suffix in ['.tsx', '.ts']] if (workspace / 'templates').exists() else [])
print(f'PASS Templates: {template_count}')
if template_count < 100:
    warnings.append(f'Only {template_count} templates found (expected >= 100)')

# 5. Count MCP servers
mcp_dirs_path = plugin_dir / 'tools/mcp-servers'
mcp_dirs = [d.name for d in mcp_dirs_path.iterdir() if d.is_dir()] if mcp_dirs_path.exists() else []
print(f'PASS MCP servers: {len(mcp_dirs)} ({", ".join(mcp_dirs)})')

# 6. Count Python tools
tools_dir_path = plugin_dir / 'tools'
tool_count = len([f for f in tools_dir_path.iterdir() if f.is_file() and f.suffix == '.py']) if tools_dir_path.exists() else 0
print(f'PASS Python tools: {tool_count}')

# 7. Check no leftover temp files
temp_patterns = ['test.py', 'test2.py', 'rewrite.py', 'copy_script.py', 'patch_']
for root, dirs, files in os.walk(plugin_dir):
    if 'node_modules' in root or '__pycache__' in root or '.venv' in root:
        continue
    for f in files:
        for pat in temp_patterns:
            if f.startswith(pat) or f == pat:
                warnings.append(f'Possible temp file in plugin: {os.path.join(root, f)}')

# 8. Summary
print(f'\n{"="*50}')
print(f'FINAL VERIFICATION SUMMARY')
print(f'{"="*50}')
if errors:
    print(f'FAIL ERRORS ({len(errors)}):')
    for e in errors: print(f'   - {e}')
else:
    print('PASS No errors')
if warnings:
    print(f'WARNINGS ({len(warnings)}):')
    for w in warnings: print(f'   - {w}')
else:
    print('PASS No warnings')
print(f'{"="*50}')
print(f'PLUGIN STATUS: {"READY FOR DISTRIBUTION" if not errors else "NEEDS FIXES"}')
