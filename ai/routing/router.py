"""
ai/routing/router.py
====================
Authoritative ModelRouter for S27 Media & Video Platform.

Invariants:
- Deterministic resolution over registry snapshot.
- Hard constraints evaluated before scoring (no compensating violations).
- Multi-deployment aware (region, deployment_id).
- Provider-neutral: zero hardcoded vendor business routing logic.
- Pure decision engine: does NOT invoke LLMs or external provider network APIs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import time
from typing import Any, Dict, List, Optional, Tuple

from ai.contracts.capability import (
    CapabilityDefinition,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    ProvenanceRecord,
    UsageRecord,
)
from ai.contracts.common import CapabilityType, PrivacyRequirement, QualityTarget
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.media_ops import SpeechToTextInput
from ai.contracts.model import ModelRequirement, ModelSelection
from ai.contracts.usage import CostEstimate
from ai.capabilities.registry import CapabilityRegistry, get_capability_registry
from ai.providers.registry import ProviderRegistry, get_provider_registry
from ai.models.registry import ModelRegistry, get_model_registry
from ai.models.types import ModelDefinition
from ai.tools.types import TrustedToolExecutionContext
from ai.speech.stt_provider import (
    InvalidAudioError,
    ModelNotAvailableError,
    STTConfig,
    STTError,
    STTProvider,
    STTRequest,
    TenantAccessDeniedError,
)
from ai.speech.cache import STTCacheManager, get_stt_cache_manager
from ai.speech.storage_resolver import _is_safe_storage_key, resolve_and_materialize_audio
from scripts.core.storage.storage_service import StorageService
from ai.routing.constraints import evaluate_hard_constraints
from ai.routing.cost import calculate_estimated_cost
from ai.routing.escalation import resolve_quality_escalation
from ai.routing.fallback import build_fallback_chain, resolve_next_fallback
from ai.routing.policy import RoutingPolicy, get_policy_for_target
from ai.routing.scoring import rank_eligible_candidates
from ai.routing.types import (
    CandidateDiagnostic,
    NoEligibleModelError,
    QualityEvaluation,
    RoutingDecision,
    RoutingReasonCode,
    WorkloadEstimate,
)


class ModelRouter:
    """
    Centralized, deterministic model routing engine.
    Translates abstract capability requirements into primary models and ordered fallback chains.
    """

    def __init__(
        self,
        model_registry: Optional[ModelRegistry] = None,
        provider_registry: Optional[ProviderRegistry] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        default_policy: Optional[RoutingPolicy] = None,
    ) -> None:
        self._model_registry = model_registry or get_model_registry()
        self._provider_registry = provider_registry or get_provider_registry()
        self._capability_registry = capability_registry or get_capability_registry()
        self._default_policy = default_policy
        self._stt_providers: Dict[str, STTProvider] = {}

    def route(
        self,
        requirement: ModelRequirement,
        workload: Optional[WorkloadEstimate] = None,
        policy: Optional[RoutingPolicy] = None,
        target_region: Optional[str] = None,
    ) -> ModelSelection:
        """
        Resolves the optimal primary model and fallback chain for the given requirement.
        
        Raises:
            NoEligibleModelError: If no candidate satisfies all hard constraints.
        """
        decision = self.route_with_diagnostics(
            requirement=requirement,
            workload=workload,
            policy=policy,
            target_region=target_region,
        )
        return decision.selection

    def route_with_diagnostics(
        self,
        requirement: ModelRequirement,
        workload: Optional[WorkloadEstimate] = None,
        policy: Optional[RoutingPolicy] = None,
        target_region: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Resolves routing decision while capturing a complete diagnostic audit trail.
        """
        active_policy = policy or self._default_policy or get_policy_for_target(requirement.quality_target)

        # 1. Snapshot candidate pool (deterministic sort by model_id)
        raw_candidates = sorted(self._model_registry.list(), key=lambda m: (m.model_id, m.deployment_id or ""))

        evaluation_records: List[Tuple[ModelDefinition, bool, List[str], Optional[Decimal]]] = []
        eligible_candidates_with_costs: List[Tuple[ModelDefinition, Optional[Decimal]]] = []

        # 2. Hard constraint filtering
        for model in raw_candidates:
            is_eligible, rejection_reasons, est_cost = evaluate_hard_constraints(
                model=model,
                requirement=requirement,
                provider_registry=self._provider_registry,
                workload=workload,
                policy=active_policy,
                target_region=target_region,
            )
            evaluation_records.append((model, is_eligible, rejection_reasons, est_cost))
            if is_eligible:
                eligible_candidates_with_costs.append((model, est_cost))

        # 3. Guard against zero eligible candidates
        if not eligible_candidates_with_costs:
            all_reasons = []
            for _, _, reasons, _ in evaluation_records:
                all_reasons.extend(reasons)
            raise NoEligibleModelError(
                capability=requirement.capability.value,
                reasons=sorted(list(set(all_reasons))),
            )

        # 4. Rank eligible candidates deterministically
        ranked = rank_eligible_candidates(
            candidates_with_costs=eligible_candidates_with_costs,
            requirement=requirement,
            policy=active_policy,
        )

        score_map = {m[0].model_id: m[1] for m in ranked}

        diagnostics: List[CandidateDiagnostic] = []
        for model, is_eligible, rejection_reasons, est_cost in evaluation_records:
            c_key = f"{model.model_id}@{model.deployment_id}" if model.deployment_id else model.model_id
            diag = CandidateDiagnostic(
                candidate_key=c_key,
                model_id=model.model_id,
                provider_id=model.provider_id,
                deployment_id=model.deployment_id,
                eligible=is_eligible,
                rejection_reasons=rejection_reasons,
                utility_score=score_map.get(model.model_id),
                estimated_cost=est_cost,
                quality_profile=model.quality_profile,
                cost_profile=model.cost_profile,
                latency_profile=model.latency_profile,
                reliability=model.reliability,
            )
            diagnostics.append(diag)

        # 5. Extract primary selection
        primary_model, primary_score, primary_cost = ranked[0]
        primary_key = primary_model.model_id

        # 6. Build ordered fallback chain
        fallbacks = build_fallback_chain(ranked, active_policy)

        # 7. Deduce deterministic reason code
        reason_code = self._determine_reason_code(
            primary=primary_model,
            ranked_count=len(ranked),
            requirement=requirement,
            policy=active_policy,
        )

        # 8. Construct canonical CostEstimate
        cost_val = primary_cost if primary_cost is not None else Decimal("0.0")
        pricing_ver = primary_model.pricing.pricing_version if primary_model.pricing else "UNPRICED"
        cost_estimate = CostEstimate(
            estimated_cost=cost_val,
            currency="USD",
            pricing_version=pricing_ver,
        )

        selection = ModelSelection(
            primary_model=primary_key,
            fallback_candidates=fallbacks,
            reason_code=reason_code.value,
            estimated_cost=cost_estimate,
        )

        return RoutingDecision(
            selection=selection,
            diagnostics=diagnostics,
            policy_id=active_policy.policy_id,
            policy_version=active_policy.version,
            evaluated_candidates_count=len(raw_candidates),
            eligible_candidates_count=len(eligible_candidates_with_costs),
        )

    def next_fallback(
        self,
        current_candidate: str,
        failure_code: AIErrorCode,
        attempted_candidates: List[str],
        requirement: ModelRequirement,
        workload: Optional[WorkloadEstimate] = None,
        policy: Optional[RoutingPolicy] = None,
        target_region: Optional[str] = None,
    ) -> Optional[str]:
        """
        Determines the next fallback candidate upon upstream execution failure.
        """
        active_policy = policy or self._default_policy or get_policy_for_target(requirement.quality_target)
        raw_candidates = sorted(self._model_registry.list(), key=lambda m: (m.model_id, m.deployment_id or ""))

        eligible = []
        for model in raw_candidates:
            is_eligible, _, est_cost = evaluate_hard_constraints(
                model=model,
                requirement=requirement,
                provider_registry=self._provider_registry,
                workload=workload,
                policy=active_policy,
                target_region=target_region,
            )
            if is_eligible:
                eligible.append((model, est_cost))

        if not eligible:
            return None

        ranked = rank_eligible_candidates(eligible, requirement, active_policy)
        return resolve_next_fallback(
            current_candidate=current_candidate,
            failure_code=failure_code,
            attempted_candidates=attempted_candidates,
            ranked_candidates=ranked,
            policy=active_policy,
        )

    def escalate(
        self,
        current_model_id: str,
        requirement: ModelRequirement,
        evaluation: QualityEvaluation,
        attempted_models: List[str],
        workload: Optional[WorkloadEstimate] = None,
        policy: Optional[RoutingPolicy] = None,
        target_region: Optional[str] = None,
    ) -> Optional[ModelSelection]:
        """
        Escalates execution to a strictly higher quality tier candidate while preserving hard constraints.
        Returns None if no eligible higher quality candidate exists within constraints.
        """
        if not self._model_registry.exists(current_model_id):
            return None

        current_model = self._model_registry.get(current_model_id)
        active_policy = policy or self._default_policy or get_policy_for_target(requirement.quality_target)
        raw_candidates = sorted(self._model_registry.list(), key=lambda m: (m.model_id, m.deployment_id or ""))

        eligible = []
        for model in raw_candidates:
            is_eligible, _, est_cost = evaluate_hard_constraints(
                model=model,
                requirement=requirement,
                provider_registry=self._provider_registry,
                workload=workload,
                policy=active_policy,
                target_region=target_region,
            )
            if is_eligible:
                eligible.append((model, est_cost))

        ranked = rank_eligible_candidates(eligible, requirement, active_policy)

        escalated_tuple = resolve_quality_escalation(
            current_model=current_model,
            requirement=requirement,
            evaluation=evaluation,
            attempted_models=attempted_models,
            eligible_candidates=ranked,
            policy=active_policy,
        )

        if escalated_tuple is None:
            return None

        escalated_model, score, est_cost = escalated_tuple
        fallbacks = [
            m[0].model_id for m in ranked
            if m[0].model_id != escalated_model.model_id
            and m[0].model_id not in attempted_models
        ][:active_policy.max_fallbacks]

        cost_val = est_cost if est_cost is not None else Decimal("0.0")
        pricing_ver = escalated_model.pricing.pricing_version if escalated_model.pricing else "UNPRICED"

        return ModelSelection(
            primary_model=escalated_model.model_id,
            fallback_candidates=fallbacks,
            reason_code=RoutingReasonCode.ESCALATED_QUALITY_UPGRADE.value,
            estimated_cost=CostEstimate(
                estimated_cost=cost_val,
                currency="USD",
                pricing_version=pricing_ver,
            ),
        )

    def _determine_reason_code(
        self,
        primary: ModelDefinition,
        ranked_count: int,
        requirement: ModelRequirement,
        policy: RoutingPolicy,
    ) -> RoutingReasonCode:
        if ranked_count == 1:
            return RoutingReasonCode.SINGLE_COMPLIANT_CANDIDATE

        if requirement.privacy_requirement in (PrivacyRequirement.INTERNAL_ONLY, PrivacyRequirement.ZERO_DATA_RETENTION):
            return RoutingReasonCode.PRIVACY_FILTERED

        if requirement.quality_target == QualityTarget.DRAFT:
            return RoutingReasonCode.LOWEST_COST_MEETING_TARGET

        if requirement.budget_constraint is not None and primary.quality_profile in (QualityTarget.HIGH, QualityTarget.ULTRA):
            return RoutingReasonCode.HIGHEST_QUALITY_WITHIN_BUDGET

        if requirement.max_latency_ms is not None and requirement.max_latency_ms <= 1000:
            return RoutingReasonCode.LOW_LATENCY_REQUIRED

        return RoutingReasonCode.BEST_BALANCED_UTILITY

    def register_stt_provider(self, provider_id: str, provider: STTProvider) -> None:
        """Registers a specialized STT provider."""
        if not isinstance(provider, STTProvider):
            raise TypeError(f"Provider must implement STTProvider interface, got {type(provider)}")
        self._stt_providers[provider_id.strip().lower()] = provider

    def get_stt_provider(self, provider_id: str = "local") -> STTProvider:
        """Resolves registered STT provider, lazily instantiating default LocalSTTProvider."""
        pid = provider_id.strip().lower()
        if pid not in self._stt_providers:
            if pid == "local":
                from ai.speech.local_provider import LocalSTTProvider
                self._stt_providers["local"] = LocalSTTProvider()
            else:
                raise ModelNotAvailableError(f"STT provider '{provider_id}' is not registered in ModelRouter.")
        return self._stt_providers[pid]

    async def execute_stt(
        self,
        request: CapabilityRequest,
        context: Optional[TrustedToolExecutionContext] = None,
        storage_service: Optional[StorageService] = None,
        cache_manager: Optional[STTCacheManager] = None,
    ) -> CapabilityResult:
        """
        Authoritative execution flow for SPEECH_TO_TEXT:
        CapabilityRequest(SPEECH_TO_TEXT)
                ↓
        CapabilityRouter
                ↓
        ModelRouter
                ↓
        STTProvider (LocalSTTProvider)
                ↓
        actual faster-whisper inference
                ↓
        validated SpeechIntelligence
                ↓
        canonical TranscriptArtifact / cache
        """
        start_time = datetime.now(timezone.utc)
        start_mono = time.monotonic()

        # 1. Validate Input Contract
        try:
            validated_input = SpeechToTextInput.model_validate(request.input)
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.FAILED,
                output=None,
                execution_metadata={"router_branch": "MODEL"},
                implementation_id="local_stt_provider",
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                error=AIError(
                    code=AIErrorCode.SCHEMA_VALIDATION_FAILED,
                    message=f"Input contract validation failed for SPEECH_TO_TEXT: {e}",
                    retryable=False,
                ),
            )

        # 2. Strict Traversal / Path Security Guard
        if not _is_safe_storage_key(validated_input.audio_storage_key):
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.FAILED,
                output=None,
                execution_metadata={"router_branch": "MODEL"},
                implementation_id="local_stt_provider",
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                error=AIError(
                    code=AIErrorCode.TENANT_ACCESS_DENIED,
                    message=f"Arbitrary filesystem path or traversal attempt rejected in audio_storage_key: '{validated_input.audio_storage_key}'",
                    retryable=False,
                ),
            )

        # 3. Tenant Boundary Verification
        if context is not None:
            ws = request.workspace_id
            if ws and context.workspace_id and ws != context.workspace_id and not context.is_admin:
                end_time = datetime.now(timezone.utc)
                duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
                return CapabilityResult(
                    request_id=request.request_id,
                    capability_id=request.capability_id,
                    status=CapabilityStatus.FAILED,
                    output=None,
                    execution_metadata={"router_branch": "MODEL"},
                    implementation_id="local_stt_provider",
                    started_at=start_time,
                    completed_at=end_time,
                    duration_ms=duration_ms,
                    error=AIError(
                        code=AIErrorCode.TENANT_ACCESS_DENIED,
                        message=f"Cross-workspace access denied: actor workspace '{context.workspace_id}' cannot access '{ws}'.",
                        retryable=False,
                    ),
                )
            if not context.can_access_project(validated_input.project_id):
                end_time = datetime.now(timezone.utc)
                duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
                return CapabilityResult(
                    request_id=request.request_id,
                    capability_id=request.capability_id,
                    status=CapabilityStatus.FAILED,
                    output=None,
                    execution_metadata={"router_branch": "MODEL"},
                    implementation_id="local_stt_provider",
                    started_at=start_time,
                    completed_at=end_time,
                    duration_ms=duration_ms,
                    error=AIError(
                        code=AIErrorCode.TENANT_ACCESS_DENIED,
                        message=f"Cross-project access denied: actor '{context.actor_id}' cannot access project '{validated_input.project_id}'.",
                        retryable=False,
                    ),
                )

        # 4. Resolve STT Provider & Config
        try:
            provider = self.get_stt_provider("local")
        except Exception as prov_err:
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.FAILED,
                output=None,
                execution_metadata={"router_branch": "MODEL"},
                implementation_id="local_stt_provider",
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                error=AIError(
                    code=AIErrorCode.PROVIDER_UNAVAILABLE,
                    message=f"STT Provider resolution failed: {prov_err}",
                    retryable=False,
                ),
            )

        model_tier = validated_input.model_size or "base"
        config = STTConfig(
            model_size=model_tier,
            language=validated_input.language,
            word_timestamps=True,
            vad_filter=True,
        )
        cache_mgr = cache_manager or get_stt_cache_manager()
        effective_timeout = request.requested_timeout or 60.0

        # 5. Resolve Storage, Check Cache, and Execute Live Inference
        try:
            async with resolve_and_materialize_audio(
                project_id=validated_input.project_id,
                audio_storage_key=validated_input.audio_storage_key,
                workspace_id=request.workspace_id,
                context=context,
                storage_service=storage_service,
                request_id=request.request_id,
            ) as (temp_path, content_hash, source_asset_id):

                cache_key = cache_mgr.derive_cache_key(
                    workspace_id=request.workspace_id or "default_workspace",
                    project_id=validated_input.project_id,
                    source_content_hash=content_hash,
                    config=config,
                    model_id=f"faster-whisper-{model_tier}",
                    model_version="1.2.1",
                )

                # Cache HIT Check
                cached_artifact = cache_mgr.get(cache_key)
                if cached_artifact is not None:
                    end_time = datetime.now(timezone.utc)
                    duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
                    speech_intel = cached_artifact.to_speech_intelligence()
                    output_dict = speech_intel.model_dump(mode="json")
                    prov_record = ProvenanceRecord(
                        source=speech_intel.provenance.producer,
                        model_id=f"faster-whisper-{model_tier}",
                        provider_id=provider.provider_id,
                        timestamp=speech_intel.provenance.timestamp,
                        latency_ms=0,
                    )
                    return CapabilityResult(
                        request_id=request.request_id,
                        capability_id=request.capability_id,
                        status=CapabilityStatus.SUCCESS,
                        output=output_dict,
                        output_data=output_dict,
                        execution_metadata={
                            "router_branch": "MODEL",
                            "provider_id": provider.provider_id,
                            "model_id": f"faster-whisper-{model_tier}",
                            "cache_hit": True,
                            "cache_key": cache_key,
                            "transcript_id": cached_artifact.transcript_id,
                        },
                        implementation_id="local_stt_provider",
                        started_at=start_time,
                        completed_at=end_time,
                        duration_ms=duration_ms,
                        confidence=speech_intel.overall_confidence or 0.95,
                        provenance=prov_record,
                        usage=UsageRecord(),
                    )

                # Cache MISS: Live Inference Execution
                stt_req = STTRequest(
                    request_id=request.request_id,
                    audio_path=str(temp_path),
                    audio_content_hash=content_hash,
                    config=config,
                    source_asset_id=source_asset_id,
                    timeout_seconds=effective_timeout,
                )

                stt_res = await provider.transcribe(stt_req)
                speech_intel = stt_res.to_speech_intelligence()
                artifact = stt_res.to_transcript_artifact(
                    source_asset_id=source_asset_id,
                    source_content_hash=content_hash,
                )
                cache_mgr.put(cache_key, artifact)

                end_time = datetime.now(timezone.utc)
                duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
                output_dict = speech_intel.model_dump(mode="json")
                prov_record = ProvenanceRecord(
                    source=speech_intel.provenance.producer,
                    model_id=stt_res.model_id,
                    provider_id=provider.provider_id,
                    timestamp=speech_intel.provenance.timestamp,
                    latency_ms=int(stt_res.inference_ms),
                )

                return CapabilityResult(
                    request_id=request.request_id,
                    capability_id=request.capability_id,
                    status=CapabilityStatus.SUCCESS,
                    output=output_dict,
                    output_data=output_dict,
                    execution_metadata={
                        "router_branch": "MODEL",
                        "provider_id": provider.provider_id,
                        "model_id": stt_res.model_id,
                        "model_version": stt_res.model_version,
                        "device": stt_res.model_device,
                        "compute_type": stt_res.compute_type,
                        "fallback_occurred": stt_res.fallback_occurred,
                        "fallback_reason": stt_res.fallback_reason,
                        "cache_hit": False,
                        "cache_key": cache_key,
                        "transcript_id": artifact.transcript_id,
                        "audio_duration_seconds": stt_res.duration_seconds,
                        "real_time_factor": stt_res.real_time_factor,
                        "queue_wait_ms": stt_res.queue_wait_ms,
                        "model_load_ms": stt_res.model_load_ms,
                        "inference_ms": stt_res.inference_ms,
                        "segments_count": len(stt_res.segments),
                        "words_count": len(stt_res.words),
                    },
                    implementation_id="local_stt_provider",
                    started_at=start_time,
                    completed_at=end_time,
                    duration_ms=duration_ms,
                    confidence=speech_intel.overall_confidence or 0.95,
                    provenance=prov_record,
                    usage=UsageRecord(audio_seconds=str(stt_res.duration_seconds)),
                )

        except STTError as stt_err:
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.FAILED,
                output=None,
                execution_metadata={
                    "router_branch": "MODEL",
                    "error_category": stt_err.__class__.__name__,
                },
                implementation_id="local_stt_provider",
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                error=stt_err.to_ai_error(),
            )
        except Exception as exc:
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.FAILED,
                output=None,
                execution_metadata={"router_branch": "MODEL"},
                implementation_id="local_stt_provider",
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                error=AIError(
                    code=AIErrorCode.INTERNAL_ERROR,
                    message=f"Unhandled STT execution error: {exc}",
                    retryable=False,
                ),
            )

    async def execute_model_capability(
        self,
        request: CapabilityRequest,
        cap_def: CapabilityDefinition,
        context: Optional[TrustedToolExecutionContext] = None,
        storage_service: Optional[StorageService] = None,
        cache_manager: Optional[STTCacheManager] = None,
    ) -> CapabilityResult:
        """
        Dispatches MODEL category capabilities to their dedicated implementations.
        """
        cap_id = request.capability_id.value if hasattr(request.capability_id, "value") else str(request.capability_id)
        if cap_id == CapabilityType.SPEECH_TO_TEXT.value:
            return await self.execute_stt(
                request=request,
                context=context,
                storage_service=storage_service,
                cache_manager=cache_manager,
            )

        start_time = datetime.now(timezone.utc)
        return CapabilityResult(
            request_id=request.request_id,
            capability_id=request.capability_id,
            status=CapabilityStatus.FAILED,
            output=None,
            execution_metadata={"router_branch": "MODEL"},
            implementation_id="model_router_unhandled",
            started_at=start_time,
            completed_at=start_time,
            duration_ms=0,
            error=AIError(
                code=AIErrorCode.CAPABILITY_UNAVAILABLE,
                message=f"Model capability '{cap_id}' is not yet supported in ModelRouter.",
                retryable=False,
            ),
        )

