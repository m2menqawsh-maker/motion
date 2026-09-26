#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""smoke_crd020_temporal.py — Multi-frame temporal runtime smoke for CRD-020.

Tests the four Clean-Room scenario templates across their complete lifecycle:
1. Herodeviceassemblewrapper (early, mid, late)
2. Splitscreenwrapper (early, mid, late)
3. Datastorywrapper (early [hook], chart-active [AnimatedBarChart], metric-active [MetricTicker], timeline-active [TimelineSteps], late [EndCard])
4. Creatorreelwrapper (early, mid, late)

Explicitly proves:
- All deferred branches mount cleanly without crashing when props are omitted
- Exact frame 72+ activation path for AnimatedBarChart renders successfully
- Images are non-empty and generated with 0 errors
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.security.security import safe_subprocess

REMOTION_APP = ROOT / "remotion-app"
OUT_DIR = ROOT / "temp" / "crd020_smoke"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Define scenario scenes with realistic production metadata
SCENARIOS = [
    {
        "template": "Herodeviceassemblewrapper",
        "duration": 180,
        "props": {
            "title": "تقنية الذكاء الاصطناعي",
            "subtitle": "تجميع الأجهزة الذكية بدقة عالية"
        },
        "frames": [
            {"name": "early", "local_frame": 15, "branch": "assemble_entrance"},
            {"name": "mid", "local_frame": 90, "branch": "device_assembled"},
            {"name": "late", "local_frame": 165, "branch": "settle_exit"},
        ]
    },
    {
        "template": "Splitscreenwrapper",
        "duration": 150,
        "props": {
            "title": "مقارنة الأداء",
            "left": {
                "src": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='600'><rect width='800' height='600' fill='%23111827'/></svg>",
                "label": "الماضي"
            },
            "right": {
                "src": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='600'><rect width='800' height='600' fill='%231f2937'/></svg>",
                "label": "الحاضر"
            }
        },
        "frames": [
            {"name": "early", "local_frame": 15, "branch": "split_wipe_in"},
            {"name": "mid", "local_frame": 75, "branch": "dual_pane_hold"},
            {"name": "late", "local_frame": 135, "branch": "split_settle"},
        ]
    },
    {
        "template": "Datastorywrapper",
        "duration": 420,
        # Recreating EXACT Clean-Room scenario: NO barData, NO metrics, NO steps provided
        "props": {
            "statNumber": "100%",
            "statLabel": "دقة النتائج النهائية",
            "trend": "up"
        },
        "frames": [
            {"name": "early_hook", "local_frame": 15, "branch": "AutoFitTitle (Hook)"},
            {"name": "chart_active", "local_frame": 85, "branch": "AnimatedBarChart (Deferred frame 72+)"},
            {"name": "metrics_active", "local_frame": 170, "branch": "MetricTicker (Deferred frame 152+)"},
            {"name": "timeline_active", "local_frame": 250, "branch": "TimelineSteps (Deferred frame 228+)"},
            {"name": "late_cta", "local_frame": 375, "branch": "EndCard (Deferred frame 358+)"},
        ]
    },
    {
        "template": "Creatorreelwrapper",
        "duration": 390,
        "props": {
            "hookHeadline": "صناعة المحتوى بذكاء",
            "hookSubtitle": "اختصر وقت الإنتاج من ساعات إلى دقائق",
            "creatorName": "Clean Room Agent",
            "handle": "@clean_room"
        },
        "frames": [
            {"name": "early", "local_frame": 20, "branch": "hook_headline"},
            {"name": "mid", "local_frame": 160, "branch": "b_roll_and_body"},
            {"name": "late", "local_frame": 360, "branch": "cta_end_card"},
        ]
    }
]


def build_smoke_project():
    scenes = []
    current_frame = 0
    all_test_frames = []

    for idx, sc in enumerate(SCENARIOS):
        tmpl = sc["template"]
        dur = sc["duration"]
        start_f = current_frame

        scenes.append({
            "scene_id": f"scene_{idx + 1}",
            "template": tmpl,
            "startFrame": start_f,
            "durationFrames": dur,
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
            "template_props": sc["props"]
        })

        for f_info in sc["frames"]:
            global_frame = start_f + f_info["local_frame"]
            all_test_frames.append({
                "template": tmpl,
                "label": f_info["name"],
                "local_frame": f_info["local_frame"],
                "global_frame": global_frame,
                "branch": f_info["branch"],
                "duration": dur,
            })

        current_frame += dur

    smoke_project = {
        "projectData": {
            "project": {
                "fps": 30,
                "title": "CRD-020 Temporal Runtime Smoke"
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

    return smoke_project, all_test_frames


def run_temporal_smoke():
    smoke_project, test_frames = build_smoke_project()
    props_file = OUT_DIR / "smoke_temporal_props.json"
    props_file.write_text(json.dumps(smoke_project, indent=2, ensure_ascii=False), encoding="utf-8")

    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    config_file = str(REMOTION_APP / "remotion.config.ts")

    print("=" * 80)
    print(f"CRD-020 TEMPORAL RUNTIME SMOKE: Testing {len(test_frames)} checkpoints across {len(SCENARIOS)} templates")
    print("=" * 80)

    results = []
    datastory_branch_results = {}

    for tf in test_frames:
        tmpl = tf["template"]
        lbl = tf["label"]
        l_frame = tf["local_frame"]
        g_frame = tf["global_frame"]
        branch = tf["branch"]

        out_image = OUT_DIR / f"smoke_{tmpl}_{lbl}_g{g_frame}.png"
        cmd = [
            npx_cmd,
            "remotion",
            "still",
            "src/index.ts",
            "BlueprintVideo",
            str(out_image.resolve()),
            f"--frame={g_frame}",
            f"--props={str(props_file.resolve())}",
            f"--config={config_file}",
            "--timeout=60000"
        ]

        print(f"▶ {tmpl} [{lbl}] | Local f:{l_frame}/{tf['duration']} (Global f:{g_frame}) | Branch: {branch}")
        res = safe_subprocess(cmd, cwd=str(REMOTION_APP), capture_output=True, text=True)

        if res.returncode != 0:
            err = res.stderr + "\n" + res.stdout
            print(f"  ❌ FAILED at frame {g_frame}: {err[:250]}")
            results.append((tmpl, lbl, g_frame, False, err))
            if tmpl == "Datastorywrapper":
                datastory_branch_results[lbl] = False
        else:
            if out_image.exists() and out_image.stat().st_size > 0:
                size_kb = out_image.stat().st_size / 1024
                print(f"  ✓ PASS ({size_kb:.1f} KB image rendered)")
                results.append((tmpl, lbl, g_frame, True, "OK"))
                if tmpl == "Datastorywrapper":
                    datastory_branch_results[lbl] = True
            else:
                print(f"  ❌ FAILED: Output image empty or missing")
                results.append((tmpl, lbl, g_frame, False, "Empty image"))
                if tmpl == "Datastorywrapper":
                    datastory_branch_results[lbl] = False

    print("=" * 80)
    passed_count = sum(1 for *_, ok, _ in results if ok)
    total_count = len(results)
    print(f"TEMPORAL SMOKE RESULTS: {passed_count}/{total_count} PASSED")
    print("=" * 80)
    print("DataStory Deferred Branch Evidence:")
    for lbl, ok in datastory_branch_results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  - {lbl}: {status}")

    if passed_count != total_count:
        sys.exit(1)

    print("\nALL TEMPORAL RUNTIME SMOKE CHECKS PASSED!")
    sys.exit(0)


if __name__ == "__main__":
    run_temporal_smoke()
