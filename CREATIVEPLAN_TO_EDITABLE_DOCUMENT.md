# CreativePlan to Editable Document (S28-R13)

**Status**: Verified Production Specification  
**Milestone**: S28-R13 — AI + Templates + Editor Unified Authoring  
**Authoritative Subsystems**: `authoring/creative-adapter.ts`, `contracts/blueprint.ts`

---

## 1. Architectural Role of CreativePlan

In previous iterations or naive designs, creative AI planning systems might treat the `CreativePlan` as a continuous runtime authority, re-compiling the entire video project whenever a downstream change is requested.

**In S28-R13, CreativePlan is strictly an ephemeral planning input, NOT a persistent authority.**

```text
┌───────────────────────────────┐
│         CreativePlan          │
│ (Transient Input Intent)      │
└───────────────┬───────────────┘
                │
                │ compileCreativePlanToCanonical()
                ▼
┌───────────────────────────────┐
│     Canonical VideoDocument   │ ◄─── Persistent Authority
│         (BlueprintV2)         │      (All subsequent edits happen here!)
└───────────────┬───────────────┘
                │
        Granular Mutations
        (AI / User / Template)
```

Once `compileCreativePlanToCanonical()` produces the initial `BlueprintV2`:
1. The `BlueprintV2` becomes the **sole persistent source of truth**.
2. The `CreativePlan` is archived as provenance metadata.
3. **No further compilation from `CreativePlan` is permitted.** All subsequent edits from either AI or human users must be applied via granular `CanonicalMutation` operations.

---

## 2. Compilation Rules & Field Mapping

`compileCreativePlanToCanonical()` executes deterministic, schema-validated mapping from `CreativePlan` structures to `BlueprintV2`:

| CreativePlan Field | Canonical BlueprintV2 Field | Normalization & Defaults |
| :--- | :--- | :--- |
| `id` / `plan_id` | `project_id` | Sanitized alphanumeric identifier. |
| `aspect_ratio` | `aspect_ratio` | Mapped to `"16:9"`, `"9:16"`, or `"1:1"`. Defaults to `"16:9"`. |
| `fps` | `fps` | Numeric framerate (e.g. 30). Defaults to 30. |
| `scenes[]` | `scenes[]` (`BlueprintScene[]`) | Each scene assigned unique, stable `scene_id` (`scene_0`, `scene_1`, etc.). |
| `scene.duration` / `duration_sec` | `scene.durationFrames` | Converted deterministically via `Math.round(durationSec * fps)`. |
| `scene.title` / `headline` | Text Layer (`BlueprintLayer`) | Converted into a text layer with stable `layer_id` (`lyr_text_...`). |
| `scene.background_color` | Scene Surface (`scene.surface`) | Converted into scene surface style with fill color. |
| `scene.image_url` / `asset_url` | Media Layer or `media_refs[]` | Converted into media layer or reference with stable `asset_id`. |
| `audio.voiceover` | Audio Track (`audio.voiceover`) | Canonical audio stream with startFrame and volume. |
| `audio.music` | Audio Track (`audio.music`) | Background music with ducking configuration. |

---

## 3. Preserving User Edits Downstream

Consider the critical scenario:
1. AI compiles initial project from `CreativePlan` (Revision 0).
2. User edits Scene 0 headline text to `"Summer Sale Special"` (Revision 1).
3. User repositions logo layer to `x: 500, y: 300` (Revision 2).
4. AI is instructed to `"make the background darker in scene 0"`.

### Forbidden Path (Naive / Competing Authority):
- AI re-compiles the entire `CreativePlan` with a darker background.
- **Catastrophic Failure**: The user's headline text edit and logo repositioning are wiped out!

### Mandated Path (S28-R13 Unified Authoring):
- AI generates an `AuthoringIntent`:
  ```typescript
  {
    type: "UPDATE_STYLE",
    target: { scene_id: "scene_0" },
    payload: { backgroundColor: "#0f172a" }
  }
  ```
- Intent is planned into a single `UPDATE_STYLE` mutation on Revision 2.
- Session applies mutation -> advances to Revision 3.
- **Result**:
  - Background color is updated to `#0f172a`.
  - User's headline `"Summer Sale Special"` is completely intact.
  - User's logo position `(500, 300)` is completely intact.
  - Zero whole-project overwrite occurs.
