#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Write Guard for Google Antigravity
يمنع الكتابة في المسارات المحظورة.
"""
import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils import load_config, log_audit, is_path_safe, check_circuit_breaker, update_circuit_breaker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("toolCall", {}).get("args", {})
        
        if not tool_input:
            tool_input = data.get("tool_input", {})
            
        file_path = tool_input.get("TargetFile", "") or tool_input.get("file_path", "")
        file_path = file_path.replace("\\", "/")
        
        if not file_path:
            allow()
            
        cb_err = check_circuit_breaker("write_guard", file_path)
        if cb_err:
            block(cb_err, file_path)
            
        config = load_config()
        write_rules = config.get("write_violations", {})
        blocked_paths = write_rules.get("blocked_paths", [])
        blocked_files = write_rules.get("blocked_files", [])
        allowed_prefixes = write_rules.get("allowed_prefixes", [])
        
        for blocked in blocked_paths:
            if blocked in file_path:
                block(f"🛑 ممنوع الكتابة في {blocked}. هذه ملفات نظامية محمية.", file_path)
        
        for blocked_file in blocked_files:
            if file_path.endswith(blocked_file):
                block(f"🛑 ممنوع تعديل أو إنشاء ملف {blocked_file} يدوياً لمنع التزوير وحماية الأختام الميكانيكية.", file_path)
        
        if not is_path_safe(file_path, allowed_prefixes):
            block(f"🛑 مسار غير آمن! (مطلق، أو يحتوي على .. ، أو غير مصرح به). المسموح: {allowed_prefixes}", file_path)
        
        allow(file_path)
        
    except Exception as e:
        # On fatal error, allow to not break system entirely, or block for safety? 
        # We will allow and log it if possible.
        allow("")

def allow(file_path=""):
    if file_path:
        log_audit("ALLOW", "Path is safe.", file_path, "WRITE_GUARD")
        update_circuit_breaker("write_guard", file_path, 0)
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

def block(reason: str, file_path: str):
    log_audit("BLOCK", reason, file_path, "WRITE_GUARD")
    update_circuit_breaker("write_guard", file_path, 1)
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "additionalContext": "محاولة تزوير أو تجاوز بروتوكول الأمان مرفوضة."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
