"""
ai/tools/dispatcher.py
======================
Deterministic Tool Dispatcher and policy enforcer for AI Tool execution (S27.9).

Execution Flow:
1. Tool lookup in canonical ToolRegistry
2. Tool enabled validation
3. Input contract schema validation
4. Server-side authorization & cross-tenant isolation enforcement
5. Bounded timeout execution of domain tool adapter
6. Output contract schema validation
7. Structured audit emission
8. Production of canonical, client-safe ToolResult
"""

from __future__ import annotations

import asyncio
import inspect
import time
from datetime import datetime, timezone
from typing import Optional
from pydantic import ValidationError

from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.tools import ToolCall, ToolCallStatus, ToolResult
from ai.tools.audit import ToolAuditRecord, ToolAuditRecorder, default_audit_recorder
from ai.tools.authorization import ToolAuthorizationPolicy
from ai.tools.contracts import ToolDefinition
from ai.tools.errors import (
    DisabledToolError,
    ToolDomainExecutionError,
    ToolInputValidationError,
    ToolOutputValidationError,
    ToolTimeoutError,
    UnknownToolError,
    to_ai_error,
)
from ai.tools.registry import ToolRegistry, default_tool_registry
from ai.tools.types import (
    AuthorizationDecision,
    SideEffectClass,
    TrustedToolExecutionContext,
)


