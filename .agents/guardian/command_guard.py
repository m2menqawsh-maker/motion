#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Guard for Google Antigravity (Protocol v4.0)
يعترض الأوامر الخطيرة قبل تنفيذها.
"""
import sys
import json
import os
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_config, log_audit, check_circuit_breaker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("toolCall", {}).get("name", "")
        tool_input = data.get("toolCall", {}).get("args", {})
        command = ""
        if isinstance(tool_input, dict):
            command = tool_input.get("command", "") or tool_input.get("CommandLine", "")
        elif isinstance(tool_input, str):
            command = tool_input
        
        if not command:
            allow("Empty Command")
            
        cb_err = check_circuit_breaker(tool_name, command)
        if cb_err:
            block(cb_err, command)
        
        config = load_config()
        cmd_rules = config.get("command_restrictions", {})
        blocked_commands = cmd_rules.get("blocked_commands", [])
        destructive_patterns = cmd_rules.get("destructive_patterns", [])
        protected_from_destruction = cmd_rules.get("protected_from_destruction", [])
        allowed_packages = cmd_rules.get("allowed_packages", [])
        
        for b_cmd in blocked_commands:
            if b_cmd["pattern"] in command:
                block(b_cmd["message"], command)
        
        # الشرط المعقد (Business Logic stays here)
        if "materialize_project.py" in command:
            project_id = extract_project_id(command)
            if project_id and not check_materialize_ready(project_id):
                block(f"🛑 ممنوع البناء للمشروع {project_id}! يجب أن تقوم أولاً بتجهيز الملفات الثلاثة: master_plan.md و 05_blueprint.json و 02_asset_manifest.json.", command)
        
        if any(op in command for op in destructive_patterns):
            if any(protected in command for protected in protected_from_destruction):
                block("🛑 ممنوع حذف ملفات النظام الحرجة.", command)
        
        if "npm install" in command or "pip install" in command:
            for pkg in extract_packages(command):
                if pkg not in allowed_packages:
                    block(f"🛑 ممنوع تثبيت حزمة غير معتمدة: {pkg}. أضفها إلى plugin.json أولاً.", command)
        
        allow(command)
        
    except Exception as e:
        allow("Exception Occurred")

def check_materialize_ready(project_id: str) -> bool:
    proj_dir = Path(f"projects/{project_id}")
    if not proj_dir.exists():
        return False
    required = ["master_plan.md", "05_blueprint.json", "02_asset_manifest.json"]
    for req in required:
        if not (proj_dir / req).exists():
            return False
    return True

def extract_project_id(command: str) -> str:
    match = re.search(r'projects/([^/\s]+)', command)
    if match: return match.group(1)
    parts = command.split()
    for i, p in enumerate(parts):
        if p.endswith("materialize_project.py") and i + 1 < len(parts):
            return parts[i+1]
    return None

def extract_packages(command: str) -> list:
    match = re.search(r'npm install\s+(.+)', command)
    if match: return [p.strip() for p in match.group(1).split() if not p.startswith('-')]
    match = re.search(r'pip install\s+(.+)', command)
    if match: return [p.strip() for p in match.group(1).split() if not p.startswith('-')]
    return []

def allow(command=""):
    if command:
        log_audit("ALLOW", "Command is safe.", command, "COMMAND_GUARD")
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

def block(reason: str, command=""):
    log_audit("BLOCK", reason, command, "COMMAND_GUARD")
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "additionalContext": "الوكيل يجب أن يتبع البروتوكول v4.0 بدقة. ممنوع الاجتهاد."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
