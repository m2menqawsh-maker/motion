import json
import os
import re
from pathlib import Path

def resolve_import(base_file, import_path):
    if import_path.startswith('.'):
        base_dir = os.path.dirname(base_file)
        resolved = os.path.normpath(os.path.join(base_dir, import_path))
        # could be .ts, .tsx, .py, etc.
        for ext in ['', '.ts', '.tsx', '.js', '.py', '/index.ts', '/index.tsx']:
            candidate = resolved + ext
            if os.path.exists(candidate):
                return candidate.replace('\\', '/')
    else:
        # absolute or node_modules
        pass
    return None

def main():
    with open('.remediation/phase-9/executable-surface.json', 'r', encoding='utf-8') as f:
        surface = json.load(f)

    # Load Phase 9.5 files if available
    agent_paths = set()
    try:
        with open('.remediation/phase-9/agent-surface.json', 'r', encoding='utf-8') as f:
            agent_surface = json.load(f)
            for item in agent_surface:
                agent_paths.add(item.get('path', '').replace('\\', '/'))
    except Exception:
        pass

    try:
        with open('.remediation/phase-9/mcp-tool-inventory.json', 'r', encoding='utf-8') as f:
            mcp = json.load(f)
            for item in mcp:
                agent_paths.add(item.get('executable_path', '').replace('\\', '/'))
    except Exception:
        pass

    # Find package.json scripts
    package_scripts_invocations = set()
    try:
        with open('package.json', 'r', encoding='utf-8') as f:
            pkg = json.load(f)
            for k, v in pkg.get('scripts', {}).items():
                package_scripts_invocations.add(v)
    except Exception:
        pass

    # Build graph
    edges = [] # (caller, callee, type)
    
    # 1. Regex find imports and subprocess calls
    for item in surface:
        path = item['path']
        try:
            content = Path(path).read_text(encoding='utf-8')
        except Exception:
            continue
            
        if path.endswith('.py'):
            # find subprocess calls to other scripts
            matches = re.findall(r'subprocess\.(?:run|Popen|check_output|check_call)\(\s*\[?[\'"]([a-zA-Z0-9_\-\.\/]+)[\'"]', content)
            for m in matches:
                edges.append((path, m, 'subprocess'))
                
            # python imports
            imports = re.findall(r'^(?:from|import)\s+([a-zA-Z0-9_\.]+)', content, re.MULTILINE)
            for imp in imports:
                # convert module to path approx
                module_path = imp.replace('.', '/') + '.py'
                if os.path.exists(module_path):
                    edges.append((path, module_path, 'import'))
                    
        elif path.endswith(('.ts', '.tsx', '.js')):
            imports = re.findall(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content)
            requires = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content)
            for imp in imports + requires:
                resolved = resolve_import(path, imp)
                if resolved:
                    edges.append((path, resolved, 'import'))
                    
    # Initialize reachability state
    for item in surface:
        item['agent_reachable'] = item['path'] in agent_paths
        item['production_reachable'] = False
        item['ci_reachable'] = False

    # Mark known production roots
    prod_roots = {'scripts/pipeline.py', 'scripts/open_studio.py', 'scripts/render_project.py'}
    for item in surface:
        if item['path'] in prod_roots:
            item['production_reachable'] = True
            
    # Mark known CI roots
    for item in surface:
        if '.github/workflows' in item['path'] or '.githooks' in item['path']:
            item['ci_reachable'] = True

    # Check package.json scripts for references
    for item in surface:
        filename = os.path.basename(item['path'])
        for script in package_scripts_invocations:
            if filename in script:
                # Roughly guess it's CI/Build reachable
                item['ci_reachable'] = True

    # Propagate reachability
    changed = True
    while changed:
        changed = False
        for caller, callee, _ in edges:
            caller_item = next((x for x in surface if x['path'] == caller), None)
            callee_item = next((x for x in surface if x['path'] == callee or callee in x['path']), None)
            
            if caller_item and callee_item:
                for prop in ['production_reachable', 'agent_reachable', 'ci_reachable']:
                    if caller_item[prop] and not callee_item[prop]:
                        callee_item[prop] = True
                        changed = True

    # Refine TSX/TS classification
    for item in surface:
        if item['language'] in ('.tsx', '.ts'):
            # If no dangerous features and in specific folders, mark high confidence UI
            if not item.get('subprocess_capable') and not item.get('filesystem_write') and not item.get('network_access'):
                if 'remotion-app' in item['path'] or 'templates' in item['path'] or 'registry' in item['path']:
                    item['classification'] = 'NON_EXECUTABLE_COMPONENT'
                    item['classification_confidence'] = 'high'
                    item['requires_manual_review'] = False
                    
        # Find explicit Zombies
        # A zombie is something not reachable by prod, agent, or CI, and not explicitly a test
        if not item['production_reachable'] and not item['agent_reachable'] and not item['ci_reachable']:
            if item['classification'] == 'UNKNOWN' and 'test' not in item['path']:
                item['classification'] = 'ZOMBIE_CANDIDATE'
                
    # Save outputs
    out_dir = Path('.remediation/phase-9')
    with open(out_dir / 'executable-reachability.json', 'w', encoding='utf-8') as f:
        json.dump({"edges": edges}, f, indent=2)
        
    with open(out_dir / 'executable-classification.json', 'w', encoding='utf-8') as f:
        json.dump(surface, f, indent=2)
        
    # Summary
    needs_review = [x for x in surface if x.get('requires_manual_review')]
    zombies = [x for x in surface if x.get('classification') == 'ZOMBIE_CANDIDATE']
    print(f"Updated classification.")
    print(f"Items needing manual review: {len(needs_review)}")
    print(f"Zombie candidates: {len(zombies)}")

if __name__ == '__main__':
    main()
