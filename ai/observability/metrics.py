"""
ai/observability/metrics.py
===========================
Standardized AI Subsystem Metrics & Telemetry Instruments (S27.19).

Invariants:
- Tracks all required AI operational, economic, and quality metrics.
- Enforces strictly bounded label cardinality:
  Forbidden labels: raw prompts, full URLs, tokens, arbitrary text.
  Permitted bounded label keys: workspace_id, project_id, capability, provider, model, status, execution_class.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Tuple


ALLOWED_LABEL_KEYS = {
    "workspace_id",
    "project_id",
    "capability",
    "provider",
    "model",
    "status",
    "execution_class",
    "reason_code",
}

FORBIDDEN_LABEL_PATTERNS = {"url", "prompt", "text", "query", "body", "input", "output"}


class HighCardinalityLabelError(ValueError):
    """Raised when an unbounded or high-cardinality label key or value is used in metrics."""
    pass


class AIMetricsCollector:
    """
    In-memory / operational metrics registry and aggregator for AI operations.
    """

    def __init__(self):
        # Counters: (metric_name, frozen_labels) -> float/Decimal
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Decimal] = {}
        # Latency/Quality samples: (metric_name, frozen_labels) -> List[float]
        self._samples: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], List[float]] = {}
        # Operational event counts
        self._requests_total = 0
        self._failures_total = 0
        self._cache_lookups = 0
        self._cache_hits = 0
        self._router_queries = 0
        self._router_escalations = 0
        self._router_fallbacks = 0

    def _validate_and_freeze_labels(self, labels: Optional[Dict[str, str]]) -> Tuple[Tuple[str, str], ...]:
        if not labels:
            return ()
        frozen = []
        for k, v in sorted(labels.items()):
            k_lower = k.lower().strip()
            if k_lower not in ALLOWED_LABEL_KEYS:
                for bad_pat in FORBIDDEN_LABEL_PATTERNS:
                    if bad_pat in k_lower:
                        raise HighCardinalityLabelError(
                            f"Label key '{k}' is forbidden due to high cardinality / unbounded data risk."
                        )
                # If key is not in explicitly allowed list and looks unbounded
                if len(str(v)) > 64:
                    raise HighCardinalityLabelError(
                        f"Label value for '{k}' exceeds maximum 64 character bounded limit ({v[:32]}...)."
                    )
            v_clean = str(v).strip()
            frozen.append((k_lower, v_clean))
        return tuple(frozen)

    def record_cost(self, amount: Decimal, workspace_id: str, project_id: Optional[str] = None) -> None:
        """Records ai.cost.total and ai.cost.per_project."""
        total_key = ("ai.cost.total", self._validate_and_freeze_labels({"workspace_id": workspace_id}))
        self._counters[total_key] = self._counters.get(total_key, Decimal("0.00")) + amount

        if project_id:
            proj_labels = {"workspace_id": workspace_id, "project_id": project_id}
            proj_key = ("ai.cost.per_project", self._validate_and_freeze_labels(proj_labels))
            self._counters[proj_key] = self._counters.get(proj_key, Decimal("0.00")) + amount

    def record_request(
        self,
        capability: str,
        provider: str,
        model: str,
        status: str,
        workspace_id: str,
    ) -> None:
        """Records ai.request.count and updates failure rate."""
        self._requests_total += 1
        if status != "SUCCESS":
            self._failures_total += 1

        labels = {
            "workspace_id": workspace_id,
            "capability": capability,
            "provider": provider,
            "model": model,
            "status": status,
        }
        key = ("ai.request.count", self._validate_and_freeze_labels(labels))
        self._counters[key] = self._counters.get(key, Decimal(0)) + Decimal(1)

    def record_cache_lookup(self, hit: bool, capability: str, workspace_id: str) -> None:
        """Records ai.cache.hit_rate."""
        self._cache_lookups += 1
        if hit:
            self._cache_hits += 1

    def record_router_event(self, event_type: str, capability: str) -> None:
        """Records ai.router.escalation_rate and ai.router.fallback_rate."""
        self._router_queries += 1
        if event_type == "escalation":
            self._router_escalations += 1
        elif event_type == "fallback":
            self._router_fallbacks += 1

    def record_latency(self, provider: str, model: str, latency_ms: float) -> None:
        """Records ai.provider.latency sample."""
        labels = {"provider": provider, "model": model}
        key = ("ai.provider.latency", self._validate_and_freeze_labels(labels))
        if key not in self._samples:
            self._samples[key] = []
        self._samples[key].append(latency_ms)

    def record_provider_error(self, provider: str, model: str) -> None:
        """Records ai.provider.error_rate."""
        labels = {"provider": provider, "model": model}
        key = ("ai.provider.error_rate", self._validate_and_freeze_labels(labels))
        self._counters[key] = self._counters.get(key, Decimal(0)) + Decimal(1)

    def record_budget_rejection(self, workspace_id: str) -> None:
        """Records ai.budget.rejections."""
        labels = {"workspace_id": workspace_id}
        key = ("ai.budget.rejections", self._validate_and_freeze_labels(labels))
        self._counters[key] = self._counters.get(key, Decimal(0)) + Decimal(1)

    def record_retry(self, count: int = 1) -> None:
        """Records ai.retry.count."""
        key = ("ai.retry.count", ())
        self._counters[key] = self._counters.get(key, Decimal(0)) + Decimal(count)

    def record_quality_score(self, score: float, capability: str, model: str) -> None:
        """Records ai.quality.score sample."""
        labels = {"capability": capability, "model": model}
        key = ("ai.quality.score", self._validate_and_freeze_labels(labels))
        if key not in self._samples:
            self._samples[key] = []
        self._samples[key].append(score)

    def get_summary(self) -> Dict[str, Any]:
        """Calculates snapshot of rates and counters."""
        failure_rate = (self._failures_total / self._requests_total) if self._requests_total > 0 else 0.0
        cache_hit_rate = (self._cache_hits / self._cache_lookups) if self._cache_lookups > 0 else 0.0
        escalation_rate = (self._router_escalations / self._router_queries) if self._router_queries > 0 else 0.0
        fallback_rate = (self._router_fallbacks / self._router_queries) if self._router_queries > 0 else 0.0

        total_cost = sum(
            amount for (name, _), amount in self._counters.items() if name == "ai.cost.total"
        )
        total_retries = int(self._counters.get(("ai.retry.count", ()), Decimal(0)))
        budget_rejections = sum(
            int(amt) for (name, _), amt in self._counters.items() if name == "ai.budget.rejections"
        )

        return {
            "ai.cost.total": str(total_cost),
            "ai.request.count": self._requests_total,
            "ai.failure.rate": round(failure_rate, 4),
            "ai.cache.hit_rate": round(cache_hit_rate, 4),
            "ai.router.escalation_rate": round(escalation_rate, 4),
            "ai.router.fallback_rate": round(fallback_rate, 4),
            "ai.budget.rejections": budget_rejections,
            "ai.retry.count": total_retries,
        }
