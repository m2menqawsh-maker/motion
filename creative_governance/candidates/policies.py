"""
creative_governance/candidates/policies.py
=========================
Centralized, machine-readable validation policies and failure codes for
TemplateCandidate Static Validation Gates (S28-07B).

Guarantees:
- Single canonical source of truth for security allowlists and forbidden modules.
- Deterministic, standardized failure codes (no ambiguous generic failures).
- Complete isolation from runtime execution or package installation.
"""

from __future__ import annotations

from typing import Any, Final, FrozenSet, List, Set

VALIDATION_POLICY_VERSION: Final[str] = "1.0.0"
RUNTIME_VALIDATION_POLICY_VERSION: Final[str] = "1.0.0"

# ─── Standardized Failure Codes ───────────────────────────────────────────────

class ValidationFailureCode:
    # Contract Gate (Section 6)
    MISSING_PROVENANCE = "MISSING_PROVENANCE"
    TENANT_WORKSPACE_MISMATCH = "TENANT_WORKSPACE_MISMATCH"
    PROJECT_OWNERSHIP_INVALID = "PROJECT_OWNERSHIP_INVALID"
    INVALID_PLAN_REFERENCE = "INVALID_PLAN_REFERENCE"
    INVALID_TIER_DECISION_REFERENCE = "INVALID_TIER_DECISION_REFERENCE"
    MISSING_REUSE_RATIONALE = "MISSING_REUSE_RATIONALE"
    MISSING_COMPOSE_RATIONALE = "MISSING_COMPOSE_RATIONALE"
    MISSING_SOURCE_CODE = "MISSING_SOURCE_CODE"
    MISSING_TEMPLATE_SCHEMA = "MISSING_TEMPLATE_SCHEMA"
    MISSING_FIXTURES = "MISSING_FIXTURES"
    INVALID_DEPENDENCIES_FORMAT = "INVALID_DEPENDENCIES_FORMAT"
    CONTENT_HASH_MISMATCH = "CONTENT_HASH_MISMATCH"

    # Static Code Gate (Section 7)
    SYNTAX_ERROR = "SYNTAX_ERROR"
    COMMONJS_FORBIDDEN = "COMMONJS_FORBIDDEN"
    MISSING_COMPONENT_EXPORT = "MISSING_COMPONENT_EXPORT"
    FORBIDDEN_EVAL = "FORBIDDEN_EVAL"
    FORBIDDEN_NEW_FUNCTION = "FORBIDDEN_NEW_FUNCTION"
    FORBIDDEN_DYNAMIC_CODE = "FORBIDDEN_DYNAMIC_CODE"
    FORBIDDEN_DYNAMIC_REQUIRE = "FORBIDDEN_DYNAMIC_REQUIRE"
    FORBIDDEN_DYNAMIC_IMPORT = "FORBIDDEN_DYNAMIC_IMPORT"
    NODE_SPECIFIC_API_FORBIDDEN = "NODE_SPECIFIC_API_FORBIDDEN"
    RAW_FILESYSTEM_ASSUMPTION = "RAW_FILESYSTEM_ASSUMPTION"

    # Security Gate (Section 8)
    SECURITY_FORBIDDEN_FS = "SECURITY_FORBIDDEN_FS"
    SECURITY_FORBIDDEN_CHILD_PROCESS = "SECURITY_FORBIDDEN_CHILD_PROCESS"
    SECURITY_FORBIDDEN_NETWORK = "SECURITY_FORBIDDEN_NETWORK"
    SECURITY_FORBIDDEN_THREADS = "SECURITY_FORBIDDEN_THREADS"
    SECURITY_FORBIDDEN_CLUSTER = "SECURITY_FORBIDDEN_CLUSTER"
    SECURITY_FORBIDDEN_VM = "SECURITY_FORBIDDEN_VM"
    SECURITY_FORBIDDEN_RUNTIME = "SECURITY_FORBIDDEN_RUNTIME"
    SECURITY_FORBIDDEN_OS = "SECURITY_FORBIDDEN_OS"
    SECURITY_FORBIDDEN_EXEC = "SECURITY_FORBIDDEN_EXEC"
    SECURITY_FORBIDDEN_ENV_ACCESS = "SECURITY_FORBIDDEN_ENV_ACCESS"

    # Dependency Gate (Section 9)
    UNDECLARED_IMPORT = "UNDECLARED_IMPORT"
    FORBIDDEN_DEPENDENCY = "FORBIDDEN_DEPENDENCY"
    UNKNOWN_EXTERNAL_DEPENDENCY = "UNKNOWN_EXTERNAL_DEPENDENCY"
    INVALID_DEPENDENCY_SPECIFIER = "INVALID_DEPENDENCY_SPECIFIER"

    # TypeScript Gate (Section 10)
    TYPESCRIPT_TYPE_ERROR = "TYPESCRIPT_TYPE_ERROR"
    TYPESCRIPT_SYNTAX_ERROR = "TYPESCRIPT_SYNTAX_ERROR"
    TYPESCRIPT_JSX_ERROR = "TYPESCRIPT_JSX_ERROR"
    VALIDATOR_EXECUTION_ERROR = "VALIDATOR_EXECUTION_ERROR"

    # Template Schema Gate (Section 11)
    INVALID_SCHEMA_STRUCTURE = "INVALID_SCHEMA_STRUCTURE"
    CORRUPTED_SCHEMA = "CORRUPTED_SCHEMA"
    UNSUPPORTED_PROPERTY_TYPE = "UNSUPPORTED_PROPERTY_TYPE"
    INVALID_REQUIRED_PROPERTIES = "INVALID_REQUIRED_PROPERTIES"
    EMPTY_FIXTURES = "EMPTY_FIXTURES"
    FIXTURE_SCHEMA_MISMATCH = "FIXTURE_SCHEMA_MISMATCH"

    # Concurrency / Orchestrator (Section 4)
    STALE_VALIDATION = "STALE_VALIDATION"

    # ─── S28-07C: Runtime Validation Failure Codes ───
    # Preconditions & Lifecycle
    NO_STATIC_PASS_FOUND = "NO_STATIC_PASS_FOUND"
    STALE_STATIC_PASS = "STALE_STATIC_PASS"
    INVALID_CANDIDATE_STATUS = "INVALID_CANDIDATE_STATUS"
    STALE_RUNTIME_VALIDATION = "STALE_RUNTIME_VALIDATION"

    # Render Smoke Gate (Section 7)
    CANDIDATE_RUNTIME_FAILURE = "CANDIDATE_RUNTIME_FAILURE"
    RENDER_SMOKE_FAILED = "RENDER_SMOKE_FAILED"
    RENDER_MOUNT_ERROR = "RENDER_MOUNT_ERROR"
    RENDER_IMPORT_ERROR = "RENDER_IMPORT_ERROR"
    RENDER_INVALID_PROPS = "RENDER_INVALID_PROPS"
    RENDER_EXCEPTION = "RENDER_EXCEPTION"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    RENDER_EMPTY_OUTPUT = "RENDER_EMPTY_OUTPUT"
    RENDER_TOOL_EXECUTION_ERROR = "RENDER_TOOL_EXECUTION_ERROR"

    # Runtime Contract Gate (Section 9)
    RUNTIME_CONTRACT_VIOLATION = "RUNTIME_CONTRACT_VIOLATION"
    INVALID_RUNTIME_FPS = "INVALID_RUNTIME_FPS"
    INVALID_RUNTIME_DURATION = "INVALID_RUNTIME_DURATION"
    INVALID_RUNTIME_FIXTURES = "INVALID_RUNTIME_FIXTURES"

    # Aspect Gate (Section 9)
    ASPECT_RENDER_FAILED = "ASPECT_RENDER_FAILED"
    UNSUPPORTED_ASPECT_RATIO = "UNSUPPORTED_ASPECT_RATIO"
    ASPECT_DIMENSIONS_MISMATCH = "ASPECT_DIMENSIONS_MISMATCH"

    # Probe Gate (Section 11)
    PROBE_FRAME_MISSING = "PROBE_FRAME_MISSING"
    PROBE_DIMENSIONS_MISMATCH = "PROBE_DIMENSIONS_MISMATCH"
    PROBE_CORRUPT_HEADER = "PROBE_CORRUPT_HEADER"
    PROBE_TOOL_EXECUTION_ERROR = "PROBE_TOOL_EXECUTION_ERROR"

    # Candidate QC Gate (Section 12 & 13)
    QC_BLACK_OUTPUT = "QC_BLACK_OUTPUT"
    QC_EMPTY_OUTPUT = "QC_EMPTY_OUTPUT"
    QC_CORRUPT_FRAME = "QC_CORRUPT_FRAME"
    QC_INVALID_DIMENSIONS = "QC_INVALID_DIMENSIONS"
    QC_TOOL_EXECUTION_ERROR = "QC_TOOL_EXECUTION_ERROR"


