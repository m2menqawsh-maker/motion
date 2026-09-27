# Trust Model and Security Architecture Specification

## Document Metadata
- **Document ID:** SEC-DOC-001
- **Status:** APPROVED & CANONICAL
- **Target Baseline:** S01 Scaffolding & S02 Implementation
- **Author:** Lead Architect / CTO
- **Scope:** Video Maker System Security, Identity, Authorization, and Execution Boundaries

---

## 1. System Context and Source of Truth Hierarchy

In accordance with the constitutional principles defined in `ARCHITECTURE_TRUTH.md` and `AGENTS.md`, this document establishes the formal Trust Model, Identity Abstraction, and Command Execution Policy for the Clean Video Workspace.

### Source of Truth Hierarchy:
1. **Runtime / Executable Behavior** (The ultimate truth of what actually runs)
2. **Tests** (Automated enforcement of runtime contracts)
3. **ARCHITECTURE_TRUTH.md** (What the system IS)
4. **TRUST_MODEL.md** (This document: Security boundaries, Identity, and Authorization contracts)
5. **AGENTS.md** (How agents and operators MUST interact with the system)
6. **references/** (How-to guides)
7. **archive/** (Historical, non-actionable context)

---

## 2. Actors and Security Entities

The system identifies and interacts with ten distinct security entities:

| Actor | Type | Description | Trust Level |
| :--- | :--- | :--- | :--- |
| **Human User** | External Principal | Video creator, designer, or stakeholder interacting via Web UI or API client. | **Untrusted** until authenticated via session / JWT. |
| **Reviewer** | External Principal | Authorized human designated to review and approve/reject stage gates (e.g. Taste Gate, Probe QC, Studio Review). | **Untrusted** until authenticated; holds specialized `reviewer` role. |
| **Operator / Admin** | External Principal | System administrator or operations engineer managing server configuration, batch pipelines, and emergency controls. | **Untrusted** until authenticated; holds `operator` or `admin` role. |
| **API Process** | Internal Process | The FastAPI/Uvicorn server receiving external HTTP/WebSocket requests, enforcing authentication, and dispatching commands. | **Trusted Boundary Enforcer** (runs on host). |
| **Worker Process** | Internal Process | Independent background process leasing and executing pipeline stages, heavy FFmpeg renders, and Remotion video builds. | **Trusted Execution Worker** (runs on host). |
| **CLI** | Local Tooling | Developer or operator executing command-line scripts directly on the host (`python scripts/pipeline.py`). | **Trusted Local Operator** (executes under host user context). |
| **Agent** | Automated Assistant | AI coding assistant operating within `.agents/` adhering strictly to canonical directives. | **Semi-Trusted** (restricted to approved tools and MCP servers; cannot bypass gates). |
| **External Media Provider** | External Service | Third-party media APIs (Pexels, Pixabay, Freesound, ElevenLabs, HeyGen). | **Untrusted Source**; all downloaded bytes must be verified and sanitized. |
| **Local Filesystem** | Operating System | Host filesystem hosting `/projects`, `/templates`, `/assets`, `/scratch`, and logs. | **Confined Storage Domain**; must be protected against directory traversal and symlink escapes. |
| **Remotion Runtime** | Sandboxed Execution | Node.js and headless Chromium environment executing React components to render video frames. | **Constrained Execution Sandbox**; must not receive unrestricted shell or arbitrary code injection. |

---

## 3. Trust Boundaries and Data Flows

Data and control signals cross multiple trust boundaries. Every transition from an outer boundary to an inner boundary requires strict validation, sanitization, and transformation into a typed internal representation.

```
                           +-----------------------------------------------+
                           |                 UNTRUSTED ZONE                |
                           |   HTTP Requests, Query Params, Raw Files      |
                           +-----------------------+-----------------------+
                                                   |
                                                   v [Boundary A: Ingress & Auth]
                           +-----------------------------------------------+
                           |            AUTHENTICATION MIDDLEWARE          |
                           |      Token / Session Verification             |
                           +-----------------------+-----------------------+
                                                   |
                                                   v [Boundary B: Identity Construction]
                           +-----------------------------------------------+
                           |              VERIFIED PRINCIPAL               |
                           |   (principal_id, roles, project_scopes)       |
                           +-----------------------+-----------------------+
                                                   |
                                                   v [Boundary C: Authorization Interceptor]
                           +-----------------------------------------------+
                           |             AUTHORIZATION POLICY              |
                           |   Can Principal X do Action Y on Project Z?   |
                           +-----------------------+-----------------------+
                                                   |
                                                   v [Boundary D: Domain Service Core]
                           +-----------------------------------------------+
                           |                DOMAIN SERVICES                |
                           |   PipelineService, ProjectService, GateService|
                           +-----------+-----------------------+-----------+
                                       |                       |
           [Boundary E: Storage Conf.] |                       | [Boundary F: Process Confinement]
                                       v                       v
                           +-----------------------+   +-----------------------+
                           |  DURABLE STATE STORE  |   | COMMAND POLICY ENGINE |
                           |  & ASSET REPOSITORY   |   | (Subprocess Allowlist)|
                           +-----------------------+   +-----------+-----------+
                                                                   |
                                                                   v
                                                       +-----------------------+
                                                       |    WORKER PROCESS     |
                                                       | (Remotion, FFmpeg, QC)|
                                                       +-----------------------+
```

### 3.1 Trust Boundary A: HTTP Ingress & Transport
- **Incoming:** Raw HTTP packets, request headers, cookies, query parameters, multipart form bodies.
- **Rule:** All input is fundamentally untrusted.
- **Enforcement:**
  - Transport Layer Security (HTTPS/TLS) in production.
  - Strict payload validation using Pydantic schemas.
  - Rejection of oversized payloads (>500MB for media uploads, >10MB for JSON manifests).
  - Complete strip / rejection of user-supplied identity parameters (`approved_by`, `by`, `actor`, `user`).

### 3.2 Trust Boundary B: Principal & Identity
- **Transition:** Cryptographic credentials (HMAC-SHA256 Signed Bearer Token) -> Server-verified `Principal`.
- **Rule:** A `Principal` instance can only be minted by the Authentication subsystem after cryptographic verification. Client-provided claims are not trusted claims. Domain logic never reads credentials directly.
- **Enforcement (S02):**
  - Production tokens follow `<base64url_payload>.<base64url_hmac_sha256>`.
  - Signature verification using `AUTH_SECRET_KEY` (minimum 32 chars) is strictly executed BEFORE parsing or trusting any claim.
  - Expiration (`exp`), non-empty identity (`sub`), recognized roles, and safe project scopes are strictly validated.
  - Unsigned development headers (`X-Principal-*`) are strictly rejected in production.

### 3.3 Trust Boundary C: Authorization
- **Transition:** `(Principal, Action, Target Project)` -> Allowed / Denied.
- **Rule:** No domain operation executes unless explicit authorization is verified. Role privileges must match the specific project scope.

### 3.4 Trust Boundary D: Domain Service & Data Models
- **Transition:** Raw request dictionary -> Validated Domain Entity (`ProjectState`, `Blueprint`, `BrandConfig`).
- **Rule:** Domain models enforce structural integrity, schema compliance, and state invariants before persistence.

### 3.5 Trust Boundary E: Filesystem & Path Confinement
- **Transition:** User-supplied paths, asset filenames, or template IDs -> Resolved filesystem `Path`.
- **Rule:**
  - Absolute paths supplied by clients are forbidden.
  - Relative paths containing `..` or leading slashes are forbidden.
  - All file access must be strictly confined within the designated root (`projects/<project_id>/` or `assets/`).
  - Symlinks pointing outside the project root must be rejected and refused (`symlink_escape`).

### 3.6 Trust Boundary F: Process Execution & Subprocesses
- **Transition:** Pipeline execution request -> OS command execution (`subprocess.run`).
- **Rule:**
  - `shell=True` is completely prohibited across the codebase.
  - Executable allowlisting alone is insufficient; commands are validated by `(Executable + Subcommand + Validated Arguments)`.
  - Dangerous flags (e.g. `-c`, `--eval`, shell redirects, unconfined Docker volume mounts) are rejected.
  - Mandatory timeout and output size caps are enforced on every subprocess.

### 3.7 Trust Boundary G: Quality & Approval Gates
- **Transition:** Stage transition -> Next lifecycle state.
- **Rule:**
  - Quality gates cannot be bypassed via environment variables (`SKIP_STRICT_QC`, `AGY_IS_MANAGED`).
  - Review approvals require a verified `reviewer` Principal.
  - In S09, approvals are cryptographically bound to the review bundle hashes.

---

## 4. Principal Data Contract

The `Principal` abstraction is the uniform representation of identity across the entire system.

### 4.1 Principal Attributes
Every authenticated caller is represented by a `Principal` object:

```python
class PrincipalType(str, Enum):
    HUMAN = "HUMAN"
    SERVICE = "SERVICE"
    SYSTEM_WORKER = "SYSTEM_WORKER"
    ANONYMOUS = "ANONYMOUS"

class Role(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    ADMIN = "admin"

class Principal(BaseModel):
    principal_id: str                      # Unique persistent identifier (e.g. "usr_104829", "svc_transcoder")
    principal_type: PrincipalType          # HUMAN, SERVICE, or SYSTEM_WORKER
    roles: Set[Role]                       # Global default roles (e.g. {Role.VIEWER})
    project_scopes: Dict[str, Set[Role]]   # Project-specific roles: {"proj_xyz": {Role.REVIEWER}}
    auth_method: str                       # "BEARER_JWT", "SESSION_COOKIE", "SERVICE_TOKEN", "INTERNAL"
    issued_at: datetime                    # Timestamp credential was minted
    expires_at: Optional[datetime]         # Credential expiration
    metadata: Dict[str, Any]               # Additional claims (email, name, client IP)
```

### 4.2 Human vs. Service Principal Rules
1. **Human Principal:**
   - Must have an identifiable user ID, name/email in metadata, and a bounded session lifetime.
   - Used for UI workflows, manual approvals, and interactive reviews.
   - Authenticated via server-verified HMAC-SHA256 signed bearer tokens in S02, with clean replacement path for future OIDC/OAuth2 providers.
2. **Service Principal:**
   - Represents an automated system, cron daemon, or webhook bridge.
   - Identified by a machine ID (`svc_...`).
   - Must never hold the `reviewer` role for human-mandated gates unless an automated QC policy explicitly designates it as an automated validator.
3. **No Shared Static API Keys for Human Identity:**
   - A static shared API key cannot represent individual humans.
   - If an API key is used, it maps strictly to a `SERVICE` Principal with audited machine scope.

---

## 5. Authorization Model & Permission Matrix

### 5.1 System Actions
The system governs eleven distinct action categories:

1. `PROJECT_READ`: View project metadata, stage status, and directory layout.
2. `PROJECT_EDIT`: Update project settings, brand colors, fonts, or overrides.
3. `PROJECT_CREATE`: Scaffold a new project directory and state.
4. `PROJECT_DELETE`: Archive or delete a project.
5. `ASSET_READ`: List or inspect media assets.
6. `ASSET_MODIFY`: Upload, transcode, or delete project assets.
7. `BLUEPRINT_READ`: Inspect `05_blueprint.json` and timeline recipes.
8. `BLUEPRINT_EDIT`: Update or regenerate the blueprint.
9. `RUN_EXECUTE`: Trigger pipeline stages (`start_stage`, `finish_stage`, `pipeline.py`).
10. `RUN_CANCEL`: Abort an active render or pipeline run.
11. `QC_VIEW`: Inspect QC reports, probe logs, and taste metrics.
12. `REVIEW_APPROVE`: Formally approve a stage review gate (e.g. Gate 3 / `.studio_approved`).
13. `REVIEW_REJECT`: Formally reject a stage review gate with mandatory rationale.
14. `RENDER_ACCESS`: Trigger final Remotion render and download `out.mp4`.
15. `SYSTEM_ADMIN`: Modify global configuration, inspect secrets, view audit logs.

### 5.2 Canonical Permission Matrix

| Action | `viewer` | `editor` | `reviewer` | `operator` | `admin` |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `PROJECT_READ` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `PROJECT_CREATE` | ❌ | ✅ | ❌ | ✅ | ✅ |
| `PROJECT_EDIT` | ❌ | ✅ | ❌ | ❌ | ✅ |
| `PROJECT_DELETE` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `ASSET_READ` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ASSET_MODIFY` | ❌ | ✅ | ❌ | ❌ | ✅ |
| `BLUEPRINT_READ` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `BLUEPRINT_EDIT` | ❌ | ✅ | ❌ | ❌ | ✅ |
| `RUN_EXECUTE` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `RUN_CANCEL` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `QC_VIEW` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **`REVIEW_APPROVE`** | ❌ | ❌ | **✅** | ❌ | **✅** |
| **`REVIEW_REJECT`** | ❌ | ❌ | **✅** | ❌ | **✅** |
| `RENDER_ACCESS` | ✅ (view) | ✅ | ✅ | ✅ (trigger) | ✅ |
| `SYSTEM_ADMIN` | ❌ | ❌ | ❌ | ❌ | ✅ |

### 5.3 Explicit Non-Hierarchical Invariants
- An `editor` cannot approve reviews (`REVIEW_APPROVE`). Content creators cannot approve their own gates without independent review authorization.
- A `reviewer` cannot modify blueprints or assets unless they also explicitly hold the `editor` role.
- An `operator` can run and cancel jobs, but cannot approve review gates.
- Only `admin` holds unconstrained cross-role capabilities.

---

## 6. Project Isolation Contract

### 6.1 The Core Authorization Question
Every domain request must answer:
$$\text{Can Principal } P \text{ perform Action } A \text{ on Project } Z?$$

### 6.2 Scope Resolution Rules
1. **Global Admin:** If $P$ possesses `Role.ADMIN` globally (`P.roles`), the action is **allowed**.
2. **Project-Bound Roles:** If $P$ possesses role $R$ within $P.\text{project\_scopes}[Z]$, and $R$ grants action $A$ in the Permission Matrix, the action is **allowed**.
3. **Global Role Fallback:** Global roles (`P.roles`) only apply to project-level actions if explicitly scoped with wildcard `*` or if the role is a global read role (`Role.VIEWER` with public project visibility).
4. **Default Deny:** If neither (1), (2), nor (3) is satisfied, access is **DENIED** with HTTP 403 Forbidden.

---

## 7. Approval Identity Contract (DEC-04 & Future S09 Binding)

### 7.1 Rejection of Request Identity Parameters
- Endpoints `POST /gates/{project_id}/approve/{gate}` and `POST /gates/{project_id}/reject/{gate}` must NOT accept `by: str` or `approved_by: str` from the client.
- Any client attempting to supply `approved_by` in the request body, header, or query string will have the field completely ignored or rejected with HTTP 422.
- The `actor_id` recorded in `.pipeline_state.json` and gate history is strictly populated from `principal.principal_id`.

### 7.2 Reviewer Gate Invariant
- A gate approval is valid if and only if:
  1. `principal.principal_type == PrincipalType.HUMAN` (or an audited, approved automated validator).
  2. The principal holds `Role.REVIEWER` or `Role.ADMIN` within the target project scope.
  3. The target gate requires review and is in the `READY_FOR_REVIEW` state.

### 7.3 Future S09 Review Bundle Integration
In S09, the approval contract will mandate cryptographic verification of the Review Bundle:
- `review_bundle_hash = SHA256(blueprint_hash + probe_qc_hash + render_preview_hash)`
- The approval record will persist:
  `{ actor: principal.principal_id, timestamp: ISO8601, bundle_hash: review_bundle_hash, revision: state_revision }`

---

## 8. Command Execution Policy & Subprocess Confinement

### 8.1 Prohibited Operations
- ❌ **TOTAL BAN on `shell=True`:** No command may be executed through a system shell.
- ❌ **TOTAL BAN on raw code execution:** Commands passing `-c`, `--eval`, or executing arbitrary user strings via `python -c` or `node -e` are prohibited.
- ❌ **TOTAL BAN on unconstrained docker commands:** Commands such as `docker exec`, `docker volume rm`, or arbitrary containers are prohibited.

### 8.2 Executable Allowlist and Parameter Validation
Every subprocess call must pass through the canonical `CommandPolicy` (`scripts/core/security/command_policy.py`), which is the **Single Canonical Authority** for execution confinement.

| Executable | Allowed Subcommands / Scripts | Prohibited Flags / Arguments | Timeout | Max Output |
| :--- | :--- | :--- | :--- | :--- |
| **Python** (`sys.executable`) | Approved scripts in `scripts/`, `scripts/gates/`, `scripts/generators/`. In Dev/Test: `-m pytest`, `-m unittest`. | `-c` (always), `-m` in production, `-m pip`, `-m venv`, interactive mode, untracked scripts | 900s | 50 MB |
| **Node / npm / npx** | `remotion render`, `remotion preview`, `npm run build` | `-e`, `--eval`, `install`, interactive shell | 900s | 100 MB |
| **FFmpeg / FFprobe** | Transcode, probe, audio extract, filter graph | Network inputs (unless allowlisted), shell pipes | 600s | 50 MB |
| **Docker** | `run` (image: `clean-video-builder`), `info` | `exec`, `--privileged`, `-v /:/...` (root mounts), `system prune` | 1200s | 50 MB |

#### Python Module Policy by Environment:
- **Production:** By default, all `python -m <anything>` invocations are **DENIED**. Runtime package installation (`python -m pip`) and virtualenv manipulation (`python -m venv`) are strictly forbidden to ensure a hermetic production runtime.
- **Development / Test:** May explicitly permit approved test runners (`pytest`, `unittest`). Runtime tools (`pip`, `venv`) remain rejected from the runtime execution path.
- **Inline Execution:** `python -c` is strictly **PROHIBITED** across all environments.

### 8.3 Environment Inheritance Policy
- Subprocesses must NEVER inherit `os.environ` unfiltered.
- A sanitized environment is constructed containing only:
  - System PATH (verified)
  - `PYTHONPATH` restricted to workspace root
  - Explicit configuration variables
- All bypass variables (`SKIP_STRICT_QC`, `AGY_IS_MANAGED`) are purged before dispatching production child processes.

### 8.4 Working Directory Confinement (CWD)
- `cwd` must be explicitly specified and verified to be within `workspace_root`.
- Execution in arbitrary directories (`/tmp`, `/etc`, user home) is forbidden.

---

## 9. Python Interpreter Policy (DISC-004)

### 9.1 The Vulnerability
In `api/services/scaffold_service.py`:
```python
# VULNERABLE CODE (Pre-remediation):
cmd = ["python", "scripts/scaffold_project.py", "--name", name, "--language", language]
result = safe_subprocess(cmd, ...)
```
When invoked under systemd, container, or non-activated shell environments, `"python"` resolves to `/usr/bin/python` rather than the active virtual environment (`.venv/bin/python`). This results in catastrophic `ModuleNotFoundError: No module named 'pydantic'` and exposes the system to PATH hijacking.

### 9.2 The Canonical Policy
- **Rule:** Every internal Python subprocess MUST invoke `sys.executable` (the running Python runtime) or an explicitly configured interpreter path from `SecuritySettings.python_interpreter`.
- **Enforcement:** Hardcoded `"python"` strings in command lists are strictly prohibited.
- `safe_subprocess` and the `CommandPolicyEngine` will automatically normalize or enforce `sys.executable`.

---

## 10. Environment Variables Policy & Classification

The system categorizes every environment variable into one of five strict classifications:

| Variable | Category | Allowed Environments | Purpose & Policy Rule |
| :--- | :--- | :--- | :--- |
| `AGY_IS_MANAGED` | **Forbidden in Production** | `test`, `local_dev` | **CANONICAL RULE:** Must NEVER bypass `.studio_approved` in production. Ignored or rejected in production runtime. |
| `SKIP_STRICT_QC` | **Forbidden in Production** | `test` | **CANONICAL RULE:** Must NEVER convert a Hard Failure to Success in production. Banned in production runtime. |
| `AGY_FAILURE_INJECTION_ENABLED` | **Test-Only** | `test` | Enabled only during fault-tolerance testing. Must be completely inactive in production. |
| `AGY_INJECT_FAILURE` | **Test-Only** | `test` | Defines fault injection payload. Ignored in production. |
| `TESTING` | **Test-Only** | `test` | Signals test runner mode. |
| `OPENAI_API_KEY` | **Secret** | All | OpenAI API Key. Must be loaded via typed SecretStr; never logged. |
| `ELEVENLABS_API_KEY` | **Secret** | All | Voiceover synthesis key. Must be loaded via SecretStr; never logged. |
| `HEYGEN_API_KEY` | **Secret** | All | Avatar generation key. Must be loaded via SecretStr; never logged. |
| `FAL_KEY` / `FALAI_API_KEY` | **Secret** | All | Video generation key. Must be loaded via SecretStr; never logged. |
| `REPLICATE_API_TOKEN` | **Secret** | All | Model API token. Must be loaded via SecretStr; never logged. |
| `PEXELS_API_KEY` | **Secret** | All | Stock video asset key. |
| `PIXABAY_API_KEY` | **Secret** | All | Stock video asset key. |
| `FREESOUND_API_KEY` | **Secret** | All | Audio effects asset key. |
| `MOTION_ENV` | **Configuration** | All | Execution environment: `production`, `staging`, `development`, `test`. |
| `MOTION_STORAGE_ROOT` | **Configuration** | All | Base directory for project storage. |
| `MOTION_HOST` | **Configuration** | All | API listen host (default: `127.0.0.1`). |
| `MOTION_PORT` | **Configuration** | All | API listen port (default: `8000`). |
| `AGY_RUN_ID` | **Runtime Tracing** | All | Unique ID for tracing cross-stage execution spans. |
| `AGY_SPAN_ID` | **Runtime Tracing** | All | Span ID for hierarchical logging. |
| `AGY_ATTEMPT` | **Runtime Tracing** | All | Retry attempt counter. |
| `DISPLAY` | **Configuration** | Dev/Worker | X11 display for screen recording. |
| `SVM_DATA_DIR` | **Configuration** | All | Plugin cache root. |
| `SVM_PLUGIN_ROOT` | **Configuration** | All | Plugin installation directory. |
| `WHISPER_DEVICE` | **Configuration** | All | Compute device for Whisper (`cpu`, `cuda`). |

---

## 11. Security Configuration Contract (Typed Settings)

Configuration must be loaded through a centralized, typed Pydantic Settings schema (`SecuritySettings`) rather than fragmented `os.environ.get()` calls.

### Schema Requirements:
1. **Type Safety:** Integer timeouts, Path objects for directories, SecretStr for credentials.
2. **Environment Invariant Validation:**
   ```python
   if self.env == EnvironmentType.PRODUCTION:
       if self.allow_bypass_qc:
           raise ValueError("QC bypass is strictly forbidden in production!")
       if self.allow_anonymous_access:
           raise ValueError("Anonymous access is forbidden in production!")
   ```
3. **Single Source of Truth:** `get_security_settings()` provides an immutable, validated settings object.

---

## 12. S02 Enforcement Points and Acceptance Mapping

The architectural foundation laid in S01 directly powers S02 implementation across these enforcement interception points:

| Vulnerability ID | Description | S01 Scaffolding Contract | S02 Enforcement Point |
| :--- | :--- | :--- | :--- |
| `AUTH-001` | User-supplied `approved_by` | `Principal` contract & `ADR-002` | `api/routers/gates.py` & `GateService`: Derive actor solely from Principal. |
| `AUTH-002` | Missing Principal abstraction | `scripts/core/security/principal.py` | `api/main.py`: Authentication middleware injecting `Principal`. |
| `AUTH-003` | No project scope isolation | `AuthorizationPolicy.is_authorized` | Dependency injection interceptor checking `(Principal, Action, Project)`. |
| `AUTH-004` | No role separation | `Role` enum & Permission Matrix | Authorization checks guarding state mutations. |
| `AUTH-005` | Non-reviewer gate approval | `Role.REVIEWER` requirement | `approve_gate` requires `Role.REVIEWER`. |
| `ASSET-009` | Path traversal in assets | `safe_resolve` specification | Reject `..`, absolute paths, and ensure target remains inside project directory. |
| `SEC-001` | Symlink directory escape | Path security symlink validator | Resolve symlinks and assert target is within allowed storage boundary. |
| `SEC-002` | Unvalidated Docker commands | `CommandPolicy` docker rules | Inspect Docker arguments: block arbitrary subcommands, volumes, and flags. |
| `SEC-003` | Dangerous subprocess flags | `CommandPolicyEngine` | Disallow `-c`, `--eval`, shell strings across all executables. |
| `DISC-004` | `"python"` interpreter drift | Python Interpreter Policy | Replace hardcoded `"python"` with `sys.executable`. |
| `LED-019` | `AGY_IS_MANAGED` approval bypass| Environment Variables Policy | Delete `.studio_approved` bypass in `render_project.py`. |
| `LED-022` | `SKIP_STRICT_QC` failure bypass | Environment Variables Policy | Delete `SKIP_STRICT_QC` bypass in `final_qc.py`. |

---

## 13. Conclusion
This Trust Model serves as the architectural contract for all subsequent remediation stages. No stage may relax or violate these invariants.
