"""
tests/ai/contracts/test_no_dict_any.py
======================================
Architectural guard verifying that no business boundary contract in `ai/contracts/`
uses unrestricted `dict[str, Any]`, `Dict[str, Any]`, or `Any` as a field type annotation.

Invariants:
- All structured dictionaries must use typed schemas or `JsonValue` (from pydantic).
- Prevents untyped escape hatches that obscure schema validation.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple

CONTRACTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ai" / "contracts"


def is_any_node(node: ast.AST) -> bool:
    """Checks if an AST annotation node is `Any`."""
    if isinstance(node, ast.Name) and node.id == "Any":
        return True
    if isinstance(node, ast.Attribute) and node.attr == "Any":
        return True
    return False


def is_dict_any_node(node: ast.AST) -> bool:
    """Checks if an AST annotation node is `Dict[..., Any]` or `dict[..., Any]`."""
    if isinstance(node, ast.Subscript):
        # Check if base is Dict or dict
        is_dict = False
        if isinstance(node.value, ast.Name) and node.value.id in {"dict", "Dict"}:
            is_dict = True
        elif isinstance(node.value, ast.Attribute) and node.value.attr in {"dict", "Dict"}:
            is_dict = True

        if is_dict:
            slice_node = node.slice
            # In Python 3.9+, slice for Dict[K, V] is a Tuple node with (K, V)
            if isinstance(slice_node, ast.Tuple) and len(slice_node.elts) >= 2:
                val_arg = slice_node.elts[1]
                if is_any_node(val_arg):
                    return True
    return False


class TestNoDictAnyGate:

    def test_no_dict_any_in_contract_field_annotations(self):
        """Scans all Pydantic model classes in ai/contracts/ for forbidden Any or Dict[str, Any]."""
        py_files = list(CONTRACTS_DIR.glob("*.py"))
        assert len(py_files) >= 10, "Expected at least 10 contract modules in ai/contracts/"

        violations: List[Tuple[str, int, str, str]] = []

        for py_file in py_files:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class looks like a contract model
                    is_model = any(
                        (isinstance(base, ast.Name) and base.id in {"AIContractModel", "BaseModel"})
                        or (isinstance(base, ast.Attribute) and base.attr in {"AIContractModel", "BaseModel"})
                        for base in node.bases
                    )
                    if not is_model:
                        continue

                    # Scan annotated assignments within the class body
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign):
                            field_name = item.target.id if isinstance(item.target, ast.Name) else "<complex>"
                            ann = item.annotation

                            # Check 1: bare Any
                            if is_any_node(ann):
                                violations.append(
                                    (py_file.name, item.lineno, node.name, f"{field_name}: Any")
                                )

                            # Check 2: Dict[str, Any]
                            if is_dict_any_node(ann):
                                violations.append(
                                    (py_file.name, item.lineno, node.name, f"{field_name}: Dict[..., Any]")
                                )

        assert not violations, (
            f"Unrestricted Any / Dict[str, Any] boundary escapes found in ai/contracts/:\n"
            + "\n".join(f"  • {f}:{line} in {cls} -> {field}" for f, line, cls, field in violations)
            + "\nUse JsonValue or explicit contract schemas instead of arbitrary Any."
        )
