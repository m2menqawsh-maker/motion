# AI and User Unified Editing Rules (S28-R13)

**Status**: Verified Production Specification  
**Milestone**: S28-R13 — AI + Templates + Editor Unified Authoring  
**Authoritative Subsystems**: `authoring/unified-authoring-session.ts`, `contracts/editor-session.ts`

---

## 1. Unified Pipeline Rule

**Human users and AI agents must pass through the EXACT SAME validation, revision, and mutation machinery.**

There is no "AI backdoor", "privileged bypass", or "direct document setter" anywhere in the system:

```text
User Action  ───┐
                ├─► UnifiedAuthoringSession ─► applyMutation() ─► Canonical Document
AI Intent    ───┘
```

Both actors are subject to:
1. **Schema Validation**: All mutations must conform to `CanonicalMutationSchema`.
2. **Revision Checking**: `base_revision` must strictly match the current document revision.
3. **Stable-ID Integrity**: Target scenes, layers, tracks, and clips must exist in the canonical document.
4. **Bijective Inversion**: Every forward mutation must have a deterministic inverse mutation computed prior to application.
5. **ChangeSet Generation**: All mutations produce a granular `ChangeSet` indicating affected entity IDs.

---

## 2. Priority & Concurrency Rules

1. **Optimistic Concurrency Control**:
   - Every modification specifies `base_revision`.
   - If User edits project from rev 10 to rev 11, and AI attempts an edit with `base_revision: 10`, the AI edit **fails immediately** with `REVISION_CONFLICT`.
   - The user's edit is protected against accidental overwriting.
2. **Retry Protocol**:
   - An AI agent receiving `REVISION_CONFLICT` must inspect the new revision (rev 11), re-evaluate its intent against the current canonical document, and re-submit with `base_revision: 11`.
3. **Idempotency Guarantee**:
   - If a network error causes an AI operation to be retransmitted with the same `operation_id`, the system returns the cached result without advancing revision or applying duplicate modifications.

---

## 3. Atomic Batches & Blast Radius Control

1. **Transactional Batches**:
   - When an operation requires modifying multiple layers (e.g. changing headline, sub-headline, and accent color), the operations are grouped into an atomic `MutationBatch`.
   - If any single mutation in the batch fails (e.g. target layer missing or invalid property), the **entire batch is rolled back**, leaving the document untouched.
2. **Granular Targeting**:
   - AI and User mutations must target the smallest possible scope (`layer_id` or `scene_id`).
   - Whole-scene or whole-project replacements are prohibited unless explicitly requested by the user as a destructive operation.

---

## 4. Undo and Redo Symmetry

1. **Shared History Stack**:
   - The `EditorSession` maintains a single, unified undo/redo history.
   - User actions and AI actions are recorded sequentially on the same stack.
2. **Single-Step Granularity**:
   - An AI compound command (even if comprising 5 sub-mutations) is stored as 1 undo step.
   - When the user triggers `undo()`, the entire AI command is reversed cleanly to the exact prior snapshot.
   - Triggering `redo()` restores the exact resulting snapshot.

---

## 5. Non-Destructive Template Parameter Edits

1. When a template is instantiated into a canonical document, its parameters (texts, colors, media, layout) are represented as standard canonical entities with stable IDs.
2. Subsequent adjustments (e.g. "change brand color to navy", "update headline text") must be executed as **granular mutations** (`UPDATE_STYLE`, `UPDATE_TEXT`), NOT by re-instantiating the template and destroying existing user tweaks.
