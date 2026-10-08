# PR-001: Authentication Hardening — Implementation Report

## Executive Summary
This report documents the architectural remediation and complete implementation of **PR-001 (Authentication Hardening)** for the `clean-video-workspace` repository. The remediation eliminates critical identity spoofing shortcuts, hardcoded secrets, and client-asserted privilege escalations, strictly enforcing cryptographic HMAC-SHA256 signature verification and fail-closed authentication across all environments.

---

## 1. Baseline Context
- **Base Commit SHA:** `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` (`main`)
- **Remediation Branch:** `remediation/pr-001-authentication-hardening`
- **Security Finding Reference:** SEC-AUTH-001 / PR-001 (Core Authentication Hardening)

---

## 2. Root Cause Analysis
Prior to remediation, codebase inspection revealed four critical vulnerabilities in operational authentication code:

1. **Client-Asserted Identity & Role Spoofing (`api/core/auth.py:265-303`):**
   When `MOTION_ENV != "production"`, the server extracted client-controlled HTTP headers (`X-Principal-ID`, `X-Principal-Roles`, `X-Principal-Scope`, `X-Principal-Type`) and directly instantiated high-privilege `Principal` objects without any signature verification. Any unauthenticated caller could assert administrative control (`X-Principal-Roles: admin`) simply by omitting production environment tags.

2. **Bearer Pseudo-Tokens (`api/core/auth.py:240-261`):**
   The application accepted arbitrary pseudo-tokens (`admin`, `admin_user`, `administrator`, `system`, `system-token`, `sys_worker`, `usr_*`) in the `Authorization: Bearer <token>` header in non-production environments, bypassing HMAC-SHA256 signature verification entirely.

3. **Hardcoded Insecure Fallback Secret (`api/core/auth.py:56`):**
   `get_auth_secret()` returned `"dev-insecure-secret-key-minimum-32-chars-long!"` as an operational default whenever `AUTH_SECRET_KEY` or `JWT_SECRET_KEY` was missing from environment variables, leaving HMAC signatures forgeable by anyone with access to the source code.

4. **Weak Claims Validation & Silent Defaults (`api/core/auth.py:203`):**
   Token verification allowed missing expiration (`exp`), accepted arbitrary token issuers (`iss`), and on unrecognized `type` claims silently defaulted to `PrincipalType.HUMAN` instead of failing closed.

---

## 3. Architectural Rationale & Design
The hardening adheres to the **Clean Video Workspace Trust Model** and **DEC-04 (Server-Authoritative Identity)**:

- **Single Verification Gateway:** All authenticated requests must pass through `extract_principal_from_request()`, which exclusively delegates to `verify_signed_token()`. There are zero bypass paths or alternate branches.
- **Token Architecture (Custom HMAC-SHA256 Bearer Token):** The token format is a project-specific 2-part bearer token (`<base64url_payload>.<base64url_hmac_signature>`), NOT standard RFC 7519 3-part JWT. The `JWT_SECRET_KEY` environment variable is supported solely as a legacy fallback alias for `AUTH_SECRET_KEY`.
- **Fail-Closed Secret Management:** If `AUTH_SECRET_KEY` (or legacy `JWT_SECRET_KEY`) is missing, empty, or shorter than 32 characters, `get_auth_secret()` immediately raises `AuthenticationRequiredError(Action.PROJECT_READ)`, producing an HTTP 401 Unauthorized response. Hardcoded development secrets in application code are strictly abolished.
- **Mandatory Cryptographic Verification First:** The HMAC-SHA256 signature is verified before parsing or trusting any token claims. Tampered signatures fail immediately.
- **Strict Claims Conformance:**
  - `exp`: Required and strictly checked against UTC `now()`. Expired tokens fail with HTTP 401.
  - `iss`: Required and must strictly equal `"clean-video-engine"`.
  - `iat`: Mandatory timestamp in seconds; rejected if missing, non-numeric, or skewed into the future (>60s).
  - `sub`: Required non-empty string identifier.
  - `type`: Mandatory claim matching a valid `PrincipalType` (`HUMAN`, `SERVICE`, `SYSTEM_WORKER`, `ANONYMOUS`). Missing or unrecognized types strictly raise `AuthenticationRequiredError` without any default fallback to `HUMAN`.
