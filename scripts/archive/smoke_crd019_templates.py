#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smoke_crd019_templates.py — Targeted render smoke for CRD-019.

Tests the five templates from the failed Clean-Room run:
1. Herodeviceassemblewrapper
2. Splitscreenwrapper
3. Landingcodeshowcasewrapper
4. Datastorywrapper
5. Creatorreelwrapper

Proves:
- registry resolution = PASS
- component load = PASS
- minimal Remotion renderStill = PASS
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.security.security import safe_subprocess

REMOTION_APP = ROOT / "remotion-app"
OUT_DIR = ROOT / "out" / "crd019_smoke"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_TEMPLATES = [
    ("Herodeviceassemblewrapper", 10, {
        "title": "Smoke Hero Device",
        "subtitle": "Testing Device Assembly"
    }),
    ("Splitscreenwrapper", 40, {
        "title": "Split Screen Comparison",
        "left": {
            "src": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='600'><rect width='800' height='600' fill='%23111827'/></svg>",
            "label": "Before"
        },
        "right": {
            "src": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='600'><rect width='800' height='600' fill='%231f2937'/></svg>",
            "label": "After"
        }
    }),
    ("Landingcodeshowcasewrapper", 70, {
        "headline": "Code Showcase",
        "tagline": "AI Driven Code",
        "codeSnippet": "console.log('CRD-019');"
    }),
    ("Datastorywrapper", 100, {
        "statNumber": "99.9%",
        "statLabel": "Uptime",
        "trend": "up"
    }),
    ("Creatorreelwrapper", 130, {
        "creatorName": "Clean Room Agent",
        "handle": "@clean_room",
        "cta": "Verified"
    })
]


def run_smoke():
    scenes = []
    for idx, (tmpl, _, props) in enumerate(TARGET_TEMPLATES):
        scenes.append({
            "scene_id": f"scene_{idx + 1}",
            "template": tmpl,
            "startFrame": idx * 30,
            "durationFrames": 30,
            "surface": {
                "text": f"Surface Text for {tmpl}",
                "primaryColor": "#00F0FF",
                "accentColor": "#FF0055",
                "backgroundColor": "#0A0A0F"
            },
            "content": {
                "lines": [f"Line 1 for {tmpl}", f"Line 2 for {tmpl}"],
                "text": f"Content Text for {tmpl}"
            },
            "template_props": props
        })

    smoke_project = {
        "projectData": {
            "project": {
                "fps": 30,
                "title": "CRD-019 Smoke Test"
            },
            "blueprint": {
                "fps": 30,
                "scenes": scenes
            },
            "brand": {
                "colors": {
                    "primary": "#00F0FF",
                    "secondary": "#7928CA",
                    "accent": "#FF0055",
                    "background": "#000000",
                    "surface": "#111111",
                    "text": "#FFFFFF"
                },
                "fonts": {
                    "display": "Inter",
                    "body": "Inter"
                }
            },
            "overrides": {
                "scenes": {}
            },
            "media_map": {}
        }
    }

    props_file = OUT_DIR / "smoke_props.json"
    props_file.write_text(json.dumps(smoke_project, indent=2, ensure_ascii=False), encoding="utf-8")

    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    config_file = str(REMOTION_APP / "remotion.config.ts")

    results = []
    resolution_failures = 0
    component_load_failures = 0
    render_smoke_failures = 0

    print(f"Executing targeted render smoke for {len(TARGET_TEMPLATES)} templates...")
    print("=" * 70)

    for tmpl, frame, _ in TARGET_TEMPLATES:
        out_image = OUT_DIR / f"smoke_{tmpl}.png"
        cmd = [
            npx_cmd,
            "remotion",
            "still",
            "src/index.ts",
            "BlueprintVideo",
            str(out_image.resolve()),
            f"--frame={frame}",
            f"--props={str(props_file.resolve())}",
            f"--config={config_file}",
            "--timeout=60000"
        ]

        print(f"Testing {tmpl} (frame {frame})...")
        res = safe_subprocess(cmd, cwd=str(REMOTION_APP), capture_output=True, text=True)

        if res.returncode != 0:
            err = res.stderr + "\n" + res.stdout
            print(f"  ❌ FAILED: {tmpl}")
            if "Template not found in registry" in err:
                resolution_failures += 1
                print("     Reason: Resolution failure")
            elif "Cannot find module" in err or "TypeError" in err:
                component_load_failures += 1
                print(f"     Reason: Component load failure: {err[:200]}")
            else:
                render_smoke_failures += 1
                print(f"     Reason: Render failure: {err[:200]}")
            results.append((tmpl, False, err))
        else:
            if out_image.exists() and out_image.stat().st_size > 0:
                print(f"  ✓ PASS: {tmpl} (rendered {out_image.stat().st_size} bytes)")
                results.append((tmpl, True, "OK"))
            else:
                render_smoke_failures += 1
                print(f"  ❌ FAILED: {tmpl} (image empty or not found)")
                results.append((tmpl, False, "Empty output"))

    print("=" * 70)
    print(f"Summary:")
    print(f"  Total templates tested:      {len(TARGET_TEMPLATES)}")
    print(f"  Successful render smokes:    {sum(1 for _, ok, _ in results if ok)}/{len(TARGET_TEMPLATES)}")
    print(f"  Runtime resolution failures: {resolution_failures}")
    print(f"  Component load failures:     {component_load_failures}")
    print(f"  Render smoke failures:       {render_smoke_failures}")

    if any(not ok for _, ok, _ in results):
        sys.exit(1)
    print("ALL TARGETED SMOKE RENDERS PASSED!")
    sys.exit(0)


if __name__ == "__main__":
    run_smoke()