# ─── Machine-Readable Security Policy (Section 8) ─────────────────────────────

FORBIDDEN_SECURITY_MODULES: Final[FrozenSet[str]] = frozenset({
    "fs", "node:fs", "fs/promises", "node:fs/promises",
    "child_process", "node:child_process",
    "net", "node:net",
    "tls", "node:tls",
    "http", "node:http",
    "https", "node:https",
    "dgram", "node:dgram",
    "dns", "node:dns",
    "worker_threads", "node:worker_threads",
    "cluster", "node:cluster",
    "vm", "node:vm",
    "v8", "node:v8",
    "repl", "node:repl",
    "os", "node:os",
    "path", "node:path",
    "axios", "node-fetch", "got", "needle", "superagent", "request",
    "ws", "socket.io",
})

FORBIDDEN_CALLS: Final[FrozenSet[str]] = frozenset({
    "eval",
    "Function",
    "exec",
    "spawn",
    "execSync",
    "spawnSync",
    "fork",
})

NODE_SPECIFIC_APIS: Final[FrozenSet[str]] = frozenset({
    "process.exit",
    "process.kill",
    "process.abort",
    "__dirname",
    "__filename",
})

SENSITIVE_ENV_KEYWORDS: Final[FrozenSet[str]] = frozenset({
    "KEY", "SECRET", "TOKEN", "PASSWORD", "AUTH", "CREDENTIAL", "PRIVATE", "API",
})


