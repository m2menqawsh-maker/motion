#!/usr/bin/env python3
"""
اختبارات العقود — Schema Tests
يفحص 6 حالات اختبار (fixtures داخل الذاكرة) لضمان صحة العقود وصرامتها.

الاستخدام:
    python scripts/test_schemas.py

المخرج:
    PASS/FAIL لكل حالة + ملخص نهائي
    Exit 0 = 6/6 PASS
    Exit 1 = أي FAIL
"""

import json
import sys
import copy
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft7Validator, RefResolver
except ImportError:
    print("❌ مكتبة jsonschema غير مثبتة. شغّل: pip install jsonschema")
    sys.exit(1)


def load_json(filepath: Path) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_resolver(schemas_dir: Path) -> RefResolver:
    schema_store = {}
    for schema_file in schemas_dir.glob("*.schema.json"):
        schema = load_json(schema_file)
        schema_id = schema.get("$id", schema_file.name)
        schema_store[schema_id] = schema

    base_uri = schemas_dir.as_uri() + "/"
    resolver = RefResolver(base_uri, {}, store=schema_store)
    return resolver


def validate(schema: dict, data: dict, resolver: RefResolver) -> list[str]:
    validator = Draft7Validator(schema, resolver=resolver)
    return [e.message for e in validator.iter_errors(data)]


# ──────────────────────────────────────────────
# بيانات العينات السليمة (تُنسخ وتُعدَّل لحالات الفشل)
# ──────────────────────────────────────────────

VALID_PROJECT = {
    "project_id": "prj_test-01",
    "name": "مشروع اختباري",
    "aspect": "9:16",
    "fps": 30,
    "language": "ar",
    "brand": None,
    "created_at": "2026-09-06T12:00:00+03:00",
    "voiceover": {
        "mode": "upload",
        "file": "assets/incoming/vo.wav",
        "voice_id": None,
    },
}

VALID_BLUEPRINT = {
    "project_id": "prj_test-01",
    "version": 1,
    "fps": 30,
    "scenes": [
        {
            "scene_id": "scene_01",
            "template": "text-reveal",
            "startFrame": 0,
            "durationFrames": 90,
            "props": {
                "text": "اختبار",
                "fontSize": 48,
                "fontFamily": "Cairo",
                "color": "#00F5FF",
                "animation": "fade_in",
                "speed": 1,
                "delay": 0,
                "position": {"anchor": "center"},
                "styleOverride": {
                    "borderRadius": "8px",
                },
            },
        }
    ],
}

VALID_BRAND = {
    "brandName": "Test Brand",
    "logoSrc": "assets/ready/logo.svg",
    "colors": {
        "primary": "#00F5FF",
        "accent": "#FFD700",
        "background": "#0A0E27",
        "text": "#FFFFFF",
    },
    "fonts": {"display": "Cairo", "body": "Inter"},
}

VALID_OVERRIDES = {
    "project_id": "prj_test-01",
    "scenes": [
        {
            "scene_id": "scene_01",
            "props": {"fontSize": 64, "color": "#FF0000"},
            "timing": {"startFrame": 10, "durationFrames": 80},
        }
    ],
}

VALID_MANIFEST = {
    "project_id": "prj_test-01",
    "generated_at": "2026-09-06T12:00:00+03:00",
    "assets": [
        {
            "asset_id": "ast_img-01",
            "type": "image",
            "path": "assets/ready/bg.png",
            "source": "ready",
            "approved": True,
        }
    ],
}

VALID_STATE = {
    "project_id": "prj_test-01",
    "current_stage": 0,
    "last_error": None,
    "stages": {
        "0": {"status": "running", "started_at": "2026-09-06T12:00:00Z", "finished_at": None},
        "1": {"status": "pending", "started_at": None, "finished_at": None},
        "2": {"status": "pending", "started_at": None, "finished_at": None},
        "3": {"status": "pending", "started_at": None, "finished_at": None},
    },
    "gates": {
        "gate_1": {"status": "locked", "approved_by": None, "approved_at": None, "note": None},
        "gate_2": {"status": "locked", "approved_by": None, "approved_at": None, "note": None},
        "gate_3": {"status": "locked", "approved_by": None, "approved_at": None, "note": None},
    },
    "updated_at": "2026-09-06T12:00:00Z",
}


