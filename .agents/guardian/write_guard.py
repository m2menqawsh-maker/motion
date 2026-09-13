#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Write Guard for Google Antigravity
يمنع الكتابة في المسارات المحظورة.
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

def log_audit(decision: str, reason: str, file_path: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    log_entry = f"[{timestamp}] [WRITE_GUARD] [{decision}] TARGET: {file_path} | REASON: {reason}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception:
        pass

def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("toolCall", {}).get("args", {})
        
        # Fallback to old format just in case
        if not tool_input:
            tool_input = data.get("tool_input", {})
            
        file_path = tool_input.get("TargetFile", "") or tool_input.get("file_path", "")
        
        # normalize path separators
        file_path = file_path.replace("\\", "/")
        
        if not file_path:
            allow()
            
        # المسارات المحظورة المطلقة
        BLOCKED_PATHS = [
            ".agents/plugins/super-video-maker-plugin/engine/",
            ".agents/plugins/super-video-maker-plugin/templates/",
            ".agents/plugins/super-video-maker-plugin/scripts/",
            ".agents/plugins/super-video-maker-plugin/ground-truth/",
            ".agents/guardian/",
            ".agents/rules/",
            ".agents/secrets/",
            "assets/processing/",
            "assets/ready/",
        ]
        
        # الملفات المحظورة كلياً (لمنع التزوير)
        BLOCKED_FILES = [
            "TEMPLATE_INDEX.md",
            "plugin.json",
            "mcp.json",
            "probe_qc_report.json",
            ".seal",
            ".qc_salt",
            ".studio_approved",
            ".studio_unlocked",
            "04_timings.json",
            "hooks.json",
            "AGENTS.md",
            "circuit_breaker.json"
        ]
        
        for blocked in BLOCKED_PATHS:
            if blocked in file_path:
                block(f"🛑 ممنوع الكتابة في {blocked}. هذه ملفات نظامية محمية.", file_path)
        
        for blocked_file in BLOCKED_FILES:
            if file_path.endswith(blocked_file):
                block(f"🛑 ممنوع تعديل أو إنشاء ملف {blocked_file} يدوياً لمنع التزوير وحماية الأختام الميكانيكية.", file_path)
        
        # المسار المسموح للكتابة: projects/, scratch/, assets/incoming/, وسجلات النظام فقط
        if not (file_path.startswith("projects/") or 
                "projects/" in file_path or
                file_path.startswith("scratch/") or
                "scratch/" in file_path or
                file_path.startswith("assets/incoming/") or
                "assets/incoming/" in file_path or
                file_path.startswith(".agents/logs/") or
                ".agents/logs/" in file_path):
            block(f"🛑 الكتابة مسموحة فقط في projects/, scratch/, assets/incoming/, و .agents/logs/. المسار: {file_path}", file_path)
        
        allow(file_path)
        
    except Exception as e:
        allow("")

def allow(file_path=""):
    if file_path:
        log_audit("ALLOW", "Path is safe.", file_path)
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

def block(reason: str, file_path: str):
    log_audit("BLOCK", reason, file_path)
    print(json.dumps({
        "decision": "block",
        "reason": reason,
        "additionalContext": "محاولة تزوير أو تجاوز بروتوكول الأمان مرفوضة."
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
