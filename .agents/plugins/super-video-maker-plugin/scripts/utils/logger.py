import logging
import sys
from pathlib import Path
from datetime import datetime

class UnifiedLogger:
    def __init__(self, script_name: str, project_id: str = None):
        self.script_name = script_name
        self.project_id = project_id
        
        # إنشاء logger
        self.logger = logging.getLogger(script_name)
        self.logger.setLevel(logging.DEBUG)
        
        # حذف الـ handlers القديمة
        if not self.logger.handlers:
            # Console handler
            console = logging.StreamHandler(sys.stdout)
            console.setLevel(logging.INFO)
            console.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%H:%M:%S'
            ))
            self.logger.addHandler(console)
            
            # File handler (للمشاريع)
            if project_id:
                log_dir = Path(f'projects/{project_id}/logs')
                log_dir.mkdir(parents=True, exist_ok=True)
                log_file = log_dir / f'{script_name}_{datetime.now().strftime("%Y%m%d")}.log'
                
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
                ))
                self.logger.addHandler(file_handler)
        
        if project_id:
            from utils.error_tracker import ErrorTracker
            self.tracker = ErrorTracker(project_id)
        else:
            self.tracker = None
    
    def info(self, msg):
        self.logger.info(f"🟢 {msg}")
    
    def success(self, msg):
        self.logger.info(f"✅ {msg}")
    
    def warning(self, msg):
        self.logger.warning(f"⚠️ {msg}")
    
    def error(self, msg, context=None):
        self.logger.error(f"❌ {msg}")
        if self.tracker:
            self.tracker.log_error(
                script=self.script_name,
                error_type="runtime",
                message=msg,
                context=context
            )
    
    def debug(self, msg):
        self.logger.debug(f"🔍 {msg}")
