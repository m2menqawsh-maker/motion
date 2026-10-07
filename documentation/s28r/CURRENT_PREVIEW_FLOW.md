# Current Preview Flow: Reality Audit & Editor Analysis

**Status**: Verified Reality Specification  
**Milestone**: S28-R01  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  

---

## 1. What Does "Preview" Mean Today?

In the current video system, **"Preview" refers strictly to Human Review Evidence and Headless Verification**, **NOT an interactive editor preview canvas**.

There are currently **two active preview modalities** and **zero live editor preview capabilities**:
1. **Headless Probe Frame & Contact Sheet Preview**: Non-interactive static image artifacts rendered via `npx remotion still` by `scripts/gates/probe_qc.py`.
2. **Remotion Studio Web Preview**: Standalone Webpack dev server launched on `http://localhost:3000` via `scripts/open_studio.py` which allows browser-based scrubbing of the full Remotion component tree.
3. **Live In-Editor Canvas**: **`NOT_IMPLEMENTED`**. There is currently no web player, embedded preview component, or reactive canvas runtime allowing live property editing, timeline dragging, or instantaneous state updates.

---

## 2. Preview Modalities Matrix

| Evaluation Dimension | 1. Remotion Studio Web Preview | 2. Probe Stills & Contact Sheet | 3. Rendered Low-Res Preview | 4. Embedded Remotion Player | 5. Live Editor Canvas |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Current Status** | **ACTIVE / PRODUCTION** | **ACTIVE / PRODUCTION** | **NOT_IMPLEMENTED** | **NOT_IMPLEMENTED** (`@remotion/player` = 0 imports) | **NOT_IMPLEMENTED** |
| **Entrypoint** | `scripts/open_studio.py` | `scripts/gates/probe_qc.py` | N/A | N/A | Target for S28-R |
| **Input Consumed** | `render_props.json` (`--props`) | `render_props.json` (`--props`) | N/A | N/A | `VideoDocument` / Canvas State |
| **Same Truth as Final Render?** | **YES** (`build_render_input()`) | **YES** (`build_render_input()`) | N/A | N/A | Target: Canonical Contract |
| **Requires Render Job?** | NO (runs dev server) | YES (runs `remotion still` CLI) | N/A | N/A | NO (Direct Client Canvas) |
| **Can Update Interactively?** | NO (requires file reload / Webpack HMR) | NO (static files on disk) | N/A | N/A | Target: YES (< 16ms) |
| **Can Seek / Scrub?** | YES (via Remotion Studio UI) | NO (discrete sampled frames) | N/A | N/A | Target: YES |
| **Can Change Props Live?** | NO (props baked in `render_props.json`) | NO (static render) | N/A | N/A | Target: YES |
| **Executes Full Remotion?** | **YES** (full React / Webpack) | **YES** (headless Chrome shell) | N/A | N/A | Target: NO (Isolated Renderer) |
| **Purpose** | Human QA visual inspection | Gate qualification & audit seal | N/A | N/A | Real-time user video creation |
| **Mechanical Guard** | Requires `.studio_unlocked` | Generates `.studio_unlocked` | N/A | N/A | None |

---

## 3. Detailed Walkthrough of Active Paths

### Path A: Remotion Studio Preview (`scripts/open_studio.py`)
1. **Mechanical Preflight**: Checks for `projects/<id>/.studio_unlocked`. If probe QC has not succeeded, access is blocked.
2. **Hash Integrity Check**: Compares SHA-256 of `05_blueprint.json` against the recorded hash in `.pipeline_state.json`. If any manual JSON edits occurred without running probe QC, access is blocked.
3. **Render Input Assembly**: Invokes `build_render_input()` to ensure `render_props.json` exists and is up to date.
4. **Execution**:
   - **Local**: `npx remotion studio --props <path_to_render_props.json>` in `remotion-app/`.
   - **Docker**: Launches container `clean-video-builder` binding host port 3000 to container port 3000.
5. **Consumption**: Reviewer opens `http://localhost:3000`, plays the video, inspects individual scenes, and manually creates `.studio_approved` to unblock final rendering.

### Path B: Headless Probe Preview (`scripts/gates/probe_qc.py`)
1. **Sampling Plan**: `derive_probe_frame_plan()` deterministically calculates critical frame numbers:
   - Scene start, middle, and end frames.
   - Transition pre, boundary, and post frames.
2. **Still Rendering**: Runs `npx remotion still src/index.ts BlueprintVideo probe_XX_fYY.png --frame=N --props=...` sequentially or concurrently.
3. **Contact Sheet Synthesis**: Synthesizes a composite grid image (`contact_sheet.png`) containing all sampled frames.
4. **Evidence Hash & Seal**: Computes cryptographic checksums of each frame and the contact sheet, writing signed `probe_qc_report.json` and `.seal`.
5. **Unlock**: If no execution or content failures occurred, writes `.studio_unlocked`.

---

## 4. Architectural Impediments to Live Editor Preview

The following architectural characteristics of the current preview model currently **prevent** live interactive editing:

1. **Heavyweight Process Boundary**: Previewing requires launching a Node.js CLI process (`remotion studio`), which compiles Webpack bundles in several seconds. It cannot be embedded directly in a fast client canvas.
2. **Fail-Closed Mechanical Locks**: The system enforces that `probe_qc` must run and pass before studio can open. In a live editor, the user needs to preview draft, incomplete, or experimental edits immediately without running an end-to-end QC probe suite.
3. **Static File Baking (`render_props.json`)**: Studio loads props via `--props <file>`. Dynamic state changes made by an editor or AI cannot be injected into the running preview without rewriting disk files and triggering a Webpack rebuild.
4. **Zero Client Player Abstraction**: The codebase currently has **zero usages of `@remotion/player`**. There is no React component library integrating player playback controls, playback timeline scrubbing, or event listeners into the application UI.

These impediments form the primary motivation for **S28-R**'s upcoming Live Editor Core and Renderer Abstraction phases.
