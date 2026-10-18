# Security, Tenancy & Authority Bypass Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous security audit of authentication, authorization (RBAC), multi-tenancy (`TenantContext`), filesystem/command confinement policies, and authority bypass vectors across the repository.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

The security architecture of the video engine represents an ongoing consolidation between a local single-node CLI tool (Pre-S25) and a hardened multi-tenant SaaS backend (S26 through S28-R).

Key findings:
1. **Strong Filesystem and Subprocess Confinement**: Path traversal (`path_policy.py`) and command injection (`command_policy.py`) are centrally enforced and mathematically bounded. Arbitrary shell execution is blocked.
2. **Robust Multi-Tenant RBAC in S28-R Live Authoring**: The authoring subsystem derives tenant identity strictly from server-verified `TenantContext` and enforces CAS revisions.
3. **Critical Non-Production Authentication Backdoors**: In `api/core/auth.py`, when `MOTION_ENV != "production"`, callers can arbitrarily forge administrative identities using hardcoded token strings (`admin`, `system`) or unverified request headers (`X-Principal-ID`, `X-Principal-Roles`).
4. **CLI Authority Bypass**: The canonical pipeline script (`scripts/pipeline.py`) can be executed locally from the shell against any project without authentication, RBAC checks, or tenant validation.
5. **Disk vs. Database Tenancy Mismatch**: While `TenantRepository` models workspaces and projects in SQL, on disk all projects sit in a flat unpartitioned directory (`projects/{project_id}`).

---

## 2. Authentication & Authorization (RBAC) Architecture

### 2.1 Authentication Middleware & Token Verification (`api/core/auth.py`)

Authentication is managed via `extract_principal_from_request` and FastAPI dependency factories `require_permission` and `require_tenant_context`.

#### 2.1.1 Production Enforcement Mode (`is_production == True`)
- **Code Path**: `api/core/auth.py:228-233`
  ```python
  if is_production:
      return verify_signed_token(token, is_production=True)
  ```
- **Behavior**:
  - Validates cryptographically signed JWT tokens via `verify_signed_token()`.
  - Rejects unverified headers (`X-Principal-ID`) and client-asserted claim strings.
  - Enforces token expiration (`exp`) and cryptographic signature against `JWT_SECRET_KEY` [`CODE_PROVEN`].

#### 2.1.2 Development / Testing Backdoor Mode (`is_production == False`)
- **Code Path**: `api/core/auth.py:234-318`
- **Observed Fallbacks**:
  1. **Hardcoded Token Spoofing**:
     - `token in ("system", "system-token", "sys_worker")` returns a full `SYSTEM_WORKER` principal (`api/core/auth.py:240-241`).
     - `token.startswith("admin")` returns `admin_user` with global administrative scope `{"*": {Role.ADMIN}}` (`api/core/auth.py:243-250`).
     - `token.startswith("usr_")` returns an `EDITOR` principal without signature validation (`api/core/auth.py:252-259`).
  2. **Arbitrary Header Identity Spoofing**:
     - Callers can pass `X-Principal-ID: attacker`, `X-Principal-Roles: admin`, and `X-Principal-Type: HUMAN` to impersonate any user without credentials (`api/core/auth.py:266-305`).
- **Security Impact**:
  If a staging or development deployment fails to set `MOTION_ENV=production` explicitly, authentication is completely bypassed.

---

### 2.2 Role-Based Access Control (RBAC) & Tenant Derivation

The system defines 5 roles (`Role.ADMIN`, `Role.EDITOR`, `Role.REVIEWER`, `Role.CREATOR`, `Role.VIEWER`) and 25 distinct actions (`Action.PROJECT_CREATE`, `Action.RUN_EXECUTE`, `Action.AUTHORING_EDIT`, `Action.TEMPLATE_PROMOTE`, etc.).

#### 2.2.1 `require_tenant_context` vs. `require_permission` Asymmetry
A significant architectural drift exists in how routers enforce tenancy:
- **Strict Tenancy (`require_tenant_context`)**:
  - Used in: `api/routers/authoring.py`, `api/routers/candidate_promotions.py`, `api/routers/candidate_reviews.py`.
  - Derives `TenantContext` from authenticated principal membership in `TenantRepository`. If the principal is not a member of the workspace, it fails closed with `AccessDeniedError` (HTTP 403) [`CODE_PROVEN`].
- **Permissive Tenancy (`require_permission`)**:
  - Used in: `api/routers/projects.py`, `api/routers/runs.py`, `api/routers/assets.py`, `api/routers/artifacts.py`, `api/routers/outputs.py`, `api/routers/gates.py`.
  - Inspects permissions via `AuthorizationPolicy.enforce()`.
  - In `api/core/auth.py:324-342`, it attempts to attach `TenantContext` to `request.state` inside a `try ... except Exception: pass` block!
  ```python
  # api/core/auth.py:341-342
  except Exception:
      pass
  ```
  If `get_project(project_id)` throws or fails, the exception is silently swallowed, and the request proceeds with `request.state.tenant_context = None`!

---

## 3. Workspace Isolation & Storage Confinement

### 3.1 Dual-Tenancy Architecture (Database vs. Filesystem)

