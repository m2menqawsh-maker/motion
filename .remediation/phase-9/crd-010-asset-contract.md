# CRD-010 Asset Lifecycle Contract

## Flaw Identified
Previously, blueprints defined explicit physical paths for assets (e.g., `C:/video/clean-video-workspace/assets/ready/bg_music.mp3`). This created fragile coupling between the generation environment (the Agent's workspace) and the runtime rendering environment, leading to path traversal risks and broken builds when transitioning between environments (e.g., local to Docker).

## Canonical Contract
All orchestration stages must now adhere to the **Logical Asset Contract**:

1. **Generation (Blueprint):**
   The Blueprint (`05_blueprint.json`) must ONLY reference assets by their **Logical Asset ID** (e.g., `scene_1_video`, `bg_music_1`). These IDs must correspond precisely to the `asset_id` fields defined in `02_asset_manifest.json`.

2. **Materialization (Gatekeeper):**
   The `scripts/generators/materialize_project.py` gate strictly extracts these Logical Asset IDs, verifies their existence in the manifest, and securely transfers the physical files to the project's public media folder. It generates a deterministic lookup map (`media_map.json`).
   - *Rule:* Unknown Logical IDs cause a hard failure.
   - *Rule:* Missing physical files cause a hard failure.
   - *Rule:* Path traversal payloads (e.g., `../`) are neutralized.

3. **Orchestration (Runner):**
   The runner (`scripts/render_project.py`) automatically bundles `media_map.json` into the engine payload (`render_props.json`).

4. **Runtime Resolution (Engine):**
   The Remotion runtime (`remotion-app/src/merge.ts`) intercepts the Logical IDs in `scene.media_refs` and exchanges them for the physical runtime paths via the `media_map.json` dictionary *before* rendering.

## Status
**Enforced & Verified.** Fully backed by regression tests in `tests/test_asset_resolution.py`.
