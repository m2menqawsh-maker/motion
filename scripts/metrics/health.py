import sys
from pathlib import Path

from scripts.metrics.metrics_collector import MetricsCollector
from scripts.metrics.metrics_model import HealthStatus

def print_health_report(snapshot):
    print("=" * 50)
    print(" 🏥 SYSTEM HEALTH REPORT")
    print("=" * 50)
    
    status_str = snapshot.health_status.value
    if snapshot.health_status == HealthStatus.HEALTHY:
        status_str = f"✅ {status_str}"
    elif snapshot.health_status == HealthStatus.DEGRADED:
        status_str = f"⚠️ {status_str}"
    else:
        status_str = f"❌ {status_str}"
        
    print(f"Status:          {status_str}")
    print(f"Generated at:    {snapshot.generated_at}")
    print(f"Events Processed:{snapshot.events_processed}")
    print("-" * 50)
    
    print(" 📊 RUN METRICS")
    print("-" * 50)
    print(f"Total Completed Runs: {snapshot.runs_total}")
    print(f"Success:              {snapshot.runs_success}")
    print(f"Failed:               {snapshot.runs_failed}")
    print(f"Success Rate:         {snapshot.success_rate:.1%}")
    print(f"Avg Run Duration:     {snapshot.avg_run_duration_ms / 1000:.1f}s")
    print("-" * 50)
    
    print(" 🔄 RESILIENCE & ERRORS")
    print("-" * 50)
    print(f"Retries Triggered:    {snapshot.retries_total}")
    print(f"Recoveries Used:      {snapshot.recoveries_total}")
    print(f"Fallback Errors:      {snapshot.fallback_errors}")
    print(f"Critical Errors:      {snapshot.critical_errors}")
    print("-" * 50)
    
    print(" 🧩 COMPONENT HIGHLIGHTS")
    print("-" * 50)
    for comp, metrics in snapshot.components.items():
        if comp in ("remotion", "docker", "pipeline"):
            print(f"[{comp.upper()}]")
            print(f"  Success: {metrics.success_count}")
            print(f"  Failure: {metrics.failure_count}")
            print(f"  Retries: {metrics.retry_count}")
            if comp in ("remotion", "docker"):
                print(f"  Avg Time: {snapshot.avg_render_duration_ms / 1000:.1f}s")
    
    print("=" * 50)

def main():
    workspace_root = Path.cwd().resolve()
    logs_path = workspace_root / "logs" / "runtime.jsonl"
    snapshot_path = workspace_root / "logs" / "health_snapshot.json"
    
    if not logs_path.exists():
        print(f"❌ Error: Log file not found at {logs_path}")
        sys.exit(1)
        
    collector = MetricsCollector(logs_path)
    snapshot = collector.collect()
    collector.save(snapshot_path)
    
    print_health_report(snapshot)
    
if __name__ == "__main__":
    main()
