# S28-R07B Milestone Closure Report: Preview Fidelity, Cache & Proxy System

**Milestone**: S28-R07B (Preview Fidelity, Cache & Proxy System)  
**Status**: **PASS**  
**Git HEAD**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Audited Timestamp**: `2026-10-06T22:45:00+03:00`  

---

## 1. Roadmap Alignment & Historical Context

```text
Original roadmap R07 scope:
Preview Fidelity, Cache & Proxy System

Historical S28-R07 implementation:
Audio Preview, Synchronization & Waveform

S28-R07B:
closes the missing original R07 roadmap scope

No milestone renumbering was performed.
```

### Context & Justification:
During earlier development, milestone `S28-R07` was successfully executed to build the complete `AudioPreviewRuntime`, Web Audio synchronization, waveform extraction, and audio ducking system. However, the original roadmap scope for `R07` ("Preview Fidelity, Cache & Proxy System") remained unclosed while downstream milestones `S28-R08` (Renderer Registry), `S28-R09` (Remotion Adapter), and `S28-R10` (Canvas Adapter) proceeded.

Milestone **S28-R07B** is the dedicated corrective closure milestone. It builds the complete Preview Fidelity, Proxy, and Cache layer without renumbering R08–R10, without modifying or deleting `AudioPreviewRuntime`, and by directly consuming the multi-engine infrastructure established in R08–R10.

---

## 2. Core Architectural Pillars Built

### 2.1 Preview Capability & Fidelity Model
Located in [`contracts/preview-fidelity.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-fidelity.ts):
- Engine-neutral capability resolution function: `resolvePreviewFidelity(document, options)`.
- Three formal preview classifications:
  1. **`LIVE_NATIVE`**: Direct real-time rendering in browser DOM/Canvas (text, basic shapes, static images, groups, keyframes, linear transitions, native audio). Quality: `full`.
  2. **`APPROXIMATE_PREVIEW`**: Deterministic, lightweight visual approximation for features too expensive for full-fidelity 60 fps scrubbing (complex transitions like zoom/wipe/iris approximated as crossfade; visual blur effects). Explicitly tagged with `previewQuality: "approximate"` and diagnostic reasons.
  3. **`PROXY_RENDER_REQUIRED`**: Unrenderable features (engine-backed templates like `rui-map-flight`, 3D scenes, particle systems, custom shaders, unsupported video compositing). Fail-closed; triggers an asynchronous proxy request rather than silent degraded fallback.

### 2.2 Preview Proxy Contracts & Quality Policies
Located in [`contracts/preview-proxy.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/preview-proxy.ts):
- `PreviewProxyRequest`: Immutable request containing `projectId`, `canonicalRevision`, `sceneId`, `layerId`, `timeRange`, `requiredCapabilities`, `width`, `height`, `fps`, `quality`, and `format`.
- `PreviewProxyArtifact`: Immutable rendered artifact with unique ID, deterministic cache key, dependency metadata, byte length, and URI/buffer.
- Configurable quality policies: `low` (360p @ 15fps), `balanced` (720p @ 30fps), and `high` (1080p @ 30fps) with aspect-ratio-preserving dimension calculation.

### 2.3 Deterministic Proxy Cache & Selective Invalidation
Located in [`preview/proxy/proxy-cache.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-cache.ts):
- `PreviewProxyCache`: Bounded in-memory store enforcing strict entry (`maxEntries`) and byte (`maxSizeBytes`) limits with LRU eviction.
- Deterministic key generation: Combines project identity, canonical revision, SHA-256 content fingerprint, entity IDs, time range, sorted required capabilities, dimensions, and quality profile.
- Fine-grained invalidation: Directly binds to S28-R04 [`ChangeSet`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/mutations.ts). Modifying text in Scene A evicts only Scene A proxies; proxies for Scene B remain active and untouched. Supports invalidation by scene ID, layer ID, asset ID, and temporal range.

### 2.4 Asynchronous Background Proxy Coordinator
Located in [`preview/proxy/proxy-coordinator.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-coordinator.ts):
- Manages proxy generation lifecycle (`queued` $\to$ `running` $\to$ `ready` / `failed` / `cancelled` / `stale`).
- Selects rendering adapters strictly through `RendererRegistry` / `CANONICAL_RENDERER_REGISTRY` based on capability matching. Zero hardcoded engine branching.
- Fail-closed error handling when no compatible engine exists for engine-backed fragments.
- **Stale Result Protection**: Rejects and discards proxy renders if the document revision advanced while the job was in flight. Older revision proxies can never overwrite newer document states.

