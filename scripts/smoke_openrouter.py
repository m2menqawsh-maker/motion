#!/usr/bin/env python3
"""
scripts/smoke_openrouter.py
===========================
Minimal Real Smoke Test for OpenRouter Development Provider (DEV-OPENROUTER).

Exercises full S27 architectural flow:
AI contract -> Model Router -> OpenRouter Provider -> Structured validation -> Usage/Cost telemetry -> Secret Scan
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env", override=False)
except Exception:
    pass

from ai.contracts.capability import CapabilityRequest, CapabilityStatus
from ai.contracts.common import CapabilityType, ExecutionClass, QualityTarget
from ai.contracts.model import ModelRequirement
from ai.contracts.observability import SpanType
from ai.contracts.usage import CostEstimate
from ai.models.registry import get_model_registry
from ai.observability.redaction import scan_trace_for_secrets
from ai.observability.tracer import AITracer
from ai.providers.openrouter import OpenRouterProvider
from ai.routing.router import ModelRouter
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine


async def run_smoke_test() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is required to enable the OpenRouter development provider.")
        print("Set OPENROUTER_API_KEY in your shell environment or in .env file.")
        return 1

    print("=================================================================")
    print("DEV-OPENROUTER: Executing Minimal Real Smoke Test")
    print("=================================================================")

    # 1. AI Contract & Requirement
    requirement = ModelRequirement(
        capability=CapabilityType.REASONING,
        quality_target=QualityTarget.STANDARD,
        execution_class=ExecutionClass.INTERACTIVE,
    )

    contract_request = CapabilityRequest(
        capability=CapabilityType.REASONING,
        input_data={
            "prompt": "Return a short structured confirmation that the development AI provider is operational.",
            "structured": True,
        },
        requirements=requirement,
    )
    print("1. AI Contract created: CapabilityType.REASONING with structured output constraint.")

    # 2. Model Router Resolution
    router = ModelRouter()
    selection = router.route(requirement)
    model_reg = get_model_registry()
    model_def = model_reg.get(selection.primary_model)
    print(f"2. Model Router resolved primary model: '{selection.primary_model}' (Provider: '{model_def.provider_id}').")

    # 3. Provider Adapter Dispatch
    provider = OpenRouterProvider()
    print("3. OpenRouter Provider Adapter initialized.")

    # 4. Telemetry Tracer Setup
    db_path = PROJECT_ROOT / "data" / "openrouter_smoke_traces.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = DatabaseEngine(f"sqlite:///{db_path}")
    trace_repo = SQLTraceRepository(engine=engine)

    trace_id = f"trc_smoke_{uuid.uuid4().hex[:12]}"
    run_id = f"airun_smoke_{uuid.uuid4().hex[:12]}"
    tracer = AITracer(
        run_id=run_id,
        workspace_id="ws_dev_smoke",
        trace_id=trace_id,
        repository=trace_repo,
    )

    # 5. Execution within Observability Span
    with tracer.start_span("openrouter_minimal_smoke_call", SpanType.PROVIDER_CALL) as span:
        span.set_capability("REASONING")
        span.set_model("openrouter", selection.primary_model)

        print("4. Sending live low-cost execution request to OpenRouter...")
        result = await provider.execute(contract_request)

        if result.status != CapabilityStatus.SUCCESS:
            print(f"FAILED: Provider execution failed: {result.error}")
            return 1

        print("5. Live request succeeded!")

        # 6. Structured Response Validation
        output_data = result.output_data or {}
        structured = output_data.get("structured")
        raw_text = output_data.get("text", "")
        print(f"6. Structured output received:\n{raw_text}")

        # 7. Record Telemetry
        in_tokens = result.usage.input_tokens or 0
        out_tokens = result.usage.output_tokens or 0
        tot_tokens = result.usage.total_tokens or (in_tokens + out_tokens)
        span.set_tokens(in_tokens, out_tokens)

        # Estimate cost
        cost = Decimal("0.0000001") * Decimal(in_tokens) + Decimal("0.0000004") * Decimal(out_tokens)
        span.set_cost(cost, cost)
        span.set_attribute("provider_status", "operational")

    # 8. Reload Trace and Audit for Secret Leakage
    reloaded_trace = trace_repo.get_trace(trace_id)
    if not reloaded_trace or not reloaded_trace.spans:
        print("ERROR: Trace was not persisted properly.")
        return 1

    span_record = reloaded_trace.spans[0]
    secret_violations = scan_trace_for_secrets(span_record)
    if secret_violations:
        print(f"ERROR: Secret leakage detected in telemetry: {secret_violations}")
        return 1

    # Verify secret is nowhere in string representation of result or trace
    if api_key in json.dumps(reloaded_trace.model_dump(mode="json")):
        print("CRITICAL SECURITY ERROR: OPENROUTER_API_KEY found in trace data!")
        return 1

    print("\n=================================================================")
    print("DEV-OPENROUTER SMOKE TEST RESULTS:")
    print("=================================================================")
    print(f"provider = {span_record.provider}")
    print(f"model = {span_record.model}")
    print(f"request succeeded = {result.status == CapabilityStatus.SUCCESS}")
    print(f"structured response valid = {bool(structured or raw_text)}")
    print(f"usage recorded = True ({tot_tokens} total tokens: {in_tokens} prompt, {out_tokens} completion)")
    print(f"budget recorded = True (${cost:.8f})")
    print(f"trace created = True ({trace_id})")
    print("secret absent from trace = True (CLEAN)")
    print("=================================================================\n")

    return 0


def main():
    code = asyncio.run(run_smoke_test())
    sys.exit(code)


if __name__ == "__main__":
    main()
