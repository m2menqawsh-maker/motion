#!/usr/bin/env python3
"""
Promote Template — ترقية القالب من proposed/ إلى templates/
ينقل القالب المقترح ويحدث TEMPLATE_INDEX.md
"""

import sys
from utils.logger import UnifiedLogger
log = UnifiedLogger("promote_template")

import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

class TemplatePromoter:
    """مروّق القوالب — ينقل القوالب المقترحة إلى المعتمدة"""

    PLUGIN_ROOT = Path(".agents/plugins/super-video-maker-plugin")
    PROPOSED_DIR = PLUGIN_ROOT / "templates" / "proposed"
    TEMPLATES_DIR = PLUGIN_ROOT / "templates"
    TEMPLATE_INDEX = PLUGIN_ROOT / "ground-truth" / "TEMPLATE_INDEX.md"

    def __init__(self, proposal_id: str):
        self.proposal_id = proposal_id
        self.proposal_dir = self.PROPOSED_DIR / proposal_id

        if not self.proposal_dir.exists():
            raise ValueError(f"❌ الاقتراح غير موجود: {self.proposal_dir}")

    def promote(self):
        """يرقي القالب المقترح إلى معتمد"""
        log.info(f"🚀 [TemplatePromoter] ترقية القالب: {self.proposal_id}")

        # 1. قراءة proposal.json
        proposal_file = self.proposal_dir / "proposal.json"
        with open(proposal_file, 'r', encoding='utf-8') as f:
            proposal = json.load(f)

        # 2. تحديد المسار الهدف
        category = proposal["category"]
        category_dir = self.get_category_dir(category)
        target_dir = category_dir / self.proposal_id

        # 3. نسخ الملفات
        if target_dir.exists():
            log.info(f"️ القالب موجود بالفعل في {target_dir} — سيتم الكتابة فوقه")
            shutil.rmtree(target_dir)

        shutil.copytree(self.proposal_dir, target_dir)
        log.success(f"تم نسخ القالب إلى {target_dir}")

        # 4. تحديث TEMPLATE_INDEX.md
        self.update_template_index(proposal)
        log.success(f"تم تحديث {self.TEMPLATE_INDEX}")

        # 5. حذف الاقتراح الأصلي
        shutil.rmtree(self.proposal_dir)
        log.success(f"تم حذف الاقتراح الأصلي من {self.proposal_dir}")

        log.info(f"\n🎉 تم ترقية القالب بنجاح!")
        log.info(f"📁 الموقع: {target_dir}")
        log.info(f"الاسم: {proposal['name']}")
        log.info(f"🏷️ التصنيف: {category}")

    def get_category_dir(self, category: str) -> Path:
        """يحدد مجلد التصنيف"""
        category_map = {
            "Typography & Text": "elements/typography",
            "Code & Tech": "elements/code",
            "Data & Stats": "elements/data",
            "UI & Layouts": "elements/ui",
            "Motion Effects & Overlays": "elements/motion",
            "Transitions": "transitions",
            "Full Scenes & Hooks": "scenes",
            "Cinematic Engine Primitives": "engine/primitives",
        }

        if category not in category_map:
            raise ValueError(f"❌ تصنيف غير معروف: {category}")
            
        target = self.TEMPLATES_DIR / category_map[category]
        target.mkdir(parents=True, exist_ok=True)
        return target

    def update_template_index(self, proposal: dict):
        """يحدث TEMPLATE_INDEX.md بإضافة القالب الجديد"""
        if not self.TEMPLATE_INDEX.exists():
            log.info(f"️ {self.TEMPLATE_INDEX} غير موجود — سيتم إنشاؤه")
            content = "# TEMPLATE INDEX\n\n"
        else:
            content = self.TEMPLATE_INDEX.read_text(encoding='utf-8')

        # إضافة القالب الجديد
        new_entry = f"\n## {proposal['name']}\n"
        new_entry += f"- **المعرف:** `{proposal['proposal_id']}`\n"
        new_entry += f"- **التصنيف:** {proposal['category']}\n"
        new_entry += f"- **الوصف:** {proposal['description']}\n"
        new_entry += f"- **المؤلف:** {proposal['author']}\n"
        new_entry += f"- **التاريخ:** {proposal['date']}\n"
        new_entry += f"- **المشروع الأصلي:** {proposal['source_project']}\n"
        
        if "use_cases" in proposal:
            new_entry += f"- **حالات الاستخدام:** {', '.join(proposal['use_cases'])}\n"
        
        if "props" in proposal:
            new_entry += "- **الخصائص:**\n"
            for prop in proposal["props"]:
                required = "✓" if prop.get("required") else "✗"
                new_entry += f"  - `{prop['name']}` ({prop['type']}) [{required}]: {prop.get('description', '')}\n"

        new_entry += f"- **تمت الترقية:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"

        # إضافة في نهاية الملف
        content += new_entry
        self.TEMPLATE_INDEX.write_text(content, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description="ترقية القالب من proposed/ إلى templates/")
    parser.add_argument("proposal_id", help="معرف القالب المقترح")
    args = parser.parse_args()

    proposal_id = args.proposal_id
    promoter = TemplatePromoter(proposal_id)

    try:
        promoter.promote()
        sys.exit(0)
    except Exception as e:
        log.info(f"\n❌ {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
