# Fallback, Default Bypass & Silent Failure Audit Report
- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Repository-wide sweep for silent `except: pass`, masked error handling, multi-tier fallback chains, default constructor injections, optional imports, and bypass environment flags.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

A comprehensive, automated, and manual sweep across the repository identified **144 silent `except: pass` or error-swallowing blocks**, multiple complex **multi-tier fallback chains**, and widespread **default injections** that mask missing production wiring and decoupled subsystems:

1. **Silent Storage Upload Swallowing (`AssetService`)**: In `api/services/asset_service.py:171-172`, failures during object storage uploads (`StorageService.put`) are silently swallowed with `except Exception: pass`. The API returns HTTP 200/201 success to the caller while leaving the object unpersisted in cloud/remote storage.
2. **Silent Database Synchronization Swallowing (`StateStore`)**: In `scripts/core/state_store.py:221-222`, if reflecting state changes to the relational database engine fails, the error is swallowed with `# Non-fatal if database is unconfigured ... pass`.
3. **Tenant Context Fallback (`RunService` & `Auth`)**: In `api/services/run_service.py:86-88` and `api/core/auth.py:341,374`, failures to resolve a project or workspace ID silently fall back to hardcoded default values (`"ws_default"`, `"usr_system"`), undermining tenant isolation guarantees under failure conditions.
4. **Three-Tier Render Fallback Chain (`scripts/render_project.py`)**: The system attempts to render through modern `RenderPlanner` (S28-R14), but on ANY exception silently catches it and falls back to `RemotionRendererAdapter` (S28-R09), and on another exception falls back to legacy `npx remotion render`.
5. **Decoupled AI Platform Defaults**: The AI subsystem (`ContextBuilder`, `ModelRouter`, `CapabilityRouter`, `ToolGateway`) provides internal fallback defaults (`DeterministicKnowledgeRetriever`, `DeterministicTokenEstimator`) that enable tests to pass in isolation without real production wiring.

---

## 2. Silent `except: pass` & Error Swallowing Audit

A syntax and AST scan reveals 144 instances of `except: pass` or `except Exception: pass` across non-test Python files. The most critical occurrences that directly impact production data integrity and security are cataloged below.

### 2.1 Critical Production Silent Exception Inventory

| File Path | Line Range | Exception Caught | Swallowed Action | Production Reality & Risk | Evidence Citation |
|---|---|---|---|---|---|
| `scripts/core/state_store.py` | 218-223 | `Exception` (non-`StateConflictError`) | Database state reflection (`_sync_to_db`) | State updates save to local JSON on disk, but DB table `project_states` silently desynchronizes without error. | `scripts/core/state_store.py:221-222` [`CODE_PROVEN`] |
| `api/services/asset_service.py` | 153-161 | `Exception` | Workspace lookup from DB | If DB query fails, workspace ID silently defaults to `"ws_default"`. | `api/services/asset_service.py:160` [`CODE_PROVEN`] |
| `api/services/asset_service.py` | 165-173 | `Exception` | `StorageService.put()` | If cloud or local storage upload fails, `storage_key` remains `None`; file is saved only to local disk. | `api/services/asset_service.py:171-172` [`CODE_PROVEN`] |
| `api/services/run_service.py` | 80-87 | `Exception` | `TenantRepository.get_project()` | If project lookup fails, run record is created under `"ws_default"` instead of the owning tenant. | `api/services/run_service.py:86` [`CODE_PROVEN`] |
| `api/core/auth.py` | 330-342 | `Exception` | TenantContext derivation | If DB lookup fails during authorization, `request.state.tenant_context` remains `None` without denying access. | `api/core/auth.py:341` [`CODE_PROVEN`] |
| `api/core/auth.py` | 370-375 | `Exception` | Auto-creating personal workspace | If creating `ws_{principal_id}` fails, error is swallowed, leading to subsequent membership denial. | `api/core/auth.py:374` [`CODE_PROVEN`] |
| `api/services/pipeline_service.py` | 95-102 | `Exception` | Reading legacy GUI state from disk | Swallows malformed JSON errors during legacy GUI state fallback. | `api/services/pipeline_service.py:100` [`CODE_PROVEN`] |
| `api/services/pipeline_service.py` | 258-266 | `Exception` | Parsing JSON state from subprocess stdout | If gate subprocess emits invalid JSON, stdout state update is silently dropped. | `api/services/pipeline_service.py:265` [`CODE_PROVEN`] |
| `api/services/pipeline_service.py` | 345-350 | `Exception` | Loading `02_asset_manifest.json` | If loading manifest fails, sets `man = None`, validating blueprint without asset verification! | `api/services/pipeline_service.py:349` [`CODE_PROVEN`] |
| `api/services/health_service.py` | 134-138 | `Exception` | `RunRepository` bootstrap initialization | Swallows DB initialization failure in `/health/ready` check. | `api/services/health_service.py:137` [`CODE_PROVEN`] |
| `api/services/health_service.py` | 285-298 | `Exception` | Lease heartbeat timestamp parsing | If timestamp parsing fails, worker liveness probe drops into stale fallback. | `api/services/health_service.py:297` [`CODE_PROVEN`] |
| `api/services/output_service.py` | 65-75 | `Exception` | `StorageService.get(key)` | If storage fetch fails, swallows exception and raises generic 404 Not Found. | `api/services/output_service.py:74` [`CODE_PROVEN`] |

