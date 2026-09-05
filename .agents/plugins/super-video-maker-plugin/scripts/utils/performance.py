import time
from functools import wraps
from pathlib import Path
import json
from datetime import datetime

def track_performance(operation_name: str):
    """Decorator لقياس أداء أي دالة"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            
            # سجل الأداء
            _log_performance(operation_name, elapsed, func.__name__)
            
            return result
        return wrapper
    return decorator

def _log_performance(operation: str, elapsed: float, func_name: str):
    """يسجل الأداء في ملف مركزي"""
    perf_file = Path('.agents/performance_log.json')
    
    if perf_file.exists():
        try:
            data = json.loads(perf_file.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    
    data.append({
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "function": func_name,
        "elapsed_seconds": round(elapsed, 3),
        "elapsed_human": f"{elapsed:.2f}s"
    })
    
    # احتفظ فقط بآخر 1000 سجل
    data = data[-1000:]
    
    perf_file.parent.mkdir(parents=True, exist_ok=True)
    perf_file.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

def generate_performance_report(project_id: str):
    perf_file = Path('.agents/performance_log.json')
    if not perf_file.exists():
        return
        
    try:
        data = json.loads(perf_file.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return
        
    # احسب الإحصائيات
    operations = {}
    for entry in data[-100:]:  # آخر 100 عملية
        op = entry['operation']
        if op not in operations:
            operations[op] = []
        operations[op].append(entry['elapsed_seconds'])
    
    stats = {}
    for op, times in operations.items():
        stats[op] = {
            "count": len(times),
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times)
        }
    
    # احفظ التقرير
    report = {
        "project_id": project_id,
        "timestamp": datetime.now().isoformat(),
        "stats": stats
    }
    
    report_file = Path(f'projects/{project_id}/performance_report.json')
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
