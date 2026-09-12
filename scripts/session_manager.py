#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

def save_state(project_id: str, state_data: dict):
    """حفظ حالة الجلسة"""
    project_dir = Path(f"projects/{project_id}")
    project_dir.mkdir(parents=True, exist_ok=True)
    state_file = project_dir / ".session_state.json"
    
    state_file.write_text(json.dumps(state_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return True

def restore_state(project_id: str) -> dict:
    """استرجاع حالة الجلسة"""
    state_file = Path(f"projects/{project_id}/.session_state.json")
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {}

def list_states():
    """استعراض كل الجلسات المحفوظة"""
    projects_dir = Path("projects")
    if not projects_dir.exists():
        return []
        
    sessions = []
    for proj in projects_dir.iterdir():
        if proj.is_dir() and (proj / ".session_state.json").exists():
            sessions.append(proj.name)
            
    return sessions
