# Architecture Change Control

## Purpose
This document defines the formal process for introducing architectural changes to the Clean Video Workspace.

## What is an Architectural Change?
An architectural change is any modification that affects:
- Canonical Pipeline (`scripts/pipeline.py`)
- Canonical State (`.pipeline_state.json`)
- API → Pipeline boundary
- Gates (e.g., Taste Gates, Output Gates)
- Engine integration (`templates/effects/engine-bridge.tsx`)
- MCP security boundary
- Agent protocol
- Core Contracts

Not every implementation detail requires an ADR. An ADR is ONLY required when changing **how the system is built or how its components interact.**

## The Change Process

1. **Proposal:** Submit an initial proposal for the architectural change.
2. **ADR Creation:** Draft an Architecture Decision Record (ADR) in `.remediation/decisions/ADR-XXX-name.md`.
3. **Impact Analysis:** Analyze the architectural impact (Pipeline, State, Invariants).
4. **Architecture Tests:** Write or update architecture tests to enforce the new design.
5. **Truth Update:** Update `ARCHITECTURE_TRUTH.md` if the fundamental truth of the system has changed.
6. **Implementation:** Proceed with code implementation.

## ADR Template Requirements
Every ADR must include:
- Context
- Decision
- Alternatives
- Consequences
- Migration
- Rollback
- Affected Invariants
