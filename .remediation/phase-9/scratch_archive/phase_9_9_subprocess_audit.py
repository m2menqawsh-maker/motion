import json
import ast
from pathlib import Path

def get_subprocess_details(filepath, content):
    details = {
        'shell_true': False,
        'has_timeout': False,
        'arbitrary_execution': False
    }
    
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr in ('run', 'Popen', 'check_output', 'check_call'):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'subprocess':
                        # Check kwargs
                        for kw in node.keywords:
                            if kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                details['shell_true'] = True
                            if kw.arg == 'timeout':
                                details['has_timeout'] = True
                                
                        # Check if command list contains non-constants at index 0 (arbitrary execution risk)
                        if len(node.args) > 0:
                            cmd_arg = node.args[0]
                            if isinstance(cmd_arg, ast.List):
                                if len(cmd_arg.elts) > 0 and not isinstance(cmd_arg.elts[0], ast.Constant):
                                    # First element is a variable
                                    details['arbitrary_execution'] = True
                            elif not isinstance(cmd_arg, ast.Constant):
                                # The entire command is a variable
                                details['arbitrary_execution'] = True
                                
                if isinstance(node.func, ast.Attribute) and node.func.attr in ('system', 'popen'):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == 'os':
                        details['shell_true'] = True
                        if len(node.args) > 0 and not isinstance(node.args[0], ast.Constant):
                            details['arbitrary_execution'] = True
    except Exception:
        pass
        
    return details

def rebuild_subprocess_inventory():
    with open('.remediation/phase-9/executable-classification.json', 'r', encoding='utf-8') as f:
        surface = json.load(f)
        
    inventory = []
    
    metrics = {
        'shell_true': 0,
        'unrestricted_arbitrary': 0,
        'production_no_timeout': 0,
        'user_controlled_construction': 0
    }
    
    for item in surface:
        if item.get('subprocess_capable') and item['path'].endswith('.py'):
            path = item['path']
            try:
                content = Path(path).read_text(encoding='utf-8')
            except Exception:
                continue
                
            details = get_subprocess_details(path, content)
            
            is_prod = item.get('production_reachable', False)
            
            # Record metrics
            if is_prod and details['shell_true']:
                metrics['shell_true'] += 1
            if is_prod and details['arbitrary_execution']:
                metrics['unrestricted_arbitrary'] += 1
                metrics['user_controlled_construction'] += 1
            if is_prod and not details['has_timeout']:
                # Special check: pipeline.py itself might wait for orchestrators which don't have timeout, but we strictly count it
                metrics['production_no_timeout'] += 1
                
            inventory.append({
                'path': path,
                'classification': item.get('classification'),
                'production_reachable': is_prod,
                'details': details
            })
            
    with open('.remediation/phase-9/subprocess-inventory.json', 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2)
        
    print(json.dumps(metrics, indent=2))

if __name__ == '__main__':
    rebuild_subprocess_inventory()
