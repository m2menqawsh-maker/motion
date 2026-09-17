import os
import json
from pathlib import Path

def analyze_package_scripts():
    results = []
    
    for root, dirs, files in os.walk('.'):
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
            
        for file in files:
            if file == 'package.json':
                pkg_path = Path(root) / file
                str_path = str(pkg_path).replace('\\', '/')
                
                try:
                    with open(pkg_path, 'r', encoding='utf-8') as f:
                        pkg = json.load(f)
                        
                    scripts = pkg.get('scripts', {})
                    for name, cmd in scripts.items():
                        
                        cls = 'UNKNOWN'
                        if 'build' in name or 'bundle' in name:
                            cls = 'BUILD'
                        elif 'test' in name or 'lint' in name:
                            cls = 'TEST'
                        elif 'start' in name or 'dev' in name:
                            cls = 'DEVELOPMENT'
                        elif 'render' in name:
                            cls = 'PRODUCTION'
                            
                        # Verify target exists (rudimentary check for first token)
                        target_exists = True
                        tokens = cmd.split()
                        if tokens:
                            first_token = tokens[0]
                            # if it's a local script path
                            if first_token.startswith('./') or first_token.startswith('../'):
                                target_exists = os.path.exists(os.path.join(root, first_token))
                                
                        results.append({
                            'package_file': str_path,
                            'script_name': name,
                            'command': cmd,
                            'classification': cls,
                            'target_exists': target_exists,
                            'status': 'ACTIVE'
                        })
                except Exception as e:
                    pass
                    
    with open('.remediation/phase-9/package-script-inventory.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
        
    print(f"Found {len(results)} package scripts across all package.json files.")

if __name__ == '__main__':
    analyze_package_scripts()
