# Undo / Redo & Editor Session Architecture Model

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R04 Part 2  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Governing Module**: `contracts/editor-session.ts`, `contracts/mutations.ts`  
**Date**: 2026-10-06  

---

## 1. Executive Summary & Core Invariant

The **Undo / Redo & Editor Session Engine** provides live interactive state management, bi-directional history traversal, transient interactive manipulation (such as high-frequency 60fps scrubber and layer dragging), and intelligent mutation coalescing.

### Crucial Architectural Invariant: Single Source of Truth
**No secondary authoritative video document (`EditorDocument` or duplicate state tree) is permitted.**  
The live editor session operates strictly as a transactional wrapper over pure `BlueprintV2`. The canonical video document remains the sole authoritative truth across UI previews, AI generation, and downstream export rendering.

```text
USER / AI AGENT
       │
       ▼
[Canonical Mutation / Batch]
       │
       ▼
[EditorSession Engine] ──(Validates, applies, tracks history)──► [Pure BlueprintV2]
       │                                                              │
       ├─ Undo Stack (Bounded)                                        ▼
       ├─ Redo Stack (Invalidated on branch fork)             [normalizeCanonicalVideo]
       └─ Transient Gesture Draft (Active mouse drag)                 │
                                                                      ▼
                                                            [evaluateVideoAtFrame]
```

---

## 2. Bijective Undo & Redo Semantics

The undo/redo model guarantees 100% bijective restoration of the canonical video state:

$$\text{State } A \xrightarrow{\quad\text{Mutation}\quad} \text{State } B$$
$$\text{State } B \xrightarrow{\quad\text{Undo}\quad} \text{State } A$$
$$\text{State } A \xrightarrow{\quad\text{Redo}\quad} \text{State } B$$

### 2.1 Reversibility Guarantees
- **Exact State Restoration**: Undoing an operation restores the exact prior document revision, applied mutation set, layer hierarchies, keyframes, transitions, and audio configurations.
- **Redoing an Operation**: Re-applies the exact forward result without loss of fidelity.
- **Bijective Equivalence**: For any committed state $S_0$ mutated by $M$ to $S_1$, $\text{Undo}(S_1) \equiv S_0$.

---

## 3. History Entry Specification

Every committed modification or atomic compound batch creates a structured `HistoryEntry`:

```typescript
export interface HistoryChangedEntities {
  scene_ids: string[];
  layer_ids: string[];
  track_ids: string[];
  clip_ids: string[];
  keyframe_ids: string[];
}

export interface HistoryEntry {
  command_id: string;
  description?: string;
  actor: "user" | "ai" | "system";
  gesture_id?: string;
  forward_mutations: CanonicalMutation[];
  inverse_mutations: CanonicalMutation[];
  revision_before: number;
  revision_after: number;
  changed_entities: HistoryChangedEntities;
  snapshot_before: BlueprintV2;
  snapshot_after: BlueprintV2;
}
```

### 3.1 Inverse Mutations vs Snapshots
1. **Computed Inverse Mutations (`computeInverseMutation`)**:  
   Every canonical mutation type ($20/20$) possesses an exact pure inverse function (e.g. `ADD_LAYER` inverts to `REMOVE_LAYER`, `UPDATE_TRANSFORM` inverts to an `UPDATE_TRANSFORM` carrying the prior coordinate payload, `SPLIT_CLIP` inverts to clip duration restoration and secondary scene removal).
2. **Snapshot Acceleration**:  
   For $O(1)$ fast rendering recovery and zero-computation undo operations, the bounded history entry retains `snapshot_before` and `snapshot_after`. The combination provides immediate state flipping plus rich auditability.

---

## 4. Redo Branch Invalidation (Branch Forking)

When a user or AI executes an undo and then executes a **new** forward mutation, a branch fork occurs:

$$\text{State } A \to \text{State } B \xrightarrow{\text{Undo}} \text{State } A \xrightarrow{\text{New Mutation } C} \text{State } C$$

