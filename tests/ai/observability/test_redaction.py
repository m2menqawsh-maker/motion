"""
tests/ai/observability/test_redaction.py
=========================================
Tests for Telemetry Redaction, Privacy Policy, and Secret Sanitization (S27.19).

Invariants verified:
1. Redacts API keys (OpenAI, Anthropic, AWS).
2. Redacts Bearer tokens and Authorization headers.
3. Redacts signed URL access tokens and cryptographic signatures.
4. Redacts storage credentials and secrets.
5. Privacy policy: Excludes raw prompts and user content by default.
6. Opt-in: When ALLOW_RAW_CONTENT_LOGGING=1, content logging is allowed in bounded form.
7. Verification: scan_trace_for_secrets(cleaned_trace) == [] (clean audit scan).
8. Negative test: Unredacted traces fail the audit scan with explicit violation messages.
"""

import os
from unittest.mock import patch
import pytest

from ai.observability.redaction import (
    redact_string,
    redact_telemetry_payload,
    scan_trace_for_secrets,
)


def test_redact_sensitive_strings():
    # 1. Bearer token
    bearer_str = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz123abc456"
    redacted = redact_string(bearer_str)
    assert "[REDACTED" in redacted
    assert "eyJhbGciOi" not in redacted

    # 2. OpenAI Key
    openai_str = "Using key sk-1234567890abcdef1234567890abcdef for provider"
    redacted = redact_string(openai_str)
    assert "[REDACTED_API_KEY]" in redacted
    assert "sk-123456" not in redacted

    # 3. Anthropic Key
    anthropic_str = "anthropic_key: sk-ant-api03-abcdef1234567890abcdef"
    redacted = redact_string(anthropic_str)
    assert "[REDACTED_API_KEY]" in redacted
    assert "sk-ant-api03" not in redacted

    # 4. AWS Access Key
    aws_str = "AWS credentials: AKIAIOSFODNN7EXAMPLE"
    redacted = redact_string(aws_str)
    assert "[REDACTED_AWS_KEY]" in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted

    # 5. Signed URL
    signed_url = "https://s3.amazonaws.com/bucket/video.mp4?X-Amz-Signature=abcd1234efgh5678ijkl9012mnop3456&Expires=1700000000"
    redacted = redact_string(signed_url)
    assert "X-Amz-Signature=[REDACTED_SIGNATURE]" in redacted
    assert "abcd1234efgh5678ijkl9012mnop3456" not in redacted


def test_telemetry_payload_redaction_and_privacy_policy():
    dirty_payload = {
        "operation": "render_scene",
        "api_key": "sk-1234567890abcdef1234567890abcdef",
        "authorization": "Bearer secret_user_token_99999",
        "raw_prompt": "Please summarize this secret customer document without leaking data.",
        "user_content": "Sensitive private customer transcript.",
        "config": {
            "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "signed_url": "https://storage.googleapis.com/asset.mp4?Signature=abcdef12345678901234",
            "safe_param": 42,
        },
    }

    # Clean payload with default privacy policy (no raw content logging)
    cleaned = redact_telemetry_payload(dirty_payload, allow_raw_content=False)

    # Assert secret fields are masked
    assert cleaned["api_key"] == "[REDACTED_SECRET]"
    assert cleaned["authorization"] == "[REDACTED_SECRET]"
    assert cleaned["config"]["aws_secret_key"] == "[REDACTED_SECRET]"
    assert "Signature=[REDACTED_SIGNATURE]" in cleaned["config"]["signed_url"]

    # Assert content privacy policy
    assert cleaned["raw_prompt"] == "[CONTENT_EXCLUDED_BY_PRIVACY_POLICY]"
    assert cleaned["user_content"] == "[CONTENT_EXCLUDED_BY_PRIVACY_POLICY]"
    assert cleaned["config"]["safe_param"] == 42

    # Assert audit scan confirms ZERO violations
    violations = scan_trace_for_secrets(cleaned)
    assert violations == [], f"Expected clean audit scan, got: {violations}"


def test_negative_audit_scanner_detects_unredacted_trace():
    leaky_trace = {
        "span_id": "spn_001",
        "attributes": {
            "api_key": "sk-unredactedkey123456789012345",
            "header": "Bearer unredacted_super_secret_token_12345",
            "signed_url": "https://storage.provider.com/file?Signature=exposed_sig_1234567890",
            "prompt": "Unredacted user prompt that violates default privacy policy",
        },
    }

    violations = scan_trace_for_secrets(leaky_trace)
    assert len(violations) >= 3
    violation_text = " ".join(violations)
    assert "Exposed secret in sensitive field" in violation_text or "Exposed API key" in violation_text
    assert "Exposed Bearer token" in violation_text
    assert "Exposed unredacted prompt/user content" in violation_text


def test_opt_in_content_logging():
    payload = {
        "prompt": "Analyze video shot duration.",
        "token": "secret_token_123456",
    }

    # With opt-in enabled
    cleaned_opted_in = redact_telemetry_payload(payload, allow_raw_content=True)

    # Prompt is preserved when explicitly opted in
    assert cleaned_opted_in["prompt"] == "Analyze video shot duration."
    # Secret is STILL redacted even with content logging opted in!
    assert cleaned_opted_in["token"] == "[REDACTED_SECRET]"
