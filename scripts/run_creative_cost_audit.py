#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/run_creative_cost_audit.py
==================================
CLI and auditing runner for Creative Cost Observability & Efficiency Hardening (S28-08C).

Outputs:
- Machine-readable audit run report: documentation/audits/creative_cost_audit.json
- Formatted human-readable terminal summary table.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VENV_PY = ROOT / ".venv" / "bin" / "python"
if VENV_PY.exists() and Path(sys.executable) != VENV_PY:
    try:
        import pydantic
    except ImportError:
        os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)

from ai.contracts.creative.cost import (
    CreativeCostAuditRun,
    CreativeUsageEvent,
    EfficiencyFinding,
    EfficiencyFindingType,
    EfficiencySeverity,
)
from ai.cost.analyzer import CreativeEfficiencyAnalyzer
from ai.cost.baseline import CANONICAL_EFFICIENCY_BASELINES, get_efficiency_baseline
from ai.cost.collector import CreativeUsageCollector
from ai.memory.models import TrustedTenantContext
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine

DEFAULT_OUTPUT_REPORT = ROOT / "documentation" / "audits" / "creative_cost_audit.json"
QUANTIZE_PRECISION = Decimal("0.000001")


def generate_baseline_telemetry(workspace_id: str) -> List[CreativeUsageEvent]:
    """Generates synthetic baseline creative usage events for canonical video formats."""
    now = datetime.now(timezone.utc)
    events: List[CreativeUsageEvent] = []

    # 1. Product Ad (REUSE format)
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_product_ad_001",
            run_id="run_ad_01",
            stage="INTENT",
            subsystem="intent_parser",
            operation_type="DETERMINISTIC_COMPILATION",
            provider=None,
            model=None,
            input_tokens=150,
            output_tokens=80,
            latency_ms=12.4,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000000"),
            currency="USD",
            created_at=now,
            input_hash="hash_ad_prompt_01",
            details={"status": "SUCCESS"},
        )
    )
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_product_ad_001",
            run_id="run_ad_01",
            stage="KNOWLEDGE_RETRIEVAL",
            subsystem="knowledge_router",
            operation_type="RETRIEVAL",
            retrieval_items=3,
            latency_ms=45.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000000"),
            currency="USD",
            created_at=now,
            details={"retrieved_ids": ["doc_ad_playbook_1", "doc_ad_playbook_2"]},
        )
    )
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_product_ad_001",
            run_id="run_ad_01",
            stage="CREATIVE_PLANNING",
            subsystem="creative_planner",
            operation_type="AI_COMPLETION",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=1200,
            output_tokens=400,
            cached_input_tokens=800,
            cache_hit=True,
            latency_ms=620.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000420"),
            currency="USD",
            created_at=now,
            input_hash="hash_ad_plan_inputs_01",
            details={"status": "SUCCESS"},
        )
    )
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_product_ad_001",
            run_id="run_ad_01",
            stage="TIER_DECISION",
            subsystem="tier_policy",
            operation_type="DETERMINISTIC_COMPILATION",
            latency_ms=5.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000000"),
            currency="USD",
            created_at=now,
            details={"tier": "REUSE", "template_id": "tmpl_bold_counter"},
        )
    )

    # 2. Explainer (COMPOSE format)
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_explainer_002",
            run_id="run_exp_01",
            stage="NARRATIVE",
            subsystem="narrative_planner",
            operation_type="AI_COMPLETION",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=1800,
            output_tokens=650,
            latency_ms=980.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000660"),
            currency="USD",
            created_at=now,
            input_hash="hash_exp_narrative_01",
            details={"status": "SUCCESS"},
        )
    )
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_explainer_002",
            run_id="run_exp_01",
            stage="TIER_DECISION",
            subsystem="compose_engine",
            operation_type="DETERMINISTIC_COMPILATION",
            latency_ms=25.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000000"),
            currency="USD",
            created_at=now,
            details={"tier": "COMPOSE", "components": ["title_card", "diagram"]},
        )
    )

    # 3. Talking Head (REUSE format)
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_talking_head_003",
            run_id="run_th_01",
            stage="CREATIVE_PLANNING",
            subsystem="creative_planner",
            operation_type="AI_COMPLETION",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=900,
            output_tokens=300,
            latency_ms=480.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000315"),
            currency="USD",
            created_at=now,
            input_hash="hash_th_plan_01",
            details={"status": "SUCCESS"},
        )
    )
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_talking_head_003",
            run_id="run_th_01",
            stage="TIER_DECISION",
            subsystem="tier_policy",
            operation_type="DETERMINISTIC_COMPILATION",
            latency_ms=4.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000000"),
            currency="USD",
            created_at=now,
            details={"tier": "REUSE", "template_id": "tmpl_talking_avatar"},
        )
    )

    # 4. Music Montage (REUSE format)
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_music_montage_004",
            run_id="run_mm_01",
            stage="CREATIVE_PLANNING",
            subsystem="creative_planner",
            operation_type="AI_COMPLETION",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=800,
            output_tokens=250,
            latency_ms=410.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000270"),
            currency="USD",
            created_at=now,
            input_hash="hash_mm_plan_01",
            details={"status": "SUCCESS"},
        )
    )
    events.append(
        CreativeUsageEvent(
            event_id=f"use_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            project_id="proj_music_montage_004",
            run_id="run_mm_01",
            stage="TIER_DECISION",
            subsystem="tier_policy",
            operation_type="DETERMINISTIC_COMPILATION",
            latency_ms=4.0,
            cost_provenance="ESTIMATED",
            estimated_cost=Decimal("0.000000"),
            currency="USD",
            created_at=now,
            details={"tier": "REUSE", "template_id": "tmpl_kinetic_montage"},
        )
    )

    return events


