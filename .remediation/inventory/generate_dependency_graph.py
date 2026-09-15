import os
import json
import re
from collections import defaultdict

IGNORE_DIRS = {'.git', 'node_modules', 'venv', '.venv', '__pycache__', '.pytest_cache', '.remediation'}

def get_all_files(root_dir):
    files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            files.append(os.path.relpath(os.path.join(dirpath, f), root_dir).replace('\\', '/'))
    return files

def resolve_python_module(module_name, all_files):
    parts = module_name.split('.')
    path1 = "/".join(parts) + ".py"
    path2 = "/".join(parts) + "/__init__.py"
    if path1 in all_files: return path1
    if path2 in all_files: return path2
    return None

def resolve_ts_module(base_path, import_str, all_files):
    if not import_str.startswith('.'):
        return None
    
    base_dir = os.path.dirname(base_path)
    norm_path = os.path.normpath(os.path.join(base_dir, import_str)).replace('\\', '/')
    
    for ext in ['.ts', '.tsx', '/index.ts', '/index.tsx', '.js', '.jsx']:
        test_path = norm_path + ext if not ext.startswith('/') else norm_path + ext
        if test_path in all_files:
            return test_path
            
    return None

def map_dependencies(files):
    files_set = set(files)
    graph = {}
    
    for f in files:
        imports = []
        mentions = []
        
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                
                if f.endswith('.py'):
                    py_imports = re.findall(r'^(?:from\s+([a-zA-Z0-9_\.]+)\s+)?import\s+([a-zA-Z0-9_\.\, ]+)', content, re.MULTILINE)
                    for m in py_imports:
                        module = m[0] if m[0] else m[1].split(',')[0].strip()
                        resolved = resolve_python_module(module, files_set)
                        if resolved:
                            imports.append(resolved)
                            
                elif f.endswith(('.ts', '.tsx', '.js', '.jsx')):
                    ts_imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content)
                    for imp in ts_imports:
                        resolved = resolve_ts_module(f, imp, files_set)
                        if resolved:
                            imports.append(resolved)
                            
                elif f.endswith('.md'):
                    words = content.split()
                    for w in words:
                        w_clean = re.sub(r'[^a-zA-Z0-9_/\.-]', '', w)
                        if w_clean in files_set:
                            mentions.append(w_clean)
                            
        except Exception:
            pass
            
        graph[f] = {"imports": list(set(imports)), "mentions": list(set(mentions))}
        
    return graph

def build_inverted_index(graph):
    imported_by = defaultdict(list)
    mentioned_by = defaultdict(list)
    
    for f, data in graph.items():
        for imp in data['imports']:
            imported_by[imp].append(f)
        for men in data['mentions']:
            mentioned_by[men].append(f)
            
    return imported_by, mentioned_by

def generate_report(graph, imported_by, mentioned_by, out_md):
    lines = []
    lines.append("# Static Dependency Analysis Report\n")
    
    lines.append("## Top 20 Most Imported Files")
    sorted_imports = sorted(imported_by.items(), key=lambda x: len(x[1]), reverse=True)
    for f, importers in sorted_imports[:20]:
        lines.append(f"- `{f}` (imported by {len(importers)} files)")
        
    lines.append("\n## Top 20 Most Mentioned Files in Docs/Agent Files")
    sorted_mentions = sorted(mentioned_by.items(), key=lambda x: len(x[1]), reverse=True)
    for f, mentors in sorted_mentions[:20]:
        lines.append(f"- `{f}` (mentioned by {len(mentors)} files)")
        
    lines.append("\n## Potential Orphans (Code files not imported by anyone)")
    orphans = []
    for f in graph.keys():
        if f.endswith(('.py', '.ts', '.tsx')) and not f.endswith('__init__.py'):
            if f not in imported_by and 'test' not in f.lower() and 'pipeline' not in f.lower() and 'main' not in f.lower():
                orphans.append(f)
                
    for f in orphans[:100]:
        lines.append(f"- `{f}`")
    if len(orphans) > 100:
        lines.append(f"- ... and {len(orphans)-100} more.")
        
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

if __name__ == "__main__":
    files = get_all_files('.')
    graph = map_dependencies(files)
    imported_by, mentioned_by = build_inverted_index(graph)
    
    out_json = '.remediation/evidence/static-dependency-graph.json'
    out_md = '.remediation/evidence/static-dependency-graph.md'
    
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump({
            "graph": graph,
            "imported_by": imported_by,
            "mentioned_by": mentioned_by
        }, f, indent=2, ensure_ascii=False)
        
    generate_report(graph, imported_by, mentioned_by, out_md)
    print(f"Generated dependency graph and saved to {out_json} and {out_md}.")
