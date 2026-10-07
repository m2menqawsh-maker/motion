"""
ai/mcp/adapters/base.py
=======================
Base typed adapter for hardened MCP operations (S27.10).

Invariants:
- Strictly no shell=True. Commands must use argument vectors.
- Bounded execution timeouts via asyncio.wait_for.
- All input and output contracts strictly typed.
- Enforces server-side identity and tenant isolation.
- Structured audit record emission on all outcomes.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, TypeVar, Generic, Union
from pydantic import ValidationError

from ai.contracts.base import AIContractModel
from ai.contracts.errors import AIErrorCode
from ai.mcp.audit import MCPAuditRecord, MCPAuditRecorder, default_mcp_audit_recorder
from ai.mcp.catalog import MCPCatalog, default_mcp_catalog
from ai.mcp.contracts import MCPOperationDefinition, MCPServerDefinition
from ai.mcp.errors import (
    MCPError,
    MCPException,
    MCPExecutionError,
    MCPNotFoundError,
    MCPTimeoutError,
)
from ai.mcp.policy import MCPSecurityPolicy

if TYPE_CHECKING:
    from ai.tools.types import TrustedToolExecutionContext


async def run_safe_subprocess(
    cmd: list[str],
    timeout_seconds: Optional[float] = None,
    output_path: Optional[Union[Path, str]] = None,
    grace_period_seconds: float = 0.5,
) -> tuple[str, str]:
    """
    Executes a subprocess safely using argument vector without shell (strictly no shell=True).
    Guarantees cooperative termination (SIGTERM), bounded grace wait, SIGKILL fallback,
    process reaping (no zombies/orphans), and partial output file cleanup on timeout or cancellation.
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out_path = Path(output_path) if output_path else None

    try:
        if timeout_seconds is not None:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout_seconds,
            )
        else:
            stdout, stderr = await proc.communicate()
    except (asyncio.CancelledError, asyncio.TimeoutError):
        # 1. Terminate cooperatively
        if proc.returncode is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass

            # 2. Bounded grace wait
            try:
                await asyncio.wait_for(proc.wait(), timeout=grace_period_seconds)
            except asyncio.TimeoutError:
                # 3. Force kill if still alive
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(proc.wait(), timeout=grace_period_seconds)
                except Exception:
                    pass

        # 4. Partial file cleanup
        if out_path and out_path.exists():
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass

        raise

    out_str = stdout.decode("utf-8", errors="replace")
    err_str = stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        if out_path and out_path.exists():
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
        raise RuntimeError(f"Command failed (code {proc.returncode}): {err_str.strip() or out_str.strip()}")
    return out_str, err_str


InT = TypeVar("InT", bound=AIContractModel)
OutT = TypeVar("OutT", bound=AIContractModel)


class BaseMCPAdapter(Generic[InT, OutT]):
    """
    Hardened execution adapter mediating production AI calls to an MCP operation.
    """
    def __init__(
        self,
        server_id: str,
        operation_name: str,
        catalog: Optional[MCPCatalog] = None,
        audit_recorder: Optional[MCPAuditRecorder] = None,
    ):
        self.server_id = server_id
        self.operation_name = operation_name
        self.catalog = catalog or default_mcp_catalog
        self.audit_recorder = audit_recorder or default_mcp_audit_recorder

        server_def = self.catalog.get_server(self.server_id)
        if not server_def:
            raise MCPNotFoundError(self.server_id)
        self.server_def = server_def

        op_def = self.catalog.get_operation(self.server_id, self.operation_name)
        if not op_def:
            raise MCPNotFoundError(f"{self.server_id}.{self.operation_name}")
        self.op_def = op_def

    async def execute(
        self,
        input_data: InT,
        context: TrustedToolExecutionContext,
    ) -> OutT:
        """
        Executes the operation through security validation, bounded timeout, and audit tracking.
        """
        start_time = datetime.now(timezone.utc)
        start_mono = time.monotonic()
        status = "SUCCESS"
        error_code = None

        try:
            # 1. Server & Operation authorization
            MCPSecurityPolicy.validate_server_access(
                server=self.server_def,
                operation_name=self.operation_name,
                is_production=True,
            )

            # 2. Argument validation & injection prevention
            raw_args = input_data.model_dump()
            MCPSecurityPolicy.validate_arguments(raw_args, context)

            # 3. Bounded execution
            timeout_s = self.op_def.timeout_seconds
            try:
                result = await asyncio.wait_for(
                    self._execute_internal(input_data, context),
                    timeout=timeout_s,
                )
                return result
            except asyncio.TimeoutError:
                status = "TIMEOUT"
                error_code = AIErrorCode.TIMEOUT.value
                out_file = getattr(input_data, "output_path", None)
                if out_file:
                    try:
                        Path(out_file).unlink(missing_ok=True)
                    except Exception:
                        pass
                raise MCPTimeoutError(self.operation_name, timeout_s)

        except MCPException as exc:
            status = "ERROR"
            error_code = exc.code.value if hasattr(exc.code, "value") else str(exc.code)
            raise
        except Exception as exc:
            status = "ERROR"
            error_code = AIErrorCode.DEPENDENCY_FAILED.value
            raise MCPExecutionError(self.operation_name, str(exc)) from exc
        finally:
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            self.audit_recorder.record(
                MCPAuditRecord(
                    server_id=self.server_id,
                    operation_name=self.operation_name,
                    actor_id=context.actor_id,
                    workspace_id=context.workspace_id,
                    target_resource=getattr(input_data, "file_path", None),
                    status=status,
                    duration_ms=duration_ms,
                    timestamp=start_time,
                    error_code=error_code,
                )
            )

    async def _execute_internal(
        self,
        input_data: InT,
        context: TrustedToolExecutionContext,
    ) -> OutT:
        """Abstract execution logic implemented by specific adapters."""
        raise NotImplementedError