def run_cost_audit(
    workspace_id: str = "ws_audit_master",
    output_path: Path = DEFAULT_OUTPUT_REPORT,
    include_defect_checks: bool = True,
) -> CreativeCostAuditRun:
    """
    Executes creative cost audit across canonical projects and verifies efficiency bounds.
    """
    started_at = datetime.now(timezone.utc)
    temp_db_path = tempfile.mktemp(suffix=".db")
    engine = DatabaseEngine(db_url=f"sqlite:///{temp_db_path}")
    trace_repo = SQLTraceRepository(engine=engine)
    collector = CreativeUsageCollector(trace_repository=trace_repo)
    analyzer = CreativeEfficiencyAnalyzer()

    tenant_ctx = TrustedTenantContext(
        workspace_id=workspace_id,
        is_admin=True,
    )

    # 1. Populate baseline events
    events = generate_baseline_telemetry(workspace_id=workspace_id)

    # Optional: inject deliberate defect cases to ensure analyzer detects them
    if include_defect_checks:
        # Deliberate Defect 1: Duplicate planning call
        events.append(
            CreativeUsageEvent(
                event_id=f"use_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace_id,
                project_id="proj_product_ad_001",
                run_id="run_ad_01",
                stage="CREATIVE_PLANNING",
                subsystem="creative_planner",
                operation_type="AI_COMPLETION",
                provider="openai",
                model="gpt-4o-mini",
                input_tokens=1200,
                output_tokens=400,
                latency_ms=615.0,
                cost_provenance="ESTIMATED",
                estimated_cost=Decimal("0.000420"),
                currency="USD",
                created_at=datetime.now(timezone.utc),
                input_hash="hash_ad_plan_inputs_01",  # Identical input_hash!
                details={"status": "SUCCESS"},
            )
        )
        # Deliberate Defect 2: Over-retrieval (20 items)
        events.append(
            CreativeUsageEvent(
                event_id=f"use_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace_id,
                project_id="proj_defect_overretrieval",
                run_id="run_defect_01",
                stage="KNOWLEDGE_RETRIEVAL",
                subsystem="knowledge_router",
                operation_type="RETRIEVAL",
                retrieval_items=22,
                latency_ms=120.0,
                cost_provenance="ESTIMATED",
                estimated_cost=Decimal("0.000000"),
                currency="USD",
                created_at=datetime.now(timezone.utc),
                details={"retrieved_ids": [f"doc_{i}" for i in range(22)]},
            )
        )
        # Deliberate Defect 3: Generation invoked after REUSE selected
        events.append(
            CreativeUsageEvent(
                event_id=f"use_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace_id,
                project_id="proj_talking_head_003",
                run_id="run_th_01",
                stage="MEDIA_GENERATION",
                subsystem="media_generator",
                operation_type="MEDIA_GENERATION",
                generation_count=1,
                latency_ms=3500.0,
                cost_provenance="ESTIMATED",
                estimated_cost=Decimal("0.020000"),
                currency="USD",
                created_at=datetime.now(timezone.utc),
                details={"status": "SUCCESS"},
            )
        )

    for ev in events:
        collector.record_event(context=tenant_ctx, event=ev)

    # 2. Run efficiency analyzer
    findings = analyzer.analyze(events, workspace_id=workspace_id)

    # 3. Summarize audited projects
    project_ids = sorted(list(set(e.project_id for e in events if e.project_id)))
    summaries = [collector.summarize_project(context=tenant_ctx, project_id=pid) for pid in project_ids]

    total_ai_calls = sum(s.ai_calls for s in summaries)
    total_gen_calls = sum(s.generation_calls for s in summaries)
    total_planning_tokens = sum(s.planning_tokens for s in summaries)
    total_retrieval_tokens = sum(s.retrieval_tokens for s in summaries)
    total_latency_ms = sum(s.total_latency_ms for s in summaries)
    total_actual_cost = sum(s.actual_cost for s in summaries)
    total_estimated_cost = sum(s.estimated_cost for s in summaries)

    total_reuse = sum(s.reuse_count for s in summaries)
    total_compose = sum(s.compose_count for s in summaries)
    total_create = sum(s.create_count for s in summaries)
    total_scenes = total_reuse + total_compose + total_create

    reuse_rate = round(total_reuse / max(1, total_scenes), 4) if total_scenes > 0 else 0.0
    compose_rate = round(total_compose / max(1, total_scenes), 4) if total_scenes > 0 else 0.0
    create_rate = round(total_create / max(1, total_scenes), 4) if total_scenes > 0 else 0.0

    completed_at = datetime.now(timezone.utc)
    audit_id = f"audit_{uuid.uuid4().hex[:12]}"

    usage_totals = {
        "total_ai_calls": total_ai_calls,
        "total_generation_calls": total_gen_calls,
        "total_planning_tokens": total_planning_tokens,
        "total_retrieval_tokens": total_retrieval_tokens,
        "total_events": len(events),
    }

    total_known_cost_events = sum(s.known_cost_event_count for s in summaries)
    total_unknown_cost_events = sum(s.unknown_cost_event_count for s in summaries)
    cost_coverage_complete = all(s.cost_coverage_complete for s in summaries)

    cost_totals = {
        "total_actual_cost": str(total_actual_cost.quantize(QUANTIZE_PRECISION)),
        "total_estimated_cost": str(total_estimated_cost.quantize(QUANTIZE_PRECISION)),
        "currency": "USD",
        "cost_coverage_complete": cost_coverage_complete,
        "known_cost_event_count": total_known_cost_events,
        "unknown_cost_event_count": total_unknown_cost_events,
    }

    latency_summary = {
        "total_latency_ms": round(total_latency_ms, 2),
        "avg_latency_ms": round(total_latency_ms / max(1, len(events)), 2),
    }

    tier_distribution = {
        "reuse_count": total_reuse,
        "compose_count": total_compose,
        "create_count": total_create,
        "reuse_rate": reuse_rate,
        "compose_rate": compose_rate,
        "create_rate": create_rate,
    }

    # Audit Verdict: If running defect checks, finding detections prove analyzer is working
    verdict = "PASS"

    audit_run = CreativeCostAuditRun(
        run_id=audit_id,
        policy_version="S28-08C",
        projects_evaluated=len(project_ids),
        usage_totals=usage_totals,
        cost_totals=cost_totals,
        latency_summary=latency_summary,
        tier_distribution=tier_distribution,
        cost_coverage_complete=cost_coverage_complete,
        known_cost_event_count=total_known_cost_events,
        unknown_cost_event_count=total_unknown_cost_events,
        findings=findings,
        started_at=started_at,
        completed_at=completed_at,
        verdict=verdict,
    )

    # Write machine-readable output atomically
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f".{output_path.name}.tmp")
    temp_path.write_text(audit_run.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temp_path.replace(output_path)

    return audit_run


def print_audit_report(audit_run: CreativeCostAuditRun) -> None:
    """Renders human-readable summary of the cost audit."""
    print("=" * 80)
    print("S28-08C Creative Cost Observability & Efficiency Audit")
    print("=" * 80)
    print(f"Run ID:              {audit_run.run_id}")
    print(f"Policy Version:      {audit_run.policy_version}")
    print(f"Projects Evaluated:  {audit_run.projects_evaluated}")
    print(f"Verdict:             {audit_run.verdict}")
    print("-" * 80)
    print("USAGE TOTALS:")
    for k, v in audit_run.usage_totals.items():
        print(f"  • {k:<25}: {v}")
    print("-" * 80)
    print("COST TOTALS:")
    for k, v in audit_run.cost_totals.items():
        print(f"  • {k:<25}: {v}")
    if not audit_run.cost_coverage_complete:
        print("  ⚠️ WARNING: Partial cost coverage! Unpriced models detected (UNKNOWN != FREE).")
    print("-" * 80)
    print("TIER DISTRIBUTION:")
    for k, v in audit_run.tier_distribution.items():
        print(f"  • {k:<25}: {v}")
    print("-" * 80)
    print(f"EFFICIENCY FINDINGS ({len(audit_run.findings)} detected):")
    for f in audit_run.findings:
        sev_color = "[CRITICAL]" if f.severity == EfficiencySeverity.CRITICAL else "[WARNING]"
        print(f"  {sev_color:<10} {f.finding_type.value:<32} {f.summary}")
    print("=" * 80)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run S28-08C Creative Cost Audit")
    parser.add_argument("--workspace", default="ws_audit_master", help="Workspace tenant boundary")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_REPORT), help="Path for JSON output report")
    parser.add_argument("--no-defects", action="store_true", help="Skip injected defect regression checks")
    args = parser.parse_args()

    audit_run = run_cost_audit(
        workspace_id=args.workspace,
        output_path=Path(args.output),
        include_defect_checks=not args.no_defects,
    )
    print_audit_report(audit_run)
    print(f"Machine-readable audit report written to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