| Subsystem / Layer | Tenancy Enforcement Mechanism | Isolation Quality | Vulnerability / Bypass Point |
|---|---|---|---|
| **SQL Database (`TenantRepository`)** | `workspaces` table, `projects` table (`workspace_id`), foreign key constraints. | **STRONG** (`CODE_PROVEN`) | None in SQL; queries strictly filter by `workspace_id`. |
| **Object Storage (`StorageService`)** | Object keys prefixed with `workspaces/{workspace_id}/projects/{project_id}/...`. | **STRONG** (`CODE_PROVEN`) | Enforces key schema and prevents cross-tenant path traversal. |
| **Local Filesystem (`projects/`)** | Flat directory structure: `projects/{project_id}/`. | **WEAK** (`CODE_PROVEN`) | Projects are NOT partitioned by workspace folder on disk (`projects/ws_1/prj_1` does not exist). Any process accessing `projects/` directly can read any project regardless of workspace boundaries. |
| **Worker Subprocess Execution** | Worker sets `AGY_WORKSPACE_ID` environment variable. | **MODERATE** (`CODE_PROVEN`) | Subprocess receives workspace ID, but `scripts/pipeline.py` does not perform database lookups to verify project-workspace pairing. |

---

## 4. Path Traversal & Subprocess Confinement Policies

### 4.1 Path Security Confinement (`scripts/core/security/path_policy.py`)
- **Strict Identifier Validation**:
  - `validate_project_id(project_id)`: enforces regex `^[a-zA-Z0-9_-]+$`.
  - `validate_asset_id(asset_id)`: enforces regex `^[a-zA-Z0-9_-]+$`.
  - Rejects `..`, `/`, `\`, and Windows drive letters (`C:`) [`CODE_PROVEN`].
- **Safe Resolution Boundary**:
  - `resolve_safe_path(base_dir, user_path)`: calls `.resolve()` and enforces `resolved.relative_to(base)`.
  - Traversal attempts throw `ValueError("Path traversal detected (escapes base)")` [`CODE_PROVEN`].

### 4.2 Subprocess Confinement Policy (`scripts/core/security/command_policy.py`)
- **Canonical Execution Wrapper**: `safe_subprocess()` in `scripts/security/security.py`.
- **Command Whitelisting**:
  - Whitelists: `python`, `node`, `npx`, `ffmpeg`, `ffprobe`, `docker`.
  - Enforces `shell=False` unconditionally to prevent shell injection.
  - Sanitizes environment variables to prevent `LD_PRELOAD` or malicious `PATH` injection [`CODE_PROVEN`].

---

## 5. Authority Bypass Vectors & Attack Surface

### 5.1 Bypass Vector 1: Direct CLI Subprocess Execution
- **Mechanism**:
  A user, agent, or cron job with shell access executes:
  ```bash
  python scripts/pipeline.py <project_id>
  ```
- **Reality**:
  `scripts/pipeline.py` requires no JWT token, no API key, and no user principal. It directly loads `projects/{project_id}/.pipeline_state.json` and runs all gates.
- **Classification**: `RUNTIME_REACHABILITY_PROVEN` (Intentional design for local worker execution, but constitutes an authorization bypass in multi-tenant environments).

### 5.2 Bypass Vector 2: Unauthenticated Dev Headers in Non-Production
- **Mechanism**:
  Deploying the API without `MOTION_ENV=production` allows any HTTP client to send:
  ```http
  POST /projects/prj_victim/mutate HTTP/1.1
  X-Principal-ID: attacker
  X-Principal-Roles: admin
  ```
- **Reality**:
  FastAPI middleware in `api/core/auth.py:298` automatically constructs an administrative principal, bypassing all tenant checks.

### 5.3 Bypass Vector 3: Silent Exception in Permissive Tenant Context
- **Mechanism**:
  In `api/core/auth.py:341`, database lookups for `TenantContext` in `require_permission` routes are wrapped in `try ... except Exception: pass`.
- **Reality**:
  If the database connection is intermittent or drops, the route executes without a tenant context rather than failing closed.

---

## 6. Secrets Management & Provider Leak Prevention

### 6.1 Secrets Scanning & CI Enforcement
- **Gate**: `scripts/validators/check_secrets.py` runs in CI (`.github/workflows/remediation-ci.yml:254`).
- **Scope**: Scans git diffs and codebase files for high-entropy strings, AWS keys, OpenAI keys, Replicate tokens, and ElevenLabs credentials.
- **Result**: `CI_PROVEN` code cleanliness; zero live secrets committed in source tree.

### 6.2 Provider Bypass Hardening
- Legacy tools in `.agents/plugins/super-video-maker-plugin/tools/` (`elevenlabs_voice.py`, `replicate_video.py`) contain active runtime blockers:
  `raise PermissionError("DIRECT SECRET ACCESS BLOCKED: Raw ELEVENLABS_API_KEY access outside canonical S27 capability adapters is prohibited.")`.
- AST guards in `tests/ai/contracts/test_provider_bypass_guards.py` enforce that no script can read raw environment variables to contact external LLM or media APIs without going through `CapabilityRouter` [`TEST_PROVEN`].

---

## 7. Remediation Direction (DO NOT FIX YET)

To achieve enterprise multi-tenant hardening in a future milestone:
1. **Remove Non-Production Auth Backdoors**:
   Deprecate hardcoded token parsing (`admin`, `system`) and `X-Principal-*` headers. Require cryptographic token validation across all environments, using ephemeral dev keys for testing.
2. **Harmonize Tenancy Enforcement**:
   Replace `try ... except Exception: pass` in `require_permission` with fail-closed error handling (`raise HTTPException(status_code=500, detail="Tenant context resolution failed")`).
3. **Partition Disk Workspaces**:
   Restructure local project workspaces from `projects/{project_id}` to `projects/{workspace_id}/{project_id}` to match `StorageService` keys.
4. **Authorize CLI Invocations**:
   Require `scripts/pipeline.py` to accept and verify a signed run token or service principal when invoked outside the internal worker daemon.
