# S28-M03 — Capability Routing & Tool Gateway Architecture

## 1. Executive Summary & Objective

In legacy video production systems, AI agents and execution recipes were tightly coupled to concrete implementation details:
```text
[LEGACY]
AI / Recipe -> Known MCP Server / Tool Name -> Raw Subprocess / Host Filesystem Path
```
This created severe architectural debt:
1. AI callers were required to know vendor names (e.g. `pexels`, `pixabay`), MCP server names (e.g. `video-tools-mcp`), and internal command-line details.
2. Insecure operations (such as command injection vectors or direct un-governed filesystem mutations) could be invoked directly.
3. Replacing or upgrading an underlying provider required rewriting AI prompts, recipes, and calling code.

Under **S28-M03**, this implementation coupling is permanently eliminated. Callers know **Capabilities only**:
```text
[CANONICAL S28-M03 ARCHITECTURE]
AI Caller / Recipe / Agent
            │
            ▼
    CapabilityRequest (Provider-Neutral)
            │
            ▼
     CapabilityRouter
      ├── MODEL ───────────────► ModelRouterSeam ──► (S28-M04 STT Lifecycle)
      │
      ├── TOOL ────────────────► ToolGateway ─────► Authorized Adapter (e.g. MCPToolAdapter)
      │                                                     │
      └── DOMAIN_SERVICE ──────► ToolGateway ─────► DomainServiceAdapter ──► Canonical Domain Services
                                                    (AssetService / RunService)
```

---

## 2. Canonical Contracts

### 2.1 `CapabilityRequest`
The canonical input contract representing an intent to execute a capability:
- `request_id`: Unique trace identifier for idempotency and audit logs.
- `capability_id` / `capability`: Canonical `CapabilityType` enum member (e.g., `TRIM_VIDEO`, `CHECK_MEDIA_CACHE`, `SPEECH_TO_TEXT`).
- `workspace_id`: Tenant workspace context.
- `project_id`: Target project context (required for `PROJECT` tenant scope).
- `actor_id`: Caller identity token for authorization.
- `tenant_context`: Structured server-side execution context.
- `input`: Strongly-typed input parameters validated against the capability's `input_contract`.
- `idempotency_key`: Optional client token for replay and deduplication.
- `correlation_id`: Distributed trace identifier.
- `requested_timeout`: Caller-requested timeout bound (cannot exceed capability ceiling).
- `metadata`: Supplemental caller metadata.

#### Architectural Guard: Forbidden Caller Keys
Callers are strictly forbidden from passing implementation-coupling keys in `CapabilityRequest`:
- `adapter_name`
- `mcp_server`
- `provider_name`
- `shell_command`
- `filesystem_path`

Any request containing these keys fails validation immediately before reaching any gateway or adapter.

### 2.2 `CapabilityResult`
The canonical output contract representing execution outcome:
- `request_id`: Echoed request identifier.
- `capability_id`: Executed capability identifier.
- `status`: `SUCCESS` or `FAILED`.
- `output`: Strongly-typed output payload validated against the capability's `output_contract`.
- `execution_metadata`: Audit metadata including `adapter_kind`, `implementation_id`, `target_storage_boundary`, `side_effects`, and `duration_ms`.
- `implementation_id`: Underlying implementation used (sanitized; no secrets).
- `started_at` / `completed_at`: Monotonic ISO timestamps.
- `duration_ms`: Wall-clock execution latency.
- `error`: Canonical `AIError` (code, message, retryable, details) if failed. Zero stack trace or secret leakage.

---

## 3. CapabilityRouter

The single entry point for all capabilities in the clean video production workspace:

```text
                  receive CapabilityRequest
                             │
                             ▼
                 validate architectural guards
                             │
                             ▼
                 resolve CapabilityDefinition
                             │
                             ▼
                branch on CapabilityCategory
               ┌─────────────┴─────────────┐
               ▼                           ▼
             MODEL               TOOL / DOMAIN_SERVICE
               │                           │
               ▼                           ▼
        ModelRouterSeam               ToolGateway
```

### Routing Rules:
1. **MODEL Category (1 Capability):**
   - Dispatches to `ModelRouterSeam`.
   - `SPEECH_TO_TEXT` routes via the seam, preserving the S28-M04 boundary without scope creep.
2. **TOOL Category (24 Capabilities):**
   - Dispatches to `ToolGateway` -> resolves authorized execution adapter (e.g., `MCPToolAdapter`, `NativeToolAdapter`, `RemoteAPIAdapter`).
3. **DOMAIN_SERVICE Category (7 Capabilities):**
   - Dispatches to `ToolGateway` -> resolves `DomainServiceAdapter` strictly.
   - Enforces that domain mutations and cache operations execute through `AssetService` and `RunService`. Never reaches raw MCP.

---

## 4. ToolGateway 15-Stage Execution Pipeline

Before any capability adapter is invoked, `ToolGateway` enforces a strict 15-stage pipeline:

