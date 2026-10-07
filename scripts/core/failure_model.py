from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import subprocess


class RetryDisposition(str, Enum):
    NEVER = "NEVER"
    RETRYABLE = "RETRYABLE"
    CONDITIONALLY_RETRYABLE = "CONDITIONALLY_RETRYABLE"


class FailureCategory(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ASSET_ERROR = "ASSET_ERROR"
    GATE_FAILURE = "GATE_FAILURE"
    STATE_ERROR = "STATE_ERROR"
    STATE_CONFLICT = "STATE_CONFLICT"
    RENDER_ERROR = "RENDER_ERROR"
    MCP_ERROR = "MCP_ERROR"
    TIMEOUT = "TIMEOUT"
    IO_ERROR = "IO_ERROR"
    SECURITY_ERROR = "SECURITY_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    CANCELLED_ERROR = "CANCELLED_ERROR"
    TRANSIENT_EXTERNAL = "TRANSIENT_EXTERNAL"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FailureCode(str, Enum):
    # Gate Rejections & Validations (Deterministic -> NEVER retry)
    ASSET_GATE_REJECTED = "ASSET_GATE_REJECTED"
    PLAN_GATE_REJECTED = "PLAN_GATE_REJECTED"
    TASTE_GATE_REJECTED = "TASTE_GATE_REJECTED"
    BLUEPRINT_VALIDATION_FAILED = "BLUEPRINT_VALIDATION_FAILED"
    MOTION_VALIDATION_FAILED = "MOTION_VALIDATION_FAILED"
    TEMPLATE_VALIDATION_FAILED = "TEMPLATE_VALIDATION_FAILED"
    QC_GATE_FAILED = "QC_GATE_FAILED"
    PROJECT_NOT_LOCKED = "PROJECT_NOT_LOCKED"

    # S09 Review & Render Authorization
    REVIEW_BUNDLE_MISSING = "REVIEW_BUNDLE_MISSING"
    REVIEW_BUNDLE_STALE = "REVIEW_BUNDLE_STALE"
    REVIEW_NOT_APPROVED = "REVIEW_NOT_APPROVED"
    REVIEW_IDENTITY_INVALID = "REVIEW_IDENTITY_INVALID"
    RENDER_NOT_AUTHORIZED = "RENDER_NOT_AUTHORIZED"

    # S18 Probe & Evidence Bundle Failures
    PROBE_INVALID_BLUEPRINT = "PROBE_INVALID_BLUEPRINT"
    PROBE_FRAME_RENDER_FAILED = "PROBE_FRAME_RENDER_FAILED"
    PROBE_CONTACT_SHEET_FAILED = "PROBE_CONTACT_SHEET_FAILED"
    PROBE_REPORT_FAILED = "PROBE_REPORT_FAILED"
    PROBE_EVIDENCE_STALE = "PROBE_EVIDENCE_STALE"

    # S10 Contracts & Dependency Graph
    CONTRACT_AUTHORITY_VIOLATION = "CONTRACT_AUTHORITY_VIOLATION"
    CONTRACT_VERSION_UNSUPPORTED = "CONTRACT_VERSION_UNSUPPORTED"
    DEPENDENCY_GRAPH_INVALID = "DEPENDENCY_GRAPH_INVALID"
    INVALIDATION_PLAN_STALE = "INVALIDATION_PLAN_STALE"

    # Execution / Subprocess Failures
    GATE_EXECUTION_FAILED = "GATE_EXECUTION_FAILED"

    # Timeouts & Transient (RETRYABLE)
    TIMEOUT = "TIMEOUT"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    RENDERER_TIMEOUT = "RENDERER_TIMEOUT"
    TRANSIENT_NETWORK_ERROR = "TRANSIENT_NETWORK_ERROR"

    # Render Failures (CONDITIONALLY_RETRYABLE)
    RENDER_PROCESS_FAILED = "RENDER_PROCESS_FAILED"
    RENDER_OUTPUT_MISSING = "RENDER_OUTPUT_MISSING"
    RENDER_DOCKER_FAILED = "RENDER_DOCKER_FAILED"
    RENDERER_UNAVAILABLE = "RENDERER_UNAVAILABLE"
    RENDERER_EXECUTION_FAILED = "RENDERER_EXECUTION_FAILED"
    RENDERER_OUTPUT_INVALID = "RENDERER_OUTPUT_INVALID"
    RENDERER_CANCELLED = "RENDERER_CANCELLED"
    RENDERER_CAPABILITY_MISMATCH = "RENDERER_CAPABILITY_MISMATCH"

    # State & Preconditions
    STATE_CORRUPTION = "STATE_CORRUPTION"
    STATE_CONFLICT = "STATE_CONFLICT"
    RETRY_PRECONDITION_FAILED = "RETRY_PRECONDITION_FAILED"

    # Artifacts
    ARTIFACT_MISSING = "ARTIFACT_MISSING"
    ARTIFACT_CORRUPTED = "ARTIFACT_CORRUPTED"

    # Security & Unexpected Internal
    SECURITY_POLICY_BLOCKED = "SECURITY_POLICY_BLOCKED"
    UNEXPECTED_INTERNAL_ERROR = "UNEXPECTED_INTERNAL_ERROR"

    # S28-R14 Integration & Section 27 Taxonomy
    REVISION_CONFLICT = "REVISION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    AUTHORING_TARGET_NOT_FOUND = "AUTHORING_TARGET_NOT_FOUND"
    AUTHORING_TARGET_AMBIGUOUS = "AUTHORING_TARGET_AMBIGUOUS"
    UNSUPPORTED_AUTHORING_OPERATION = "UNSUPPORTED_AUTHORING_OPERATION"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TENANT_SCOPE_VIOLATION = "TENANT_SCOPE_VIOLATION"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    RUN_CANCELLED = "RUN_CANCELLED"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
    PERSISTENCE_CONFLICT = "PERSISTENCE_CONFLICT"


@dataclass
class FailureMetadata:
    category: FailureCategory
    severity: Severity
    retry_disposition: RetryDisposition
    retryable: bool
    recoverable: bool
    user_action_required: bool
    max_attempts: int = 1


# Central registry for failure metadata
_FAILURE_METADATA_REGISTRY: Dict[FailureCode, FailureMetadata] = {
    # Gate Rejections & Validations: Deterministic -> NEVER retry
    FailureCode.ASSET_GATE_REJECTED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.WARNING, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.PLAN_GATE_REJECTED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.WARNING, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.TASTE_GATE_REJECTED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.WARNING, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.BLUEPRINT_VALIDATION_FAILED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.WARNING, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.MOTION_VALIDATION_FAILED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.WARNING, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.TEMPLATE_VALIDATION_FAILED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.WARNING, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.QC_GATE_FAILED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.PROJECT_NOT_LOCKED: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.WARNING, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.REVIEW_BUNDLE_MISSING: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.REVIEW_BUNDLE_STALE: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.REVIEW_NOT_APPROVED: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.REVIEW_IDENTITY_INVALID: FailureMetadata(
        FailureCategory.SECURITY_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.RENDER_NOT_AUTHORIZED: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),

    # S18 Probe & Evidence Bundle Failures
    FailureCode.PROBE_INVALID_BLUEPRINT: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.PROBE_FRAME_RENDER_FAILED: FailureMetadata(
        FailureCategory.RENDER_ERROR, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=2
    ),
    FailureCode.PROBE_CONTACT_SHEET_FAILED: FailureMetadata(
        FailureCategory.RENDER_ERROR, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=2
    ),
    FailureCode.PROBE_REPORT_FAILED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=2
    ),
    FailureCode.PROBE_EVIDENCE_STALE: FailureMetadata(
        FailureCategory.STATE_CONFLICT, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),

    # S10 Contracts & Dependency Graph
    FailureCode.CONTRACT_AUTHORITY_VIOLATION: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.CRITICAL, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.CONTRACT_VERSION_UNSUPPORTED: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.DEPENDENCY_GRAPH_INVALID: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.CRITICAL, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.INVALIDATION_PLAN_STALE: FailureMetadata(
        FailureCategory.STATE_CONFLICT, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=True, user_action_required=False, max_attempts=2
    ),

    # Timeouts & Transient: RETRYABLE
    FailureCode.TIMEOUT: FailureMetadata(
        FailureCategory.TIMEOUT, Severity.WARNING, RetryDisposition.RETRYABLE, retryable=True, recoverable=True, user_action_required=False, max_attempts=3
    ),
    FailureCode.RENDER_TIMEOUT: FailureMetadata(
        FailureCategory.TIMEOUT, Severity.WARNING, RetryDisposition.RETRYABLE, retryable=True, recoverable=True, user_action_required=False, max_attempts=3
    ),
    FailureCode.TRANSIENT_NETWORK_ERROR: FailureMetadata(
        FailureCategory.TRANSIENT_EXTERNAL, Severity.WARNING, RetryDisposition.RETRYABLE, retryable=True, recoverable=True, user_action_required=False, max_attempts=3
    ),

    # Render & Execution: CONDITIONALLY_RETRYABLE
    FailureCode.RENDER_PROCESS_FAILED: FailureMetadata(
        FailureCategory.RENDER_ERROR, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=2
    ),
    FailureCode.RENDER_DOCKER_FAILED: FailureMetadata(
        FailureCategory.RENDER_ERROR, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=2
    ),
    FailureCode.RENDER_OUTPUT_MISSING: FailureMetadata(
        FailureCategory.IO_ERROR, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=2
    ),
    FailureCode.RENDERER_TIMEOUT: FailureMetadata(
        FailureCategory.TIMEOUT, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=2
    ),
    FailureCode.RENDERER_UNAVAILABLE: FailureMetadata(
        FailureCategory.RENDER_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.RENDERER_EXECUTION_FAILED: FailureMetadata(
        FailureCategory.RENDER_ERROR, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=2
    ),
    FailureCode.RENDERER_OUTPUT_INVALID: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.RENDERER_CANCELLED: FailureMetadata(
        FailureCategory.CANCELLED_ERROR, Severity.INFO, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=False, max_attempts=1
    ),
    FailureCode.RENDERER_CAPABILITY_MISMATCH: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.GATE_EXECUTION_FAILED: FailureMetadata(
        FailureCategory.INTERNAL_ERROR, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=False, user_action_required=False, max_attempts=3
    ),

    # State & Conflicts
    FailureCode.STATE_CORRUPTION: FailureMetadata(
        FailureCategory.STATE_ERROR, Severity.CRITICAL, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.STATE_CONFLICT: FailureMetadata(
        FailureCategory.STATE_CONFLICT, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=True, user_action_required=False, max_attempts=2
    ),
    FailureCode.RETRY_PRECONDITION_FAILED: FailureMetadata(
        FailureCategory.STATE_CONFLICT, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=False, max_attempts=1
    ),

    # Artifacts
    FailureCode.ARTIFACT_MISSING: FailureMetadata(
        FailureCategory.IO_ERROR, Severity.ERROR, RetryDisposition.CONDITIONALLY_RETRYABLE, retryable=True, recoverable=True, user_action_required=False, max_attempts=2
    ),
    FailureCode.ARTIFACT_CORRUPTED: FailureMetadata(
        FailureCategory.IO_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),

    # Security & Unexpected Internal
    FailureCode.SECURITY_POLICY_BLOCKED: FailureMetadata(
        FailureCategory.SECURITY_ERROR, Severity.CRITICAL, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.UNEXPECTED_INTERNAL_ERROR: FailureMetadata(
        FailureCategory.INTERNAL_ERROR, Severity.CRITICAL, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),

    # S28-R14 Metadata
    FailureCode.REVISION_CONFLICT: FailureMetadata(
        FailureCategory.STATE_CONFLICT, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.IDEMPOTENCY_CONFLICT: FailureMetadata(
        FailureCategory.STATE_CONFLICT, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.PERSISTENCE_CONFLICT: FailureMetadata(
        FailureCategory.STATE_CONFLICT, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=True, user_action_required=True, max_attempts=1
    ),
    FailureCode.AUTHORING_TARGET_NOT_FOUND: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.AUTHORING_TARGET_AMBIGUOUS: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.UNSUPPORTED_AUTHORING_OPERATION: FailureMetadata(
        FailureCategory.VALIDATION_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.UNAUTHORIZED: FailureMetadata(
        FailureCategory.SECURITY_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.FORBIDDEN: FailureMetadata(
        FailureCategory.SECURITY_ERROR, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.TENANT_SCOPE_VIOLATION: FailureMetadata(
        FailureCategory.SECURITY_ERROR, Severity.CRITICAL, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.BUDGET_EXCEEDED: FailureMetadata(
        FailureCategory.GATE_FAILURE, Severity.ERROR, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=True, max_attempts=1
    ),
    FailureCode.RUN_CANCELLED: FailureMetadata(
        FailureCategory.CANCELLED_ERROR, Severity.INFO, RetryDisposition.NEVER, retryable=False, recoverable=False, user_action_required=False, max_attempts=1
    ),
    FailureCode.STORAGE_UNAVAILABLE: FailureMetadata(
        FailureCategory.TRANSIENT_EXTERNAL, Severity.ERROR, RetryDisposition.RETRYABLE, retryable=True, recoverable=True, user_action_required=False, max_attempts=3
    ),
}


def get_failure_metadata(code: FailureCode) -> FailureMetadata:
    """Returns the metadata (category, severity, retry policy) for a given canonical FailureCode."""
    if code in _FAILURE_METADATA_REGISTRY:
        return _FAILURE_METADATA_REGISTRY[code]
    return FailureMetadata(
        FailureCategory.INTERNAL_ERROR,
        Severity.CRITICAL,
        RetryDisposition.NEVER,
        retryable=False,
        recoverable=False,
        user_action_required=True,
    )


@dataclass
class FailureInfo:
    code: FailureCode
    message: str
    cause_type: Optional[str] = None
    stage: Optional[str] = None
    component: Optional[str] = None
    is_fallback: bool = False

    @property
    def metadata(self) -> FailureMetadata:
        return get_failure_metadata(self.code)

    @property
    def retry_disposition(self) -> RetryDisposition:
        return self.metadata.retry_disposition

    def to_dict(self) -> Dict[str, Any]:
        meta = self.metadata
        return {
            "code": self.code.value,
            "error_code": self.code.value,
            "category": meta.category.value,
            "error_category": meta.category.value,
            "severity": meta.severity.value,
            "retry_disposition": meta.retry_disposition.value,
            "retryable": meta.retryable,
            "recoverable": meta.recoverable,
            "user_action_required": meta.user_action_required,
            "error_message": self.message,
            "cause_type": self.cause_type,
            "stage": self.stage,
            "component": self.component,
            "is_fallback": self.is_fallback,
        }


class FailureClassifier:
    """
    Authoritative classifier for mapping script executions, exit codes,
    and exceptions to canonical FailureCode and FailureInfo.
    Replaces generic GATE_EXECUTION_FAILED blanket with specific domain failure codes.
    """

    @staticmethod
    def classify(
        script_name: str,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        exception: Optional[Exception] = None,
        stage: Optional[str] = None,
        component: Optional[str] = None,
    ) -> FailureInfo:
        combined_text = f"{stdout}\n{stderr}"
        if exception:
            combined_text += f"\n{exception}"

        clean_script = str(script_name).replace("\\", "/").lower()

        # 1. Security policy blocks
        if (
            "securitypolicy" in combined_text.lower()
            or "security alert" in combined_text.lower()
            or "path traversal" in combined_text.lower()
            or isinstance(exception, PermissionError)
        ):
            return FailureInfo(
                code=FailureCode.SECURITY_POLICY_BLOCKED,
                message=f"Security policy blocked operation in {script_name}",
                cause_type="SecurityPolicyBlocked",
                stage=stage,
                component=component or "security",
            )

        # R14 Renderer Specific Failures
        if "RENDERER_TIMEOUT" in combined_text:
            return FailureInfo(
                code=FailureCode.RENDERER_TIMEOUT,
                message=f"Renderer node execution timed out in {script_name}",
                cause_type="RendererTimeoutError",
                stage=stage or "render",
                component=component or "renderer",
            )
        if "RENDERER_UNAVAILABLE" in combined_text:
            return FailureInfo(
                code=FailureCode.RENDERER_UNAVAILABLE,
                message=f"Assigned renderer is unavailable in {script_name}",
                cause_type="RendererUnavailableError",
                stage=stage or "render",
                component=component or "renderer",
            )
        if "RENDERER_CAPABILITY_MISMATCH" in combined_text:
            return FailureInfo(
                code=FailureCode.RENDERER_CAPABILITY_MISMATCH,
                message=f"Renderer capability mismatch in {script_name}",
                cause_type="CapabilityMismatchError",
                stage=stage or "render",
                component=component or "renderer",
            )
        if "RENDERER_OUTPUT_INVALID" in combined_text:
            return FailureInfo(
                code=FailureCode.RENDERER_OUTPUT_INVALID,
                message=f"Renderer produced invalid media output in {script_name}",
                cause_type="InvalidOutputError",
                stage=stage or "render",
                component=component or "renderer",
            )
        if "RENDERER_CANCELLED" in combined_text:
            return FailureInfo(
                code=FailureCode.RENDERER_CANCELLED,
                message=f"Renderer execution was cancelled in {script_name}",
                cause_type="CancelledError",
                stage=stage or "render",
                component=component or "renderer",
            )
        if "RENDERER_EXECUTION_FAILED" in combined_text:
            return FailureInfo(
                code=FailureCode.RENDERER_EXECUTION_FAILED,
                message=f"Renderer execution failed in {script_name}",
                cause_type="ExecutionFailedError",
                stage=stage or "render",
                component=component or "renderer",
            )

        # 2. Timeouts
        if (
            isinstance(exception, (TimeoutError, subprocess.TimeoutExpired))
            or "timed out" in combined_text.lower()
            or "timeout" in combined_text.lower()
            or returncode == -9
        ):
            code = FailureCode.RENDER_TIMEOUT if "render" in clean_script else FailureCode.TIMEOUT
            return FailureInfo(
                code=code,
                message=f"Operation timed out in {script_name}",
                cause_type="TimeoutError",
                stage=stage,
                component=component or "timeout",
            )

        # 3. State conflicts
        if "stateconflict" in combined_text.lower() or "stale revision" in combined_text.lower():
            return FailureInfo(
                code=FailureCode.STATE_CONFLICT,
                message="State conflict or stale revision detected",
                cause_type="StateConflictError",
                stage=stage,
                component=component or "state",
            )

        # 4. Gate-specific mappings
        if "validate_blueprint" in clean_script or "blueprint" in clean_script and returncode != 0:
            return FailureInfo(
                code=FailureCode.BLUEPRINT_VALIDATION_FAILED,
                message=f"Blueprint validation failed in {script_name}",
                cause_type=type(exception).__name__ if exception else "BlueprintValidationError",
                stage=stage or "blueprint",
                component=component or "validate_blueprint",
            )

        if "motion_validator" in clean_script:
            return FailureInfo(
                code=FailureCode.MOTION_VALIDATION_FAILED,
                message=f"Motion contract validation failed in {script_name}",
                cause_type=type(exception).__name__ if exception else "MotionValidationError",
                stage=stage or "blueprint",
                component=component or "motion_validator",
            )

        if "code_template_gate" in clean_script or "template_lint" in clean_script:
            return FailureInfo(
                code=FailureCode.TEMPLATE_VALIDATION_FAILED,
                message=f"Template validation failed in {script_name}",
                cause_type=type(exception).__name__ if exception else "TemplateValidationError",
                stage=stage or "blueprint",
                component=component or "code_template_gate",
            )

        if "taste_gate" in clean_script:
            return FailureInfo(
                code=FailureCode.TASTE_GATE_REJECTED,
                message=f"Taste gate rejected plan in {script_name}",
                cause_type=type(exception).__name__ if exception else "TasteGateRejected",
                stage=stage or "plan",
                component=component or "taste_gate",
            )

        if "plan_gate" in clean_script:
            return FailureInfo(
                code=FailureCode.PLAN_GATE_REJECTED,
                message=f"Plan gate rejected plan in {script_name}",
                cause_type=type(exception).__name__ if exception else "PlanGateRejected",
                stage=stage or "plan",
                component=component or "plan_gate",
            )

        if "asset_gate" in clean_script:
            return FailureInfo(
                code=FailureCode.ASSET_GATE_REJECTED,
                message=f"Asset gate rejected manifest in {script_name}",
                cause_type=type(exception).__name__ if exception else "AssetGateRejected",
                stage=stage or "assets",
                component=component or "asset_gate",
            )

        if "probe_qc" in clean_script or "final_qc" in clean_script or "smart_qc" in clean_script:
            return FailureInfo(
                code=FailureCode.QC_GATE_FAILED,
                message=f"Quality control verification failed in {script_name}",
                cause_type=type(exception).__name__ if exception else "QCGateFailed",
                stage=stage or "qc",
                component=component or "qc_gate",
            )

        if "render_project" in clean_script or "render" in clean_script:
            if "project_not_locked" in combined_text.upper():
                return FailureInfo(
                    code=FailureCode.PROJECT_NOT_LOCKED,
                    message="Render blocked: Project is not approved for rendering",
                    cause_type="ProjectNotLocked",
                    stage=stage or "render",
                    component=component or "render_project",
                )
            if "docker" in combined_text.lower():
                return FailureInfo(
                    code=FailureCode.RENDER_DOCKER_FAILED,
                    message="Docker render container execution failed",
                    cause_type="DockerError",
                    stage=stage or "render",
                    component=component or "render_project",
                )
            if "out.mp4" in combined_text.lower() and ("missing" in combined_text.lower() or "not created" in combined_text.lower()):
                return FailureInfo(
                    code=FailureCode.RENDER_OUTPUT_MISSING,
                    message="Render output video file (out.mp4) was not created",
                    cause_type="RenderOutputMissing",
                    stage=stage or "render",
                    component=component or "render_project",
                )
            return FailureInfo(
                code=FailureCode.RENDER_PROCESS_FAILED,
                message=f"Render process failed in {script_name}",
                cause_type=type(exception).__name__ if exception else "RenderProcessError",
                stage=stage or "render",
                component=component or "render_project",
            )

        # 5. Fallback classification
        if exception and not isinstance(exception, RuntimeError):
            return FailureInfo(
                code=FailureCode.UNEXPECTED_INTERNAL_ERROR,
                message=str(exception),
                cause_type=type(exception).__name__,
                stage=stage,
                component=component,
                is_fallback=True,
            )

        return FailureInfo(
            code=FailureCode.GATE_EXECUTION_FAILED,
            message=str(exception) if exception else f"{script_name} failed with code {returncode}",
            cause_type=type(exception).__name__ if exception else "ExecutionError",
            stage=stage,
            component=component,
            is_fallback=False,
        )
