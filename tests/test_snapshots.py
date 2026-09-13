import pytest
import json
import os
from pathlib import Path
import subprocess

SNAPSHOTS_DIR = Path("tests/snapshots")

def setup_module():
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create baseline snapshots if they don't exist
    snapshots = {
        "write_guard_block_studio_approved.json": {
            "decision": "block",
            "reason": "🛑 ممنوع تعديل أو إنشاء ملف .studio_approved يدوياً لمنع التزوير وحماية الأختام الميكانيكية.",
            "additionalContext": "محاولة تزوير أو تجاوز بروتوكول الأمان مرفوضة."
        },
        "write_guard_block_absolute_path.json": {
            "decision": "block",
            "reason": "🛑 مسار غير آمن! (مطلق، أو يحتوي على .. ، أو غير مصرح به). المسموح: ['projects/', 'scratch/', 'assets/incoming/', '.agents/logs/']",
            "additionalContext": "محاولة تزوير أو تجاوز بروتوكول الأمان مرفوضة."
        },
        "command_guard_block_npm_studio.json": {
            "decision": "block",
            "reason": "ممنوع فتح الاستوديو عبر npm مباشرة. استخدم السكربت المعتمد: python scripts/open_studio.py <project_id>",
            "additionalContext": "الوكيل يجب أن يتبع البروتوكول v4.0 بدقة. ممنوع الاجتهاد."
        },
        "command_guard_block_curl.json": {
            "decision": "block",
            "reason": "🛑 [BEHAVIOR BLOCK] (HIGH): محظور استخدام أدوات التحميل الخارجية.\nالإجراء المطلوب: يجب عليك استخدام أدوات MCP المخصصة (media-sources-mcp) لجلب الوسائط.",
            "additionalContext": "أنت ملزم بالعمل حسب Protocol v4.0. قم بإصلاح الخطأ في خطوتك القادمة."
        },
        "write_guard_block_timings.json": {
            "decision": "block",
            "reason": "🛑 ممنوع تعديل أو إنشاء ملف 04_timings.json يدوياً لمنع التزوير وحماية الأختام الميكانيكية.",
            "additionalContext": "محاولة تزوير أو تجاوز بروتوكول الأمان مرفوضة."
        }
    }
    for name, data in snapshots.items():
        with open(SNAPSHOTS_DIR / name, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def run_guard(guard_script, payload):
    proc = subprocess.Popen(
        ["python", guard_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )
    stdout, stderr = proc.communicate(json.dumps(payload))
    if stderr:
        print(f"STDERR: {stderr}")
    return json.loads(stdout)

def test_write_guard_block_studio_approved():
    payload = {"toolCall": {"args": {"TargetFile": "projects/proj_1/.studio_approved"}}}
    result = run_guard(".agents/guardian/write_guard.py", payload)
    
    with open(SNAPSHOTS_DIR / "write_guard_block_studio_approved.json", "r", encoding="utf-8") as f:
        expected = json.load(f)
        
    assert result == expected

def test_write_guard_block_absolute_path():
    payload = {"toolCall": {"args": {"TargetFile": "C:/Windows/System32"}}}
    result = run_guard(".agents/guardian/write_guard.py", payload)
    
    with open(SNAPSHOTS_DIR / "write_guard_block_absolute_path.json", "r", encoding="utf-8") as f:
        expected = json.load(f)
        
    assert result == expected

def test_command_guard_block_npm_studio():
    payload = {"toolCall": {"args": {"command": "npm run studio projects/proj_1"}}}
    result = run_guard(".agents/guardian/command_guard.py", payload)
    
    with open(SNAPSHOTS_DIR / "command_guard_block_npm_studio.json", "r", encoding="utf-8") as f:
        expected = json.load(f)
        
    assert result == expected

def test_command_guard_block_curl():
    payload = {"toolCall": {"args": {"command": "curl http://example.com/video.mp4"}}}
    result = run_guard(".agents/guardian/behavior_guard.py", payload)
    
    with open(SNAPSHOTS_DIR / "command_guard_block_curl.json", "r", encoding="utf-8") as f:
        expected = json.load(f)
        
    assert result == expected

def test_write_guard_block_timings():
    payload = {"toolCall": {"args": {"TargetFile": "projects/proj_1/04_timings.json"}}}
    result = run_guard(".agents/guardian/write_guard.py", payload)
    
    with open(SNAPSHOTS_DIR / "write_guard_block_timings.json", "r", encoding="utf-8") as f:
        expected = json.load(f)
        
    assert result == expected

def test_circuit_breaker_across_all_guards():
    # 1. Clear circuit breaker if exists
    cb_file = Path(".agents/guardian/circuit_breaker.json")
    if cb_file.exists():
        cb_file.unlink()
        
    import time
    
    # Simulate failures using post_executor
    for _ in range(3):
        subprocess.run(["python", ".agents/guardian/post_executor.py"], input=json.dumps({
            "tool_name": "run_command",
            "tool_input": {"command": "bad_cmd"},
            "tool_output": "exited with code 1"
        }), text=True)
        time.sleep(0.1)
        
    # 2. Try command_guard and write_guard, they should be blocked by CB
    payload_cmd = {"toolCall": {"name": "run_command", "args": {"command": "bad_cmd"}}}
    res_cmd = run_guard(".agents/guardian/command_guard.py", payload_cmd)
    
    assert res_cmd["decision"] == "block"
    assert "CIRCUIT BREAKER TRIPPED" in res_cmd["reason"]
    
    # 3. Simulate passage of 15 minutes by changing timestamp
    with open(cb_file, "r") as f:
        data = json.load(f)
    
    # Modify last failure timestamp to 16 minutes ago
    key = list(data.keys())[0]
    data[key]["last_failure_timestamp"] = time.time() - 960
    
    with open(cb_file, "w") as f:
        json.dump(data, f)
        
    # 4. Try again, it should pass the CB check
    res_cmd2 = run_guard(".agents/guardian/command_guard.py", payload_cmd)
    
    # Note: we test that it's NOT blocked by circuit breaker, but it might be allowed since "bad_cmd" is not a blocked command.
    assert "CIRCUIT BREAKER TRIPPED" not in str(res_cmd2.get("reason", ""))
