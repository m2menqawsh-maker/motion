import json
import re
from pathlib import Path

def analyze_ts_tsx(path, content):
    features = {
        'child_process': False,
        'filesystem': False,
        'network': False,
        'cli': False,
        'render_registration': False
    }
    
    if re.search(r'(child_process|exec\(|spawn\(|execFile\(|execSync)', content):
        features['child_process'] = True
    if re.search(r'(fs\.|writeFileSync|createReadStream|createWriteStream)', content):
        features['filesystem'] = True
    if re.search(r'(fetch\(|axios\.|http\.request|https\.request)', content):
        features['network'] = True
    if re.search(r'(process\.argv|commander|yargs)', content):
        features['cli'] = True
    if re.search(r'(registerRoot|renderMedia|renderStill)', content):
        features['render_registration'] = True
        
    return features

def recover():
    with open('.remediation/phase-9/executable-classification.json', 'r', encoding='utf-8') as f:
        surface = json.load(f)
        
    for item in surface:
        path = item['path']
        if path.endswith('.ts') or path.endswith('.tsx') or path.endswith('.ps1'):
            if item.get('classification') in ('NON_EXECUTABLE_COMPONENT', 'QUARANTINED') and 'scratch' not in path and '.remediation' not in path:
                try:
                    content = Path(path).read_text(encoding='utf-8')
                except Exception:
                    continue
                
                if path.endswith('.ps1'):
                    # PS1 is always executable
                    item['classification'] = 'TEST_SUPPORT' if 'test' in path.lower() else 'UNKNOWN_EXECUTABLE'
                    item['requires_manual_review'] = True
                    item['classification_confidence'] = 'low'
                    item['evidence'].append('PS1 recovered from blanket classification.')
                    continue
                    
                features = analyze_ts_tsx(path, content)
                is_dangerous = any(features.values())
                
                if is_dangerous:
                    # Upgrade to executable
                    item['classification'] = 'PRODUCTION' if item.get('production_reachable') else 'UNKNOWN_EXECUTABLE'
                    item['classification_confidence'] = 'low'
                    item['requires_manual_review'] = True
                    item['evidence'] = [f"Recovered. Detected features: {[k for k, v in features.items() if v]}"]
                else:
                    item['classification'] = 'NON_EXECUTABLE_COMPONENT'
                    item['classification_confidence'] = 'high'
                    item['requires_manual_review'] = False
                    
    with open('.remediation/phase-9/executable-classification.json', 'w', encoding='utf-8') as f:
        json.dump(surface, f, indent=2)
        
    needs_review = [x['path'] for x in surface if x.get('requires_manual_review')]
    print(f"Recovered {len(needs_review)} files for manual review.")
    for p in needs_review:
        print(f" - {p}")
        
if __name__ == '__main__':
    recover()
