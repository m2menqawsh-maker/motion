import os
import json

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    worklist_path = os.path.join(repo_root, 'registry', 'docs-worklist.json')
    
    with open(worklist_path, 'r', encoding='utf-8') as f:
        docs = json.load(f)
        
    for doc in docs:
        if doc['tier'] == 'unknown' and not doc['implemented']:
            path_lower = doc['path'].lower()
            if 'premium' in path_lower:
                doc['tier'] = 'A'
            elif 'components' in path_lower or 'archetypes' in path_lower:
                doc['tier'] = 'B'
            else:
                doc['tier'] = 'C'

    # write back
    with open(worklist_path, 'w', encoding='utf-8') as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)
        
    # Stats
    stats = {}
    for doc in docs:
        tier = doc['tier']
        impl = "implemented" if doc['implemented'] else "unimplemented"
        if tier not in stats:
            stats[tier] = {"implemented": 0, "unimplemented": 0}
        stats[tier][impl] += 1
        
    print("New Worklist Stats:")
    for tier in sorted(stats.keys()):
        data = stats[tier]
        print(f"Tier {tier}: {data['implemented']} implemented, {data['unimplemented']} unimplemented")

    # Get first 20 unimplemented sorted by tier A->B->C
    unimplemented = [doc for doc in docs if not doc['implemented']]
    
    def get_tier_rank(tier):
        if tier == 'A': return 1
        if tier == 'B': return 2
        if tier == 'C': return 3
        return 4
        
    unimplemented.sort(key=lambda x: (get_tier_rank(x['tier']), x['name']))
    
    top_20 = unimplemented[:20]
    print("\nTop 20 templates to implement:")
    for doc in top_20:
        print(f"- {doc['name']} (Tier {doc['tier']}, Path: {doc['path']})")

if __name__ == '__main__':
    main()
