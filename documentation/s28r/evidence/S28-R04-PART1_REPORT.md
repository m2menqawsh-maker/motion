# S28-R04 Part 1 Milestone Report: Canonical Mutation Core

**Milestone**: S28-R04 — Part 1: Canonical Mutation Core  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Git Baseline Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Execution Date**: 2026-10-06  
**Final Status**: **PASS (100% Verified)**  

---

## 1. Executive Summary

Milestone **S28-R04 Part 1** establishes the formal mutation substrate for `BlueprintV2`, ensuring that it remains the **single authoritative source of truth** across all human, artificial intelligence, and automated editing operations.

Under this architecture:
- **No Second Truth**: No `EditorDocument` or runtime session fork is created. All operations mutate `BlueprintV2` directly.
- **Pure Mutation Engine**: `contracts/mutations.ts` contains zero imports from React, Remotion, Canvas, DOM, filesystem, network, or databases.
- **Deterministic & Wall-Clock Free**: 0 references to `Date.now()`, `performance.now()`, or `Math.random()`.
- **Domain-Aware Typed Mutations**: Replaces arbitrary JSON patches with a strictly typed discriminated union of 20 domain mutations (including all 18 core mutations requested).
- **Revision Tracking & Optimistic Concurrency**: Monotonic revision increments ($N \to N+1$) with compare-and-swap checks against `expected_revision`. Rejects stale edits with `REVISION_CONFLICT`.
- **Idempotency**: Automatic deduplication of `mutation_id` ensures safe network retries without duplicate side effects.
- **Batch Atomicity**: Compound mutations in `MutationBatch` execute all-or-nothing with automatic rollback upon any failure.
- **Granular Invalidation**: Computed `ChangeSet` metadata tracks affected IDs, bounding `time_range`, and flags (`requires_layout`, `requires_render`, `requires_audio_remix`, `requires_timeline_rebuild`).
- **Engine-Free Subprocess Proof**: Verified in an isolated subprocess with React and Remotion blocked at the Node.js module loader level.

---

## 2. Implemented Core Mutations Matrix

| Mutation Type | Scope | Target | Status |
| :--- | :--- | :--- | :--- |
| `UPDATE_TEXT` | Typography / Content | `{ scene_id, layer_id? }` | **PASS** |
| `UPDATE_TRANSFORM` | Spatial Layout | `{ scene_id, layer_id? }` | **PASS** |
| `ADD_LAYER` | Layer Stack | `{ scene_id }` | **PASS** |
| `REMOVE_LAYER` | Layer Stack | `{ scene_id, layer_id }` | **PASS** |
| `DUPLICATE_LAYER` | Layer Stack | `{ scene_id, layer_id }` | **PASS** |
| `REORDER_LAYER` | Layer Stack | `{ scene_id, layer_id }` | **PASS** |
| `MOVE_CLIP` | Timeline | `{ clip_id?, scene_id?, layer_id? }` | **PASS** |
| `TRIM_CLIP` | Timeline | `{ clip_id?, scene_id?, layer_id? }` | **PASS** |
| `SPLIT_CLIP` | Timeline | `{ clip_id?, scene_id?, layer_id? }` | **PASS** |
| `SET_KEYFRAME` | Keyframe Engine | `{ scene_id, layer_id, channel_id?, channel_target? }` | **PASS** |
| `UPDATE_KEYFRAME` | Keyframe Engine | `{ scene_id, layer_id, keyframe_id }` | **PASS** |
| `REMOVE_KEYFRAME` | Keyframe Engine | `{ scene_id, layer_id, keyframe_id }` | **PASS** |
| `SET_TRANSITION` | Scene Boundary | `{ scene_id }` | **PASS** |
| `REMOVE_TRANSITION` | Scene Boundary | `{ scene_id }` | **PASS** |
| `ADD_SCENE` | Project Structure | Project | **PASS** |
| `REMOVE_SCENE` | Project Structure | `{ scene_id }` | **PASS** |
| `DUPLICATE_SCENE` | Project Structure | `{ scene_id }` | **PASS** |
| `REORDER_SCENE` | Project Structure | `{ scene_id }` | **PASS** |
| `UPDATE_PROJECT` | Project Metadata | Project | **PASS** |
| `UPDATE_AUDIO` | Audio Plan | Project | **PASS** |

---

## 3. Test Verification & Conformance Evidence

