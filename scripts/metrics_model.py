from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional

class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"

@dataclass
class ComponentMetrics:
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "retry_count": self.retry_count
        }

@dataclass
class RunSummary:
    run_id: str
    status: str = "IN_PROGRESS" # SUCCESS, FAILED, IN_PROGRESS
    duration_ms: Optional[int] = None
    retry_count: int = 0
    recovery_used: bool = False
    failure_codes: Set[str] = field(default_factory=set)
    final_stage: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "recovery_used": self.recovery_used,
            "failure_codes": list(self.failure_codes),
            "final_stage": self.final_stage
        }

@dataclass
class HealthSnapshot:
    generated_at: str
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    events_processed: int = 0
    runs_observed: int = 0
    
    runs_total: int = 0
    runs_success: int = 0
    runs_failed: int = 0
    
    retries_total: int = 0
    recoveries_total: int = 0
    fallback_errors: int = 0
    critical_errors: int = 0
    
    corrupted_events: int = 0
    corrupted_line_numbers: List[int] = field(default_factory=list)
    corruption_types: Set[str] = field(default_factory=set)
    
    avg_run_duration_ms: int = 0
    avg_render_duration_ms: int = 0
    
    components: Dict[str, ComponentMetrics] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.runs_total == 0:
            return 1.0
        return self.runs_success / self.runs_total
        
    @property
    def health_status(self) -> HealthStatus:
        if self.critical_errors > 0:
            return HealthStatus.UNHEALTHY
            
        render_metrics = self.components.get("render")
        if render_metrics and render_metrics.failure_count > 5: # e.g. repeated render failures
            return HealthStatus.UNHEALTHY
            
        if self.success_rate < 0.7:
            return HealthStatus.UNHEALTHY
            
        if self.retries_total > 5 or self.recoveries_total > 2 or self.fallback_errors > 0:
            return HealthStatus.DEGRADED
            
        return HealthStatus.HEALTHY
        
    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "health_status": self.health_status.value,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "events_processed": self.events_processed,
            "runs_observed": self.runs_observed,
            "runs_total": self.runs_total,
            "runs_success": self.runs_success,
            "runs_failed": self.runs_failed,
            "success_rate": round(self.success_rate, 3),
            "retries_total": self.retries_total,
            "recoveries_total": self.recoveries_total,
            "fallback_errors": self.fallback_errors,
            "critical_errors": self.critical_errors,
            "corrupted_events": self.corrupted_events,
            "corrupted_line_numbers": self.corrupted_line_numbers,
            "corruption_types": list(self.corruption_types),
            "avg_run_duration_ms": self.avg_run_duration_ms,
            "avg_render_duration_ms": self.avg_render_duration_ms,
            "components": {k: v.to_dict() for k, v in self.components.items()}
        }
