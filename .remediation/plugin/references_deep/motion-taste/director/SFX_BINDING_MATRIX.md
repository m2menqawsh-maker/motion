# SFX to Visual Gestures Binding Matrix (Mandatory)

## 📌 Strict Rules:
1. Every visual gesture (from §3 Emphasis Grammar in `user-signature-style.md`) **MUST** have a corresponding SFX from this matrix.
2. Silent visual gestures are strictly forbidden.
3. Repeating the same SFX file in consecutive scenes is strictly forbidden.
4. This matrix MUST be read before writing any scene plan.

## 🎼 The Mandatory Matrix:

| Visual Gesture | Primary SFX | Alternate SFX (if repeated) | Timing | Volume Level |
|---|---|---|---|---|
| **Neon Ring** (Neon circle for numbers/promises) | `chime-soft.wav` | `bell-subtle.wav`, `crystal-ring.wav` | 0ms (at appearance) | -24 LUFS |
| **Marker Underline** (Marker line for summaries) | `swish-metal.wav` | `whoosh-soft.wav`, `brush-stroke.wav` | 0ms | -24 LUFS |
| **Highlighter BG** (Highlighted background for rules) | `soft-whoosh.wav` | `brush-sweep.wav`, `air-whoosh.wav` | -50ms (before text appears) | -28 LUFS |
| **Strikethrough** (Red line for negation) | `glitch-cut.wav` | `digital-error.wav`, `static-burst.wav` | 0ms | -24 LUFS |
| **Flash Cut** (Flash for emphasis) | `dramatic-boom.wav` | `cinematic-impact.wav`, `thunder-clap.wav` | 0ms | -20 LUFS |
| **Typewriter** (Code/Text typing) | `mechanical-keyboard.wav` | `typewriter-ding.wav`, `key-click.wav` | Every 80ms (per char) | -28 LUFS |
| **Zoom Through** (Deep zoom for transition) | `whoosh-deep.wav` | `cinematic-swoosh.wav`, `wind-rush.wav` | -100ms (before zoom) | -24 LUFS |
| **Shock Zoom** (Shock zoom for emphasis) | `vine-boom.wav` | `impact-hard.wav`, `bass-drop.wav` | 0ms | -18 LUFS |
| **Card Pop** (Card/Notification appearance) | `pop-soft.wav` | `click-subtle.wav`, `notification-ding.wav` | 0ms | -24 LUFS |
| **Slide Reveal** (Pull/Reveal) | `swish-fast.wav` | `whip-pan.wav`, `slide-whoosh.wav` | 0ms | -24 LUFS |
| **Transition** (Between scenes) | `transition-whoosh.wav` | `page-turn.wav`, `glass-shatter.wav` | -100ms (before transition) | -24 LUFS |
| **Stat Counter** (Digital counter) | `tick-soft.wav` | `stat-click.wav`, `counter-beep.wav` | Every 200ms (per digit) | -28 LUFS |
| **Chart Animation** (Data graph) | `data-flow.wav` | `chart-draw.wav`, `graph-rise.wav` | 0ms | -28 LUFS |
| **Code Block** (Code appearance) | `terminal-type.wav` | `code-compile.wav`, `syntax-highlight.wav` | Every 100ms (per line) | -28 LUFS |

## 🚨 Action on Violation:

If you find a scene plan containing a visual gesture without a matching SFX from the table above:

1. **Automatically add the SFX** from the "Primary SFX" column.
2. If the Primary SFX was used in the previous scene, use the "Alternate SFX".
3. Log the injection in the scene plan:
   ```
   ✅ Auto-SFX Injected: [Visual Gesture] → [SFX filename]
   ```

## 📊 Examples of Correct Usage:

### Example 1: Educational Scene (Python)
```
Sentence: "Python is the fastest language to learn"

Visual Gestures:
- Neon Ring around "Python" → SFX: chime-soft.wav
- Marker Underline under "fastest language" → SFX: swish-metal.wav
- Code Block showing Python code → SFX: terminal-type.wav

Result: 3 visual gestures → 3 different SFX ✅
```

### Example 2: Statistics Scene
```
Sentence: "Just 30 days to master programming"

Visual Gestures:
- Neon Ring around "30 days" → SFX: chime-soft.wav
- Stat Counter counts from 1 to 30 → SFX: tick-soft.wav (every 200ms)
- Flash Cut at "Just" → SFX: dramatic-boom.wav

Result: 3 visual gestures → 3 different SFX ✅
```

### Example 3: Comparison Scene
```
Sentence: "The old way vs The new way"

Visual Gestures:
- Strikethrough on "The old way" → SFX: glitch-cut.wav
- Card Pop for "The new way" → SFX: pop-soft.wav
- Highlighter BG under the summary → SFX: soft-whoosh.wav

Result: 3 visual gestures → 3 different SFX ✅
```

## 🛑 Hard Stop Rule:

If you find a scene plan without a matching SFX for every visual gesture:
- **DO NOT proceed** to the next step (media fetching).
- **Inject** the missing SFX immediately.
- **Re-run** the validation until it passes.
