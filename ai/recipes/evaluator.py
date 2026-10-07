"""
ai/recipes/evaluator.py
=======================
Recipe Selection Matrix Evaluation Harness (S28-03 DEC-31 / DEC-48).

Evaluates the multidimensional matrix:
video_type × platform × audio_mode × available assets × budget/quality

Measures:
- Hard Eligibility Compliance (no disqualified recipe ever selected)
- Forbidden Recipe Avoidance (must_not_select invariants)
- Selection Accuracy (selected recipe matches expected primary or allowed ambiguous set)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import Field

from ai.contracts.base import AIContractModel
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.recipe import RecipeSelection
from ai.intent.brief_builder import CreativeBriefBuilder
from ai.recipes.contracts import NoEligibleRecipeError
from ai.recipes.selector import RecipeSelector


class RecipeMatrixTestCase(AIContractModel):
    """Evaluation case for the Recipe Selection Matrix."""
    matrix_id: str
    user_request: str
    video_type: Optional[str] = None
    platform: str = "instagram_reels"
    audio_mode: str = "VO_MUSIC"
    expected_selected_recipe: Union[str, List[str]]
    must_not_select: List[str] = Field(default_factory=list)
    has_source_speech_media: bool = False
    available_media: Optional[List[str]] = None
    budget_tier: Optional[str] = None
    quality_profile: Optional[str] = None



class RecipeMatrixReport(AIContractModel):
    """Machine-readable report summarizing Recipe Selection Matrix evaluation."""
    total_cases: int
    selection_accuracy: float = Field(ge=0.0, le=1.0)
    forbidden_avoidance_rate: float = Field(ge=0.0, le=1.0)
    cases_passed: int
    cases_failed: int
    failure_details: List[Dict[str, Any]] = Field(default_factory=list)


class RecipeMatrixEvaluator:
    """
    Evaluator running the Recipe Selection Matrix benchmark.
    """

    def __init__(
        self,
        selector: Optional[RecipeSelector] = None,
        builder: Optional[CreativeBriefBuilder] = None,
    ) -> None:
        self.selector = selector or RecipeSelector()
        self.builder = builder or CreativeBriefBuilder()

    def evaluate_cases(self, cases: List[RecipeMatrixTestCase]) -> RecipeMatrixReport:
        """Evaluates a list of RecipeMatrixTestCases."""
        total = len(cases)
        if total == 0:
            return RecipeMatrixReport(
                total_cases=0,
                selection_accuracy=1.0,
                forbidden_avoidance_rate=1.0,
                cases_passed=0,
                cases_failed=0,
            )

        correct_selections = 0
        forbidden_avoided_count = 0
        total_forbidden_checks = 0
        failed_cases: List[Dict[str, Any]] = []

        for case in cases:
            case_passed = True
            reasons = []

            # Synthesize brief
            brief = self.builder.build_brief(
                user_request=case.user_request,
                workspace_constraints={"target_platforms": [case.platform]},
            )

            # Mock media intelligence if speech required
            media_intel = None
            if case.has_source_speech_media:
                from ai.contracts.media import MediaIntelligence, SpeechIntelligence, AnalysisProvenance
                now_iso = datetime.now(timezone.utc).isoformat()
                media_intel = MediaIntelligence(
                    workspace_id="ws_eval",
                    asset_id="asset_eval_01",
                    content_hash="hash_eval_speech_01",
                    created_at=now_iso,
                    speech=SpeechIntelligence(
                        transcript="Sample spoken audio transcript",
                        language="en",
                        provenance=AnalysisProvenance(producer="probe", timestamp=now_iso),
                    ),
                    provenance=AnalysisProvenance(producer="probe", timestamp=now_iso),
                )

            if case.available_media is not None:
                media_list = case.available_media
            else:
                media_list = ["sample_video.mp4"] if case.has_source_speech_media else None

            try:
                selection: RecipeSelection = self.selector.select_recipe(
                    brief=brief,
                    available_media=media_list,
                    media_intelligence=media_intel,
                    budget_tier=case.budget_tier,
                    quality_profile=case.quality_profile,
                )
                selected_id = selection.selected_recipe_id

                # 1. Check must_not_select invariants
                for forbidden_recipe in case.must_not_select:
                    total_forbidden_checks += 1
                    if selected_id == forbidden_recipe:
                        case_passed = False
                        reasons.append(
                            f"CRITICAL INVARIANT VIOLATION: Selected forbidden recipe '{selected_id}'"
                        )
                    else:
                        forbidden_avoided_count += 1

                # 2. Check expected selection
                expected = case.expected_selected_recipe
                expected_list = expected if isinstance(expected, list) else [expected]
                if selected_id in expected_list:
                    correct_selections += 1
                else:
                    case_passed = False
                    reasons.append(
                        f"Selection mismatch: expected one of {expected_list}, got '{selected_id}'"
                    )

            except NoEligibleRecipeError as e:
                # If expecting rejection
                expected = case.expected_selected_recipe
                if expected == "NO_RECIPE_ELIGIBLE" or (isinstance(expected, list) and "NO_RECIPE_ELIGIBLE" in expected):
                    correct_selections += 1
                else:
                    case_passed = False
                    reasons.append(f"Unexpected NoEligibleRecipeError: {e}")

            if not case_passed:
                failed_cases.append({
                    "matrix_id": case.matrix_id,
                    "user_request": case.user_request,
                    "reasons": reasons,
                })

        cases_passed = total - len(failed_cases)
        accuracy = correct_selections / max(1, total)
        forbidden_rate = (
            forbidden_avoided_count / max(1, total_forbidden_checks)
            if total_forbidden_checks > 0
            else 1.0
        )

        return RecipeMatrixReport(
            total_cases=total,
            selection_accuracy=round(accuracy, 4),
            forbidden_avoidance_rate=round(forbidden_rate, 4),
            cases_passed=cases_passed,
            cases_failed=len(failed_cases),
            failure_details=failed_cases,
        )

    def evaluate_file(self, json_path: Path) -> RecipeMatrixReport:
        """Loads matrix dataset from JSON and runs evaluation."""
        data = json.loads(json_path.read_text(encoding="utf-8"))
        cases = [RecipeMatrixTestCase.model_validate(c) for c in data.get("cases", data)]
        return self.evaluate_cases(cases)
