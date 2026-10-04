"""
ai/intent/evaluator.py
======================
Intent Evaluation Harness measuring intent accuracy, field accuracy,
unsupported inference rate, and contradiction detection (S28-03 DEC-07 / DEC-32).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ai.contracts.creative.brief import ProvenanceType
from ai.intent.contracts import IntentEvaluationCase, IntentEvaluationReport, IntentParseResult
from ai.intent.parser import IntentParser


class IntentEvaluator:
    """
    Evaluates IntentParser performance across multilingual test cases,
    measuring accuracy, unsupported inference rate, and contradiction detection.
    """

    def __init__(self, parser: Optional[IntentParser] = None) -> None:
        self.parser = parser or IntentParser()

    def evaluate_cases(self, cases: List[IntentEvaluationCase]) -> IntentEvaluationReport:
        """Runs evaluation over a list of IntentEvaluationCases and computes standard metrics."""
        total = len(cases)
        if total == 0:
            return IntentEvaluationReport(
                total_cases=0,
                intent_accuracy=1.0,
                field_accuracy=1.0,
                unsupported_inference_rate=0.0,
                contradiction_detection_rate=1.0,
                cases_passed=0,
                cases_failed=0,
            )

        intent_correct = 0
        total_fields_checked = 0
        correct_fields_count = 0
        unsupported_inferences = 0
        contradiction_expected_count = 0
        contradiction_detected_count = 0

        failed_cases: List[Dict[str, Any]] = []

        per_field_stats: Dict[str, Dict[str, int]] = {
            "video_type": {"checked": 0, "correct": 0},
            "platform": {"checked": 0, "correct": 0},
            "duration": {"checked": 0, "correct": 0},
            "language": {"checked": 0, "correct": 0},
            "audio_mode": {"checked": 0, "correct": 0},
            "style": {"checked": 0, "correct": 0},
            "pace": {"checked": 0, "correct": 0},
        }
        wrong_explicit_count = 0
        unsupported_count = 0

        for case in cases:
            case_passed = True
            failure_reasons = []

            # Execute parse
            result: IntentParseResult = self.parser.parse(
                user_request=case.user_request,
                workspace_constraints=case.workspace_constraints,
            )

            # 1. Contradiction evaluation
            if case.has_contradiction:
                contradiction_expected_count += 1
                if len(result.detected_contradictions) > 0:
                    contradiction_detected_count += 1
                else:
                    case_passed = False
                    failure_reasons.append("Expected contradiction was not detected")

            # 2. Language check
            if case.language:
                per_field_stats["language"]["checked"] += 1
                total_fields_checked += 1
                if result.detected_language == case.language:
                    per_field_stats["language"]["correct"] += 1
                    correct_fields_count += 1
                else:
                    case_passed = False
                    failure_reasons.append(
                        f"Language mismatch: expected '{case.language}', got '{result.detected_language}'"
                    )

            # 3. Intent accuracy (video_type)
            if case.expected_intent is not None:
                per_field_stats["video_type"]["checked"] += 1
                total_fields_checked += 1
                if result.video_type == case.expected_intent:
                    intent_correct += 1
                    per_field_stats["video_type"]["correct"] += 1
                    correct_fields_count += 1
                else:
                    case_passed = False
                    failure_reasons.append(
                        f"Intent mismatch: expected '{case.expected_intent}', got '{result.video_type}'"
                    )
                    if result.field_provenance.get("video_type", None) and result.field_provenance["video_type"].source_type.value == "EXPLICIT":
                        wrong_explicit_count += 1

            # 4. Audio Mode check
            if case.expected_audio_mode is not None:
                per_field_stats["audio_mode"]["checked"] += 1
                total_fields_checked += 1
                if result.audio_mode.value == case.expected_audio_mode:
                    per_field_stats["audio_mode"]["correct"] += 1
                    correct_fields_count += 1
                else:
                    case_passed = False
                    failure_reasons.append(
                        f"Audio mode mismatch: expected '{case.expected_audio_mode}', got '{result.audio_mode.value}'"
                    )
                    if result.field_provenance.get("audio_mode", None) and result.field_provenance["audio_mode"].source_type.value == "EXPLICIT":
                        wrong_explicit_count += 1

            # 5. Pace check
            if case.expected_pace is not None:
                per_field_stats["pace"]["checked"] += 1
                total_fields_checked += 1
                if result.pace == case.expected_pace:
                    per_field_stats["pace"]["correct"] += 1
                    correct_fields_count += 1
                else:
                    case_passed = False
                    failure_reasons.append(
                        f"Pace mismatch: expected '{case.expected_pace}', got '{result.pace}'"
                    )
                    if result.field_provenance.get("pace", None) and result.field_provenance["pace"].source_type.value == "EXPLICIT":
                        wrong_explicit_count += 1

            # 6. Style check
            if case.expected_style is not None:
                per_field_stats["style"]["checked"] += 1
                total_fields_checked += 1
                if result.style == case.expected_style:
                    per_field_stats["style"]["correct"] += 1
                    correct_fields_count += 1
                else:
                    case_passed = False
                    failure_reasons.append(
                        f"Style mismatch: expected '{case.expected_style}', got '{result.style}'"
                    )
                    if result.field_provenance.get("style", None) and result.field_provenance["style"].source_type.value == "EXPLICIT":
                        wrong_explicit_count += 1

            # 7. Platform check
            if case.expected_platform is not None:
                per_field_stats["platform"]["checked"] += 1
                total_fields_checked += 1
                if case.expected_platform in result.target_platforms:
                    per_field_stats["platform"]["correct"] += 1
                    correct_fields_count += 1
                else:
                    case_passed = False
                    failure_reasons.append(
                        f"Platform mismatch: expected '{case.expected_platform}' in {result.target_platforms}"
                    )

            # 8. Duration provenance check
            if "duration" in case.expected_provenance_types:
                per_field_stats["duration"]["checked"] += 1
                total_fields_checked += 1
                dur_prov = result.field_provenance.get("duration")
                if dur_prov and dur_prov.source_type.value == case.expected_provenance_types["duration"]:
                    per_field_stats["duration"]["correct"] += 1
                    correct_fields_count += 1
                else:
                    case_passed = False
                    failure_reasons.append(
                        f"Duration provenance mismatch: expected '{case.expected_provenance_types['duration']}', got '{dur_prov.source_type.value if dur_prov else None}'"
                    )

            # 9. Provenance validation & Unsupported Inference check
            for field_name, expected_prov in case.expected_provenance_types.items():
                if field_name == "duration":
                    continue  # Already checked above
                total_fields_checked += 1
                actual_prov = result.field_provenance.get(field_name)
                if actual_prov is not None:
                    if actual_prov.source_type.value == expected_prov:
                        correct_fields_count += 1
                    else:
                        case_passed = False
                        failure_reasons.append(
                            f"Provenance mismatch on '{field_name}': expected '{expected_prov}', got '{actual_prov.source_type.value}'"
                        )
                        # Check for unsupported inference:
                        if expected_prov in ("DEFAULTED", "UNKNOWN") and actual_prov.source_type.value in ("EXPLICIT", "INFERRED"):
                            unsupported_inferences += 1
                            unsupported_count += 1
                else:
                    case_passed = False
                    failure_reasons.append(f"Missing provenance for field '{field_name}'")

            if not case_passed:
                failed_cases.append({
                    "case_id": case.case_id,
                    "user_request": case.user_request,
                    "reasons": failure_reasons,
                })

        cases_passed = total - len(failed_cases)
        intent_acc = intent_correct / max(1, sum(1 for c in cases if c.expected_intent is not None))
        field_acc = correct_fields_count / max(1, total_fields_checked)
        unsupported_rate = unsupported_inferences / max(1, total_fields_checked)
        contra_rate = (
            (contradiction_detected_count / contradiction_expected_count)
            if contradiction_expected_count > 0
            else 1.0
        )

        per_field_accuracy = {
            f: round(stats["correct"] / max(1, stats["checked"]), 4)
            for f, stats in per_field_stats.items()
            if stats["checked"] > 0
        }

        return IntentEvaluationReport(
            total_cases=total,
            intent_accuracy=round(intent_acc, 4),
            field_accuracy=round(field_acc, 4),
            per_field_accuracy=per_field_accuracy,
            wrong_explicit_field_count=wrong_explicit_count,
            unsupported_inferred_or_defaulted_field_count=unsupported_count,
            unsupported_inference_rate=round(unsupported_rate, 4),
            contradiction_detection_rate=round(contra_rate, 4),
            cases_passed=cases_passed,
            cases_failed=len(failed_cases),
            failure_details=failed_cases,
        )

    def evaluate_file(self, json_path: Path) -> IntentEvaluationReport:
        """Loads dataset from JSON file and runs evaluation."""
        data = json.loads(json_path.read_text(encoding="utf-8"))
        cases = [IntentEvaluationCase.model_validate(c) for c in data.get("cases", data)]
        return self.evaluate_cases(cases)
