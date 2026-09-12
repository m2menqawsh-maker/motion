import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path
from jsonschema import validate

BASE_FIXTURE = Path("build/fixtures/prj_e2e")
SCRIPT_PATH = Path("scripts/gates/stage_gate.py")
SCHEMA_PATH = Path("schemas/state.schema.json")

def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def run_cmd(project_dir, *args):
    cmd = [sys.executable, str(SCRIPT_PATH), str(project_dir)] + list(args)
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return res.returncode, res.stdout, res.stderr

def assert_schema(project_dir):
    state = load_json(Path(project_dir) / "state.json")
    schema = load_json(SCHEMA_PATH)
    validate(instance=state, schema=schema)

def run_tests():
    passed = 0
    total = 12

    schema = load_json(SCHEMA_PATH)

    with tempfile.TemporaryDirectory() as tmpdir:
        def setup_fixture():
            dst = Path(tmpdir) / "prj"
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(BASE_FIXTURE, dst)
            return dst

        # Test 1: status
        p = setup_fixture()
        code, out, _ = run_cmd(p, "status")
        assert code == 0, "Test 1 Failed"
        assert "Stage 0: pending" in out
        assert_schema(p)
        print("✅ Test 1 Passed")
        passed += 1

        # Test 2: start 0 then finish 0
        p = setup_fixture()
        code, _, _ = run_cmd(p, "start", "0")
        assert code == 0, "Test 2 start Failed"
        code, _, _ = run_cmd(p, "finish", "0")
        assert code == 0, "Test 2 finish Failed"
        state = load_json(p / "state.json")
        assert state["stages"]["0"]["status"] == "done"
        assert state["gates"]["gate_1"]["status"] == "awaiting"
        assert_schema(p)
        print("✅ Test 2 Passed")
        passed += 1

        # Test 3: approve 1 without manifest
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        (p / "manifest.json").unlink()
        code, out, _ = run_cmd(p, "approve", "1", "TestBot")
        assert code != 0, "Test 3 Failed (should fail without manifest)"
        assert_schema(p)
        print("✅ Test 3 Passed")
        passed += 1

        # Test 4: approve 1 with full fixture
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        code, out, _ = run_cmd(p, "approve", "1", "TestBot")
        assert code == 0, f"Test 4 Failed: {out}"
        state = load_json(p / "state.json")
        assert state["gates"]["gate_1"]["status"] == "approved"
        assert state["gates"]["gate_1"]["approved_by"] == "TestBot"
        assert_schema(p)
        print("✅ Test 4 Passed")
        passed += 1

        # Test 5: start 1 before approve 1
        p = setup_fixture()
        code, out, _ = run_cmd(p, "start", "1")
        assert code != 0, "Test 5 Failed (should block start 1)"
        assert_schema(p)
        print("✅ Test 5 Passed")
        passed += 1

        # Test 6: start 1 after approve 1
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        run_cmd(p, "approve", "1", "TestBot")
        code, out, _ = run_cmd(p, "start", "1")
        assert code == 0, f"Test 6 Failed: {out}"
        state = load_json(p / "state.json")
        assert state["stages"]["1"]["status"] == "running"
        assert_schema(p)
        print("✅ Test 6 Passed")
        passed += 1

        # Test 7: approve 2 with unknown template
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        run_cmd(p, "approve", "1", "TestBot")
        run_cmd(p, "start", "1")
        run_cmd(p, "finish", "1")
        # mess up template
        bp = load_json(p / "blueprint.json")
        bp["scenes"][0]["template"] = "ghost-tpl"
        with open(p / "blueprint.json", "w") as f:
            json.dump(bp, f)
        code, out, _ = run_cmd(p, "approve", "2", "TestBot")
        assert code != 0, "Test 7 Failed (should fail unknown template)"
        assert_schema(p)
        print("✅ Test 7 Passed")
        passed += 1

        # Test 8: approve 2 valid
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        run_cmd(p, "approve", "1", "TestBot")
        run_cmd(p, "start", "1")
        run_cmd(p, "finish", "1")
        code, out, _ = run_cmd(p, "approve", "2", "TestBot")
        assert code == 0, f"Test 8 Failed: {out}"
        state = load_json(p / "state.json")
        assert state["gates"]["gate_2"]["status"] == "approved"
        assert_schema(p)
        print("✅ Test 8 Passed")
        passed += 1

        # Test 9: overlapping scenes
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        run_cmd(p, "approve", "1", "TestBot")
        run_cmd(p, "start", "1")
        run_cmd(p, "finish", "1")
        bp = load_json(p / "blueprint.json")
        bp["scenes"][1]["startFrame"] = 10 # Overlaps with scene 0 which is 0-60
        with open(p / "blueprint.json", "w") as f:
            json.dump(bp, f)
        code, out, _ = run_cmd(p, "approve", "2", "TestBot")
        assert code != 0, "Test 9 Failed (should fail overlap)"
        assert_schema(p)
        print("✅ Test 9 Passed")
        passed += 1

        # Test 10: reject 1 then approve 1
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        code, out, _ = run_cmd(p, "reject", "1", "TestBot", "Need fix")
        assert code == 0, f"Test 10 reject Failed: {out}"
        state = load_json(p / "state.json")
        assert state["gates"]["gate_1"]["status"] == "rejected"
        code, out, _ = run_cmd(p, "approve", "1", "TestBot")
        assert code == 0, f"Test 10 approve Failed: {out}"
        state = load_json(p / "state.json")
        assert state["gates"]["gate_1"]["status"] == "approved"
        assert_schema(p)
        print("✅ Test 10 Passed")
        passed += 1

        # Test 11: fail 1 sets last_error
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        run_cmd(p, "approve", "1", "TestBot")
        run_cmd(p, "start", "1")
        code, out, _ = run_cmd(p, "fail", "1", "Crash")
        assert code == 0, f"Test 11 fail Failed: {out}"
        state = load_json(p / "state.json")
        assert state["stages"]["1"]["status"] == "failed"
        assert state["last_error"] == "Crash"
        # can we start 2? no gate 2 is not approved
        code, _, _ = run_cmd(p, "start", "2")
        assert code != 0
        assert_schema(p)
        print("✅ Test 11 Passed")
        passed += 1

        # Test 12: all state.json modifications pass schema validation (implicitly checked in all tests via assert_schema)
        # We will do one full run through
        p = setup_fixture()
        run_cmd(p, "start", "0")
        run_cmd(p, "finish", "0")
        run_cmd(p, "approve", "1", "User")
        run_cmd(p, "start", "1")
        run_cmd(p, "finish", "1")
        run_cmd(p, "approve", "2", "User")
        run_cmd(p, "start", "2")
        run_cmd(p, "finish", "2")
        code, out, _ = run_cmd(p, "approve", "3", "User")
        assert code == 0, f"Test 12 approve 3 Failed: {out}"
        run_cmd(p, "start", "3")
        assert_schema(p)
        print("✅ Test 12 Passed")
        passed += 1

    print(f"\n✅ All {passed}/{total} tests passed!")

if __name__ == "__main__":
    run_tests()
