#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Behavior Guard for Google Antigravity
يعمل قبل أي أداة لمراقبة السلوكيات (النصوص والأدوات) ومنع الهلوسات.
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
        transcript_path = data.get("transcriptPath", "")
        tool_call = data.get("toolCall", {})
        
        config = load_config()
        if not config:
            allow("No config found")
            
        current_tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})
        command = args.get("command", "") or args.get("CommandLine", "") or str(args)
        
        cb_err = check_circuit_breaker(current_tool_name, command)
        if cb_err:
            block(cb_err, "Circuit Breaker")
            
        current_tool_str = json.dumps(tool_call, ensure_ascii=False)
        violation = check_text_for_violations(current_tool_str, config, is_read_tool=current_tool_name in ["view_file", "grep_search", "list_dir", "read_url_content", "read_resource", "list_resources"])
        if violation:
            block(violation, "Current Tool Call")
            
        if transcript_path and os.path.exists(transcript_path):
            agent_text_since_user = []
            
            with open(transcript_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            last_user_idx = 0
            for i in range(len(lines) - 1, -1, -1):
                try:
                    step = json.loads(lines[i])
                    if step.get("type") == "USER_INPUT":
                        last_user_idx = i
                        break
                except:
                    pass
                    
            for i in range(last_user_idx, len(lines)):
                try:
                    step = json.loads(lines[i])
                    if step.get("source") == "MODEL":
                        agent_text_since_user.append(step.get("content", ""))
                        if "tool_calls" in step:
                            agent_text_since_user.append(json.dumps(step["tool_calls"], ensure_ascii=False))
                except:
                    pass
                    
            full_text_to_check = " ".join(agent_text_since_user)
            violation = check_text_for_violations(full_text_to_check, config)
            if violation:
                block(violation, "Transcript Since Last User")
                
        allow("Tool Call Passed")
        
    except Exception as e:
        allow()

def check_text_for_violations(text: str, config: dict, is_read_tool: bool = False):
    if not text.strip():
        return None
        
    for category in ["command_violations", "behavioral_violations", "protocol_violations", "plan_quality_violations"]:
        if is_read_tool and category == "protocol_violations":
            continue
            
        rules = config.get(category, [])
        for rule in rules:
            pattern = rule.get("pattern", "")
            if pattern and re.search(pattern, text, re.IGNORECASE):
                severity = rule.get("severity", "MEDIUM")
                msg = rule.get("message", "")
                fix = rule.get("fix", "")
                return f"🛑 [BEHAVIOR BLOCK] ({severity}): {msg}\nالإجراء المطلوب: {fix}"
    return None

def allow(context=""):
    if context:
        log_audit("ALLOW", "Behavior is safe.", context, "BEHAVIOR_GUARD")
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

def block(reason: str, context=""):
    log_audit("BLOCK", reason, context, "BEHAVIOR_GUARD")
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "additionalContext": "أنت ملزم بالعمل حسب Protocol v4.0. قم بإصلاح الخطأ في خطوتك القادمة."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
