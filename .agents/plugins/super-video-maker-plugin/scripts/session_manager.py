import os
import sys
from utils.logger import UnifiedLogger
log = UnifiedLogger("session_manager")

import json
import argparse
import shutil
import subprocess

sys.stdout.reconfigure(encoding="utf-8")

PROJECTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../projects"))
SCRIPTS_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "../templates")

def get_project_dir(project_id):
    return os.path.join(PROJECTS_DIR, project_id)

def get_state_file(project_id):
    return os.path.join(get_project_dir(project_id), ".session_state.json")

def get_digest_file(project_id):
    return os.path.join(get_project_dir(project_id), "session_digest.md")

def run_compactor(project_id):
    compactor_path = os.path.join(SCRIPTS_DIR, "context_compactor.py")
    subprocess.run([sys.executable, compactor_path, "compact", project_id], check=True)

def save_state(project_id):
    state_file = get_state_file(project_id)
    if not os.path.exists(state_file):
        log.info(f"جاري إنشاء حالة جديدة للمشروع {project_id}...")
    
    # compactor creates or updates the state
    try:
        run_compactor(project_id)
        log.info(f"تم حفظ حالة المشروع {project_id} بنجاح.")
    except Exception as e:
        log.info(f"حدث خطأ أثناء حفظ الحالة: {e}")

def restore_state(project_id):
    state_file = get_state_file(project_id)
    if os.path.exists(state_file):
        log.info(f"تم استعادة حالة المشروع {project_id}. يمكنك الآن المتابعة.")
    else:
        log.info(f"لا توجد حالة محفوظة للمشروع {project_id}.")

def list_projects():
    if not os.path.exists(PROJECTS_DIR):
        log.info("مجلد المشاريع غير موجود.")
        return
        
    projects_with_state = []
    for d in os.listdir(PROJECTS_DIR):
        proj_dir = os.path.join(PROJECTS_DIR, d)
        if os.path.isdir(proj_dir):
            if os.path.exists(os.path.join(proj_dir, ".session_state.json")):
                projects_with_state.append(d)
                
    if not projects_with_state:
        log.info("لا توجد مشاريع لها حالات محفوظة.")
    else:
        log.info("المشاريع التي لها حالات محفوظة:")
        for p in projects_with_state:
            log.info(f"- {p}")

def get_current_session_id():
    brain_dir = r"C:\Users\momen\.gemini\antigravity-ide\brain"
    if not os.path.exists(brain_dir):
        return None
    subdirs = [os.path.join(brain_dir, d) for d in os.listdir(brain_dir) if os.path.isdir(os.path.join(brain_dir, d))]
    if not subdirs:
        return None
    latest_subdir = max(subdirs, key=os.path.getmtime)
    return os.path.basename(latest_subdir)

