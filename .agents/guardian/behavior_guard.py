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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

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
            allow()
            
        # 1. فحص الأداة الحالية
        current_tool_str = json.dumps(tool_call, ensure_ascii=False)
        violation = check_text_for_violations(current_tool_str, config)
        if violation:
            block(violation)
            
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
                block(violation)
                
        allow()
        
    except Exception as e:
        allow()

def check_text_for_violations(text: str, config: dict):
    if not text.strip():
        return None
        
    for category in ["command_violations", "behavioral_violations", "protocol_violations", "plan_quality_violations"]:
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

def allow():
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

def block(reason: str):
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "additionalContext": "أنت ملزم بالعمل حسب Protocol v4.0. قم بإصلاح الخطأ في خطوتك القادمة."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
