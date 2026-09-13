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
import datetime
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

LOG_FILE = Path(".agents/logs/guardrails.log")
CIRCUIT_BREAKER_FILE = Path(".agents/guardian/circuit_breaker.json")

def check_circuit_breaker(tool_name: str, tool_call: dict):
    if not CIRCUIT_BREAKER_FILE.exists():
        return
        
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
        with open(CIRCUIT_BREAKER_FILE, "r", encoding="utf-8") as f:
            cb_data = json.load(f)
            
        args = tool_call.get("args", {})
        command = args.get("command", "") or args.get("CommandLine", "") or str(args)
        sig = str(command)[:50] if command else "default"
        key = f"{tool_name}::{sig}"
        
        if key in cb_data:
            failures = cb_data[key].get("failures", 0)
            last_fail = cb_data[key].get("last_failure_timestamp", 0)
            now = time.time()
            if now - last_fail > 900:
                failures = 0
            if failures >= 3:
                block(f"🛑 CIRCUIT BREAKER TRIPPED: Tool failed 3 times. Stop and ask the user for manual intervention.", "Circuit Breaker")
    except Exception:
        pass
    finally:
        try:
            lock_dir.rmdir()
        except Exception:
            pass


def log_audit(decision: str, reason: str, context: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"[{timestamp}] [BEHAVIOR_GUARD] [{decision}] CONTEXT: {context} | REASON: {reason}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass

def load_config():
    config_path = Path(os.path.dirname(__file__)).parent.parent / "config" / "violations_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def main():
    try:
        data = json.load(sys.stdin)
        transcript_path = data.get("transcriptPath", "")
        tool_call = data.get("toolCall", {})
        
        config = load_config()
        if not config:
            allow("No config found")
            
        # 1. فحص الأداة الحالية
        current_tool_name = tool_call.get("name", "")
        check_circuit_breaker(current_tool_name, tool_call)
        current_tool_str = json.dumps(tool_call, ensure_ascii=False)
        violation = check_text_for_violations(current_tool_str, config, is_read_tool=current_tool_name in ["view_file", "grep_search", "list_dir", "read_url_content", "read_resource", "list_resources"])
        if violation:
            block(violation, "Current Tool Call")
            
        # 2. فحص السجل (منذ آخر رسالة مستخدم)
        if transcript_path and os.path.exists(transcript_path):
            agent_text_since_user = []
            
            # قراءة السجل لاستخراج خطوات الوكيل فقط بعد آخر رسالة مستخدم
            with open(transcript_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # العثور على آخر USER_INPUT
            last_user_idx = 0
            for i in range(len(lines) - 1, -1, -1):
                try:
                    step = json.loads(lines[i])
                    if step.get("type") == "USER_INPUT":
                        last_user_idx = i
                        break
                except:
                    pass
                    
            # جمع نصوص الوكيل
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
                # إذا وجد مخالفة، يعيد رسالة الخطأ
                severity = rule.get("severity", "MEDIUM")
                msg = rule.get("message", "")
                fix = rule.get("fix", "")
                return f"🛑 [BEHAVIOR BLOCK] ({severity}): {msg}\nالإجراء المطلوب: {fix}"
    return None

def allow(context=""):
    if context:
        log_audit("ALLOW", "Behavior is safe.", context)
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

def block(reason: str, context=""):
    log_audit("BLOCK", reason, context)
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "additionalContext": "أنت ملزم بالعمل حسب Protocol v4.0. قم بإصلاح الخطأ في خطوتك القادمة."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
