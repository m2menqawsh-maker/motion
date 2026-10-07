import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

from scripts.metrics.metrics_model import HealthSnapshot, RunSummary, ComponentMetrics

class MetricsCollector:
    def __init__(self, logs_path: Path):
        self.logs_path = logs_path
        self.snapshot = HealthSnapshot(
            generated_at=datetime.now(timezone.utc).isoformat()
        )
        self.runs: Dict[str, RunSummary] = {}
        
    def _get_or_create_run(self, run_id: str) -> RunSummary:
        if run_id not in self.runs:
            self.runs[run_id] = RunSummary(run_id=run_id)
        return self.runs[run_id]
        
    def _get_or_create_component(self, component: str) -> ComponentMetrics:
        if component not in self.snapshot.components:
            self.snapshot.components[component] = ComponentMetrics()
        return self.snapshot.components[component]

    def collect(self) -> HealthSnapshot:
        if not self.logs_path.exists():
            return self.snapshot
            
        render_durations = []
        run_durations = []
        
        with open(self.logs_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError("Not a JSON object")
                except Exception as e:
                    self.snapshot.corrupted_events += 1
                    self.snapshot.corrupted_line_numbers.append(line_idx)
                    self.snapshot.corruption_types.add(type(e).__name__)
                    continue
                    
                self.snapshot.events_processed += 1
                
                timestamp = event.get("timestamp")
                if not self.snapshot.window_start:
                    self.snapshot.window_start = timestamp
                self.snapshot.window_end = timestamp
                
                run_id = event.get("run_id")
                if not run_id:
                    continue
                    
                run = self._get_or_create_run(run_id)
                
                evt_name = event.get("event")
                status = event.get("status")
                component = event.get("component")
                stage = event.get("stage")
                
                if component:
                    comp_metrics = self._get_or_create_component(component)
                    
                    if evt_name == "gate.execution" or evt_name == "render.execution":
                        if status == "success":
                            comp_metrics.success_count += 1
                            if component == "remotion" or component == "docker":
                                # Render success
                                duration = event.get("duration_ms")
                                if duration:
                                    render_durations.append(duration)
                        elif status == "failure":
                            comp_metrics.failure_count += 1
                            
                    elif evt_name == "retry.scheduled":
                        comp_metrics.retry_count += 1
                        
                if evt_name == "retry.scheduled":
                    self.snapshot.retries_total += 1
                    run.retry_count += 1
                    
                if evt_name == "recovery.resumed":
                    self.snapshot.recoveries_total += 1
                    run.recovery_used = True
                    
                if event.get("is_fallback") is True:
                    self.snapshot.fallback_errors += 1
                    
                if event.get("severity") == "CRITICAL":
                    self.snapshot.critical_errors += 1
                    
                failure_code = event.get("error_code")
                if failure_code:
                    run.failure_codes.add(failure_code)
                    
                if stage:
                    run.final_stage = stage

                # S28-R14 Section 17 Production Telemetry Parsing
                self._record_telemetry_fields(event, render_durations, run_durations)
                    
                # Terminal events for pipeline
                if evt_name == "pipeline.execution":
                    if status == "success":
                        run.status = "SUCCESS"
                        dur = event.get("duration_ms")
                        if dur:
                            run.duration_ms = dur
                            run_durations.append(dur)
                    elif status == "failure":
                        run.status = "FAILED"
                        dur = event.get("duration_ms")
                        if dur:
                            run.duration_ms = dur
                            
        # Aggregate runs
        for run in self.runs.values():
            if run.status == "SUCCESS":
                self.snapshot.runs_success += 1
            elif run.status == "FAILED":
                self.snapshot.runs_failed += 1
                
        self.snapshot.runs_total = self.snapshot.runs_success + self.snapshot.runs_failed
        self.snapshot.runs_observed = len(self.runs)
        
        if run_durations:
            self.snapshot.avg_run_duration_ms = sum(run_durations) // len(run_durations)
        if render_durations:
            self.snapshot.avg_render_duration_ms = sum(render_durations) // len(render_durations)
            
        return self.snapshot

    def record_event(self, event: dict) -> None:
        """Directly ingest a telemetry/metric event into the snapshot."""
        self.snapshot.events_processed += 1
        durations = []
        run_durs = []
        self._record_telemetry_fields(event, durations, run_durs)

    def _record_telemetry_fields(self, event: dict, render_durations: list, run_durations: list) -> None:
        evt_name = event.get("event") or event.get("event_type") or ""
        error_code = event.get("error_code") or event.get("code") or ""
        dur = event.get("duration_ms") or event.get("latency_ms")

        # 1. Authoring latency & CAS conflicts
        if "authoring" in evt_name.lower() and dur:
            self.snapshot.authoring_latencies_ms.append(dur)
        if error_code == "REVISION_CONFLICT" or evt_name == "mutation.conflict":
            self.snapshot.mutation_conflicts += 1

        # 2. Idempotency hits & conflicts
        if evt_name in ("idempotency.hit", "IDEMPOTENCY_REPLAY") or event.get("idempotency_hit"):
            self.snapshot.idempotency_hits += 1
        if error_code == "IDEMPOTENCY_CONFLICT" or evt_name == "idempotency.conflict":
            self.snapshot.idempotency_conflicts += 1

        # 3. Preview proxy metrics
        if "preview_queue" in evt_name.lower() and dur:
            self.snapshot.preview_proxy_queue_latencies_ms.append(dur)
        if ("preview_render" in evt_name.lower() or evt_name == "PROXIES_MATERIALIZED") and dur:
            self.snapshot.preview_proxy_render_latencies_ms.append(dur)
        if event.get("preview_cache_hit") is True or evt_name == "preview.cache_hit":
            self.snapshot.preview_cache_hits += 1
        elif event.get("preview_cache_hit") is False or evt_name == "preview.cache_miss":
            self.snapshot.preview_cache_misses += 1

        # 4. Render queue & duration
        if "render_queue" in evt_name.lower() and dur:
            self.snapshot.render_queue_latencies_ms.append(dur)
        if evt_name in ("RENDER_SUCCEEDED", "render.execution") and dur:
            self.snapshot.render_durations_ms.append(dur)
            render_durations.append(dur)

        # 5. Renderer metrics
        renderer_id = event.get("renderer_id") or event.get("assigned_renderer")
        if renderer_id and dur:
            if renderer_id not in self.snapshot.renderer_durations_by_renderer:
                self.snapshot.renderer_durations_by_renderer[renderer_id] = []
            self.snapshot.renderer_durations_by_renderer[renderer_id].append(dur)

        if error_code.startswith("RENDERER_") or "RENDER" in error_code:
            self.snapshot.renderer_errors_by_class[error_code] = (
                self.snapshot.renderer_errors_by_class.get(error_code, 0) + 1
            )
        if error_code == "RENDERER_TIMEOUT":
            self.snapshot.renderer_timeouts += 1

        # 6. RenderGraph node counts
        node_count = event.get("node_count") or event.get("nodeCount")
        if node_count is not None:
            self.snapshot.render_graph_node_counts.append(int(node_count))

        # 7. Cancellations
        if error_code in ("RENDERER_CANCELLED", "RUN_CANCELLED") or evt_name in ("RENDER_CANCELLED", "cancellation"):
            self.snapshot.cancellations_total += 1

        # 8. Composition & QC duration
        if ("composition" in evt_name.lower() or evt_name == "COMPOSITION_COMPLETED") and dur:
            self.snapshot.composition_durations_ms.append(dur)
        if ("qc" in evt_name.lower() or evt_name == "QC_COMPLETED") and dur:
            self.snapshot.qc_durations_ms.append(dur)

        # 9. Storage failures & worker lease loss
        if error_code == "STORAGE_UNAVAILABLE" or "storage.failure" in evt_name.lower():
            self.snapshot.storage_failures += 1
        if error_code == "WORKER_LEASE_LOST" or "lease_loss" in evt_name.lower():
            self.snapshot.worker_lease_losses += 1

        # 10. Budget & Usage
        if error_code == "BUDGET_EXCEEDED" or evt_name == "BUDGET_EXCEEDED":
            self.snapshot.budget_exceeded_total += 1
        if evt_name in ("USAGE_METERED", "usage.recorded"):
            self.snapshot.usage_events_total += 1
        
    def save(self, output_path: Path):
        snapshot = self.collect()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
