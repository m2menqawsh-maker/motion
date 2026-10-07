"""
ai/security/scrubber.py
=======================
Secret Scrubber & Data Loss Prevention for AI Workflows (S27.22 / AI-15).

Invariants:
- Zero Secret Exfiltration: API keys, bearer tokens, storage secrets, credentials,
  and signed URL sensitive signatures must NEVER leak into prompts, tool outputs,
  traces, logs, or artifact metadata.
- Deterministic redaction with replacement token [REDACTED_SECRET].
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union


class SecretScrubber:
    """
    Scans and redacts sensitive credentials and secrets from text and nested payloads.
    """

    PATTERNS = [
        # Bearer tokens & JWTs
        (re.compile(r"Bearer\s+([A-Za-z0-9\-_\.=]{16,})", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
        (re.compile(r"eyJ[A-Za-z0-9\-_]{10,}\.eyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_\.]{10,}"), "[REDACTED_JWT]"),
        # OpenAI keys
        (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "[REDACTED_OPENAI_KEY]"),
        # Google API keys
        (re.compile(r"AIza[0-9A-Za-z\-_]{30,40}"), "[REDACTED_GOOGLE_KEY]"),
        # AWS Access Keys & Secrets
        (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
        (re.compile(r"aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]", re.IGNORECASE), "aws_secret_access_key='[REDACTED_AWS_SECRET]'"),
        # Generic Secret / Password / Token assignments
        (re.compile(r"(api[_-]?key|secret|token|password|auth|authorization)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", re.IGNORECASE), r"\1='[REDACTED_SECRET]'"),
        # Signed URL signatures / query params
        (re.compile(r"(signature|sig|x-amz-signature|token)=([A-Za-z0-9%_-]{20,})", re.IGNORECASE), r"\1=[REDACTED_SIGNATURE]"),
    ]

    @classmethod
    def scrub_text(cls, text: str) -> str:
        """Applies regex redactions across raw string."""
        if not text:
            return ""
        result = text
        for pattern, replacement in cls.PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def scrub_payload(cls, data: Any) -> Any:
        """Recursively traverses dictionaries, lists, and strings to redact sensitive secrets."""
        if isinstance(data, str):
            return cls.scrub_text(data)
        if isinstance(data, dict):
            clean_dict = {}
            for k, v in data.items():
                # If key itself denotes a secret, redact value entirely
                if any(sec_term in str(k).lower() for sec_term in ["password", "secret", "token", "apikey", "api_key"]):
                    clean_dict[k] = "[REDACTED_SECRET]"
                else:
                    clean_dict[k] = cls.scrub_payload(v)
            return clean_dict
        if isinstance(data, list):
            return [cls.scrub_payload(item) for item in data]
        return data