---

## 3. Multi-Tier Fallback Chains & Degradation Cascades

### 3.1 The Three-Tier Video Render Fallback Chain

In `scripts/render_project.py:127-186`, video rendering executes through a three-tier fallback cascade:

```
[Incoming Render Request]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ Tier 1: S28-R14 Multi-Engine RenderPlanner & Compositor│
│ Command: npx tsx scripts/render_via_planner.ts         │
└────────────────────────────────────────────────────────┘
          │ (on Exception: logs warning, catches ALL)
          ▼
┌────────────────────────────────────────────────────────┐
│ Tier 2: S28-R09 RemotionRendererAdapter                │
│ Command: npx tsx scripts/render_via_adapter.ts         │
└────────────────────────────────────────────────────────┘
          │ (on Exception: logs warning, catches ALL)
          ▼
┌────────────────────────────────────────────────────────┐
│ Tier 3: Legacy Direct Remotion CLI Execution           │
│ Command: npx remotion render src/index.ts              │
└────────────────────────────────────────────────────────┘
```

#### Verbatim Code Evidence (`scripts/render_project.py:136-186`):
```python
if not use_legacy and planner_script.exists():
    try:
        # Tier 1
        safe_subprocess(cmd_planner, ...)
        render_success = True
    except Exception as ex:
        print(f"⚠️ فشل مسار Multi-Engine Planner ({ex}) — تجربة مسار Adapter الفردي...")

if not render_success and not use_legacy and adapter_script.exists():
    try:
        # Tier 2
        safe_subprocess([npx_cmd, "tsx", str(adapter_script), ...], ...)
        render_success = True
    except Exception as ex:
        print(f"⚠️ فشل مسار Adapter ({ex}) — تفعيل جسر التوافق (Legacy Remotion CLI)...")

if not render_success:
    # Tier 3 (Fallback)
    result = safe_subprocess([npx_cmd, "remotion", "render", ...], ...)
```

#### Architectural Assessment:
- **Masking Render Failures**: If the modern TypeScript RenderPlanner or MasterCompositor has syntax errors, runtime crashes, or missing dependencies, the build does not fail. It silently drops down to legacy Remotion CLI.
- **Bypass Flag**: Setting environment variable `USE_LEGACY_RENDER_PATH=1` or command line flag `--legacy-cli` completely bypasses Tiers 1 and 2 without running the modern pipeline.

---

## 4. Default Injections and Protocol Stubs in Core Registries

A major architectural observation is that all core AI subsystems provide default fallback implementations in their constructors. When instantiated without parameters (as occurs in standalone unit tests), they initialize deterministic stubs rather than failing closed.

### 4.1 Subsystem Default Fallback Matrix

| Subsystem | Constructor Location | Parameter | Default Fallback Value | Behavioral Impact |
|---|---|---|---|---|
| `ContextBuilder` | `ai/context/builder.py:77` | `knowledge_retriever` | `DeterministicKnowledgeRetriever()` | Returns hardcoded static knowledge snippets without hitting KnowledgeRouter. |
| `ContextBuilder` | `ai/context/builder.py:84` | `token_estimator` | `DeterministicTokenEstimator()` | Returns heuristic string length token counts without model tokenizers. |
| `ContextBuilder` | `ai/context/builder.py:85` | `compressor` | `DeterministicContextCompressor()` | Truncates text deterministically without NLP or semantic summarization. |
| `KnowledgeRouter`| `ai/knowledge/router.py:65` | `registry` | `KnowledgeRegistry()` | Creates empty in-memory registry rather than binding to production database. |
| `KnowledgeRouter`| `ai/knowledge/router.py:68` | `loader` | `KnowledgeLoader(workspace_root=...)` | Binds to local disk filesystem rather than managed object storage. |
| `ModelRouter` | `ai/routing/router.py:80` | `model_registry` | `get_model_registry()` | Binds to static frozen singleton `CANONICAL_MODELS`. |
| `ModelRouter` | `ai/routing/router.py:81` | `provider_registry` | `get_provider_registry()` | Binds to static frozen singleton `CANONICAL_PROVIDERS`. |
| `CapabilityRouter`| `ai/routing/capability_router.py:84` | `tool_gateway` | `ToolGateway(catalog=...)` | Auto-instantiates ToolGateway without external DI container. |
| `ToolGateway` | `ai/tools/gateway.py:256` | `idempotency_store` | `_default_idempotency_store` | Defaults to in-memory `InMemoryIdempotencyStore`. |
| `RecipeRegistry` | `ai/recipes/registry.py:106` | `recipe_dir` | Local `recipes/` folder | Automatically parses JSON files from disk on boot. |

