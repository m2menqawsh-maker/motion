#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ⚠️ تحذير: هذا السكريبت يولّد الهيكل فقط.
# المحتوى الإبداعي يجب أن يكتبه الوكيل بنفسه.
# لا تستخدم هذا السكريبت لتوليد خطة كاملة.

import os
import sys
import json
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python generate_plan.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]
    project_dir = Path(f"projects/{project_id}")
    
    if not project_dir.exists():
        print(f"❌ المشروع {project_id} غير موجود.")
        sys.exit(1)
        
    skeleton_path = project_dir / "plan_skeleton.md"
    
    # محاولة قراءة التوقيتات لاستخراج بعض المعلومات الأساسية
    timings_path = project_dir / "04_timings.json"
    total_duration = "[يملأه الوكيل من 04_timings.json]"
    num_scenes = "[يملأه الوكيل]"
    
    if timings_path.exists():
        try:
            timings = json.loads(timings_path.read_text(encoding="utf-8"))
            if "total_duration" in timings:
                total_duration = f"{timings['total_duration']} ثانية"
            if "scenes" in timings:
                num_scenes = f"{len(timings['scenes'])} مشاهد"
        except Exception:
            pass

    skeleton_content = f"""# 📋 خطة الفيديو التفصيلية

## القسم 1: الهوية والمعلومات الأساسية
- المشروع: {project_id}
- العنوان: [يملأه الوكيل]
- المدة الكلية: {total_duration}
- عدد المشاهد: {num_scenes}

## القسم 2: الهوية البصرية والصوتية
[يملأه الوكيل بالكامل بناءً على مراجع التصميم والشخصية الحركية]

## القسم 3: جدول المشاهد التفصيلي
[يملأه الوكيل - مشهد بمشهد، لقطة بلقطة، مع جداول التوقيت الدقيقة واختيار القوالب والـ SFX]

## القسم 4: الانتقالات والبنية الزمنية
[يملأه الوكيل]

## القسم 5: قائمة القوالب المعتمدة
[يملأه الوكيل]

## القسم 6: حزمة الميديا النهائية
[يملأه الوكيل]

## القسم 7: بوابات الجودة والموافقات
[يملأه الوكيل]

## القسم 8: ملاحظات ومخاطر
[يملأه الوكيل]
"""

    skeleton_path.write_text(skeleton_content, encoding="utf-8")
    print(f"✅ تم توليد هيكل الخطة بنجاح في: {skeleton_path}")
    print("⚠️ يجب على الوكيل الآن ملء الهيكل بالمحتوى الإبداعي وحفظه كـ master_plan.md")

if __name__ == "__main__":
    main()
