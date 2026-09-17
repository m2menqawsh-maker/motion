import json
from pathlib import Path

def classify_executables():
    with open('.remediation/phase-9/executable-classification.json', 'r', encoding='utf-8') as f:
        surface = json.load(f)
        
    for item in surface:
        path = item['path']
        is_prod = item['production_reachable']
        is_agent = item['agent_reachable']
        is_ci = item['ci_reachable']
        
        # 1. Historical / Archive
        if path.startswith('.remediation/') or 'archive/' in path or 'quarantine/' in path:
            if not is_prod and not is_agent and not is_ci:
                item['classification'] = 'HISTORICAL'
                item['classification_confidence'] = 'high'
                item['requires_manual_review'] = False
            else:
                item['classification'] = 'HISTORICAL_LEAKAGE'
                item['classification_confidence'] = 'high'
                item['requires_manual_review'] = True
                
        # 2. Scratch
        elif path.startswith('scratch/'):
            if not is_prod:
                item['classification'] = 'CERTIFICATION_TEMPORARY'
                item['classification_confidence'] = 'high'
                item['requires_manual_review'] = False
            else:
                item['classification'] = 'PRODUCTION_LEAKAGE'
                item['classification_confidence'] = 'high'
                item['requires_manual_review'] = True
                
        # 3. Tests
        elif path.startswith('tests/') or 'test_' in path or '.test.' in path:
            if not is_prod:
                item['classification'] = 'TEST_SUPPORT'
                item['classification_confidence'] = 'high'
                item['requires_manual_review'] = False
            
        # 4. Git Hooks / Workflows
        elif path.startswith('.githooks/') or path.startswith('.github/'):
            item['classification'] = 'GOVERNANCE'
            item['classification_confidence'] = 'high'
            item['requires_manual_review'] = False
            
        # 5. Production scripts
        elif is_prod:
            item['classification'] = 'PRODUCTION'
            item['classification_confidence'] = 'high'
            
            # Check safety
            if item.get('subprocess_capable'):
                item['requires_manual_review'] = True
            else:
                item['requires_manual_review'] = False
                
        # 6. Agent scripts
        elif is_agent:
            item['classification'] = 'AGENT_TOOL'
            item['classification_confidence'] = 'high'
            if item.get('subprocess_capable'):
                item['requires_manual_review'] = True
            else:
                item['requires_manual_review'] = False
                
    # Save back
    with open('.remediation/phase-9/executable-classification.json', 'w', encoding='utf-8') as f:
        json.dump(surface, f, indent=2)
        
    needs_review = [x for x in surface if x.get('requires_manual_review')]
    zombies = [x for x in surface if x.get('classification') == 'ZOMBIE_CANDIDATE']
    
    print(f"Items needing manual review: {len(needs_review)}")
    print(f"Zombie candidates: {len(zombies)}")
    
    # Check Gate constraints
    shell_true_prod = [x for x in surface if x.get('shell_true') and x.get('production_reachable')]
    shell_true_agent = [x for x in surface if x.get('shell_true') and x.get('agent_reachable')]
    
    print(f"Prod shell=True: {len(shell_true_prod)}")
    print(f"Agent shell=True: {len(shell_true_agent)}")

if __name__ == '__main__':
    classify_executables()
