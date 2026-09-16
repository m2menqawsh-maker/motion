# Decision Record: Legacy Documentation Quarantine

## Context
During Phase 5 (Quarantine & Cleanup), it was identified that eferences/WORKFLOW_EXAMPLES.md and eferences/CUSTOM_CODE_GUIDE.md contained deprecated guidelines that conflicted with the strict Protocol v3.0+.
WORKFLOW_EXAMPLES.md promoted the quarantined workflows/ directory and outdated Python tools.
CUSTOM_CODE_GUIDE.md instructed users to create custom templates in projects/<project_id>/custom/ which violates the unified template catalog approach.

## Decision
Quarantine these legacy documentation files to prevent agents and users from adopting outdated, insecure practices.

## Actions Taken
- Moved eferences/WORKFLOW_EXAMPLES.md to .remediation/quarantine/references/
- Moved eferences/CUSTOM_CODE_GUIDE.md to .remediation/quarantine/references/

## Status
Completed as part of QAC-06.
