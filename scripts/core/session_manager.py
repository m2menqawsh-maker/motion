import subprocess
from scripts.security.security import safe_subprocess
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from typing import Optional

from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState

def save_state(project_id: str, state_data: dict, expected_revision: Optional[int] = None) -> bool:
    """حفظ حالة الجلسة عبر StateStore مع الالتزام الصريح بعقد الـ CAS"""
    project_dir = Path(f"projects/{project_id}")
    project_dir.mkdir(parents=True, exist_ok=True)
    state = ProjectState(**state_data)
    
    if expected_revision is None:
        if "expected_revision" in state_data:
            expected_revision = state_data["expected_revision"]
        elif "revision" in state_data:
            expected_revision = state_data["revision"]

    StateStore.save(project_dir, state, expected_revision=expected_revision)
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
