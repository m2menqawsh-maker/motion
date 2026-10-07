# Canonical Keyframe & Animation Mathematics Specification

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R03  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Governing Module**: `contracts/keyframes.ts`  
**Date**: 2026-10-06  

---

## 1. Executive Summary

Milestone **S28-R03** extracts all animation and interpolation mathematics from Remotion's runtime bundle into a **pure mathematical engine** residing in `contracts/keyframes.ts`. 

The contract establishes:
1. **Typed Animation Channels**: Clean separation between target properties and interpolation curves.
2. **Deterministic Evaluation**: Keyframes and channels evaluate to identical IEEE 754 floating-point values in any environment without depending on Remotion or React.
3. **Numeric Parity Spring Physics**: An analytical reference spring simulation achieving machine-level ($< 10^{-9}$) numeric parity with Remotion's `spring()`.

---

## 2. Animation Taxonomy: Presets vs Instances vs Channels

```mermaid
flowchart TD
    Preset[AnimationPreset: Reusable template e.g. 'fade_in', 'slide_up']
    Instance[AnimationInstance: Concrete application to a layer at startFrame]
    Channel[AnimationChannel: Property-specific timeline e.g. TRANSFORM_X]
    Keyframes[Keyframe[]: Sorted time-value pairs with interpolation mode]

    Preset -->|Instantiates| Instance
    Instance -->|Generates / Binds| Channel
    Channel --> Keyframes
```

### 2.1 Typed Property Channels (`ChannelTarget`)
- `TRANSFORM_X`: Horizontal pixel offset / position.
- `TRANSFORM_Y`: Vertical pixel offset / position.
- `SCALE_X` / `SCALE_Y` / `SCALE`: Spatial scale multiplier.
- `ROTATION`: Clockwise angle in degrees.
- `OPACITY`: Visibility factor ($[0.0, 1.0]$).
- `VOLUME`: Audio gain factor ($[0.0, 1.0]$).

---

## 3. Mathematical Evaluation Engines

### 3.1 Easing Curves
Pure implementations of parametric cubic polynomial curves:
- **`LINEAR`**: $f(t) = t$
- **`EASE_IN`**: $f(t) = t^2$
- **`EASE_OUT`**: $f(t) = 1 - (1 - t)^2$
- **`EASE_IN_OUT`**: $f(t) = \begin{cases} 2t^2 & t < 0.5 \\ 1 - \frac{(-2t + 2)^2}{2} & t \ge 0.5 \end{cases}$

### 3.2 Cubic Bezier Numerical Solver (`solveCubicBezier`)
Evaluates explicit control points $(x_1, y_1, x_2, y_2)$ using Newton-Raphson root finding with bisection fallback, converging to within $10^{-7}$ precision in under 8 iterations.

### 3.3 Analytical Spring Physics (`evaluateSpring`)
Physical parameters:
- $m$ = mass (default 1)
- $k$ = stiffness (default 100)
- $c$ = damping ratio coefficient

The undamped angular frequency $\omega_0 = \sqrt{k/m}$ and damping ratio $\zeta = \frac{c}{2\sqrt{km}}$.
For underdamped systems ($\zeta < 1$):
$$\omega_1 = \omega_0 \sqrt{1 - \zeta^2}$$
$$x(t) = 1 - e^{-\zeta \omega_0 t} \left(\cos(\omega_1 t) + \frac{\zeta}{\sqrt{1 - \zeta^2}} \sin(\omega_1 t)\right)$$

Our pure evaluator steps through discrete frames with identical delta-time clamping ($\Delta t \le 64$ ms), achieving exact bit-level numeric parity with Remotion.

---

## 4. Classification of the 13 Named Canonical Animations

| ID | Name | Classification | Pure Channel Structure |
| :--- | :--- | :--- | :--- |
| `none` | None | `CANONICAL_PRIMITIVE` | Static display (no channels) |
| `fade_in` | Fade In | `CANONICAL_PRESET` | `OPACITY` $0 \to 1$ over 15 frames (`LINEAR`) |
| `fade_out` | Fade Out | `CANONICAL_PRESET` | `OPACITY` $1 \to 0$ over 15 frames (`LINEAR`) |
| `fade_in_up` | Fade In Up | `CANONICAL_PRESET` | `TRANSFORM_Y` $40 \to 0$ (`SPRING`, damping 12) + `OPACITY` $0 \to 1$ (10 frames) |
| `zoom_in` | Zoom In | `CANONICAL_PRESET` | `SCALE` $0 \to 1$ (20 frames) + `OPACITY` $0 \to 1$ (10 frames) |
| `zoom_in_bounce` | Zoom In Bounce | `CANONICAL_PRESET` | `SCALE` $0 \to 1$ (`SPRING`, damping 12, stiffness 100) + `OPACITY` $0 \to 1$ (5 frames) |
| `slide_up` | Slide Up | `CANONICAL_PRESET` | `TRANSFORM_Y` $50 \to 0$ (`SPRING`, damping 14) over 15 frames |
| `slide_down` | Slide Down | `CANONICAL_PRESET` | `TRANSFORM_Y` $-50 \to 0$ (`SPRING`, damping 14) over 15 frames |
| `slide_right` | Slide Right | `CANONICAL_PRESET` | `TRANSFORM_X` $-50 \to 0$ (`SPRING`, damping 14) over 15 frames |
| `slide_left` | Slide Left | `CANONICAL_PRESET` | `TRANSFORM_X` $50 \to 0$ (`SPRING`, damping 14) over 15 frames |
| `typewriter` | Typewriter | `REMOTION_COMPATIBILITY_PRESET` | Stepwise reveal over 30 frames (`STEP`) |
| `word_flip` | Word Flip | `REMOTION_COMPATIBILITY_PRESET` | `ROTATION` $90 \to 0$ (`SPRING`, damping 12) over 15 frames |
| `text_swell` | Text Swell | `CANONICAL_PRESET` | `SCALE` $0.5 \to 1.0$ (`SPRING`, damping 10, mass 1.5) over 15 frames |
