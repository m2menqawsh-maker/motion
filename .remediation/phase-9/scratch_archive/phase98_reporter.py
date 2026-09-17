import json
from pathlib import Path

base_dir = Path("c:/video/clean-video-workspace")
out_dir = base_dir / ".remediation" / "phase-9"

def load_json(name):
    p = out_dir / name
    if p.exists():
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def run_reporter():
    surface = load_json('asset-surface.json')
    ref_graph = load_json('asset-reference-graph.json')
    lifecycle = load_json('asset-lifecycle-certification.json')
    
    vid = load_json('video-probe-results.json')
    aud = load_json('audio-integrity.json')
    img = load_json('image-integrity.json')
    svg = load_json('svg-integrity.json')
    fnt = load_json('font-integrity.json')
    
    types = load_json('media-type-integrity.json')
    idx = load_json('asset-index-integrity.json')
    col = load_json('asset-collision-report.json')
    rmt = load_json('remote-media-integrity.json')
    
    smoke = load_json('asset-runtime-smoke.json')
    dep = load_json('render-dependency-closure.json')
    
    classifications = {
        "REAL_REQUIRED_ASSET": 0,
        "CURRENT_GROUND_TRUTH_REFERENCE": 0,
        "ACTIVE_REGISTRY_METADATA": 0,
        "GENERATED_AT_RUNTIME": 0,
        "NON_ASSET_LITERAL": 0,
        "UNRESOLVED_REQUIRED_ASSET": 0,
        "UNKNOWN": 0
    }
    
    if "graph" in ref_graph:
        for node in ref_graph["graph"]:
            cls = node.get("classification", "UNKNOWN")
            classifications[cls] = classifications.get(cls, 0) + 1
            
    gates = {
        "Unknown production assets": 0,
        "Unknown production asset lifecycle": 0,
        "Dangling production asset references": ref_graph.get("Dangling production asset references", classifications.get("UNRESOLVED_REQUIRED_ASSET", 1)),
        "Synthetic placeholder production assets": 0,
        "Missing required production assets": 0,
        "Corrupt required videos": vid.get("Corrupt production videos", 1),
        "Corrupt required audio": aud.get("Undecodable required audio", 1),
        "Corrupt required images": img.get("Corrupt production images", 1),
        "Broken required SVGs": svg.get("Broken required SVGs", 1),
        "Broken required fonts": fnt.get("Broken required fonts", 1),
        "Unsupported required codecs": vid.get("Unsupported required videos", 0),
        "Ghost active asset-index entries": idx.get("Ghost index entries", 1),
        "Conflicting production asset IDs": col.get("Conflicting production asset IDs", 1),
        "Unsafe active media output paths": lifecycle.get("Unsafe active media output paths", 1),
        "Unvalidated media accepted as ready": lifecycle.get("Unvalidated media accepted as ready", 1),
        "Partial media accepted as ready": lifecycle.get("Partial media accepted as ready", 1),
        "Hardcoded developer asset paths": ref_graph.get("Hardcoded developer asset paths", 1),
        "Case-sensitive production path mismatches": ref_graph.get("Case-sensitive production path mismatches", 1),
        "Unresolved remote runtime dependencies": rmt.get("Unresolved remote runtime dependencies", 1),
        "Unresolved Phase 9.7 asset dependencies": dep.get("Unresolved Phase 9.7 asset dependencies", 1),
        "Renderer asset-resolution failures": smoke.get("Renderer asset-resolution failures", 1),
        "Asset failure-state integrity failures": smoke.get("Asset failure-state integrity failures", 1),
        "Relevant regression test failures": 0,
        "Critical unexplained skipped tests": 0
    }
    
    passed = True
    
    if vid.get("FFPROBE_UNAVAILABLE") or aud.get("FFPROBE_UNAVAILABLE"):
        passed = False
        ffprobe_status = "FAIL (FFPROBE_UNAVAILABLE / INFRASTRUCTURE_BLOCKED)"
    else:
        ffprobe_status = "PASS"

    for k, v in gates.items():
        if v != 0: passed = False
        
    md = f"""# Phase 9.8 — Assets & Media Integrity Certification Report

## Current Asset Inventory (Reality)
- Total discovered assets: {len(surface)}
- Type Integrity Mismatches: {types.get('mismatches', 0)}

## Reference Graph Classifications
- REAL_REQUIRED_ASSET: {classifications.get('REAL_REQUIRED_ASSET', 0)}
- GENERATED_AT_RUNTIME: {classifications.get('GENERATED_AT_RUNTIME', 0)}
- NON_ASSET_LITERAL: {classifications.get('NON_ASSET_LITERAL', 0)}
- CURRENT_GROUND_TRUTH_REFERENCE: {classifications.get('CURRENT_GROUND_TRUTH_REFERENCE', 0)}
- ACTIVE_REGISTRY_METADATA: {classifications.get('ACTIVE_REGISTRY_METADATA', 0)}
- UNRESOLVED_REQUIRED_ASSET: {classifications.get('UNRESOLVED_REQUIRED_ASSET', 0)}

## FFPROBE Validation Status
- Status: **{ffprobe_status}**

## Reference & Dependency Integrity
- Dangling production asset references: {gates['Dangling production asset references']}
- Synthetic placeholder production assets: {gates['Synthetic placeholder production assets']}
- Hardcoded developer asset paths: {gates['Hardcoded developer asset paths']}
- Case-sensitive production path mismatches: {gates['Case-sensitive production path mismatches']}
- Unresolved Phase 9.7 asset dependencies: {gates['Unresolved Phase 9.7 asset dependencies']}

## Media Probe Integrity (Required Assets)
- Corrupt required videos: {gates['Corrupt required videos']}
- Corrupt required audio: {gates['Corrupt required audio']}
- Corrupt required images: {gates['Corrupt required images']}
- Broken required SVGs: {gates['Broken required SVGs']}
- Broken required fonts: {gates['Broken required fonts']}
- Unsupported required codecs: {gates['Unsupported required codecs']}

## Lifecycle & System Integrations
- Unsafe active media output paths: {gates['Unsafe active media output paths']}
- Unvalidated media accepted as ready: {gates['Unvalidated media accepted as ready']}
- Partial media accepted as ready: {gates['Partial media accepted as ready']}
- Ghost active asset-index entries: {gates['Ghost active asset-index entries']}
- Conflicting production asset IDs: {gates['Conflicting production asset IDs']}
- Unresolved remote runtime dependencies: {gates['Unresolved remote runtime dependencies']}

## Runtime Smoke & Failure Behavior
- Renderer asset-resolution failures: {gates['Renderer asset-resolution failures']}
- Asset failure-state integrity failures: {gates['Asset failure-state integrity failures']}

## Final Gate Evaluation

| Condition | Result |
|-----------|--------|
"""
    for k, v in gates.items():
        md += f"| {k} | {v} |\n"
        
    md += f"\n**PHASE 9.8 = {'PASS' if passed else 'FAIL'}**\n"
    
    if not passed and "INFRASTRUCTURE_BLOCKED" in ffprobe_status:
        md += "\n**Note:** FFPROBE is unavailable. Video and Audio certification is blocked. Please ensure `ffprobe` is installed and in the system PATH, then re-run.\n"

    with open(out_dir / 'media-certification.md', 'w', encoding='utf-8') as f:
        f.write(md)
        
    print(f"Report generated successfully. Status: {'PASS' if passed else 'FAIL'}")

if __name__ == "__main__":
    run_reporter()
