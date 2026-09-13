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

import time

CIRCUIT_BREAKER_FILE = Path(".agents/guardian/circuit_breaker.json")

def update_circuit_breaker(tool_name: str, command: str, exit_code: int):
    lock_dir = CIRCUIT_BREAKER_FILE.with_suffix(".lock")
    for _ in range(50):
        try:
            lock_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            time.sleep(0.1)
    else:
        pass
        
    try:
        cb_data = {}
        if CIRCUIT_BREAKER_FILE.exists():
            try:
                with open(CIRCUIT_BREAKER_FILE, "r", encoding="utf-8") as f:
                    cb_data = json.load(f)
            except Exception:
                pass
                
        sig = str(command)[:50] if command else "default"
        key = f"{tool_name}::{sig}"
        
        now = time.time()
        if key not in cb_data:
            cb_data[key] = {"failures": 0, "last_failure_timestamp": 0.0}
            
        if now - cb_data[key].get("last_failure_timestamp", 0) > 900:
            cb_data[key]["failures"] = 0
            
        if exit_code != 0:
            cb_data[key]["failures"] += 1
            cb_data[key]["last_failure_timestamp"] = now
        else:
            cb_data[key]["failures"] = 0
            
        CIRCUIT_BREAKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CIRCUIT_BREAKER_FILE, "w", encoding="utf-8") as f:
            json.dump(cb_data, f, ensure_ascii=False, indent=2)
            
    finally:
        try:
            lock_dir.rmdir()
        except Exception:
            pass

def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        tool_output = data.get("tool_output", "")
        command = ""
        if isinstance(tool_input, dict):
            command = tool_input.get("command", "") or tool_input.get("CommandLine", "") or str(tool_input)
        elif isinstance(tool_input, str):
            command = tool_input

        # Determine success
        is_failure = False
        m = re.search(r"exited with code (\d+)", str(tool_output))
        if m and m.group(1) != "0":
            is_failure = True
        elif "Error" in str(tool_output) or "Failed" in str(tool_output) or "Exception" in str(tool_output):
            if "SUCCESS" not in str(tool_output):
                is_failure = True

        if tool_name:
            update_circuit_breaker(tool_name, command, 1 if is_failure else 0)
        
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
