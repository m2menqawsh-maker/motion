import os
import sys
import json
import argparse
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")

PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../projects"))

def get_project_dir(project_id):
    return os.path.join(PROJECTS_DIR, project_id)

def get_state_file(project_id):
    return os.path.join(get_project_dir(project_id), ".session_state.json")

def get_digest_file(project_id):
    return os.path.join(get_project_dir(project_id), "session_digest.md")

def load_state(project_id):
    state_file = get_state_file(project_id)
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "project_id": project_id,
        "current_phase": "غير محددة",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "approved_decisions": [],
        "rejected_decisions": [],
        "scenes_status": {},
        "issues_resolved": [],
        "warnings": []
    }

def save_state(project_id, state):
    state['last_updated'] = datetime.now(timezone.utc).isoformat()
    state_file = get_state_file(project_id)
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def generate_digest(project_id, state):
    lines = []
    lines.append("# 📋 ملخص الجلسة (Session Digest)")
    lines.append(f"**المشروع:** `{project_id}`")
    lines.append(f"**آخر تحديث:** {state['last_updated']}")
    lines.append(f"**المرحلة الحالية:** {state.get('current_phase', 'غير محددة')}")
    lines.append("")
    lines.append("## 🎯 الحالة الحالية")
    lines.append(f"الوكيل يعمل حالياً في مرحلة: {state.get('current_phase', 'غير محددة')}")
    lines.append("")
    lines.append("## ✅ القرارات المعتمدة (لا تقترح عكسها)")
    if state.get('approved_decisions'):
        for d in state['approved_decisions']:
            lines.append(f"- {d['text']}")
    else:
        lines.append("- لا توجد قرارات بعد")
    lines.append("")
    lines.append("## ❌ القرارات المرفوضة (ممنوع تكرارها)")
    if state.get('rejected_decisions'):
        for d in state['rejected_decisions']:
            lines.append(f"- {d['text']}")
    else:
        lines.append("- لا توجد قرارات مرفوضة")
    lines.append("")
    lines.append("## 📊 حالة المشاهد")
    lines.append("| المشهد | الحالة | ملاحظات |")
    lines.append("|---|---|---|")
    if state.get('scenes_status'):
        for scene, status in state['scenes_status'].items():
            lines.append(f"| {scene} | {status} | |")
    else:
        lines.append("| - | - | - |")
    lines.append("")
    
    lines.append("## 🔧 مشاكل محلولة سابقاً")
    issues = state.get('issues_resolved', [])
    warnings = state.get('warnings', [])
    
    # Calculate capacity to keep total lines <= 100
    current_lines_count = len(lines)
    warnings_header_and_content_count = 2 + (len(warnings) if warnings else 1)
    capacity_for_issues = 98 - current_lines_count - warnings_header_and_content_count
    
    if capacity_for_issues < 0:
        capacity_for_issues = 0
        
    display_issues = issues[-capacity_for_issues:] if capacity_for_issues > 0 and issues else []
    
    if display_issues:
        for i in display_issues:
            solution_text = f": {i['solution']}" if i.get('solution') else ""
            lines.append(f"- {i['issue']}{solution_text}")
    else:
        lines.append("- لا توجد مشاكل مسجلة")
        
    lines.append("")
    lines.append("## ⚠️ تحذيرات للوكيل")
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- لا توجد تحذيرات")
        
    # Hard trim just in case
    if len(lines) > 100:
        lines = lines[:100]

    digest_file = get_digest_file(project_id)
    os.makedirs(os.path.dirname(digest_file), exist_ok=True)
    with open(digest_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        
import subprocess

def get_current_session_id():
    brain_dir = r"C:\Users\momen\.gemini\antigravity-ide\brain"
    if not os.path.exists(brain_dir):
        return None
    subdirs = [os.path.join(brain_dir, d) for d in os.listdir(brain_dir) if os.path.isdir(os.path.join(brain_dir, d))]
    if not subdirs:
        return None
    latest_subdir = max(subdirs, key=os.path.getmtime)
    return os.path.basename(latest_subdir)

def count_turns(transcript_path):
    if not os.path.exists(transcript_path):
        return 0
    with open(transcript_path, 'r', encoding='utf-8') as f:
        return len(f.readlines())

def compact(project_id):
    state = load_state(project_id)
    project_dir = get_project_dir(project_id)
    
    # Try reading 04_timings.json to populate scenes if empty
    timings_file = os.path.join(project_dir, "04_timings.json")
    if os.path.exists(timings_file):
        try:
            with open(timings_file, 'r', encoding='utf-8') as f:
                timings = json.load(f)
                scenes = timings.get('scenes', [])
                for idx, sc in enumerate(scenes):
                    scene_name = f"Scene{idx+1}"
                    if scene_name not in state['scenes_status']:
                        state['scenes_status'][scene_name] = "pending"
        except Exception:
            pass
            
    # تنظيف تلقائي للـ transcript
    session_id = get_current_session_id()
    if session_id:
        transcript_path = os.path.join(r"C:\Users\momen\.gemini\antigravity-ide\brain", session_id, ".system_generated", "logs", "transcript.jsonl")
        if count_turns(transcript_path) > 50:
            cleaner_path = os.path.join(os.path.dirname(__file__), "transcript_cleaner.py")
            try:
                subprocess.run([sys.executable, cleaner_path, "clean", session_id], check=True)
                # سجل عملية التنظيف في .session_state.json كـ "issue_resolved"
                state['issues_resolved'].append({"issue": "تنظيف السجل التلقائي", "solution": f"تم تنظيف سجل الجلسة {session_id}"})
            except Exception as e:
                print(f"فشل تنظيف السجل التلقائي: {e}")

    save_state(project_id, state)
    generate_digest(project_id, state)
    print(f"تم إنشاء الـ digest للمشروع {project_id} بنجاح.")


def add_decision(project_id, decision, status):
    state = load_state(project_id)
    entry = {"text": decision, "date": datetime.now(timezone.utc).isoformat()}
    if status == 'approved':
        state['approved_decisions'].append(entry)
    elif status == 'rejected':
        state['rejected_decisions'].append(entry)
    else:
        print("حالة القرار غير صحيحة. استخدم approved أو rejected.")
        return
    save_state(project_id, state)
    generate_digest(project_id, state)
    print(f"تمت إضافة القرار كـ {status}.")

def set_phase(project_id, phase):
    state = load_state(project_id)
    state['current_phase'] = phase
    save_state(project_id, state)
    generate_digest(project_id, state)
    print(f"تم تحديث المرحلة إلى {phase}.")

def add_note(project_id, category, note):
    state = load_state(project_id)
    if category == 'issue_resolved':
        parts = note.split(":", 1)
        issue = parts[0].strip()
        solution = parts[1].strip() if len(parts) > 1 else ""
        state['issues_resolved'].append({"issue": issue, "solution": solution})
    elif category == 'warning':
        state['warnings'].append(note)
    elif category == 'context':
        pass # Could be added to a context array if needed in the future
    save_state(project_id, state)
    generate_digest(project_id, state)
    print("تمت إضافة الملاحظة.")

def show(project_id):
    digest_file = get_digest_file(project_id)
    if os.path.exists(digest_file):
        with open(digest_file, 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print("ملف الـ digest غير موجود.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    p_compact = subparsers.add_parser("compact")
    p_compact.add_argument("project_id")
    
    p_decision = subparsers.add_parser("add-decision")
    p_decision.add_argument("project_id")
    p_decision.add_argument("decision")
    p_decision.add_argument("--status", required=True, choices=["approved", "rejected"])
    
    p_phase = subparsers.add_parser("set-phase")
    p_phase.add_argument("project_id")
    p_phase.add_argument("phase")
    
    p_note = subparsers.add_parser("add-note")
    p_note.add_argument("project_id")
    p_note.add_argument("category", choices=["issue_resolved", "warning", "context"])
    p_note.add_argument("note")
    
    p_show = subparsers.add_parser("show")
    p_show.add_argument("project_id")
    
    args = parser.parse_args()
    
    if args.command == "compact":
        compact(args.project_id)
    elif args.command == "add-decision":
        add_decision(args.project_id, args.decision, args.status)
    elif args.command == "set-phase":
        set_phase(args.project_id, args.phase)
    elif args.command == "add-note":
        add_note(args.project_id, args.category, args.note)
    elif args.command == "show":
        show(args.project_id)
    else:
        parser.print_help()
