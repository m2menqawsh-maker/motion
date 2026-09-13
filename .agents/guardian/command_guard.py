#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Guard for Google Antigravity (Protocol v4.0)
يعترض الأوامر الخطيرة قبل تنفيذها.
"""
import sys
import json
import os
import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

LOG_FILE = Path(".agents/logs/guardrails.log")

def log_audit(decision: str, reason: str, command: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"[{timestamp}] [COMMAND_GUARD] [{decision}] COMMAND: {command} | REASON: {reason}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass

def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("toolCall", {}).get("args", {})
        command = ""
        if isinstance(tool_input, dict):
            command = tool_input.get("command", "") or tool_input.get("CommandLine", "")
        elif isinstance(tool_input, str):
            command = tool_input
        
        if not command:
            allow("Empty Command")
        
        # ── القواعد الصارمة (v4.0) ──────────────────────────
        
        # 1. المنع المطلق لأوامر Node/npm المباشرة
        if "npx remotion render" in command:
            block("🛑 ممنوع استخدام أمر npx remotion render مباشرة. استخدم السكربت المعتمد: python scripts/render_project.py <project_id>", command)
            
        if "npm run studio" in command or "npx remotion studio" in command:
            block("🛑 ممنوع فتح الاستوديو عبر npm مباشرة. استخدم السكربت المعتمد: python scripts/open_studio.py <project_id>", command)
        
        # 2. شرط البناء (Materialize Project)
        if "materialize_project.py" in command:
            project_id = extract_project_id(command)
            if project_id and not check_materialize_ready(project_id):
                block(f"🛑 ممنوع البناء للمشروع {project_id}! يجب أن تقوم أولاً بتجهيز الملفات الثلاثة: master_plan.md و 05_blueprint.json و 02_asset_manifest.json.", command)
        
        # 3. منع حذف الملفات الحرجة
        if any(op in command for op in ["rm -rf", "del /s", "rmdir /s"]):
            if any(protected in command for protected in [".agents/", "engine/", "templates/", "scripts/"]):
                block("🛑 ممنوع حذف ملفات النظام الحرجة.", command)
        
        # 4. منع تثبيت حزم غير معتمدة
        if "npm install" in command or "pip install" in command:
            allowed_packages = ["remotion", "@remotion/cli", "react", "ffmpeg-static", "typescript"]
            for pkg in extract_packages(command):
                if pkg not in allowed_packages:
                    block(f"🛑 ممنوع تثبيت حزمة غير معتمدة: {pkg}. أضفها إلى plugin.json أولاً.", command)
        
        # الأمر سليم
        allow(command)
        
    except Exception as e:
        # في حال الخطأ، اسمح
        allow("Exception Occurred")

def check_materialize_ready(project_id: str) -> bool:
    """هل ملفات المشروع الأساسية موجودة للبناء؟"""
    proj_dir = Path(f"projects/{project_id}")
    if not proj_dir.exists():
        return False
        
    required = ["master_plan.md", "05_blueprint.json", "02_asset_manifest.json"]
    for req in required:
        if not (proj_dir / req).exists():
            return False
            
    return True

def extract_project_id(command: str) -> str:
    import re
    match = re.search(r'projects/([^/\s]+)', command)
    if match: return match.group(1)
    
    # Try finding it as an argument
    parts = command.split()
    for i, p in enumerate(parts):
        if p.endswith("materialize_project.py") and i + 1 < len(parts):
            return parts[i+1]
            
    return None

def extract_packages(command: str) -> list:
    import re
    match = re.search(r'npm install\s+(.+)', command)
    if match: return [p.strip() for p in match.group(1).split() if not p.startswith('-')]
    match = re.search(r'pip install\s+(.+)', command)
    if match: return [p.strip() for p in match.group(1).split() if not p.startswith('-')]
    return []

def allow(command=""):
    if command:
        log_audit("ALLOW", "Command is safe.", command)
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

def block(reason: str, command=""):
    log_audit("BLOCK", reason, command)
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "additionalContext": "الوكيل يجب أن يتبع البروتوكول v4.0 بدقة. ممنوع الاجتهاد."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
