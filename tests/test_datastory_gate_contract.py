# -*- coding: utf-8 -*-
"""tests/test_datastory_gate_contract.py

Permanent contract tests for Datastorywrapper in code_template_gate.py.
Verifies:
1. Datastorywrapper without template_props passes gate (allowed omission, runtime default).
2. Datastorywrapper with valid template_props (barData, metrics, steps) passes gate.
3. Datastorywrapper with explicit empty arrays [] passes gate.
4. Datastorywrapper with malformed barData (string, null, invalid elements) is rejected.
5. Datastorywrapper with malformed metrics is rejected.
6. Datastorywrapper with malformed steps is rejected.
"""
import json
import pytest
from pathlib import Path
import tempfile
from scripts.code_template_gate import run_gate


def create_mock_project(tmp_path: Path, scene_template_props=None) -> Path:
    proj_dir = tmp_path / "prj_test"
    proj_dir.mkdir(parents=True, exist_ok=True)
    
    scene = {
        "scene_id": "scene_1",
        "template": "Datastorywrapper",
        "startFrame": 0,
        "durationFrames": 150,
        "surface": {
            "text": "Data Analysis",
            "primaryColor": "#00F0FF",
        },
        "content": {
            "lines": ["Line 1", "Line 2"],
            "text": "Data Analysis Text"
        }
    }
    if scene_template_props is not None:
        scene["template_props"] = scene_template_props

    bp = {
        "project_id": "prj_test",
                "scenes": [scene]
    }
    
    (proj_dir / "05_blueprint.json").write_text(json.dumps(bp, ensure_ascii=False), encoding="utf-8")
    return proj_dir


def test_datastory_omitted_props_passes(tmp_path):
    # Omitted template_props is valid (falls back to runtime canonical defaults)
    proj_dir = create_mock_project(tmp_path, scene_template_props=None)
    # Should not raise SystemExit
    run_gate(str(proj_dir))


def test_datastory_valid_props_passes(tmp_path):
    valid_props = {
        "barData": [
            {"label": "Q1", "value": 40},
            {"label": "Q2", "value": 65}
        ],
        "metrics": [
            {"label": "Throughput", "value": 120}
        ],
        "steps": [
            {"title": "Step 1", "description": "First step"}
        ]
    }
    proj_dir = create_mock_project(tmp_path, scene_template_props=valid_props)
    run_gate(str(proj_dir))


def test_datastory_empty_array_props_passes(tmp_path):
    # Explicit empty arrays [] are preserved and allowed
    empty_props = {
        "barData": [],
        "metrics": [],
        "steps": []
    }
    proj_dir = create_mock_project(tmp_path, scene_template_props=empty_props)
    run_gate(str(proj_dir))


def test_datastory_malformed_bardata_rejected(tmp_path):
    # String barData
    proj_str = create_mock_project(tmp_path / "str", scene_template_props={"barData": "invalid"})
    with pytest.raises(SystemExit) as exc:
        run_gate(str(proj_str))
    assert exc.value.code == 1

    # Null barData
    proj_null = create_mock_project(tmp_path / "null", scene_template_props={"barData": None})
    with pytest.raises(SystemExit) as exc:
        run_gate(str(proj_null))
    assert exc.value.code == 1

    # Invalid item
    proj_bad_item = create_mock_project(tmp_path / "bad_item", scene_template_props={"barData": [{"label": "Q1", "value": "not_a_number"}]})
    with pytest.raises(SystemExit) as exc:
        run_gate(str(proj_bad_item))
    assert exc.value.code == 1


def test_datastory_malformed_metrics_rejected(tmp_path):
    proj_str = create_mock_project(tmp_path / "str_m", scene_template_props={"metrics": "not_an_array"})
    with pytest.raises(SystemExit) as exc:
        run_gate(str(proj_str))
    assert exc.value.code == 1

    proj_null = create_mock_project(tmp_path / "null_m", scene_template_props={"metrics": None})
    with pytest.raises(SystemExit) as exc:
        run_gate(str(proj_null))
    assert exc.value.code == 1


def test_datastory_malformed_steps_rejected(tmp_path):
    proj_bad = create_mock_project(tmp_path / "bad_s", scene_template_props={"steps": [{"description": "missing title"}]})
    with pytest.raises(SystemExit) as exc:
        run_gate(str(proj_bad))
    assert exc.value.code == 1
