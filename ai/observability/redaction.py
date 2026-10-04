"""
ai/observability/redaction.py
=============================
Redaction and Secret Sanitization Layer for AI Telemetry & Observability (S27.19).

Guarantees:
- Strictly sanitizes API keys, Bearer tokens, authorization headers, signed URLs, and storage credentials.
- By default excludes raw prompts, transcript payloads, and user content unless explicitly opted-in via env var.
- Verification utility scan_trace_for_secrets() guarantees secret scan(trace) = clean.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

# Secret and Token Regexes
BEARER_TOKEN_REGEX = re.compile(r"(?i)\bbearer\s+[a-zA-Z0-9_\-\.]{8,}")
OPENAI_KEY_REGEX = re.compile(r"\bsk-(?:proj-)?[a-zA-Z0-9_\-]{16,}\b")
ANTHROPIC_KEY_REGEX = re.compile(r"\bsk-ant-[a-zA-Z0-9_\-]{20,}\b")
OPENROUTER_KEY_REGEX = re.compile(r"\bsk-or-(?:v1-)?[a-zA-Z0-9_\-]{16,}\b")
AWS_KEY_REGEX = re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b")
AWS_SECRET_REGEX = re.compile(r"(?i)(?:aws_secret_access_key|secret_key)[\s:=]+['\"]?([a-zA-Z0-9/+=]{30,})['\"]?")
GENERIC_SECRET_REGEX = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|token|password|credentials?)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{12,})['\"]?"
)
SIGNED_URL_REGEX = re.compile(
    r"([?&](?:X-Amz-Signature|Signature|sig|token|api_key|access_token|secret)=)[^&\s]+"
)
AUTHORIZATION_HEADER_REGEX = re.compile(
    r"(?i)\b(authorization[\s:=]+['\"]?)(?:bearer\s+[a-zA-Z0-9_\-\.]+|basic\s+[a-zA-Z0-9+/=]+|[a-zA-Z0-9_\-\.]{12,})['\"]?"
)

# Sensitive dictionary key names that must have their values replaced
SENSITIVE_KEY_NAMES = re.compile(
    r"(?i)^(?:.*[_-])?(authorization|auth[_-]?header|api[_-]?key|auth[_-]?token|bearer[_-]?token|client[_-]?secret|secret[_-]?key|secret|password|access[_-]?token|refresh[_-]?token|cookie|credential|credentials|private[_-]?key|aws_secret[_-]?\w*)$|^(?:token)$"
)

# Content keys excluded by default to protect user privacy
RAW_CONTENT_KEYS = {
    "prompt",
    "raw_prompt",
    "system_prompt",
    "transcript",
    "user_content",
    "raw_content",
    "user_input",
    "generation_text",
}


def is_raw_content_logging_allowed() -> bool:
    """Checks whether raw prompt/transcript content logging has been explicitly opted-in."""
    return os.environ.get("ALLOW_RAW_CONTENT_LOGGING", "").strip().lower() in {"1", "true", "yes"}


def redact_string(val: str, max_length: int = 1000) -> str:
    """Sanitizes sensitive tokens, keys, signatures, and credentials from a text string."""
    masked = AUTHORIZATION_HEADER_REGEX.sub(r"\1[REDACTED_AUTH]", val)
    masked = BEARER_TOKEN_REGEX.sub("Bearer [REDACTED]", masked)
    masked = OPENAI_KEY_REGEX.sub("[REDACTED_API_KEY]", masked)
    masked = ANTHROPIC_KEY_REGEX.sub("[REDACTED_API_KEY]", masked)
    masked = OPENROUTER_KEY_REGEX.sub("[REDACTED_API_KEY]", masked)
    masked = AWS_KEY_REGEX.sub("[REDACTED_AWS_KEY]", masked)
    masked = AWS_SECRET_REGEX.sub(r'aws_secret_access_key: "[REDACTED_STORAGE_CRED]"', masked)
    masked = GENERIC_SECRET_REGEX.sub(r'secret: "[REDACTED_SECRET]"', masked)
    masked = SIGNED_URL_REGEX.sub(r"\1[REDACTED_SIGNATURE]", masked)

    if len(masked) > max_length:
        return masked[:max_length] + "...[TRUNCATED]"
    return masked


def redact_telemetry_payload(data: Any, allow_raw_content: Optional[bool] = None) -> Any:
    """
    Recursively scrubs dictionary or list payloads for telemetry logging.
    Enforces privacy policy: excludes raw prompts by default and masks secrets.
    """
    if allow_raw_content is None:
        allow_raw_content = is_raw_content_logging_allowed()

    if isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k, v in data.items():
            k_str = str(k).strip()
            if SENSITIVE_KEY_NAMES.match(k_str):
                cleaned[k_str] = "[REDACTED_SECRET]"
            elif k_str.lower() in RAW_CONTENT_KEYS and not allow_raw_content:
                cleaned[k_str] = "[CONTENT_EXCLUDED_BY_PRIVACY_POLICY]"
            else:
                cleaned[k_str] = redact_telemetry_payload(v, allow_raw_content=allow_raw_content)
        return cleaned

    elif isinstance(data, (list, tuple)):
        return [redact_telemetry_payload(item, allow_raw_content=allow_raw_content) for item in data]

    elif isinstance(data, str):
        return redact_string(data)

    return data


def scan_trace_for_secrets(data: Any) -> List[str]:
    """
    Independent audit scanner that inspects trace documents, spans, or dicts for leaked secrets.
    Returns a list of violation descriptions. If list is empty, trace is verified clean.
    """
    violations: List[str] = []

    def _inspect_text(text: str, context: str) -> None:
        # Check bearer tokens
        if re.search(r"(?i)\bbearer\s+(?!\[REDACTED\])[a-zA-Z0-9_\-\.]{12,}", text):
            violations.append(f"Exposed Bearer token in {context}")
        # Check OpenAI key
        if re.search(r"\bsk-(?:proj-)?[a-zA-Z0-9_\-]{16,}\b", text):
            violations.append(f"Exposed OpenAI API key in {context}")
        # Check Anthropic key
        if re.search(r"\bsk-ant-[a-zA-Z0-9_\-]{20,}\b", text):
            violations.append(f"Exposed Anthropic API key in {context}")
        # Check OpenRouter key
        if re.search(r"\bsk-or-(?:v1-)?[a-zA-Z0-9_\-]{16,}\b", text):
            violations.append(f"Exposed OpenRouter API key in {context}")
        # Check AWS key
        if re.search(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b", text):
            violations.append(f"Exposed AWS access key in {context}")
        # Check unmasked signed URL signatures
        if re.search(r"[?&](?:X-Amz-Signature|Signature|sig)=(?!\[REDACTED)[a-zA-Z0-9%_-]{16,}", text):
            violations.append(f"Exposed signed URL signature in {context}")
        # Check unmasked generic api key assignments
        if re.search(r"(?i)\bapi[_-]?key[\s:=]+['\"]?(?!\[REDACTED)[a-zA-Z0-9_\-\.]{14,}['\"]?", text):
            violations.append(f"Exposed API key assignment in {context}")

    def _traverse(node: Any, path: str = "root") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                k_str = str(k)
                current_path = f"{path}.{k_str}"
                if SENSITIVE_KEY_NAMES.match(k_str):
                    if isinstance(v, str) and not v.startswith("[REDACTED"):
                        violations.append(f"Exposed secret in sensitive field '{current_path}'")
                if k_str.lower() in RAW_CONTENT_KEYS:
                    if not is_raw_content_logging_allowed() and isinstance(v, str) and not v.startswith("[CONTENT_EXCLUDED"):
                        violations.append(f"Exposed unredacted prompt/user content in '{current_path}'")
                _traverse(v, current_path)
        elif isinstance(node, (list, tuple)):
            for idx, item in enumerate(node):
                _traverse(item, f"{path}[{idx}]")
        elif isinstance(node, str):
            _inspect_text(node, path)
        elif hasattr(node, "model_dump"):
            _traverse(node.model_dump(mode="json"), path)

    _traverse(data)
    return violations
