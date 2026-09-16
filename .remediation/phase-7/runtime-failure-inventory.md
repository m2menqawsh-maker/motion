# Phase 7 Runtime Failure Inventory

This document tracks all known operational failures, their metadata, and their coverage status in Phase 7.

| FailureCode | Category | Severity | Retryable | Recoverable | Runbook Entry | Failure Matrix Entry | Test Coverage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ASSET_GATE_REJECTED** | GATE_FAILURE | WARNING | No | Yes | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
| **PLAN_GATE_REJECTED** | GATE_FAILURE | WARNING | No | Yes | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
| **TASTE_GATE_REJECTED** | GATE_FAILURE | WARNING | No | Yes | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
| **BLUEPRINT_VALIDATION_FAILED** | GATE_FAILURE | WARNING | No | Yes | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
| **MOTION_VALIDATION_FAILED** | GATE_FAILURE | WARNING | No | Yes | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
| **TEMPLATE_VALIDATION_FAILED** | GATE_FAILURE | WARNING | No | Yes | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
| **QC_GATE_FAILED** | GATE_FAILURE | ERROR | No | Yes | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
| **GATE_EXECUTION_FAILED** | INTERNAL_ERROR | ERROR | Yes | No | [x] Yes | [x] Yes | [x] `test_retry_policy.py`, `test_failure_injection.py` |
| **RENDER_PROCESS_FAILED** | RENDER_ERROR | ERROR | Yes | No | [x] Yes | [x] Yes | [x] `test_retry_policy.py` |
| **RENDER_TIMEOUT** | TIMEOUT | WARNING | Yes | Yes | [x] Yes | [x] Yes | [x] `test_failure_injection.py` |
| **RENDER_OUTPUT_MISSING** | IO_ERROR | ERROR | Yes | No | [x] Yes | [x] Yes | [x] `test_failure_injection.py` |
| **RENDER_DOCKER_FAILED** | RENDER_ERROR | ERROR | Yes | No | [x] Yes | [x] Yes | [x] `test_retry_policy.py` |
| **PROJECT_NOT_LOCKED** | VALIDATION_ERROR | WARNING | No | Yes | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
| **STATE_CORRUPTION** | STATE_ERROR | CRITICAL | No | No | [x] Yes | [x] Yes | [x] `test_recovery.py` |
| **SECURITY_POLICY_BLOCKED** | SECURITY_ERROR | CRITICAL | No | No | [x] Yes | [x] Yes | [x] `test_failure_injection.py` |
| **UNEXPECTED_INTERNAL_ERROR** | INTERNAL_ERROR | CRITICAL | No | No | [x] Yes | [x] Yes | [x] `test_failure_classification.py` |
