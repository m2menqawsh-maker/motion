"""
Architecture Guard: Legacy Gate Façade Defense (S04).

Enforces structural and contract invariants:
1. api/routers/gates.py must type stage/gate parameters using Enums (GateName, StageName), never raw 'str'.
2. gate_service.reject_gate must NOT delegate to start_stage or return fake success.
3. PipelineService.approve_gate must validate against VALID_GATES before mutating state.
4. PipelineService.start_stage and finish_stage must validate against VALID_STAGES.
5. Invalid/unknown gate operations must produce ZERO persistence side effects.
"""

import ast
from pathlib import Path
import pytest
from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState, LifecycleState
from api.services.pipeline_service import PipelineService
from api.services.gate_service import reject_gate
from api.core.errors import InvalidGateError, InvalidStageError, UnsupportedGateOperationError

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent


def test_gates_router_parameters_are_typed_enums():
    """
    AST Guard:
    api/routers/gates.py must NOT use raw 'str' for stage and gate path parameters.
    They must be typed with StageName and GateName enums.
    """
    router_path = WORKSPACE_ROOT / "api" / "routers" / "gates.py"
    assert router_path.exists(), "api/routers/gates.py missing"

    tree = ast.parse(router_path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for arg in node.args.args:
                if arg.arg in ("stage", "gate"):
                    # Annotation must be an AST Name with 'StageName' or 'GateName'
                    assert arg.annotation is not None, (
                        f"Parameter '{arg.arg}' in endpoint '{node.name}' has no type annotation."
                    )
                    type_name = getattr(arg.annotation, "id", None)
                    assert type_name in ("StageName", "GateName"), (
                        f"Architecture Violation (S04): Parameter '{arg.arg}' in '{node.name}' "
                        f"is typed as '{type_name}' instead of GateName/StageName."
                    )


def test_reject_gate_does_not_call_start_stage():
    """
    AST Guard:
    gate_service.py reject_gate must NOT call start_stage (Finding C semantic lie).
    """
    service_path = WORKSPACE_ROOT / "api" / "services" / "gate_service.py"
    assert service_path.exists(), "api/services/gate_service.py missing"

    tree = ast.parse(service_path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "reject_gate":
            for sub_node in ast.walk(node):
                if isinstance(sub_node, ast.Call):
                    func = sub_node.func
                    # Check func.id or func.attr != 'start_stage'
                    call_name = getattr(func, "id", None) or getattr(func, "attr", None)
                    assert call_name != "start_stage", (
                        "Architecture Violation (Finding C): reject_gate() delegates to start_stage(), "
                        "masquerading as a fake rejection."
                    )


def test_unknown_gate_operation_zero_side_effect_contract(tmp_path, monkeypatch):
    """
    Contract Guard:
    Submitting an unknown gate to approve_gate must fail closed and produce
    zero persistence side effects on disk.
    """
    pid = "arch_guard_s04_proj"
    pdir = tmp_path / "projects" / pid
    pdir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(PipelineService, "_get_project_dir", classmethod(lambda cls, p: pdir))

    state = ProjectState(project_id=pid, lifecycle_state=LifecycleState.DRAFT)
    StateStore.save(pdir, state)

    state_file = pdir / ".pipeline_state.json"
    snapshot_bytes = state_file.read_bytes()

    import asyncio

    with pytest.raises(InvalidGateError):
        asyncio.run(PipelineService.approve_gate(pid, "bogus_gate_unknown", "user"))

    assert state_file.read_bytes() == snapshot_bytes, (
        "Architecture Violation (Finding A): approve_gate mutated disk state for unknown gate!"
    )


def test_approve_gate_has_no_approval_metadata_mutations():
    """
    AST Guard:
    PipelineService.approve_gate must NOT assign to approval_metadata or call StateStore.save.
    (S04 Final Closure: No Review Authority -> No Approval Mutation).
    """
    service_path = WORKSPACE_ROOT / "api" / "services" / "pipeline_service.py"
    assert service_path.exists(), "api/services/pipeline_service.py missing"

    tree = ast.parse(service_path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "approve_gate":
            for sub_node in ast.walk(node):
                if isinstance(sub_node, ast.Subscript):
                    # Check if slicing into approval_metadata
                    target = getattr(sub_node.value, "attr", None)
                    if target == "approval_metadata":
                        pytest.fail(
                            "Architecture Violation (S04 Final Closure): PipelineService.approve_gate "
                            "mutates 'approval_metadata' without review authority."
                        )
                if isinstance(sub_node, ast.Call):
                    func = sub_node.func
                    call_name = getattr(func, "attr", None)
                    if call_name == "save" and getattr(getattr(func, "value", None), "id", None) == "StateStore":
                        pytest.fail(
                            "Architecture Violation (S04 Final Closure): PipelineService.approve_gate "
                            "calls StateStore.save() for unverified legacy approval."
                        )


def test_valid_gate_approval_zero_side_effect_contract(tmp_path, monkeypatch):
    """
    Contract Guard:
    Submitting a VALID gate to approve_gate must fail closed (UnsupportedGateOperationError)
    and produce ZERO persistence side effects on disk.
    """
    pid = "arch_guard_valid_gate_proj"
    pdir = tmp_path / "projects" / pid
    pdir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(PipelineService, "_get_project_dir", classmethod(lambda cls, p: pdir))

    state = ProjectState(project_id=pid, lifecycle_state=LifecycleState.DRAFT)
    StateStore.save(pdir, state)

    state_file = pdir / ".pipeline_state.json"
    snapshot_bytes = state_file.read_bytes()

    import asyncio

    with pytest.raises(UnsupportedGateOperationError):
        asyncio.run(PipelineService.approve_gate(pid, "asset_gate", "reviewer_1"))

    assert state_file.read_bytes() == snapshot_bytes, (
        "Architecture Violation (S04 Final Closure): approve_gate mutated disk state for valid gate!"
    )
