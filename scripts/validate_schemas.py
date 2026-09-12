#!/usr/bin/env python3
"""
فاحص العقود — Schema Validator
يفحص ملفات JSON لمشروع فيديو مقابل العقود المعرّفة في schemas/

الاستخدام:
    python scripts/validate_schemas.py <project_dir>

المخرج:
    ✅ أو ❌ لكل ملف مع تفاصيل الأخطاء
    Exit 0 = كل الملفات الموجودة سليمة
    Exit 1 = خطأ واحد على الأقل
"""

import json
import sys
import os
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft7Validator, RefResolver, ValidationError
except ImportError:
    print("❌ مكتبة jsonschema غير مثبتة. شغّل: pip install jsonschema")
    sys.exit(1)


# خريطة الملفات ← العقود
FILE_SCHEMA_MAP = {
    "project.json": "project.schema.json",
    "blueprint.json": "blueprint.schema.json",
    "brand.json": "brand.schema.json",
    "overrides.json": "overrides.schema.json",
    "manifest.json": "manifest.schema.json",
    "state.json": "state.schema.json",
}


def load_json(filepath: Path) -> dict:
    """يقرأ ملف JSON ويعيد المحتوى كقاموس."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_resolver(schemas_dir: Path) -> RefResolver:
    """
    يبني RefResolver لحل مراجع $ref العابرة للملفات.
    يستخدم base_uri = مجلد schemas/ كـ URI أساسي.
    """
    schema_store = {}
    for schema_file in schemas_dir.glob("*.schema.json"):
        schema = load_json(schema_file)
        schema_id = schema.get("$id", schema_file.name)
        schema_store[schema_id] = schema

    base_uri = schemas_dir.as_uri() + "/"
    # نستخدم مخطط فارغ كمرجع أساسي، والـ store يحتوي كل العقود
    resolver = RefResolver(base_uri, {}, store=schema_store)
    return resolver


def validate_file(
    filepath: Path,
    schema: dict,
    resolver: RefResolver,
) -> list[str]:
    """
    يفحص ملف JSON مقابل عقد معيّن.
    يعيد قائمة فارغة عند النجاح، أو قائمة رسائل خطأ.
    """
    try:
        data = load_json(filepath)
    except json.JSONDecodeError as e:
        return [f"خطأ في قراءة JSON: {e}"]

    validator = Draft7Validator(schema, resolver=resolver)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        json_path = " → ".join(str(p) for p in error.absolute_path) or "(الجذر)"
        errors.append(f"  [{json_path}] {error.message}")
    return errors


def main():
    if len(sys.argv) != 2:
        print("الاستخدام: python scripts/validate_schemas.py <project_dir>")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    if not project_dir.is_dir():
        print(f"❌ المجلد غير موجود: {project_dir}")
        sys.exit(1)

    # حدد مجلد العقود (schemas/) — بجانب scripts/ أو في الجذر
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent
    schemas_dir = workspace_root / "schemas"

    if not schemas_dir.is_dir():
        print(f"❌ مجلد العقود غير موجود: {schemas_dir}")
        sys.exit(1)

    resolver = build_resolver(schemas_dir)
    has_errors = False
    checked = 0
    skipped = 0

    for data_filename, schema_filename in FILE_SCHEMA_MAP.items():
        data_path = project_dir / data_filename
        schema_path = schemas_dir / schema_filename

        if not data_path.exists():
            print(f"⬜ {data_filename:<20s} — غير موجود (تخطّي)")
            skipped += 1
            continue

        schema = load_json(schema_path)
        errors = validate_file(data_path, schema, resolver)
        checked += 1

        if errors:
            has_errors = True
            print(f"❌ {data_filename:<20s} — {len(errors)} خطأ:")
            for err in errors:
                print(err)
        else:
            print(f"✅ {data_filename:<20s} — سليم")

    print(f"\n{'─' * 50}")
    print(f"النتيجة: {checked} فُحص | {skipped} تُخطّي | {'❌ فشل' if has_errors else '✅ نجاح'}")
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
