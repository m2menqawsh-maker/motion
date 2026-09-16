import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

from scripts.metrics_model import HealthSnapshot, RunSummary, ComponentMetrics

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
        
    def save(self, output_path: Path):
        snapshot = self.collect()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
