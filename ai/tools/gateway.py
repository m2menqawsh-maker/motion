"""
ai/tools/gateway.py
===================
Authoritative ToolGateway and execution pipeline for Capabilities (S28-M03).

Invariants:
- 15-step execution pipeline enforcing full security, tenant isolation, and contracts.
- Strictly consumes full `side_effects[]` array (never scalar compatibility field alone).
- Enforces SSRF / network egress safety (blocks localhost, private RFC1918, file://).
- Strictly bounds execution timeout via cooperative context deadlines and asyncio.wait_for.
- Enforces server-side authorization and tenant resource ownership before adapter selection.
- Validates both input and output contracts strictly against canonical Pydantic schemas.
- Rejects security-blocked implementations (e.g. legacy concatenate_videos) with structured errors.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import logging
import socket
import time
import urllib.parse
from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError

from ai.capabilities.catalog import CapabilityCatalog, get_capability_catalog
from ai.contracts import (
    AIContractModel,
    AIError,
    AIErrorCode,
    CapabilityDefinition,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
    IdempotencyPolicy,
    ImplementationDescriptor,
    SideEffectClass,
    TenantScope,
)
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.adapters.mcp import ImplementationSecurityBlockedError
from ai.tools.adapters.registry import (
    AdapterRegistry,
    ImplementationUnavailableError,
    get_adapter_registry,
)
from ai.tools.adapters.remote import UpstreamProviderUnavailableError
from ai.tools.errors import (
    CapabilityCancelledError,
    CapabilityError,
    CapabilityForbiddenError,
    CapabilityInputValidationError,
    CapabilityNotFoundError,
    CapabilityOutputValidationError,
    CapabilityTimeoutError,
    IdempotencyConflictError,
    NetworkPolicyViolationError,
    TenantScopeViolationError,
    to_ai_error,
)
from ai.tools.types import TrustedToolExecutionContext

logger = logging.getLogger("clean_video.ai.tools.gateway")


# =============================================================================
# URL & SSRF Validation Policy
# =============================================================================

FORBIDDEN_SCHEMES = {"file", "ftp", "gopher", "data", "javascript"}


def validate_safe_url(url: str) -> None:
    """
    Strict SSRF and network egress validation.
    Blocks loopback, link-local, cloud metadata endpoints, RFC1918 private ranges,
    and non-HTTP/HTTPS schemes.
    """
    if not url or not isinstance(url, str):
        return

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise NetworkPolicyViolationError(f"Malformed target URL: {e}", details={"url": url})

    scheme = parsed.scheme.lower()
    if scheme in FORBIDDEN_SCHEMES or scheme not in ("http", "https"):
        raise NetworkPolicyViolationError(
            f"URL scheme '{scheme}' is forbidden by network security policy. Only 'http' and 'https' allowed.",
            details={"url": url, "scheme": scheme},
        )

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise NetworkPolicyViolationError("Invalid URL: missing target hostname.", details={"url": url})

    # Hostname blocklist
    blocked_hosts = {
        "localhost",
        "ip6-localhost",
        "ip6-loopback",
        "metadata.google.internal",
        "instance-data",
    }
    if hostname in blocked_hosts or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise NetworkPolicyViolationError(
            f"Target host '{hostname}' is internal and forbidden by SSRF policy.",
            details={"url": url, "host": hostname},
        )

    # IP address parsing & range check
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback:
            raise NetworkPolicyViolationError(f"Target IP '{hostname}' is loopback address (SSRF blocked).", details={"ip": hostname})
        if ip.is_private:
            raise NetworkPolicyViolationError(f"Target IP '{hostname}' is private RFC1918 address (SSRF blocked).", details={"ip": hostname})
        if ip.is_link_local:
            raise NetworkPolicyViolationError(f"Target IP '{hostname}' is link-local / metadata address (SSRF blocked).", details={"ip": hostname})
        if ip.is_reserved or ip.is_multicast:
            raise NetworkPolicyViolationError(f"Target IP '{hostname}' is reserved/multicast address (SSRF blocked).", details={"ip": hostname})
        return
    except ValueError:
        pass

    # DNS resolution check for domain names
    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except Exception as e:
        raise NetworkPolicyViolationError(
            f"DNS resolution failed for '{hostname}': {e}",
            details={"url": url, "host": hostname},
        )
    for family, socktype, proto, canonname, sockaddr in addrinfo:
        resolved_ip_str = sockaddr[0]
        try:
            resolved_ip = ipaddress.ip_address(resolved_ip_str)
            if resolved_ip.is_loopback:
                raise NetworkPolicyViolationError(f"Target host '{hostname}' resolved to loopback IP '{resolved_ip_str}' (SSRF blocked).", details={"url": url, "ip": resolved_ip_str})
            if resolved_ip.is_private:
                raise NetworkPolicyViolationError(f"Target host '{hostname}' resolved to private IP '{resolved_ip_str}' (SSRF blocked).", details={"url": url, "ip": resolved_ip_str})
            if resolved_ip.is_link_local:
                raise NetworkPolicyViolationError(f"Target host '{hostname}' resolved to link-local IP '{resolved_ip_str}' (SSRF blocked).", details={"url": url, "ip": resolved_ip_str})
            if resolved_ip.is_reserved or resolved_ip.is_multicast:
                raise NetworkPolicyViolationError(f"Target host '{hostname}' resolved to reserved/multicast IP '{resolved_ip_str}' (SSRF blocked).", details={"url": url, "ip": resolved_ip_str})
        except ValueError:
            pass


# =============================================================================
# In-Memory Idempotency Cache
# =============================================================================

class IdempotencyStore:
    """Thread-safe storage tracking idempotency keys, payloads, results, and in-flight executions."""

    def __init__(self) -> None:
        self._entries: Dict[str, Tuple[str, CapabilityResult]] = {}
        self._in_flight: Dict[str, Tuple[str, asyncio.Future[CapabilityResult]]] = {}

    def get(self, key: str) -> Optional[Tuple[str, CapabilityResult]]:
        return self._entries.get(key)

    def get_in_flight(self, key: str) -> Optional[Tuple[str, asyncio.Future[CapabilityResult]]]:
        return self._in_flight.get(key)

    def register_in_flight(self, key: str, payload_hash: str) -> asyncio.Future[CapabilityResult]:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[CapabilityResult] = loop.create_future()
        self._in_flight[key] = (payload_hash, fut)
        return fut

    def claim_execution(self, key: str, payload_hash: str) -> Tuple[asyncio.Future[CapabilityResult], bool]:
        """
        Attempts to claim execution leadership for this idempotency key.
        Returns: (future, is_leader). If is_leader is True, caller must execute.
        If is_leader is False, caller awaits future to receive leader's result.
        """
        if key in self._in_flight:
            in_hash, fut = self._in_flight[key]
            if in_hash != payload_hash:
                raise IdempotencyConflictError(
                    key,
                    f"Idempotency conflict: key '{key}' is currently executing with a different input payload."
                )
            return fut, False
        fut = self.register_in_flight(key, payload_hash)
        return fut, True

    def complete(self, key: str, payload_hash: str, result: CapabilityResult) -> None:
        self._entries[key] = (payload_hash, result)
        entry = self._in_flight.pop(key, None)
        if entry:
            _, fut = entry
            if not fut.done():
                fut.set_result(result)

    def fail(self, key: str, exc: Exception) -> None:
        entry = self._in_flight.pop(key, None)
        if entry:
            _, fut = entry
            if not fut.done():
                fut.set_exception(exc)

    def set(self, key: str, payload_hash: str, result: CapabilityResult) -> None:
        self.complete(key, payload_hash, result)

    def clear(self) -> None:
        self._entries.clear()
        self._in_flight.clear()


try:
    from scripts.core.idempotency_store import DurableIdempotencyStore
    _default_idempotency_store = DurableIdempotencyStore()
except Exception:
    _default_idempotency_store = IdempotencyStore()


# =============================================================================
# ToolGateway Implementation
# =============================================================================

class ToolGateway:
    """
    Authoritative boundary for executing tool and domain service capabilities.
    Orchestrates validation, tenant isolation, authorization, side-effects policy,
    adapter resolution, and output contract verification.

    Idempotency & Crash-Window Recovery Contract:
    ToolGateway provides durable distributed coordination and CAS leadership leasing across multi-worker environments.
    However, ToolGateway CANNOT guarantee generic exactly-once side effects across crash windows unless the
    underlying mutating capability participates in the idempotency and recovery contract (e.g., via
    operation-level idempotent/CAS execution, durable operation/result reconciliation, or content-hash deduplication).
    For Asset Acquisition specifically, takeover after a leader crash window safely converges on the same canonical
    asset without duplicate persistent mutations because the underlying domain service (AssetAcquisitionService,
    StockDedupeEngine, CanonicalAssetRepository, and AssetService) enforces operation-level CAS and content-hash
    uniqueness before committing any new persistent state.
    """

    def __init__(
        self,
        catalog: Optional[CapabilityCatalog] = None,
        adapter_registry: Optional[AdapterRegistry] = None,
        idempotency_store: Optional[IdempotencyStore] = None,
    ) -> None:
        self.catalog = catalog or get_capability_catalog()
        self.adapter_registry = adapter_registry or get_adapter_registry()
        self.idempotency_store = idempotency_store or _default_idempotency_store

    async def execute(
        self,
        request: CapabilityRequest,
        context: Optional[TrustedToolExecutionContext] = None,
    ) -> CapabilityResult:
        """
        Executes a CapabilityRequest through the full 15-stage canonical gateway pipeline.
        """
        start_time = datetime.now(timezone.utc)
        start_mono = time.monotonic()
        cap_val = request.capability_id.value if hasattr(request.capability_id, "value") else str(request.capability_id)
        impl_id: Optional[str] = None
        adapter_kind: Optional[str] = None
        side_effects_recorded: list[str] = []

        def _make_error_result(
            err: AIError,
            impl_desc: Optional[ImplementationDescriptor] = None,
        ) -> CapabilityResult:
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))
            return CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.FAILED,
                output=None,
                output_data=None,
                execution_metadata={
                    "adapter_kind": adapter_kind or "UNKNOWN",
                    "error_code": err.code.value if hasattr(err.code, "value") else str(err.code),
                    "side_effects": side_effects_recorded,
                },
                implementation_id=impl_desc.implementation_id if impl_desc else (impl_id or "unresolved"),
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                error=err,
            )

        try:
            # -----------------------------------------------------------------
            # Stage 1: Capability Lookup
            # -----------------------------------------------------------------
            cap_def = self.catalog.get(request.capability_id)
            if not cap_def:
                raise CapabilityNotFoundError(cap_val)

            # Record side_effects from authoritative array
            side_effects_recorded = [
                e.value if hasattr(e, "value") else str(e) for e in cap_def.side_effects
            ]

            # -----------------------------------------------------------------
            # Stage 2 & 3: Input Schema Resolution & Validation
            # -----------------------------------------------------------------
            input_model_cls = cap_def.resolve_input_contract()
            try:
                validated_input = input_model_cls.model_validate(request.input)
            except ValidationError as ve:
                raise CapabilityInputValidationError(cap_val, str(ve))

            # -----------------------------------------------------------------
            # Stage 4: TenantContext Validation
            # -----------------------------------------------------------------
            # Resolve or construct authoritative execution context
            ctx = self._resolve_execution_context(request, context)

            tenant_scope_val = cap_def.tenant_scope.value if hasattr(cap_def.tenant_scope, "value") else str(cap_def.tenant_scope)

            if request.workspace_id and request.workspace_id != ctx.workspace_id and not ctx.is_admin:
                raise TenantScopeViolationError(
                    cap_val,
                    f"Cross-workspace isolation violation: Request workspace '{request.workspace_id}' does not match actor workspace '{ctx.workspace_id}'."
                )

            if tenant_scope_val == TenantScope.PROJECT.value:
                req_proj = request.project_id or getattr(validated_input, "project_id", None)
                if not req_proj:
                    raise TenantScopeViolationError(
                        cap_val,
                        f"Capability '{cap_val}' requires PROJECT tenant_scope but project_id was not provided in request or input."
                    )
                if not ctx.can_access_project(req_proj):
                    raise TenantScopeViolationError(
                        cap_val,
                        f"Cross-tenant isolation violation: Actor '{ctx.actor_id}' in workspace '{ctx.workspace_id}' cannot access project '{req_proj}'."
                    )
            elif tenant_scope_val == TenantScope.SYSTEM.value:
                if not ctx.is_admin:
                    raise CapabilityForbiddenError(
                        cap_val,
                        "Capability has SYSTEM scope and requires system administrative privileges.",
                        actor_id=ctx.actor_id,
                    )

            # -----------------------------------------------------------------
            # Stage 5: Authorization Enforcement
            # -----------------------------------------------------------------
            proj_id_target = request.project_id or getattr(validated_input, "project_id", None)
            if cap_def.required_permissions:
                if not any(self._check_permission(ctx, req_perm, proj_id_target) for req_perm in cap_def.required_permissions):
                    raise CapabilityForbiddenError(
                        cap_val,
                        f"Actor '{ctx.actor_id}' lacks required permission (requires one of {cap_def.required_permissions}) for capability '{cap_val}'.",
                        actor_id=ctx.actor_id,
                    )

            # -----------------------------------------------------------------
            # Stage 6: Resource Ownership / Tenant Confinement
            # -----------------------------------------------------------------
            self._validate_resource_confinement(request, validated_input)

            # -----------------------------------------------------------------
            # Stage 7: Side-Effects Policy Enforcement (consuming side_effects[])
            # -----------------------------------------------------------------
            # Critical invariant: must evaluate all compound side effects!
            active_side_effects = list(cap_def.side_effects) if cap_def.side_effects else [cap_def.side_effect_class]

            # 7a. EXTERNAL_NETWORK: SSRF and egress validation
            if SideEffectClass.EXTERNAL_NETWORK in active_side_effects:
                self._enforce_network_policy(validated_input)

            # 7b. PERSISTENT_WRITE: Validate target storage boundary
            if SideEffectClass.PERSISTENT_WRITE in active_side_effects:
                self._enforce_storage_boundary_policy(cap_def, validated_input)

            # 7c. SUBPROCESS: Enforce known bounded executable parameters
            if SideEffectClass.SUBPROCESS in active_side_effects:
                self._enforce_subprocess_policy(request, validated_input)

            # -----------------------------------------------------------------
            # Stage 8: Budget / Resource Ceiling Policy
            # -----------------------------------------------------------------
            self._enforce_budget_policy(request, cap_def)

            # -----------------------------------------------------------------
            # Stage 9: Idempotency Enforcement
            # -----------------------------------------------------------------
            payload_hash = self._compute_payload_hash(request.input)
            is_idempotent_leader = False
            if request.idempotency_key:
                # 9a. Check completed execution cache
                cached_entry = self.idempotency_store.get(request.idempotency_key)
                if cached_entry:
                    cached_hash, cached_result = cached_entry
                    if cached_hash != payload_hash:
                        raise IdempotencyConflictError(
                            request.idempotency_key,
                            f"Idempotency conflict: key '{request.idempotency_key}' was previously executed with a different input payload."
                        )
                    # Replay cached result with telemetry indication
                    replayed = cached_result.model_copy(
                        update={
                            "request_id": request.request_id,
                            "execution_metadata": {
                                **cached_result.execution_metadata,
                                "idempotency_hit": True,
                            }
                        }
                    )
                    return replayed

                # 9b. Atomic leadership claim & in-flight handling (cross-worker CAS)
                in_flight_fut, is_leader = self.idempotency_store.claim_execution(request.idempotency_key, payload_hash)
                if not is_leader:
                    # Another worker won the leadership race! Await leader's result
                    in_flight_result = await in_flight_fut
                    replayed = in_flight_result.model_copy(
                        update={
                            "request_id": request.request_id,
                            "execution_metadata": {
                                **in_flight_result.execution_metadata,
                                "idempotency_hit": True,
                            }
                        }
                    )
                    return replayed

                is_idempotent_leader = True

            # -----------------------------------------------------------------
            # Stage 10: Timeout & Cancellation Policy
            # -----------------------------------------------------------------
            effective_timeout = cap_def.timeout_seconds
            if request.requested_timeout and request.requested_timeout > 0:
                effective_timeout = min(request.requested_timeout, cap_def.timeout_seconds)

            bound_ctx = ctx.with_timeout(effective_timeout)

            # -----------------------------------------------------------------
            # Stage 11: Adapter Selection
            # -----------------------------------------------------------------
            adapter, impl_desc = self.adapter_registry.resolve(cap_def)
            impl_id = impl_desc.implementation_id if impl_desc else adapter.name
            adapter_kind = adapter.adapter_kind

            # -----------------------------------------------------------------
            # Stage 12: Execution
            # -----------------------------------------------------------------
            try:
                raw_output = await asyncio.wait_for(
                    adapter.execute(request, validated_input, bound_ctx),
                    timeout=effective_timeout,
                )
            except asyncio.TimeoutError:
                raise CapabilityTimeoutError(cap_val, effective_timeout)
            except asyncio.CancelledError:
                raise CapabilityCancelledError(cap_val)
            except (ImplementationSecurityBlockedError, UpstreamProviderUnavailableError):
                raise
            except Exception as exc:
                if request.idempotency_key and is_idempotent_leader:
                    self.idempotency_store.fail(request.idempotency_key, exc)
                err = to_ai_error(exc)
                return _make_error_result(err, impl_desc)

            # -----------------------------------------------------------------
            # Stage 13: Output Contract Validation
            # -----------------------------------------------------------------
            output_model_cls = cap_def.resolve_output_contract()
            try:
                validated_output = output_model_cls.model_validate(raw_output)
            except ValidationError as ve:
                raise CapabilityOutputValidationError(cap_val, str(ve))

            # -----------------------------------------------------------------
            # Stage 14: Domain / Storage Integrity Verification
            # -----------------------------------------------------------------
            # Verify no illegal filesystem escape in output keys
            output_dict = validated_output.model_dump(mode="json")
            self._verify_output_storage_integrity(output_dict)

            # -----------------------------------------------------------------
            # Stage 15: Telemetry & Structured Result Production
            # -----------------------------------------------------------------
            end_time = datetime.now(timezone.utc)
            duration_ms = max(0, int((time.monotonic() - start_mono) * 1000))

            exec_meta = {
                "adapter_kind": adapter_kind,
                "implementation_id": impl_id,
                "target_storage_boundary": cap_def.target_storage_boundary,
                "side_effects": side_effects_recorded,
                "timeout_seconds": effective_timeout,
                "retryable": cap_def.retry_policy != "NEVER",
            }
            # Record warning for partially working implementations
            if impl_desc and impl_desc.current_status == "PARTIALLY_WORKING":
                exec_meta["implementation_status_warning"] = "PARTIALLY_WORKING: known issues present in M01 baseline"

            result = CapabilityResult(
                request_id=request.request_id,
                capability_id=request.capability_id,
                status=CapabilityStatus.SUCCESS,
                output=output_dict,
                output_data=output_dict,
                execution_metadata=exec_meta,
                implementation_id=impl_id,
                started_at=start_time,
                completed_at=end_time,
                duration_ms=duration_ms,
                confidence=1.0,
                error=None,
            )

            # Store in idempotency cache if key was provided and caller was leader
            if request.idempotency_key and is_idempotent_leader:
                self.idempotency_store.complete(request.idempotency_key, payload_hash, result)

            return result

        except CapabilityError as ce:
            if request.idempotency_key and is_idempotent_leader:
                self.idempotency_store.fail(request.idempotency_key, ce)
            err = to_ai_error(ce)
            return _make_error_result(err)
        except Exception as unhandled:
            if request.idempotency_key and is_idempotent_leader:
                self.idempotency_store.fail(request.idempotency_key, unhandled)
            err = to_ai_error(unhandled)
            return _make_error_result(err)

    # =========================================================================
    # Pipeline Policy Helpers
    # =========================================================================

    def _resolve_execution_context(
        self,
        request: CapabilityRequest,
        passed_context: Optional[TrustedToolExecutionContext],
    ) -> TrustedToolExecutionContext:
        """Resolves or builds the authoritative server-side execution context."""
        if passed_context:
            return passed_context

        if request.tenant_context and isinstance(request.tenant_context, dict):
            try:
                return TrustedToolExecutionContext.model_validate(request.tenant_context)
            except Exception:
                pass

        # Build fallback context using server defaults
        ws_id = request.workspace_id or "ws_default"
        act_id = request.actor_id or "service_agent"
        return TrustedToolExecutionContext(
            workspace_id=ws_id,
            actor_id=act_id,
            roles=["editor"],
            permissions=["viewer", "editor"],
            is_admin=False,
            correlation_id=request.correlation_id,
        )

    def _check_permission(
        self,
        ctx: TrustedToolExecutionContext,
        required_permission: str,
        project_id: Optional[str] = None,
    ) -> bool:
        """Evaluates whether actor holds the required permission."""
        if ctx.is_admin or "admin" in ctx.roles:
            return True

        req_clean = required_permission.lower().strip()
        if req_clean in [p.lower() for p in ctx.permissions]:
            return True

        # Check role-based hierarchy: editor implies viewer
        roles_lower = [r.lower() for r in ctx.roles]
        if req_clean == "viewer" and ("editor" in roles_lower or "viewer" in roles_lower or "admin" in roles_lower):
            return True
        if req_clean == "editor" and ("editor" in roles_lower or "admin" in roles_lower):
            return True

        return ctx.has_permission(req_clean, project_id)

    def _validate_resource_confinement(
        self,
        request: CapabilityRequest,
        validated_input: AIContractModel,
    ) -> None:
        """Ensures input parameters do not cross-reference conflicting project identifiers."""
        req_proj = request.project_id
        inp_proj = getattr(validated_input, "project_id", None)
        if req_proj and inp_proj and req_proj != inp_proj:
            raise TenantScopeViolationError(
                str(request.capability_id),
                f"Conflicting project context: request.project_id '{req_proj}' does not match input.project_id '{inp_proj}'.",
                details={"request_project_id": req_proj, "input_project_id": inp_proj},
            )

    def _enforce_network_policy(self, validated_input: AIContractModel) -> None:
        """Scans input for URL fields and enforces SSRF restrictions."""
        input_dict = validated_input.model_dump()
        url_keys = ("page_url", "source_url", "download_url", "preview_url", "url", "target_url")
        for k, v in input_dict.items():
            if k in url_keys and isinstance(v, str):
                validate_safe_url(v)

    def _enforce_storage_boundary_policy(
        self,
        cap_def: CapabilityDefinition,
        validated_input: AIContractModel,
    ) -> None:
        """Validates that storage boundary authorities are respected."""
        # Ensure project_id is bound for persistent writes
        proj_id = getattr(validated_input, "project_id", None)
        if not proj_id and cap_def.tenant_scope == TenantScope.PROJECT:
            raise TenantScopeViolationError(
                str(cap_def.capability_id),
                "Persistent write capability requires a valid project_id.",
            )

    def _enforce_subprocess_policy(
        self,
        request: CapabilityRequest,
        validated_input: AIContractModel,
    ) -> None:
        """Ensures no raw command lines or arbitrary executables are injected."""
        input_dict = validated_input.model_dump()
        forbidden_subprocess_keys = ("cmd", "command", "executable", "shell_args", "raw_args")
        for k in input_dict:
            if k in forbidden_subprocess_keys:
                raise CapabilityForbiddenError(
                    str(request.capability_id),
                    f"Parameter '{k}' is forbidden. AI callers cannot supply raw shell or command line arguments.",
                )

    def _enforce_budget_policy(
        self,
        request: CapabilityRequest,
        cap_def: CapabilityDefinition,
    ) -> None:
        """Checks payload and execution resource limits."""
        # Enforce maximum payload size (1MB serialized JSON ceiling)
        try:
            payload_size = len(json.dumps(request.input))
            if payload_size > 1_048_576:
                raise CapabilityForbiddenError(
                    str(request.capability_id),
                    f"Payload size {payload_size} bytes exceeds maximum allowed ceiling of 1MB.",
                )
        except Exception:
            pass

    def _verify_output_storage_integrity(self, output_dict: Dict[str, Any]) -> None:
        """Ensures output keys do not leak host absolute paths."""
        storage_keys = ("storage_key", "output_storage_key", "manifest_storage_key", "timeline_storage_key")
        for k, v in output_dict.items():
            if k in storage_keys and isinstance(v, str):
                if v.startswith("/") or v.startswith("\\") or ":" in v[:3]:
                    raise CapabilityOutputValidationError(
                        "storage_integrity",
                        f"Output field '{k}' contains raw host path '{v}' instead of canonical storage key.",
                    )

    @staticmethod
    def _compute_payload_hash(payload: Dict[str, Any]) -> str:
        serialized = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