### 3.1 S28 Test Suites Summary
```text
Test Files  10 passed (10)
Tests       75 passed (75)
Duration    6.36s

✓ tests/architecture/test_s28_r04_architecture_guards.test.ts (5 tests)
    ✓ R04-AG-01: mutations.ts exists in contracts/ and has ZERO imports from React or Remotion
    ✓ R04-AG-02: mutations.ts has ZERO wall-clock or non-deterministic dependencies
    ✓ R04-AG-03: mutations.ts has ZERO browser DOM, Canvas, or UI rendering dependencies
    ✓ R04-AG-04: mutations.ts has ZERO network, database, or filesystem I/O dependencies
    ✓ R04-AG-05: mutations.ts has ZERO unconstrained 'any' types in its exported signatures

✓ tests/remotion/s28_r04_mutations_core.test.ts (15 tests)
    ✓ MUT-01: Immutable Mutation — Original blueprint is never mutated
    ✓ MUT-02: Invalid edit leaves original unchanged (Fail-Closed)
    ✓ MUT-03: Optimistic concurrency — revision conflict rejected without silent overwrite
    ✓ MUT-04: Revision increments sequentially (N -> N+1)
    ✓ MUT-05: Idempotency — Re-applying identical mutation_id is a safe no-op
    ✓ MUT-06: Atomic Batch — All mutations succeed or entire batch rolls back
    ✓ MUT-07: Successful atomic batch advances document revision with aggregated changeset
    ✓ MUT-08: Target validation enforces stable alphanumeric IDs (no array indices)
    ✓ MUT-09: ADD_LAYER, DUPLICATE_LAYER, REORDER_LAYER, and REMOVE_LAYER
    ✓ MUT-10: REMOVE_LAYER fails closed when child layers are parented to it without cascade
    ✓ MUT-11: MOVE_CLIP, TRIM_CLIP, and SPLIT_CLIP on scenes
    ✓ MUT-12: SET_KEYFRAME, UPDATE_KEYFRAME, and REMOVE_KEYFRAME
    ✓ MUT-13: Transitions and Scene lifecycle mutations
    ✓ MUT-14: Normalization after edit + evaluateVideoAtFrame sees edited state
    ✓ MUT-15: User and AI use identical mutation contract and validation path

✓ tests/remotion/s28_r04_subprocess_isolation.test.ts (1 test)
    ✓ R04-ISO-01: Mutations apply and evaluate in pure isolated Node process with React/Remotion blocked

✓ tests/architecture/test_s28_r03_architecture_guards.test.ts (4 tests)
✓ tests/architecture/test_s28_r02_architecture_guards.test.ts (5 tests)
✓ tests/remotion/s28_r03_red_tests.test.ts (12 tests)
✓ tests/remotion/s28_r03_canonical_parity.test.ts (8 tests)
✓ tests/remotion/s28_r02_canonical_parity.test.ts (11 tests)
✓ tests/remotion/s28_r02_red_tests.test.ts (7 tests)
✓ tests/remotion/s28_06_render_smoke.test.ts (6 tests)
```

### 3.2 Regression Suite Verification
- Standard `npm test` suite: **153 passed (153)** across all contracts, templates, and smoke suites.
- Pytest architecture suite: **6 passed (6)** in `.venv/bin/pytest tests/architecture/test_s28_r02_architecture_guards.py`.
- Total test count: **174 (pre-R04) $\to$ 195 (post-R04)** with 0 failures and 0 regressions.

---

## 4. Subprocess Isolation Proof

To prove complete independence from rendering engines, an isolated Node subprocess was spawned with module interceptors blocking:
`react`, `react-dom`, `remotion`, `@remotion/transitions`, `@remotion/core`, `@remotion/cli`, `@remotion/google-fonts`.

Within this isolated environment:
1. Canonical blueprint was parsed and validated.
2. `applyMutation` applied single updates (text, layer, transform).
3. Optimistic concurrency conflict was confirmed.
4. Idempotency deduplication was confirmed.
5. `applyBatch` executed an atomic compound transaction.
6. `normalizeCanonicalVideo` normalized the edited blueprint into `NormalizedVideo`.
7. `evaluateVideoAtFrame` evaluated the frame state, observing updated layers and transforms.
8. Subprocess exited cleanly with exit code 0.

---

## 5. Artifacts Created & Updated

1. `contracts/mutations.ts`: Authoritative pure mutation engine, schemas, types, error codes, and changeset calculation.
2. `contracts/blueprint.ts`: Added additive optional `revision?: number` and `applied_mutations?: string[]` to `BlueprintV2Schema`.
3. `contracts/canonical-video.ts`: Re-exported all mutation engine primitives.
4. `contracts/index.ts`: Re-exported mutation primitives for consumer index.
5. `tests/architecture/test_s28_r04_architecture_guards.test.ts`: Architecture boundary guards.
6. `tests/remotion/s28_r04_mutations_core.test.ts`: 15 comprehensive domain tests.
7. `tests/remotion/s28_r04_subprocess_isolation.test.ts`: Engine-free subprocess isolation test.
8. `documentation/s28r/CANONICAL_MUTATION_MODEL.md`: Architecture specification.
9. `documentation/s28r/EDITOR_REVISION_MODEL.md`: Concurrency and revision specification.
10. `documentation/s28r/MUTATION_INVALIDATION_MODEL.md`: Invalidation specification.
11. `documentation/s28r/R04_COMPATIBILITY_MAP.md`: Compatibility matrix.
12. `documentation/s28r/evidence/S28-R04-PART1_REPORT.md`: This milestone closure report.
