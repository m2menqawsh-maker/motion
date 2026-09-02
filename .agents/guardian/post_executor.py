#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Post-Executor Hook for Google Antigravity
يفحص النتائج بعد تنفيذ الأوامر الحرجة.
"""
import sys
import json
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        tool_output = data.get("tool_output", "")
        command = ""
        if isinstance(tool_input, dict):
            command = tool_input.get("command", "") or tool_input.get("CommandLine", "")
        elif isinstance(tool_input, str):
            command = tool_input
        
        # بعد تشغيل probe_qc.py، تحقق من النتيجة
        if "probe_qc.py" in command:
            if "pass" not in str(tool_output).lower():
                # أرسل تحذيراً للوكيل
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "⚠️ Probe-QC فشل. لا تنتقل للرندر أو الاستوديو حتى يتم إصلاح الأخطاء."
                    }
                }))
                sys.exit(0)
        
        # بعد تشغيل motion_validator.py
        if "motion_validator.py" in command:
            if "Failed" in str(tool_output) or "❌" in str(tool_output):
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "⚠️ motion_validator فشل. لا تنتقل للبناء حتى يتم إصلاح الأخطاء الإبداعية."
                    }
                }))
                sys.exit(0)
        
        # بعد materialize_project.py، تأكد من نجاحه
        if "materialize_project.py" in command:
            if "Error" in str(tool_output) or "Failed" in str(tool_output):
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": "⚠️ materialize_project فشل. أصلح الأخطاء قبل المتابعة."
                    }
                }))
                sys.exit(0)
        
        # افتراضياً: لا تعليق إضافي
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)
        
    except Exception:
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)


if __name__ == "__main__":
    main()
