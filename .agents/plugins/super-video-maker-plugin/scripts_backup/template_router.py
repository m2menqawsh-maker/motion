import json
import argparse
from pathlib import Path

def route(intent=None, use_case=None, mood=None, type_=None, 
          family=None, capability=None, min_quality="C"):
    
    # Path relative to script location
    catalog_path = Path(__file__).resolve().parent.parent / "ground-truth" / "template_catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    
    quality_order = {"A": 3, "B": 2, "C": 1}
    min_q = quality_order.get(min_quality, 1)
    
    results = []
    for item in catalog:
        score = 0
        
        # Quality filter
        if quality_order.get(item.get("quality", "C"), 1) < min_q:
            continue
        
        # Intent matching
        if intent and intent in item.get("intents", []):
            score += 10
        
        # Use case matching
        if use_case and use_case in item.get("use_cases", []):
            score += 8
        
        # Mood matching
        if mood and mood in item.get("moods", []):
            score += 5
        
        # Type matching
        if type_ and item.get("type") == type_:
            score += 7
        
        # Family matching
        if family and item.get("family") == family:
            score += 6
        
        # Capability matching
        if capability and capability in item.get("capabilities", []):
            score += 9
        
        # Quality reward
        score += quality_order.get(item.get("quality", "C"), 1) * 2
        
        if score > 0:
            results.append((score, item))
    
    # Sort descending
    results.sort(key=lambda x: x[0], reverse=True)
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Template Router")
    parser.add_argument("--intent", type=str)
    parser.add_argument("--use-case", type=str)
    parser.add_argument("--mood", type=str)
    parser.add_argument("--type", type=str)
    parser.add_argument("--family", type=str)
    parser.add_argument("--capability", type=str)
    parser.add_argument("--min-quality", type=str, default="C")
    parser.add_argument("--top", type=int, default=5)
    
    args = parser.parse_args()
    
    results = route(
        intent=args.intent,
        use_case=args.use_case,
        mood=args.mood,
        type_=args.type,
        family=args.family,
        capability=args.capability,
        min_quality=args.min_quality
    )
    
    print(f"Found {len(results)} matching templates (showing top {args.top}):")
    print(f"{'Score':<6} {'Name':<25} {'Type':<10} {'Quality':<8} {'Path'}")
    print("-" * 90)
    for score, item in results[:args.top]:
        print(f"{score:<6} {item['name']:<25} {item['type']:<10} {item['quality']:<8} {item['path']}")
