import json
from pathlib import Path

plugin = Path("c:/video/clean-video-workspace/.agents/plugins/super-video-maker-plugin")
catalog = []

def add_folder(folder_name, tier, default_status="raw"):
    p = plugin / folder_name
    if not p.exists(): return
    for f in p.rglob("*.tsx"):
        name = f.stem
        
        # Override tier for known premium ones
        actual_tier = tier
        if name in ["Captions", "Typewriter", "BlurReveal", "RgbGlitchText", "KenBurns", "StatCard", "Terminal", "CodeBlock", "CodeDiff", "SplitScreen", "glassWipe", "whip-pan", "CardStack", "SocialClip", "AudioVisualizer"]:
            actual_tier = "S"
            status = "production-ready"
        elif tier == "C":
            status = "raw"
        else:
            status = default_status
            
        is_rtl = False
        if name in ["Captions", "WordStagger", "StatCard", "Typewriter"]:
            is_rtl = True
            
        ltr_ex = []
        if name in ["CodeBlock", "Terminal", "CodeDiff"]:
            ltr_ex = ["code", "terminal"]
            
        catalog.append({
            "id": f"{folder_name}/{name}",
            "canonical_path": f"{folder_name}/{f.name}",
            "family": "Unclassified",
            "intent": [name.lower()],
            "tier": actual_tier,
            "status": status,
            "rtl_ready": is_rtl,
            "ltr_exceptions": ltr_ex,
            "quality_score": 100 if actual_tier == "S" else 50,
            "aliases": [],
            "replaces": [],
            "fallback": [],
            "evidence": [],
            "notes": ""
        })

add_folder("templates", "C")
add_folder("cinematic-engine", "A", "production-ready")
add_folder("premium-templates", "B", "production-ready")

out = plugin / "reference" / "ground-truth" / "template_catalog.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Catalog generated: {len(catalog)} entries")
