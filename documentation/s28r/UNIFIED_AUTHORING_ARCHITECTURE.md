# Unified Authoring Architecture (S28-R13)

**Status**: Verified Production Specification  
**Milestone**: S28-R13 — AI + Templates + Editor Unified Authoring  
**Authoritative Subsystems**: `contracts/authoring.ts`, `authoring/unified-authoring-session.ts`, `authoring/intent-planner.ts`, `contracts/editor-session.ts`, `contracts/mutations.ts`

---

## 1. Executive Architectural Principle

In the Unified Video Authoring Architecture, **all authors—AI agents, human users, and procedural templates—are subordinated to the exact same mutation pipeline modifying the single canonical truth**:

```text
               ┌──────────────────────┐
               │    CreativePlan      │
               │  (Transient Intent)  │
               └──────────┬───────────┘
                          │ compileCreativePlanToCanonical()
                          ▼
               ┌──────────────────────┐   TemplateSpec
               │ Canonical Blueprint  │ ◄───────┴────────
               │ (Persistent Truth)   │   instantiateTemplate()
               └──────────┬───────────┘
                          │
     ┌────────────────────┼────────────────────┐
     │                    │                    │
     ▼                    ▼                    ▼
┌──────────────┐   ┌──────────────┐   ┌────────────────┐
│   AI Agent   │   │  Human User  │   │   Templates    │
│  (Intent)    │   │   (Direct)   │   │  (Parameters)  │
└──────┬───────┘   └──────┬───────┘   └───────┬────────┘
       │                  │                   │
       ▼                  │                   ▼
┌──────────────┐          │            ┌───────────────┐
│IntentPlanner │          │            │IntentPlanner /│
│ (authoring)  │          │            │ Param Adapter │
└──────┬───────┘          │            └──────┬────────┘
       │                  │                   │
       └──────────────────┼───────────────────┘
                          ▼
            CanonicalMutation[] (Typed)
                          │
                          ▼
           ┌─────────────────────────────┐
           │   UnifiedAuthoringSession   │
           │  • Revision validation      │
           │  • Idempotency cache        │
           │  • Atomic compound batches  │
           │  • EditorSession (Bijective)│
           │  • Provenance tracking      │
           └──────────────┬──────────────┘
                          │
       ┌──────────────────┴──────────────────┐
       ▼                                     ▼
┌──────────────┐                      ┌──────────────┐
│  ChangeSet   │                      │  Canonical   │
│  (Granular)  │                      │VideoDocument │
└──────┬───────┘                      └──────┬───────┘
       │                                     │
       ▼                                     ▼
┌──────────────┐                      ┌──────────────┐
│PreviewRuntime│                      │RenderPlanner │
│(Proxy Inval) │                      │(Multi-Engine)│
└──────────────┘                      └──────────────┘
```

### Absolute Invariants:
1. **Single Persistent Truth**: `Canonical VideoDocument` (`BlueprintV2`) is the sole persistent authority. There is no separate "AI document", "Editor document", "Template document", or "Render document".
2. **Zero Bypasses**: Neither AI nor Templates are permitted to directly mutate `BlueprintV2` objects in-place or rewrite entire documents wholesale during authoring.
3. **Engine Neutrality**: The authoring layer and AI planning pipeline have zero imports from React, Remotion, Canvas adapters, WebGL, or FFmpeg.
4. **AI Cannot Emit Renderer Code**: AI authoring intents are strictly mapped to typed canonical mutations (`UPDATE_TEXT`, `UPDATE_STYLE`, `UPDATE_TRANSFORM`, `REPLACE_MEDIA`, `INSERT_LAYER`, `DELETE_LAYER`, etc.). AI is architecturally prohibited from generating TSX, JSX, Remotion Compositions, or FFmpeg filtergraphs in the normal authoring loop.

---

## 2. Layered Responsibilities

| Subsystem | Layer | Primary Responsibility | Architectural Bounds |
| :--- | :--- | :--- | :--- |
| **`contracts/authoring.ts`** | Contract | Engine-neutral schemas: `AuthoringRequest`, `AuthoringIntent`, `AuthoringOperation`, `AuthoringResult`, `AuthoringProvenance`. | Zero runtime dependencies; 100% Zod validated. |
| **`authoring/intent-planner.ts`** | Translation | Pure translation function `planAuthoringIntent` mapping high-level intents into typed `CanonicalMutation[]`. | Pure logic; target resolution by stable IDs (`scene_id`, `layer_id`, `clip_id`); ambiguous queries fail closed. |
| **`authoring/unified-authoring-session.ts`** | Orchestration | Stateful session wrapper managing base revision concurrency, idempotency deduplication, atomic compound commands, provenance auditing, and preview runtime synchronization. | Wraps `EditorSession`; produces `ChangeSet` on each execution. |
| **`contracts/editor-session.ts`** | Mutation Authority | Authoritative execution of `applyMutation` and `applyBatch`, maintaining bijective undo/redo stacks and computing exact inverse mutations. | Enforces snapshot immutability, entity existence, and revision monotonicity. |
| **`authoring/creative-adapter.ts`** | Ingestion | Deterministic compiler transforming raw `CreativePlan` inputs into baseline `BlueprintV2`. | One-way compilation; after compilation, `CreativePlan` retains zero persistent authority. |
| **`authoring/template-adapter.ts`** | Ingestion | Instantiates `TemplateSpec` into canonical document or sub-document fragments. | Post-instantiation, template structures are fully open to granular mutations by AI or User. |

---

## 3. Concurrency, Revision Checks & Fail-Closed Guards

To eliminate silent race conditions between AI agents and human users:
1. Every `AuthoringRequest` must declare `base_revision: number`.
2. `UnifiedAuthoringSession` verifies:
   ```typescript
   if (request.base_revision !== this.getRevision()) {
     return {
       success: false,
       error: {
         code: "REVISION_CONFLICT",
         message: `Revision conflict: request based on revision ${request.base_revision}, but current revision is ${this.getRevision()}`
       }
     };
   }
   ```
3. If an AI agent plans a mutation based on revision 10, but a user makes an edit that advances the project to revision 11, the AI request **fails closed** with `REVISION_CONFLICT`. No silent overwrite occurs; the user's edit remains intact.

---

## 4. Idempotency & Operation Deduplication

Network retries or repeated AI dispatch are protected via deterministic idempotency keys:
1. Every operation includes an `operation_id` or `request_id`.
2. `UnifiedAuthoringSession` stores successful execution results in an LRU operation cache.
3. When an identical `request_id` or `operation_id` is re-submitted:
   - The session verifies the operation was already executed.
   - It returns the cached `AuthoringResult` with `idempotent: true`.
   - The underlying mutation is not re-applied, and the document revision is not advanced twice.

---

## 5. Preview & Render Independence

After mutations are committed by `UnifiedAuthoringSession`:
1. **ChangeSet Generation**: The session receives the exact `ChangeSet` (affected scene IDs, layer IDs, clip IDs, audio tracks).
2. **Selective Preview Invalidation**: If connected to `BrowserPreviewRuntime`, the session triggers `preview.applyChangeSet(changeset)`:
   - For `LIVE_NATIVE` scenes, the visual canvas/DOM updates instantly in sub-millisecond time.
   - For scenes with active proxy video artifacts, the proxy cache selectively invalidates only the affected scenes/layers, leaving unedited scenes cached.
3. **RenderPlanner Dispatch**: The authoring layer does not select render engines. The mutated `Canonical VideoDocument` is passed to `RenderPlanner.plan()`, which inspects required scene capabilities and dispatches to Canvas, Remotion, or Master Compositor based strictly on capability matching.
