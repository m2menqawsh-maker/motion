# Remotion Video Production Guide — Zero-Build Master Engine

This document is the canonical reference for the **Zero-Build Master Engine** architecture used in this video workspace. It replaces all legacy "actor-based" or manual React coding workflows.

**Use this as your primary system prompt when dealing with the Remotion engine or generating video plans.**

---

## 1. Core Philosophy: Zero React Coding

In the past, generating videos meant asking an AI to write `.tsx` files containing animations, springs, and React components. This proved fragile and error-prone. 

The new architecture relies on the **Zero-Build Master Engine**:
1. **The Engine is Pre-built:** The Remotion app (`remotion-app/`) is a fully functional, dynamic rendering engine.
2. **Data-Driven:** The engine does not require custom React code to render a video. Instead, it dynamically reads a standard JSON file (`05_blueprint.json`).
3. **Your Role as an Agent:** You are **strictly forbidden** from writing or editing `.tsx` files for video generation. Your sole job is to act as a Director: outputting a pristine `05_blueprint.json` that the Master Engine will interpret.

---

## 2. Architecture: The Unified Template System

Instead of a single flat composition, the engine uses modular, pre-registered components. 

### Category Breakdown
Components are categorized into three distinct layers, stored in `remotion-app/src/templates/`:
- **`scenes/`**: Full-screen layouts (e.g., a SaaS dashboard, a split-screen interview, a 3D card layout). These dictate the primary visual structure.
- **`elements/`**: Smaller, reusable primitives (e.g., floating badges, cursors, animated text blocks, progress bars, UI popups). These are injected into scenes or overlaid on top of them.
- **`effects/`**: Transitions (Wipe, Fade, Slide) and background shaders (Gradients, Matrix, Noise).

### The Registry (`template-registry.tsx`)
The engine knows about these templates via a single source of truth: `registry/template-registry.tsx`. 
All 169+ templates (including Native Remotion, `remotion-ui`, and `remotion-bits`) are lazily loaded and registered here with a unique `id`.

When the Master Engine reads `05_blueprint.json`, it looks up the template `id` in this registry and dynamically renders the mapped component.

---

## 3. The Universal Component Contract (Wrappers)

To allow the Master Engine to seamlessly mix and match templates from different libraries (e.g., `remotion-ui` vs Aceternity), every template in the registry is a **Wrapper**. 

Wrappers act as translation layers. They accept a unified API and map it to the underlying component's specific props. 

Every template accepts exactly two main property groups in the blueprint:
1. **`surface`**: Controls colors, themes, sizing, layout, and visual styling.
2. **`content`**: Controls the actual text, images, data, or arrays passed to the component.

*Example of a Blueprint node targeting a wrapper:*
```json
{
  "id": "ui-card-01",
  "template": "elements/ui/card",
  "props": {
    "surface": {
      "theme": "dark",
      "accentColor": "#FF6B00",
      "scale": 1.2
    },
    "content": {
      "title": "Zero-Build Engine",
      "subtitle": "No React Code Required",
      "images": ["/assets/ready/logo.png"]
    }
  },
  "start_sec": 2.5,
  "end_sec": 8.0
}
```

---

## 4. The `05_blueprint.json` Specification

As the AI agent, your final output for rendering is the Blueprint. The Blueprint is a second-by-second timeline.

### Blueprint Structure
- **`metadata`**: Video resolution, FPS, total duration, and global settings.
- **`assets`**: References to verified local paths (from `02_asset_manifest.json`) using standard aliases (e.g., `${ASSETS}/ready/...`).
- **`tracks`**:
  - `video`: An array of elements and scenes. Each block defines what template to use, when it starts/ends, and what props to pass.
  - `audio`: An array of voiceover clips and sound effects (`sfx`). Each SFX must include `asset`, `at_ms`, `volume_db`, and `tone`.

### Blueprint Rules
1. **Exhaustive Props:** When defining `surface` and `content`, do not assume default fallbacks will look good. Provide explicit colors, text arrays, and layout constraints suitable for a 9:16 vertical canvas (or 16:9 if specified).
2. **Frame-Perfect Audio Sync:** Visual motions (Pop, Zoom, Slide) must hit exactly (in milliseconds) with the spoken word in the VO timestamps.
3. **No Padding/Fake Data:** Every asset referenced in the blueprint MUST exist in the `ready/` folder.

---

## 5. Animation & Motion Personality

Because you cannot write `spring()` physics yourself, you control motion via the Blueprint's `motion` block for each element. The Master Engine applies these physics globally.

```json
"motion": {
  "enter": "slide-up",
  "exit": "fade-out",
  "easing": "cinematic",
  "duration_ms": 450
}
```

### The 4 Motion Tastes (Moods)
When generating a plan, you must assign a motion personality that dictates the spring physics applied by the engine:
1. **Cinematic**: Smooth, deep, gradual eases (350-600ms, 0% overshoot). Best for corporate, luxury, medical.
2. **Energetic**: Snappy, punchy, fast (100-250ms, 15-30% overshoot). Best for Gen-Z social, ads.
3. **Playful**: Bouncy, exaggerated (150-300ms, 10-20% overshoot). Best for casual, kids.
4. **Technical**: Linear, precise, no-nonsense (200-400ms, 0-3% overshoot). Best for SaaS, coding, data.

---

## 6. Rendering Workflow

You DO NOT run `npm run` or `npx remotion` directly. You use the Python orchestrator scripts:

1. **Materialize Media:** `python scripts/materialize_project.py projects/<id>` (Moves assets to public directory).
2. **Open Studio (Preview):** `python scripts/open_studio.py <project_id>` (Opens local server for user preview).
3. **Render:** `python scripts/render_project.py <project_id>` (Generates final MP4 after user approves).

*Note: Rendering requires the presence of a manual `.studio_approved` file created by the user.*

---

## 7. Anti-Patterns (What NOT to Do)

| Don't | Do instead |
|-------|------------|
| **Write `.tsx` files** | Generate a `05_blueprint.json` file. |
| **Write custom `generate_react.py` scripts** | Rely on the Master Engine and pre-registered templates. |
| **Use hardcoded `npm run` commands** | Use `scripts/open_studio.py` and `scripts/render_project.py`. |
| **Use manual paths to the `remotion-app/` folder** | Route all media through `materialize_project.py`. |
| **Skip the `surface` and `content` wrapper logic** | Ensure every component uses the universal API in the blueprint. |

---
*Generated by AI Agent. Updated for v4.0 Zero-Build Architecture.*
