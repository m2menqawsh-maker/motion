# Video Production Protocol — v4.0 (Agile Visual-First)

## Phase 1: Media Package + Preview (🛑 STOP 1)

**Step 0 (Before any phase): Check Live Alerts**
- Check for the existence of `projects/<id>/.agent_alerts.md`.
- If it exists, read the alerts and handle them before proceeding.
- If it is empty or does not exist, proceed to the next step.

### Step 1: Mandatory Audio Analysis
Once the user uploads the VO (or requests its generation):
1. Immediately run: `audio-tools-mcp:analyze_voiceover` on the file.
2. Wait for the analysis results (`04_timings.json`).

### Step 2: Fetch and Process Media
1. User uploads first → `assets/incoming/`
2. Check Cache: `common-tools-mcp:check_cache` (Fetching from the internet is forbidden if a matching processed asset exists).
3. Fetch missing assets via `media-sources-mcp` directly.
4. Processing (All-Intra for video, -16 LUFS for VO, -24 LUFS for SFX).
5. Save to Cache: `common-tools-mcp:save_to_cache`.

**Output:** Ready Media Package.
**🛑 STOP 1: Wait for user approval on the Media Package.**

---

## Phase 2: Detailed Plan + Preview (🛑 STOP 2)

**Step 0 (Before any phase): Check Live Alerts**
- Check for the existence of `projects/<id>/.agent_alerts.md`.
- If it exists, read the alerts and handle them before proceeding.
- If it is empty or does not exist, proceed to the next step.

#### ⚠️ Non-Negotiable Mandatory Rule:
**The detailed plan must be written by the Agent itself, NOT via a script.**

**Reasons:**
- Scripts do not understand the creative context of the content.
- Scripts cannot select appropriate templates based on the nature of each sentence.
- Scripts cannot bind words to motions (Gestural Sync).
- Creative generation is the Agent's job, while validation is the Scripts' job.

#### Mandatory Steps:
1. Read `references/PLAN_TEMPLATE.md` to understand the structure and rules.
2. Read `04_timings.json` for exact word-level timings.
3. Read `TEMPLATE_INDEX.md` to select appropriate templates.
4. Read `SFX_BINDING_MATRIX.md` to select appropriate sound effects.
5. Read `motion-personality.md` and `user-signature-style.md` for citations.
6. Write the plan yourself, scene by scene, shot by shot.
7. Save it to `projects/<project_id>/master_plan.md`.
8. Run: `python scripts/plan_gate.py <project_id>` for validation.
9. If validation fails, fix the plan and retry.

#### Accepted Plan Criteria:
- ✅ Every scene has a word table with exact timings.
- ✅ Every scene has ≥ 2 detailed shots.
- ✅ Every shot has: Template + Camera + Gesture + SFX + Synced Word.
- ✅ ≥ 3 different templates in the entire plan.
- ✅ ≥ 3 different SFX.
- ✅ No padding, no empty comments, no generic terms.
- ✅ `motion_taste_citation` and `treatment_citation` are present.

#### ❌ Absolute Prohibitions:
- DO NOT use `generate_plan.py` to generate the plan (it is only a structure generator).
- DO NOT use any script to write creative content.
- DO NOT add padding just to reach a specific line count.
- DO NOT use sequential line repetition (repeating the same sentence with just a changed number).
- If you run out of content, stop immediately — do not fill the void.

**Output:** `master_plan.md` fully written by the Agent.
**🛑 STOP 2: Wait for explicit user approval on the detailed plan.**

---

## Phase 3: Build + Preview + Render (🛑 STOP 3)

**Step 0 (Before any phase): Check Live Alerts**
- Check for the existence of `projects/<id>/.agent_alerts.md`.
- If it exists, read the alerts and handle them before proceeding.
- If it is empty or does not exist, proceed to the next step.

### Step 1: Scene Building & Structural Files (JSON & Code Generation)
- ⚠️ **MANDATORY BEFORE BUILD:** The agent must manually translate the text plan (`master_plan.md`) and media package into structural JSON files: `05_blueprint.json` (for scenes and timings) and `02_asset_manifest.json` (for media registry).
- Building any scene without a matching scene plan is forbidden.
- You must use approved templates from `TEMPLATE_INDEX.md` (Zero Improvisation).
- You must apply the motion personality from `motion-personality.md`.
- All media enters the build via `materialize_project.py` only (which requires the JSON files to exist first). Manual copying is forbidden.

### Step 2: Preview & Quality (Probe-QC & Studio)
- Do not open the studio before the quality check `probe_qc.py` passes successfully.
- Run Studio for preview: `python scripts/open_studio.py <project_id>` (Using npm/npx directly is forbidden).

### Step 3: Final Render
- 🛑 Rendering before preview and explicit user approval is forbidden.
- 🛑 A `.studio_approved` file must be created manually by the user after preview (programmatic or automatic creation is forbidden).
- Rendering is done via the command: `python scripts/render_project.py <project_id>`.

**Output:** The final exported video.
**🛑 STOP 3: Final stop for delivery.**