- **Public Probes Preserved:** Explicitly exempted endpoints (`/health`, `/health/live`, `/health/ready`) remain unauthenticated and continue to return HTTP 200 OK.
- **Uniform Enforcement Across All Environments:** Development, test, staging, and production environments share identical verification rules. No environment variable (`MOTION_ENV`) can disable authentication checks in operational code.

---

## 4. Modified Files & Behavioral Summary

| File Path | Description of Changes |
| :--- | :--- |
| `api/core/auth.py` | Removed all `X-Principal-*` header spoofing, Bearer pseudo-tokens, and hardcoded dev secrets. Hardened `get_auth_secret()`, `create_signed_token()`, `verify_signed_token()`, and `extract_principal_from_request()`. |
| `scripts/core/security/settings.py` | Added `set_security_settings()` to allow hermetic resetting of security singleton state across test execution. |
| `tests/conftest.py` | Injected `TEST_PYTEST_AUTH_SECRET` (32 chars) into `setup_test_env` test fixture and created `make_test_auth_headers()` utility. |
| `tests/security/test_pr001_authentication_hardening.py` | New comprehensive red-to-green test suite containing 61 tests validating all G1–G10 gates. |
| `tests/security/test_s02_negative_enforcement.py` | Migrated legacy test assertions to authentic signed tokens. |
| `tests/api/test_render.py` | Migrated API render test client headers to authentic signed tokens. |
| `tests/api/test_projects.py` | Migrated test client to use signed tokens via `make_test_auth_headers`. |
| `tests/api/test_project_creation.py` | Migrated test client to use signed tokens via `make_test_auth_headers`. |
| `tests/api/test_gates.py` | Migrated test client to use signed tokens via `make_test_auth_headers`. |
| `tests/api/test_client_without_filesystem.py` | Migrated test headers to signed tokens via `make_test_auth_headers`. |
| `tests/api/test_lifecycle_bypass_prevention.py` | Migrated test clients to signed tokens via `make_test_auth_headers`. |
| `tests/api/test_tenant_endpoints.py` | Migrated multi-tenant test headers to signed tokens via `make_test_auth_headers`. |
| `tests/api/test_candidate_reviews_router.py` | Migrated candidate review API test headers to signed tokens. |
| `tests/api/test_candidate_promotions_router.py` | Migrated candidate promotion API test headers to signed tokens. |
| `tests/core/test_s28_r14_production_integration.py` | Migrated authoring document API test headers to signed tokens. |
| `tests/e2e/test_saas_multi_tenant_e2e.py` | Migrated multi-tenant E2E scenarios to signed tokens. |
| `tests/fault_injection/test_fi_07_db_storage_disagreement.py` | Migrated test headers to signed tokens and instantiated test client. |
| `tests/fault_injection/test_fi_09_idempotency.py` | Migrated test headers to signed tokens. |
| `tests/fault_injection/test_fi_18_event_stream_reconnect.py` | Migrated test headers to signed tokens. |
| `tests/fault_injection/test_fi_19_cancellation_execution.py` | Migrated test headers to signed tokens. |
| `tests/fault_injection/test_fi_20_e2e_destructive.py` | Migrated test headers to signed tokens. |
| `tests/remediation/*` | Migrated reproduction and acceptance suites to authentic signed tokens. |

---

## 5. Observable Behavioral Changes
1. **Unauthenticated Requests to Protected Endpoints:**
   - Any request lacking an `Authorization: Bearer <signed-token>` header receives `401 Unauthorized` (`detail: Authentication required for action ...`).
2. **Pseudo-Tokens & Development Headers:**
   - Sending `Authorization: Bearer admin` or `X-Principal-ID: admin` now receives `401 Unauthorized`.
3. **Missing or Short Secret Key:**
   - If `AUTH_SECRET_KEY` is not set or `< 32` characters in the environment, all protected endpoints immediately reject calls with `401 Unauthorized` without server crashes.
4. **Liveness & Readiness Probes:**
   - Requests to `/health`, `/health/live`, and `/health/ready` succeed with `200 OK` regardless of authorization headers.
