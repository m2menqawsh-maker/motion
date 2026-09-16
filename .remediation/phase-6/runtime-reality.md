# Phase 6.0: Runtime Reality Snapshot

This document records the exact state of the project as it operates *right now*, following the cleanup and containment phases. It forms the baseline for the canonical architecture.

## Canonical Paths

- **Canonical Pipeline**: `scripts/pipeline.py`
- **Canonical State**: `.pipeline_state.json`
- **Rendering Engine**: Remotion (`remotion-app/`)

## Engine Status: ACTIVE

The engine subsystem is active and connected. The legacy audit mischaracterized it as a zombie or disconnected system.

**Integration Path:**
`templates/effects/engine-bridge.tsx` -> `remotion-app/src/engine/`

**Evidence:**
- `EngineBridge` is actively imported and used in the blueprint generation and `BlueprintVideo.tsx`.
- TypeScript compilation and type checks pass.
- Backend regression tests against the pipeline and blueprint merging pass.

## Backend APIs

- **API Layer**: `api/services/`
- **API integration**: Routes calls into the official pipeline service (`scripts/pipeline.py`) preventing parallel pipeline logic.

## Contracts & Types

- `contracts/blueprint.ts` defines the canonical video representation.
- Merging logic in `merge.ts` feeds into `BlueprintVideo`.

## Content Inventory (Approximate)
- Templates: ~87
- Recipes: ~20
- Scenes: ~60
- Compositions: ~22

### Conclusion
The architecture is running exactly as defined by the canonical pipeline. There are no two active pipelines. The engine is fully restored and operational.
