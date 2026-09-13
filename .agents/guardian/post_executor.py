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

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_config, update_circuit_breaker

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
            command = tool_input.get("command", "") or tool_input.get("CommandLine", "") or str(tool_input)
        elif isinstance(tool_input, str):
            command = tool_input

        is_failure = False
        m = re.search(r"exited with code (\d+)", str(tool_output))
        if m and m.group(1) != "0":
            is_failure = True
        elif "Error" in str(tool_output) or "Failed" in str(tool_output) or "Exception" in str(tool_output):
            if "SUCCESS" not in str(tool_output):
                is_failure = True

        if tool_name:
            update_circuit_breaker(tool_name, command, 1 if is_failure else 0)
        
        config = load_config()
        post_rules = config.get("post_execution_warnings", {})
        
        for script_name, rule in post_rules.items():
            if script_name in command:
                triggered = False
                if rule.get("is_inverse"):
                    trigger_word = rule.get("failure_trigger", "")
                    if trigger_word and trigger_word.lower() not in str(tool_output).lower():
                        triggered = True
                else:
                    triggers = rule.get("failure_triggers", [])
                    for t in triggers:
                        if t in str(tool_output):
                            triggered = True
                            break
                            
                if triggered:
                    print(json.dumps({
                        "hookSpecificOutput": {
                            "hookEventName": "PostToolUse",
                            "additionalContext": rule.get("message", "⚠️ Command failed.")
                        }
                    }))
                    sys.exit(0)
        
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)
        
    except Exception:
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)

if __name__ == "__main__":
    main()
