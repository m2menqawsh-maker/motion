"""
ai/regression/trace_grader.py
=============================
Authoritative Trace Grading Engine for Creative Regression (S28-08B).

Invariants:
- Observes and evaluates traces against canonical TraceAssertions.
- Answers core architectural questions:
  * Did it choose the right Recipe?
  * Did it load required Skill?
  * Did it retrieve irrelevant Knowledge?
  * Did it choose compatible Template?
  * Did it execute REUSE before COMPOSE?
  * Did it jump to CREATE without evidence?
  * Did it use a forbidden Tool (e.g. TTS under SILENT)?
  * Did UserStyle override current request incorrectly?
- Zero runtime authority: purely observational, zero side-effects on production registries or state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from ai.contracts.creative.regression import (
    TraceAssertion,
    TraceAssertionResult,
    TraceAssertionType,
)

logger = logging.getLogger(__name__)


def _extract_field(obj: Any, field_path: str) -> Any:
    """Extracts a nested field value using dot notation from dict or object."""
    if not field_path:
        return obj

    parts = field_path.split(".")
    curr = obj
    for part in parts:
        if curr is None:
            return None
        if isinstance(curr, dict):
            curr = curr.get(part)
        elif hasattr(curr, part):
            curr = getattr(curr, part)
        else:
            return None
    return curr


def normalize_trace_records(trace: Any) -> List[Dict[str, Any]]:
    """
    Normalizes diverse trace structures (AITrace, list of spans, list of dicts)
    into a uniform list of structured event records.
    """
    if trace is None:
        return []

    # If AITrace object
    if hasattr(trace, "spans") or hasattr(trace, "events"):
        records: List[Dict[str, Any]] = []
        spans = getattr(trace, "spans", []) or []
        for s in spans:
            rec = {
                "name": getattr(s, "name", ""),
                "span_type": str(getattr(s, "span_type", "")),
                "started_at": getattr(s, "started_at", None),
                "ended_at": getattr(s, "ended_at", None),
                "duration_ms": getattr(s, "duration_ms", None),
                "status": getattr(s, "status", "SUCCESS"),
                "attributes": getattr(s, "attributes", {}) or {},
            }
            # Flatten top attributes for easy access
            for k, v in rec["attributes"].items():
                if k not in rec:
                    rec[k] = v
            records.append(rec)

        events = getattr(trace, "events", []) or []
        for e in events:
            rec = {
                "name": getattr(e, "event_name", getattr(e, "name", "")),
                "span_type": "EVENT",
                "timestamp": getattr(e, "timestamp", None),
                "attributes": getattr(e, "attributes", {}) or {},
            }
            for k, v in rec["attributes"].items():
                if k not in rec:
                    rec[k] = v
            records.append(rec)
        return records

    # If already a list
    if isinstance(trace, list):
        records = []
        for item in trace:
            if isinstance(item, dict):
                rec = dict(item)
                # If attributes exist, flatten them
                attrs = rec.get("attributes", {})
                if isinstance(attrs, dict):
                    for k, v in attrs.items():
                        if k not in rec:
                            rec[k] = v
                records.append(rec)
            elif hasattr(item, "__dict__"):
                rec = {}
                for k, v in item.__dict__.items():
                    if not k.startswith("_"):
                        rec[k] = v
                records.append(rec)
            else:
                records.append({"name": str(item), "value": item})
        return records

    if isinstance(trace, dict):
        return [dict(trace)]

    return [{"name": str(trace)}]


class CreativeTraceGrader:
    """
    Observational trace assertion evaluator.
    Evaluates execution traces without mutating production behavior.
    """

    def grade_assertion(
        self,
        assertion: TraceAssertion,
        normalized_records: List[Dict[str, Any]],
    ) -> TraceAssertionResult:
        """Evaluates a single TraceAssertion against normalized trace events."""
        atype = assertion.assertion_type
        target = assertion.target_event_or_span

        if atype == TraceAssertionType.EVENT_EXISTS:
            matching = [
                r for r in normalized_records
                if r.get("name") == target or r.get("event") == target
            ]
            if (assertion.field_path or assertion.expected_value is not None or assertion.allowed_values is not None) and matching:
                fpath = assertion.field_path or "selected_value"
                filtered = []
                for m in matching:
                    val = _extract_field(m, fpath)
                    if assertion.expected_value is not None:
                        if val == assertion.expected_value:
                            filtered.append(m)
                    elif assertion.allowed_values is not None:
                        if val in assertion.allowed_values:
                            filtered.append(m)
                    else:
                        filtered.append(m)
                matching = filtered

            count = len(matching)
            min_c = assertion.min_count if assertion.min_count is not None else 1
            max_c = assertion.max_count

            passed = count >= min_c and (max_c is None or count <= max_c)
            details = (
                f"Found {count} event(s) matching '{target}'. "
                + (f"Required at least {min_c}. " if not passed else "")
                + (assertion.description or "")
            )
            return TraceAssertionResult(
                assertion_type=atype.value if hasattr(atype, "value") else str(atype),
                target=target,
                passed=passed,
                details=details.strip(),
            )

        elif atype == TraceAssertionType.EVENT_ABSENT:
            matching = [
                r for r in normalized_records
                if r.get("name") == target or r.get("event") == target
            ]
            if (assertion.field_path or assertion.expected_value is not None or assertion.forbidden_values is not None) and matching:
                fpath = assertion.field_path or "selected_value"
                filtered = []
                for m in matching:
                    val = _extract_field(m, fpath)
                    if assertion.forbidden_values is not None:
                        if val in assertion.forbidden_values:
                            filtered.append(m)
                    elif assertion.expected_value is not None:
                        if val == assertion.expected_value:
                            filtered.append(m)
                    else:
                        filtered.append(m)
                matching = filtered

            passed = len(matching) == 0
            details = (
                f"Expected event '{target}' to be absent, found {len(matching)} occurrence(s). "
                + (assertion.description or "")
            )
            return TraceAssertionResult(
                assertion_type=atype.value if hasattr(atype, "value") else str(atype),
                target=target,
                passed=passed,
                details=details.strip(),
            )

        elif atype == TraceAssertionType.ORDERED_BEFORE:
            sec_target = assertion.secondary_target
            if not sec_target:
                return TraceAssertionResult(
                    assertion_type=str(atype),
                    target=target,
                    passed=False,
                    details=f"ORDERED_BEFORE requires secondary_target for '{target}'.",
                )

            idx_a: Optional[int] = None
            idx_b: Optional[int] = None

            for idx, r in enumerate(normalized_records):
                name = r.get("name") or r.get("event")
                if name == target and idx_a is None:
                    idx_a = idx
                if name == sec_target and idx_b is None:
                    idx_b = idx

            if idx_a is None:
                passed = False
                details = f"Target event '{target}' was not found in trace."
            elif idx_b is None:
                # If secondary did not occur, ordering depends on intent; if secondary was required:
                passed = False
                details = f"Secondary event '{sec_target}' was not found in trace."
            else:
                passed = idx_a < idx_b
                details = (
                    f"'{target}' occurred at index {idx_a}, '{sec_target}' occurred at index {idx_b}. "
                    + ("Correct order." if passed else "Ordering violation!")
                )

            return TraceAssertionResult(
                assertion_type=atype.value if hasattr(atype, "value") else str(atype),
                target=f"{target} -> {sec_target}",
                passed=passed,
                details=details.strip(),
            )

        elif atype == TraceAssertionType.SELECTED_VALUE_EQUALS:
            matching = [
                r for r in normalized_records
                if r.get("name") == target or r.get("event") == target
            ]
            if not matching:
                return TraceAssertionResult(
                    assertion_type=str(atype),
                    target=target,
                    passed=False,
                    details=f"Event '{target}' not found in trace.",
                )

            last_rec = matching[-1]
            actual = _extract_field(last_rec, assertion.field_path or "selected_value")
            passed = actual == assertion.expected_value
            details = (
                f"Field '{assertion.field_path}' in '{target}': expected '{assertion.expected_value}', "
                f"got '{actual}'."
            )
            return TraceAssertionResult(
                assertion_type=atype.value if hasattr(atype, "value") else str(atype),
                target=target,
                passed=passed,
                details=details.strip(),
            )

        elif atype == TraceAssertionType.SELECTED_VALUE_IN_SET:
            matching = [
                r for r in normalized_records
                if r.get("name") == target or r.get("event") == target
            ]
            if not matching:
                return TraceAssertionResult(
                    assertion_type=str(atype),
                    target=target,
                    passed=False,
                    details=f"Event '{target}' not found in trace.",
                )

            last_rec = matching[-1]
            actual = _extract_field(last_rec, assertion.field_path or "selected_value")
            allowed = assertion.allowed_values or []
            passed = actual in allowed
            details = (
                f"Field '{assertion.field_path}' in '{target}': got '{actual}', "
                f"allowed set: {allowed}."
            )
            return TraceAssertionResult(
                assertion_type=atype.value if hasattr(atype, "value") else str(atype),
                target=target,
                passed=passed,
                details=details.strip(),
            )

        elif atype == TraceAssertionType.FORBIDDEN_TRANSITION_ABSENT:
            # Check if any event has forbidden value or direct illegal jump
            for r in normalized_records:
                name = r.get("name") or r.get("event")
                if name == target:
                    val = _extract_field(r, assertion.field_path or "transition")
                    if assertion.forbidden_values and val in assertion.forbidden_values:
                        return TraceAssertionResult(
                            assertion_type=str(atype),
                            target=target,
                            passed=False,
                            details=f"Forbidden transition value '{val}' detected in '{target}'.",
                        )
            return TraceAssertionResult(
                assertion_type=str(atype),
                target=target,
                passed=True,
                details=f"No forbidden transitions observed for '{target}'.",
            )

        elif atype == TraceAssertionType.TOOL_INVOCATION_COUNT_IN_RANGE:
            # Count invocations where name matches target or attributes.tool matches target
            count = 0
            for r in normalized_records:
                name = r.get("name") or r.get("event")
                tool = r.get("tool") or r.get("tool_name")
                if name == target or tool == target:
                    count += 1

            min_c = assertion.min_count if assertion.min_count is not None else 0
            max_c = assertion.max_count
            passed = count >= min_c and (max_c is None or count <= max_c)
            details = (
                f"Tool/operation '{target}' invoked {count} time(s). "
                f"Allowed range: [{min_c}, {max_c if max_c is not None else 'inf'}]."
            )
            return TraceAssertionResult(
                assertion_type=str(atype),
                target=target,
                passed=passed,
                details=details.strip(),
            )

        return TraceAssertionResult(
            assertion_type=str(atype),
            target=target,
            passed=False,
            details=f"Unsupported assertion type '{atype}'.",
        )

    def grade_trace(
        self,
        trace: Any,
        assertions: List[TraceAssertion],
    ) -> Tuple[bool, List[TraceAssertionResult]]:
        """
        Evaluates a suite of TraceAssertions against an execution trace.
        Returns: (overall_passed: bool, results: List[TraceAssertionResult])
        """
        if not assertions:
            return True, []

        normalized = normalize_trace_records(trace)
        results: List[TraceAssertionResult] = []
        all_passed = True

        for assertion in assertions:
            res = self.grade_assertion(assertion, normalized)
            results.append(res)
            if not res.passed:
                all_passed = False

        return all_passed, results
