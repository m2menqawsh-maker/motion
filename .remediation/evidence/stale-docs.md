# Stale Documentation Analysis
**Phase 1.5: Docs & Agent Instructions Mapping**

The following documents have been identified as referencing dead (zombie) systems, presenting a severe risk of Agent Hallucination:

## 1. Zombie Root Documents
- **`WORKSPACE_PIPELINE_EXPLAINED.md`**: Describes the dead `engine/` system and legacy primitives.
- **`workspace_overview.md`**: References disconnected components and deprecated paths.
- **`PROJECT_AUDIT_REPORT.md`**: Outdated analysis that does not reflect the current dual-pipeline reality.

## 2. Zombie Directories
- **`documentation/legacy/`**: Completely disconnected from current operations.
- **`documentation/archive/`**: Contains historic drafts that are still occasionally indexed by the Agent.

## 3. Ghost Instructions
- **`.agent_alerts.md`**: Protocol forces the Agent to read this, but it often contains stale context or is absent, causing unnecessary lookups.

## Recommendation
Move all items in category 1 and 2 to `.remediation/quarantine/old_docs/` to immediately prevent Agent hallucination. Update `AGENTS.md` to point ONLY to `ARCHITECTURE_TRUTH.md` (to be created in Phase 6).
