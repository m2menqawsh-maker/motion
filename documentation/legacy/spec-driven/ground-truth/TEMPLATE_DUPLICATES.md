# TEMPLATE_DUPLICATES (مصفوفة التكرار)

| Intent | Candidates | Winner | Losers | Reason | Evidence |
|---|---|---|---|---|---|
| captions | Captions (premium), typewriter-subtitle (legacy), animated-text (legacy) | Captions | typewriter-subtitle, animated-text | Tier S, RTL-Ready, Modern font, glassmorphism support | tested via materialized_project |
| typewriter | Typewriter (premium), typewriter (legacy) | Typewriter (premium) | typewriter (legacy) | Better timing hooks, remocn based, cursor options | tested via python_challenge |
| text reveal | BlurReveal (premium), text-reveal (premium), fade-in-text (legacy) | BlurReveal | text-reveal, fade-in-text | Smooth blur transitions, supports Cairo font out of the box | premium-templates/BlurReveal.tsx |
| glitch text | RgbGlitchText (premium), glitch-text (legacy) | RgbGlitchText | glitch-text | Uses modern RGB split channels, smooth seed animation | premium-templates/RgbGlitchText.tsx |
| ken burns | KenBurns (premium), ken-burns (legacy) | KenBurns | ken-burns (legacy) | Native remotion-bits integration, better placement | premium-templates/KenBurns.tsx |
| stat / counter | StatCard (premium), stat-counter (legacy) | StatCard | stat-counter | Implements Onda data look, cascade animations, RTL fixed | premium-templates/StatCard.tsx |
| terminal | Terminal (premium), terminal-window (legacy) | Terminal | terminal-window | Syntax highlighting, LTR preserved, type-speed controls | premium-templates/Terminal.tsx |
| code block | CodeBlock (premium), code-block (legacy) | CodeBlock | code-block | Modern syntax themes, layout auto-fit | premium-templates/CodeBlock.tsx |
| code diff | CodeDiff (premium), code-diff (legacy) | CodeDiff | code-diff | Diff viewer, line addition/removal highlights | premium-templates/CodeDiff.tsx |
| split screen | SplitScreen (premium), split-screen (legacy) | SplitScreen | split-screen | Dynamic flex boxes, responsive text labels | premium-templates/SplitScreen.tsx |
| transitions | glassWipe (premium), whip-pan (premium), cross-dissolve (legacy) | glassWipe, whip-pan | cross-dissolve | Modern frost/glass wipes, cinematic pans | Tier S templates |
| whip pan | whip-pan (premium), whip-pan (legacy) | whip-pan (premium) | whip-pan (legacy) | Directional blur integration | premium-templates/whip-pan.tsx |
| glass wipe | glassWipe (premium) | glassWipe | none | Frost effect is standard | premium-templates/glassWipe.tsx |
| end card | EndCard (cinematic), end-card (legacy) | EndCard | end-card (legacy) | Advanced layout, call to action, social links | cinematic-engine/EndCard.tsx |
| lower third | LowerThird (onda), lower-third (legacy) | needs_probe_qc | lower-third | Visual test required | N/A |
| charts | BarChart (onda), area-chart (legacy) | needs_probe_qc | area-chart | Requires data binding test | N/A |
| carousel / card stack | CardStack (premium), Carousel (premium), image-carousel (legacy) | CardStack | image-carousel | 3D depth, stack interaction | premium-templates/CardStack.tsx |
