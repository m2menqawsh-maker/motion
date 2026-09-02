#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Guard for Google Antigravity
يعترض الأوامر الخطيرة قبل تنفيذها.
"""
import sys
import json
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    # Antigravity يرسل البيانات كـ JSON في stdin
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        command = ""
        if isinstance(tool_input, dict):
            command = tool_input.get("command", "") or tool_input.get("CommandLine", "")
        elif isinstance(tool_input, str):
            command = tool_input
        
        if not command:
            allow()
        
        # ── القواعد الصارمة ──────────────────────────
        
        # 1. منع الرندر قبل موافقة الاستوديو
        if "npx remotion render" in command:
            if not check_studio_approval():
                block("🛑 ممنوع الرندر قبل الموافقة في الاستوديو. افتح الاستوديو أولاً وراجع الفيديو.")
        
        # 2. منع الاستوديو قبل Probe-QC
        if "npm run studio" in command or "npx remotion studio" in command:
            if not check_probe_qc_passed():
                block("🛑 ممنوع فتح الاستوديو قبل نجاح Probe-QC. شغّل probe_qc.py أولاً.")
        
        # 3. منع materialize بدون stage_gate
        if "materialize_project.py" in command:
            project_id = extract_project_id(command)
            if project_id and not check_stage_gate(project_id, "materialize"):
                block(f"🛑 ممنوع البناء قبل نجاح stage_gate للمشروع {project_id}.")
        
        # 4. منع الرندر المتزامن قبل اكتمال المشاهد
        if "--concurrency" in command and "render" in command:
            if not all_scenes_completed():
                block("🛑 ممنوع الرندر المتزامن قبل اكتمال جميع المشاهد. أنهِ كل المشاهد أولاً.")
        
        # 5. منع حذف الملفات الحرجة
        if any(op in command for op in ["rm -rf", "del /s", "rmdir /s"]):
            if any(protected in command for protected in [".agents/", "engine/", "templates/", "scripts/"]):
                block("🛑 ممنوع حذف ملفات النظام الحرجة.")
        
        # 6. منع تثبيت حزم غير معتمدة
        if "npm install" in command or "pip install" in command:
            allowed_packages = ["remotion", "@remotion/cli", "react", "ffmpeg-static"]
            for pkg in extract_packages(command):
                if pkg not in allowed_packages:
                    block(f"🛑 ممنوع تثبيت حزمة غير معتمدة: {pkg}. أضفها إلى plugin.json أولاً.")
        
        # الأمر سليم
        allow()
        
    except Exception as e:
        # في حال الخطأ، اسمح (لا نريد منع العمل بسبب خطأ في الحارس)
        allow()


def check_studio_approval() -> bool:
    """هل وافق المستخدم في الاستوديو؟"""
    # افحص وجود ملف موافقة
    approval_files = list(Path("projects").glob("*/.studio_approved"))
    return len(approval_files) > 0


def check_probe_qc_passed() -> bool:
    """هل نجح Probe-QC؟"""
    reports = list(Path("projects").glob("*/probe_qc_report.json"))
    if not reports:
        return False
    latest = max(reports, key=lambda p: p.stat().st_mtime)
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        return data.get("status") == "pass"
    except:
        return False


def check_stage_gate(project_id: str, stage: str) -> bool:
    """هل نجح stage_gate للمرحلة المطلوبة؟"""
    gate_file = Path(f"projects/{project_id}/.stage_gate_status.json")
    if not gate_file.exists():
        return False
    try:
        data = json.loads(gate_file.read_text(encoding="utf-8"))
        return data.get(stage) == "passed"
    except:
        return False


def all_scenes_completed() -> bool:
    """هل اكتملت جميع المشاهد؟"""
    # افحص وجود QC reports لكل مشهد
    scene_plans = list(Path("projects").glob("*/scenes/scene_*_plan.md"))
    scene_qcs = list(Path("projects").glob("*/scenes/scene*_qc_report.json"))
    return len(scene_plans) == len(scene_qcs)


def extract_project_id(command: str) -> str:
    """يستخرج معرف المشروع من الأمر"""
    import re
    match = re.search(r'projects/([^/\s]+)', command)
    return match.group(1) if match else None


def extract_packages(command: str) -> list:
    """يستخرج أسماء الحزم من أمر التثبيت"""
    import re
    # npm install pkg1 pkg2
    match = re.search(r'npm install\s+(.+)', command)
    if match:
        return [p.strip() for p in match.group(1).split() if not p.startswith('-')]
    # pip install pkg1 pkg2
    match = re.search(r'pip install\s+(.+)', command)
    if match:
        return [p.strip() for p in match.group(1).split() if not p.startswith('-')]
    return []


def allow():
    """يسمح بتنفيذ الأمر"""
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)


def block(reason: str):
    """يمنع تنفيذ الأمر ويرسل سبباً للوكيل"""
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "additionalContext": "الوكيل يجب أن يتبع البروتوكول v3.0 بدقة."
    }))
    sys.exit(0)  # ملاحظة: sys.exit(0) وليس 2 لأن Antigravity يتعامل مع stdout


if __name__ == "__main__":
    main()
