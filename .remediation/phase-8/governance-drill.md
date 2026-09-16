# Phase 8 Governance Drill

## Scenario A — Broken Test
- **Action:** A PR is submitted with a failing unit test.
- **Expected Result:** CI pipeline fails. Branch protection rules (to be enforced in GitHub) prevent the PR from being merged. **BLOCK**.

## Scenario B — Architecture Drift
- **Action:** A PR introduces a new pipeline script `scripts/new_pipeline.py`.
- **Expected Result:** `governance_audit.py` detects an unknown pipeline script and fails the CI check, OR the PR reviewers reject it because there is no ADR attached as required by `ARCHITECTURE_CHANGE_CONTROL.md`.

## Scenario C — Documentation Drift
- **Action:** A canonical path is changed without updating `ARCHITECTURE_TRUTH.md`.
- **Expected Result:** Docs consistency checks (to be added to CI) fail.

## Scenario D — Security Regression
- **Action:** Subprocess usage without restrictions added in a sandbox test.
- **Expected Result:** Governance audit or security linter flags the unsafe `subprocess` usage.

## Scenario E — New Bug
- **Action:** A new bug is reported (e.g., Engine fails on missing font).
- **Expected Result:** A new `INCIDENT_TEMPLATE.md` is filled out. Root Cause Analysis is performed. A fix is implemented, followed by a regression test to prevent recurrence, and the incident is closed.

## Scenario F — New Dependency
- **Action:** A new npm package is added to `package.json`.
- **Expected Result:** The PR Evidence Contract requires justification. `npm audit` runs in CI. The change cannot be merged silently.
