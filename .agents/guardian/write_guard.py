#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Write Guard for Google Antigravity
يمنع الكتابة في المسارات المحظورة.
"""
import sys
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    try:
        data = json.load(sys.stdin)
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "") or tool_input.get("TargetFile", "")
        
        # normalize path separators
        file_path = file_path.replace("\\", "/")
        
        if not file_path:
            allow()
        
        # المسارات المحظورة
        BLOCKED_PATHS = [
            ".agents/plugins/super-video-maker-plugin/engine/",
            ".agents/plugins/super-video-maker-plugin/templates/",
            ".agents/plugins/super-video-maker-plugin/scripts/",
            ".agents/plugins/super-video-maker-plugin/ground-truth/",
            "assets/processing/",
            "assets/ready/",
        ]
        
        # الملفات المحظورة (لا تُعدل إلا بإذن)
        BLOCKED_FILES = [
            "TEMPLATE_INDEX.md",
            "plugin.json",
            "mcp.json",
        ]
        
        for blocked in BLOCKED_PATHS:
            if blocked in file_path:
                block(f"🛑 ممنوع الكتابة في {blocked}. هذه ملفات نظامية محمية.")
        
        for blocked_file in BLOCKED_FILES:
            if file_path.endswith(blocked_file):
                block(f"🛑 ممنوع تعديل {blocked_file} إلا بطلب صريح من المستخدم.")
        
        # المسار المسموح للكتابة: projects/ فقط
        if not (file_path.startswith("projects/") or 
                "projects/" in file_path or
                file_path.startswith("scratch/") or
                "scratch/" in file_path or
                file_path.startswith("assets/incoming/") or
                "assets/incoming/" in file_path or
                file_path.startswith(".agents/") or
                ".agents/" in file_path):
            block(f"🛑 الكتابة مسموحة فقط في projects/, scratch/, أو assets/incoming/. المسار: {file_path}")
        
        allow()
        
    except Exception:
        allow()


def allow():
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)


def block(reason: str):
    print(json.dumps({
        "decision": "block",
        "reason": reason
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
