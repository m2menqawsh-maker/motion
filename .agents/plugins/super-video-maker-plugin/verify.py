import os, json

base = 'c:/video/video-workspace/super-video-maker-plugin'
errors = []
warnings = []

# 1. Check plugin.json
try:
    with open(f'{base}/plugin.json') as f:
        manifest = json.load(f)
    assert manifest['$schema'] == 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
    assert manifest['name'] == 'super-video-maker'
    print('PASS plugin.json valid')
except Exception as e:
    errors.append(f'plugin.json: {e}')

# 2. Check mcp.json
try:
    with open(f'{base}/mcp.json') as f:
        mcp = json.load(f)
    assert len(mcp['mcpServers']) == 7
    print('PASS mcp.json valid (7 servers)')
except Exception as e:
    errors.append(f'mcp.json: {e}')

# 3. Check critical paths
critical = [
    'skills/super-video-maker/SKILL.md',
    'templates', 'cinematic-engine', 'recipes', 'tools',
    'tools/mcp-servers', 'references', 'remotion-app',
    'remotion-app/package.json', 'remotion-app/tsconfig.json',
    'remotion-app/src/Root.tsx',
    'scripts/sync_templates.py',
    '.env.example', '.gitignore', 'README.md',
    'package.json', 'requirements.txt',
]
missing = [p for p in critical if not os.path.exists(os.path.join(base, p))]
if missing:
    errors.append(f'Missing: {missing}')
else:
    print(f'PASS All {len(critical)} critical paths exist')

# 4. Count templates
template_count = len([f for f in os.listdir(f'{base}/templates') if f.endswith('.tsx')])
print(f'PASS Templates: {template_count}')
if template_count < 75:
    warnings.append(f'Only {template_count} templates found (expected ~81)')

# 5. Count recipes
recipe_count = len([f for f in os.listdir(f'{base}/recipes') if f.endswith('.json') and f != 'schema.json'])
print(f'PASS Recipes: {recipe_count}')

# 6. Count MCP servers
mcp_dirs = os.listdir(f'{base}/tools/mcp-servers')
print(f'PASS MCP servers: {len(mcp_dirs)} ({", ".join(mcp_dirs)})')

# 7. Count Python tools
tool_count = len([f for f in os.listdir(f'{base}/tools') if f.endswith('.py')])
print(f'PASS Python tools: {tool_count}')

# 8. Check references
ref_count = 0
for root, dirs, files in os.walk(f'{base}/references'):
    ref_count += len([f for f in files if f.endswith('.md')])
print(f'PASS Reference docs: {ref_count}')

# 9. Check no leftover temp files
temp_patterns = ['test.py', 'test2.py', 'rewrite.py', 'copy_script.py', 'patch_']
for root, dirs, files in os.walk(base):
    if 'node_modules' in root or '__pycache__' in root:
        continue
    for f in files:
        for pat in temp_patterns:
            if f.startswith(pat) or f == pat:
                warnings.append(f'Possible temp file: {os.path.join(root, f)}')

# 10. Summary
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
