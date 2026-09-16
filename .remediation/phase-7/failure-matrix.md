# Phase 7 Failure Matrix

| Scenario | Expected Code | Retry | Recovery | Final State | Runbook Reference |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Render timeout | RENDER_TIMEOUT / GATE_EXECUTION_FAILED | Yes | No | Success (if retry passes) or Failed cleanly | Section 2 |
| Missing asset | GATE_EXECUTION_FAILED | No (SAFE_TO_RETRY but often fails fast) | Yes / manual fix | Blocked | Section 1 |
| Checkpoint corruption | STATE_CORRUPTION / PROJECT_NOT_LOCKED | No | Safe rejection | Restart from safe stage | Section 3 |
| Pipeline crash after plan | None (Process died) | N/A | Yes | Resumes from BLUEPRINT | Section 4 |
| Silent failure (missing out.mp4) | RENDER_OUTPUT_MISSING | Yes | No | Caught by postcondition, Retried | Section 2 |
| Malformed log line | UNEXPECTED_INTERNAL_ERROR | N/A | Metrics survive | Logged as `corrupted_events` | Section 4 |
