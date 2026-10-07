# Editor Revision Model & Concurrency Specification

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R04 Part 1  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Governing Modules**: `contracts/mutations.ts`, `contracts/blueprint.ts`  
**Date**: 2026-10-06  

---

## 1. Executive Summary

In a multi-actor editing environment where **Human Users**, **Autonomous AI Agents**, and **Automated Pipeline Tasks** propose modifications to a video project, reliable concurrency control is paramount. The **Editor Revision Model** establishes:
1. **Monotonic Document Revisions**: Every persistent modification increments the project revision $N \to N+1$.
2. **Optimistic Concurrency Control (OCC / CAS)**: Mutations declare an `expected_revision`. Stale edits are rejected with structured `REVISION_CONFLICT` errors.
3. **Idempotency Guarantees**: Mutations declare a unique `mutation_id`. Duplicate deliveries (e.g. network retries) are recognized as no-ops.
4. **Batch Atomicity**: Compound editing operations execute all-or-nothing in a single transaction.

---

## 2. Document Revision Semantics

A canonical `BlueprintV2` document contains two foundational tracking attributes:
```typescript
{
  "blueprint_version": "2.0.0",
  "project_id": "prj_example_01",
  "revision": 3,
  "applied_mutations": ["mut_user_01", "mut_ai_optimize_02", "mut_user_trim_03"],
  ...
}
```

- **Initial State**: Newly created projects start at `revision: 0` with `applied_mutations: []`. Legacy documents omitting these fields automatically default to revision `0` during parsing.
- **Monotonic Increment**: Each successful mutation advances the revision:
  $$\text{revision}_{t+1} = \text{revision}_t + 1$$
- **Atomic Commits**: No intermediate, partial, or corrupted revisions are ever observable.

---

## 3. Optimistic Concurrency Control (OCC)

When proposing a mutation, clients provide `expected_revision?: number`:

```typescript
const mutation: UpdateTextMutation = {
  mutation_id: "mut_user_edit_headline",
  type: "UPDATE_TEXT",
  expected_revision: 5,
  target: { scene_id: "sc_intro" },
  payload: { text: "Updated Headline" },
};
```

### 3.1 Conflict Resolution Logic

When `applyMutation(blueprint, mutation)` evaluates:
1. **Idempotency check runs first**: If `mutation.mutation_id` is already in `blueprint.applied_mutations`, the mutation succeeds immediately as an idempotent no-op (`idempotent: true`).
2. **Revision validation**: If `mutation.expected_revision !== undefined` and `mutation.expected_revision !== blueprint.revision`:
   The mutation is rejected fail-closed.
3. **Structured Error Output**:
   ```json
   {
     "success": false,
     "revision": 6,
     "blueprint": "<ORIGINAL_UNTOUCHED_BLUEPRINT>",
     "applied_mutation_ids": [],
     "changeset": { ... },
     "error": {
       "code": "REVISION_CONFLICT",
       "message": "Optimistic concurrency conflict: expected revision 5, but current revision is 6",
       "mutation_id": "mut_user_edit_headline",
       "expected_revision": 5,
       "actual_revision": 6
     }
   }
   ```
4. **Zero Silent Overwrite**: The server or engine will NEVER silently overwrite changes made by a concurrent actor.

---

## 4. Idempotency Model (`mutation_id`)

In distributed, agentic, or web environments, network retries and duplicate event dispatches can cause the same mutation to arrive multiple times.

### Invariants:
1. Every mutation MUST have a valid stable `mutation_id` (`/^[a-zA-Z0-9_\-]+$/`).
2. If `blueprint.applied_mutations.includes(mutation.mutation_id)`:
   - The mutation is recognized as already committed.
   - The document is NOT modified.
   - The revision is NOT incremented.
   - The engine returns `{ success: true, revision: currentRevision, idempotent: true }`.
3. Retrying a request that succeeded previously is completely safe and free of side effects.

---

## 5. Batch Transaction Atomicity (`MutationBatch`)

When multiple mutations must take effect together (e.g. splitting a scene into two, moving multiple clips, or replacing an entire layer group), they are packaged as a `MutationBatch`:

```typescript
export interface MutationBatch {
  batch_id: string;
  mutations: CanonicalMutation[];
  expected_revision?: number;
  author?: "user" | "ai" | "system";
  description?: string;
}
```

### Atomicity Guarantees:
1. **Transaction Isolation**: Mutations execute sequentially on an in-memory draft clone.
2. **All-or-Nothing Rollback**: If ANY mutation in the batch fails (due to target not found, hierarchy cycle, invalid parameter, or semantic validation failure), the entire batch is aborted.
3. **Rollback State**: The original blueprint is returned 100% intact, and the error code `BATCH_EXECUTION_FAILED` identifies the exact mutation and underlying error.
4. **Unified Commit**: If all mutations succeed, revision advances atomically, and an aggregated `ChangeSet` covering all affected entities is returned.

---

## 6. Live Editor Session & Transient Gestures

The `EditorSession` manages live interactive sessions while preserving `BlueprintV2` as the sole authority:

```typescript
export class EditorSession {
  private currentBlueprint: BlueprintV2;
  private lastSavedRevision: number;
  private undoStack: HistoryEntry[] = [];
  private redoStack: HistoryEntry[] = [];
  private maxHistorySize: number;
  // Transient state for pointer drags
  private transientDraft: BlueprintV2 | null = null;
  ...
}
```

### 6.1 Transient Revisions vs Committed Revisions
- **Transient Edits (Drags / Sliders)**: Mouse events fire `applyTransientMutation()`. The working revision of `currentBlueprint` does NOT increment. Preview viewport evaluates `transientDraft`.
- **Gesture Commitment**: Mouse release fires `commitGesture()`, validating final state and advancing canonical revision: $\text{revision} \to \text{revision} + 1$.
- **Unified Undo Entry**: 500 transient updates collapse into exactly 1 history entry.

---

## 7. Persistence & Save Boundaries

| Stage | Trigger | Scope | Authoritative Source |
| :--- | :--- | :--- | :--- |
| **Interactive Draft** | Mouse drag | Ephemeral in-memory | `transientDraft` |
| **Committed Revision** | Pointer up / command | Memory + Undo Stack | `currentBlueprint` (Revision $N$) |
| **Durable Save** | Autosave / user save | Database / File Storage | Serialized `BlueprintV2` |

- `isDirty()` is `true` whenever `currentBlueprint.revision !== lastSavedRevision`.
- `markSaved()` updates `lastSavedRevision = currentBlueprint.revision`.
- Rendering and headless exports load only durable `BlueprintV2`. The interactive history stack is never required for video rendering.