---

## 5. Optional Imports & Soft Dependency Bypasses

Seven files in the repository utilize `try: import ... except ImportError:` patterns to allow execution in environments where dependencies are missing:

1. **FastMCP Compatibility Server (`ai/mcp/compatibility/server.py:89-94`)**:
   ```python
   try:
       from mcp.server.fastmcp import FastMCP
   except ImportError:
       logger.warning("mcp package not installed in current environment; FastMCP instance unavailable.")
       return None
   ```
   If `mcp` is not installed, calling `create_fastmcp_instance()` silently returns `None` rather than failing closed with an explicit configuration error.

2. **Fal Seedance Video Wrapper (`.agents/plugins/super-video-maker-plugin/tools/fal_seedance_video.py:82-94`)**:
   ```python
   try:
       import fal_client
   except ImportError:
       emit({"status": "failed", "error": "fal-client is not installed..."})
       sys.exit(2)
   ```
   Fails with custom exit code 2 if `fal-client` is missing.

3. **Contract Generators (`scripts/generate_ai_contracts.py:35-39`)**:
   ```python
   try:
       import pydantic
   except ImportError:
       os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)
   ```
   Auto-respawns into virtualenv Python if Pydantic is not found in ambient interpreter.

---

## 6. Bypass Flags, Environment Variables & Execution Escape Hatches

The following environment variables and runtime flags act as execution bypasses across the codebase:

| Flag / Env Var | Target Component | Default Behavior | Bypass Behavior When Set | Safety Classification |
|---|---|---|---|---|
| `SKIP_STRICT_QC` | `scripts/core/security/env_policy.py:40` | QC fails closed on defect. | Historically converted QC failures to exit 0 (LED-022). Now restricted in production by `EnvPolicy`. | **CRITICAL SECURITY RISK** (Banned in prod) |
| `USE_LEGACY_RENDER_PATH` | `scripts/render_project.py:128` | Uses `RenderPlanner` & `MasterCompositor`. | Skips modern render planner and executes legacy Remotion CLI directly. | **HIGH DRIFT RISK** |
| `--legacy-cli` | `scripts/render_project.py:128` | Uses modern planner. | CLI flag skipping RenderPlanner. | **HIGH DRIFT RISK** |
| `AGY_IS_MANAGED` | `scripts/pipeline.py:108` | Requires review approval or CLI prompt. | Marks execution as daemon-managed; disables interactive prompts. | `ACTIVE_PRODUCT_RUNTIME` |
| `AGY_FAILURE_INJECTION_ENABLED` | `scripts/core/failure_injection.py:26` | Failure injection disabled. | Enables simulated crash points during pipeline stages. (Fails closed in prod). | `DEV_ONLY` |
| `AGY_INJECT_FAILURE` | `scripts/core/failure_injection.py:30` | None. | Injects specific error (e.g. `before_render:attempt=1`). | `DEV_ONLY` |
| `AGY_EPHEMERAL_WORKSPACE` | `scripts/core/worker.py:280` | Uses project dir. | Runs execution inside ephemeral tempdir, wiping scratch on finish. | `ACTIVE_PRODUCT_RUNTIME` |

---

## 7. Architectural Impact Assessment

1. **Masked Disconnection**: The extensive use of constructor defaults in `ai/` (`DeterministicKnowledgeRetriever`, etc.) allowed the AI subsystem to achieve near-100% test pass rates in isolated unit tests despite having **ZERO runtime integration** into FastAPI (`api/main.py`) or the worker pipeline (`scripts/pipeline.py`).
2. **False Operational Health**: Because `AssetService.upload_asset()` catches `StorageService.put()` exceptions silently (`api/services/asset_service.py:171`), an AWS S3 outage or MinIO credentials misconfiguration would not surface as an HTTP 500 error to end users; instead, assets would be saved locally and lost upon worker container destruction.
3. **Desynchronized Databases**: Because `StateStore._sync_to_db()` swallows non-CAS exceptions (`scripts/core/state_store.py:221`), disk-based projects can proceed through pipeline stages while the relational database `project_states` table remains stale or empty.

---

## 8. Verification Methods and Reproducible Commands

To independently reproduce and verify the findings in this report:

1. **Verify AssetService Silent Storage Swallowing**:
   ```bash
   sed -n '165,174p' api/services/asset_service.py
   # Observe: try storage.put() except Exception: pass
   ```

2. **Verify StateStore Silent DB Synchronization Swallowing**:
   ```bash
   sed -n '218,224p' scripts/core/state_store.py
   # Observe: except Exception as e: ... pass
   ```

3. **Verify Render Project Three-Tier Fallback Chain**:
   ```bash
   sed -n '127,186p' scripts/render_project.py
   # Observe: planner -> adapter -> legacy remotion CLI cascade
   ```

4. **Verify RunService Workspace Fallback**:
   ```bash
   sed -n '79,88p' api/services/run_service.py
   # Observe: except Exception: pass; actual_ws_id = actual_ws_id or "ws_default"
   ```
