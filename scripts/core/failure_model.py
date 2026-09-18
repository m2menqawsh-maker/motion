from enum import Enum
from dataclasses import dataclass
from typing import Optional

class FailureCategory(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ASSET_ERROR = "ASSET_ERROR"
    GATE_FAILURE = "GATE_FAILURE"
    STATE_ERROR = "STATE_ERROR"
    RENDER_ERROR = "RENDER_ERROR"
    MCP_ERROR = "MCP_ERROR"
    TIMEOUT = "TIMEOUT"
    IO_ERROR = "IO_ERROR"
    SECURITY_ERROR = "SECURITY_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class FailureCode(str, Enum):
    # Gate Rejections
    ASSET_GATE_REJECTED = "ASSET_GATE_REJECTED"
    PLAN_GATE_REJECTED = "PLAN_GATE_REJECTED"
    TASTE_GATE_REJECTED = "TASTE_GATE_REJECTED"
    BLUEPRINT_VALIDATION_FAILED = "BLUEPRINT_VALIDATION_FAILED"
    MOTION_VALIDATION_FAILED = "MOTION_VALIDATION_FAILED"
    TEMPLATE_VALIDATION_FAILED = "TEMPLATE_VALIDATION_FAILED"
    QC_GATE_FAILED = "QC_GATE_FAILED"
    
    # Subprocess / Execution Failures
    GATE_EXECUTION_FAILED = "GATE_EXECUTION_FAILED"
    
    # Render Failures
    RENDER_PROCESS_FAILED = "RENDER_PROCESS_FAILED"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    RENDER_OUTPUT_MISSING = "RENDER_OUTPUT_MISSING"
    RENDER_DOCKER_FAILED = "RENDER_DOCKER_FAILED"
    PROJECT_NOT_LOCKED = "PROJECT_NOT_LOCKED"
    
    # Internal / State
    STATE_CORRUPTION = "STATE_CORRUPTION"
    SECURITY_POLICY_BLOCKED = "SECURITY_POLICY_BLOCKED"
    UNEXPECTED_INTERNAL_ERROR = "UNEXPECTED_INTERNAL_ERROR"
    
@dataclass
class FailureMetadata:
    category: FailureCategory
    severity: Severity
    retryable: bool
    recoverable: bool
    user_action_required: bool

# Central registry for failure metadata
_FAILURE_METADATA_REGISTRY = {
    # Gate Rejections: often recoverable by agent action, but not instantly retryable
    FailureCode.ASSET_GATE_REJECTED: FailureMetadata(FailureCategory.GATE_FAILURE, Severity.WARNING, retryable=False, recoverable=True, user_action_required=True),
    FailureCode.PLAN_GATE_REJECTED: FailureMetadata(FailureCategory.GATE_FAILURE, Severity.WARNING, retryable=False, recoverable=True, user_action_required=True),
    FailureCode.TASTE_GATE_REJECTED: FailureMetadata(FailureCategory.GATE_FAILURE, Severity.WARNING, retryable=False, recoverable=True, user_action_required=True),
    FailureCode.BLUEPRINT_VALIDATION_FAILED: FailureMetadata(FailureCategory.GATE_FAILURE, Severity.WARNING, retryable=False, recoverable=True, user_action_required=True),
    FailureCode.MOTION_VALIDATION_FAILED: FailureMetadata(FailureCategory.GATE_FAILURE, Severity.WARNING, retryable=False, recoverable=True, user_action_required=True),
    FailureCode.TEMPLATE_VALIDATION_FAILED: FailureMetadata(FailureCategory.GATE_FAILURE, Severity.WARNING, retryable=False, recoverable=True, user_action_required=True),
    FailureCode.QC_GATE_FAILED: FailureMetadata(FailureCategory.GATE_FAILURE, Severity.ERROR, retryable=False, recoverable=True, user_action_required=True),
    
    # Process Crashes
    FailureCode.GATE_EXECUTION_FAILED: FailureMetadata(FailureCategory.INTERNAL_ERROR, Severity.ERROR, retryable=True, recoverable=False, user_action_required=False),
    
    # Render
    FailureCode.RENDER_PROCESS_FAILED: FailureMetadata(FailureCategory.RENDER_ERROR, Severity.ERROR, retryable=True, recoverable=False, user_action_required=False),
    FailureCode.RENDER_TIMEOUT: FailureMetadata(FailureCategory.TIMEOUT, Severity.WARNING, retryable=True, recoverable=True, user_action_required=False),
    FailureCode.RENDER_OUTPUT_MISSING: FailureMetadata(FailureCategory.IO_ERROR, Severity.ERROR, retryable=True, recoverable=False, user_action_required=False),
    FailureCode.RENDER_DOCKER_FAILED: FailureMetadata(FailureCategory.RENDER_ERROR, Severity.ERROR, retryable=True, recoverable=False, user_action_required=False),
    FailureCode.PROJECT_NOT_LOCKED: FailureMetadata(FailureCategory.VALIDATION_ERROR, Severity.WARNING, retryable=False, recoverable=True, user_action_required=True),
    
    # State & Security
    FailureCode.STATE_CORRUPTION: FailureMetadata(FailureCategory.STATE_ERROR, Severity.CRITICAL, retryable=False, recoverable=False, user_action_required=True),
    FailureCode.SECURITY_POLICY_BLOCKED: FailureMetadata(FailureCategory.SECURITY_ERROR, Severity.CRITICAL, retryable=False, recoverable=False, user_action_required=True),
    FailureCode.UNEXPECTED_INTERNAL_ERROR: FailureMetadata(FailureCategory.INTERNAL_ERROR, Severity.CRITICAL, retryable=False, recoverable=False, user_action_required=True),
}

def get_failure_metadata(code: FailureCode) -> FailureMetadata:
    """Returns the metadata (category, severity, retry policy) for a given canonical FailureCode."""
    if code in _FAILURE_METADATA_REGISTRY:
        return _FAILURE_METADATA_REGISTRY[code]
    # Fallback if someone adds a code to Enum but forgets to register it
    return FailureMetadata(FailureCategory.INTERNAL_ERROR, Severity.CRITICAL, retryable=False, recoverable=False, user_action_required=True)

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
    
    def to_dict(self):
        meta = self.metadata
        return {
            "error_code": self.code.value,
            "error_category": meta.category.value,
            "severity": meta.severity.value,
            "retryable": meta.retryable,
            "recoverable": meta.recoverable,
            "user_action_required": meta.user_action_required,
            "error_message": self.message,
            "cause_type": self.cause_type,
            "stage": self.stage,
            "component": self.component,
            "is_fallback": self.is_fallback
        }