# ─── Machine-Readable Dependency Policy (Section 9) ───────────────────────────

APPROVED_CORE_PACKAGES: Final[FrozenSet[str]] = frozenset({
    "react",
    "react/jsx-runtime",
    "react-dom",
    "remotion",
    "@remotion/transitions",
    "@remotion/google-fonts",
    "@remotion/cli",
    "zod",
    "culori",
    "maplibre-gl",
    "remotion-bits",
})

FORBIDDEN_DEPENDENCY_PACKAGES: Final[FrozenSet[str]] = frozenset({
    "child_process",
    "fs",
    "shelljs",
    "puppeteer",
    "playwright",
    "electron",
    "dotenv",
    "express",
    "fastify",
    "ws",
    "socket.io",
    "needle",
    "request",
    "axios",
    "got",
    "superagent",
})

# ─── S28-07C: Canonical Aspect Ratios & QC Profile ───────────────────────────

CANONICAL_ASPECT_RATIOS: Final[dict[str, tuple[int, int]]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "21:9": (2560, 1080),
}

CANDIDATE_RUNTIME_QC_PROFILE: Final[dict[str, Any]] = {
    "check_black_frame": True,
    "black_threshold_mean": 2.0,      # Mean luminance below 2.0 considered pure black
    "check_empty_frame": True,
    "empty_variance_threshold": 0.5,  # Variance below 0.5 considered completely blank
    "check_dimensions": True,
    "check_image_integrity": True,
}

