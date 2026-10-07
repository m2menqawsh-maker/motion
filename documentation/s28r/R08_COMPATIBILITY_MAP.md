# S28-R08 Compatibility Map & Subsystem Interoperability

## 1. Overview

This document defines the interoperability and backward compatibility matrix between S28 milestones (R02 through R08) and sets the technical handover baseline for S28-R09 (Remotion Renderer Adapter).

---

## 2. Milestone Integration Matrix

| Milestone | Subsystem | Interaction with S28-R08 Renderer Abstraction | Compatibility Status |
| :--- | :--- | :--- | :--- |
| **S28-R02** | Canonical Video Document (`BlueprintV2`, `Normalization`) | `RenderRequest` wraps `BlueprintV2` as read-only canonical input. Document schemas contain zero renderer-specific metadata. | `100% PASS` |
| **S28-R03** | Pure Deterministic Evaluator (`evaluateVideoAtFrame`) | Headless renderers and preview adapters use `evaluateVideoAtFrame` for exact frame mathematics. | `100% PASS` |
| **S28-R04** | Mutation Core & EditorSession (`applyMutation`, ChangeSets) | Mutations generate invalidated ChangeSets; editor sessions request targeted frame/sequence renders without coupling to concrete engines. | `100% PASS` |
| **S28-R05** | TemplateSpec & Instantiator | `deriveRequiredCapabilities()` inspects template classifications (`NATIVE`, `ENGINE_BACKED`, `HYBRID`) to derive exact renderer capabilities (`map`, `3d`, `particles`, `webgl`). | `100% PASS` |
| **S28-R06** | Browser Live Preview Runtime | Bridged as `BrowserPreviewAdapter` (`frame_rendering`, `live_preview`). Does not usurp renderer authority. | `100% PASS` |
| **S28-R07** | Audio Preview & Waveform | Audio plan capabilities (`audio_voiceover`, `audio_music`, `audio_sfx`, `audio_ducking`, `audio_mixing`, `audio_timing`) integrated into renderer capability requirements. | `100% PASS` |
| **S28-R08** | Renderer Registry & Engine Decoupling | Introduces `RendererRegistry`, `RendererAdapter`, `RendererCapabilities`, and structured error taxonomy. | `CURRENT (PASS)` |
| **S28-R09** | Full Remotion Renderer Adapter | Replaces `RemotionRendererAdapterStub` with concrete implementation executing `@remotion/bundler` and `@remotion/renderer`. | `HANDOVER TARGET` |

---

## 3. Remotion Evolution Map (R08 $\to$ R09)

In S28-R08, Remotion is formally placed behind the `RendererAdapter` boundary:

```text
S28-R08 (Current Stub):
┌────────────────────────────────────────────────────────┐
│             createRemotionAdapterStub()                │
│  • Declares 18 standard Remotion capabilities          │
│  • Matches requests requiring standard video/audio     │
│  • Rejects map / 3d / particles (requires extensions)  │
│  • Throws structured error on renderFrame/exportVideo  │
└────────────────────────────────────────────────────────┘

S28-R09 (Target Implementation):
┌────────────────────────────────────────────────────────┐
│              RemotionRendererAdapter                   │
│  • Same declared capabilities & contract               │
│  • Implements exportVideo via Remotion CLI/Bundler     │
│  • Translates Canonical BlueprintV2 to Remotion Root   │
│  • Executes within clean-video-builder container       │
└────────────────────────────────────────────────────────┘
```
