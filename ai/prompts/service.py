"""
ai/prompts/service.py
=====================
Prompt Registry and Authority Service (S27.18).

Invariants:
- All production prompts must be versioned entities referenced by prompt_id + version + hash.
- Business code must never use unversioned random string prompts in production.
- Lifecycle strictly enforced: DRAFT -> TESTING -> PRODUCTION -> RETIRED.
- Promotion from DRAFT directly to PRODUCTION is blocked.
- AI models have zero authority to promote or mutate prompts.
- All versions are strictly immutable.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Dict, List, Optional

from ai.contracts.prompt import (
    InvalidPromptLifecycleTransitionError,
    MissingPromptVariableError,
    PromptContract,
    PromptMetadata,
    PromptNotFoundError,
    PromptRenderRequest,
    PromptRenderResult,
    PromptStatus,
    PromptVersionImmutableError,
    PromptVersionNotFoundError,
    UnauthorizedPromptMutationError,
    PromptEvalGateRejectedError,
)
from ai.prompts.repository import PromptRepository
from scripts.core.ai_prompt_repository import SQLPromptRepository


class PromptService:
    """
    Authoritative domain service for managing prompt lifecycle, resolution, and rendering.
    """

    def __init__(self, repository: Optional[PromptRepository] = None):
        self._repository = repository or SQLPromptRepository()

    def create_prompt(
        self,
        prompt_id: str,
        template: str,
        system_prompt: Optional[str] = None,
        variables: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        author: Optional[str] = None,
        description: Optional[str] = None,
        initial_status: PromptStatus = PromptStatus.DRAFT,
        caller_role: str = "HUMAN_OPERATOR",
    ) -> PromptContract:
        """
        Creates the initial version (v1) of a canonical prompt.
        AI models are forbidden from creating prompts.
        Direct creation as PRODUCTION is forbidden.
        """
        if caller_role.upper() in {"AI_MODEL", "MODEL", "AGENT", "LLM"}:
            raise UnauthorizedPromptMutationError("AI models have zero authority to create or mutate prompts.")

        if initial_status == PromptStatus.PRODUCTION:
            raise InvalidPromptLifecycleTransitionError(
                "Prompts cannot be created directly in PRODUCTION status. Must enter DRAFT or TESTING first."
            )

        content_hash = PromptContract.compute_content_hash(template, system_prompt)
        declared_vars = variables or self._extract_variables(template)

        prompt = PromptContract(
            prompt_id=prompt_id,
            version=1,
            hash=content_hash,
            status=initial_status,
            template=template,
            system_prompt=system_prompt,
            variables=declared_vars,
            created_at=datetime.now(timezone.utc),
            workspace_id=workspace_id,
            metadata=PromptMetadata(
                author=author,
                description=description,
            ),
        )
        return self._repository.save_prompt(prompt)

    def create_version(
        self,
        prompt_id: str,
        template: str,
        system_prompt: Optional[str] = None,
        variables: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        author: Optional[str] = None,
        description: Optional[str] = None,
        caller_role: str = "HUMAN_OPERATOR",
    ) -> PromptContract:
        """
        Creates a new immutable version of an existing prompt (e.g. v2, v3).
        Starts in DRAFT status.
        """
        if caller_role.upper() in {"AI_MODEL", "MODEL", "AGENT", "LLM"}:
            raise UnauthorizedPromptMutationError("AI models have zero authority to create or mutate prompts.")

        versions = self._repository.list_versions(prompt_id, workspace_id)
        if not versions:
            raise PromptNotFoundError(f"Prompt '{prompt_id}' does not exist. Call create_prompt for v1.")

        next_version = max(p.version for p in versions) + 1
        content_hash = PromptContract.compute_content_hash(template, system_prompt)
        declared_vars = variables or self._extract_variables(template)

        prompt = PromptContract(
            prompt_id=prompt_id,
            version=next_version,
            hash=content_hash,
            status=PromptStatus.DRAFT,
            template=template,
            system_prompt=system_prompt,
            variables=declared_vars,
            created_at=datetime.now(timezone.utc),
            workspace_id=workspace_id,
            metadata=PromptMetadata(
                author=author,
                description=description,
            ),
        )
        return self._repository.save_prompt(prompt)

    def promote_prompt(
        self,
        prompt_id: str,
        version: int,
        target_status: PromptStatus,
        workspace_id: Optional[str] = None,
        eval_gate_id: Optional[str] = None,
        eval_quality_score: Optional[float] = None,
        caller_role: str = "HUMAN_OPERATOR",
    ) -> PromptContract:
        """
        Transitions a prompt version through its lifecycle.
        Enforces:
        - AI model caller is rejected.
        - DRAFT -> TESTING is valid.
        - TESTING -> PRODUCTION requires eval_gate_id or eval_quality_score.
        - DRAFT -> PRODUCTION is strictly blocked.
        - PRODUCTION -> RETIRED is valid.
        """
        if caller_role.upper() in {"AI_MODEL", "MODEL", "AGENT", "LLM"}:
            raise UnauthorizedPromptMutationError("AI models have zero authority to promote prompts.")

        current = self._repository.get_prompt(prompt_id, version, workspace_id)
        if not current:
            raise PromptVersionNotFoundError(f"Prompt '{prompt_id}' v{version} not found.")

        # Validate Lifecycle State Machine
        if current.status == target_status:
            return current

        if current.status == PromptStatus.DRAFT:
            if target_status == PromptStatus.PRODUCTION:
                raise InvalidPromptLifecycleTransitionError(
                    f"Direct promotion from DRAFT to PRODUCTION for '{prompt_id}' v{version} is strictly forbidden. "
                    "Prompt must advance to TESTING and pass evaluation gate."
                )
            if target_status not in {PromptStatus.TESTING, PromptStatus.RETIRED}:
                raise InvalidPromptLifecycleTransitionError(
                    f"Cannot transition prompt from DRAFT to {target_status}."
                )

        elif current.status == PromptStatus.TESTING:
            if target_status == PromptStatus.PRODUCTION:
                # Promotion to PRODUCTION requires passing evaluation
                if not eval_gate_id and eval_quality_score is None:
                    raise PromptEvalGateRejectedError(
                        f"Cannot promote prompt '{prompt_id}' v{version} to PRODUCTION without eval_gate_id "
                        "or verified evaluation quality score."
                    )
                if eval_quality_score is not None and eval_quality_score < 0.8:
                    raise PromptEvalGateRejectedError(
                        f"Evaluation quality score {eval_quality_score:.3f} is below the 0.80 minimum threshold."
                    )
            elif target_status not in {PromptStatus.DRAFT, PromptStatus.RETIRED}:
                raise InvalidPromptLifecycleTransitionError(
                    f"Cannot transition prompt from TESTING to {target_status}."
                )

        elif current.status == PromptStatus.PRODUCTION:
            if target_status != PromptStatus.RETIRED:
                raise InvalidPromptLifecycleTransitionError(
                    f"Active PRODUCTION prompt '{prompt_id}' v{version} can only be transitioned to RETIRED."
                )

        elif current.status == PromptStatus.RETIRED:
            raise InvalidPromptLifecycleTransitionError(
                f"RETIRED prompt '{prompt_id}' v{version} cannot be resurrected."
            )

        # If promoting to PRODUCTION, retire any previously active PRODUCTION version
        if target_status == PromptStatus.PRODUCTION:
            existing_prod = self._repository.get_active_production_prompt(prompt_id, workspace_id)
            if existing_prod and existing_prod.version != version:
                self._repository.update_status(
                    prompt_id=prompt_id,
                    version=existing_prod.version,
                    new_status=PromptStatus.RETIRED,
                    workspace_id=workspace_id,
                )

        return self._repository.update_status(
            prompt_id=prompt_id,
            version=version,
            new_status=target_status,
            workspace_id=workspace_id,
        )

    def render_prompt(self, request: PromptRenderRequest) -> PromptRenderResult:
        """
        Resolves prompt and safely interpolates parameters.
        If version is omitted, resolves latest active PRODUCTION version.
        """
        if request.version is not None:
            prompt = self._repository.get_prompt(request.prompt_id, request.version, request.workspace_id)
            if not prompt:
                raise PromptVersionNotFoundError(
                    f"Prompt '{request.prompt_id}' version {request.version} not found."
                )
        else:
            prompt = self._repository.get_active_production_prompt(request.prompt_id, request.workspace_id)
            if not prompt:
                raise PromptNotFoundError(
                    f"No active PRODUCTION version found for prompt '{request.prompt_id}'."
                )

        # Validate that all required template variables are supplied
        missing_vars = [var for var in prompt.variables if var not in request.variables]
        if missing_vars:
            raise MissingPromptVariableError(
                f"Missing required variables for prompt '{prompt.prompt_id}' v{prompt.version}: {missing_vars}"
            )

        rendered_text = self._interpolate(prompt.template, request.variables)
        rendered_system = self._interpolate(prompt.system_prompt, request.variables) if prompt.system_prompt else None

        return PromptRenderResult(
            prompt_id=prompt.prompt_id,
            version=prompt.version,
            hash=prompt.hash,
            rendered_text=rendered_text,
            system_prompt=rendered_system,
            status=prompt.status,
        )

    @staticmethod
    def _extract_variables(template: str) -> List[str]:
        """Extracts {var_name} patterns from template string."""
        return sorted(list(set(re.findall(r"\{([a-zA-Z0-9_]+)\}", template))))

    @staticmethod
    def _interpolate(template: str, variables: Dict[str, JsonValue]) -> str:
        """Performs safe token replacement."""
        res = template
        for k, v in variables.items():
            res = res.replace(f"{{{k}}}", str(v))
        return res