```text
 Stage 1: Capability Lookup (Catalog verification)
    │
 Stage 2: Input Contract Resolution (resolve_input_contract)
    │
 Stage 3: Input Schema Validation (strict Pydantic, extra="forbid")
    │
 Stage 4: TenantContext Validation (cross-workspace & cross-project confinement)
    │
 Stage 5: Authorization Enforcement (required_permissions evaluation)
    │
 Stage 6: Resource Ownership Confinement (request vs input project consistency)
    │
 Stage 7: Side-Effects Policy Enforcement (full side_effects[] evaluation)
    ├── 7a. EXTERNAL_NETWORK: SSRF prevention, URL validation
    ├── 7b. PERSISTENT_WRITE: Storage boundary confinement
    └── 7c. SUBPROCESS: Safe argument vectors, command injection blocking
    │
 Stage 8: Budget & Payload Ceiling Policy (1MB payload limit)
    │
 Stage 9: Idempotency Enforcement (cache replay vs payload conflict detection)
    │
 Stage 10: Timeout & Cancellation Policy (asyncio.wait_for + context deadlines)
    │
 Stage 11: Adapter Selection (deterministic resolution via AdapterRegistry)
    │
 Stage 12: Adapter Execution (governed execution with circuit breaker)
    │
 Stage 13: Output Contract Validation (strict Pydantic, extra="forbid")
    │
 Stage 14: Storage & Domain Integrity Verification (no raw path leaks)
    │
 Stage 15: Telemetry & Structured Result Production (CapabilityResult)
```

---

## 5. Security & Isolation Invariants

### 5.1 Multi-Side-Effect Array Consumption
As mandated by **S28-M02.1**, all security, authorization, and resource policies consume the entire `side_effects[]` array:
- A capability declaring `[PERSISTENT_WRITE, SUBPROCESS, BACKGROUND_JOB]` is simultaneously subject to storage boundary checks, command argument vector restrictions, and async job lifecycle tracking.
- The scalar `side_effect_class` field is maintained solely for backwards compatibility and is never used as the sole authorization gate.

### 5.2 Anti-SSRF & Network Egress Validation
All external network capabilities undergo strict URL validation:
- Blocked Schemes: `file://`, `ftp://`, `gopher://`, `data:`, `javascript:`. Only `http://` and `https://` permitted.
- Blocked Hostnames: `localhost`, `ip6-localhost`, `metadata.google.internal`, `instance-data`, `*.local`, `*.internal`.
- Blocked IP Ranges: Loopback (`127.0.0.0/8`, `::1`), RFC1918 Private Subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), Link-Local (`169.254.0.0/16`), Multicast/Reserved.

### 5.3 Subprocess Safety & Parameter Injection Prevention
- Shell execution (`shell=True`) is completely forbidden.
- Argument vectors (`list[str]`) are strictly constructed by backend adapters from validated input parameters.
- Callers cannot supply `cmd`, `command`, `executable`, or `shell_args`.

### 5.4 Security-Blocked Implementations
Implementations identified as vulnerable during M01/M02 baseline audits are actively blocked at runtime:
- `CONCATENATE_VIDEOS` (`legacy_ffmpeg_mcp_server_concatenate_videos`): Contains verified shell injection vulnerability. Returns `AIErrorCode.CAPABILITY_UNAVAILABLE` with a security-blocked explanation. Clean rewrite scheduled for S28-M06.

---

## 6. Adapter Architecture

All execution adapters implement the abstract `CapabilityAdapter` interface:
```python
class CapabilityAdapter(ABC):
    name: str
    adapter_kind: str

    @abstractmethod
    def can_handle(self, capability: CapabilityDefinition, implementation: Optional[ImplementationDescriptor] = None) -> bool: ...

    @abstractmethod
    async def execute(self, request: CapabilityRequest, validated_input: AIContractModel, context: TrustedToolExecutionContext) -> Dict[str, Any]: ...

    async def cancel(self, request_id: str, context: TrustedToolExecutionContext) -> bool: ...
```

### Canonical Adapters:
1. **`DomainServiceAdapter` (`DOMAIN_SERVICE`):**
   - Routes `MUTATE_ASSET_STATUS`, `CHECK_MEDIA_CACHE`, `STORE_MEDIA_CACHE` to `AssetService`.
   - Routes `GET_JOB_STATUS`, `CANCEL_PROCESSING_JOB` to `RunService`.
   - Generates speech manifests and timelines.
   - Enforces that no MCP server ever mutates domain state.
2. **`MCPToolAdapter` (`COMPATIBILITY_MCP`):**
   - Bridges 20 media tools to legacy MCP server scripts safely.
   - Executes via safe subprocess argument vectors (`run_safe_subprocess`).
   - Normalizes outputs to match canonical Pydantic contracts.
3. **`NativeToolAdapter` (`NATIVE_PYTHON`):**
   - In-process verified Python routines.
4. **`RemoteAPIAdapter` (`REMOTE_API`):**
   - External stock media providers (Pexels, Pixabay, Freesound, Iconify).
   - Fails closed when required API credentials are absent.
5. **`WorkerToolAdapter` (`WORKER_QUEUE`):**
   - Background job dispatching for asynchronous media processing.

---

## 7. Migration & Compatibility Seam

| Capability | Legacy Implementation | S28-M03 Runtime Adapter | S28 Target Architecture |
|---|---|---|---|
| `TRIM_VIDEO` | `video-tools-mcp::trim_video` | `MCPToolAdapter` | S28-M06 Native FFmpeg Service |
| `CHECK_MEDIA_CACHE` | `common-tools-mcp::check_cache` | `DomainServiceAdapter` -> `AssetService` | S28 Domain Authority (ACTIVE) |
| `MUTATE_ASSET_STATUS` | `media-sources-mcp::change_asset_status` | `DomainServiceAdapter` -> `AssetService` | S28 Domain Authority (ACTIVE) |
| `SPEECH_TO_TEXT` | Embedded faster-whisper | `ModelRouterSeam` | S28-M04 LocalSTTProvider |
| `CONCATENATE_VIDEOS` | `ffmpeg-mcp-server::concatenate_videos` | **BLOCKED** (`SECURITY_BLOCKED`) | S28-M06 Native Safe Concat |
| Stock Searches (5) | `media-sources-mcp` | `RemoteAPIAdapter` | S28-M05 Rebuilt Stock Provider |
