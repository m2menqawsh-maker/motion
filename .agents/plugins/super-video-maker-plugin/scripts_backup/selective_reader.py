import sys
import json
import argparse
import re

sys.stdout.reconfigure(encoding="utf-8")

def get_files_for_phase(phase):
    if phase == "analyze":
        return [
            "projects/<id>/04_timings.json",
            "projects/<id>/.session_state.json"
        ]
    elif phase == "plan":
        return [
            "references/deep/motion-taste/director/motion-personality.md",
            "references/deep/motion-taste/director/emotion-mapping.md",
            "references/deep/motion-taste/director/choreography.md",
            "references/deep/motion-taste/director/SFX_BINDING_MATRIX.md",
            "references/deep/motion-taste/reference/timing-easing-tables.md",
            "ground-truth/TEMPLATE_INDEX.md",
            "projects/<id>/04_timings.json"
        ]
    elif phase.startswith("build_scene_"):
        match = re.match(r"build_scene_(\d+)", phase)
        files = []
        if match:
            n = int(match.group(1))
            files.append(f"projects/<id>/scenes/scene_{n}_plan.md")
            if n > 1:
                files.append(f"projects/<id>/06_build/src/compositions/Scene{n-1}.tsx")
        files.extend([
            "ground-truth/TEMPLATE_INDEX.md",
            "references/deep/motion-taste/director/SFX_BINDING_MATRIX.md"
        ])
        return files
    elif phase == "audio":
        return [
            "projects/<id>/04_timings.json",
            "references/deep/motion-taste/director/SFX_BINDING_MATRIX.md",
            "projects/<id>/02_asset_manifest.json"
        ]
    elif phase == "review":
        return [
            "projects/<id>/smart_qc_report.json",
            "projects/<id>/06_build/src/compositions/SceneN.tsx",
            "projects/<id>/.agent_alerts.md"
        ]
    elif phase == "render":
        return [
            "projects/<id>/.session_state.json",
            "projects/<id>/.studio_unlocked",
            "projects/<id>/.studio_approved"
        ]
    else:
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", help="المرحلة")
    parser.add_argument("--json", action="store_true", help="طباعة المخرجات كـ JSON")
    args = parser.parse_args()

    files = get_files_for_phase(args.phase)

    if args.json:
        print(json.dumps(files, ensure_ascii=False, indent=2))
    else:
        if files:
            for f in files:
                print(f"{f}")
        else:
            print("مرحلة غير معروفة")
