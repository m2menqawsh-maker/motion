import json
from pathlib import Path

DST = Path(r"C:\video\clean-video-workspace\.agents\plugins\super-video-maker-plugin")
CATALOG_PATH = DST / "ground-truth" / "template_catalog.json"

def get_use_cases(family, name, path):
    cases = []
    
    if family in ["typography", "captions"]:
        cases.extend(["ad", "explainer", "social", "saas"])
    if family in ["data"]:
        cases.extend(["saas", "explainer", "product"])
    if family in ["transitions"]:
        cases.extend(["ad", "social", "explainer", "product"])
    if family in ["backgrounds", "overlays", "motion"]:
        cases.extend(["social", "explainer", "ad"])
    if family in ["branding"]:
        cases.extend(["product", "launch", "ad"])
    if family in ["code"]:
        cases.extend(["saas", "education"])
    if family in ["camera", "cursor", "layout", "choreography", "ui-state"]:
        cases.extend(["saas", "product"])
    if family in ["primitives", "scenes"]:
        cases.extend(["ad", "explainer", "saas", "product"])
    if family in ["ui"]:
        cases.extend(["saas", "product", "explainer"])
    
    name_lower = name.lower()
    if "hook" in name_lower or "intro" in name_lower:
        if "ad" not in cases: cases.append("ad")
    if "end" in name_lower or "cta" in name_lower or "credits" in name_lower:
        if "ad" not in cases: cases.append("ad")
    if "social" in path or "reel" in name_lower or "podcast" in name_lower:
        if "social" not in cases: cases.append("social")
    
    if not cases:
        cases = ["explainer", "ad"]
    
    return list(set(cases))

def get_intents(family, name, type_):
    intents = []
    name_lower = name.lower()
    
    if family == "typography":
        intents.append("title_reveal")
    if family == "captions":
        intents.append("caption")
    if family == "data":
        intents.append("stat")
    if family == "transitions":
        intents.append("transition")
    if family == "backgrounds":
        intents.append("background")
    if family == "overlays":
        intents.append("overlay")
    if family == "motion":
        intents.append("motion_effect")
    if family == "branding":
        intents.append("logo")
    if family == "code":
        intents.append("code_demo")
    if family == "ui":
        intents.append("ui_element")
    if family in ["camera", "cursor", "layout"]:
        intents.append("camera_movement")
    
    if "hook" in name_lower or "intro" in name_lower:
        intents.append("hook")
    if "end" in name_lower or "cta" in name_lower:
        intents.append("cta")
    if "counter" in name_lower or "stat" in name_lower or "chart" in name_lower:
        intents.append("stat")
    if "typewriter" in name_lower:
        intents.append("typing")
    if "caption" in name_lower or "subtitle" in name_lower:
        intents.append("caption")
    if "transition" in name_lower or "wipe" in name_lower or "dissolve" in name_lower:
        intents.append("transition")
    if "logo" in name_lower:
        intents.append("logo")
    if "terminal" in name_lower or "code" in name_lower:
        intents.append("code_demo")
    if "ken-burns" in name_lower or "zoom" in name_lower:
        intents.append("image_motion")

    if family in ["camera", "cursor", "layout", "choreography", "audio", "ui-state"]:
        intents.append("camera_movement")
    if family == "primitives":
        intents.extend(["ui_element", "scene_element"])
    if family == "scenes":
        intents.extend(["scene_composition", "cinematic"])
    
    if "stagger" in name_lower or "enter" in name_lower or "exit" in name_lower:
        intents.append("element_animation")
    if "wallpaper" in name_lower or "bg" in name_lower:
        intents.append("background")
    if "pulse" in name_lower or "highlight" in name_lower:
        intents.append("emphasis")
    if "window" in name_lower or "app" in name_lower:
        intents.extend(["ui_element", "windows"])
    if "count" in name_lower or "counter" in name_lower:
        intents.append("stat")
    if "end" in name_lower or "closer" in name_lower:
        intents.append("cta")
    if "headline" in name_lower or "title" in name_lower:
        intents.append("title_reveal")
    if "typewriter" in name_lower or "writer" in name_lower:
        intents.append("typing")
    if "marquee" in name_lower:
        intents.append("scrolling_text")
    if "chart" in name_lower or "graph" in name_lower or "plot" in name_lower:
        intents.append("stat")
    if "progress" in name_lower:
        intents.append("progress_indicator")
    if "notification" in name_lower or "toast" in name_lower:
        intents.append("notification")
    if "avatar" in name_lower:
        intents.append("avatar")
    if "badge" in name_lower or "tag" in name_lower:
        intents.append("badge")
    if "button" in name_lower or "input" in name_lower or "dialog" in name_lower or "spinner" in name_lower:
        intents.append("ui_element")
    if "data" in name_lower or "table" in name_lower or "list" in name_lower:
        intents.append("data_display")
    if "search" in name_lower:
        intents.append("search_ui")
    if "sidebar" in name_lower or "nav" in name_lower or "tab" in name_lower:
        intents.append("navigation")
    if "message" in name_lower or "chat" in name_lower:
        intents.append("messaging")
    if "form" in name_lower:
        intents.append("form_ui")
    
    if not intents:
        intents.append("general_element")
    
    return list(set(intents))

def get_moods(family, name, quality):
    moods = []
    name_lower = name.lower()
    
    if quality == "A":
        moods.extend(["cinematic", "technical"])
    
    if "glitch" in name_lower or "rgb" in name_lower:
        moods.extend(["energetic", "technical"])
    if "blur" in name_lower or "fade" in name_lower:
        moods.append("cinematic")
    if "bounce" in name_lower or "pop" in name_lower or "bubble" in name_lower:
        moods.append("playful")
    if "matrix" in name_lower or "cyber" in name_lower or "terminal" in name_lower:
        moods.append("technical")
    if "cinematic" in name_lower or "film" in name_lower:
        moods.append("cinematic")
    if "energetic" in name_lower or "fast" in name_lower or "whip" in name_lower:
        moods.append("energetic")
    if family in ["data", "code"]:
        moods.append("technical")
    if family in ["branding"]:
        moods.extend(["cinematic", "technical"])
    if family in ["camera", "cursor", "layout"]:
        moods.extend(["cinematic", "technical"])
    
    if not moods:
        moods.append("technical")
    
    return list(set(moods))

def get_capabilities(family, name, source):
    caps = []
    
    if source == "cinematic-engine":
        if family == "camera":
            caps.append("camera")
        if family == "cursor":
            caps.append("cursor")
        if family == "layout":
            caps.append("windows")
        if family == "audio":
            caps.append("audio_sync")
        if family == "choreography":
            caps.append("choreography")
    
    if family == "code":
        caps.append("terminal")
    if family == "data":
        caps.append("data")
    if family == "captions":
        caps.append("captions")
    if family == "typography":
        caps.append("text_animation")
    if family == "ui":
        caps.append("ui")
    
    return caps

if __name__ == "__main__":
    if not CATALOG_PATH.exists():
        print("Catalog not found")
        exit(1)
        
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    for item in catalog:
        f = item.get("family", "")
        n = item.get("name", "")
        p = item.get("path", "")
        t = item.get("type", "")
        q = item.get("quality", "C")
        s = item.get("source", "")
        
        item["use_cases"] = get_use_cases(f, n, p)
        item["intents"] = get_intents(f, n, t)
        item["moods"] = get_moods(f, n, q)
        item["capabilities"] = get_capabilities(f, n, s)
        
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        
    print(f"Classified {len(catalog)} templates.")
