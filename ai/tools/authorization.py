"""
ai/tools/authorization.py
=========================
Authoritative server-side authorization policy for AI Tool invocations (S27.9).

Invariants:
- Absolute Server-Side Authority: Untrusted AI model or ToolCall arguments NEVER grant authority.
- Pre-Execution Enforcement: Authorization checks execute BEFORE any adapter or domain side-effect.
- Zero Side-Effects on Denial: Denied requests abort before touching domain services or state.
- Cross-Tenant Confinement: Prevents cross-workspace resource access and tenant spoofing.
"""

from __future__ import annotations

from typing import Optional

from ai.contracts.base import AIContractModel
from ai.contracts.errors import AIErrorCode
from ai.tools.contracts import ToolDefinition
from ai.tools.types import (
    AuthorizationDecision,
    SideEffectClass,
    ToolAuthorizationResult,
    TrustedToolExecutionContext,
)


class ToolAuthorizationPolicy:
    """
    Canonical evaluator for AI Tool access control and tenant isolation.
    """

    @classmethod
    def authorize(
        cls,
        tool_def: ToolDefinition,
        context: TrustedToolExecutionContext,
        input_data: AIContractModel,
    ) -> ToolAuthorizationResult:
        """
        Evaluates whether context is permitted to execute tool_def with input_data.
        
        Order of evaluation:
        1. Tool Enabled Gate
        2. Authenticated Identity Gate
        3. Action & Side-Effect Permission Gate
        4. Tenant Isolation & Resource Ownership Gate
        """
        # 1. Tool Enabled Gate
        if not tool_def.enabled:
            return ToolAuthorizationResult(
                decision=AuthorizationDecision.DENY_TOOL_DISABLED,
                allowed=False,
                reason=f"Tool '{tool_def.name}' is currently disabled.",
                error_code=AIErrorCode.CAPABILITY_UNAVAILABLE,
            )

        # 2. Authenticated Identity Gate
        if not context.actor_id or context.actor_id == "anonymous":
            return ToolAuthorizationResult(
                decision=AuthorizationDecision.DENY_UNAUTHENTICATED,
                allowed=False,
                reason="Unauthenticated caller cannot execute AI tools.",
                error_code=AIErrorCode.POLICY_DENIED,
            )

        # 3. Action & Side-Effect Permission Gate
        # Admin tools strictly require admin authority
        if tool_def.side_effect_class == SideEffectClass.ADMIN and not context.is_admin:
            return ToolAuthorizationResult(
                decision=AuthorizationDecision.DENY_PERMISSION,
                allowed=False,
                reason=f"Tool '{tool_def.name}' requires administrative role.",
                error_code=AIErrorCode.POLICY_DENIED,
            )

        # Evaluate permission claim
        has_perm = context.has_permission(tool_def.required_permission)
        if not has_perm and not context.is_admin:
            return ToolAuthorizationResult(
                decision=AuthorizationDecision.DENY_PERMISSION,
                allowed=False,
                reason=f"Actor '{context.actor_id}' lacks required permission '{tool_def.required_permission}'.",
                error_code=AIErrorCode.POLICY_DENIED,
            )

        # 4. Tenant Isolation & Resource Ownership Gate
        target_project_id: Optional[str] = getattr(input_data, "project_id", None)
        if target_project_id:
            # 4a. Check caller context accessible projects list
            if not context.can_access_project(target_project_id):
                return ToolAuthorizationResult(
                    decision=AuthorizationDecision.DENY_TENANT,
                    allowed=False,
                    reason=f"Project '{target_project_id}' is outside the authorized project scope for actor '{context.actor_id}'.",
                    error_code=AIErrorCode.TENANT_ACCESS_DENIED,
                )

            # 4b. Authoritative domain resolution and tenant isolation check via ProjectService (Domain boundary)
            from api.services.project_service import ProjectService
            is_accessible, reason = ProjectService.is_project_accessible_by_tenant(
                project_id=target_project_id,
                workspace_id=context.workspace_id,
                is_admin=context.is_admin,
                actor_id=context.actor_id,
            )
            if not is_accessible:
                return ToolAuthorizationResult(
                    decision=AuthorizationDecision.DENY_TENANT,
                    allowed=False,
                    reason=reason or f"Project '{target_project_id}' is not accessible by workspace '{context.workspace_id}'.",
                    error_code=AIErrorCode.TENANT_ACCESS_DENIED,
                )

        # All gates passed -> Authorization granted
        return ToolAuthorizationResult(
            decision=AuthorizationDecision.ALLOW,
            allowed=True,
            reason="Authorization granted by server-side policy.",
            error_code=None,
        )
