import json
from pathlib import Path
from datetime import datetime
from typing import Optional

class ErrorTracker:
    def __init__(self, project_id: str):
        self.project_id = project_id
        # Workspace root is usually CWD, so 'projects/{project_id}'
        self.errors_file = Path(f'projects/{project_id}/error_log.json')
        self.errors_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_error(self, 
                  script: str, 
                  error_type: str, 
                  message: str,
                  context: Optional[dict] = None,
                  severity: str = "error"):
        """يسجل خطأ مع السياق الكامل"""
        errors = self._load_errors()
        
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "script": script,
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "context": context or {},
            "project_id": self.project_id
        }
        
        errors.append(error_entry)
        self._save_errors(errors)
        
        return error_entry
    
    def get_errors(self, script: str = None, since: datetime = None):
        """يحصل على الأخطاء مع فلترة"""
        errors = self._load_errors()
        if script:
            errors = [e for e in errors if e['script'] == script]
        if since:
            errors = [e for e in errors 
                     if datetime.fromisoformat(e['timestamp']) >= since]
        return errors
    
    def get_stats(self):
        """إحصائيات الأخطاء"""
        errors = self._load_errors()
        by_script = {}
        by_type = {}
        
        for e in errors:
            by_script[e['script']] = by_script.get(e['script'], 0) + 1
            by_type[e['error_type']] = by_type.get(e['error_type'], 0) + 1
        
        return {
            "total": len(errors),
            "by_script": by_script,
            "by_type": by_type
        }
    
    def _load_errors(self):
        if self.errors_file.exists():
            try:
                return json.loads(self.errors_file.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                return []
        return []
    
    def _save_errors(self, errors):
        self.errors_file.write_text(
            json.dumps(errors, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