### Rule of Branch Invalidation:
- The entire `redoStack` is immediately discarded (`redoStack = []`).
- Re-entering the $B$ branch is impossible unless explicitly tracked by version control.
- Prevents split-brain state trees, divergent histories, and phantom mutations.

---

## 5. Transient Editing vs Committed Mutations

Interactive canvas operations (such as dragging transform handles, resizing bounding boxes, or scrubbing time sliders) fire at up to 60fps. Directly committing each mouse movement as an authoritative revision would generate thousands of history entries and catastrophic memory bloat.

### 5.1 Architecture of a Drag Gesture:
1. **`applyTransientMutation(mutation, gestureId)`**:
   - Updates `transientDraft` in real time at 60fps.
   - Evaluates fast preview transforms for viewport rendering.
   - **Does NOT advance canonical document revision**.
   - **Does NOT pollute the undo stack** (`undoStack.length` remains unchanged).
2. **`commitGesture(gestureId, description)`**:
   - Invoked on mouse-up / gesture completion.
   - Executes semantic validation on the final drafted blueprint.
   - Advances canonical revision: $\text{revision} \to \text{revision} + 1$.
   - Pushes **exactly ONE** combined history entry representing the net result of the entire gesture.
3. **`cancelGesture(gestureId)`**:
   - Invoked on Escape key or cancelled pointer.
   - Discards `transientDraft` cleanly, restoring viewport preview to `currentBlueprint`.

---

## 6. Safe Mutation Coalescing

In scenarios where rapid discrete mutations occur outside an explicit drag gesture (e.g. continuous typing in a text field or rapid property slider nudges), the engine supports safe mutation coalescing.

### The 4 Strict Invariants for Coalescing:
Mutation $M_{t+1}$ coalesces with topmost undo entry $E_t$ **ONLY IF**:
1. **Same Actor**: $M_{t+1}.\text{author} \equiv E_t.\text{actor}$ (User edits NEVER coalesce with AI edits).
2. **Same Target**: Targets identical `scene_id`, `layer_id`, `clip_id`, `track_id`, and `keyframe_id`.
3. **Same Operation Family**: $M_{t+1}.\text{type} \equiv E_t.\text{forward\_mutations}[0].\text{type}$.
4. **Same Gesture Token**: If gesture IDs are defined, they must match identically.

When coalescing occurs:
- The topmost history entry updates its `forward_mutations` to the latest payload and advances `revision_after`.
- The original `snapshot_before` is retained, guaranteeing that a single undo command reverts all coalesced keystrokes/nudges back to the initial pre-edit state.

---

## 7. Bounded & Configurable History

To avoid unbounded memory growth in long-running browser sessions:
- `maxHistorySize` is configurable (default: `100` entries).
- When `undoStack.length > maxHistorySize`, the oldest entry is dropped (`undoStack.shift()`).
- High-frequency transient gestures coalesce to 1 entry per gesture, keeping memory consumption strictly bounded.

---

## 8. Persistence & Autosave Boundaries

The boundary between interactive session memory and durable persistence is strictly defined:

```text
Committed Mutation (Revision N -> N+1)
       │
       ▼
[EditorSession.isDirty() === true]
       │
       ▼ (Debounced Autosave / Explicit Save)
[Durable Storage (Database / File)]
       │
       ▼
[EditorSession.markSaved()] ──► isDirty() resets to false
```

### Persistence Invariants:
1. **History Is Purely In-Memory**: History stacks are editor conveniences. Export rendering and durable database records store ONLY the canonical `BlueprintV2` at its current revision.
2. **Dirty Tracking**:
   - `isDirty()` evaluates `getRevision() !== lastSavedRevision`.
   - Undoing back to the revision where the document was last saved resets `isDirty()` to `false`.
   - Undoing past the saved point marks the document dirty again.
3. **Fail-Closed Autosave**: If validation fails during mutation application, the document remains untouched and un-persisted.
