"""
ai/skills/context.py
====================
Skill Execution Context and Tool Authorization Enforcement (S28-02).

Guarantees:
- Skill ≠ Permission: A skill cannot grant itself or the model execution authority.
- Mandatory Server-Side Gate: All tool invocations must pass through ToolAuthorizationPolicy.
- Knowledge Authority: Skills resolve required_knowledge via KnowledgeRouter, never raw files.
- Least Privilege: Declaring a tool in allowed_tools does not bypass security or RBAC.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import SkillDefinition
from ai.contracts.errors import AIErrorCode
from ai.knowledge.router import KnowledgeRouter
from ai.skills.contracts import SkillContext
from ai.tools.authorization import ToolAuthorizationPolicy
from ai.tools.contracts import ToolDefinition
from ai.tools.types import (
    SideEffectClass,
    ToolAuthorizationResult,
    TrustedToolExecutionContext,
)


class SkillExecutionError(Exception):
    """Base exception for skill execution errors."""
    pass


class ToolUndeclaredError(SkillExecutionError):
    """Raised when a skill attempts to invoke a tool it did not declare in allowed_tools."""
    pass


class ToolAuthorizationDeniedError(SkillExecutionError):
    """Raised when ToolAuthorizationPolicy denies execution of a tool requested by a skill."""
    pass


class SkillContextBuilder:
    """
    Constructs an authoritative, bounded SkillContext.
    Resolves required_knowledge through KnowledgeRouter to maintain single authority.
    """

    def __init__(self, knowledge_router: KnowledgeRouter) -> None:
        self.knowledge_router = knowledge_router

    def build_context(
        self,
        skill: SkillDefinition,
        creative_context: Optional[Dict[str, JsonValue]] = None,
        audio_mode: Optional[AudioMode] = None,
    ) -> SkillContext:
        """
        Builds a SkillContext resolving any required_knowledge via KnowledgeRouter.
        """
        retrieved_chunks = []
        if skill.required_knowledge:
            k_res = self.knowledge_router.resolve_skill_knowledge(
                skill_id=skill.skill_id,
                required_knowledge_ids=skill.required_knowledge,
                audio_mode=audio_mode,
            )
            retrieved_chunks = k_res.chunks

        return SkillContext(
            skill=skill,
            creative_context=creative_context or {},
            retrieved_knowledge=retrieved_chunks,
            declared_capabilities=skill.required_capabilities,
            declared_tools=skill.allowed_tools,
        )


class SkillExecutor:
    """
    Executes or stages operations for a Skill.
    Enforces the critical architectural invariant: Skill ≠ Permission.
    """

    def __init__(
        self,
        context: SkillContext,
        tool_policy: type[ToolAuthorizationPolicy] = ToolAuthorizationPolicy,
    ) -> None:
        self.context = context
        self.tool_policy = tool_policy

    def authorize_tool_call(
        self,
        tool_def: ToolDefinition,
        exec_context: TrustedToolExecutionContext,
        input_data: AIContractModel,
    ) -> ToolAuthorizationResult:
        """
        Evaluates whether a tool call attempted within this skill context is permitted.
        
        Step 1: Check if skill declared the tool in allowed_tools (Skill need check).
        Step 2: Check server-side ToolAuthorizationPolicy (Server authority gate).
        """
        # Step 1: Skill declared need
        if tool_def.name not in self.context.declared_tools:
            raise ToolUndeclaredError(
                f"Tool '{tool_def.name}' was not declared in allowed_tools for skill '{self.context.skill.skill_id}'."
            )

        # Step 2: Absolute Server-Side Authority
        # Skill declaration NEVER bypasses ToolAuthorizationPolicy!
        auth_result = self.tool_policy.authorize(
            tool_def=tool_def,
            context=exec_context,
            input_data=input_data,
        )

        if not auth_result.allowed:
            raise ToolAuthorizationDeniedError(
                f"Tool '{tool_def.name}' denied by ToolAuthorizationPolicy: {auth_result.reason}"
            )

        return auth_result
