"""
scripts/core/ai_run_repository.py
==================================
SQL-backed persistent implementation of AIRunRepository (S27.11).

Architectural Boundaries (ADR-004 DEC-01):
- Implemented in scripts/core/ (approved persistence layer) to satisfy S27.0 architecture guards.
- DatabaseEngine handles connection management, SQLite WAL mode, and transactions.
- Implements atomic CAS worker claims, monotonic lease fencing, and multi-tenant isolation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.contracts.activity import (
    AIActivityRecord,
    ActivityStatus,
    IdempotencySemantics,
)
from ai.contracts.common import CapabilityTypeEnum, ExecutionClass, ExecutionClassEnum
from ai.contracts.errors import AIError
from ai.contracts.run import AIRun, AIRunStatus, AIStep, AIStepStatus
from ai.contracts.usage import CostEstimate, UsageRecord
from ai.orchestration.errors import (
    ActivityNotFoundError,
    RunAlreadyTerminalError,
    RunNotFoundError,
    StaleWorkerLeaseError,
    StepNotFoundError,
    TenantAccessDeniedError,
)
from ai.orchestration.repository import AIRunRepository
from ai.orchestration.state import AIRunStateMachine, AIStepStateMachine
from scripts.core.database import DatabaseEngine, get_database_engine


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_runs (
    run_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT,
    session_id TEXT,
    status TEXT NOT NULL,
    capability TEXT NOT NULL,
    workflow_ref TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    usage_json TEXT NOT NULL,
    cost_json TEXT NOT NULL,
    error_json TEXT,
    contract_version TEXT NOT NULL DEFAULT '1.0.0',
    execution_class TEXT NOT NULL DEFAULT 'INTERACTIVE',
    prompt_id TEXT,
    prompt_version TEXT,
    prompt_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_runs_ws_status ON ai_runs(workspace_id, status);

CREATE TABLE IF NOT EXISTS ai_steps (
    step_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    capability TEXT NOT NULL,
    input_ref TEXT,
    output_ref TEXT,
    provider TEXT,
    model TEXT,
    usage_json TEXT NOT NULL,
    cost_json TEXT NOT NULL,
    error_json TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    worker_id TEXT,
    lease_token TEXT,
    lease_acquired_at TEXT,
    lease_expires_at TEXT,
    heartbeat_at TEXT,
    input_hash TEXT,
    idempotency_key TEXT,
    dependencies_json TEXT NOT NULL DEFAULT '[]',
    max_attempts INTEGER NOT NULL DEFAULT 3,
    next_retry_at TEXT,
    prompt_id TEXT,
    prompt_version TEXT,
    prompt_hash TEXT,
    FOREIGN KEY (run_id) REFERENCES ai_runs(run_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_ai_steps_ws_status ON ai_steps(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ai_steps_run ON ai_steps(run_id);
CREATE INDEX IF NOT EXISTS idx_ai_steps_runnable ON ai_steps(status, next_retry_at);

CREATE TABLE IF NOT EXISTS ai_activities (
    activity_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL,
    semantics TEXT NOT NULL DEFAULT 'EFFECTIVELY_ONCE',
    started_at TEXT,
    completed_at TEXT,
    provider TEXT,
    model TEXT,
    remote_operation_ref TEXT,
    output_ref TEXT,
    error_json TEXT,
    cost_json TEXT,
    usage_json TEXT,
    cost_settled INTEGER NOT NULL DEFAULT 0,
    reservation_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES ai_runs(run_id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES ai_steps(step_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ai_activities_ws_step_idem ON ai_activities(workspace_id, step_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_ai_activities_run ON ai_activities(run_id);
CREATE INDEX IF NOT EXISTS idx_ai_activities_ws_idem ON ai_activities(workspace_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_ai_activities_status ON ai_activities(status);
"""