def generate_resume_brief(project_id):
    state_file = get_state_file(project_id)
    digest_file = get_digest_file(project_id)
    
    if not os.path.exists(state_file) or not os.path.exists(digest_file):
        log.info(f"البيانات غير مكتملة للمشروع {project_id}. جاري توليدها...")
        try:
            run_compactor(project_id)
        except Exception as e:
            log.info(f"فشل في إيجاد أو إنشاء حالة المشروع {project_id}: {e}")
            return
            
    if not os.path.exists(state_file):
        log.info(f"فشل في إيجاد أو إنشاء حالة المشروع {project_id}.")
        return

    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception as e:
        log.info(f"حدث خطأ أثناء قراءة ملف الحالة: {e}")
        return
        
    current_phase = state.get('current_phase', 'غير محددة')
    
    # تنظيف السجل التلقائي للجلسة الجديدة
    session_id = get_current_session_id()
    if session_id:
        cleaner_path = os.path.join(SCRIPTS_DIR, "transcript_cleaner.py")
        try:
            # We use --force if we want to bypass, but requirements say "منع التنظيف إذا تم خلال آخر 30 دقيقة"
            # cleaner script already handles the 30-minute block check!
            subprocess.run([sys.executable, cleaner_path, "clean", session_id], check=True)
            from datetime import datetime, timezone
            state['transcript_cleaned_at'] = datetime.now(timezone.utc).isoformat()
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            log.info(f"ملاحظة: تعذر تنظيف السجل تلقائياً: {e}")

    # Suggest next step based on current phase
    next_step = ""
    if current_phase in ["not_started", "غير محددة"]:
        next_step = "يرجى البدء بتحديد الخطة (المرحلة 1: جلب الميديا ومعالجتها)."
    elif "plan" in current_phase.lower() or "تخطيط" in current_phase:
        next_step = "يرجى بناء الخطة التفصيلية (المرحلة 2) مشهداً بمشهد."
    elif "build" in current_phase.lower() or "بناء" in current_phase:
        next_step = "يرجى كتابة الكود البرمجي للمشاهد في مجلد البناء (المرحلة 3)."
    elif "render" in current_phase.lower() or "رندر" in current_phase:
        next_step = "يرجى مراجعة الفيديو النهائي وإجراء الرندر."
    else:
        next_step = f"متابعة العمل على مرحلة {current_phase}."

    template_file = os.path.join(TEMPLATES_DIR, "resume_prompt.md")
    if os.path.exists(template_file):
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
            
        brief_content = template_content.replace("<project_id>", project_id)
        brief_content = brief_content.replace("<id>", project_id)
        brief_content = brief_content.replace("<current_phase>", current_phase)
        brief_content = brief_content.replace("<نص ديناميكي بناءً على المرحلة الحالية>", next_step)
    else:
        # Fallback if template is not found
        brief_content = f"# استئناف مشروع: {project_id}\n\n"
        brief_content += "## السياق المحفوظ\nاقرأ الملفات التالية بالترتيب لاستعادة الحالة الكاملة:\n"
        brief_content += f"1. `projects/{project_id}/session_digest.md`\n"
        brief_content += f"2. `projects/{project_id}/.session_state.json`\n"
        brief_content += f"3. `projects/{project_id}/master_plan.md` (إن وجد)\n"
        brief_content += f"4. `projects/{project_id}/04_timings.json`\n\n"
        brief_content += f"## القواعد الإلزامية\n- لا تقترح أي قرار موجود في \"القرارات المرفوضة\"\n- اتبع جميع \"القرارات المعتمدة\"\n- ابدأ من المرحلة: {current_phase}\n- اقرأ `.agent_alerts.md` قبل أي خطوة\n\n"
        brief_content += f"## الخطوة التالية المقترحة\n{next_step}\n\n"
        brief_content += "ابدأ بتأكيد فهمك للحالة في 2-3 جمل قبل المتابعة.\n"

    brief_file = os.path.join(get_project_dir(project_id), "resume_brief.md")
    os.makedirs(os.path.dirname(brief_file), exist_ok=True)
    with open(brief_file, 'w', encoding='utf-8') as f:
        f.write(brief_content)
        
    log.info(f"تم إنشاء حزمة الاستئناف في: {brief_file}")
    log.info("يرجى قراءة الملف ولصق البرومبت في المحادثة الجديدة.")

def export_state(project_id):
    state_file = get_state_file(project_id)
    if os.path.exists(state_file):
        export_file = os.path.join(get_project_dir(project_id), f"exported_state_{project_id}.json")
        shutil.copy2(state_file, export_file)
        log.info(f"تم تصدير الحالة إلى: {export_file}")
    else:
        log.info(f"لا توجد حالة محفوظة للمشروع {project_id} لتصديرها.")

def delete_state(project_id):
    state_file = get_state_file(project_id)
    digest_file = get_digest_file(project_id)
    deleted = False
    
    if os.path.exists(state_file):
        os.remove(state_file)
        deleted = True
    
    if os.path.exists(digest_file):
        os.remove(digest_file)
        deleted = True
        
    if deleted:
        log.info(f"تم حذف حالة المشروع {project_id} بنجاح.")
    else:
        log.info(f"لم يتم العثور على حالة محفوظة للمشروع {project_id}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    p_save = subparsers.add_parser("save")
    p_save.add_argument("project_id")
    
    p_restore = subparsers.add_parser("restore")
    p_restore.add_argument("project_id")
    
    p_list = subparsers.add_parser("list")
    
    p_resume = subparsers.add_parser("resume")
    p_resume.add_argument("project_id")
    
    p_export = subparsers.add_parser("export")
    p_export.add_argument("project_id")
    
    p_delete = subparsers.add_parser("delete")
    p_delete.add_argument("project_id")
    
    args = parser.parse_args()
    
    if args.command == "save":
        save_state(args.project_id)
    elif args.command == "restore":
        restore_state(args.project_id)
    elif args.command == "list":
        list_projects()
    elif args.command == "resume":
        generate_resume_brief(args.project_id)
    elif args.command == "export":
        export_state(args.project_id)
    elif args.command == "delete":
        delete_state(args.project_id)
    else:
        parser.print_help()