class ToolDispatcher:
    """
    Authoritative boundary orchestrating tool validation, authorization,
    execution, and auditing.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        audit_recorder: Optional[ToolAuditRecorder] = None,
    ):
        self.registry = registry or default_tool_registry
        self.audit_recorder = audit_recorder or default_audit_recorder

    async def dispatch_async(
        self,
        call: ToolCall,
        context: TrustedToolExecutionContext,
    ) -> ToolResult:
        """
        Asynchronously executes an authorized tool call through the canonical pipeline.
        """
        start_time = datetime.now(timezone.utc)
        start_mono = time.monotonic()
        target_resource: Optional[str] = None
        side_effect = SideEffectClass.READ_ONLY
        tool_version = "1.0.0"

        def _make_error_result(
            err: AIError,
            decision: AuthorizationDecision,
            status_code: Optional[str] = None,
        ) -> ToolResult:
            completed_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            
            # Emit audit record
            self.audit_recorder.record(
                ToolAuditRecord(
                    tool_name=call.tool_name,
                    tool_version=tool_version,
                    actor_id=context.actor_id,
                    workspace_id=context.workspace_id,
                    target_resource=target_resource,
                    decision=decision,
                    side_effect_class=side_effect,
                    timestamp=start_time,
                    correlation_id=context.correlation_id,
                    status=ToolCallStatus.ERROR,
                    duration_ms=duration_ms,
                    error_code=status_code or err.code.value if hasattr(err.code, "value") else str(err.code),
                )
            )

            return ToolResult(
                call_id=call.call_id,
                status=ToolCallStatus.ERROR,
                output=None,
                error=err,
                started_at=start_time,
                completed_at=completed_time,
                duration_ms=duration_ms,
            )

        # 1. Lookup Tool Definition
        reg = self.registry.get(call.tool_name)
        if reg is None:
            return _make_error_result(
                to_ai_error(UnknownToolError(call.tool_name)),
                decision=AuthorizationDecision.DENY_POLICY,
            )

        tool_def: ToolDefinition = reg.definition
        tool_version = tool_def.version
        side_effect = tool_def.side_effect_class

        # 2. Check Tool Enabled State
        if not tool_def.enabled:
            return _make_error_result(
                to_ai_error(DisabledToolError(call.tool_name)),
                decision=AuthorizationDecision.DENY_TOOL_DISABLED,
            )

        # 3. Input Schema Validation
        try:
            validated_input = tool_def.input_contract.model_validate(call.parameters)
        except ValidationError as val_err:
            err_msg = "; ".join(f"{e['loc']}: {e['msg']}" for e in val_err.errors())
            return _make_error_result(
                to_ai_error(ToolInputValidationError(call.tool_name, err_msg)),
                decision=AuthorizationDecision.DENY_POLICY,
            )

        # Extract target resource if available for security auditing
        target_resource = getattr(validated_input, "project_id", None)

        # 4. Server-Side Authorization & Isolation Policy
        auth_decision = ToolAuthorizationPolicy.authorize(tool_def, context, validated_input)
        if not auth_decision.allowed:
            err = AIError(
                code=auth_decision.error_code or AIErrorCode.POLICY_DENIED,
                message=auth_decision.reason or "Authorization denied by server-side policy.",
                retryable=False,
                details={
                    "tool_name": call.tool_name,
                    "actor_id": context.actor_id,
                    "workspace_id": context.workspace_id,
                    "target_resource": target_resource,
                }
            )
            return _make_error_result(
                err,
                decision=auth_decision.decision,
                status_code=auth_decision.error_code.value if hasattr(auth_decision.error_code, "value") else str(auth_decision.error_code),
            )

        # 5. Bounded Timeout Execution of Domain Tool Adapter
        adapter_res = None
        exec_context = context.with_timeout(tool_def.timeout_seconds)
        try:
            adapter = reg.adapter
            timeout_sec = tool_def.timeout_seconds

            if inspect.iscoroutinefunction(adapter):
                adapter_coro = adapter(validated_input, exec_context)
                adapter_res = await asyncio.wait_for(adapter_coro, timeout=timeout_sec)
            else:
                # Synchronous adapter: execute in thread pool to prevent blocking event loop
                func = lambda: adapter(validated_input, exec_context)
                loop = asyncio.get_running_loop()
                adapter_res = await asyncio.wait_for(loop.run_in_executor(None, func), timeout=timeout_sec)

        except asyncio.TimeoutError:
            exec_context.cancel()
            return _make_error_result(
                to_ai_error(ToolTimeoutError(call.tool_name, tool_def.timeout_seconds)),
                decision=AuthorizationDecision.ALLOW,
                status_code=AIErrorCode.TIMEOUT.value,
            )
        except Exception as exc:
            exec_context.cancel()
            # Map domain service exceptions to canonical AIError
            return _make_error_result(
                to_ai_error(ToolDomainExecutionError(call.tool_name, str(exc))),
                decision=AuthorizationDecision.ALLOW,
                status_code=AIErrorCode.DEPENDENCY_FAILED.value,
            )

        # 6. Output Schema Validation
        try:
            if isinstance(adapter_res, tool_def.output_contract):
                validated_output = adapter_res
            else:
                validated_output = tool_def.output_contract.model_validate(adapter_res)
        except ValidationError as out_val_err:
            err_msg = "; ".join(f"{e['loc']}: {e['msg']}" for e in out_val_err.errors())
            return _make_error_result(
                to_ai_error(ToolOutputValidationError(call.tool_name, err_msg)),
                decision=AuthorizationDecision.ALLOW,
                status_code=AIErrorCode.SCHEMA_VALIDATION_FAILED.value,
            )

        # 7. Successful Completion & Structured Audit Emission
        completed_time = datetime.now(timezone.utc)
        duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))

        self.audit_recorder.record(
            ToolAuditRecord(
                tool_name=call.tool_name,
                tool_version=tool_version,
                actor_id=context.actor_id,
                workspace_id=context.workspace_id,
                target_resource=target_resource,
                decision=AuthorizationDecision.ALLOW,
                side_effect_class=side_effect,
                timestamp=start_time,
                correlation_id=context.correlation_id,
                status=ToolCallStatus.SUCCESS,
                duration_ms=duration_ms,
                error_code=None,
            )
        )

        return ToolResult(
            call_id=call.call_id,
            status=ToolCallStatus.SUCCESS,
            output=validated_output.model_dump(mode="json"),
            error=None,
            started_at=start_time,
            completed_at=completed_time,
            duration_ms=duration_ms,
        )

    def dispatch(
        self,
        call: ToolCall,
        context: TrustedToolExecutionContext,
    ) -> ToolResult:
        """
        Synchronous entrypoint for tool execution.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If called inside an existing running event loop in a synchronous context, run via new loop in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(lambda: asyncio.run(self.dispatch_async(call, context)))
                return fut.result()
        else:
            return asyncio.run(self.dispatch_async(call, context))