class SQLAIRunRepository(AIRunRepository):
    """
    Production-grade persistent repository for AIRun and AIStep.
    Supports atomic worker claims, lease fencing, and tenant boundary enforcement.
    """

    def __init__(self, engine: Optional[DatabaseEngine] = None):
        self.engine = engine or get_database_engine()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.engine.transaction("IMMEDIATE") as conn:
            for statement in SCHEMA_SQL.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(stmt)
            # Safe column additions if tables pre-existed
            for col_sql in [
                "ALTER TABLE ai_runs ADD COLUMN execution_class TEXT NOT NULL DEFAULT 'INTERACTIVE'",
                "ALTER TABLE ai_runs ADD COLUMN prompt_id TEXT",
                "ALTER TABLE ai_runs ADD COLUMN prompt_version TEXT",
                "ALTER TABLE ai_runs ADD COLUMN prompt_hash TEXT",
                "ALTER TABLE ai_steps ADD COLUMN prompt_id TEXT",
                "ALTER TABLE ai_steps ADD COLUMN prompt_version TEXT",
                "ALTER TABLE ai_steps ADD COLUMN prompt_hash TEXT",
            ]:
                try:
                    conn.execute(col_sql)
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Mapping Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _row_to_run(row: Any) -> AIRun:
        data: Dict[str, Any] = dict(row)
        error = json.loads(data["error_json"]) if data.get("error_json") else None
        usage = json.loads(data["usage_json"]) if data.get("usage_json") else {}
        cost = json.loads(data["cost_json"]) if data.get("cost_json") else {"estimated_cost": "0.00"}
        return AIRun(
            run_id=data["run_id"],
            workspace_id=data["workspace_id"],
            project_id=data.get("project_id"),
            session_id=data.get("session_id"),
            status=AIRunStatus(data["status"]),
            capability=CapabilityTypeEnum(data["capability"]),
            workflow_ref=data.get("workflow_ref"),
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            usage=UsageRecord.model_validate(usage),
            cost=CostEstimate.model_validate(cost),
            error=AIError.model_validate(error) if error else None,
            contract_version=data.get("contract_version", "1.0.0"),
            execution_class=ExecutionClass(data.get("execution_class", "INTERACTIVE")),
            prompt_id=data.get("prompt_id"),
            prompt_version=data.get("prompt_version"),
            prompt_hash=data.get("prompt_hash"),
        )

    @staticmethod
    def _row_to_step(row: Any) -> AIStep:
        data: Dict[str, Any] = dict(row)
        error = json.loads(data["error_json"]) if data.get("error_json") else None
        usage = json.loads(data["usage_json"]) if data.get("usage_json") else {}
        cost = json.loads(data["cost_json"]) if data.get("cost_json") else {"estimated_cost": "0.00"}
        deps = json.loads(data["dependencies_json"]) if data.get("dependencies_json") else []

        return AIStep(
            step_id=data["step_id"],
            run_id=data["run_id"],
            status=AIStepStatus(data["status"]),
            attempt=data["attempt"],
            capability=CapabilityTypeEnum(data["capability"]),
            input_ref=data.get("input_ref"),
            output_ref=data.get("output_ref"),
            provider=data.get("provider"),
            model=data.get("model"),
            usage=UsageRecord.model_validate(usage),
            cost=CostEstimate.model_validate(cost),
            error=AIError.model_validate(error) if error else None,
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            worker_id=data.get("worker_id"),
            lease_token=data.get("lease_token"),
            lease_expires_at=data.get("lease_expires_at"),
            heartbeat_at=data.get("heartbeat_at"),
            input_hash=data.get("input_hash"),
            idempotency_key=data.get("idempotency_key"),
            dependencies=deps,
            max_attempts=data.get("max_attempts", 3),
            next_retry_at=data.get("next_retry_at"),
            prompt_id=data.get("prompt_id"),
            prompt_version=data.get("prompt_version"),
            prompt_hash=data.get("prompt_hash"),
        )

    @staticmethod
    def _row_to_activity(row: Any) -> AIActivityRecord:
        data: Dict[str, Any] = dict(row)
        error = json.loads(data["error_json"]) if data.get("error_json") else None
        usage = json.loads(data["usage_json"]) if data.get("usage_json") else None
        cost = json.loads(data["cost_json"]) if data.get("cost_json") else None
        return AIActivityRecord(
            activity_id=data["activity_id"],
            run_id=data["run_id"],
            step_id=data["step_id"],
            idempotency_key=data["idempotency_key"],
            status=ActivityStatus(data["status"]),
            semantics=IdempotencySemantics(data["semantics"]),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            provider=data.get("provider"),
            model=data.get("model"),
            remote_operation_ref=data.get("remote_operation_ref"),
            output_ref=data.get("output_ref"),
            error=AIError.model_validate(error) if error else None,
            cost=CostEstimate.model_validate(cost) if cost else None,
            usage=UsageRecord.model_validate(usage) if usage else None,
            cost_settled=bool(data.get("cost_settled", 0)),
            reservation_id=data.get("reservation_id"),
            created_at=data["created_at"],
        )

    # -------------------------------------------------------------------------
    # AIRun Operations
    # -------------------------------------------------------------------------

    def create_run(self, run: AIRun) -> AIRun:
        usage_json = json.dumps(run.usage.model_dump(mode="json"))
        cost_json = json.dumps(run.cost.model_dump(mode="json"))
        error_json = json.dumps(run.error.model_dump(mode="json")) if run.error else None

        with self.engine.transaction("IMMEDIATE") as conn:
            conn.execute(
                """
                INSERT INTO ai_runs (
                    run_id, workspace_id, project_id, session_id,
                    status, capability, workflow_ref, created_at,
                    started_at, completed_at, usage_json, cost_json,
                    error_json, contract_version, execution_class,
                    prompt_id, prompt_version, prompt_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.workspace_id,
                    run.project_id,
                    run.session_id,
                    run.status.value,
                    run.capability.value,
                    run.workflow_ref,
                    run.created_at.isoformat(),
                    run.started_at.isoformat() if run.started_at else None,
                    run.completed_at.isoformat() if run.completed_at else None,
                    usage_json,
                    cost_json,
                    error_json,
                    run.contract_version,
                    run.execution_class.value,
                    run.prompt_id,
                    run.prompt_version,
                    run.prompt_hash,
                ),
            )
        return run

    def get_run(self, run_id: str, workspace_id: Optional[str] = None) -> Optional[AIRun]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute("SELECT * FROM ai_runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                return None
            run = self._row_to_run(row)
            if workspace_id and run.workspace_id != workspace_id:
                raise TenantAccessDeniedError(
                    f"Access denied: AIRun '{run_id}' belongs to workspace '{run.workspace_id}', not '{workspace_id}'."
                )
            return run
        finally:
            conn.close()

    def update_run(self, run: AIRun) -> AIRun:
        existing = self.get_run(run.run_id)
        if not existing:
            raise RunNotFoundError(f"AIRun '{run.run_id}' not found.")

        AIRunStateMachine.validate_transition(existing.status, run.status)

        usage_json = json.dumps(run.usage.model_dump(mode="json"))
        cost_json = json.dumps(run.cost.model_dump(mode="json"))
        error_json = json.dumps(run.error.model_dump(mode="json")) if run.error else None

        with self.engine.transaction("IMMEDIATE") as conn:
            conn.execute(
                """
                UPDATE ai_runs
                SET status = ?,
                    started_at = ?,
                    completed_at = ?,
                    usage_json = ?,
                    cost_json = ?,
                    error_json = ?,
                    execution_class = COALESCE(?, execution_class),
                    prompt_id = COALESCE(?, prompt_id),
                    prompt_version = COALESCE(?, prompt_version),
                    prompt_hash = COALESCE(?, prompt_hash)
                WHERE run_id = ?
                """,
                (
                    run.status.value,
                    run.started_at.isoformat() if run.started_at else None,
                    run.completed_at.isoformat() if run.completed_at else None,
                    usage_json,
                    cost_json,
                    error_json,
                    run.execution_class.value if run.execution_class else None,
                    run.prompt_id,
                    run.prompt_version,
                    run.prompt_hash,
                    run.run_id,
                ),
            )
        return run

    # -------------------------------------------------------------------------
    # AIStep Operations
    # -------------------------------------------------------------------------

    def create_steps(self, steps: List[AIStep]) -> List[AIStep]:
        if not steps:
            return []

        # Find workspace_id from run
        run = self.get_run(steps[0].run_id)
        if not run:
            raise RunNotFoundError(f"Parent AIRun '{steps[0].run_id}' not found.")
        ws_id = run.workspace_id

        with self.engine.transaction("IMMEDIATE") as conn:
            for step in steps:
                usage_json = json.dumps(step.usage.model_dump(mode="json"))
                cost_json = json.dumps(step.cost.model_dump(mode="json"))
                error_json = json.dumps(step.error.model_dump(mode="json")) if step.error else None
                deps_json = json.dumps(step.dependencies)

                conn.execute(
                    """
                    INSERT INTO ai_steps (
                        step_id, run_id, workspace_id, status, attempt,
                        capability, input_ref, output_ref, provider,
                        model, usage_json, cost_json, error_json,
                        created_at, started_at, completed_at, worker_id,
                        lease_token, lease_acquired_at, lease_expires_at,
                        heartbeat_at, input_hash, idempotency_key,
                        dependencies_json, max_attempts, next_retry_at,
                        prompt_id, prompt_version, prompt_hash
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        step.step_id,
                        step.run_id,
                        ws_id,
                        step.status.value,
                        step.attempt,
                        step.capability.value,
                        step.input_ref,
                        step.output_ref,
                        step.provider,
                        step.model,
                        usage_json,
                        cost_json,
                        error_json,
                        step.created_at.isoformat(),
                        step.started_at.isoformat() if step.started_at else None,
                        step.completed_at.isoformat() if step.completed_at else None,
                        step.worker_id,
                        step.lease_token,
                        step.lease_expires_at.isoformat() if step.lease_expires_at else None,
                        step.lease_expires_at.isoformat() if step.lease_expires_at else None,
                        step.heartbeat_at.isoformat() if step.heartbeat_at else None,
                        step.input_hash,
                        step.idempotency_key,
                        deps_json,
                        step.max_attempts,
                        step.next_retry_at.isoformat() if step.next_retry_at else None,
                        step.prompt_id,
                        step.prompt_version,
                        step.prompt_hash,
                    ),
                )
        return steps

    def get_step(self, step_id: str, workspace_id: Optional[str] = None) -> Optional[AIStep]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute("SELECT * FROM ai_steps WHERE step_id = ?", (step_id,))
            row = cur.fetchone()
            if not row:
                return None
            step = self._row_to_step(row)
            if workspace_id and row["workspace_id"] != workspace_id:
                raise TenantAccessDeniedError(
                    f"Access denied: AIStep '{step_id}' belongs to workspace '{row['workspace_id']}', not '{workspace_id}'."
                )
            return step
        finally:
            conn.close()

    def get_steps_for_run(self, run_id: str, workspace_id: Optional[str] = None) -> List[AIStep]:
        if workspace_id:
            run = self.get_run(run_id, workspace_id=workspace_id)
            if not run:
                raise RunNotFoundError(f"AIRun '{run_id}' not found in workspace '{workspace_id}'.")

        conn = self.engine.get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM ai_steps WHERE run_id = ? ORDER BY created_at ASC, step_id ASC",
                (run_id,),
            )
            rows = cur.fetchall()
            return [self._row_to_step(r) for r in rows]
        finally:
            conn.close()

    def update_step(self, step: AIStep) -> AIStep:
        existing = self.get_step(step.step_id)
        if not existing:
            raise StepNotFoundError(f"AIStep '{step.step_id}' not found.")

        AIStepStateMachine.validate_transition(existing.status, step.status)

        usage_json = json.dumps(step.usage.model_dump(mode="json"))
        cost_json = json.dumps(step.cost.model_dump(mode="json"))
        error_json = json.dumps(step.error.model_dump(mode="json")) if step.error else None
        deps_json = json.dumps(step.dependencies)

        with self.engine.transaction("IMMEDIATE") as conn:
            conn.execute(
                """
                UPDATE ai_steps
                SET status = ?,
                    attempt = ?,
                    output_ref = ?,
                    provider = ?,
                    model = ?,
                    usage_json = ?,
                    cost_json = ?,
                    error_json = ?,
                    started_at = ?,
                    completed_at = ?,
                    worker_id = ?,
                    lease_token = ?,
                    lease_expires_at = ?,
                    heartbeat_at = ?,
                    dependencies_json = ?,
                    max_attempts = ?,
                    next_retry_at = ?,
                    prompt_id = COALESCE(?, prompt_id),
                    prompt_version = COALESCE(?, prompt_version),
                    prompt_hash = COALESCE(?, prompt_hash)
                WHERE step_id = ?
                """,
                (
                    step.status.value,
                    step.attempt,
                    step.output_ref,
                    step.provider,
                    step.model,
                    usage_json,
                    cost_json,
                    error_json,
                    step.started_at.isoformat() if step.started_at else None,
                    step.completed_at.isoformat() if step.completed_at else None,
                    step.worker_id,
                    step.lease_token,
                    step.lease_expires_at.isoformat() if step.lease_expires_at else None,
                    step.heartbeat_at.isoformat() if step.heartbeat_at else None,
                    deps_json,
                    step.max_attempts,
                    step.next_retry_at.isoformat() if step.next_retry_at else None,
                    step.prompt_id,
                    step.prompt_version,
                    step.prompt_hash,
                    step.step_id,
                ),
            )
        return step

    # -------------------------------------------------------------------------
    # Worker Lease Operations & Atomic Claims
    # -------------------------------------------------------------------------

    def claim_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        lease_duration_seconds: float,
        workspace_id: Optional[str] = None,
    ) -> Optional[AIStep]:
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        from datetime import timedelta
        expires_dt = now_dt + timedelta(seconds=lease_duration_seconds)
        expires_iso = expires_dt.isoformat()

        with self.engine.transaction("IMMEDIATE") as conn:
            # 1. Atomic compare-and-swap claim
            if workspace_id:
                cur = conn.execute(
                    """
                    UPDATE ai_steps
                    SET status = 'RUNNING',
                        worker_id = ?,
                        lease_token = ?,
                        lease_acquired_at = ?,
                        lease_expires_at = ?,
                        heartbeat_at = ?,
                        started_at = COALESCE(started_at, ?)
                    WHERE step_id = ?
                      AND workspace_id = ?
                      AND (
                          status = 'PENDING'
                          OR (status = 'RUNNING' AND lease_expires_at < ?)
                      )
                    """,
                    (
                        worker_id,
                        lease_token,
                        now_iso,
                        expires_iso,
                        now_iso,
                        now_iso,
                        step_id,
                        workspace_id,
                        now_iso,
                    ),
                )
            else:
                cur = conn.execute(
                    """
                    UPDATE ai_steps
                    SET status = 'RUNNING',
                        worker_id = ?,
                        lease_token = ?,
                        lease_acquired_at = ?,
                        lease_expires_at = ?,
                        heartbeat_at = ?,
                        started_at = COALESCE(started_at, ?)
                    WHERE step_id = ?
                      AND (
                          status = 'PENDING'
                          OR (status = 'RUNNING' AND lease_expires_at < ?)
                      )
                    """,
                    (
                        worker_id,
                        lease_token,
                        now_iso,
                        expires_iso,
                        now_iso,
                        now_iso,
                        step_id,
                        now_iso,
                    ),
                )

            if cur.rowcount == 0:
                return None  # Step already claimed, not runnable, or lease not expired

            # 2. Fetch updated step record
            fetch_cur = conn.execute("SELECT * FROM ai_steps WHERE step_id = ?", (step_id,))
            row = fetch_cur.fetchone()
            if not row:
                return None
            step = self._row_to_step(row)

            # 3. Update parent run from PENDING to RUNNING if not already RUNNING
            conn.execute(
                """
                UPDATE ai_runs
                SET status = 'RUNNING',
                    started_at = COALESCE(started_at, ?)
                WHERE run_id = ? AND status = 'PENDING'
                """,
                (now_iso, step.run_id),
            )

            return step

    def renew_lease(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        lease_duration_seconds: float,
    ) -> bool:
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        from datetime import timedelta
        new_expires_iso = (now_dt + timedelta(seconds=lease_duration_seconds)).isoformat()

        with self.engine.transaction("IMMEDIATE") as conn:
            cur = conn.execute(
                """
                UPDATE ai_steps
                SET heartbeat_at = ?,
                    lease_expires_at = ?
                WHERE step_id = ?
                  AND status = 'RUNNING'
                  AND worker_id = ?
                  AND lease_token = ?
                  AND lease_expires_at >= ?
                """,
                (
                    now_iso,
                    new_expires_iso,
                    step_id,
                    worker_id,
                    lease_token,
                    now_iso,
                ),
            )
            return cur.rowcount == 1

    def complete_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        output_ref: Optional[str],
        usage: UsageRecord,
        cost: CostEstimate,
    ) -> AIStep:
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        usage_json = json.dumps(usage.model_dump(mode="json"))
        cost_json = json.dumps(cost.model_dump(mode="json"))

        with self.engine.transaction("IMMEDIATE") as conn:
            # Check existence and lease match
            cur = conn.execute("SELECT * FROM ai_steps WHERE step_id = ?", (step_id,))
            row = cur.fetchone()
            if not row:
                raise StepNotFoundError(f"AIStep '{step_id}' not found.")

            step_data = dict(row)
            if (
                step_data.get("worker_id") != worker_id
                or step_data.get("lease_token") != lease_token
            ):
                raise StaleWorkerLeaseError(
                    f"Stale worker commit rejected: Worker '{worker_id}' with token '{lease_token}' "
                    f"does not match active lease holder '{step_data.get('worker_id')}' / '{step_data.get('lease_token')}'."
                )

            lease_exp = step_data.get("lease_expires_at")
            if lease_exp and lease_exp < now_iso:
                raise StaleWorkerLeaseError(
                    f"Stale worker commit rejected: Lease for worker '{worker_id}' expired at '{lease_exp}' (current: '{now_iso}')."
                )

            if step_data["status"] != AIStepStatus.RUNNING.value:
                raise StaleWorkerLeaseError(
                    f"Cannot complete step '{step_id}': status is '{step_data['status']}', expected 'RUNNING'."
                )

            conn.execute(
                """
                UPDATE ai_steps
                SET status = 'SUCCEEDED',
                    completed_at = ?,
                    output_ref = ?,
                    usage_json = ?,
                    cost_json = ?,
                    lease_token = NULL,
                    lease_expires_at = NULL
                WHERE step_id = ?
                  AND status = 'RUNNING'
                  AND worker_id = ?
                  AND lease_token = ?
                """,
                (
                    now_iso,
                    output_ref,
                    usage_json,
                    cost_json,
                    step_id,
                    worker_id,
                    lease_token,
                ),
            )

            # Return updated step
            updated_cur = conn.execute("SELECT * FROM ai_steps WHERE step_id = ?", (step_id,))
            return self._row_to_step(updated_cur.fetchone())

    def fail_step(
        self,
        step_id: str,
        worker_id: str,
        lease_token: str,
        error: AIError,
        next_status: AIStepStatus,
        next_retry_at: Optional[datetime] = None,
    ) -> AIStep:
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        error_json = json.dumps(error.model_dump(mode="json"))

        with self.engine.transaction("IMMEDIATE") as conn:
            cur = conn.execute("SELECT * FROM ai_steps WHERE step_id = ?", (step_id,))
            row = cur.fetchone()
            if not row:
                raise StepNotFoundError(f"AIStep '{step_id}' not found.")

            step_data = dict(row)
            if (
                step_data.get("worker_id") != worker_id
                or step_data.get("lease_token") != lease_token
            ):
                raise StaleWorkerLeaseError(
                    f"Stale worker fail rejected: Worker '{worker_id}' does not hold active lease."
                )

            # Update step
            conn.execute(
                """
                UPDATE ai_steps
                SET status = ?,
                    completed_at = (CASE WHEN ? = 'FAILED' THEN ? ELSE completed_at END),
                    attempt = (CASE WHEN ? = 'PENDING' THEN attempt + 1 ELSE attempt END),
                    error_json = ?,
                    next_retry_at = ?,
                    worker_id = NULL,
                    lease_token = NULL,
                    lease_expires_at = NULL
                WHERE step_id = ?
                """,
                (
                    next_status.value,
                    next_status.value,
                    now_iso,
                    next_status.value,
                    error_json,
                    next_retry_at.isoformat() if next_retry_at else None,
                    step_id,
                ),
            )

            updated_cur = conn.execute("SELECT * FROM ai_steps WHERE step_id = ?", (step_id,))
            return self._row_to_step(updated_cur.fetchone())

    def list_runnable_steps(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[AIStep]:
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.engine.get_connection()
        try:
            query = """
                SELECT * FROM ai_steps
                WHERE (
                    status = 'PENDING'
                    AND (next_retry_at IS NULL OR next_retry_at <= ?)
                )
                OR (
                    status = 'RUNNING'
                    AND lease_expires_at < ?
                )
            """
            params: List[Any] = [now_iso, now_iso]

            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)

            query += " ORDER BY created_at ASC LIMIT ?"
            params.append(limit)

            cur = conn.execute(query, tuple(params))
            rows = cur.fetchall()
            return [self._row_to_step(r) for r in rows]
        finally:
            conn.close()

    def list_expired_steps(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[AIStep]:
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.engine.get_connection()
        try:
            query = "SELECT * FROM ai_steps WHERE status = 'RUNNING' AND lease_expires_at < ?"
            params: List[Any] = [now_iso]
            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)
            query += " ORDER BY created_at ASC"
            cur = conn.execute(query, tuple(params))
            return [self._row_to_step(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def list_active_runs(
        self,
        workspace_id: Optional[str] = None,
    ) -> List[AIRun]:
        conn = self.engine.get_connection()
        try:
            query = "SELECT * FROM ai_runs WHERE status IN ('PENDING', 'RUNNING')"
            params: List[Any] = []
            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)
            query += " ORDER BY created_at ASC"
            cur = conn.execute(query, tuple(params))
            return [self._row_to_run(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def cancel_run(
        self,
        run_id: str,
        workspace_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AIRun:
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        cancellation_error = AIError.cancelled(
            message=reason or f"AIRun '{run_id}' was cancelled by tenant request.",
        )
        error_json = json.dumps(cancellation_error.model_dump(mode="json"))

        with self.engine.transaction("IMMEDIATE") as conn:
            cur = conn.execute("SELECT * FROM ai_runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                raise RunNotFoundError(f"AIRun '{run_id}' not found.")

            run_data = dict(row)
            if workspace_id and run_data["workspace_id"] != workspace_id:
                raise TenantAccessDeniedError(
                    f"Access denied: AIRun '{run_id}' belongs to workspace '{run_data['workspace_id']}'."
                )

            current_status = AIRunStatus(run_data["status"])
            if current_status in {AIRunStatus.SUCCEEDED, AIRunStatus.FAILED, AIRunStatus.CANCELLED}:
                raise RunAlreadyTerminalError(
                    f"Cannot cancel AIRun '{run_id}' in terminal state '{current_status.value}'."
                )

            # 1. Update run
            conn.execute(
                """
                UPDATE ai_runs
                SET status = 'CANCELLED',
                    completed_at = ?,
                    error_json = ?
                WHERE run_id = ?
                """,
                (now_iso, error_json, run_id),
            )

            # 2. Cancel non-terminal steps
            conn.execute(
                """
                UPDATE ai_steps
                SET status = 'CANCELLED',
                    completed_at = ?,
                    error_json = ?,
                    worker_id = NULL,
                    lease_token = NULL,
                    lease_expires_at = NULL
                WHERE run_id = ?
                  AND status IN ('WAITING', 'PENDING', 'RUNNING')
                """,
                (now_iso, error_json, run_id),
            )

            # 3. Cancel non-terminal activities
            conn.execute(
                """
                UPDATE ai_activities
                SET status = 'CANCELLED',
                    completed_at = ?,
                    error_json = ?
                WHERE run_id = ?
                  AND status IN ('PENDING', 'RUNNING')
                """,
                (now_iso, error_json, run_id),
            )

            updated_run_cur = conn.execute("SELECT * FROM ai_runs WHERE run_id = ?", (run_id,))
            return self._row_to_run(updated_run_cur.fetchone())

    # -------------------------------------------------------------------------
    # Durable Activity Boundary (S27.11 / AI-10B)
    # -------------------------------------------------------------------------

    def record_activity_intent(
        self,
        activity: AIActivityRecord,
        workspace_id: str,
    ) -> AIActivityRecord:
        with self.engine.transaction("IMMEDIATE") as conn:
            # 1. Check if exists for (workspace_id, step_id, idempotency_key)
            cur = conn.execute(
                """
                SELECT * FROM ai_activities
                WHERE workspace_id = ? AND step_id = ? AND idempotency_key = ?
                """,
                (workspace_id, activity.step_id, activity.idempotency_key),
            )
            row = cur.fetchone()
            if row:
                return self._row_to_activity(row)

            # 2. Check if exists for (workspace_id, idempotency_key) across steps/runs (shared logical execution)
            cur = conn.execute(
                """
                SELECT * FROM ai_activities
                WHERE workspace_id = ? AND idempotency_key = ?
                ORDER BY created_at ASC LIMIT 1
                """,
                (workspace_id, activity.idempotency_key),
            )
            row = cur.fetchone()
            if row:
                return self._row_to_activity(row)

            # Insert intent
            error_json = json.dumps(activity.error.model_dump(mode="json")) if activity.error else None
            cost_json = json.dumps(activity.cost.model_dump(mode="json")) if activity.cost else None
            usage_json = json.dumps(activity.usage.model_dump(mode="json")) if activity.usage else None

            conn.execute(
                """
                INSERT INTO ai_activities (
                    activity_id, run_id, step_id, workspace_id, idempotency_key,
                    status, semantics, started_at, completed_at, provider,
                    model, remote_operation_ref, output_ref, error_json,
                    cost_json, usage_json, cost_settled, reservation_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity.activity_id,
                    activity.run_id,
                    activity.step_id,
                    workspace_id,
                    activity.idempotency_key,
                    activity.status.value,
                    activity.semantics.value,
                    activity.started_at.isoformat() if activity.started_at else None,
                    activity.completed_at.isoformat() if activity.completed_at else None,
                    activity.provider,
                    activity.model,
                    activity.remote_operation_ref,
                    activity.output_ref,
                    error_json,
                    cost_json,
                    usage_json,
                    1 if activity.cost_settled else 0,
                    activity.reservation_id,
                    activity.created_at.isoformat(),
                ),
            )
            return activity

    def get_activity(
        self,
        activity_id: str,
        workspace_id: Optional[str] = None,
    ) -> Optional[AIActivityRecord]:
        conn = self.engine.get_connection()
        try:
            cur = conn.execute("SELECT * FROM ai_activities WHERE activity_id = ?", (activity_id,))
            row = cur.fetchone()
            if not row:
                return None
            activity = self._row_to_activity(row)
            if workspace_id and row["workspace_id"] != workspace_id:
                raise TenantAccessDeniedError(
                    f"Access denied: AIActivityRecord '{activity_id}' belongs to workspace '{row['workspace_id']}', not '{workspace_id}'."
                )
            return activity
        finally:
            conn.close()

    def get_activity_by_idempotency_key(
        self,
        workspace_id: str,
        step_id_or_idem: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        step_id: Optional[str] = None,
    ) -> Optional[AIActivityRecord]:
        actual_step_id = step_id
        actual_idem_key = idempotency_key

        if step_id_or_idem is not None:
            if idempotency_key is not None:
                actual_step_id = step_id_or_idem
                actual_idem_key = idempotency_key
            else:
                actual_idem_key = step_id_or_idem

        if not actual_idem_key:
            return None

        conn = self.engine.get_connection()
        try:
            if actual_step_id:
                cur = conn.execute(
                    """
                    SELECT * FROM ai_activities
                    WHERE workspace_id = ? AND step_id = ? AND idempotency_key = ?
                    """,
                    (workspace_id, actual_step_id, actual_idem_key),
                )
                row = cur.fetchone()
                if row:
                    return self._row_to_activity(row)

            cur = conn.execute(
                """
                SELECT * FROM ai_activities
                WHERE workspace_id = ? AND idempotency_key = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (workspace_id, actual_idem_key),
            )
            row = cur.fetchone()
            return self._row_to_activity(row) if row else None
        finally:
            conn.close()

    def get_activities_for_step(
        self,
        step_id: str,
        workspace_id: Optional[str] = None,
    ) -> List[AIActivityRecord]:
        conn = self.engine.get_connection()
        try:
            query = "SELECT * FROM ai_activities WHERE step_id = ?"
            params: List[Any] = [step_id]
            if workspace_id:
                query += " AND workspace_id = ?"
                params.append(workspace_id)
            query += " ORDER BY created_at ASC"
            cur = conn.execute(query, tuple(params))
            return [self._row_to_activity(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def update_activity(
        self,
        activity: AIActivityRecord,
        workspace_id: Optional[str] = None,
    ) -> AIActivityRecord:
        existing = self.get_activity(activity.activity_id, workspace_id=workspace_id)
        if not existing:
            raise ActivityNotFoundError(f"AIActivityRecord '{activity.activity_id}' not found.")

        error_json = json.dumps(activity.error.model_dump(mode="json")) if activity.error else None
        cost_json = json.dumps(activity.cost.model_dump(mode="json")) if activity.cost else None
        usage_json = json.dumps(activity.usage.model_dump(mode="json")) if activity.usage else None

        with self.engine.transaction("IMMEDIATE") as conn:
            conn.execute(
                """
                UPDATE ai_activities
                SET status = ?,
                    semantics = ?,
                    started_at = ?,
                    completed_at = ?,
                    provider = ?,
                    model = ?,
                    remote_operation_ref = ?,
                    output_ref = ?,
                    error_json = ?,
                    cost_json = ?,
                    usage_json = ?,
                    cost_settled = ?,
                    reservation_id = ?
                WHERE activity_id = ?
                """,
                (
                    activity.status.value,
                    activity.semantics.value,
                    activity.started_at.isoformat() if activity.started_at else None,
                    activity.completed_at.isoformat() if activity.completed_at else None,
                    activity.provider,
                    activity.model,
                    activity.remote_operation_ref,
                    activity.output_ref,
                    error_json,
                    cost_json,
                    usage_json,
                    1 if activity.cost_settled else 0,
                    activity.reservation_id,
                    activity.activity_id,
                ),
            )
        return activity

    def mark_activity_completed(
        self,
        activity_id: str,
        output_ref: str,
        usage: UsageRecord,
        cost: CostEstimate,
        remote_op_ref: Optional[str] = None,
    ) -> AIActivityRecord:
        now_iso = datetime.now(timezone.utc).isoformat()
        usage_json = json.dumps(usage.model_dump(mode="json"))
        cost_json = json.dumps(cost.model_dump(mode="json"))

        with self.engine.transaction("IMMEDIATE") as conn:
            cur = conn.execute("SELECT * FROM ai_activities WHERE activity_id = ?", (activity_id,))
            row = cur.fetchone()
            if not row:
                raise ActivityNotFoundError(f"AIActivityRecord '{activity_id}' not found.")

            conn.execute(
                """
                UPDATE ai_activities
                SET status = 'SUCCEEDED',
                    completed_at = ?,
                    output_ref = ?,
                    usage_json = ?,
                    cost_json = ?,
                    remote_operation_ref = COALESCE(?, remote_operation_ref),
                    error_json = NULL
                WHERE activity_id = ?
                """,
                (now_iso, output_ref, usage_json, cost_json, remote_op_ref, activity_id),
            )

            updated = conn.execute("SELECT * FROM ai_activities WHERE activity_id = ?", (activity_id,)).fetchone()
            return self._row_to_activity(updated)

    def mark_activity_failed(
        self,
        activity_id: str,
        error: AIError,
    ) -> AIActivityRecord:
        now_iso = datetime.now(timezone.utc).isoformat()
        error_json = json.dumps(error.model_dump(mode="json"))

        with self.engine.transaction("IMMEDIATE") as conn:
            cur = conn.execute("SELECT * FROM ai_activities WHERE activity_id = ?", (activity_id,))
            row = cur.fetchone()
            if not row:
                raise ActivityNotFoundError(f"AIActivityRecord '{activity_id}' not found.")

            conn.execute(
                """
                UPDATE ai_activities
                SET status = 'FAILED',
                    completed_at = ?,
                    error_json = ?
                WHERE activity_id = ?
                """,
                (now_iso, error_json, activity_id),
            )

            updated = conn.execute("SELECT * FROM ai_activities WHERE activity_id = ?", (activity_id,)).fetchone()
            return self._row_to_activity(updated)

    def mark_cost_settled(self, activity_id: str) -> bool:
        with self.engine.transaction("IMMEDIATE") as conn:
            cur = conn.execute(
                """
                UPDATE ai_activities
                SET cost_settled = 1
                WHERE activity_id = ? AND cost_settled = 0
                """,
                (activity_id,),
            )
            return cur.rowcount == 1

