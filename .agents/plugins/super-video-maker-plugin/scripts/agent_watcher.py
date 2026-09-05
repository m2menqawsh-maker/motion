import os
import sys
from utils.logger import UnifiedLogger
log = UnifiedLogger("agent_watcher")

import json
import time
import re
import argparse
from datetime import datetime

def load_config():
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..", "config", "violations_config.json"
    )
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def check_line(line, config, alerts_path):
    # Parse json line
    try:
        data = json.loads(line)
    except:
        return
        
    # We mainly care about agent responses/tool calls or tool outputs
    content = data.get("content", "")
    tool_calls = data.get("tool_calls", [])
    
    text_to_check = content
    for call in tool_calls:
        if isinstance(call, dict):
            # Convert args to string to check for commands
            text_to_check += " " + json.dumps(call.get("arguments", {}))
            
    if not text_to_check.strip():
        return
        
    violations = []
    
    for category in ["command_violations", "behavioral_violations", "protocol_violations", "plan_quality_violations"]:
        rules = config.get(category, [])
        for rule in rules:
            pattern = rule.get("pattern", "")
            if pattern and re.search(pattern, text_to_check, re.IGNORECASE):
                violations.append((category, rule, text_to_check))
                
    if violations:
        write_alerts(alerts_path, violations)

def write_alerts(alerts_path, violations):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode = 'a' if os.path.exists(alerts_path) else 'w'
    
    with open(alerts_path, mode, encoding="utf-8") as f:
        for cat, rule, text in violations:
            severity = rule.get("severity", "MEDIUM")
            f.write(f"## تنبيه (التصنيف: {severity})\n")
            f.write(f"- **النوع:** {cat}\n")
            f.write(f"- **التوقيت:** {timestamp}\n")
            f.write(f"- **القاعدة:** {rule.get('message', '')}\n")
            f.write(f"- **الإجراء المطلوب:** {rule.get('fix', '')}\n")
            f.write(f"- **المصدر:** agent_watcher.py\n")
            f.write("---\n\n")
            log.info(f"️ تم رصد مخالفة ({severity}): {rule.get('message', '')}")

def watch_transcript(project_id, brain_session_path):
    alerts_path = os.path.join("projects", project_id, ".agent_alerts.md")
    os.makedirs(os.path.dirname(alerts_path), exist_ok=True)
    
    transcript_path = os.path.join(brain_session_path, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(transcript_path):
        log.info(f"Transcript not found at {transcript_path}")
        sys.exit(1)
        
    config = load_config()
    log.info(f"👀 بدء مراقبة الوكيل لمشروع {project_id}...")
    
    with open(transcript_path, "r", encoding="utf-8") as f:
        # Seek to the end of the file
        f.seek(0, os.SEEK_END)
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
                
            check_line(line, config, alerts_path)
            
            # Simple check to clear alerts if a user message is detected
            try:
                data = json.loads(line)
                if data.get("type") == "USER_INPUT":
                    if os.path.exists(alerts_path):
                        os.remove(alerts_path)
                        log.info("🧹 تم مسح التنبيهات السابقة بعد رسالة المستخدم.")
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description="مراقب الوكيل")
    parser.add_argument("project_id", help="معرف المشروع")
    parser.add_argument("brain_session_path", help="مسار الجلسة")
    args = parser.parse_args()
    
    try:
        watch_transcript(args.project_id, args.brain_session_path)
    except KeyboardInterrupt:
        log.info("تم إيقاف المراقبة.")

if __name__ == "__main__":
    main()
