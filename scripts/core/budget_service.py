"""
scripts/core/budget_service.py
==============================
S28-R14 Section 18: Cost and Budget Policy Enforcement & Usage Metering Service.

Guarantees:
- Pre-execution fail-closed policy checks before expensive work begins.
- Raises structured BudgetExceededError with FailureCode.BUDGET_EXCEEDED.
- Integrates with UsageRepository for durable consumption recording.
- Reuses existing tenant isolation and FailureModel boundaries.
"""

from typing import Optional, Dict
from scripts.core.database import DatabaseEngine, UsageRepository, UsageEventType, get_database_engine
from scripts.core.failure_model import FailureCode


class BudgetExceededError(Exception):
    """Raised when tenant/workspace consumption policy limits are violated."""

    def __init__(self, message: str, workspace_id: str, estimated_units: float, current_units: float, limit: float):
        super().__init__(f"[{FailureCode.BUDGET_EXCEEDED.value}] Workspace '{workspace_id}': {message}")
        self.code = FailureCode.BUDGET_EXCEEDED.value
        self.workspace_id = workspace_id
        self.estimated_units = estimated_units
        self.current_units = current_units
        self.limit = limit


class BudgetService:
    """Production service evaluating budget limits and recording actual usage consumption."""

    def __init__(self, engine: Optional[DatabaseEngine] = None):
        self._engine = engine

    @property
    def engine(self) -> DatabaseEngine:
        return self._engine or get_database_engine()

    @property
    def usage_repo(self) -> UsageRepository:
        return UsageRepository(self.engine)

    def check_budget(
        self,
        workspace_id: str,
        estimated_units: float,
        limit: Optional[float] = None,
        event_type: UsageEventType = UsageEventType.RENDER_SECONDS,
        project_id: Optional[str] = None,
    ) -> bool:
        """
        Pre-execution check: evaluate workspace budget before running expensive work.
        If limit is specified and (current_usage + estimated_units) > limit, fails closed.
        """
        if limit is None:
            return True

        usage_map = self.usage_repo.get_workspace_usage(workspace_id)
        current = usage_map.get(event_type.value, 0.0)

        if current + estimated_units > limit:
            raise BudgetExceededError(
                message=f"Budget limit of {limit} {event_type.value} exceeded (current: {current}, requested: {estimated_units})",
                workspace_id=workspace_id,
                estimated_units=estimated_units,
                current_units=current,
                limit=limit,
            )
        return True

    def record_usage(
        self,
        workspace_id: str,
        quantity: float,
        event_type: UsageEventType = UsageEventType.RENDER_SECONDS,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Durable post-execution usage metering record."""
        return self.usage_repo.record_usage(
            workspace_id=workspace_id,
            event_type=event_type,
            quantity=quantity,
            project_id=project_id,
            user_id=user_id,
        )
