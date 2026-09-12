# User Signature Style — Director's Signature v2

## §0 The Golden Structure: Scene = Sentence, Shot = Beat
1. **Scene** = A complete VO sentence; the count comes from `split_voiceover_sentences`. There is no fixed count.
2. **Shot** = A visual unit within the scene.
3. **Shot Density based on sentence energy (Beat Density):**
   - Sentence < 2.5s → 1 shot
   - 2.5–5s → 2 shots
   - 5–8s → 2–3 shots
   - \> 8s → 3–4 shots
4. **Double Variance:** Two consecutive shots (inside a scene) must not carry the same frame style; and two consecutive scenes must not open with the same style.
5. **Layering as Spice:** Maximum one combined text+video shot per scene; the rest must be either Typography-dominant or Video-dominant.

## §1 Kinetic RTL Tracking
Text is revealed Right-to-Left, and the camera **chases** the words (Camera Tracking). Revealing text by sliding it from a fixed direction is forbidden.

## §2 Word-Chase Zoom
Scale 1.25–1.4 over 250–400ms (ease-out-expo) on the key word, locked to the `word_index`. The camera "dives" into the word.

## §3 Emphasis Grammar
Every spoken sentence carries ≥1 visual gesture on the important word. Do not repeat the same gesture in consecutive scenes:

| Gesture | Term | When to use |
|---|---|---|
| Neon circle | Neon Ring | Promise / Number |
| Marker line | Marker Underline | Summary |
| Highlighted background | Highlighter BG | Golden rule |
| Red strike line | Strikethrough | Negation / Myth |
| Flash | Flash Cut | Emphasis / Urgency |

## §4 Frame Vocabulary
[Full-Bleed, Square Framed Window, Split Screen, Dynamic Typography purely on black] — Cycling is done **at the shot level**, not the scene level.

## §5 Transitions as Verbs
- **Zoom-into-Glyph (Dive):** Diving inside ? or ! = Curiosity
- **Whip Pan:** Energy/Mood shift
- **Zoom-Out Reveal:** Context reveal (roadmap)
- **Graphic Match / Match Cut:** Conceptual link between two shots
≥60% must be camera-driven; simple fades are forbidden except during Visual Rest.

## §6 Color Discipline
Dark base + 2–3 neon accents derived from the product domain; every color in the Blueprint must come from the palette only.

## §7 Gestural Sync
Every visual gesture has a matching audio gesture (underline=swish, shock zoom=boom, ring=chime). No silent gestures, and no prominent sound without a gesture.

## §8 Visual Rest
After two dense scenes (≥3 shots): A calm shot (Dynamic Typography + slow zoom) where music swells = breathing space for the viewer.

## §9 Bookending Motif
One visual motif (e.g., Neon Ring) returns in: The Hook + The Turning Point + The CTA = Closed narrative arc.

## §10 Parallax Depth Staging
Important shots have three layers at varying speeds (Grid background / Center card / Front text) to create 2.5D depth.

## §11 Diegetic CTA
Every action in the CTA = a micro-interaction locked to its word (Save→Bookmark click, Open→Laptop opens, Type→Cursor blinks and types).

## §12 Rhythm and Readability
Duration = VO duration. No shot shorter than 0.8s (mobile reading time). No gesture hold shorter than 0.5s.

## §13 Procedural Purity
Absolutely no stock videos. Rely 100% on motion graphics and live interactive programmatic backgrounds (stars, cyber grids, particles) to guarantee a pure visual identity.

## §14 Hero Text & Breathing Zone
- **Text is the Hero:** Massive (100px+), possessing a full "breathing zone" in the center, with horizontal safety margins (40px) to prevent mobile cropping.
- **Peripheral Icon Distribution:** Icons and flying elements are distributed **"around"** the text (top, bottom, screen edges). Stacking them over the text or in the center is strictly forbidden.
- **No Opaque Boxes:** Avoid solid boxes behind captions. Use bright neon halos (Neon Glow) to ensure extreme contrast.

## §15 Depth & Boundary Breaking
- **No Flat Icons:** Replace simple linear icons (Wireframes) with 3D, color-rich elements (Rich SVG).
- **Reject Flatness:** Eliminate repetitive Split-Screen styles and favor building the scene as deep layers.
- **Break Boundaries:** Explosions and effects (like Shockwaves or Plasma) **must not be trapped inside the card or window bounds**. Let them exceed the edges at massive scales (1000px+) to fill the screen.

## §16 Semantic Directing & Audio Restraint
- **Meaning Change = Visual Change:** Do not keep a visual element static if the VO context completely changes. The old element leaves (e.g., accelerating out of frame) and the new element smoothly replaces it.
- **Audio Restraint:** No audio pollution. Placing a sound effect (SFX) on every single word is forbidden. Massive effects are reserved for transitions, dramatic beats, and explosions only.
