# 💾 Session Management & Auto-Backup

## 1. Session Manager
مدير الجلسات يتيح حفظ واسترجاع حالة العمل المؤقتة في المشاريع المعقدة.
- **المسار:** `.agents/plugins/super-video-maker-plugin/scripts/session_manager.py`
- **آلية العمل:** يقوم بحفظ الـ State في ملف JSON مسماه `.session_state.json` في جذر مجلد المشروع.

يمكن استخدامه برمجياً كالتالي:
```python
from session_manager import save_state, restore_state
save_state("tech_world", {"current_stage": "blueprint", "approved": True})
```

## 2. Auto-Backup (النسخ الاحتياطي التلقائي)
لتجنب فقدان خطط العمل المعتمدة `01_plan.md` والتوقيتات `04_timings.json` عند تعديلها عن طريق الخطأ.
- يفضل وضع الاستدعاء `create_backup(project_id, stage_name)` قبل توليد أي بيانات جديدة.
- سيقوم بإنشاء مجلد داخل `projects/<id>/backups/` يحتوي على نسخة مطابقة بالوقت والتاريخ.
