import pytest
import sys
from pathlib import Path
import json

# إضافة مجلد scripts إلى مسار البحث
scripts_dir = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(scripts_dir))

from utils.config import Config
from utils.logger import UnifiedLogger
from utils.error_tracker import ErrorTracker
from utils.performance import track_performance, generate_performance_report

def test_config_singleton():
    """اختبار أن الـ Config هو Singleton"""
    c1 = Config()
    c2 = Config()
    assert c1 is c2

def test_config_get():
    """اختبار قراءة القيم من Config"""
    config = Config()
    # تأكد أننا نقرأ القيم الافتراضية إذا لم نجدها
    assert config.get("non.existent.key", "default_val") == "default_val"
    
def test_unified_logger(tmp_path):
    """اختبار UnifiedLogger وأنه يكتب في الملف الصحيح"""
    import utils.logger
    utils.logger.Path = lambda p: tmp_path / p
    log = UnifiedLogger("test_script", project_id="test_proj")
    log.info("Test message")
    
    log_dir = tmp_path / "projects" / "test_proj" / "logs"
    assert log_dir.exists()
    
    log_files = list(log_dir.glob("test_script*.log"))
    assert len(log_files) > 0
    content = log_files[0].read_text(encoding="utf-8")
    assert "Test message" in content

def test_error_tracker(tmp_path):
    """اختبار متتبع الأخطاء"""
    # نعدل مسار الحفظ ليكون مؤقتاً
    import utils.error_tracker
    utils.error_tracker.Path = lambda p: tmp_path / p
    
    tracker = ErrorTracker("test_proj")
    tracker.log_error("test_script", "runtime", "Test Error")
    
    errors = tracker.get_errors()
    assert len(errors) == 1
    assert errors[0]["message"] == "Test Error"
    
    stats = tracker.get_stats()
    assert stats["total"] == 1
    assert stats["by_script"]["test_script"] == 1

def test_performance_tracker(tmp_path):
    """اختبار مقياس الأداء"""
    import utils.performance
    utils.performance.Path = lambda p: tmp_path / p
    
    @track_performance("test_op")
    def fast_function():
        return 42
        
    res = fast_function()
    assert res == 42
    
    generate_performance_report("test_proj")
    
    perf_file = tmp_path / 'projects' / 'test_proj' / 'performance_report.json'
    assert perf_file.exists()
    data = json.loads(perf_file.read_text(encoding="utf-8"))
    assert "test_op" in data["stats"]
    assert data["stats"]["test_op"]["count"] == 1