def main():
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent
    schemas_dir = workspace_root / "schemas"

    if not schemas_dir.is_dir():
        print(f"❌ مجلد العقود غير موجود: {schemas_dir}")
        sys.exit(1)

    resolver = build_resolver(schemas_dir)

    project_schema = load_json(schemas_dir / "project.schema.json")
    blueprint_schema = load_json(schemas_dir / "blueprint.schema.json")
    brand_schema = load_json(schemas_dir / "brand.schema.json")
    overrides_schema = load_json(schemas_dir / "overrides.schema.json")
    manifest_schema = load_json(schemas_dir / "manifest.schema.json")
    state_schema = load_json(schemas_dir / "state.schema.json")

    results = []

    # ──────────────────────────────────────────────
    # اختبار 1: عينة سليمة كاملة تمر
    # ──────────────────────────────────────────────
    test_name = "1. عينة سليمة كاملة تمرّ بنجاح"
    all_valid = True
    for label, schema, data in [
        ("project", project_schema, VALID_PROJECT),
        ("blueprint", blueprint_schema, VALID_BLUEPRINT),
        ("brand", brand_schema, VALID_BRAND),
        ("overrides", overrides_schema, VALID_OVERRIDES),
        ("manifest", manifest_schema, VALID_MANIFEST),
        ("state", state_schema, VALID_STATE),
    ]:
        errs = validate(schema, data, resolver)
        if errs:
            all_valid = False
            print(f"    ✗ {label}: {errs}")
    results.append((test_name, all_valid))

    # ──────────────────────────────────────────────
    # اختبار 2: لون "#ZZZ999" يُرفض
    # ──────────────────────────────────────────────
    test_name = '2. لون "#ZZZ999" يُرفض'
    bad_color = copy.deepcopy(VALID_BLUEPRINT)
    bad_color["scenes"][0]["props"]["color"] = "#ZZZ999"
    errs = validate(blueprint_schema, bad_color, resolver)
    results.append((test_name, len(errs) > 0))

    # ──────────────────────────────────────────────
    # اختبار 3: styleOverride بمفتاح zIndex يُرفض
    # ──────────────────────────────────────────────
    test_name = "3. styleOverride بمفتاح zIndex يُرفض"
    bad_override = copy.deepcopy(VALID_BLUEPRINT)
    bad_override["scenes"][0]["props"]["styleOverride"]["zIndex"] = 10
    errs = validate(blueprint_schema, bad_override, resolver)
    results.append((test_name, len(errs) > 0))

    # ──────────────────────────────────────────────
    # اختبار 4: voiceover mode=upload بدون file يُرفض
    # ──────────────────────────────────────────────
    test_name = "4. voiceover mode=upload بدون file يُرفض"
    bad_vo = copy.deepcopy(VALID_PROJECT)
    bad_vo["voiceover"] = {"mode": "upload", "file": None, "voice_id": None}
    errs = validate(project_schema, bad_vo, resolver)
    results.append((test_name, len(errs) > 0))

    # ──────────────────────────────────────────────
    # اختبار 5: template بقيمة "Text_Reveal!" يُرفض
    # ──────────────────────────────────────────────
    test_name = '5. template بقيمة "Text_Reveal!" يُرفض'
    bad_template = copy.deepcopy(VALID_BLUEPRINT)
    bad_template["scenes"][0]["template"] = "Text_Reveal!"
    errs = validate(blueprint_schema, bad_template, resolver)
    results.append((test_name, len(errs) > 0))

    # ──────────────────────────────────────────────
    # اختبار 6: gate بحالة "maybe" يُرفض
    # ──────────────────────────────────────────────
    test_name = '6. gate بحالة "maybe" يُرفض'
    bad_gate = copy.deepcopy(VALID_STATE)
    bad_gate["gates"]["gate_1"]["status"] = "maybe"
    errs = validate(state_schema, bad_gate, resolver)
    results.append((test_name, len(errs) > 0))

    # ──────────────────────────────────────────────
    # اختبار 7: scene بـ content.numbers يمر
    # ──────────────────────────────────────────────
    test_name = "7. scene بـ content.numbers يمر"
    good_content = copy.deepcopy(VALID_BLUEPRINT)
    good_content["scenes"][0]["content"] = {"numbers": [1, 2, 3]}
    errs = validate(blueprint_schema, good_content, resolver)
    results.append((test_name, len(errs) == 0))

    # ──────────────────────────────────────────────
    # اختبار 8: scene بـ content حقل غريب يُرفض
    # ──────────────────────────────────────────────
    test_name = "8. scene بـ content حقل غريب يُرفض"
    bad_content = copy.deepcopy(VALID_BLUEPRINT)
    bad_content["scenes"][0]["content"] = {"invalid_field": True}
    errs = validate(blueprint_schema, bad_content, resolver)
    results.append((test_name, len(errs) > 0))

    # ──────────────────────────────────────────────
    # اختبار 9: scene بـ effects مقبول
    # ──────────────────────────────────────────────
    test_name = "9. scene بـ effects مقبول"
    good_effects = copy.deepcopy(VALID_BLUEPRINT)
    good_effects["scenes"][0]["effects"] = [
        {"effect": "camera-shake", "params": {"intensity": 5}, "apply": "scene"}
    ]
    errs = validate(blueprint_schema, good_effects, resolver)
    results.append((test_name, len(errs) == 0))

    # ──────────────────────────────────────────────
    # اختبار 10: شكل effect مجهول يُرفض
    # ──────────────────────────────────────────────
    test_name = "10. شكل effect مجهول يُرفض"
    bad_effects = copy.deepcopy(VALID_BLUEPRINT)
    bad_effects["scenes"][0]["effects"] = [
        {"effect": 123, "params": {}}
    ]
    errs = validate(blueprint_schema, bad_effects, resolver)
    results.append((test_name, len(errs) > 0))

    # ──────────────────────────────────────────────
    # ملخص النتائج
    # ──────────────────────────────────────────────
    print("=" * 55)
    print("  اختبارات العقود — Schema Contract Tests")
    print("=" * 55)
    passed = 0
    for name, ok in results:
        status = "PASS ✅" if ok else "FAIL ❌"
        print(f"  {status}  {name}")
        if ok:
            passed += 1
    total = len(results)
    print("─" * 55)
    print(f"  النتيجة: {passed}/{total} {'— نجاح كامل ✅' if passed == total else '— يوجد فشل ❌'}")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
