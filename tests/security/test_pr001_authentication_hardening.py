"""PR-001 Authentication Hardening Test Suite.

Proves:
1. Vulnerability reproduction (Red tests on vulnerable code).
2. Elimination of identity and privilege spoofing via dev/test shortcuts.
3. Strict fail-closed authentication across all deployment environments.
4. Protection against hardcoded secrets, weak keys, and client-asserted headers.
5. Correct 401 vs 403 status code contracts and public probe preservation.
"""

import os
import json
import base64
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Generator

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token, verify_signed_token
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.security.permissions import Action, AuthenticationRequiredError
from scripts.core.security.settings import (
    get_security_settings,
    set_security_settings,
    SecuritySettings,
    EnvironmentType,
)

VALID_TEST_SECRET = "super-test-secret-key-at-least-32-chars-long-strictly!"
ANOTHER_KEY = "another-completely-different-secret-key-32-chars!"


@pytest.fixture(autouse=True)
def clean_security_settings(monkeypatch):
    """Ensure clean configuration singleton state between test executions."""
    # Reset singleton before and after each test
    set_security_settings(None)
    yield
    set_security_settings(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _mint_raw_token(payload: Dict[str, Any], secret: str) -> str:
    """Helper to mint raw tokens with arbitrary payloads for negative testing."""
    payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    return f"{payload_b64}.{sig_b64}"


# ─────────────────────────────────────────────────────────────────────────────
# 1. PSEUDO-TOKENS & BEARER SHORTCUTS MUST FAIL (RED ON VULNERABLE CODE)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("env_val", [None, "development", "test", "staging", "production"])
@pytest.mark.parametrize("token", [
    "admin",
    "admin_user",
    "administrator",
    "system",
    "system-token",
    "sys_worker",
    "usr_fake123",
])
def test_pseudo_tokens_rejected_in_all_environments(client, monkeypatch, env_val, token):
    """Bearer pseudo-tokens must NEVER authenticate a request in ANY environment."""
    if env_val is None:
        monkeypatch.delenv("MOTION_ENV", raising=False)
    else:
        monkeypatch.setenv("MOTION_ENV", env_val)
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    resp = client.post(
        "/projects/",
        json={"name": "HackedProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401, (
        f"Security Failure: Token '{token}' under MOTION_ENV='{env_val}' returned {resp.status_code}, expected 401"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. X-PRINCIPAL-* HEADERS MUST NEVER GRANT IDENTITY (RED ON VULNERABLE CODE)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("env_val", [None, "development", "test", "staging", "production"])
def test_x_principal_headers_rejected_in_all_environments(client, monkeypatch, env_val):
    """X-Principal-* headers must NEVER be trusted as caller identity in ANY environment."""
    if env_val is None:
        monkeypatch.delenv("MOTION_ENV", raising=False)
    else:
        monkeypatch.setenv("MOTION_ENV", env_val)
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    headers = {
        "X-Principal-ID": "admin_attacker",
        "X-Principal-Roles": "admin",
        "X-Principal-Scope": "*",
        "X-Principal-Type": "HUMAN",
    }

    # Case A: Headers alone without Authorization header
    resp_no_auth = client.post(
        "/projects/",
        json={"name": "HackedProjectNoAuth", "language": "en"},
        headers=headers,
    )
    assert resp_no_auth.status_code == 401, (
        f"Security Failure: X-Principal headers without Authorization under MOTION_ENV='{env_val}' returned {resp_no_auth.status_code}, expected 401"
    )

    # Case B: Headers with invalid Authorization header
    headers_with_bad_auth = dict(headers)
    headers_with_bad_auth["Authorization"] = "Bearer invalid.token.value"
    resp_bad_auth = client.post(
        "/projects/",
        json={"name": "HackedProjectBadAuth", "language": "en"},
        headers=headers_with_bad_auth,
    )
    assert resp_bad_auth.status_code == 401, (
        f"Security Failure: X-Principal headers with bad Authorization under MOTION_ENV='{env_val}' returned {resp_bad_auth.status_code}, expected 401"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. EMBEDDED/HARDCODED SECRET REJECTION (RED ON VULNERABLE CODE)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("env_val", [None, "development", "test", "staging"])
def test_hardcoded_dev_secret_never_accepted_when_secret_unset(client, monkeypatch, env_val):
    """A token signed with known hardcoded dev secret must be rejected when AUTH_SECRET_KEY is unset."""
    if env_val is None:
        monkeypatch.delenv("MOTION_ENV", raising=False)
    else:
        monkeypatch.setenv("MOTION_ENV", env_val)
    monkeypatch.delenv("AUTH_SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    set_security_settings(None)

    # Token signed with the old hardcoded fallback string
    hardcoded_secret = "dev-insecure-secret-key-minimum-32-chars-long!"
    principal = Principal(
        principal_id="usr_attacker",
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
        project_scopes={"*": {Role.ADMIN}},
    )
    token = create_signed_token(principal, secret=hardcoded_secret)

    resp = client.post(
        "/projects/",
        json={"name": "HardcodedSecretProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, (
        f"Security Failure: Hardcoded fallback secret accepted under MOTION_ENV='{env_val}', got {resp.status_code}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. FAIL-CLOSED ON MISSING OR WEAK SECRETS IN ALL ENVIRONMENTS
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("weak_secret", ["", "short", "less-than-32-characters!"])
def test_weak_or_empty_secret_fails_closed(client, monkeypatch, weak_secret):
    """If AUTH_SECRET_KEY is missing or less than 32 characters, all requests must fail-closed,
    even when presented with a structurally authentic token signed with that key."""
    monkeypatch.setenv("AUTH_SECRET_KEY", weak_secret)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test_weak",
        "type": "HUMAN",
        "roles": ["admin"],
        "scopes": {},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }
    # Mint a structurally authentic token signed with the weak secret
    token = _mint_raw_token(payload, weak_secret if weak_secret else "dummy-signing-key")

    resp = client.post(
        "/projects/",
        json={"name": "WeakSecretProbe", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401, f"Expected 401 for weak secret '{weak_secret}', got {resp.status_code}"
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token)


def test_missing_secret_fails_closed_with_valid_token(client, monkeypatch):
    """When AUTH_SECRET_KEY and JWT_SECRET_KEY are completely unset, valid tokens fail-closed."""
    monkeypatch.delenv("AUTH_SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test_missing",
        "type": "HUMAN",
        "roles": ["admin"],
        "scopes": {},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }
    token = _mint_raw_token(payload, VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "MissingSecretProbe", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token)


# ─────────────────────────────────────────────────────────────────────────────
# 5. CRYPTOGRAPHIC VERIFICATION & CLAIM INTEGRITY
# ─────────────────────────────────────────────────────────────────────────────

def test_tampered_payload_rejected(client, monkeypatch):
    """Tampering with token payload without re-signing must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    principal = Principal(
        principal_id="usr_normal",
        principal_type=PrincipalType.HUMAN,
        roles={Role.VIEWER},
    )
    token = create_signed_token(principal, secret=VALID_TEST_SECRET)
    payload_b64, sig_b64 = token.split(".", 1)

    # Tamper payload to elevate to admin
    tampered_payload = {"sub": "usr_normal", "type": "HUMAN", "roles": ["admin"], "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())}
    tampered_json = json.dumps(tampered_payload, separators=(',', ':'), sort_keys=True).encode("utf-8")
    tampered_b64 = base64.urlsafe_b64encode(tampered_json).decode("ascii").rstrip("=")
    tampered_token = f"{tampered_b64}.{sig_b64}"

    resp = client.post(
        "/projects/",
        json={"name": "TamperedProject", "language": "en"},
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert resp.status_code == 401


def test_tampered_signature_rejected(client, monkeypatch):
    """Tampering with signature must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    principal = Principal(
        principal_id="usr_normal",
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
    )
    token = create_signed_token(principal, secret=VALID_TEST_SECRET)
    payload_b64, sig_b64 = token.split(".", 1)
    bad_sig = "A" * len(sig_b64)
    tampered_token = f"{payload_b64}.{bad_sig}"

    resp = client.post(
        "/projects/",
        json={"name": "BadSigProject", "language": "en"},
        headers={"Authorization": f"Bearer {tampered_token}"}
    )
    assert resp.status_code == 401


def test_wrong_key_signed_token_rejected(client, monkeypatch):
    """Token signed with a different key must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    principal = Principal(
        principal_id="usr_admin",
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
    )
    token = create_signed_token(principal, secret=ANOTHER_KEY)

    resp = client.post(
        "/projects/",
        json={"name": "WrongKeyProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_expired_token_rejected(client, monkeypatch):
    """Token whose expiry is in the past must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    principal = Principal(
        principal_id="usr_admin",
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
    )
    token = create_signed_token(principal, secret=VALID_TEST_SECRET, expires_in_seconds=-10)

    resp = client.post(
        "/projects/",
        json={"name": "ExpiredProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_unknown_principal_type_rejected(client, monkeypatch):
    """Token with unrecognized principal type must NOT silently default to HUMAN; must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test",
        "type": "SUPER_ALIEN",
        "roles": ["admin"],
        "scopes": {},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }
    token = _mint_raw_token(payload, VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "AlienTypeProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_missing_type_claim_rejected_no_fallback_to_human(client, monkeypatch):
    """Token missing 'type' claim must NOT fallback to HUMAN; must be strictly rejected (401)."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload_no_type = {
        "sub": "usr_test",
        "roles": ["admin"],
        "scopes": {},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }
    token = _mint_raw_token(payload_no_type, VALID_TEST_SECRET)

    # 1. API endpoint rejects missing type with HTTP 401
    resp = client.post(
        "/projects/",
        json={"name": "NoTypeProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401, f"Expected 401 Unauthorized for missing 'type', got {resp.status_code}"

    # 2. Unit verification via verify_signed_token raises AuthenticationRequiredError
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token, secret=VALID_TEST_SECRET)


def test_unrecognized_role_rejected(client, monkeypatch):
    """Token with unrecognized role must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test",
        "type": "HUMAN",
        "roles": ["super_superuser"],
        "scopes": {},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }
    token = _mint_raw_token(payload, VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "BadRoleProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_malformed_scope_rejected(client, monkeypatch):
    """Token with invalid/traversal project scope must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test",
        "type": "HUMAN",
        "roles": [],
        "scopes": {"../escape": ["editor"]},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }
    token = _mint_raw_token(payload, VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "BadScopeProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_missing_or_corrupted_exp_claim_rejected(client, monkeypatch):
    """Token missing 'exp' or with corrupted 'exp' must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    # Missing exp
    payload_no_exp = {
        "sub": "usr_test",
        "type": "HUMAN",
        "roles": ["admin"],
        "scopes": {},
        "iat": int(now.timestamp()),
        "iss": "clean-video-engine",
    }
    token_no_exp = _mint_raw_token(payload_no_exp, VALID_TEST_SECRET)
    resp = client.post(
        "/projects/",
        json={"name": "NoExpProject", "language": "en"},
        headers={"Authorization": f"Bearer {token_no_exp}"}
    )
    assert resp.status_code == 401

    # Corrupted non-numeric exp
    payload_bad_exp = dict(payload_no_exp, exp="not-a-timestamp")
    token_bad_exp = _mint_raw_token(payload_bad_exp, VALID_TEST_SECRET)
    resp2 = client.post(
        "/projects/",
        json={"name": "BadExpProject", "language": "en"},
        headers={"Authorization": f"Bearer {token_bad_exp}"}
    )
    assert resp2.status_code == 401


def test_missing_or_invalid_iat_claim_rejected(client, monkeypatch):
    """Token missing 'iat', with future clock skew, or with invalid type must be strictly rejected (401)."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    base_payload = {
        "sub": "usr_test",
        "type": "HUMAN",
        "roles": ["admin"],
        "scopes": {},
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }

    # Case A: Missing 'iat' claim completely
    payload_no_iat = dict(base_payload)
    token_no_iat = _mint_raw_token(payload_no_iat, VALID_TEST_SECRET)
    resp = client.post(
        "/projects/",
        json={"name": "NoIatProject", "language": "en"},
        headers={"Authorization": f"Bearer {token_no_iat}"}
    )
    assert resp.status_code == 401, f"Expected 401 for missing 'iat', got {resp.status_code}"
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token_no_iat, secret=VALID_TEST_SECRET)

    # Case B: Future 'iat' beyond clock skew tolerance (>60s)
    payload_future_iat = dict(base_payload, iat=int((now + timedelta(minutes=10)).timestamp()))
    token_future_iat = _mint_raw_token(payload_future_iat, VALID_TEST_SECRET)
    resp_future = client.post(
        "/projects/",
        json={"name": "FutureIatProject", "language": "en"},
        headers={"Authorization": f"Bearer {token_future_iat}"}
    )
    assert resp_future.status_code == 401, f"Expected 401 for future 'iat', got {resp_future.status_code}"
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token_future_iat, secret=VALID_TEST_SECRET)

    # Case C: Corrupted non-numeric 'iat'
    payload_corrupt_iat = dict(base_payload, iat="invalid-non-numeric-timestamp")
    token_corrupt_iat = _mint_raw_token(payload_corrupt_iat, VALID_TEST_SECRET)
    resp_corrupt = client.post(
        "/projects/",
        json={"name": "CorruptIatProject", "language": "en"},
        headers={"Authorization": f"Bearer {token_corrupt_iat}"}
    )
    assert resp_corrupt.status_code == 401, f"Expected 401 for non-numeric 'iat', got {resp_corrupt.status_code}"
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token_corrupt_iat, secret=VALID_TEST_SECRET)


@pytest.mark.parametrize("invalid_iat", [
    float("nan"),
    float("inf"),
    float("-inf"),
    True,
    False,
    0,
    -1,
    -1000.5,
    "not-a-number",
    "NaN",
    "Infinity",
    "-Infinity",
    [],
    {},
    None,
])
def test_invalid_iat_values_strictly_rejected(client, monkeypatch, invalid_iat):
    """Tokens with NaN, Infinity, boolean, non-positive, or non-numeric iat values must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test_iat_invalid",
        "type": "HUMAN",
        "roles": ["admin"],
        "scopes": {},
        "iat": invalid_iat,
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }
    token = _mint_raw_token(payload, VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "InvalidIatProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401, f"Expected 401 for invalid iat={invalid_iat!r}, got {resp.status_code}"
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token, secret=VALID_TEST_SECRET)


def test_iat_greater_than_exp_rejected(client, monkeypatch):
    """Token where iat > exp must be strictly rejected (401)."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test_iat_exp_order",
        "type": "HUMAN",
        "roles": ["admin"],
        "scopes": {},
        "iat": int((now + timedelta(hours=2)).timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "clean-video-engine",
    }
    token = _mint_raw_token(payload, VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "IatAfterExpProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token, secret=VALID_TEST_SECRET)


@pytest.mark.parametrize("invalid_exp", [
    float("nan"),
    float("inf"),
    float("-inf"),
    True,
    False,
    0,
    -500,
    "not-a-number",
    [],
    {},
    None,
])
def test_invalid_exp_values_strictly_rejected(client, monkeypatch, invalid_exp):
    """Tokens with NaN, Infinity, boolean, non-positive, or non-numeric exp values must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test_exp_invalid",
        "type": "HUMAN",
        "roles": ["admin"],
        "scopes": {},
        "iat": int(now.timestamp()),
        "exp": invalid_exp,
        "iss": "clean-video-engine",
    }
    token = _mint_raw_token(payload, VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "InvalidExpProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401, f"Expected 401 for invalid exp={invalid_exp!r}, got {resp.status_code}"
    with pytest.raises(AuthenticationRequiredError):
        verify_signed_token(token, secret=VALID_TEST_SECRET)


def test_foreign_issuer_rejected(client, monkeypatch):
    """Token with foreign issuer claim must return 401."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": "usr_test",
        "type": "HUMAN",
        "roles": ["admin"],
        "scopes": {},
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": "untrusted-foreign-engine",
    }
    token = _mint_raw_token(payload, VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "ForeignIssuerProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 6. POSITIVE CONTRACTS: 401 vs 403 & HEALTH PRESERVATION
# ─────────────────────────────────────────────────────────────────────────────

def test_authenticated_viewer_cannot_perform_admin_action_yields_403(client, monkeypatch):
    """An authenticated principal with insufficient roles receives 403 Forbidden (NOT 401)."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    viewer_principal = Principal(
        principal_id="usr_viewer_legit",
        principal_type=PrincipalType.HUMAN,
        roles={Role.VIEWER},
    )
    token = create_signed_token(viewer_principal, secret=VALID_TEST_SECRET)

    # Creating a project requires EDITOR or ADMIN
    resp = client.post(
        "/projects/",
        json={"name": "ViewerForbiddenCreate", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}"


def test_authenticated_admin_permitted_yields_200(client, monkeypatch):
    """A valid, authentic Admin token succeeds with 200."""
    monkeypatch.setenv("AUTH_SECRET_KEY", VALID_TEST_SECRET)
    set_security_settings(None)

    admin_principal = Principal(
        principal_id="usr_admin_legit",
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
    )
    token = create_signed_token(admin_principal, secret=VALID_TEST_SECRET)

    resp = client.post(
        "/projects/",
        json={"name": "LegitAdminProject", "language": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.text}"
    proj_id = resp.json().get("project_id")
    if proj_id:
        proj_dir = Path("projects") / proj_id
        if proj_dir.exists():
            import shutil
            shutil.rmtree(proj_dir)


@pytest.mark.parametrize("path", ["/health/live", "/health/ready", "/health"])
def test_public_health_endpoints_accessible_without_auth(client, path):
    """Public health/liveness/readiness probes must remain accessible without auth."""
    resp = client.get(path)
    assert resp.status_code in (200, 503)
