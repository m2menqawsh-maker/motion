import json
import copy
from pathlib import Path
import pytest
from jsonschema import Draft7Validator, RefResolver


def test_blueprint_schema_rejects_extraneous_keys():
    """
    REGRESSION TEST:
    A valid blueprint augmented with an unexpected root key ('evil_key')
    and an unexpected scene key ('evil_scene_key') must be rejected by
    Draft7Validator when validating against schemas/blueprint.schema.json.
    """
    schemas_dir = Path("schemas")
    schema_store = {}
    for schema_file in schemas_dir.glob("*.schema.json"):
        s = json.loads(schema_file.read_text(encoding="utf-8"))
        schema_store[s.get("$id", schema_file.name)] = s

    base_uri = schemas_dir.resolve().as_uri() + "/"
    resolver = RefResolver(base_uri, {}, store=schema_store)

    blueprint_schema = json.loads((schemas_dir / "blueprint.schema.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(blueprint_schema, resolver=resolver)

    # 1. Base minimal blueprint must be completely valid
    valid_bp = json.loads(Path("tests/fixtures/blueprint/valid_minimal_blueprint.json").read_text(encoding="utf-8"))
    baseline_errors = list(validator.iter_errors(valid_bp))
    assert baseline_errors == [], f"Baseline minimal blueprint failed validation: {baseline_errors}"

    # 2. Inject extraneous keys at root and scene level
    evil_bp = copy.deepcopy(valid_bp)
    evil_bp["evil_key"] = 1
    evil_bp["scenes"][0]["evil_scene_key"] = 1

    errors = list(validator.iter_errors(evil_bp))
    error_messages = [e.message for e in errors]
    error_paths = [list(e.path) for e in errors]

    # Both evil_key and evil_scene_key must trigger additionalProperties validation failures
    has_root_evil = any("evil_key" in msg for msg in error_messages)
    has_scene_evil = any("evil_scene_key" in msg for msg in error_messages)

    assert has_root_evil, (
        f"Expected schema to reject 'evil_key' at root with additionalProperties: false, "
        f"but got errors: {error_messages}"
    )
    assert has_scene_evil, (
        f"Expected schema to reject 'evil_scene_key' in scenes[0] with additionalProperties: false, "
        f"but got errors: {error_messages}"
    )
