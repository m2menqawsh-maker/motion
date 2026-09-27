import subprocess
from scripts.security.security import safe_subprocess
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path

from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState

def save_state(project_id: str, state_data: dict):
    """حفظ حالة الجلسة"""
    project_dir = Path(f"projects/{project_id}")
    project_dir.mkdir(parents=True, exist_ok=True)
    state = ProjectState(**state_data)
    StateStore.save(project_dir, state)
    return True

def restore_state(project_id: str) -> dict:
    """استرجاع حالة الجلسة"""
    project_dir = Path(f"projects/{project_id}")
    state = StateStore.load(project_dir)
    if not state:
        return {}
    return state.model_dump(mode="json") if hasattr(state, "model_dump") else state.dict()

def list_states():
    """استعراض كل الجلسات المحفوظة"""
    projects_dir = Path("projects")
    if not projects_dir.exists():
        return []
        
    sessions = []
    for proj in projects_dir.iterdir():
        if proj.is_dir() and (proj / ".pipeline_state.json").exists():
            sessions.append(proj.name)
            
    return sessions
