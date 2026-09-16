# Change Policy (Change Classification)

Every change to this project must be classified into one of the following levels to determine its review, testing, and approval requirements.

## LEVEL-0 — Documentation Only
Changes that only affect Markdown files, comments, or non-executable documentation.
- **Requirements:**
  - Pull Request
  - Link to issue or reason

## LEVEL-1 — Low-Risk Implementation Change
Minor bug fixes, refactoring of implementation details, or isolated component tweaks that do not affect architecture or boundaries.
- **Requirements:**
  - PR Evidence Contract (WHY, WHAT, EVIDENCE)
  - Unit tests updated/added
  - CI must pass

## LEVEL-2 — Behavioral Change
Changes that alter how the application behaves, new features, or modifications to API responses.
- **Requirements:**
  - PR Evidence Contract
  - Unit and integration tests
  - Regression tests for the affected behavior
  - Behavioral impact documented
  - CI must pass

## LEVEL-3 — Architectural Change
Changes that modify system boundaries, state management, Canonical Pipeline, or component contracts.
- **Requirements:**
  - Architecture Decision Record (ADR)
  - Architecture impact analysis
  - Architecture tests updated
  - Rollback plan defined
  - Clean Agent Review

## LEVEL-4 — Security / State / Pipeline Change
Critical changes that affect the core pipeline execution, state persistence mechanisms, permissions, or MCP boundaries.
- **Requirements:**
  - ADR
  - Threat/security review
  - Rollback plan
  - Failure/recovery tests
  - Integration and E2E tests
  - Explicit user approval (Clean Agent Review mandatory)
