# AI Mutation Model (S28-R13)

**Status**: Verified Production Specification  
**Milestone**: S28-R13 — AI + Templates + Editor Unified Authoring  
**Authoritative Subsystems**: `contracts/authoring.ts`, `authoring/intent-planner.ts`, `contracts/mutations.ts`

---

## 1. Core Principle: Intent to Typed Mutations

AI agents **never modify video blueprints directly**. Rather, AI agents operate exclusively by declaring high-level `AuthoringIntent` objects, which the pure `IntentPlanner` translates into one or more strongly-typed `CanonicalMutation` primitives:

```text
┌─────────────────────────────────┐
│       AI Agent Intent           │
│   e.g. "Move title 50px right"  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     planAuthoringIntent()       │
│  • Stable ID resolution         │
│  • Constraint validation        │
│  • Ambiguity check              │
│  • Capability verification      │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│      CanonicalMutation[]        │
│  • UPDATE_TRANSFORM             │
│  • UPDATE_TEXT                  │
│  • UPDATE_STYLE                 │
│  • REPLACE_MEDIA                │
│  • SET_TIMING                   │
└─────────────────────────────────┘
```

---

## 2. Intent Vocabulary & Translation Matrix

The pure intent planner maps the following canonical intent types to discrete mutations:

| Intent Type | Target Selector | Payload Parameters | Emitted Canonical Mutation | Inverse Mutation Support |
| :--- | :--- | :--- | :--- | :--- |
| `UPDATE_TEXT` | `{ scene_id, layer_id }` or `{ text_query }` | `{ text, fontSize, fontFamily, color }` | `UPDATE_TEXT` | Bijective text & styling restoration |
| `UPDATE_TRANSFORM` | `{ scene_id, layer_id }` | `{ x, y, scale, rotation, opacity }` | `UPDATE_TRANSFORM` | Bijective matrix/property restoration |
| `UPDATE_STYLE` | `{ scene_id, layer_id }` | `{ backgroundColor, fill, stroke, borderRadius, etc. }` | `UPDATE_STYLE` | Bijective property restoration |
| `REPLACE_MEDIA` | `{ scene_id, layer_id }` or `{ scene_id }` | `{ asset_ref, asset_id }` | `REPLACE_MEDIA` | Bijective asset URL/ref restoration |
| `UPDATE_TIMING` | `{ scene_id }` | `{ durationFrames, startFrame }` | `SET_TIMING` | Exact frame restoration |
| `COMPOUND_COMMAND` | `{ scene_id }` | Command specific (`quote_card`, `bullet_list`, `brand_theme`) | Multiple mutations bundled into atomic batch | Single-step atomic undo/redo |
| `RAW_MUTATION` | Explicit target | Typed `CanonicalMutation` | Direct passthrough after schema validation | Native bijective inverse |

---

## 3. Stable-ID Targeting Protocol

To prevent accidental modification of elements due to layout shifts or array index changes:
1. AI intents target elements using **canonical stable IDs**:
   - `scene_id`
   - `layer_id`
   - `clip_id`
   - `keyframe_id`
   - `asset_id`
2. If an intent targets an element via natural language or query selectors (e.g. `layer_name: "Header"` or `text_query: "Sale"`):
   - If **exactly 1 matching element** exists: Resolved to the target's stable ID.
   - If **0 matching elements** exist: Fails closed with diagnostic `AUTHORING_TARGET_NOT_FOUND`.
   - If **> 1 matching elements** exist: Fails closed with diagnostic `AUTHORING_TARGET_AMBIGUOUS`.
3. AI is **strictly prohibited from guessing** visual coordinates or array indices when targeting is ambiguous.

---

## 4. Unsupported Operations & Fail-Closed Guardrails

When an AI intent requests an unsupported feature or impossible rendering effect (such as "add a 3D holographic particle system" or "evaluate arbitrary TSX React hook"):
1. The authoring subsystem **fails closed**.
2. No stub or fallback TSX code is generated.
3. An `AuthoringResult` is returned with `success: false` and error code:
   ```typescript
   {
     success: false,
     error: {
       code: "UNSUPPORTED_AUTHORING_OPERATION",
       message: "Unsupported authoring operation: 'add_3d_holographic_particles'. Reason: 3D holographic particle rendering is unsupported in 2D canonical video model.",
       details: { operation: "add_3d_holographic_particles" }
     }
   }
   ```
4. The document revision remains unchanged, and zero mutations are committed.

---

## 5. Compound Operations as Single Undo Steps

Certain semantic AI actions require modifying multiple layers or properties simultaneously (for example, applying a "Quote Card" layout requires adding quote text, author text, background color, and sizing).

Under the S28-R13 model:
1. The intent planner decomposes the compound command into multiple `CanonicalMutation` objects.
2. The mutations are executed as a single atomic batch in `UnifiedAuthoringSession`.
3. In `EditorSession`, the batch is recorded as **a single HistoryEntry**:
   ```typescript
   historyEntry: {
     command_id: "batch_ai_compound_quote",
     actor: "ai",
     forward_mutations: [mutText, mutAuthor, mutStyle],
     inverse_mutations: [invStyle, invAuthor, invText],
     ...
   }
   ```
4. When the user clicks **Undo**, the entire compound operation is undone in a single step, restoring the document to its exact state before the AI action.
