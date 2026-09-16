# Defect Policy (Zero-Known-Defects)

This project strictly adheres to a "Zero-Known-Defects" governance policy. This does not mean the system is flawless; it means **no defect exists without explicit triage, tracking, and a formal decision.**

## Defect Classifications & Enforcement

### 1. CRITICAL
System crash, data loss, security breach, or pipeline failure.
- **Enforcement:** Merge and release are strictly **BLOCKED**. Immediate containment required.

### 2. HIGH
Major feature broken, no workaround exists.
- **Enforcement:** Must be fixed before any new release.

### 3. MEDIUM
Non-critical bug, visual glitch, or issue with a viable workaround.
- **Enforcement:** Must be fixed OR explicitly accepted with a documented justification in an ADR or Incident Report.

### 4. LOW
Minor typos, non-breaking formatting issues.
- **Enforcement:** May be accepted if documented.

## The Zero-Known-Defects Promise
At any given time, the project guarantees:
- **0** untriaged known defects.
- **0** unresolved critical defects.
- **0** silently accepted defects (all known issues must have an explicit status).

## Valid Defect States
Any reported bug must enter one of these states:
- `OPEN` — Actively being fixed.
- `ACCEPTED-RISK` — Explicitly documented and justified.
- `FIXED` — Resolved and protected by a regression test.
- `INVALID` — Closed with evidence proving it is not a bug.
- `DUPLICATE` — Linked to the canonical issue.
