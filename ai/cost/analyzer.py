"""
ai/cost/analyzer.py
===================
Creative Efficiency Analyzer & Waste Detection Engine (S28-08C).

Responsibilities:
- Detect unnecessary premium model calls on simple/deterministic tasks.
- Detect accidental duplicate planning calls (distinguishing intentional retries/fallbacks).
- Detect over-retrieval (excessive chunk volume or duplicate/irrelevant context).
- Detect unnecessary generation (generation calls when REUSE was already selected).
- Detect unjustified CREATE tier escalations.
- Detect expensive repeated failures.

Invariants:
- Zero runtime authority: Pure observation and diagnostic reporting.
- Does NOT mutate registries, models, candidate lifecycles, memory, or pipeline state.
- Does NOT automatically switch models, force REUSE, or override tier policies.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from ai.contracts.creative.cost import (
    CostProvenance,
    CreativeUsageEvent,
    EfficiencyFinding,
    EfficiencyFindingType,
    EfficiencySeverity,
    ThresholdProvenance,
)
from ai.contracts.common import QualityTarget
from ai.models.registry import get_model_registry, UnknownModelError
from ai.models.types import CostTier

HIGH_COST_THRESHOLD = Decimal("0.050000")
DETERMINISTIC_STAGES: Set[str] = {
    "INTENT",
    "RECIPE_SELECTION",
    "TASTE",
    "TIER_DECISION",
    "TEMPLATE_SELECTION",
}
MAX_ACCEPTABLE_RETRIEVAL_ITEMS = 15


class CreativeEfficiencyAnalyzer:
    """
    Authoritative observational engine for identifying inefficiencies and waste
    across Creative Intelligence execution telemetry.
    """

    def analyze(
        self,
        events: List[CreativeUsageEvent],
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[EfficiencyFinding]:
        """
        Analyzes a sequence of CreativeUsageEvents and produces structured EfficiencyFindings.
        Strictly read-only; has no mutating side-effects.
        """
        findings: List[EfficiencyFinding] = []
        if not events:
            return findings

        ws_id = workspace_id or events[0].workspace_id
        proj_id = project_id or events[0].project_id

        # 1. Unnecessary Premium Calls & High Cost Calls
        findings.extend(self._detect_premium_calls(events, ws_id, proj_id))

        # 2. Duplicate Planning
        findings.extend(self._detect_duplicate_planning(events, ws_id, proj_id))

        # 3. Over-Retrieval
        findings.extend(self._detect_over_retrieval(events, ws_id, proj_id))

        # 4. Unnecessary Generation (REUSE + Generation)
        findings.extend(self._detect_unnecessary_generation(events, ws_id, proj_id))

        # 5. CREATE escalation without reason
        findings.extend(self._detect_create_escalation(events, ws_id, proj_id))

        # 6. Expensive Repeated Failures
        findings.extend(self._detect_repeated_failures(events, ws_id, proj_id))

        # 7. Incomplete Cost Coverage (UNKNOWN != FREE)
        findings.extend(self._detect_incomplete_coverage(events, ws_id, proj_id))

        return findings

    def _detect_premium_calls(
        self,
        events: List[CreativeUsageEvent],
        workspace_id: str,
        project_id: Optional[str],
    ) -> List[EfficiencyFinding]:
        """Detects expensive premium calls on deterministic tasks or unusually high cost."""
        findings: List[EfficiencyFinding] = []
        registry = get_model_registry()

        for ev in events:
            cost = ev.actual_cost or ev.estimated_cost or Decimal("0")
            stage = (ev.stage or ev.subsystem or "").upper()
            model_id = ev.model
            ev_proj = ev.project_id or project_id

            # High cost threshold check (EMPIRICAL_BASELINE)
            if cost > HIGH_COST_THRESHOLD:
                findings.append(
                    EfficiencyFinding.create(
                        workspace_id=workspace_id,
                        project_id=ev_proj,
                        run_id=ev.run_id,
                        finding_type=EfficiencyFindingType.HIGH_COST_CALL_OBSERVED,
                        severity=EfficiencySeverity.WARNING,
                        observed_value={"cost": str(cost), "threshold_provenance": ThresholdProvenance.EMPIRICAL_BASELINE.value},
                        expected_bound={"cost_ceiling": str(HIGH_COST_THRESHOLD), "threshold_provenance": ThresholdProvenance.EMPIRICAL_BASELINE.value},
                        evidence_refs=[ev.event_id],
                        summary=f"High-cost call observed: model '{model_id}' spent ${cost} during stage '{stage}'.",
                    )
                )

            # Deterministic task with premium model
            # Policy-backed: Requires canonical ModelRegistry to classify model cost_tier as HIGH or VERY_HIGH,
            # or flagship MEDIUM with QualityTarget.HIGH. Unknown models fail closed (no false UNNECESSARY_PREMIUM_CALL).
            if stage in DETERMINISTIC_STAGES and model_id:
                try:
                    mdef = registry.get(model_id)
                    cost_tier = mdef.cost_profile
                    quality_target = getattr(mdef, "quality_profile", None)
                except UnknownModelError:
                    mdef = None
                    cost_tier = None
                    quality_target = None

                is_premium = (
                    cost_tier in (CostTier.HIGH, CostTier.VERY_HIGH)
                    or (cost_tier == CostTier.MEDIUM and quality_target == QualityTarget.HIGH)
                )

                if is_premium:
                    details = ev.details or {}
                    if not details.get("requires_creative_generation", False):
                        findings.append(
                            EfficiencyFinding.create(
                                workspace_id=workspace_id,
                                project_id=ev_proj,
                                run_id=ev.run_id,
                                finding_type=EfficiencyFindingType.UNNECESSARY_PREMIUM_CALL,
                                severity=EfficiencySeverity.WARNING,
                                observed_value={
                                    "model": model_id,
                                    "cost_tier": cost_tier.value if cost_tier else None,
                                    "stage": stage,
                                    "cost": str(cost),
                                    "policy_basis": "ModelRegistry.cost_profile_and_quality",
                                },
                                expected_bound={
                                    "recommended_mode": "DETERMINISTIC_OR_CHEAP",
                                    "allowed_tiers": ["LOW", "FREE"],
                                    "threshold_provenance": ThresholdProvenance.CANONICAL_POLICY.value,
                                },
                                evidence_refs=[ev.event_id],
                                summary=(
                                    f"Unnecessary premium model '{model_id}' (cost_profile: {cost_tier.value if cost_tier else 'N/A'}) "
                                    f"invoked for deterministic stage '{stage}' where deterministic path or low-tier model was expected by policy."
                                ),
                            )
                        )

        return findings

    def _detect_duplicate_planning(
        self,
        events: List[CreativeUsageEvent],
        workspace_id: str,
        project_id: Optional[str],
    ) -> List[EfficiencyFinding]:
        """
        Detects multiple identical planning calls with the same input_hash without retry/error reason.
        """
        findings: List[EfficiencyFinding] = []
        # Group by (project_id, run_id, stage, input_hash)
        planning_groups: Dict[tuple, List[CreativeUsageEvent]] = defaultdict(list)

        for ev in events:
            stage = (ev.stage or ev.subsystem or "").upper()
            if stage in ("CREATIVE_PLANNING", "PLANNING", "NARRATIVE", "DIRECTOR_RECOMMENDATION") and ev.input_hash:
                planning_groups[(ev.project_id or project_id, ev.run_id, stage, ev.input_hash)].append(ev)

        for (grp_proj, run_id, stage, input_hash), group in planning_groups.items():
            if len(group) > 1:
                # Check if duplicates are legitimate retries/fallbacks
                unjustified_calls: List[CreativeUsageEvent] = []
                for i, ev in enumerate(group):
                    details = ev.details or {}
                    is_retry = bool(details.get("is_retry") or details.get("retry_count", 0) > 0)
                    is_fallback = bool(details.get("is_fallback") or details.get("fallback", False))
                    has_error = bool(details.get("error") or details.get("status") in ("FAILED", "ERROR"))
                    is_comparison = bool(details.get("judge_comparison") or details.get("is_pairwise"))

                    # If not first call and no legitimate justification
                    if i > 0 and not (is_retry or is_fallback or has_error or is_comparison):
                        unjustified_calls.append(ev)

                if unjustified_calls:
                    all_ids = [ev.event_id for ev in group]
                    findings.append(
                        EfficiencyFinding.create(
                            workspace_id=workspace_id,
                            project_id=grp_proj,
                            run_id=run_id,
                            finding_type=EfficiencyFindingType.DUPLICATE_PLANNING,
                            severity=EfficiencySeverity.CRITICAL,
                            observed_value={"duplicate_call_count": len(group), "stage": stage},
                            expected_bound={"max_calls": 1},
                            evidence_refs=all_ids,
                            summary=(
                                f"Duplicate planning detected in stage '{stage}': {len(group)} calls executed "
                                f"with identical inputs (hash: {input_hash[:10]}...) without retry or fallback reason."
                            ),
                        )
                    )

        return findings

    def _detect_over_retrieval(
        self,
        events: List[CreativeUsageEvent],
        workspace_id: str,
        project_id: Optional[str],
    ) -> List[EfficiencyFinding]:
        """Detects retrieval volume far exceeding acceptable policy bounds or duplicate items."""
        findings: List[EfficiencyFinding] = []

        for ev in events:
            stage = (ev.stage or ev.subsystem or "").upper()
            ev_proj = ev.project_id or project_id
            if stage in ("KNOWLEDGE_RETRIEVAL", "RETRIEVAL") or ev.operation_type == "RETRIEVAL":
                count = ev.retrieval_items
                details = ev.details or {}
                retrieved_ids = details.get("retrieved_ids", [])

                # Volume bound check (HEURISTIC observation, purely advisory WARNING, never hard architectural error)
                if count > MAX_ACCEPTABLE_RETRIEVAL_ITEMS:
                    findings.append(
                        EfficiencyFinding.create(
                            workspace_id=workspace_id,
                            project_id=ev_proj,
                            run_id=ev.run_id,
                            finding_type=EfficiencyFindingType.OVER_RETRIEVAL,
                            severity=EfficiencySeverity.WARNING,
                            observed_value={"retrieved_count": count, "threshold_provenance": ThresholdProvenance.HEURISTIC.value},
                            expected_bound={"max_retrieval_bound": MAX_ACCEPTABLE_RETRIEVAL_ITEMS, "threshold_provenance": ThresholdProvenance.HEURISTIC.value},
                            evidence_refs=[ev.event_id],
                            summary=(
                                f"Over-retrieval observed (heuristic): {count} knowledge chunks retrieved "
                                f"exceeding reference bound ({MAX_ACCEPTABLE_RETRIEVAL_ITEMS})."
                            ),
                        )
                    )

                # Duplicate chunks check
                if isinstance(retrieved_ids, list) and len(retrieved_ids) > len(set(retrieved_ids)):
                    findings.append(
                        EfficiencyFinding.create(
                            workspace_id=workspace_id,
                            project_id=ev_proj,
                            run_id=ev.run_id,
                            finding_type=EfficiencyFindingType.OVER_RETRIEVAL,
                            severity=EfficiencySeverity.WARNING,
                            observed_value={"total_chunks": len(retrieved_ids), "unique_chunks": len(set(retrieved_ids))},
                            expected_bound={"duplicates_allowed": 0},
                            evidence_refs=[ev.event_id],
                            summary="Duplicate knowledge chunks retrieved in single query execution.",
                        )
                    )

        return findings

    def _detect_unnecessary_generation(
        self,
        events: List[CreativeUsageEvent],
        workspace_id: str,
        project_id: Optional[str],
    ) -> List[EfficiencyFinding]:
        """
        Critical Invariant:
        If REUSE was selected for a scene or project, calling new template/media generation is a defect!
        Also detects repeat identical generations without retry reason.
        """
        findings: List[EfficiencyFinding] = []

        # Group events by (project_id, run_id)
        events_by_scope: Dict[tuple, List[CreativeUsageEvent]] = defaultdict(list)
        for ev in events:
            events_by_scope[(ev.project_id or project_id, ev.run_id)].append(ev)

        for (scoped_proj, scoped_run), scope_events in events_by_scope.items():
            reuse_events = [
                ev for ev in scope_events
                if (ev.details or {}).get("tier") == "REUSE" or (ev.details or {}).get("selected_tier") == "REUSE"
            ]

            if reuse_events:
                # Check if generation occurred in this same scope
                gen_events = [
                    ev for ev in scope_events
                    if ev.operation_type in ("MEDIA_GENERATION", "TEMPLATE_GENERATION") or ev.generation_count > 0
                ]
                for gen_ev in gen_events:
                    details = gen_ev.details or {}
                    if details.get("tier_downgrade") or details.get("reuse_failed_qc"):
                        continue

                    evidence = [r.event_id for r in reuse_events] + [gen_ev.event_id]
                    findings.append(
                        EfficiencyFinding.create(
                            workspace_id=workspace_id,
                            project_id=scoped_proj,
                            run_id=scoped_run,
                            finding_type=EfficiencyFindingType.UNNECESSARY_GENERATION,
                            severity=EfficiencySeverity.CRITICAL,
                            observed_value={"generation_operation": gen_ev.operation_type, "tier_selected": "REUSE"},
                            expected_bound={"allowed_generations_under_reuse": 0},
                            evidence_refs=evidence,
                            summary=(
                                f"Unnecessary generation invoked: Operation '{gen_ev.operation_type}' called "
                                f"despite reusable canonical template already selected for project '{scoped_proj}'."
                            ),
                        )
                    )

        # Duplicate identical generations without retry
        gen_by_hash: Dict[tuple, List[CreativeUsageEvent]] = defaultdict(list)
        for ev in events:
            if (ev.operation_type in ("MEDIA_GENERATION", "TEMPLATE_GENERATION") or ev.generation_count > 0) and ev.input_hash:
                gen_by_hash[(ev.project_id or project_id, ev.input_hash)].append(ev)

        for (scoped_proj, in_hash), g_events in gen_by_hash.items():
            if len(g_events) > 1:
                unjustified = []
                for i, ev in enumerate(g_events):
                    details = ev.details or {}
                    if i > 0 and not (details.get("is_retry") or details.get("status") in ("FAILED", "ERROR")):
                        unjustified.append(ev)
                if unjustified:
                    findings.append(
                        EfficiencyFinding.create(
                            workspace_id=workspace_id,
                            project_id=scoped_proj,
                            run_id=g_events[0].run_id,
                            finding_type=EfficiencyFindingType.UNNECESSARY_GENERATION,
                            severity=EfficiencySeverity.CRITICAL,
                            observed_value={"duplicate_media_generations": len(g_events)},
                            expected_bound={"max_generations": 1},
                            evidence_refs=[ev.event_id for ev in g_events],
                            summary=f"Duplicate media generation executed {len(g_events)} times without retry reason.",
                        )
                    )

        return findings

    def _detect_create_escalation(
        self,
        events: List[CreativeUsageEvent],
        workspace_id: str,
        project_id: Optional[str],
    ) -> List[EfficiencyFinding]:
        """Detects CREATE escalation when a valid REUSE candidate was eligible."""
        findings: List[EfficiencyFinding] = []

        for ev in events:
            details = ev.details or {}
            selected_tier = details.get("selected_tier") or details.get("tier")
            ev_proj = ev.project_id or project_id
            if str(selected_tier).upper() == "CREATE":
                reuse_candidate_available = details.get("reuse_candidate_available")
                reuse_score = details.get("reuse_score", 0.0)
                # If a valid reuse candidate existed with score >= 0.8 but CREATE was chosen
                if reuse_candidate_available and float(reuse_score) >= 0.8:
                    findings.append(
                        EfficiencyFinding.create(
                            workspace_id=workspace_id,
                            project_id=ev_proj,
                            run_id=ev.run_id,
                            finding_type=EfficiencyFindingType.CREATE_ESCALATION_WITHOUT_REASON,
                            severity=EfficiencySeverity.CRITICAL,
                            observed_value={"tier": "CREATE", "reuse_score": reuse_score},
                            expected_bound={"expected_tier": "REUSE"},
                            evidence_refs=[ev.event_id],
                            summary=(
                                f"CREATE escalation without sufficient reason: CREATE chosen despite eligible "
                                f"REUSE candidate available with score {reuse_score}."
                            ),
                        )
                    )

        return findings

    def _detect_repeated_failures(
        self,
        events: List[CreativeUsageEvent],
        workspace_id: str,
        project_id: Optional[str],
    ) -> List[EfficiencyFinding]:
        """Detects expensive accumulated failed runs on the same project."""
        findings: List[EfficiencyFinding] = []
        failures_by_project: Dict[str, List[CreativeUsageEvent]] = defaultdict(list)

        for ev in events:
            if (ev.details or {}).get("status") in ("FAILED", "ERROR"):
                p_id = ev.project_id or project_id or "proj_unknown"
                failures_by_project[p_id].append(ev)

        for p_id, failed_events in failures_by_project.items():
            if len(failed_events) >= 3:
                total_failed_cost = sum(
                    (ev.actual_cost or ev.estimated_cost or Decimal("0")) for ev in failed_events
                )
                findings.append(
                    EfficiencyFinding.create(
                        workspace_id=workspace_id,
                        project_id=p_id,
                        run_id=failed_events[0].run_id,
                        finding_type=EfficiencyFindingType.EXPENSIVE_REPEATED_FAILURE,
                        severity=EfficiencySeverity.WARNING,
                        observed_value={"failed_attempts": len(failed_events), "total_failed_cost": str(total_failed_cost)},
                        expected_bound={"max_unsuccessful_attempts": 2},
                        evidence_refs=[ev.event_id for ev in failed_events],
                        summary=(
                            f"Expensive repeated failure detected: {len(failed_events)} failed runs on project '{p_id}' "
                            f"accumulating ${total_failed_cost}."
                        ),
                    )
                )

        return findings

    def _detect_incomplete_coverage(
        self,
        events: List[CreativeUsageEvent],
        workspace_id: str,
        project_id: Optional[str],
    ) -> List[EfficiencyFinding]:
        """
        Detects events where cost provenance is UNKNOWN (pricing unavailable).
        Enforces that UNKNOWN != FREE, ensuring partial coverage is explicitly flagged.
        """
        findings: List[EfficiencyFinding] = []
        unknown_events = [
            ev for ev in events
            if ev.cost_provenance == CostProvenance.UNKNOWN
            or (ev.actual_cost is None and ev.estimated_cost is None and ev.cost_provenance != CostProvenance.ACTUAL)
        ]

        if unknown_events:
            all_ids = [ev.event_id for ev in unknown_events]
            findings.append(
                EfficiencyFinding.create(
                    workspace_id=workspace_id,
                    project_id=project_id or unknown_events[0].project_id,
                    run_id=unknown_events[0].run_id,
                    finding_type=EfficiencyFindingType.INCOMPLETE_COST_COVERAGE,
                    severity=EfficiencySeverity.WARNING,
                    observed_value={
                        "unknown_cost_events": len(unknown_events),
                        "total_events": len(events),
                        "unknown_models": list({ev.model for ev in unknown_events if ev.model}),
                    },
                    expected_bound={"cost_coverage_complete": True},
                    evidence_refs=all_ids,
                    summary=(
                        f"Incomplete cost coverage: {len(unknown_events)}/{len(events)} events have UNKNOWN "
                        f"cost provenance (UNKNOWN != FREE). Total project cost represents a partial lower bound only."
                    ),
                )
            )

        return findings
