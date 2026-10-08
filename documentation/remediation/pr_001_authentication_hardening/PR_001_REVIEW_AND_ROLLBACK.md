# PR-001: Authentication Hardening — Review & Rollback Guide

## 1. Unified Diff Summary

### Operational Code Changes:
- **[`api/core/auth.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/core/auth.py):**
  - Completely excised the `is_production` check and conditional logic for non-production environments.
  - Removed all code accepting `X-Principal-*` headers (`X-Principal-ID`, `X-Principal-Roles`, `X-Principal-Scope`, `X-Principal-Type`).
  - Removed code accepting Bearer pseudo-tokens (`admin`, `system`, `usr_*`).
  - Removed hardcoded default secret `"dev-insecure-secret-key-minimum-32-chars-long!"`.
  - Added strict validation to `get_auth_secret()`: raises `AuthenticationRequiredError` if secret is unset or `< 32` characters.
  - Hardened `verify_signed_token()`:
    - Enforces HMAC-SHA256 signature verification before decoding payload.
    - Requires `exp` claim and ensures it is in the future.
    - Requires `iss` claim and verifies `iss == "clean-video-engine"`.
    - Requires `iat` claim.
    - Requires non-empty `sub` claim.
    - Rejects unknown `type` claims (no silent fallback).
  - Hardened `extract_principal_from_request()` to strictly require and parse `Authorization: Bearer <token>`.
- **[`scripts/core/security/settings.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/security/settings.py):**
  - Added `set_security_settings(settings: Optional[SecuritySettings])` function to allow atomic resetting of the settings singleton between tests.

### Test Harness & Migration Changes:
- **`tests/conftest.py`:**
  - Injected `TEST_PYTEST_AUTH_SECRET = "test-signing-secret-for-pytest-harness-32-chars!"` via the autouse `setup_test_env` fixture.
  - Added `make_test_auth_headers(...)` helper to generate authentic signed HMAC-SHA256 bearer tokens (custom 2-part `<payload>.<sig>` format) for test cases, defaulting to least-privilege (`Role.VIEWER`, empty scopes) to prevent unintentional admin privilege leakage.
- **Suite-Wide Migration:**
  - Migrated tests across `tests/api/`, `tests/fault_injection/`, `tests/core/`, `tests/e2e/`, and `tests/remediation/` to pass authentic signed headers.

---

## 2. Local Developer Setup Instructions
Developers running the application locally must configure a valid 32+ character authentication key.

### Step 1: Set the Secret Key
Add the following to your local `.env` or export in your shell (do **NOT** commit this to version control):
```bash
export AUTH_SECRET_KEY="<generate-at-least-32-random-alphanumeric-characters>"
```
Example generating a secure key via OpenSSL:
```bash
export AUTH_SECRET_KEY=$(openssl rand -hex 32)
```

### Step 2: Generating Signed Development Tokens
To generate a signed token for local API testing or curl/Postman scripts:
```python
from api.core.auth import create_signed_token
from scripts.core.security.principal import Principal, Role, PrincipalType

# Example: Generate an admin token for local use
principal = Principal(
    principal_id="dev_admin",
    principal_type=PrincipalType.HUMAN,
    roles={Role.ADMIN},
)
token = create_signed_token(principal)
print("Authorization: Bearer " + token)
```

### Step 3: Run the Local API Server
```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

---

## 3. Client & Test Migration Notice
- **Legacy Headers Removed:** Requests sending `X-Principal-ID` or `X-Principal-Roles` without an `Authorization: Bearer <signed-token>` header will receive an immediate `401 Unauthorized`.
- **Pseudo-Tokens Removed:** Calls with `Authorization: Bearer admin` or `Authorization: Bearer system` will receive `401 Unauthorized`.
- **Client Integration:** All API clients, CLI tools, and background services must pass authentic HMAC-SHA256 signed bearer tokens (`<base64_payload>.<signature>`) issued with `iss: "clean-video-engine"`, valid `exp`, mandatory `iat`, mandatory `type`, and signed with the shared `AUTH_SECRET_KEY`. *(Note: The token format is a project-specific 2-part HMAC-SHA256 bearer token, not standard RFC 7519 3-part JWT).*

---

## 4. Safe Rollback Procedure
If an issue occurs in staging or deployment that requires reverting this patch:

### Immediate Rollback (Git Revert)
The changes are isolated to branch `remediation/pr-001-authentication-hardening`.
To revert this branch to the baseline commit `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`:

```bash
git checkout remediation/pr-001-authentication-hardening
git reset --hard 90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1
```

### Impact of Rollback
- Reverting will restore the insecure fallback secret and re-enable `X-Principal-*` spoofing and pseudo-tokens in non-production environments.
- Rollback should only be performed if an emergency regression prevents service operation, and must be immediately followed by a prioritized remediation.
