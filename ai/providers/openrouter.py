"""
ai/providers/openrouter.py
===========================
OpenRouter Development Provider Adapter for S28 (DEV-OPENROUTER).

Invariants:
- Strictly a temporary development gateway for S28 (NOT a final production decision).
- Loads OPENROUTER_API_KEY from environment only (never logs or leaks secret).
- Conforms to canonical AIProvider interface and CapabilityRequest / CapabilityResult contracts.
- Strictly provider-neutral: Domain services never import this adapter directly.
- Development-safe budget controls: hard execution bounds, pre-flight budget checks,
  concurrency limits, and timeout protection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
from pydantic import JsonValue

from ai.contracts.capability import CapabilityRequest, CapabilityResult, CapabilityStatus
from ai.contracts.common import (
    CapabilityType,
    ExecutionClass,
    PrivacyRequirement,
    ProvenanceRecord,
)
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.model import ModelPricing
from ai.contracts.usage import UsageRecord
from ai.providers.base import AIProvider, ProviderDefinition

logger = logging.getLogger("ai.providers.openrouter")

# Default development wire model (cost-effective, multimodal reasoning/planning/vision)
DEFAULT_DEV_WIRE_MODEL = "google/gemini-2.5-flash"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT_SEC = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_MAX_CONCURRENCY = 3
DEFAULT_MAX_SPEND_PER_CALL = Decimal("0.50")


class OpenRouterConfigurationError(Exception):
    """Raised when OpenRouter configuration or environment variables are missing or invalid."""
    pass


def get_openrouter_provider_definition() -> ProviderDefinition:
    """Returns canonical definition for OpenRouter development gateway."""
    return ProviderDefinition(
        provider_id="openrouter",
        display_name="OpenRouter (Development Gateway)",
        supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
        privacy_compliance=PrivacyRequirement.PUBLIC_ALLOWED,
        enabled=True,
        environment="development",
        production_default=False,
        adapter_class="ai.providers.openrouter.OpenRouterProvider",
        description="Development gateway for S28. Production provider selection will happen after S28 benchmarks.",
    )


class OpenRouterProvider(AIProvider):
    """
    OpenRouter integration adapter for development workflows.
    Mediates Canonical CapabilityRequests to OpenRouter's OpenAI-compatible HTTP REST endpoint.
    """

    def __init__(
        self,
        definition: Optional[ProviderDefinition] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_sec: Optional[float] = None,
        max_retries: Optional[int] = None,
        max_concurrency: Optional[int] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        model_registry: Optional[Any] = None,
    ) -> None:
        defn = definition or get_openrouter_provider_definition()
        super().__init__(defn)
        self._explicit_api_key = api_key
        self._base_url = (base_url or os.environ.get("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)).rstrip("/")
        self._timeout_sec = float(timeout_sec or os.environ.get("OPENROUTER_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC)))
        self._max_retries = int(max_retries or os.environ.get("OPENROUTER_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
        concurrency = int(max_concurrency or os.environ.get("OPENROUTER_MAX_CONCURRENCY", str(DEFAULT_MAX_CONCURRENCY)))
        self._semaphore = asyncio.Semaphore(max(1, concurrency))
        self._custom_client = http_client
        self._model_registry = model_registry

    @property
    def api_key(self) -> Optional[str]:
        """
        Loads API key from environment only.
        Never cached in long-lived state or logs.
        """
        if self._explicit_api_key is not None:
            return self._explicit_api_key.strip() if self._explicit_api_key else None
        key = os.environ.get("OPENROUTER_API_KEY")
        if key:
            key = key.strip()
        return key if key else None

    def validate_credentials(self) -> None:
        """Validates that the API key is present in environment without leaking its value."""
        if not self.api_key:
            raise OpenRouterConfigurationError(
                "OPENROUTER_API_KEY is required to enable the OpenRouter development provider."
            )

    def _resolve_wire_model(self, request: CapabilityRequest) -> str:
        """Determines the exact OpenRouter wire model identifier to invoke."""
        # 1. Explicit model in input_data
        if "model" in request.input_data and isinstance(request.input_data["model"], str):
            candidate = request.input_data["model"].strip()
            if candidate and not candidate.startswith("openrouter-dev-"):
                return candidate

        # 2. Model from requirement allowed_models if available
        if request.requirements and hasattr(request.requirements, "allowed_models") and getattr(request.requirements, "allowed_models", None):
            models = getattr(request.requirements, "allowed_models")
            if models and isinstance(models, list):
                first_model = models[0]
                if first_model != "openrouter-dev-model":
                    return first_model

        # 3. Environment override or default development model
        return os.environ.get("OPENROUTER_DEV_MODEL", DEFAULT_DEV_WIRE_MODEL)

    def _format_messages(self, request: CapabilityRequest) -> List[Dict[str, Any]]:
        """Constructs OpenAI-compatible message array from Canonical CapabilityRequest."""
        data = request.input_data
        messages: List[Dict[str, Any]] = []

        # System prompt if specified
        system_prompt = data.get("system_prompt")
        if system_prompt and isinstance(system_prompt, str):
            messages.append({"role": "system", "content": system_prompt})

        # Pre-formatted messages passed directly
        if "messages" in data and isinstance(data["messages"], list):
            for m in data["messages"]:
                if isinstance(m, dict) and "role" in m and "content" in m:
                    messages.append({"role": str(m["role"]), "content": m["content"]})
            return messages

        # Vision handling: multimodal prompt
        if request.capability == CapabilityType.VISION or "image_url" in data or "images" in data:
            prompt_text = str(data.get("prompt") or data.get("text") or "Analyze this image")
            content_parts: List[Dict[str, Any]] = [{"type": "text", "text": prompt_text}]

            # Single image URL
            if "image_url" in data:
                content_parts.append({"type": "image_url", "image_url": {"url": str(data["image_url"])}})

            # Multiple images
            if "images" in data and isinstance(data["images"], list):
                for img in data["images"]:
                    if isinstance(img, str):
                        content_parts.append({"type": "image_url", "image_url": {"url": img}})
                    elif isinstance(img, dict) and "url" in img:
                        content_parts.append({"type": "image_url", "image_url": {"url": str(img["url"])}})

            messages.append({"role": "user", "content": content_parts})
            return messages

        # Standard text/reasoning/planning prompt
        prompt_text = data.get("prompt") or data.get("text") or data.get("query")
        if prompt_text is not None:
            messages.append({"role": "user", "content": str(prompt_text)})
        else:
            # Fallback: stringify input data safely
            safe_payload = {k: v for k, v in data.items() if k not in ("system_prompt", "model")}
            messages.append({"role": "user", "content": json.dumps(safe_payload)})

        return messages

    def _estimate_cost(self, wire_model: str, input_tokens: int, output_tokens: int) -> Optional[Decimal]:
        """Calculates estimated cost using ModelRegistry pricing if available."""
        try:
            registry = self._model_registry
            if registry is None:
                from ai.models.registry import get_model_registry
                registry = get_model_registry()
            # Try openrouter-dev-model or canonical definitions
            model_def = None
            if registry.exists("openrouter-dev-model"):
                model_def = registry.get("openrouter-dev-model")
            elif registry.exists(wire_model):
                model_def = registry.get(wire_model)

            if model_def and model_def.pricing:
                pricing = model_def.pricing
                in_cost = (pricing.input_token_price or Decimal("0")) * Decimal(input_tokens)
                out_cost = (pricing.output_token_price or Decimal("0")) * Decimal(output_tokens)
                req_cost = pricing.request_price or Decimal("0")
                return in_cost + out_cost + req_cost
        except Exception:
            pass
        return None

    def _check_preflight_budget(self, request: CapabilityRequest) -> Optional[AIError]:
        """Performs pre-flight development budget validation before network dispatch."""
        if not request.requirements:
            return None

        budget_constraint = request.requirements.budget_constraint
        if budget_constraint is not None:
            try:
                limit = Decimal(str(budget_constraint.estimated_cost))
                # Conservative estimate: ~500 input, ~500 output tokens
                est = self._estimate_cost("openrouter-dev-model", 500, 500) or Decimal("0.001")
                if est > limit:
                    return AIError.create(
                        code=AIErrorCode.BUDGET_EXCEEDED,
                        message=f"Estimated cost ${est} exceeds budget ceiling ${limit} before dispatch",
                        retryable=False,
                        dependency_reference="openrouter",
                    )
            except Exception as e:
                logger.warning(f"Pre-flight budget parse error: {e}")

        return None

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        """
        Executes a canonical capability request via OpenRouter.
        Guarantees:
        - Structured error normalization without secret leakage.
        - Provenance and token usage recording.
        - Concurrency and timeout bounds.
        """
        start_time = time.monotonic()
        now = datetime.now(timezone.utc)
        wire_model = self._resolve_wire_model(request)

        # 1. Validate Secret Presence
        key = self.api_key
        if not key:
            err = AIError.create(
                code=AIErrorCode.PROVIDER_UNAVAILABLE,
                message="OPENROUTER_API_KEY is required to enable the OpenRouter development provider.",
                retryable=False,
                dependency_reference="openrouter",
            )
            provenance = ProvenanceRecord(
                source="openrouter_adapter",
                model_id=wire_model,
                provider_id=self.provider_id,
                timestamp=now,
                latency_ms=0,
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 2. Pre-flight budget check
        budget_err = self._check_preflight_budget(request)
        if budget_err:
            provenance = ProvenanceRecord(
                source="openrouter_adapter",
                model_id=wire_model,
                provider_id=self.provider_id,
                timestamp=now,
                latency_ms=0,
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=budget_err,
            )

        # 3. Format payload
        messages = self._format_messages(request)
        payload: Dict[str, Any] = {
            "model": wire_model,
            "messages": messages,
        }

        # Structured output constraint if requested
        wants_structured = (
            request.input_data.get("structured") is True
            or "schema" in request.input_data
            or "response_format" in request.input_data
        )
        if wants_structured:
            payload["response_format"] = {"type": "json_object"}

        # Development safety: hard cap on completion tokens
        max_tokens = request.input_data.get("max_tokens")
        if max_tokens and isinstance(max_tokens, int):
            payload["max_tokens"] = min(max_tokens, 4096)
        else:
            payload["max_tokens"] = 2048

        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://videomaker.local",
            "X-Title": "VideoMaker S28 Dev",
            "Content-Type": "application/json",
        }

        url = f"{self._base_url}/chat/completions"

        # 4. Dispatch with Concurrency Control & Retries
        async with self._semaphore:
            attempt = 0
            last_error: Optional[AIError] = None

            while attempt <= self._max_retries:
                attempt += 1
                try:
                    if self._custom_client is not None:
                        resp = await self._custom_client.post(
                            url,
                            json=payload,
                            headers=headers,
                            timeout=self._timeout_sec,
                        )
                    else:
                        async with httpx.AsyncClient(timeout=self._timeout_sec) as client:
                            resp = await client.post(
                                url,
                                json=payload,
                                headers=headers,
                            )

                    latency_ms = int((time.monotonic() - start_time) * 1000)

                    # Handle HTTP Status
                    if resp.status_code == 200:
                        try:
                            body = resp.json()
                        except Exception:
                            err = AIError.create(
                                code=AIErrorCode.INVALID_MODEL_OUTPUT,
                                message="OpenRouter response body was not valid JSON.",
                                retryable=False,
                                dependency_reference="openrouter",
                            )
                            return self._build_failure_result(request, wire_model, err, latency_ms)

                        choices = body.get("choices")
                        if not choices or not isinstance(choices, list) or len(choices) == 0:
                            err = AIError.create(
                                code=AIErrorCode.INVALID_MODEL_OUTPUT,
                                message="OpenRouter returned an empty choices list.",
                                retryable=False,
                                dependency_reference="openrouter",
                            )
                            return self._build_failure_result(request, wire_model, err, latency_ms)

                        first_choice = choices[0]
                        finish_reason = first_choice.get("finish_reason")
                        if finish_reason == "content_filter":
                            err = AIError.create(
                                code=AIErrorCode.CONTENT_REJECTED,
                                message="Content rejected by upstream OpenRouter safety filter.",
                                retryable=False,
                                dependency_reference="openrouter",
                            )
                            return self._build_failure_result(request, wire_model, err, latency_ms)

                        msg = first_choice.get("message", {})
                        raw_content = msg.get("content") or ""

                        # Extract token usage
                        usage_dict = body.get("usage", {})
                        in_tokens = usage_dict.get("prompt_tokens", 0)
                        out_tokens = usage_dict.get("completion_tokens", 0)
                        tot_tokens = usage_dict.get("total_tokens", in_tokens + out_tokens)
                        usage_record = UsageRecord(
                            input_tokens=in_tokens,
                            output_tokens=out_tokens,
                            total_tokens=tot_tokens,
                        )

                        # Output parsing & structured extraction
                        structured_output: Optional[Dict[str, Any]] = None
                        if wants_structured:
                            try:
                                structured_output = json.loads(raw_content)
                            except json.JSONDecodeError:
                                err = AIError.create(
                                    code=AIErrorCode.SCHEMA_VALIDATION_FAILED,
                                    message="OpenRouter output failed JSON structured validation.",
                                    retryable=False,
                                    dependency_reference="openrouter",
                                )
                                return self._build_failure_result(request, wire_model, err, latency_ms)

                        output_payload: Dict[str, JsonValue] = {
                            "text": raw_content,
                            "structured": structured_output,
                            "model": body.get("model", wire_model),
                            "finish_reason": finish_reason or "stop",
                        }

                        provenance = ProvenanceRecord(
                            source="openrouter_adapter",
                            model_id=body.get("model", wire_model),
                            provider_id=self.provider_id,
                            timestamp=datetime.now(timezone.utc),
                            latency_ms=latency_ms,
                        )

                        return CapabilityResult(
                            capability=request.capability,
                            status=CapabilityStatus.SUCCESS,
                            output_data=output_payload,
                            confidence=0.95,
                            provenance=provenance,
                            usage=usage_record,
                            error=None,
                        )

                    elif resp.status_code in (401, 403):
                        # Authentication failure - NEVER include key in message
                        err = AIError.create(
                            code=AIErrorCode.PROVIDER_UNAVAILABLE,
                            message="OpenRouter authentication failed: Invalid or expired API credentials.",
                            retryable=False,
                            dependency_reference="openrouter",
                        )
                        latency_ms = int((time.monotonic() - start_time) * 1000)
                        return self._build_failure_result(request, wire_model, err, latency_ms)

                    elif resp.status_code == 429:
                        last_error = AIError.create(
                            code=AIErrorCode.RATE_LIMITED,
                            message="OpenRouter upstream rate limit exceeded (HTTP 429).",
                            retryable=True,
                            details={"retry_after_seconds": 30},
                            dependency_reference="openrouter",
                        )
                        if attempt <= self._max_retries:
                            await asyncio.sleep(0.5 * attempt)
                            continue
                        latency_ms = int((time.monotonic() - start_time) * 1000)
                        return self._build_failure_result(request, wire_model, last_error, latency_ms)

                    elif resp.status_code >= 500:
                        last_error = AIError.create(
                            code=AIErrorCode.PROVIDER_UNAVAILABLE,
                            message=f"OpenRouter upstream server error (HTTP {resp.status_code}).",
                            retryable=True,
                            dependency_reference="openrouter",
                        )
                        if attempt <= self._max_retries:
                            await asyncio.sleep(0.5 * attempt)
                            continue
                        latency_ms = int((time.monotonic() - start_time) * 1000)
                        return self._build_failure_result(request, wire_model, last_error, latency_ms)

                    else:
                        err = AIError.create(
                            code=AIErrorCode.DEPENDENCY_FAILED,
                            message=f"OpenRouter returned unexpected HTTP status {resp.status_code}.",
                            retryable=False,
                            dependency_reference="openrouter",
                        )
                        latency_ms = int((time.monotonic() - start_time) * 1000)
                        return self._build_failure_result(request, wire_model, err, latency_ms)

                except httpx.TimeoutException:
                    last_error = AIError.create(
                        code=AIErrorCode.TIMEOUT,
                        message=f"Request to OpenRouter timed out after {self._timeout_sec}s.",
                        retryable=True,
                        dependency_reference="openrouter",
                    )
                    if attempt <= self._max_retries:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    return self._build_failure_result(request, wire_model, last_error, latency_ms)

                except Exception as exc:
                    # Sanitize exception message to prevent secret leaking
                    sanitized_exc = str(exc)
                    if key and key in sanitized_exc:
                        sanitized_exc = sanitized_exc.replace(key, "[REDACTED_API_KEY]")
                    last_error = AIError.create(
                        code=AIErrorCode.INTERNAL_ERROR,
                        message=f"OpenRouter adapter error: {sanitized_exc}",
                        retryable=False,
                        dependency_reference="openrouter",
                    )
                    latency_ms = int((time.monotonic() - start_time) * 1000)
                    return self._build_failure_result(request, wire_model, last_error, latency_ms)

            latency_ms = int((time.monotonic() - start_time) * 1000)
            return self._build_failure_result(
                request,
                wire_model,
                last_error or AIError.create(AIErrorCode.INTERNAL_ERROR, "Unknown failure", False),
                latency_ms,
            )

    def _build_failure_result(
        self,
        request: CapabilityRequest,
        model_id: str,
        error: AIError,
        latency_ms: int,
    ) -> CapabilityResult:
        provenance = ProvenanceRecord(
            source="openrouter_adapter",
            model_id=model_id,
            provider_id=self.provider_id,
            timestamp=datetime.now(timezone.utc),
            latency_ms=latency_ms,
        )
        return CapabilityResult(
            capability=request.capability,
            status=CapabilityStatus.FAILED,
            output_data=None,
            provenance=provenance,
            error=error,
        )
