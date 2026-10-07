#!/usr/bin/env python3
"""
scripts/validators/check_secrets.py — Repository Static Secret Scanner (LED-081)
Scans codebase for leaked credentials, private keys, high-entropy API keys, and sensitive tokens.
Fails with exit code 1 if any unallowlisted, high-confidence secret is found.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple

PATTERNS = [
    ("Private Key", re.compile(r"-----BEGIN (?:\w+ )?PRIVATE KEY-----")),
    ("AWS Access Key ID", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    ("OpenAI API Key", re.compile(r"\b(sk-[a-zA-Z0-9]{20,})\b")),
    ("GitHub Personal Access Token", re.compile(r"\b(ghp_[a-zA-Z0-9]{36})\b")),
    ("Generic High-Entropy Secret", re.compile(r'(?i)(?:api_key|secret_key|password|bearer|auth_token)\s*[:=]\s*["\']([a-zA-Z0-9_\-\.]{32,})["\']')),
]

IGNORED_DIRS = {
    ".git", ".venv", "venv", "node_modules", ".pytest_cache", "__pycache__",
    ".agents/logs", "projects", "dist", "build", ".idea", ".vscode"
}

IGNORED_FILES = {
    "uv.lock", "package-lock.json", "check_secrets.py", "test_s24_architecture_guards.py",
    "test_s24_remediation_proof.py", "test_redaction.py", "test_ai_security.py"
}

ALLOWED_TEST_PATTERNS = [
    "production-test-secret-must-be-at-least-32-chars-long!",
    "another-completely-different-secret-key-32-chars!",
    "sk-proj-supersecretkey1234567890",
    "AKIAIOSFODNN7EXAMPLE",
    "sk-secret",
    "dummy",
    "test",
    "mock",
]

def is_allowed_value(val: str) -> bool:
    for allowed in ALLOWED_TEST_PATTERNS:
        if allowed in val or val in allowed:
            return True
    return False

def scan_file(file_path: Path) -> List[Tuple[int, str, str]]:
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    lines = content.splitlines()
    for line_idx, line in enumerate(lines, 1):
        # Skip comments indicating false positives or test comments
        if "# nosec" in line or "# test-token" in line or "# pragma: allowlist" in line:
            continue
        for name, regex in PATTERNS:
            for match in regex.finditer(line):
                secret = match.group(1) if match.groups() else match.group(0)
                if not is_allowed_value(secret):
                    findings.append((line_idx, name, secret[:8] + "..." if len(secret) > 8 else secret))
    return findings

def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    violations = 0

    print("🔍 [Secret Scanner] Scanning workspace for credentials and secrets...")

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.name in IGNORED_FILES or path.suffix in [".png", ".jpg", ".wav", ".mp4", ".pyc"]:
            continue

        file_findings = scan_file(path)
        for line_no, secret_type, snippet in file_findings:
            rel_path = path.relative_to(root)
            print(f"❌ [SECRET FOUND] {rel_path}:{line_no} — {secret_type} ({snippet})")
            violations += 1

    if violations > 0:
        print(f"\n🚨 Secret Scan FAILED: {violations} potential secret(s) found.")
        return 1

    print("✅ Secret Scan PASSED: No exposed credentials or secrets detected.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
