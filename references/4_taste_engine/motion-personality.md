> [!NOTE]
> **Source of Truth Hierarchy:**
> This is a Reference Document (Level 5).
> Current Architectural Authority: `ARCHITECTURE_TRUTH.md`
> Agent Instructions Authority: `.agents/AGENTS.md`
> Do not use this document to bypass official pipeline gates or engine boundaries.

# Motion Personality

## Four Archetypes

### Playful

| Parameter | Value |
|-----------|-------|
| Duration | 150-300ms |
| Easing | ease-out-back / bouncy springs |
| Overshoot | 10-20% |
| Paths | Arcs and curves, never straight |
| Squash-stretch | Yes, on impacts |

Signature: bounce settle, squash-stretch on press, rotation wobble, bright color pops, varied stagger timing.
Use for: children's apps, casual games, social media, celebrations, onboarding, creative tools.

### Premium / Luxury

| Parameter | Value |
|-----------|-------|
| Duration | 350-600ms |
| Easing | cubic-bezier(0.4, 0, 0.2, 1) |
| Overshoot | 0% |
| Paths | Smooth curves, subtle parallax |
| Squash-stretch | Never |

Signature: slow fades, subtle scale (98%→100%), generous pauses, minimal properties (opacity+one), ultra-smooth.
Use for: fashion, finance, luxury brands, premium SaaS, portfolios, editorial.

### Corporate / Professional

| Parameter | Value |
|-----------|-------|
| Duration | 200-400ms |
| Easing | cubic-bezier(0.2, 0, 0, 1) |
| Overshoot | 0-3% |
| Paths | Mostly straight, small arcs for emphasis |
| Squash-stretch | No |

Signature: consistent timing, clear state transitions, functional motion, predictable patterns, uniform stagger.
Use for: enterprise, dashboards, business tools, admin, healthcare, banking.

### Energetic / Dynamic

| Parameter | Value |
|-----------|-------|
| Duration | 100-250ms |
| Easing | ease-out-expo / elastic |
| Overshoot | 15-30% |
| Paths | Dramatic arcs, large displacement, diagonal |
| Squash-stretch | Yes, exaggerated |

Signature: large scale changes (50-150%), fast color transitions, particle bursts, accelerating stagger, bold edge entrances.
Use for: gaming, sports, music, events, marketing, fitness apps.

## Keyword Matching

| Keywords | Archetype |
|----------|-----------|
| fun, whimsical, bouncy, cute, friendly | Playful |
| elegant, minimal, luxury, sophisticated | Premium |
| clean, professional, business, dashboard | Corporate |
| dynamic, energetic, bold, exciting | Energetic |
| (unspecified) + UI | Corporate (default) |
| (unspecified) + illustration | Playful (default) |

## Brand Motion Identity

Define three constants for recognizable motion:

### 1. Signature Easing (80% of animations)
Playful: ease-out-back | Premium: (0.4,0,0.2,1) | Corporate: (0.2,0,0,1) | Energetic: ease-out-expo

### 2. Duration Palette

| Tier | Playful | Premium | Corporate | Energetic |
|------|---------|---------|-----------|-----------|
| Quick | 150ms | 350ms | 200ms | 100ms |
| Standard | 250ms | 500ms | 300ms | 180ms |
| Slow | 400ms | 800ms | 450ms | 300ms |

### 3. Entrance Pattern
Playful: bounce up from below | Premium: slow fade + scale 98%→100% | Corporate: slide right + opacity | Energetic: snap from edge + overshoot

## Cinematic Pacing & Choreography (Mandatory Rules)

To elevate the motion design from basic templates to professional studio quality, you MUST apply these principles in your scene plans:

### 1. The Rollercoaster Effect (Pacing)
Never make all scenes the exact same duration. Pacing should be driven by the story:
- **Fast/Urgent:** Use snappier cuts (2-3 seconds) for lists, fast facts, or energetic transitions.
- **Slow/Profound:** Allow important statements or emotional beats to "breathe" (4-6 seconds) with longer durations.

### 2. Choreography and Staggering
Elements should feel connected and organic. Avoid showing all UI elements at exactly 0ms.
- **Staggering:** If a scene has a Title and a Card, the Title appears at 0ms, and the Card appears at 150ms. 
- **Sequential Flow:** Guide the user's eye deliberately (e.g., Title -> Subtitle -> Code Block).

### 3. Transition Mapping
Match the transition to the scene's archetype and pacing:
- **Playful/Energetic:** Use `slide` or fast `wipe`.
- **Premium/Corporate:** Use slow `fade` or subtle depth transitions.

## Mixing Archetypes
- 90% primary archetype; specific moments can borrow another
- Ease into personality shifts, don't snap
- Example: corporate dashboard borrows Playful for success state only
