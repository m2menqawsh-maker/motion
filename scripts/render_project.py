#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_project.py — سكريبت وسيط لرندر المشروع بأمان وفي المسار الصحيح
"""
import sys
from pathlib import Path

# Fix python path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.core.pipeline import UnifiedPipeline
from scripts.core.gates import GateViolation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python render_project.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]

    pipeline = UnifiedPipeline(project_id)
    print(f"✅ جاري التحقق من المشروع {project_id}...")
    try:
        result = pipeline.render()
        print(f"✅ نجاح الرندر! تم حفظ الفيديو في: {result.get('output')}")
    except GateViolation as e:
        print(f"\n{'='*60}")
        print(f"🛑 [GUARDIAN BLOCK] ممنوع الرندر!")
        print(f"{'='*60}")
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"❌ فشل الرندر: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