### 2.5 Live BrowserPreviewRuntime Integration
Located in [`preview/preview-runtime.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/preview-runtime.ts) and [`preview/visual-frame.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/visual-frame.ts):
- `BrowserPreviewRuntime` remains the sole playhead clock and live preview authority.
- Seamless proxy replacement: Renders diagnostic placeholder (`visual_type = "proxy_placeholder"`) while background job runs, and cleanly swaps in rendered proxy visual node (`visual_type = "proxy_layer"`) once ready, without pausing playback or reloading the project.
- Preserves audio synchronization: Web Audio playback via [`AudioPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/audio/audio-preview-runtime.ts) remains lock-step synchronized across all proxy generation and live swaps.

---

## 3. Real Performance Baseline Measurements

Benchmarks executed on host Linux system (Intel/x86_64 architecture):

| Benchmark Operation | Measured Real Latency / Metric | Operations / Throughput |
| :--- | :--- | :--- |
| **Capability Resolution** (`resolvePreviewFidelity`) | **`0.0116 ms`** ($11.6\ \mu\text{s}$) | $\approx 86,200\text{ ops/sec}$ |
| **Proxy Cache Lookup (Hit)** | **`0.00047 ms`** ($0.47\ \mu\text{s}$) | $\approx 2,120,000\text{ ops/sec}$ |
| **Proxy Cache Lookup (Miss)** | **`0.00010 ms`** ($0.10\ \mu\text{s}$) | $\approx 10,000,000\text{ ops/sec}$ |
| **Small Proxy Generation Dispatch** (Adapter $\to$ Artifact) | **`2.895 ms`** | Real dispatch & frame encode |
| **ChangeSet Selective Invalidation** | **`0.314 ms`** ($314\ \mu\text{s}$) | Granular dependency pruning |
| **Live Proxy Replacement in Runtime** | **`0.360 ms`** ($360\ \mu\text{s}$) | Rebuilds visual frame with proxy |
| **Memory Footprint (100 Cached Proxy Entries)** | **`~397.0 KB`** | Highly bounded in-memory storage |

---

## 4. Verification & Test Suite Summary

### 4.1 New S28-R07B Test Suites
All 4 new test suites pass with 100% success rate (22/22 tests):
- `tests/remotion/s28_r07b_preview_fidelity_and_proxy.test.ts` (13 tests PASS)
  - `LIVE_NATIVE` classification for basic shapes, text, images, groups
  - `APPROXIMATE_PREVIEW` classification for complex zoom/wipe/iris transitions
  - `PROXY_RENDER_REQUIRED` classification for engine-backed templates & shaders
  - Deterministic proxy request generation
  - Multi-engine renderer selection via `RendererRegistry`
  - Bounded proxy cache hit, miss, and LRU eviction
  - ChangeSet selective invalidation by scene and layer
  - Asset-specific proxy invalidation
  - Stale revision result rejection
  - Proxy replacement in visual frame
  - Failed job diagnostics & cancelled job lifecycle
  - Rejection when no compatible renderer is registered
- `tests/remotion/s28_r07b_critical_integration.test.ts` (1 test PASS)
  - End-to-end integration: Mixed document with native + proxy fragment, live playback, background generation via `RendererRegistry`, seamless swap, user mutation, selective invalidation, stale rejection, undo, redo, and uninterrupted synchronized audio playback.
- `tests/architecture/test_s28_r07b_architecture_guards.test.ts` (7 tests PASS)
  - Canonical contracts contain zero concrete renderer imports
  - `BrowserPreviewRuntime` contains zero hardcoded Remotion or Canvas imports
  - `PreviewProxyCache` contains zero canonical mutation methods
  - Proxy artifacts do not assert canonical authority
  - Preview jobs do not directly mutate document state
  - Audio preview timeline independence is preserved
  - No milestone renumbering was performed
- `tests/remotion/s28_r07b_performance.test.ts` (1 test PASS)
  - Automated measurement of resolution latency, cache lookup, dispatch, invalidation, and memory footprint.

### 4.2 Full Regression Verification
Zero regressions across the existing test suite:
- `s28_r06_preview_runtime.test.ts`: **22/22 PASS**
- `s28_r07_audio_preview.test.ts`: **21/21 PASS**
- `s28_r08_renderer_registry.test.ts`: **13/13 PASS**
- `s28_r09_remotion_adapter.test.ts`: **17/17 PASS**
- `s28_r10_canvas_adapter.test.ts`: **18/18 PASS**
- **Total Milestone Tests Passing**: **113/113 PASS**

---

## 5. File Inventory

### 5.1 Newly Created Files
- `contracts/preview-fidelity.ts`: Engine-neutral preview capability contracts and evaluation logic.
- `contracts/preview-proxy.ts`: Proxy request, artifact, and quality policy contracts.
- `preview/proxy/proxy-cache.ts`: Bounded LRU proxy cache with selective ChangeSet invalidation.
- `preview/proxy/proxy-coordinator.ts`: In-process async background proxy job coordinator.
- `preview/proxy/index.ts`: Proxy subsystem barrel export.
- `tests/remotion/s28_r07b_preview_fidelity_and_proxy.test.ts`: Comprehensive unit tests.
- `tests/remotion/s28_r07b_critical_integration.test.ts`: End-to-end integration test.
- `tests/architecture/test_s28_r07b_architecture_guards.test.ts`: Structural architectural guards.
- `tests/remotion/s28_r07b_performance.test.ts`: Real performance benchmark suite.
- `PREVIEW_FIDELITY_MODEL.md`: Fidelity taxonomy and classification specification.
- `PREVIEW_PROXY_ARCHITECTURE.md`: Subsystem pipeline and lifecycle specification.
- `PREVIEW_CACHE_INVALIDATION.md`: Cache keys, dependency tracking, and stale protection specification.
- `R07B_COMPATIBILITY_MAP.md`: Subsystem integration and multi-milestone compatibility map.
- `evidence/S28-R07B_REPORT.md`: This milestone closure report.

### 5.2 Modified Files
- `contracts/index.ts`: Re-exported preview fidelity and proxy contracts.
- `preview/types.ts`: Added fidelity metadata, proxy artifact IDs, and proxy runtime events.
- `preview/capabilities.ts`: Re-exported fidelity resolution module.
- `preview/visual-frame.ts`: Implemented proxy visual node rendering, placeholders, and approximations.
- `preview/preview-runtime.ts`: Integrated active proxy storage, coordinator attachment, and selective invalidation.
- `preview/index.ts`: Re-exported proxy subsystem and types.
- `AUTHORITY_MATRIX.md`: Updated global authority matrix with Preview Fidelity and Proxy Subsystem.

---

## 6. Conclusion & Next Milestone

Milestone **S28-R07B** is completely verified and closed with zero architectural violations and zero regressions.

**Recommended Next Official Milestone**:
`S28-R11 — Master Compositor & Output Normalization`
