from enum import Enum
from dataclasses import dataclass
import time
from typing import Optional
from scripts.failure_model import FailureInfo, FailureCode

class IdempotencyClass(str, Enum):
    SAFE_TO_RETRY = "SAFE_TO_RETRY"
    CONDITIONALLY_RETRYABLE = "CONDITIONALLY_RETRYABLE"
    NOT_RETRYABLE = "NOT_RETRYABLE"

@dataclass
class RetryDecision:
    should_retry: bool
    reason: str
    next_attempt: int
    delay_seconds: int
    max_attempts: int

class RetryPolicyEngine:
    # A mapping to define max attempts per category or specific error. Default is 3 for retryable.
    # Delay could be attempt * 1s.
    
    @staticmethod
    def evaluate(
        failure: FailureInfo, 
        idempotency: IdempotencyClass, 
        current_attempt: int,
        is_state_valid: bool = True
    ) -> RetryDecision:
        
        meta = failure.metadata
        max_attempts = RetryPolicyEngine._get_max_attempts(failure.code)
        
        # 1. Is operation idempotency class allowed?
        if idempotency == IdempotencyClass.NOT_RETRYABLE:
            return RetryDecision(
                should_retry=False, 
                reason="Operation is NOT_RETRYABLE", 
                next_attempt=current_attempt, 
                delay_seconds=0, 
                max_attempts=max_attempts
            )
            
        # 2. Is failure retryable?
        if not meta.retryable:
            return RetryDecision(
                should_retry=False, 
                reason=f"Failure {failure.code.name} is not retryable", 
                next_attempt=current_attempt, 
                delay_seconds=0, 
                max_attempts=max_attempts
            )
            
        # 3. Have max attempts been exhausted?
        if current_attempt >= max_attempts:
            return RetryDecision(
                should_retry=False, 
                reason=f"Max attempts exhausted ({max_attempts})", 
                next_attempt=current_attempt, 
                delay_seconds=0, 
                max_attempts=max_attempts
            )
            
        # 4. Is current state valid for retry?
        if not is_state_valid:
            return RetryDecision(
                should_retry=False, 
                reason="State is invalid for retry", 
                next_attempt=current_attempt, 
                delay_seconds=0, 
                max_attempts=max_attempts
            )
            
        # 5. All yes -> Schedule retry
        next_attempt = current_attempt + 1
        delay_seconds = RetryPolicyEngine._get_backoff(current_attempt)
        
        return RetryDecision(
            should_retry=True,
            reason=f"Retrying after {failure.code.name}",
            next_attempt=next_attempt,
            delay_seconds=delay_seconds,
            max_attempts=max_attempts
        )
        
    @staticmethod
    def _get_max_attempts(code: FailureCode) -> int:
        if code == FailureCode.RENDER_TIMEOUT:
            return 3
        if code == FailureCode.RENDER_PROCESS_FAILED or code == FailureCode.RENDER_DOCKER_FAILED:
            return 2
        return 3 # default
        
    @staticmethod
    def _get_backoff(current_attempt: int) -> int:
        """
        Simple fixed/exponential backoff.
        current_attempt 1 -> 1s
        current_attempt 2 -> 3s
        """
        if current_attempt == 1:
            return 1
        elif current_attempt == 2:
            return 3
        else:
            return 5
            
    @staticmethod
    def delay_for(decision: RetryDecision):
        """Abstraction for delaying. Can be mocked in tests."""
        if decision.should_retry and decision.delay_seconds > 0:
            time.sleep(decision.delay_seconds)
