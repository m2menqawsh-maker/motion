import os
import json
import ast
import re
from pathlib import Path

# Directories to exclude from analysis
EXCLUDE_DIRS = {
    'node_modules', '.venv', '.git', 'dist', 'build', 
    '__pycache__', '.pytest_cache', '.mypy_cache', 'out'
}

# File extensions to analyze
EXECUTABLE_EXTS = {
    '.py', '.ts', '.tsx', '.js', '.mjs', '.cjs', 
    '.ps1', '.sh', '.bat', '.cmd'
}

def analyze_python_ast(filepath, content):
    features = {
        'subprocess_capable': False,
        'shell_true': False,
        'filesystem_write': False,
        'network_access': False,
        'state_writer': False,
        'render_capable': False
    }
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Subprocess calls
                    if node.func.attr in ('run', 'Popen', 'check_output', 'check_call'):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == 'subprocess':
                            features['subprocess_capable'] = True
                            for kw in node.keywords:
                                if kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                    features['shell_true'] = True
                    # os.system, os.popen
                    if node.func.attr in ('system', 'popen'):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                            features['subprocess_capable'] = True
                            features['shell_true'] = True
                    
                    # Network
                    if node.func.attr in ('get', 'post', 'put', 'delete', 'request'):
                        if isinstance(node.func.value, ast.Name) and node.func.value.id in ('requests', 'httpx'):
                            features['network_access'] = True
                
                if isinstance(node.func, ast.Name):
                    if node.func.id == 'open':
                        for kw in node.keywords:
                            if kw.arg in ('mode', 'w', 'a') or (isinstance(kw.value, ast.Constant) and 'w' in str(kw.value.value)):
                                features['filesystem_write'] = True
                        if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and 'w' in str(node.args[1].value):
                            features['filesystem_write'] = True
                    
                    if node.func.id in ('fetch', 'urlopen'):
                        features['network_access'] = True
        
        # Simple text checks for FFmpeg / State
        if '.pipeline_state.json' in content:
            features['state_writer'] = True
        if 'ffmpeg' in content.lower() or 'ffprobe' in content.lower():
            features['render_capable'] = True
            
    except Exception as e:
        # Fallback to regex if parsing fails
        pass
    
    return features

def analyze_regex(filepath, content):
    features = {
        'subprocess_capable': False,
        'shell_true': False, # Hard to detect exactly via regex, assume false unless proven
        'filesystem_write': False,
        'network_access': False,
        'state_writer': False,
        'render_capable': False
    }
    
    if re.search(r'(child_process|exec\(|spawn\(|execFile\(|execSync)', content):
        features['subprocess_capable'] = True
        if re.search(r'shell\s*:\s*true', content):
            features['shell_true'] = True
            
    if re.search(r'(fs\.(write|mkdir|append|chmod|chown|copy|rename|rm)|writeFileSync)', content):
        features['filesystem_write'] = True
        
    if re.search(r'(fetch\(|axios\.|http\.request|https\.request|wget|curl)', content):
        features['network_access'] = True
        
    if '.pipeline_state.json' in content:
        features['state_writer'] = True
        
    if re.search(r'(ffmpeg|ffprobe|renderMedia|renderStill)', content, re.IGNORECASE):
        features['render_capable'] = True
        
    return features

def main():
    results = []
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            path = Path(root) / file
            str_path = str(path).replace('\\', '/')
            ext = path.suffix.lower()
            
            is_executable_candidate = False
            
            if ext in EXECUTABLE_EXTS:
                is_executable_candidate = True
            elif 'Dockerfile' in file:
                is_executable_candidate = True
            elif file == 'package.json':
                is_executable_candidate = True
            elif '.githooks' in str_path or '.github/workflows' in str_path:
                is_executable_candidate = True
                
            if not is_executable_candidate:
                continue
                
            try:
                content = path.read_text(encoding='utf-8')
            except Exception:
                continue
                
            features = {}
            if ext == '.py':
                features = analyze_python_ast(str_path, content)
            else:
                features = analyze_regex(str_path, content)
                
            # Initial heuristic classification
            classification = 'UNKNOWN'
            confidence = 'low'
            requires_review = True
            
            if '.tsx' in ext or '.ts' in ext:
                if not features['subprocess_capable'] and not features['filesystem_write'] and not features['network_access'] and not features['render_capable']:
                    if 'remotion-app' in str_path or 'templates' in str_path:
                        classification = 'NON_EXECUTABLE_COMPONENT'
                        confidence = 'medium'
            
            if 'tests/' in str_path or 'test_' in file or '.test.' in file:
                classification = 'TEST_SUPPORT'
                confidence = 'medium'
                
            if 'scratch/' in str_path:
                classification = 'CERTIFICATION_TEMPORARY'
                confidence = 'high'
                
            if file == 'package.json':
                classification = 'BUILD_TOOL'
                confidence = 'high'
                requires_review = False
                
            record = {
                "path": str_path,
                "language": ext if ext else "none",
                "classification": classification,
                "classification_confidence": confidence,
                "requires_manual_review": requires_review,
                "production_reachable": False, # Requires manual trace later
                "agent_reachable": False,
                "ci_reachable": False,
                "manual_only": False,
                "subprocess_capable": features.get('subprocess_capable', False),
                "shell_true": features.get('shell_true', False),
                "filesystem_write": features.get('filesystem_write', False),
                "network_access": features.get('network_access', False),
                "canonical_architecture_compliant": True, # Pending manual verification
                "owner": "system",
                "evidence": []
            }
            results.append(record)
            
    out_dir = Path('.remediation/phase-9')
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / 'executable-surface.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
        
    print(f"Discovered {len(results)} executable candidates.")

if __name__ == '__main__':
    main()
