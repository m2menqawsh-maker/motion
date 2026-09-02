# نظرة عامة على المشروع (Project Overview)

هذا الملف يحتوي على النظرة العامة الشاملة لبيئة وكيل الموشن التجاري `.agents`، شاملة شجرة الملفات وملفات التوجيه الأساسية.

## 1. شجرة ملفات بيئة العمل (.agents)
> تم استثناء مجلدات المكتبات الكبيرة (مثل `node_modules` و `.venv`).

```text
.agents
├── plugins
│   └── super-video-maker-plugin
│       ├── .agents
│       │   └── mcp_state
│       ├── cinematic-engine
│       │   ├── engine
│       │   │   ├── audio
│       │   │   │   ├── AudioManager.tsx
│       │   │   │   ├── index.ts
│       │   │   │   ├── resolveCues.ts
│       │   │   │   └── types.ts
│       │   │   ├── camera
│       │   │   │   ├── AutoZoom.tsx
│       │   │   │   ├── CameraRig.tsx
│       │   │   │   ├── index.ts
│       │   │   │   ├── interpolate.ts
│       │   │   │   ├── resolveTimeline.ts
│       │   │   │   └── types.ts
│       │   │   ├── choreography
│       │   │   │   ├── filterCursorPath.ts
│       │   │   │   ├── index.ts
│       │   │   │   ├── mapCursorPath.ts
│       │   │   │   └── resolveWindowPose.ts
│       │   │   ├── cursor
│       │   │   │   ├── arc.ts
│       │   │   │   ├── Cursor.tsx
│       │   │   │   ├── CursorSprite.tsx
│       │   │   │   ├── index.ts
│       │   │   │   ├── resolveAnchor.ts
│       │   │   │   └── types.ts
│       │   │   ├── layout
│       │   │   │   ├── index.ts
│       │   │   │   ├── LayoutContext.tsx
│       │   │   │   ├── LayoutWindow.tsx
│       │   │   │   ├── types.ts
│       │   │   │   ├── useWindowRect.ts
│       │   │   │   └── zones.ts
│       │   │   ├── ui-state
│       │   │   │   ├── generatePressKeyframes.ts
│       │   │   │   ├── index.ts
│       │   │   │   ├── types.ts
│       │   │   │   └── UIStateProvider.tsx
│       │   │   ├── index.ts
│       │   │   └── types.ts
│       │   ├── primitives
│       │   │   ├── app-ui
│       │   │   │   ├── AppFromDescriptor.tsx
│       │   │   │   ├── AppShell.tsx
│       │   │   │   ├── Avatar.tsx
│       │   │   │   ├── Badge.tsx
│       │   │   │   ├── Button.tsx
│       │   │   │   ├── DataTable.tsx
│       │   │   │   ├── index.ts
│       │   │   │   ├── ListItems.tsx
│       │   │   │   ├── MessageList.tsx
│       │   │   │   ├── NotificationToast.tsx
│       │   │   │   ├── Panel.tsx
│       │   │   │   ├── PanelGrid.tsx
│       │   │   │   ├── Placeholder.tsx
│       │   │   │   ├── SearchBar.tsx
│       │   │   │   ├── SidebarNav.tsx
│       │   │   │   ├── StatCard.tsx
│       │   │   │   ├── TabBar.tsx
│       │   │   │   └── TopNav.tsx
│       │   │   ├── CountUp.tsx
│       │   │   ├── EndCard.tsx
│       │   │   ├── Enter.tsx
│       │   │   ├── Exit.tsx
│       │   │   ├── Headline.tsx
│       │   │   ├── Highlight.tsx
│       │   │   ├── index.ts
│       │   │   ├── Pulse.tsx
│       │   │   ├── ScenePush.tsx
│       │   │   ├── Stagger.tsx
│       │   │   ├── TrafficLights.tsx
│       │   │   ├── TypeWriter.tsx
│       │   │   ├── Wallpaper.tsx
│       │   │   └── Window.tsx
│       │   ├── scenes
│       │   │   ├── ChaosDesktop.tsx
│       │   │   ├── Closer.tsx
│       │   │   ├── DynamicWindows.tsx
│       │   │   ├── FeatureShowcase.tsx
│       │   │   ├── HeadlineResolution.tsx
│       │   │   ├── index.ts
│       │   │   └── ProductReveal.tsx
│       │   ├── fonts.ts
│       │   ├── schema.ts
│       │   └── tokens.ts
│       ├── commands
│       │   ├── avatar-insta-reel.md
│       │   ├── avatar-vo-reel.md
│       │   └── review-video.md
│       ├── hyperframes-template
│       │   ├── compositions
│       │   │   └── demo.html
│       │   ├── package.json
│       │   └── README.md
│       ├── premium-templates
│       │   ├── assets
│       │   ├── backgrounds
│       │   ├── remocn
│       │   │   ├── blur-out-up.tsx
│       │   │   ├── caret.tsx
│       │   │   ├── typewriter.tsx
│       │   │   └── whip-pan.tsx
│       │   ├── remocn-ui
│       │   │   ├── color.ts
│       │   │   ├── index.ts
│       │   │   ├── motion.ts
│       │   │   ├── theme.ts
│       │   │   ├── timeline.ts
│       │   │   └── types.ts
│       │   ├── remotion-bits
│       │   │   ├── CardStack.tsx
│       │   │   └── Carousel.tsx
│       │   ├── scenes
│       │   │   ├── ken-burns
│       │   │   │   ├── ken-burns.meta.json
│       │   │   │   ├── KenBurns.tsx
│       │   │   │   ├── README.md
│       │   │   │   └── schema.ts
│       │   │   └── social-clip
│       │   │       └── index.tsx
│       │   ├── transitions
│       │   │   ├── glass-wipe
│       │   │   │   ├── glass-wipe.meta.json
│       │   │   │   ├── glassWipe.tsx
│       │   │   │   ├── README.md
│       │   │   │   └── schema.ts
│       │   │   └── type-mask
│       │   │       ├── README.md
│       │   │       ├── schema.ts
│       │   │       ├── type-mask.meta.json
│       │   │       └── typeMask.tsx
│       │   ├── typography
│       │   │   ├── blur-reveal
│       │   │   │   ├── blur-reveal.meta.json
│       │   │   │   ├── BlurReveal.tsx
│       │   │   │   ├── README.md
│       │   │   │   └── schema.ts
│       │   │   ├── captions
│       │   │   │   ├── captions.meta.json
│       │   │   │   ├── Captions.tsx
│       │   │   │   ├── README.md
│       │   │   │   └── schema.ts
│       │   │   ├── rgb-glitch-text
│       │   │   │   ├── README.md
│       │   │   │   ├── rgb-glitch-text.meta.json
│       │   │   │   ├── RgbGlitchText.tsx
│       │   │   │   └── schema.ts
│       │   │   ├── tracking-in
│       │   │   │   ├── README.md
│       │   │   │   ├── schema.ts
│       │   │   │   ├── tracking-in.meta.json
│       │   │   │   └── TrackingIn.tsx
│       │   │   ├── typewriter
│       │   │   │   ├── README.md
│       │   │   │   ├── schema.ts
│       │   │   │   ├── typewriter.meta.json
│       │   │   │   └── Typewriter.tsx
│       │   │   ├── word-stagger
│       │   │   │   ├── README.md
│       │   │   │   ├── schema.ts
│       │   │   │   ├── word-stagger.meta.json
│       │   │   │   └── WordStagger.tsx
│       │   │   └── text-reveal.tsx
│       │   ├── ui-mockups
│       │   │   ├── code-block
│       │   │   │   ├── code-block.meta.json
│       │   │   │   ├── CodeBlock.tsx
│       │   │   │   ├── README.md
│       │   │   │   └── schema.ts
│       │   │   ├── code-diff
│       │   │   │   ├── code-diff.meta.json
│       │   │   │   ├── CodeDiff.tsx
│       │   │   │   ├── README.md
│       │   │   │   └── schema.ts
│       │   │   ├── split-screen
│       │   │   │   ├── README.md
│       │   │   │   ├── schema.ts
│       │   │   │   ├── split-screen.meta.json
│       │   │   │   └── SplitScreen.tsx
│       │   │   └── terminal
│       │   │       ├── README.md
│       │   │       ├── schema.ts
│       │   │       ├── terminal.meta.json
│       │   │       └── Terminal.tsx
│       │   ├── AudioVisualizer.tsx
│       │   ├── SocialClip.tsx
│       │   └── StatCard.tsx
│       ├── recipes
│       │   ├── agent-browser-proof.json
│       │   ├── avatar-explainer.json
│       │   ├── avatar-hook-broll.json
│       │   ├── avatar-insta-split.json
│       │   ├── avatar-product-walkthrough.json
│       │   ├── avatar-vo-broll.json
│       │   ├── captioned-talking-head.json
│       │   ├── dynamic-montage-ad.json
│       │   ├── faceless-broll-ad.json
│       │   ├── living-canvas-explainer.json
│       │   ├── longform-repurpose.json
│       │   ├── misotts-article-sprint.json
│       │   ├── motion-collage-explainer.json
│       │   ├── motion-graphics.json
│       │   ├── README.md
│       │   ├── review-conquest-compilation.json
│       │   ├── schema.json
│       │   ├── screencast-demo.json
│       │   ├── tabletop-levels-explainer.json
│       │   └── ugc-ai-ad.json
│       ├── reference
│       │   └── ground-truth
│       │       ├── CINEMATIC_INDEX.md
│       │       ├── MCP_INDEX.md
│       │       ├── PLAYBOOKS_INDEX.md
│       │       ├── RECIPES_INDEX.md
│       │       ├── template_catalog.json
│       │       ├── TEMPLATE_DUPLICATES.md
│       │       ├── TEMPLATE_INDEX.md
│       │       ├── TOOLS_INDEX.md
│       │       └── VOCAB_REMAP.md
│       ├── references
│       │   ├── deep
│       │   │   ├── ad-spine
│       │   │   │   ├── ad-creative
│       │   │   │   │   ├── batch-ad-pipeline.md
│       │   │   │   │   ├── platform-specs.md
│       │   │   │   │   └── SKILL.md
│       │   │   │   ├── launch
│       │   │   │   │   ├── launch-structure.md
│       │   │   │   │   └── SKILL.md
│       │   │   │   ├── testimonial
│       │   │   │   │   ├── batch-and-typography.md
│       │   │   │   │   ├── quote-card.md
│       │   │   │   │   └── SKILL.md
│       │   │   │   ├── INDEX.md
│       │   │   │   └── REMOTION-VIDEO-CREATION-CHAT.md
│       │   │   ├── cinematic
│       │   │   │   ├── CUSTOMIZATION.md
│       │   │   │   ├── ENGINE.md
│       │   │   │   ├── GETTING-STARTED.md
│       │   │   │   ├── INDEX.md
│       │   │   │   ├── layer-stack.md
│       │   │   │   └── SCENES.md
│       │   │   ├── ground-truth
│       │   │   │   ├── CINEMATIC_INDEX.md
│       │   │   │   ├── MCP_INDEX.md
│       │   │   │   ├── PLAYBOOKS_INDEX.md
│       │   │   │   ├── RECIPES_INDEX.md
│       │   │   │   ├── TEMPLATE_INDEX.md
│       │   │   │   └── TOOLS_INDEX.md
│       │   │   ├── legacy
│       │   │   │   ├── REFERENCE_legacy.md
│       │   │   │   └── SKILL_51_RULES.md
│       │   │   ├── motion-taste
│       │   │   │   ├── director
│       │   │   │   │   ├── choreography.md
│       │   │   │   │   ├── context-adaptation.md
│       │   │   │   │   ├── core-philosophy.md
│       │   │   │   │   ├── decision-framework.md
│       │   │   │   │   ├── disney-principles.md
│       │   │   │   │   ├── emotion-mapping.md
│       │   │   │   │   ├── motion-personality.md
│       │   │   │   │   └── narrative-structure.md
│       │   │   │   ├── patterns
│       │   │   │   │   ├── ambient-continuous.md
│       │   │   │   │   ├── entrance-exit.md
│       │   │   │   │   ├── multi-element.md
│       │   │   │   │   └── state-feedback.md
│       │   │   │   ├── reference
│       │   │   │   │   ├── property-selection.md
│       │   │   │   │   ├── quality-checklist.md
│       │   │   │   │   ├── timing-easing-tables.md
│       │   │   │   │   └── troubleshooting.md
│       │   │   │   ├── INDEX.md
│       │   │   │   └── SKILL.md
│       │   │   ├── patterns
│       │   │   │   ├── examples
│       │   │   │   │   ├── animated-shapes.ts
│       │   │   │   │   ├── falling-spheres.ts
│       │   │   │   │   ├── gold-price-chart.ts
│       │   │   │   │   ├── histogram.ts
│       │   │   │   │   ├── index.ts
│       │   │   │   │   ├── lottie-animation.ts
│       │   │   │   │   ├── progress-bar.ts
│       │   │   │   │   ├── text-rotation.ts
│       │   │   │   │   ├── typewriter-highlight.ts
│       │   │   │   │   └── word-carousel.ts
│       │   │   │   ├── 3d.md
│       │   │   │   ├── charts.md
│       │   │   │   ├── INDEX.md
│       │   │   │   ├── index.ts
│       │   │   │   ├── messaging.md
│       │   │   │   ├── sequencing.md
│       │   │   │   ├── social-media.md
│       │   │   │   ├── spring-physics.md
│       │   │   │   ├── transitions.md
│       │   │   │   └── typography.md
│       │   │   ├── remotion
│       │   │   │   ├── captions
│       │   │   │   │   ├── display-captions.md
│       │   │   │   │   ├── import-srt-captions.md
│       │   │   │   │   ├── SKILL.md
│       │   │   │   │   └── transcribe-captions.md
│       │   │   │   ├── create
│       │   │   │   │   ├── SKILL.md
│       │   │   │   │   ├── tailwind.md
│       │   │   │   │   └── video-layout.md
│       │   │   │   ├── markup
│       │   │   │   │   ├── 3d.md
│       │   │   │   │   ├── audio-visualization.md
│       │   │   │   │   ├── audio.md
│       │   │   │   │   ├── calculate-metadata.md
│       │   │   │   │   ├── compositions.md
│       │   │   │   │   ├── cropping.md
│       │   │   │   │   ├── effects.md
│       │   │   │   │   ├── embedding-videos.md
│       │   │   │   │   ├── ffmpeg.md
│       │   │   │   │   ├── gifs.md
│       │   │   │   │   ├── google-fonts.md
│       │   │   │   │   ├── html-in-canvas.md
│       │   │   │   │   ├── images.md
│       │   │   │   │   ├── light-leaks.md
│       │   │   │   │   ├── local-fonts.md
│       │   │   │   │   ├── lottie.md
│       │   │   │   │   ├── measuring-dom-nodes.md
│       │   │   │   │   ├── measuring-text.md
│       │   │   │   │   ├── multi-scene-video.md
│       │   │   │   │   ├── parameters.md
│       │   │   │   │   ├── sequencing.md
│       │   │   │   │   ├── sfx.md
│       │   │   │   │   ├── silence-detection.md
│       │   │   │   │   ├── SKILL.md
│       │   │   │   │   ├── text-highlights.md
│       │   │   │   │   ├── timing.md
│       │   │   │   │   ├── transitions.md
│       │   │   │   │   ├── video-editing.md
│       │   │   │   │   └── voiceover.md
│       │   │   │   ├── multimedia
│       │   │   │   │   ├── get-audio-duration.md
│       │   │   │   │   ├── get-video-dimensions.md
│       │   │   │   │   ├── get-video-duration.md
│       │   │   │   │   └── SKILL.md
│       │   │   │   ├── render
│       │   │   │   │   ├── SKILL.md
│       │   │   │   │   └── transparent-videos.md
│       │   │   │   ├── studio
│       │   │   │   │   └── SKILL.md
│       │   │   │   ├── INDEX.md
│       │   │   │   └── SKILL.md
│       │   │   ├── INDEX.md
│       │   │   └── mcp-toolbook.md
│       │   ├── FFMPEG_PLAYBOOK.md
│       │   ├── HOOK_PLAYBOOK_ARTICLE_SPRINT.md
│       │   ├── HYPERREALISTIC_IMAGE_SOP.md
│       │   ├── LIVING_CANVAS_PLAYBOOK.md
│       │   ├── MOTION_COLLAGE_STYLE.md
│       │   ├── README.md
│       │   ├── REMOTION_VIDEO_GUIDE.md
│       │   ├── REVIEW_VIDEO_PLAYBOOK.md
│       │   ├── ROUTER.md
│       │   ├── SEEDANCE_AVATAR_ROI.md
│       │   ├── SPOKEN_VO_HUMANIZER.md
│       │   ├── TABLETOP_EXPLAINER_PLAYBOOK.md
│       │   ├── VIDEO_COPY_PLAYBOOK.md
│       │   └── WORKFLOW_EXAMPLES.md
│       ├── remotion-template
│       │   ├── .agents
│       │   │   └── skills
│       │   ├── .claude
│       │   │   └── skills
│       │   │       └── remotionui-agent
│       │   │           └── SKILL.md
│       │   ├── public
│       │   │   └── render-props.json
│       │   ├── src
│       │   │   ├── components
│       │   │   │   ├── onda
│       │   │   │   │   ├── audio-clip
│       │   │   │   │   │   ├── audio-clip.meta.json
│       │   │   │   │   │   ├── AudioClip.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── audio-visualizer
│       │   │   │   │   │   ├── audio-visualizer.meta.json
│       │   │   │   │   │   ├── AudioVisualizer.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── bar-chart
│       │   │   │   │   │   ├── bar-chart.meta.json
│       │   │   │   │   │   ├── BarChart.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── blur-reveal
│       │   │   │   │   │   ├── blur-reveal.meta.json
│       │   │   │   │   │   ├── BlurReveal.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── bounding-box
│       │   │   │   │   │   ├── bounding-box.meta.json
│       │   │   │   │   │   ├── BoundingBox.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── callout
│       │   │   │   │   │   ├── callout.meta.json
│       │   │   │   │   │   ├── Callout.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── camera-shake
│       │   │   │   │   │   ├── camera-shake.meta.json
│       │   │   │   │   │   ├── CameraShake.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── captions
│       │   │   │   │   │   ├── captions.meta.json
│       │   │   │   │   │   ├── Captions.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── chapter-card
│       │   │   │   │   │   ├── chapter-card.meta.json
│       │   │   │   │   │   ├── ChapterCard.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── code-block
│       │   │   │   │   │   ├── code-block.meta.json
│       │   │   │   │   │   ├── CodeBlock.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── code-diff
│       │   │   │   │   │   ├── code-diff.meta.json
│       │   │   │   │   │   ├── CodeDiff.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── confetti
│       │   │   │   │   │   ├── confetti.meta.json
│       │   │   │   │   │   ├── Confetti.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── count-up
│       │   │   │   │   │   ├── count-up.meta.json
│       │   │   │   │   │   ├── CountUp.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── draw-on
│       │   │   │   │   │   ├── draw-on.meta.json
│       │   │   │   │   │   ├── DrawOn.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── dynamic-grid
│       │   │   │   │   │   ├── dynamic-grid.meta.json
│       │   │   │   │   │   ├── DynamicGrid.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── end-card
│       │   │   │   │   │   ├── end-card.meta.json
│       │   │   │   │   │   ├── EndCard.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── fade-in
│       │   │   │   │   │   ├── fade-in.meta.json
│       │   │   │   │   │   ├── FadeIn.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── fade-out
│       │   │   │   │   │   ├── fade-out.meta.json
│       │   │   │   │   │   ├── FadeOut.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── gradient-shift
│       │   │   │   │   │   ├── gradient-shift.meta.json
│       │   │   │   │   │   ├── GradientShift.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── grain-overlay
│       │   │   │   │   │   ├── grain-overlay.meta.json
│       │   │   │   │   │   ├── GrainOverlay.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── highlight
│       │   │   │   │   │   ├── highlight.meta.json
│       │   │   │   │   │   ├── Highlight.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── icon-pop
│       │   │   │   │   │   ├── icon-pop.meta.json
│       │   │   │   │   │   ├── IconPop.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── image-reveal
│       │   │   │   │   │   ├── image-reveal.meta.json
│       │   │   │   │   │   ├── ImageReveal.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── ken-burns
│       │   │   │   │   │   ├── ken-burns.meta.json
│       │   │   │   │   │   ├── KenBurns.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── line-chart
│       │   │   │   │   │   ├── line-chart.meta.json
│       │   │   │   │   │   ├── LineChart.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── logo-sting
│       │   │   │   │   │   ├── logo-sting.meta.json
│       │   │   │   │   │   ├── LogoSting.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── lower-third
│       │   │   │   │   │   ├── lower-third.meta.json
│       │   │   │   │   │   ├── LowerThird.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── marquee
│       │   │   │   │   │   ├── marquee.meta.json
│       │   │   │   │   │   ├── Marquee.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── mask-reveal
│       │   │   │   │   │   ├── mask-reveal.meta.json
│       │   │   │   │   │   ├── MaskReveal.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── matrix-decode
│       │   │   │   │   │   ├── matrix-decode.meta.json
│       │   │   │   │   │   ├── MatrixDecode.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── mesh-gradient
│       │   │   │   │   │   ├── mesh-gradient.meta.json
│       │   │   │   │   │   ├── MeshGradient.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── node-graph
│       │   │   │   │   │   ├── node-graph.meta.json
│       │   │   │   │   │   ├── NodeGraph.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── parallax
│       │   │   │   │   │   ├── parallax.meta.json
│       │   │   │   │   │   ├── Parallax.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── pie-reveal
│       │   │   │   │   │   ├── pie-reveal.meta.json
│       │   │   │   │   │   ├── PieReveal.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── progress-bar
│       │   │   │   │   │   ├── progress-bar.meta.json
│       │   │   │   │   │   ├── ProgressBar.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── quote-card
│       │   │   │   │   │   ├── quote-card.meta.json
│       │   │   │   │   │   ├── QuoteCard.tsx
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── rgb-glitch-text
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── rgb-glitch-text.meta.json
│       │   │   │   │   │   ├── RgbGlitchText.tsx
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── rotate-in
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── rotate-in.meta.json
│       │   │   │   │   │   ├── RotateIn.tsx
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── scale-in
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── scale-in.meta.json
│       │   │   │   │   │   ├── ScaleIn.tsx
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── shimmer-sweep
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── shimmer-sweep.meta.json
│       │   │   │   │   │   └── ShimmerSweep.tsx
│       │   │   │   │   ├── slide-in
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── slide-in.meta.json
│       │   │   │   │   │   └── SlideIn.tsx
│       │   │   │   │   ├── slide-out
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── slide-out.meta.json
│       │   │   │   │   │   └── SlideOut.tsx
│       │   │   │   │   ├── slot-machine-roll
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── slot-machine-roll.meta.json
│       │   │   │   │   │   └── SlotMachineRoll.tsx
│       │   │   │   │   ├── split-screen
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── split-screen.meta.json
│       │   │   │   │   │   └── SplitScreen.tsx
│       │   │   │   │   ├── spotlight
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── spotlight.meta.json
│       │   │   │   │   │   └── Spotlight.tsx
│       │   │   │   │   ├── spotlight-card
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── spotlight-card.meta.json
│       │   │   │   │   │   └── SpotlightCard.tsx
│       │   │   │   │   ├── stagger-group
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── stagger-group.meta.json
│       │   │   │   │   │   └── StaggerGroup.tsx
│       │   │   │   │   ├── stat-card
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── stat-card.meta.json
│       │   │   │   │   │   └── StatCard.tsx
│       │   │   │   │   ├── terminal
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── terminal.meta.json
│       │   │   │   │   │   └── Terminal.tsx
│       │   │   │   │   ├── text-fade-replace
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── text-fade-replace.meta.json
│       │   │   │   │   │   └── TextFadeReplace.tsx
│       │   │   │   │   ├── timeline
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── timeline.meta.json
│       │   │   │   │   │   └── Timeline.tsx
│       │   │   │   │   ├── title-card
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── title-card.meta.json
│       │   │   │   │   │   └── TitleCard.tsx
│       │   │   │   │   ├── tracking-in
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── tracking-in.meta.json
│       │   │   │   │   │   └── TrackingIn.tsx
│       │   │   │   │   ├── transitions
│       │   │   │   │   │   ├── blur
│       │   │   │   │   │   │   ├── blur.meta.json
│       │   │   │   │   │   │   ├── blur.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── chromatic-aberration
│       │   │   │   │   │   │   ├── chromatic-aberration.meta.json
│       │   │   │   │   │   │   ├── chromaticAberration.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── clock-wipe
│       │   │   │   │   │   │   ├── clock-wipe.meta.json
│       │   │   │   │   │   │   ├── clockWipe.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── cross-fade
│       │   │   │   │   │   │   ├── cross-fade.meta.json
│       │   │   │   │   │   │   ├── crossFade.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── depth-push
│       │   │   │   │   │   │   ├── depth-push.meta.json
│       │   │   │   │   │   │   ├── depthPush.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── device-pullback
│       │   │   │   │   │   │   ├── device-pullback.meta.json
│       │   │   │   │   │   │   ├── devicePullback.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── dip-to-color
│       │   │   │   │   │   │   ├── dip-to-color.meta.json
│       │   │   │   │   │   │   ├── dipToColor.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── expand-morph
│       │   │   │   │   │   │   ├── expand-morph.meta.json
│       │   │   │   │   │   │   ├── expandMorph.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── flip
│       │   │   │   │   │   │   ├── flip.meta.json
│       │   │   │   │   │   │   ├── flip.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── glass-wipe
│       │   │   │   │   │   │   ├── glass-wipe.meta.json
│       │   │   │   │   │   │   ├── glassWipe.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── grid-pixelate
│       │   │   │   │   │   │   ├── grid-pixelate.meta.json
│       │   │   │   │   │   │   ├── gridPixelate.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── iris
│       │   │   │   │   │   │   ├── iris.meta.json
│       │   │   │   │   │   │   ├── iris.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── morph
│       │   │   │   │   │   │   ├── morph.meta.json
│       │   │   │   │   │   │   ├── morph.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── push
│       │   │   │   │   │   │   ├── push.meta.json
│       │   │   │   │   │   │   ├── push.tsx
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   └── schema.ts
│       │   │   │   │   │   ├── slide
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   │   ├── slide.meta.json
│       │   │   │   │   │   │   └── slide.tsx
│       │   │   │   │   │   ├── type-mask
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   │   ├── type-mask.meta.json
│       │   │   │   │   │   │   └── typeMask.tsx
│       │   │   │   │   │   ├── wipe
│       │   │   │   │   │   │   ├── README.md
│       │   │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   │   ├── wipe.meta.json
│       │   │   │   │   │   │   └── wipe.tsx
│       │   │   │   │   │   └── zoom
│       │   │   │   │   │       ├── README.md
│       │   │   │   │   │       ├── schema.ts
│       │   │   │   │   │       ├── zoom.meta.json
│       │   │   │   │   │       └── zoom.tsx
│       │   │   │   │   ├── typewriter
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── typewriter.meta.json
│       │   │   │   │   │   └── Typewriter.tsx
│       │   │   │   │   ├── underline
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── underline.meta.json
│       │   │   │   │   │   └── Underline.tsx
│       │   │   │   │   ├── video-clip
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── video-clip.meta.json
│       │   │   │   │   │   └── VideoClip.tsx
│       │   │   │   │   ├── vignette
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── vignette.meta.json
│       │   │   │   │   │   └── Vignette.tsx
│       │   │   │   │   ├── word-rotate
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── word-rotate.meta.json
│       │   │   │   │   │   └── WordRotate.tsx
│       │   │   │   │   ├── word-stagger
│       │   │   │   │   │   ├── README.md
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   ├── word-stagger.meta.json
│       │   │   │   │   │   └── WordStagger.tsx
│       │   │   │   │   ├── .ondajs-installed.json
│       │   │   │   │   └── index.ts
│       │   │   │   ├── remocn
│       │   │   │   │   ├── button.tsx
│       │   │   │   │   ├── caret.tsx
│       │   │   │   │   ├── dialog.tsx
│       │   │   │   │   ├── input.tsx
│       │   │   │   │   ├── spinner.tsx
│       │   │   │   │   ├── use-button-transition.ts
│       │   │   │   │   ├── use-dialog-transition.ts
│       │   │   │   │   └── use-input-transition.ts
│       │   │   │   └── snap-cn
│       │   │   ├── compositions
│       │   │   │   ├── ai-composer-showcase
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── ai-generation-canvas
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── bento-pan
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── browser-flow
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── creator-reel
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── dashboard-populate
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── data-story
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── deploy-reveal
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── ecosystem-orbit
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── hero-device-assemble
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── hero-loop
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── image-expand
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── intro
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── landing-code-showcase
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── live-code-split
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── podcast-clip
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── pricing-focus
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── showcase
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── social-clip
│       │   │   │   │   └── index.tsx
│       │   │   │   ├── tool-menu-slide
│       │   │   │   │   └── index.tsx
│       │   │   │   └── tutorial-clip
│       │   │   │       └── index.tsx
│       │   │   ├── lib
│       │   │   │   ├── onda
│       │   │   │   │   ├── primitives
│       │   │   │   │   │   ├── Camera.tsx
│       │   │   │   │   │   ├── Glow.tsx
│       │   │   │   │   │   ├── GridField.tsx
│       │   │   │   │   │   ├── index.ts
│       │   │   │   │   │   └── Surface.tsx
│       │   │   │   │   ├── canvas-schemas.ts
│       │   │   │   │   ├── canvas.tsx
│       │   │   │   │   ├── choreography.ts
│       │   │   │   │   ├── easing.ts
│       │   │   │   │   ├── elevation.ts
│       │   │   │   │   ├── hooks.ts
│       │   │   │   │   ├── motion.ts
│       │   │   │   │   ├── random.ts
│       │   │   │   │   ├── timing.ts
│       │   │   │   │   └── tokens.ts
│       │   │   │   ├── remocn-ui
│       │   │   │   │   ├── color.ts
│       │   │   │   │   ├── index.ts
│       │   │   │   │   ├── motion.ts
│       │   │   │   │   ├── theme.ts
│       │   │   │   │   ├── timeline.ts
│       │   │   │   │   └── types.ts
│       │   │   │   └── snap-cn-ui
│       │   │   │       ├── color.ts
│       │   │   │       ├── index.ts
│       │   │   │       ├── motion.ts
│       │   │   │       ├── theme.ts
│       │   │   │       ├── timeline.ts
│       │   │   │       └── types.ts
│       │   │   ├── premium-templates
│       │   │   │   ├── remocn
│       │   │   │   │   ├── blur-out-up.tsx
│       │   │   │   │   ├── caret.tsx
│       │   │   │   │   ├── typewriter.tsx
│       │   │   │   │   └── whip-pan.tsx
│       │   │   │   ├── remocn-ui
│       │   │   │   │   ├── color.ts
│       │   │   │   │   ├── index.ts
│       │   │   │   │   ├── motion.ts
│       │   │   │   │   ├── theme.ts
│       │   │   │   │   ├── timeline.ts
│       │   │   │   │   └── types.ts
│       │   │   │   ├── remotion-bits
│       │   │   │   │   ├── CardStack.tsx
│       │   │   │   │   └── Carousel.tsx
│       │   │   │   ├── scenes
│       │   │   │   │   ├── ken-burns
│       │   │   │   │   │   ├── KenBurns.tsx
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   └── social-clip
│       │   │   │   │       └── index.tsx
│       │   │   │   ├── transitions
│       │   │   │   │   ├── glass-wipe
│       │   │   │   │   │   ├── glassWipe.tsx
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   └── type-mask
│       │   │   │   │       ├── schema.ts
│       │   │   │   │       └── typeMask.tsx
│       │   │   │   ├── typography
│       │   │   │   │   ├── blur-reveal
│       │   │   │   │   │   ├── BlurReveal.tsx
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── captions
│       │   │   │   │   │   ├── Captions.tsx
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── rgb-glitch-text
│       │   │   │   │   │   ├── RgbGlitchText.tsx
│       │   │   │   │   │   └── schema.ts
│       │   │   │   │   ├── tracking-in
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   └── TrackingIn.tsx
│       │   │   │   │   ├── typewriter
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   └── Typewriter.tsx
│       │   │   │   │   ├── word-stagger
│       │   │   │   │   │   ├── schema.ts
│       │   │   │   │   │   └── WordStagger.tsx
│       │   │   │   │   └── text-reveal.tsx
│       │   │   │   └── ui-mockups
│       │   │   │       ├── code-block
│       │   │   │       │   ├── CodeBlock.tsx
│       │   │   │       │   └── schema.ts
│       │   │   │       ├── code-diff
│       │   │   │       │   ├── CodeDiff.tsx
│       │   │   │       │   └── schema.ts
│       │   │   │       ├── split-screen
│       │   │   │       │   ├── schema.ts
│       │   │   │       │   └── SplitScreen.tsx
│       │   │   │       └── terminal
│       │   │   │           ├── schema.ts
│       │   │   │           └── Terminal.tsx
│       │   │   ├── remotion
│       │   │   │   ├── hooks
│       │   │   │   │   └── use-stagger.ts
│       │   │   │   ├── lib
│       │   │   │   │   ├── ai-composer-utils.tsx
│       │   │   │   │   ├── audio-viz-utils.ts
│       │   │   │   │   ├── caption-utils.ts
│       │   │   │   │   ├── chart-utils.ts
│       │   │   │   │   ├── code-syntax.tsx
│       │   │   │   │   ├── displacement-presentation.tsx
│       │   │   │   │   ├── displacement-transition.ts
│       │   │   │   │   ├── gpu.ts
│       │   │   │   │   ├── layout.ts
│       │   │   │   │   ├── map-utils.ts
│       │   │   │   │   ├── media-utils.ts
│       │   │   │   │   ├── motion-primitive.ts
│       │   │   │   │   ├── motion-tokens.ts
│       │   │   │   │   ├── motion-wrapper.tsx
│       │   │   │   │   ├── path-morph.ts
│       │   │   │   │   ├── path-utils.ts
│       │   │   │   │   ├── sample-media.ts
│       │   │   │   │   ├── springs.ts
│       │   │   │   │   ├── text-emphasis.ts
│       │   │   │   │   ├── text-fit-utils.ts
│       │   │   │   │   ├── text-split.ts
│       │   │   │   │   ├── timing.ts
│       │   │   │   │   └── transition-timing.ts
│       │   │   │   ├── primitives
│       │   │   │   │   ├── animated-noise-grain.tsx
│       │   │   │   │   ├── arrow-annotate.tsx
│       │   │   │   │   ├── audio-pulse.tsx
│       │   │   │   │   ├── audio-reactive-scale.tsx
│       │   │   │   │   ├── audio-scrubber.tsx
│       │   │   │   │   ├── audiogram-bars.tsx
│       │   │   │   │   ├── aurora-bg.tsx
│       │   │   │   │   ├── badge-stamp.tsx
│       │   │   │   │   ├── bar-chart-race.tsx
│       │   │   │   │   ├── beat-pulse-grid.tsx
│       │   │   │   │   ├── blob-morph.tsx
│       │   │   │   │   ├── blur-focus-in.tsx
│       │   │   │   │   ├── blur-in.tsx
│       │   │   │   │   ├── blur-reveal.tsx
│       │   │   │   │   ├── bubble-chart-pack.tsx
│       │   │   │   │   ├── candlestick-chart.tsx
│       │   │   │   │   ├── caption-emoji-beat.tsx
│       │   │   │   │   ├── caption-highlight.tsx
│       │   │   │   │   ├── caustics-bg.tsx
│       │   │   │   │   ├── chromatic-aberration-wipe.tsx
│       │   │   │   │   ├── comparison-bars.tsx
│       │   │   │   │   ├── confetti-burst.tsx
│       │   │   │   │   ├── connector-lines.tsx
│       │   │   │   │   ├── counter.tsx
│       │   │   │   │   ├── cursor-path.tsx
│       │   │   │   │   ├── dashed-path-travel.tsx
│       │   │   │   │   ├── depth-of-field-blur.tsx
│       │   │   │   │   ├── directional-wipe.tsx
│       │   │   │   │   ├── donut-chart.tsx
│       │   │   │   │   ├── dynamic-grid.tsx
│       │   │   │   │   ├── fade-in.tsx
│       │   │   │   │   ├── fade-out.tsx
│       │   │   │   │   ├── frosted-glass-wipe.tsx
│       │   │   │   │   ├── funnel-chart.tsx
│       │   │   │   │   ├── gantt-timeline.tsx
│       │   │   │   │   ├── gauge-dial.tsx
│       │   │   │   │   ├── globe-arc.tsx
│       │   │   │   │   ├── glow-pulse.tsx
│       │   │   │   │   ├── grid-pixelate-wipe.tsx
│       │   │   │   │   ├── handwriting-text.tsx
│       │   │   │   │   ├── heatmap-grid.tsx
│       │   │   │   │   ├── infinite-marquee.tsx
│       │   │   │   │   ├── karaoke-captions.tsx
│       │   │   │   │   ├── light-rays.tsx
│       │   │   │   │   ├── light-sweep-text.tsx
│       │   │   │   │   ├── line-chart-draw.tsx
│       │   │   │   │   ├── liquid-text-morph.tsx
│       │   │   │   │   ├── map-canvas.tsx
│       │   │   │   │   ├── map-heat-overlay.tsx
│       │   │   │   │   ├── map-markers.tsx
│       │   │   │   │   ├── map-route.tsx
│       │   │   │   │   ├── marker-highlight.tsx
│       │   │   │   │   ├── masked-slide-reveal.tsx
│       │   │   │   │   ├── matrix-decode.tsx
│       │   │   │   │   ├── mesh-gradient-bg.tsx
│       │   │   │   │   ├── motion-trail.tsx
│       │   │   │   │   ├── multi-device-lineup.tsx
│       │   │   │   │   ├── neon-flicker-text.tsx
│       │   │   │   │   ├── orbit-motion.tsx
│       │   │   │   │   ├── parallax-layers.tsx
│       │   │   │   │   ├── particle-field.tsx
│       │   │   │   │   ├── path-draw.tsx
│       │   │   │   │   ├── perspective-marquee.tsx
│       │   │   │   │   ├── pie-slice-reveal.tsx
│       │   │   │   │   ├── progress-bar.tsx
│       │   │   │   │   ├── radar-chart.tsx
│       │   │   │   │   ├── rgb-glitch-text.tsx
│       │   │   │   │   ├── rotate-in.tsx
│       │   │   │   │   ├── scale-in.tsx
│       │   │   │   │   ├── scanline-crt.tsx
│       │   │   │   │   ├── scatter-plot-pop.tsx
│       │   │   │   │   ├── scramble-text.tsx
│       │   │   │   │   ├── shake-emphasis.tsx
│       │   │   │   │   ├── shape-morph.tsx
│       │   │   │   │   ├── simulated-cursor.tsx
│       │   │   │   │   ├── skew-in.tsx
│       │   │   │   │   ├── slide-left.tsx
│       │   │   │   │   ├── slide-up.tsx
│       │   │   │   │   ├── slot-roll.tsx
│       │   │   │   │   ├── sparkline-row.tsx
│       │   │   │   │   ├── spatial-push.tsx
│       │   │   │   │   ├── speaker-label-captions.tsx
│       │   │   │   │   ├── split-text-chars.tsx
│       │   │   │   │   ├── spring-in.tsx
│       │   │   │   │   ├── squash-stretch.tsx
│       │   │   │   │   ├── srt-caption-track.tsx
│       │   │   │   │   ├── stacked-area-chart.tsx
│       │   │   │   │   ├── stagger-children.tsx
│       │   │   │   │   ├── staggered-fade-up.tsx
│       │   │   │   │   ├── strikethrough-replace.tsx
│       │   │   │   │   ├── stroke-to-fill-text.tsx
│       │   │   │   │   ├── subtitle-translate.tsx
│       │   │   │   │   ├── svg-mask-reveal.tsx
│       │   │   │   │   ├── text-mask-video.tsx
│       │   │   │   │   ├── topographic-lines-bg.tsx
│       │   │   │   │   ├── tracking-in.tsx
│       │   │   │   │   ├── transcript-scroll.tsx
│       │   │   │   │   ├── transition-blinds.tsx
│       │   │   │   │   ├── transition-card-flip.tsx
│       │   │   │   │   ├── transition-circle-reveal.tsx
│       │   │   │   │   ├── transition-clock-wipe.tsx
│       │   │   │   │   ├── transition-fade.tsx
│       │   │   │   │   ├── transition-light-leak.tsx
│       │   │   │   │   ├── transition-liquid-warp.tsx
│       │   │   │   │   ├── transition-morph-shape.tsx
│       │   │   │   │   ├── transition-slide.tsx
│       │   │   │   │   ├── transition-whip-pan.tsx
│       │   │   │   │   ├── transition-wipe.tsx
│       │   │   │   │   ├── treemap-blocks.tsx
│       │   │   │   │   ├── typewriter.tsx
│       │   │   │   │   ├── variable-font-morph.tsx
│       │   │   │   │   ├── voice-note-bubble.tsx
│       │   │   │   │   ├── vu-meter.tsx
│       │   │   │   │   ├── waterfall-chart.tsx
│       │   │   │   │   ├── wave-text.tsx
│       │   │   │   │   ├── waveform-bars-radial.tsx
│       │   │   │   │   ├── waveform-line.tsx
│       │   │   │   │   ├── word-pop-captions.tsx
│       │   │   │   │   └── zoom-through.tsx
│       │   │   │   └── scenes
│       │   │   │       ├── animated-bar-chart
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── audiogram-scene
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── auto-fit-title
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── b-roll-stack
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── calendar-month-fill
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── callout-spotlight
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── caption-bumper
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── caption-scene
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── changelog-entry
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── chat-gpt
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── chat-to-preview
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── claude-chat
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── claude-code
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── code-accordion
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── code-diff-wipe
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── code-reveal
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── comment-callout
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── commit-graph
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── comparison-table
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── countdown-timer
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── data-flow-pipes
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── device-mockup-zoom
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── drag-drop-flow
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── end-card
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── faq-accordion
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── feature-list
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── file-tree-reveal
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── form-fill-sequence
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── hook-card
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── kanban-move
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── logo-reveal
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── logo-wall
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── lower-third
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── map-flight
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── media-frame
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── media-sequence
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── metric-ticker
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── news-ticker-bar
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── notification-stack
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── opencode
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── org-chart-build
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── poll-overlay
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── pricing-card
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── quiz-question
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── quote-card
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── reaction-burst
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── roadmap-lanes
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── search-results-populate
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── split-screen
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── sports-scorebug
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── stat-card
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── tab-switch-panel
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── talking-head-layout
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── team-grid
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── terminal-simulator
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── timeline-steps
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── title-card
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── v0
│       │   │   │       │   └── index.tsx
│       │   │   │       ├── weather-card
│       │   │   │       │   └── index.tsx
│       │   │   │       └── zoom-pan-frame
│       │   │   │           └── index.tsx
│       │   │   ├── templates
│       │   │   │   ├── animated-list.tsx
│       │   │   │   ├── animated-text.tsx
│       │   │   │   ├── area-chart.tsx
│       │   │   │   ├── blinds-transition.tsx
│       │   │   │   ├── bokeh-circles.tsx
│       │   │   │   ├── bounce-text.tsx
│       │   │   │   ├── bubble-pop-text.tsx
│       │   │   │   ├── camera-shake.tsx
│       │   │   │   ├── card-flip.tsx
│       │   │   │   ├── chapter-title.tsx
│       │   │   │   ├── chart-animation.tsx
│       │   │   │   ├── cinematic-title-intro.tsx
│       │   │   │   ├── circular-progress.tsx
│       │   │   │   ├── clock-wipe.tsx
│       │   │   │   ├── comparison-chart.tsx
│       │   │   │   ├── countdown-intro.tsx
│       │   │   │   ├── countdown-timer.tsx
│       │   │   │   ├── credits-roll.tsx
│       │   │   │   ├── cross-dissolve.tsx
│       │   │   │   ├── donut-chart.tsx
│       │   │   │   ├── end-card.tsx
│       │   │   │   ├── fade-through-black.tsx
│       │   │   │   ├── film-burn.tsx
│       │   │   │   ├── floating-bubble-text.tsx
│       │   │   │   ├── gallery-grid.tsx
│       │   │   │   ├── geometric-patterns.tsx
│       │   │   │   ├── glitch-text.tsx
│       │   │   │   ├── gradient-shift.tsx
│       │   │   │   ├── grid-pulse.tsx
│       │   │   │   ├── image-carousel.tsx
│       │   │   │   ├── image-comparison-slider.tsx
│       │   │   │   ├── image-zoom-reveal.tsx
│       │   │   │   ├── iris-transition.tsx
│       │   │   │   ├── ken-burns.tsx
│       │   │   │   ├── letterbox-reveal.tsx
│       │   │   │   ├── line-chart.tsx
│       │   │   │   ├── liquid-wave.tsx
│       │   │   │   ├── logo-blur-reveal.tsx
│       │   │   │   ├── logo-bounce-drop.tsx
│       │   │   │   ├── logo-fade-reveal.tsx
│       │   │   │   ├── logo-glitch-reveal.tsx
│       │   │   │   ├── logo-scale-rotate.tsx
│       │   │   │   ├── logo-spin-reveal.tsx
│       │   │   │   ├── logo-split-reveal.tsx
│       │   │   │   ├── logo-stroke-draw.tsx
│       │   │   │   ├── logo-typewriter.tsx
│       │   │   │   ├── lower-third.tsx
│       │   │   │   ├── masonry-gallery.tsx
│       │   │   │   ├── matrix-rain.tsx
│       │   │   │   ├── morph-transition.tsx
│       │   │   │   ├── noise-grain.tsx
│       │   │   │   ├── notification-pop.tsx
│       │   │   │   ├── parallax-pan.tsx
│       │   │   │   ├── particle-explosion.tsx
│       │   │   │   ├── photo-stack.tsx
│       │   │   │   ├── picture-in-picture.tsx
│       │   │   │   ├── pie-chart.tsx
│       │   │   │   ├── pixel-transition.tsx
│       │   │   │   ├── polaroid-frame.tsx
│       │   │   │   ├── popping-text.tsx
│       │   │   │   ├── progress-bars.tsx
│       │   │   │   ├── progress-steps.tsx
│       │   │   │   ├── pulsing-text.tsx
│       │   │   │   ├── push-transition.tsx
│       │   │   │   ├── quote-card.tsx
│       │   │   │   ├── rotating-carousel.tsx
│       │   │   │   ├── slide-text.tsx
│       │   │   │   ├── slide-wipe.tsx
│       │   │   │   ├── sound-wave.tsx
│       │   │   │   ├── split-screen.tsx
│       │   │   │   ├── spotlight-reveal.tsx
│       │   │   │   ├── starfield.tsx
│       │   │   │   ├── stat-counter.tsx
│       │   │   │   ├── subscribe-reminder.tsx
│       │   │   │   ├── text-highlight.tsx
│       │   │   │   ├── title-split.tsx
│       │   │   │   ├── typewriter-subtitle.tsx
│       │   │   │   ├── vignette-pulse.tsx
│       │   │   │   ├── whip-pan.tsx
│       │   │   │   ├── zoom-pulse.tsx
│       │   │   │   └── zoom-through.tsx
│       │   │   ├── CaptionedTalkingHead.tsx
│       │   │   ├── captionLayout.ts
│       │   │   ├── index.ts
│       │   │   ├── Root.tsx
│       │   │   ├── rtl.css
│       │   │   └── SurgicalSutureAd.tsx
│       │   ├── build_caption_props.py
│       │   ├── card_stack.json
│       │   ├── carousel.json
│       │   ├── components.json
│       │   ├── dependency_tree.json
│       │   ├── package-lock.json
│       │   ├── package.json
│       │   ├── README.md
│       │   ├── remotion-ui.json
│       │   ├── remotion.config.ts
│       │   ├── skills-lock.json
│       │   └── tsconfig.json
│       ├── scripts
│       │   ├── verify
│       │   │   ├── contact-sheet.sh
│       │   │   ├── probe-mp4.sh
│       │   │   ├── README.md
│       │   │   ├── seek-shot.sh
│       │   │   └── verify_preview.py
│       │   ├── audit_imports.py
│       │   ├── audit_skill.py
│       │   ├── build_catalog.py
│       │   ├── build_ground_truth.py
│       │   ├── check_orphans.py
│       │   ├── materialize_project.py
│       │   ├── motion_validator.py
│       │   ├── probe_qc.py
│       │   ├── stage_gate.py
│       │   ├── stitch_skill.py
│       │   ├── sync_templates.py
│       │   ├── template_lint.py
│       │   ├── validate_blueprint.py
│       │   ├── verify_links.py
│       │   └── verify_media_layer.py
│       ├── skills
│       │   ├── remocn
│       │   │   ├── references
│       │   │   │   ├── archetypes
│       │   │   │   │   ├── changelog.md
│       │   │   │   │   ├── cli-tool-demo.md
│       │   │   │   │   ├── feature-announcement.md
│       │   │   │   │   ├── index.md
│       │   │   │   │   ├── logo-bumper.md
│       │   │   │   │   ├── oss-showcase.md
│       │   │   │   │   ├── pricing-reveal.md
│       │   │   │   │   ├── product-demo.md
│       │   │   │   │   ├── testimonial-reel.md
│       │   │   │   │   └── year-in-review.md
│       │   │   │   └── anatomy.md
│       │   │   └── SKILL.md
│       │   ├── snapcn
│       │   │   ├── references
│       │   │   │   ├── archetypes
│       │   │   │   │   ├── changelog.md
│       │   │   │   │   ├── cli-tool-demo.md
│       │   │   │   │   ├── feature-announcement.md
│       │   │   │   │   ├── index.md
│       │   │   │   │   ├── logo-bumper.md
│       │   │   │   │   ├── oss-showcase.md
│       │   │   │   │   ├── pricing-reveal.md
│       │   │   │   │   ├── product-demo.md
│       │   │   │   │   ├── testimonial-reel.md
│       │   │   │   │   └── year-in-review.md
│       │   │   │   ├── components
│       │   │   │   │   ├── announce-title.md
│       │   │   │   │   ├── answer-stream.md
│       │   │   │   │   ├── block-wordmark.md
│       │   │   │   │   ├── caret.md
│       │   │   │   │   ├── follower-rush.md
│       │   │   │   │   ├── hero-launch.md
│       │   │   │   │   ├── index.md
│       │   │   │   │   ├── input.md
│       │   │   │   │   ├── karaoke-captions.md
│       │   │   │   │   ├── laptop-frame.md
│       │   │   │   │   ├── logo-assemble.md
│       │   │   │   │   ├── logo-flicker.md
│       │   │   │   │   ├── moodboard-reveal.md
│       │   │   │   │   ├── orbit-gallery.md
│       │   │   │   │   ├── phone-frame.md
│       │   │   │   │   ├── prompt-zoom.md
│       │   │   │   │   ├── pulsing-border.md
│       │   │   │   │   ├── search-typing.md
│       │   │   │   │   ├── snap-cn-ui.md
│       │   │   │   │   ├── status-cycle.md
│       │   │   │   │   ├── terminal-simulator.md
│       │   │   │   │   ├── text-build.md
│       │   │   │   │   ├── text-highlight.md
│       │   │   │   │   ├── text-reveal.md
│       │   │   │   │   ├── text-swap.md
│       │   │   │   │   ├── text-swell.md
│       │   │   │   │   ├── word-captions.md
│       │   │   │   │   └── word-flip.md
│       │   │   │   ├── anatomy.md
│       │   │   │   ├── anti-patterns.md
│       │   │   │   ├── design.md
│       │   │   │   └── motion-principles.md
│       │   │   └── SKILL.md
│       │   └── super-video-maker
│       │       └── SKILL.md
│       ├── templates
│       │   ├── animated-list.tsx
│       │   ├── animated-text.tsx
│       │   ├── area-chart.tsx
│       │   ├── blinds-transition.tsx
│       │   ├── bokeh-circles.tsx
│       │   ├── bounce-text.tsx
│       │   ├── bubble-pop-text.tsx
│       │   ├── camera-shake.tsx
│       │   ├── card-flip.tsx
│       │   ├── chapter-title.tsx
│       │   ├── chart-animation.tsx
│       │   ├── cinematic-title-intro.tsx
│       │   ├── circular-progress.tsx
│       │   ├── clock-wipe.tsx
│       │   ├── comparison-chart.tsx
│       │   ├── countdown-intro.tsx
│       │   ├── countdown-timer.tsx
│       │   ├── credits-roll.tsx
│       │   ├── cross-dissolve.tsx
│       │   ├── donut-chart.tsx
│       │   ├── end-card.tsx
│       │   ├── fade-through-black.tsx
│       │   ├── film-burn.tsx
│       │   ├── floating-bubble-text.tsx
│       │   ├── gallery-grid.tsx
│       │   ├── geometric-patterns.tsx
│       │   ├── glitch-text.tsx
│       │   ├── gradient-shift.tsx
│       │   ├── grid-pulse.tsx
│       │   ├── image-carousel.tsx
│       │   ├── image-comparison-slider.tsx
│       │   ├── image-zoom-reveal.tsx
│       │   ├── iris-transition.tsx
│       │   ├── ken-burns.tsx
│       │   ├── letterbox-reveal.tsx
│       │   ├── line-chart.tsx
│       │   ├── liquid-wave.tsx
│       │   ├── logo-blur-reveal.tsx
│       │   ├── logo-bounce-drop.tsx
│       │   ├── logo-fade-reveal.tsx
│       │   ├── logo-glitch-reveal.tsx
│       │   ├── logo-scale-rotate.tsx
│       │   ├── logo-spin-reveal.tsx
│       │   ├── logo-split-reveal.tsx
│       │   ├── logo-stroke-draw.tsx
│       │   ├── logo-typewriter.tsx
│       │   ├── lower-third.tsx
│       │   ├── masonry-gallery.tsx
│       │   ├── matrix-rain.tsx
│       │   ├── morph-transition.tsx
│       │   ├── noise-grain.tsx
│       │   ├── notification-pop.tsx
│       │   ├── parallax-pan.tsx
│       │   ├── particle-explosion.tsx
│       │   ├── photo-stack.tsx
│       │   ├── picture-in-picture.tsx
│       │   ├── pie-chart.tsx
│       │   ├── pixel-transition.tsx
│       │   ├── polaroid-frame.tsx
│       │   ├── popping-text.tsx
│       │   ├── progress-bars.tsx
│       │   ├── progress-steps.tsx
│       │   ├── pulsing-text.tsx
│       │   ├── push-transition.tsx
│       │   ├── quote-card.tsx
│       │   ├── README.md
│       │   ├── rotating-carousel.tsx
│       │   ├── slide-text.tsx
│       │   ├── slide-wipe.tsx
│       │   ├── sound-wave.tsx
│       │   ├── split-screen.tsx
│       │   ├── spotlight-reveal.tsx
│       │   ├── starfield.tsx
│       │   ├── stat-counter.tsx
│       │   ├── subscribe-reminder.tsx
│       │   ├── text-highlight.tsx
│       │   ├── title-split.tsx
│       │   ├── typewriter-subtitle.tsx
│       │   ├── vignette-pulse.tsx
│       │   ├── whip-pan.tsx
│       │   ├── zoom-pulse.tsx
│       │   └── zoom-through.tsx
│       ├── tests
│       │   └── test_video_recipes.py
│       ├── tools
│       │   ├── mcp-servers
│       │   │   ├── audio-tools-mcp
│       │   │   │   ├── src
│       │   │   │   │   └── audio_tools_mcp
│       │   │   │   │       └── __init__.py
│       │   │   │   ├── utils
│       │   │   │   │   ├── ffmpeg_ops.py
│       │   │   │   │   ├── manifest_builder.py
│       │   │   │   │   ├── sentence_splitter.py
│       │   │   │   │   ├── timeline_builder.py
│       │   │   │   │   └── voiceover_ops.py
│       │   │   │   ├── .gitignore
│       │   │   │   ├── .python-version
│       │   │   │   ├── complex_test_result.json
│       │   │   │   ├── pyproject.toml
│       │   │   │   ├── README.md
│       │   │   │   ├── server.py
│       │   │   │   ├── test_result.json
│       │   │   │   ├── uv.lock
│       │   │   │   └── voiceover_manifest.json
│       │   │   ├── common-tools-mcp
│       │   │   │   ├── src
│       │   │   │   │   └── common_tools_mcp
│       │   │   │   │       └── __init__.py
│       │   │   │   ├── utils
│       │   │   │   │   └── cache_ops.py
│       │   │   │   ├── .gitignore
│       │   │   │   ├── .python-version
│       │   │   │   ├── pyproject.toml
│       │   │   │   ├── README.md
│       │   │   │   ├── server.py
│       │   │   │   └── uv.lock
│       │   │   ├── ffmpeg-mcp-server
│       │   │   │   ├── scripts
│       │   │   │   │   └── .gitkeep
│       │   │   │   ├── test
│       │   │   │   │   └── .gitkeep
│       │   │   │   ├── .gitignore
│       │   │   │   ├── Dockerfile
│       │   │   │   ├── LICENSE
│       │   │   │   ├── package-lock.json
│       │   │   │   ├── package.json
│       │   │   │   ├── README.md
│       │   │   │   ├── server.js
│       │   │   │   └── server.js.bak
│       │   │   ├── image-tools-mcp
│       │   │   │   ├── src
│       │   │   │   │   └── image_tools_mcp
│       │   │   │   │       └── __init__.py
│       │   │   │   ├── utils
│       │   │   │   │   └── image_ops.py
│       │   │   │   ├── .gitignore
│       │   │   │   ├── .python-version
│       │   │   │   ├── pyproject.toml
│       │   │   │   ├── README.md
│       │   │   │   ├── server.py
│       │   │   │   └── uv.lock
│       │   │   ├── media-sources-mcp
│       │   │   │   ├── assets
│       │   │   │   │   └── downloads
│       │   │   │   │       ├── coding_keyboard.mp4
│       │   │   │   │       │   └── pexels_video_coding_keyboard.mp4
│       │   │   │   │       └── coding_keyboard_v2.mp4
│       │   │   │   │           └── pexels_video_coding_keyboard_v2.mp4
│       │   │   │   ├── src
│       │   │   │   │   └── media_sources_mcp
│       │   │   │   │       └── __init__.py
│       │   │   │   ├── tools
│       │   │   │   │   ├── freesound.py
│       │   │   │   │   ├── iconify.py
│       │   │   │   │   ├── pexels.py
│       │   │   │   │   └── pixabay.py
│       │   │   │   ├── utils
│       │   │   │   │   ├── downloader.py
│       │   │   │   │   ├── file_organizer.py
│       │   │   │   │   ├── http_client.py
│       │   │   │   │   └── pixabay_scraper.py
│       │   │   │   ├── .env.example
│       │   │   │   ├── .gitignore
│       │   │   │   ├── .python-version
│       │   │   │   ├── dump.html
│       │   │   │   ├── dump_html.py
│       │   │   │   ├── pyproject.toml
│       │   │   │   ├── pyrightconfig.json
│       │   │   │   ├── README.md
│       │   │   │   ├── server.py
│       │   │   │   ├── test_attrs.py
│       │   │   │   ├── test_click.py
│       │   │   │   ├── test_internal_api.py
│       │   │   │   ├── test_network.py
│       │   │   │   ├── test_pix.py
│       │   │   │   ├── test_playwright.py
│       │   │   │   ├── test_regex.py
│       │   │   │   ├── test_scrape.py
│       │   │   │   ├── test_workflow.py
│       │   │   │   ├── test_workflow_final.py
│       │   │   │   └── uv.lock
│       │   │   ├── video-tools-mcp
│       │   │   │   ├── src
│       │   │   │   │   └── video_tools_mcp
│       │   │   │   │       └── __init__.py
│       │   │   │   ├── utils
│       │   │   │   │   └── ffmpeg_ops.py
│       │   │   │   ├── .gitignore
│       │   │   │   ├── .python-version
│       │   │   │   ├── pyproject.toml
│       │   │   │   ├── README.md
│       │   │   │   ├── server.py
│       │   │   │   └── uv.lock
│       │   │   └── Video_Editor_MCP
│       │   │       ├── src
│       │   │       │   └── video_editor
│       │   │       │       ├── __init__.py
│       │   │       │       ├── __main__.py
│       │   │       │       ├── newserver.py
│       │   │       │       └── server.py
│       │   │       ├── .gitignore
│       │   │       ├── .python-version
│       │   │       ├── pyproject.toml
│       │   │       ├── README.md
│       │   │       └── uv.lock
│       │   ├── ad_quality_gate.py
│       │   ├── agent_browser_recorder.py
│       │   ├── broll_layout_qc.py
│       │   ├── demo_video_composer.py
│       │   ├── elevenlabs_voice.py
│       │   ├── fal_seedance_video.py
│       │   ├── ffmpeg_qc.py
│       │   ├── heygen_client.py
│       │   ├── image_provider.py
│       │   ├── local_explainer_broll.py
│       │   ├── media_pipeline.py
│       │   ├── music_provider.py
│       │   ├── replicate_video.py
│       │   ├── screen_recorder.py
│       │   ├── ugc_ad_runner.py
│       │   ├── video_captioner.py
│       │   ├── video_orchestrator.py
│       │   └── video_recipes.py
│       ├── workflows
│       │   ├── avatar-insta-split
│       │   │   ├── build_reel.py
│       │   │   ├── capture_article.py
│       │   │   ├── gen_avatar.py
│       │   │   ├── LOCAL.md
│       │   │   ├── make_badge.py
│       │   │   ├── make_sfx.py
│       │   │   ├── plan.example.json
│       │   │   └── README.md
│       │   ├── avatar-vo-broll
│       │   │   ├── build_vo_broll.py
│       │   │   ├── plan.example.json
│       │   │   └── README.md
│       │   ├── living-canvas-explainer
│       │   │   ├── motion-library.tsx
│       │   │   ├── README.md
│       │   │   └── section-template.tsx
│       │   └── tabletop-levels-explainer
│       │       ├── assemble.py
│       │       ├── build_captions.py
│       │       ├── capture_anim.py
│       │       ├── capture_receipts.py
│       │       ├── finalize.py
│       │       ├── gen_craft_clip.py
│       │       ├── gen_presenter.py
│       │       ├── README.md
│       │       └── whisper_timeline.py
│       ├── .blueprint_lock.json
│       ├── .env
│       ├── .gitignore
│       ├── ARCHITECTURE.md
│       ├── AUDIT_REPORT.md
│       ├── CHANGELOG.md
│       ├── DISTRIBUTION_CHECKLIST.md
│       ├── DYNAMIC_MONTAGE_PLAYBOOK.md
│       ├── extract_comps.py
│       ├── INSTALLATION.md
│       ├── LICENSE
│       ├── mcp_config.json
│       ├── package.json
│       ├── plugin.json
│       ├── README.md
│       ├── requirements.txt
│       ├── USAGE.md
│       └── verify.py
├── rules
│   └── video-production-protocol.md
├── skills
│   ├── remocn
│   │   ├── references
│   │   │   ├── archetypes
│   │   │   │   ├── changelog.md
│   │   │   │   ├── cli-tool-demo.md
│   │   │   │   ├── feature-announcement.md
│   │   │   │   ├── index.md
│   │   │   │   ├── logo-bumper.md
│   │   │   │   ├── oss-showcase.md
│   │   │   │   ├── pricing-reveal.md
│   │   │   │   ├── product-demo.md
│   │   │   │   ├── testimonial-reel.md
│   │   │   │   └── year-in-review.md
│   │   │   └── anatomy.md
│   │   └── SKILL.md
│   └── snapcn
│       ├── references
│       │   ├── archetypes
│       │   │   ├── changelog.md
│       │   │   ├── cli-tool-demo.md
│       │   │   ├── feature-announcement.md
│       │   │   ├── index.md
│       │   │   ├── logo-bumper.md
│       │   │   ├── oss-showcase.md
│       │   │   ├── pricing-reveal.md
│       │   │   ├── product-demo.md
│       │   │   ├── testimonial-reel.md
│       │   │   └── year-in-review.md
│       │   ├── components
│       │   │   ├── announce-title.md
│       │   │   ├── answer-stream.md
│       │   │   ├── block-wordmark.md
│       │   │   ├── caret.md
│       │   │   ├── follower-rush.md
│       │   │   ├── hero-launch.md
│       │   │   ├── index.md
│       │   │   ├── input.md
│       │   │   ├── karaoke-captions.md
│       │   │   ├── laptop-frame.md
│       │   │   ├── logo-assemble.md
│       │   │   ├── logo-flicker.md
│       │   │   ├── moodboard-reveal.md
│       │   │   ├── orbit-gallery.md
│       │   │   ├── phone-frame.md
│       │   │   ├── prompt-zoom.md
│       │   │   ├── pulsing-border.md
│       │   │   ├── search-typing.md
│       │   │   ├── snap-cn-ui.md
│       │   │   ├── status-cycle.md
│       │   │   ├── terminal-simulator.md
│       │   │   ├── text-build.md
│       │   │   ├── text-highlight.md
│       │   │   ├── text-reveal.md
│       │   │   ├── text-swap.md
│       │   │   ├── text-swell.md
│       │   │   ├── word-captions.md
│       │   │   └── word-flip.md
│       │   ├── anatomy.md
│       │   ├── anti-patterns.md
│       │   ├── design.md
│       │   └── motion-principles.md
│       └── SKILL.md
└── AGENTS.md

```

## 2. ملفات التوجيه والقواعد الإلزامية

### 2.1 القواعد الأساسية للوكيل (AGENTS.md)
<details>
<summary>اضغط لعرض AGENTS.md</summary>

```markdown
﻿# Clean Video Workspace — Agent Directives

## 1. الهوية
أنت **مخرج موشن تجاري** تعمل في مساحة إنتاج فيديو نظيفة.
مصدر قدراتك الوحيد هو الـ Plugin المثبت في:
`.agents/plugins/super-video-maker-plugin/`
# 🤖 دور الذكاء الاصطناعي: المخطط الرئيسي ومنسق خط الإنتاج (Master Planner & Pipeline Orchestrator)

## 🎯 الرؤية الأساسية (Core Identity)
أنت لست مولد فيديوهات مباشر، بل أنت **المخطط الاستراتيجي ومهندس خط الإنتاج (Pipeline Architect)** لمساحة العمل المحلية. 
مهمتك هي التخطيط، كتابة السكريبتات (Python/Node/PowerShell)، إدارة خوادم الـ MCP، معالجة الأخطاء، وتوجيه محرك الـ Remotion و FFmpeg لبناء الفيديو برمجياً. أنت العقل المدبر الذي يضمن مرور المشروع عبر المراحل التسع بصرامة ودون ارتجال.

## 🛑 القواعد الذهبية (لا تفاوض)
1. **أنت لا تصنع الفيديوهات بيدك**: أنت تكتب الكود (React/Remotion)، والسكريبتات (Python/FFmpeg)، وتدير الأدوات المحلية والسحابية (MCPs) التي تقوم بالتنفيذ الفعلي.
2. **الاعتماد على البيئة المحلية (Local-First)**: كل المعالجات الثقيلة (تطبيع الصوت، تحويل الفيديوهات لـ All-Intra، تحميل الأيقونات والستوك) تتم عبر سكريبتات تكتبها وتُشغلها محلياً في مجلد `scratch/`.
3. **التوثيق الحي (Live Logging)**: يجب توثيق كل خطوة، كل سكريبت مُنفذ، وكل خطأ تم حله في ملفات المشروع (مثل `conversation_log.md` أو تقارير المراحل).
4. **التوقفات الإجبارية (Hard Stops)**: لا تتجاوز أي مرحلة دون موافقة صريحة من المستخدم عند بوابات الموافقة (الخطة، الأصول، والـ Blueprint).
5. **مكافحة الأوهام (Anti-Hallucination)**: إذا فشلت أداة MCP أو API، لا تتوقف ولا تخترع أدوات وهمية. اكتب سكريبت Python بديل (Fallback) في مجلد `scratch/` لتجاوز المشكلة (مثل استخدام Playwright للـ Scraping أو FFmpeg المباشر).

## ⚙️ المسؤوليات التنفيذية (ماذا تفعل بالضبط؟)
1. **المرحلة 0-1 (الاستيضاح والتخطيط)**: تحليل طلب المستخدم، مطابقة الوصفة (Recipe)، وكتابة العمود الفقري والخطة (`01_plan.md`).
2. **المرحلة 2-3 (جلب ومعالجة الميديا)**: 
   - كتابة سكريبتات للتواصل مع `media-sources-mcp` و `audio-tools-mcp`.
   - إذا فشلت الـ APIs، تكتب سكريبتات `urllib` أو `Playwright` لجلب الأصول.
   - استخدام `FFmpeg` لمعالجة الفيديوهات (GOP=1, yuv420p) وتطبيع الصوت (-16 LUFS للـ VO، -24 LUFS للـ SFX).
3. **المرحلة 4-5 (التوقيتات والـ Blueprint)**: استخراج التوقيتات بالكلمة (Word-level timings) وربطها بسجل الأصول والمخطط البشري.
4. **المرحلة 6 (البناء البرمجي - Remotion)**:
   - تهيئة بيئة Node.js/Remotion محلياً.
   - كتابة مكونات React (`MainComposition.tsx`, `CaptionLayer.tsx`) مع الاستفادة من القوالب الجاهزة (`templates/`).
   - إدارة الـ Hot Reloading وتشغيل الاستوديو (`npm run studio`) لمعاينة المستخدم.
5. **المرحلة 7-8 (المعاينة والرندر)**: تشغيل بوابات الجودة (QC) عبر `ffmpeg_qc.py` والتأكد من جاهزية الفيديو للتسليم.

## 🛠️ آلية التعامل مع الأخطاء (Debugging Protocol)
- **خطأ في ملف أو مسار؟** -> اكتب سكريبت Python لفحص الشجرة (`os.walk`) وإعادة تسمية الملفات.
- **خطأ في تشغيل الميديا (MediaPlaybackError)؟** -> أعد ترميز الملف فوراً باستخدام `ffmpeg` (تحويل الـ Pixel format والـ Codec).
- **نقص في الـ APIs (مثل Pexels/Pixabay)؟** -> اكتب Scraper مخصص باستخدام `Playwright` أو `BeautifulSoup` في مجلد `scratch/`.
- **مشكلة في النصوص العربية (RTL)؟** -> تدخل مباشرة في كود الـ CSS/React لإضافة `direction: 'rtl'` و `flex-wrap`.

## 📝 مخرجاتك المتوقعة في كل جلسة
- **ملفات التخطيط**: `00_answers.md`, `01_plan.md`, `05_blueprint_human.md`.
- **السكريبتات الديناميكية**: تكتب وتُشغل سكريبتات في `scratch/` (مثل `fetch_mcp_videos.py`, `process_media.py`, `fix_icons.py`).
- **كود الـ Remotion**: تحديث ملفات `src/*.tsx` في مجلد `06_build/`.
- **التقارير**: `02_asset_manifest.json`, `03_preprocess_report.json`, `04_timings.json`.

---
**تأكيد الدور**: في كل مرة تبدأ فيها جلسة جديدة، تعامل مع نفسك كمدير تقني (CTO) لخط إنتاج فيديو. المستخدم هو "المنتج/العميل" الذي يوجه الرؤية، وأنت من يترجم هذه الرؤية إلى كود، سكريبتات، وأوامر تقنية تنفذها البيئة المحلية وخوادم الـ MCP.

## 2. قوانين الوصول
- **ممنوع** تعديل أي ملف داخل `.agents/plugins/super-video-maker-plugin/` إلا إذا طلب المستخدم صراحة ترقية الـ Plugin.
- **ممنوع** إنشاء مشاريع خارج `projects/`.
- **ممنوع** كتابة ميديا داخل مجلد الـ Plugin.
- الميديا تُخزن حصراً في: `assets/`, `storage/`, `processed/`, `projects/<id>/`.

## 3. البروتوكول الإلزامي
كل مهمة فيديو تمر عبر `rules/video-production-protocol.md` حرفياً.
لا استثناءات. لا اختصارات. لا "سأفعلها بسرعة".

## 4. القراءة الإلزامية قبل أي مهمة فيديو
قبل كتابة أي كود أو جلب أي أصل:
1. اقرأ `.agents/plugins/super-video-maker-plugin/skills/super-video-maker/SKILL.md`
2. اقرأ `.agents/rules/video-production-protocol.md`
3. اقرأ `ROUTER.md` داخل الـ Plugin إذا لزم الأمر

## 5. التعامل مع الـ MCP
- الخوادم السبعة معرّفة في `plugin.json` → `mcp.json`
- **ممنوع** إنشاء سكربتات Python لاستدعاء أدوات الـ MCP يدوياً
- **ممنوع** استخدام `curl`, `wget`, `yt-dlp` خارج أدوات `media-sources-mcp`
- استدعِ الأدوات مباشرة عبر الـ MCP Client

## 6. الأخطاء المحظورة
- ❌ إنشاء ملفات وهمية (تقارير/توقيتات بدون تنفيذ فعلي)
- ❌ تخطي المراحل بدون اكتمال سابقتها
- ❌ توليد صوت بيب/نغمات بدلاً من جلب موسيقى حقيقية
- ❌ جلب أقل من المطلوب (مؤثرين لفيديو 52 ثانية)
- ❌ تجاوز قفل الأمان (mechanical_lock) بدون إذن صريح

## 7. القوانين الصارمة للبروتوكول الجديد (v3.0)

1. **ممنوع الرندر قبل المعاينة:** لا `npx remotion render` قبل موافقة المستخدم الصريحة في الاستوديو.
2. **ممنوع الاستوديو قبل الفحص:** لا فتح استوديو قبل نجاح `probe_qc_report.json` بحالة "pass".
3. **القفل الميكانيكي مقدس:** لا اختراق لـ `mechanical_lock` بأي طريقة. القفل يُفتح فقط عبر ملف `.studio_unlocked` الذي يُنشأ تلقائياً بعد نجاح الـ Probe-QC.
4. **صفر ارتجال:** ممنوع كتابة `spring()` أو `interpolate()` خارج `templates/` و `cinematic-engine/`. كل كود حركة يجب أن يكون من قالب معتمد في `TEMPLATE_INDEX.md`.
5. **بوابة واحدة للميديا:** كل ميديا تدخل البناء عبر `scripts/materialize_project.py` فقط. ممنوع النسخ اليدوي.
6. **الصوت أولاً:** `analyze_voiceover` هي أول خطوة تقنية في أي مشروع. لا خطة بدون تحليل صوتي فعلي.
7. **التعديل → فحص جزئي → QC كامل:** عند طلب تعديل من الاستوديو، نفحص اللقطة المتأثرة فقط. لكن قبل أي رندر نهائي، نعيد الـ Probe-QC الكامل.
8. **مكافحة الأوهام:** لا ملفات وهمية، لا تقارير فارغة، لا توقيتات مخمنة. كل رقم يأتي من أداة فعلية.
9. **بوابات المراحل:** `stage_gate.py` يعمل قبل كل مرحلة. لا تخطي.
10. **الذوق بوابة لا نصيحة:** شخصية الحركة وأرقامها تُكتب في خطة المشهد، و `motion_validator.py` يفحصها. فشل الفحص = لا بناء.
11. **القراءة قبل كل مشهد:** الوكيل يجب أن يقرأ ملفات محرك الذوق قبل كتابة أي كود للمشهد.
12. **خطة لكل مشهد:** لا بناء بدون خطة مشهد مكتوبة وموافقة المستخدم عليها.
# 🎨 Personal Design & Directing Protocol (إلزامي لكل المشاريع)

## 1. المسافات والهوامش (Spacing & Breathing Room)
- **قاعدة التنفس:** ممنوع تماماً أن تلتصق النصوص أو البطاقات ببعضها. يجب ترك هوامش (Margins) واسعة ومريحة للعين (مثلاً 40px - 80px بين العناوين والبطاقات).
- **استغلال المساحة:** ممنوع حشر العناصر في زاوية واحدة أو ترك فراغات ميتة (Dead Space) في المنتصف. يجب استغلال مساحة الشاشة (9:16) بالكامل (Full Canvas Coverage).
- **فصل الطبقات:** يجب فصل شارات الهيدر (Headers) عن العناوين الرئيسية، وفصل أكواد البرمجة عن النصوص العربية بمسافات واضحة.

## 2. الخطوط والنصوص (Typography & RTL)
- **الخطوط الافتراضية ممنوعة:** استخدم دائماً خطوطاً حديثة، تقنية، وهندسية (مثل: Alexandria, Cairo, IBM Plex Sans Arabic للعناوين، و JetBrains Mono للأكواد).
- **حجم الخط:** النصوص يجب أن تكون ضخمة وعريضة (Bold & Massive) لتتناسب مع شاشات الموبايل. (العناوين 50px+، النصوص الفرعية 30px+).
- **مشكلة تكسر الحروف (Sub-pixel Bug):** عند تحريك النصوص العربية أو تكبيرها، يجب إضافة `willChange: "transform"` للحاوية لمنع المتصفح من تكسير الحروف وظهور خطوط بيضاء بينها.
- **الاتجاه:** فرض `direction: "rtl"` و `flex-wrap` على كل حاويات النصوص العربية.

## 3. الحركة والكاميرا (Motion & Camera Choreography)
- **الزوم السينمائي:** الزوم يجب أن يكون عميقاً (Deep Zoom) وسلساً (Gradual Ease) وليس سريعاً ومزعجاً. استخدم الـ Zoom كـ "بوابة" للانتقال بين المشاهد (مثال: الغوص داخل علامة الاستفهام).
- **منع الدروب فريم (Zero-Drop Smoothness):** ممنوع القفزات المفاجئة (Snappy Jumps) في الموقع أو الحجم. استخدم الـ Cross-fade أو الحاويات ثابتة الأبعاد لمنع أي اهتزاز بصري.
- **الكاميرا تتبع النص (Dynamic Camera Tracking):** الكاميرا لا يجب أن تكون ثابتة. يجب أن تتحرك (Pan/Tilt) لتتبع ظهور النصوص في أماكن مختلفة من الشاشة.
- **الخلفيات الموحدة:** ممنوع القطع المفاجئ (Hard Cut) للخلفيات بين المشاهد. استخدم خلفية موحدة ومستمرة (Unified Cyber/Matrix Background) تتدفق عبر التايم لاين بالكامل.

## 4. التوزيع المكاني والتماثل (Spatial Layout & Symmetry)
- **التماثل (Symmetry 100%):** المشاهد يجب أن تكون متماثلة وموزعة بعناية (مثل توزيع الهرم: عنصر بالأعلى، عنصران بالأسفل).
- **التنوع المكاني:** ممنوع وضع كل النصوص في المنتصف. وزع العناصر ديناميكياً (أعلى يمين، أسفل يسار، منتصف) لتخلق حركة بصرية.
- **القوالب الجاهزة (Template-looking):** إذا كان التصميم يبدو بدائياً أو كقالب جاهز، ابحث في النت عن تنسيقات حديثة (مثل Glassmorphism, Neon Cyber Cards, Split Screen) وطبقها.

## 5. الصوتيات والمؤثرات (Audio & SFX)
- **منع التكرار:** ممنوع استخدام نفس المؤثر الصوتي (SFX) في أكثر من مشهد. كل حدث له صوتunique.
- **جودة المؤثرات:** استخدم مؤثرات سينمائية (Cinematic Booms, Swish Metal, Mechanical Keyboards). ممنوع استخدام أصوات النظام المزعجة (مثل Windows Chime/Bell).
- **المعالجة (Normalization):** كل الـ SFX يجب أن تطبع عند `-24 LUFS` والـ VO عند `-16 LUFS`.
- **الموسيقى الديناميكية:** في لحظات الصمت (Silence Gaps) أو التوقف الدراماتيكي، يجب أن يرتفع صوت الموسيقى الخلفية (BGM) تلقائياً لملء الفراغ.
- **التزامن (Frame-Perfect Sync):** كل حركة بصرية (Pop, Zoom, Slide) يجب أن تضرب بالضبط (بالملي ثانية) مع نطق الكلمة في الـ VO.

## 6. الألوان والأصول (Colors & Assets)
- **الثيم الداكن (Dark/Cyber Theme):** الخلفيات يجب أن تكون داكنة (Deep Indigo, Black, Dark Cyber) مع إضاءات نيون (Neon Cyan, Gold) لخلق تباين عالي (High Contrast).
- **الأيقونات:** ممنوع استخدام الأيقونات الخطية الأحادية (Monochrome Wireframes). يجب استخدام شارات فيكتورية ملونة وغنية (Rich Colorful SVG Badges) ذات هوية بصرية مستقلة.
- **الكابشن:** استخدم الكابشن الزجاجي (Glassmorphism Pills) مع حدود نيون وأيقونات، ولا تستخدم النصوص العادية المكشوفة.
```
</details>

### 2.2 بروتوكول إنتاج الفيديو (video-production-protocol.md)
<details>
<summary>اضغط لعرض video-production-protocol.md</summary>

```markdown
﻿# Video Production Protocol — v3.0 (Agile Visual-First)

## المرحلة 0: الاستيضاح + تشخيص المشروع (🛑 توقف 1)

اطبع الأسئلة الـ 10 التالية حرفياً وانتظر:
1. الهدف؟ (تحويل/بيع، توعية، تعليم، إطلاق)
2. المنصة والنسبة؟ (9:16 / 16:9 / 1:1)
3. المدة؟ (بالثواني أو نفس مدة الـ VO)
4. المزاج؟ (Cinematic / Energetic / Playful / Technical)
5. ماذا سترفع أنت؟ (VO/فيديوهات/صور/شعار)
6. ما الناقص الذي أجلبه؟
7. ستوك أم موشن جرافيك؟
8. كابشن؟ (كاريوكي دائم / نقاط مفتاحية / بدون)
9. أفاتار أم Faceless؟
10. عناصر إجبارية الظهور؟

المخرج: 00_answers.md
🛑 توقف: انتظر موافقة المستخدم.

---

## المرحلة 1: الخطة الشاملة (🛑 توقف 2)

### 1.1 الأساس
- تحليل الصوت الفعلي عبر `analyze_voiceover` (أول خطوة تقنية دائماً)
- العمود الفقري 4 أسطر (مشاهد واحد، وعد واحد، آلية واحدة، خطوة تالية)
- شخصية الحركة مع `motion_taste_citation` (اقتباس حرفي من `motion-personality.md:رقم_السطر`)

### 1.2 جدول المشاهد الكامل (وصف فقط — لا أسماء ملفات)
لكل مشهد:
- التوقيت (من الـ VO)
- النص الفعلي
- الوصف البصري (ماذا يحدث)
- أنواع الميديا المطلوبة (وصف نصي، ليس أسماء ملفات)
- القالب المقترح (من TEMPLATE_INDEX.md فقط)
- الانتقال

### 1.3 حزمة الميديا الأولية
حدد فقط ما يُستخدم في 3+ مشاهد:
- الخلفيات العامة
- الموسيقى
- المؤثرات المشتركة
- الأيقونات الأساسية (إن وُجدت في 3+ مشاهد)

كل ما عدا ذلك يُجلب عند بناء المشهد المعني.

### 1.4 قائمة القوالب المعتمدة
من `TEMPLATE_INDEX.md` فقط. اسم غير موجود → `VOCAB_REMAP` → إن لم يوجد → توقف واسأل.

المخرج: 01_plan.md
🛑 توقف: انتظر موافقة المستخدم الصريحة.

---

## المرحلة 2: حزمة الميديا الأولية (🛑 توقف 3)

1. مرفوعات المستخدم أولاً → `assets/incoming/`
2. فحص الكاش: `common-tools-mcp:check_cache`
3. جلب الناقص عبر `media-sources-mcp` مباشرة
4. المعالجة (All-Intra للفيديو، -16 LUFS للـ VO، -24 LUFS للـ SFX)
5. الحفظ في الكاش: `common-tools-mcp:save_to_cache`

المخرج: 02_initial_assets.json
🛑 توقف: انتظر موافقة المستخدم على الحزمة الأولية.

---

## المرحلة 3: البناء مشهداً بمشهد (🛑 توقف لكل مشهد)

لكل مشهد N، اتبع الخطوات التالية بالترتيب الصارم:

### الخطوة أ: القراءة الإلزامية قبل المشهد (لا استثناء)
قبل كتابة أي كود أو جلب أي ميديا للمشهد، اقرأ الملفات التالية:
1. `references/deep/motion-taste/director/motion-personality.md` (شخصية الحركة وأرقامها)
2. `references/deep/motion-taste/director/emotion-mapping.md` (الشعور → حركة)
3. `references/deep/motion-taste/director/choreography.md` (تنسيق العناصر)
4. `references/deep/motion-taste/reference/timing-easing-tables.md` (أرقام التوقيت)
5. `reference/ground-truth/TEMPLATE_INDEX.md` (القوالب المعتمدة)
6. أي ملف آخر من `ROUTER.md` §7 (راوتر المعرفة الخاصة) حسب حاجة المشهد

اكتب في خطة المشهد: "تم قراءة الملفات التالية قبل التنفيذ: [قائمة الملفات]"

### الخطوة ب: كتابة خطة المشهد (خطة مفصلة)
لكل مشهد، اكتب خطة تحتوي على:
- شرح المشهد (ماذا يحدث، لماذا، ما الشعور المطلوب)
- القوالب المستخدمة (جدول: القالب / العائلة / الوظيفة)
- الميديا المطلوبة (جدول: الأصل / النوع / المصدر / المسار)
- شخصية الحركة المطبقة (المدة، الـ Easing، الـ Overshoot)
- الدخول والخروج (كيف يدخل كل عنصر، كيف يخرج)
- الانتقال من المشهد السابق

المخرج: `projects/<id>/scenes/scene_N_plan.md`
🛑 توقف: انتظر موافقة المستخدم على خطة المشهد.

### الخطوة ج: جلب ميديا المشهد (إن ناقصة)
1. `check_cache` لكل أصل مطلوب
2. موجود؟ → استخدمه مباشرة
3. غير موجود؟ → اجلبه الآن من `media-sources-mcp` → عالج → `save_to_cache`

### الخطوة د: بناء المشهد
1. `materialize_project.py` للمشهد المعني (أو نقل يدوي للمشهد الواحد)
2. كود من القوالب المعتمدة فقط (صفر ارتجال)
3. تطبيق شخصية الحركة من `motion-personality.md`

### الخطوة هـ: بوابة الوكيل — الفحص البصري (Probe-QC)
1. رندر لقطات ثابتة عند اللحظات الحرجة:
   - أول إطار في المشهد
   - لحظة دخول كل عنصر
   - لحظة الذروة
   - لحظة الكابشن
   - آخر إطار في المشهد
   الأمر: `npx remotion still src/index.ts <Comp> probe_sceneN_XX.png --frame=F`
2. اقرأ كل لقطة وابحث عن:
   - ❌ نص مكسور أو خارج الإطار
   - ❌ عناصر متداخلة
   - ❌ الكابشن غير مقروء
   - ❌ ألوان خاطئة
   - ❌ عنصر يظهر فجأة بدون حركة
3. وُجد خطأ؟ → أصلح → أعد رندر نفس اللقطة → تحقق
4. ما في أخطاء؟ → أنشئ Contact Sheet للمشهد:
   `scripts/verify/contact-sheet.sh contact_sheet_sceneN.png probe_sceneN_*.png`

المخرج: `projects/<id>/scenes/sceneN_qc_report.json`
🛑 توقف: انتظر موافقة المستخدم على المشهد (مع عرض الـ Contact Sheet).

### الخطوة و: الانتقال للمشهد التالي
بعد موافقة المستخدم على المشهد، انتقل للمشهد N+1 وكرر من الخطوة أ.

---

## المرحلة 4: الرندر النهائي + التسليم (🛑 توقف نهائي)

1. بعد موافقة المستخدم على كل المشاهد:
2. أعد الـ Probe-QC الكامل على الفيديو كاملاً (كل المشاهد متتالية)
3. رندر كامل: `npx remotion render src/index.ts <Comp> out/final.mp4 --concurrency=4`
4. QC النهائي: `ffmpeg_qc.py` + `broll_layout_qc.py`
5. التسليم

🛑 ممنوع الرندر قبل موافقة المستخدم الصريحة.
```
</details>

### 2.3 محرك القرار وراوتر العمليات (ROUTER.md)
<details>
<summary>اضغط لعرض ROUTER.md</summary>

```markdown
# ROUTER.md — محرك القرار: متى MCP / متى أداة / متى قالب / متى مرجع
> هذا الملف هو العقل الموجّه. أي مهمة فيديو تمر هنا أولاً قبل أي كود.

## §1 الـ Pipeline العالمي (مستوحى من patterns/index.ts)
Validation (هل الطلب مهمة فيديو؟) → Recipe Match → Skill Detection → Suitability Gate → Build → Verify → QC
1. Validation: إن لم يكن الطلب مهمة فيديو/موشن → لا تُفعّل المهارة.
2. Recipe Match: `python tools/video_recipes.py match --goal "<الهدف>"` إلزامي قبل أي بناء.
3. Skill Detection: حدد المراجع المطلوبة من §7 واقرأها قبل الكود.
4. Suitability Gate: قبل قبول أي أصل: هل اللون يناسب الـ palette؟ هل النبرة تناسب الـ mood؟ هل الأسلوب يطابق باقي العناصر؟ إن لا → استبدله.
5. Build: قوالب من TEMPLATE_INDEX فقط + layer-stack + personality.
6. Verify: scripts/verify/ (seek-shot.sh → contact-sheet.sh → probe-mp4.sh).
7. QC: ffmpeg_qc.py + broll_layout_qc.py + ad_quality_gate.py حسب نوع الفيديو.

## §2 جدول الـ MCPs السبعة (التفاصيل الكاملة: ground-truth/MCP_INDEX.md)
| الخادم | متى يُستخدم (إلزامي) | أبرز الأدوات |
|---|---|---|
| audio-tools-mcp | أول خطوة تقنية عند وجود صوت/VO | analyze_voiceover → timings، detect_and_trim_silence، trim_audio، extend_audio، normalize_loudness (-16 LUFS)، split_voiceover_sentences، build_voiceover_timeline |
| media-sources-mcp | أي أصل حي: stock/أيقونة/SFX/رابط مباشر | pixabay_search_*، pexels_search_*، freesound_search، iconify_search، download_iconify_icon، download_direct_file، change_asset_status |
| video-tools-mcp | قص/تمديد/أبعاد/إطارات سوداء للفيديو | trim_video، extend_video، resize_video، detect_and_trim_black_frames |
| image-tools-mcp | ترقية صور/قص نسب/حذف هوامش | upscale_image، crop_to_ratio، auto_crop_content |
| common-tools-mcp | قبل أي معالجة (check_cache) وبعدها (save_to_cache) | check_cache، save_to_cache |
| ffmpeg-mcp-server | مهام FFmpeg طويلة بالخلفية + حالة/إلغاء/دمج | jobs API |
| Video_Editor_MCP | أوامر FFmpeg حرة فقط إن لم تغطِّها أداة متخصصة | freeform + progress |

### مصفوفة القرار السريع (أي خادم؟ أي أداة أولى؟)
| المهمة | الخادم الإلزامي | الأداة الأولى |
|---|---|---|
| تحليل VO ومواقع الكلمات | audio-tools-mcp | analyze_voiceover |
| جهارة -16 LUFS | audio-tools-mcp | normalize_loudness |
| بحث B-Roll/صور/أيقونات | media-sources-mcp | pexels_search_videos / iconify_search |
| تنزيل SVG ملون | media-sources-mcp | download_iconify_icon |
| قص نسب/ترقية صور | image-tools-mcp | crop_to_ratio / upscale_image |
| أبعاد فيديو/إطارات سوداء | video-tools-mcp | resize_video / detect_and_trim_black_frames |
| فحص معالج مسبقاً | common-tools-mcp | check_cache |
| رندر خلفية/دمج | ffmpeg | concatenate_videos / check_processing_status |
| أمر FFmpeg حر | video-editor | execute_command |
> أمثلة JSON الكاملة: `reference/mcp-toolbook.md` • أولوية المصادر: مرفوع المستخدم → كاش → بوابة (ROUTER §10)

## §3 جدول أدوات Python الـ19 (التفاصيل: ground-truth/TOOLS_INDEX.md)
video_recipes.py (match/plan/validate أولاً) • video_orchestrator.py (دورة حياة الوظيفة) • elevenlabs_voice.py • heygen_client.py • fal_seedance_video.py • image_provider.py • replicate_video.py (احتياطي) • screen_recorder.py + agent_browser_recorder.py • demo_video_composer.py • video_captioner.py • music_provider.py • local_explainer_broll.py • ugc_ad_runner.py • media_pipeline.py (تنسيق دورة حياة الأصول) • ffmpeg_qc.py • broll_layout_qc.py • ad_quality_gate.py + materialize_project.py (بوابة نقل الميديا للبناء — scripts/)

## §4 راوتر نوع الفيديو (الـ17 وصفة كاملة)
| الهدف | الوصفة | المرجع |
|---|---|---|
| شرح SaaS / إطلاق منتج مستمر | living-canvas-explainer | LIVING_CANVAS_PLAYBOOK + cinematic/ENGINE.md |
| مفهوم متعدد المستويات هرمي | tabletop-levels-explainer | TABLETOP_EXPLAINER_PLAYBOOK |
| وثائقي فكري / فكرة واحدة | motion-collage-explainer | MOTION_COLLAGE_STYLE |
| إعلان تحويل بدون متحدث | faceless-broll-ad | ad-spine/ad-creative + platform-specs |
| إعلان UGC صانع محتوى خيالي | ugc-ai-ad | HYPERREALISTIC_IMAGE_SOP |
| مراجعات منافس واقتناص عملاء | review-conquest-compilation | REVIEW_VIDEO_PLAYBOOK |
| إثبات متصفح وتصفح آلي | agent-browser-proof | agent_browser_recorder.py |
| شورت مقال + رأس عائم سريع | misotts-article-sprint | HOOK_PLAYBOOK_ARTICLE_SPRINT |
| شورت إنستغرام مقسوم شاشة | avatar-insta-split | commands/avatar-insta-reel.md |
| هوك أفاتار سيلفي + B-roll | avatar-hook-broll | SEEDANCE_AVATAR_ROI + commands/avatar-vo-reel.md |
| استعراض منتج مع مؤسس/أفاتار | avatar-product-walkthrough | WORKFLOW_EXAMPLES #1 |
| أفاتار إخباري متكامل + إثباتات | avatar-explainer | WORKFLOW_EXAMPLES #10 + SEEDANCE_AVATAR_ROI |
| أفاتار VO فوق B-Roll بالكامل | avatar-vo-broll | commands/avatar-vo-reel.md |
| متحدث موجود + كابشن كاريوكي | captioned-talking-head | remotion/captions + WORKFLOW_EXAMPLES #3 |
| استعراض شاشة تفاعلي SaaS | screencast-demo | demo_video_composer.py |
| موشن جرافيك برمجياً Remotion/HTML | motion-graphics | WORKFLOW_EXAMPLES #4 + REMOTION_VIDEO_GUIDE |
| تقطيع طويل لـ Shorts اجتماعية | longform-repurpose | SPOKEN_VO_HUMANIZER + WORKFLOW_EXAMPLES #5 |

## §5 راوتر الذوق (Mood → Personality)
> **تحذير: لا تربط مجال المنتج بشخصية الحركة.** منتج طبي يمكن أن يكون Cinematic أو Energetic. يجب أخذ مجال المنتج للصياغة، وأخذ الـ Personality للحركة حصراً.

| المزاج | الشخصية | الأرقام |
|---|---|---|
| طبي/فاخر/جاد | Cinematic | 350-600ms، cubic-bezier(0.4,0,0.2,1)، overshoot 0% |
| شبابي/ترويجي سريع | Energetic | 100-250ms، ease-out-expo، 15-30% |
| أطفال/مرح | Playful | 150-300ms، ease-out-back، 10-20% |
| تقني/SaaS دقيق | Technical | 200-400ms، cubic-bezier(0.2,0,0,1)، 0-3% |
اقرأ قبل البناء: motion-taste/director/motion-personality.md + emotion-mapping.md

## §6 راوتر الطبقات الذوقية (Intent → Constraints → Tier → Canonical)

الترتيب الإلزامي عند اختيار أي قالب:

### Tier S — Signature Approved
الأولوية القصوى للمكونات الحديثة، الأجمل، المختبرة، والمعتمدة.
تُستخدم للعناوين، الكابشن، الانتقالات الحديثة، الواجهات، البطاقات، والتأثيرات النصية.
لا يُستخدم أي قالب من طبقة أدنى إذا وُجد قالب Tier S يغطي نفس الـ intent.

### Tier A — Cinematic Engine
يُستخدم عندما يحتاج المشهد إلى كاميرا، مؤشر، نوافذ، عمق، أو كوريغرافيا سينمائية معقدة.
ليس بالضرورة البديل الأول للعناوين البسيطة، لكنه الأول للمشاهد المركبة.

### Tier B — Modern Production Ready
مكونات Onda / RemotionUI / remocn / snapcn / remotion-bits بعد التطبيع والاختبار.
تُستخدم إذا لم يوجد قالب Tier S مناسب، أو إذا كانت المكتبة الحديثة توفر مكوناً أدق.

### Tier C — Legacy 81
الملاذ الأخير فقط.
يُستخدم إذا لم يوجد بديل حديث، أو إذا طلب المستخدم التأثير القديم صراحة.
لا يُستخدم تلقائياً مع وجود بديل حديث مكافئ.

### Tier D — Deprecated / Broken / Duplicate-Loser
لا يُستخدم إلا للفهم أو الاستبدال.
أي قالب هنا يجب أن يكون له `replaced_by` أو سبب واضح للإهمال.

### قواعد الاختيار
1. لا تختار بالاسم فقط. اختر حسب:
   intent + family + constraints + tier + canonical_path.

2. أي مكون نصي عربي يجب أن يكون RTL-Ready.
   مكونات الكود والترمينال تبقى LTR أو تُعامل حسب محتواها.

3. لا تستخدم نسختين من نفس التأثير في نفس المشروع إلا إذا وُجد سبب إبداعي موثق.

4. أي قالب جديد لا يدخل Tier S إلا بعد:
   - تثبيت فعلي
   - تطبيع إن كان نصياً
   - اختبار Probe/Contact Sheet
   - تحديث الفهرس

5. إذا لم يوجد قالب مناسب في كل الطبقات:
   توقف واسأل المستخدم.
   ممنوع كتابة قالب من الصفر.

## §7 راوتر المعرفة الخاصة
3D → patterns/3d.md • شات → patterns/messaging.md • رسوم بيانات → patterns/charts.md • إعدادات spring → patterns/spring-physics.md + REMOTION_VIDEO_GUIDE.md • كابشن → remotion/captions/SKILL.md • كاميرا وعمق → cinematic/ENGINE.md + layer-stack.md • أبعاد منصات → patterns/social-media.md + ad-spine/ad-creative/platform-specs.md • كود جاهز → patterns/examples/
فهرس المكونات السينمائية وpropsها → ground-truth/CINEMATIC_INDEX.md

## §8 بروتوكول التوقف والسؤال
لا قالب مطابق؟ → ركّب قوالب موجودة (layering). فشل التركيب؟ → توقف واسأل المستخدم.
إضافة قالب جديد = مراسم مكتبة: نسخ أقرب قالب + تعديل ثوابته فقط + إعادة تشغيل build_ground_truth.py + ثم الاستخدام. ممنوع كود من الصفر إطلاقاً.

## §9 ربط الدفاتر التشغيلية (Playbooks)
| الدفتر | متى يُقرأ |
|---|---|
| VIDEO_COPY_PLAYBOOK.md | قبل كتابة أي نص/سيناريو |
| SPOKEN_VO_HUMANIZER.md | تحويل نص مكتوب إلى VO منطوق |
| HOOK_PLAYBOOK_ARTICLE_SPRINT.md | صياغة الخطاف (أول 3 ثوانٍ) |
| FFMPEG_PLAYBOOK.md | أي عملية FFmpeg يدوية |
| REMOTION_VIDEO_GUIDE.md | الأرقام الرسمية لفيزياء النوابض والتوقيت |
| LIVING_CANVAS_PLAYBOOK.md | وصفة living-canvas-explainer |
| TABLETOP_EXPLAINER_PLAYBOOK.md | وصفة tabletop-levels-explainer |
| MOTION_COLLAGE_STYLE.md | وصفة motion-collage-explainer |
| HYPERREALISTIC_IMAGE_SOP.md | توليد شخصيات UGC واقعية |
| REVIEW_VIDEO_PLAYBOOK.md | وصفة review-conquest-compilation |
| SEEDANCE_AVATAR_ROI.md | قرارات أفاتار Seedance/HeyGen |
| WORKFLOW_EXAMPLES.md | أمثلة تنفيذية كاملة لخطوط الإنتاج |

## §10 Media Pipeline Law — أولوية المستخدم + بوابة واحدة + معالجة نوعية
1. **مرفوع المستخدم مقدّس**: VO/فيديو/صور مرفوعة = المصدر الرسمي؛ يُمنع جلب بديل لها أو توليد VO بـ `elevenlabs_voice.py`.
2. **الكاش يحكم الطرفين**: `check_cache` قبل أي معالجة؛ `save_to_cache` بعدها (common-tools-mcp).
3. **البوابة للناقص فقط**: `media-sources-mcp` حصراً (pixabay/pexels/freesound/iconify/روابط)؛ ممنوع curl/wget/yt-dlp خارجها.
4. **معالجة نوعية**: صوت→audio-tools-mcp (silence→trim/extend→-16 LUFS؛ ولأي VO: analyze_voiceover→split→manifest→timeline أولاً)؛ صورة→image-tools-mcp؛ فيديو→video-tools-mcp؛ مهام خلفية طويلة→ffmpeg؛ أوامر حرة/تصدير→video-editor. ممنوع ffmpeg طرفي يدوي لما يغطيه خادم.
5. **ملاءمة**: المجلوب يمر Suitability Gate (§1)؛ المرفوع يخضع للفحوص التقنية والمساحات الآمنة فقط.
6. **بروتوكول SFX المعالج:** لكل cue: check_cache → trim_audio(مدة المرئي) → afade out 0.2 → normalize_loudness(-24) → save_to_cache → يُسجل processed_path + volume_db + tone في الـ Blueprint.
7. **التنويع الإلزامي:** نفس ملف المؤثر لا يتكرر خلال 8 ثوانٍ؛ انتقالات متتالية تتناوب بين أصلين مختلفين على الأقل؛ إن ضاقت المكتبة → جلب من freesound_search/pixabay_search_audio عبر بوابة الملاءمة (§1) ومعالجتها وتكاشها.

## §11 بوابة الموافقة (User Approval Gate)
لا استدعاء لأي نموذج مدفوع/توليدي (HeyGen/Seedance/ElevenLabs/OpenAI/Replicate) قبل اعتماد المستخدم خطة مكتوبة تشمل: الوصفة، العمود الفقري 4 أسطر، قائمة الأصول ومصادرها، التوقيتات، والمنصات المستهدفة.

## §12 التعافي والفشل (Deterministic Repair vs Creative Stop)
- إصلاح حتمي مسموح صامتاً: إعادة محاولة، trim، resize، re-normalize، استبدال أصل مكاش بآخر مكاش.
- أي تغيير إبداعي (زاوية، نص، عائلة قوالب، شخصية حركة) → توقف واسأل (§8).
- فشل بوابة QC ثلاث مرات متتالية → تصعيد للمستخدم مع الأدلة (contact-sheet + probe).

## §13 خط الإنتاج المرحلي المقفول (9 مراحل — إلزامي لكل فيديو)
قاعدة عامة: قبل بدء أي مرحلة شغّل `python scripts/stage_gate.py projects/<id> --check <المرحلة>`؛ exit 1 = توقف فوراً.

### المرحلة 0 — الاستيضاح (🛑 توقف 1)
اطبع الأسئلة الـ18 من ملحق (أ) حرفياً وكاملة وانتظر. ممنوع خطة أو كود قبل الأجوبة. المُخرَج: `00_answers.md`.

### المرحلة 1 — الخطة (🛑 توقف 2)
عمود فقري 4 أسطر + `video_recipes.py match --goal` + personality + جدول أصول (مرفوع/مجلوب) + خطة SFX.
يجب أن تتضمن الخطة حقل `motion_taste_citation` يحتوي اقتباساً من `motion-personality.md:رقم_السطر` أو `decision-framework.md:رقم_السطر` يثبت قراءة قيم الشخصية.
المُخرَج: `01_plan.md` + ملف `01_plan.approved` يُكتب فقط بعد موافقتك الصريحة.

### المرحلة 2 — تجميع الميديا
مرفوعات المستخدم تُبتلع أولاً؛ الناقص: check_cache → media-sources-mcp. كل أصل يُسجل في
`02_asset_manifest.json` بهيكل ملحق (ب-2): id، type، source، path/fetch+fallback، processing chain بخوادم MCP النوعية.
🛑 توقف 4 (Assets Review): قبل الانتقال للمرحلة 3، اعرض للمستخدم مسارات جميع الأصول المجلوبة عبر mcp_fetch.
*للمؤثرات الصوتية SFX تحديداً:* يجب تقديم "وصف نصي" مسموع لما سيسمعه المستخدم (مثال: "صوت نقرة معدني حاد 0.3 ثانية").
انتظر الموافقة الصريحة لإنشاء ملف `02b_assets_reviewed.approved`. ممنوع بدء المرحلة 3 بدونه.

### المرحلة 3 — المعالجة والتطبيع (قانون All-Intra)
- كل فيديو (مرفوعاً أو مجلوباً) يُعاد ترميزه All-Intra قبل دخوله Remotion:
  `ffmpeg -y -i IN -c:v libx264 -x264-params keyint=1:scenecut=0 -crf 16 -preset medium -c:a copy OUT`
  (أو `increase_keyframes`) ثم تحقق بـ `get_files_info` أن GOP=1.
  (السبب الموثق: Long GOP يجعل Chromium يفشل في الـ frame-seeking في Remotion → تقطيع وجمود.)
- فيديو أيضاً: detect_and_trim_black_frames → resize_video. صوت: detect_and_trim_silence → normalize_loudness(-16).
  صورة: auto_crop_content → upscale_image → crop_to_ratio.
- مشاهد متتالية من نفس المصدر: تحقق Seamless Cut (آخر فريم ↔ أول فريم).
المُخرَج: `03_preprocess_report.json` — stage_gate يرفض إن لم يكن لكل فيديو `keyframe_mode:"all_intra"` و`gop:1`.

### المرحلة 4 — التوقيتات
`analyze_voiceover` → `04_timings.json` (حتى لو VO مرفوعاً).

### المرحلة 5 — Blueprint (🛑 توقف 3)
JSON ثانية-بثانية بهيكل ملحق (ب) الكامل (عناصر بكل الحقول، taken_from، locks، طبقات، coverage، sfx) +
`validate_blueprint.py --md` → PASS → تقرأ النسخة البشرية → `05_blueprint.approved` بعد موافقتك.
كل cue في sfx يحمل إلزامياً: asset, at_ms, tone, volume_db, processing (§10.6) وإلا رفض validate_blueprint.
ملف حالة القفل: `.blueprint_lock.json` (يُنشأ تلقائياً عند قفل الـ Blueprint عبر `validate_blueprint.py --lock` لمنع خرق القوالب).

### المرحلة 6 — البناء
شغّل `python scripts/materialize_project.py projects/<id>` أولاً (ينقل الميديا والقوالب من المصادر المعتمدة ويكتب media_map.json)؛ ممنوع نسخ ميديا يدوياً؛ ثم كود من الـ Blueprint فقط + `template_lint.py --verify-build`.

### المرحلة 7 — رندر ومعاينة متدرجة
رندر ثوانٍ قليلة → معاينة → contact-sheet → إصلاح. ممنوع رندر كامل قبل معاينة جزئية ناجحة.

### المرحلة 8 — QC والتسليم
ffmpeg_qc + broll_layout_qc + ad_quality_gate + probe-mp4 → `08_qc_report.json`.

### ملحق (أ) — أسئلة الاستيضاح الـ19 (تُطبع كاملة حرفياً)
1. الهدف الواحد؟ (تحويل/بيع، توعية، تعليم، إطلاق)
2. المشاهد الواحد بدقة؟ (شخصية واحدة)
3. المنصة والنسبة؟ (9:16 / 16:9 / 1:1 / متعدد)
4. المدة بالثواني؟ (أو سقف أقصى)
5. الخطوة التالية في النهاية (CTA)؟
6. مجال العمل (Product Domain): ما هو مجال المنتج/الخدمة؟ (لغة النص فقط).
7. المزاج المطلوب (Motion Personality): اختر مزاجاً واحداً (Cinematic, Energetic, Playful, Technical) للحركة.
8. هوية ثابتة؟ (شعار/ألوان/خطوط) أرفقها
9. ممنوعات بصرية؟
10. ماذا سترفع أنت؟ (VO/فيديوهات/صور/شعار) عدّد
11. ما الناقص الذي أجلبه من MCP؟
12. لقطات حقيقية أم ستوك يكفي؟
13. الفويس: تسجيلك / ElevenLabs / بدون؟
14. إن توليد: اللغة وطابع الصوت؟
15. الموسيقى: هادئة/حماسية/بدون؟ + هل تريد SFX؟
16. أفاتار متحدث أم faceless؟
17. كابشن كاريوكي دائم أم نقاط مفتاحية؟
18. عناصر إجبارية الظهور؟ (سعر/عداد/مقارنة/أيقونة)
19. تأكيد: لا استدعاء مدفوع قبل موافقتك على الـ Blueprint؟ (افتراضي: نعم)

### ملحق (ب) — الهيكل الإلزامي لعنصر Blueprint (ب-1) وأصل (ب-2)
(ب-1) عنصر:
{"id","kind":"template|video|image|icon|text|caption|sfx|music","template","asset_ref",
 "props":{...},"start_sec","end_sec","frames":[a,b],
 "lock":{"type":"word","word_index":N} أو {"type":"absolute_ms","ms":X},
 "layout":{"zone","x_pct","y_pct","coverage_pct","layer":1-5},
 "motion":{"enter","exit","easing","duration_ms"},
 "taken_from":"templates/x.tsx | ${PLUGIN_DATA}/assets/sfx/... | cinematic-engine/... | mcp:server/tool",
 "paid":false,"notes"}
(ب-2) أصل:
{"asset_id","type","source":"user_upload|cache|mcp_fetch|generated","path",
 "fetch":{"server","tool","query"},"fallback":{"tool","query"},
 "processing":["...","all_intra"],"covers_sec":[a,b]}

```
</details>

### 2.4 جدول إعادة التوجيه للأسماء (VOCAB_REMAP.md)
<details>
<summary>اضغط لعرض VOCAB_REMAP.md</summary>

```markdown
# VOCAB_REMAP — جدول الأسماء الوهمية → الحقيقية
> قاعدة إلزامية: ممنوع على الـ Agent استيراد أي اسم غير موجود في TEMPLATE_INDEX.md.
> إذا لم يوجد الاسم في الفهرس → ابحث هنا → إن لم يوجد → توقف واسأل المستخدم.

| الاسم الوهمي (محفوظ بالذاكرة) | موجود؟ | البديل الحقيقي (من templates/) |
|---|---|---|
| typewriter-subtitle | ❌ | Captions أو WordStagger (من premium-templates) |
| glitch-text | ❌ | RgbGlitchText (من premium-templates) |
| ken-burns | ❌ | premium-templates/scenes/ken-burns/KenBurns.tsx |
| stat-counter | ❌ | StatCard (من premium-templates) |
| terminal-window | ❌ | Terminal (من premium-templates) |
| code-block | ❌ | CodeBlock (من premium-templates) |
| whip-pan | ❌ | whip-pan (من premium-templates) |
| split-screen | ❌ | SplitScreen (من premium-templates) |
| 3d-card-flip | ❌ | CardStack / Carousel (من premium-templates) |
| kinetic-typography | ❌ | WordStagger / BlurReveal / TrackingIn (من premium-templates) |
| film-grain | ❌ | noise-grain |
| light-leak | ❌ | film-burn |
| gradient-mesh | ❌ | gradient-shift |

## البروتوكول
1. قبل كتابة أي import: افتح TEMPLATE_INDEX.md.
2. الاسم غير موجود؟ ابحث في هذا الجدول واستخدم البديل الحقيقي.
3. غير موجود هنا؟ يُسمح بتركيب قوالب موجودة (layering)؛ يُمنع كتابة قالب جديد من الصفر — توقف واسأل.

```
</details>

### 2.5 فهرس القوالب الحي (TEMPLATE_INDEX.md)
<details>
<summary>اضغط لعرض TEMPLATE_INDEX.md</summary>

```markdown
# TEMPLATE_INDEX — القوالب الحقيقية على القرص (Tiered)
> AUTO-GENERATED by build_ground_truth.py — DO NOT EDIT BY HAND
> Source: `template_catalog.json` | Generated: 2026-08-28T16:26:03 | SHA256: 0a6b3cb873f613ed

**العدد: 149 قالباً**


## 🥇 Tier S — Signature Approved

| File | Tier | Canonical Path | RTL | Status | Replaces | Family |
|---|---|---|---|---|---|---|
| `whip-pan` | S | `templates/whip-pan.tsx` | ❌ | production-ready | — | Unclassified |
| `StatCard` | S | `cinematic-engine/StatCard.tsx` | ✅ | production-ready | — | Unclassified |
| `AudioVisualizer` | S | `premium-templates/AudioVisualizer.tsx` | ❌ | production-ready | — | Unclassified |
| `SocialClip` | S | `premium-templates/SocialClip.tsx` | ❌ | production-ready | — | Unclassified |
| `StatCard` | S | `premium-templates/StatCard.tsx` | ✅ | production-ready | — | Unclassified |
| `whip-pan` | S | `premium-templates/whip-pan.tsx` | ❌ | production-ready | — | Unclassified |
| `CardStack` | S | `premium-templates/CardStack.tsx` | ❌ | production-ready | — | Unclassified |
| `CodeBlock` | S | `premium-templates/CodeBlock.tsx` | ❌ | production-ready | — | Unclassified |
| `CodeDiff` | S | `premium-templates/CodeDiff.tsx` | ❌ | production-ready | — | Unclassified |
| `SplitScreen` | S | `premium-templates/SplitScreen.tsx` | ❌ | production-ready | — | Unclassified |
| `Terminal` | S | `premium-templates/Terminal.tsx` | ❌ | production-ready | — | Unclassified |
| `BlurReveal` | S | `premium-templates/BlurReveal.tsx` | ❌ | production-ready | — | Unclassified |
| `Captions` | S | `premium-templates/Captions.tsx` | ✅ | production-ready | — | Unclassified |
| `RgbGlitchText` | S | `premium-templates/RgbGlitchText.tsx` | ❌ | production-ready | — | Unclassified |
| `Typewriter` | S | `premium-templates/Typewriter.tsx` | ✅ | production-ready | — | Unclassified |
| `glassWipe` | S | `premium-templates/glassWipe.tsx` | ❌ | production-ready | — | Unclassified |
| `KenBurns` | S | `premium-templates/KenBurns.tsx` | ❌ | production-ready | — | Unclassified |

## 🥈 Tier A — Cinematic Engine

| File | Tier | Canonical Path | RTL | Status | Replaces | Family |
|---|---|---|---|---|---|---|
| `CountUp` | A | `cinematic-engine/CountUp.tsx` | ❌ | production-ready | — | Unclassified |
| `EndCard` | A | `cinematic-engine/EndCard.tsx` | ❌ | production-ready | — | Unclassified |
| `Enter` | A | `cinematic-engine/Enter.tsx` | ❌ | production-ready | — | Unclassified |
| `Exit` | A | `cinematic-engine/Exit.tsx` | ❌ | production-ready | — | Unclassified |
| `Headline` | A | `cinematic-engine/Headline.tsx` | ❌ | production-ready | — | Unclassified |
| `Highlight` | A | `cinematic-engine/Highlight.tsx` | ❌ | production-ready | — | Unclassified |
| `Pulse` | A | `cinematic-engine/Pulse.tsx` | ❌ | production-ready | — | Unclassified |
| `ScenePush` | A | `cinematic-engine/ScenePush.tsx` | ❌ | production-ready | — | Unclassified |
| `Stagger` | A | `cinematic-engine/Stagger.tsx` | ❌ | production-ready | — | Unclassified |
| `TrafficLights` | A | `cinematic-engine/TrafficLights.tsx` | ❌ | production-ready | — | Unclassified |
| `TypeWriter` | A | `cinematic-engine/TypeWriter.tsx` | ❌ | production-ready | — | Unclassified |
| `Wallpaper` | A | `cinematic-engine/Wallpaper.tsx` | ❌ | production-ready | — | Unclassified |
| `Window` | A | `cinematic-engine/Window.tsx` | ❌ | production-ready | — | Unclassified |
| `ChaosDesktop` | A | `cinematic-engine/ChaosDesktop.tsx` | ❌ | production-ready | — | Unclassified |
| `Closer` | A | `cinematic-engine/Closer.tsx` | ❌ | production-ready | — | Unclassified |
| `DynamicWindows` | A | `cinematic-engine/DynamicWindows.tsx` | ❌ | production-ready | — | Unclassified |
| `FeatureShowcase` | A | `cinematic-engine/FeatureShowcase.tsx` | ❌ | production-ready | — | Unclassified |
| `HeadlineResolution` | A | `cinematic-engine/HeadlineResolution.tsx` | ❌ | production-ready | — | Unclassified |
| `ProductReveal` | A | `cinematic-engine/ProductReveal.tsx` | ❌ | production-ready | — | Unclassified |
| `AppFromDescriptor` | A | `cinematic-engine/AppFromDescriptor.tsx` | ❌ | production-ready | — | Unclassified |
| `AppShell` | A | `cinematic-engine/AppShell.tsx` | ❌ | production-ready | — | Unclassified |
| `Avatar` | A | `cinematic-engine/Avatar.tsx` | ❌ | production-ready | — | Unclassified |
| `Badge` | A | `cinematic-engine/Badge.tsx` | ❌ | production-ready | — | Unclassified |
| `Button` | A | `cinematic-engine/Button.tsx` | ❌ | production-ready | — | Unclassified |
| `DataTable` | A | `cinematic-engine/DataTable.tsx` | ❌ | production-ready | — | Unclassified |
| `ListItems` | A | `cinematic-engine/ListItems.tsx` | ❌ | production-ready | — | Unclassified |
| `MessageList` | A | `cinematic-engine/MessageList.tsx` | ❌ | production-ready | — | Unclassified |
| `NotificationToast` | A | `cinematic-engine/NotificationToast.tsx` | ❌ | production-ready | — | Unclassified |
| `Panel` | A | `cinematic-engine/Panel.tsx` | ❌ | production-ready | — | Unclassified |
| `PanelGrid` | A | `cinematic-engine/PanelGrid.tsx` | ❌ | production-ready | — | Unclassified |
| `Placeholder` | A | `cinematic-engine/Placeholder.tsx` | ❌ | production-ready | — | Unclassified |
| `SearchBar` | A | `cinematic-engine/SearchBar.tsx` | ❌ | production-ready | — | Unclassified |
| `SidebarNav` | A | `cinematic-engine/SidebarNav.tsx` | ❌ | production-ready | — | Unclassified |
| `TabBar` | A | `cinematic-engine/TabBar.tsx` | ❌ | production-ready | — | Unclassified |
| `TopNav` | A | `cinematic-engine/TopNav.tsx` | ❌ | production-ready | — | Unclassified |
| `AudioManager` | A | `cinematic-engine/AudioManager.tsx` | ❌ | production-ready | — | Unclassified |
| `AutoZoom` | A | `cinematic-engine/AutoZoom.tsx` | ❌ | production-ready | — | Unclassified |
| `CameraRig` | A | `cinematic-engine/CameraRig.tsx` | ❌ | production-ready | — | Unclassified |
| `Cursor` | A | `cinematic-engine/Cursor.tsx` | ❌ | production-ready | — | Unclassified |
| `CursorSprite` | A | `cinematic-engine/CursorSprite.tsx` | ❌ | production-ready | — | Unclassified |
| `LayoutContext` | A | `cinematic-engine/LayoutContext.tsx` | ❌ | production-ready | — | Unclassified |
| `LayoutWindow` | A | `cinematic-engine/LayoutWindow.tsx` | ❌ | production-ready | — | Unclassified |
| `UIStateProvider` | A | `cinematic-engine/UIStateProvider.tsx` | ❌ | production-ready | — | Unclassified |

## 🥉 Tier B — Modern Production Ready

| File | Tier | Canonical Path | RTL | Status | Replaces | Family |
|---|---|---|---|---|---|---|
| `blur-out-up` | B | `premium-templates/blur-out-up.tsx` | ❌ | production-ready | — | Unclassified |
| `caret` | B | `premium-templates/caret.tsx` | ❌ | production-ready | — | Unclassified |
| `typewriter` | B | `premium-templates/typewriter.tsx` | ❌ | production-ready | — | Unclassified |
| `Carousel` | B | `premium-templates/Carousel.tsx` | ❌ | production-ready | — | Unclassified |
| `text-reveal` | B | `premium-templates/text-reveal.tsx` | ❌ | production-ready | — | Unclassified |
| `TrackingIn` | B | `premium-templates/TrackingIn.tsx` | ❌ | production-ready | — | Unclassified |
| `WordStagger` | B | `premium-templates/WordStagger.tsx` | ✅ | production-ready | — | Unclassified |
| `typeMask` | B | `premium-templates/typeMask.tsx` | ❌ | production-ready | — | Unclassified |
| `index` | B | `premium-templates/index.tsx` | ❌ | production-ready | — | Unclassified |

## 🪨 Tier C — Legacy 81

| File | Tier | Canonical Path | RTL | Status | Replaces | Family |
|---|---|---|---|---|---|---|
| `animated-list` | C | `templates/animated-list.tsx` | ❌ | raw | — | Unclassified |
| `animated-text` | C | `templates/animated-text.tsx` | ❌ | raw | — | Unclassified |
| `area-chart` | C | `templates/area-chart.tsx` | ❌ | raw | — | Unclassified |
| `blinds-transition` | C | `templates/blinds-transition.tsx` | ❌ | raw | — | Unclassified |
| `bokeh-circles` | C | `templates/bokeh-circles.tsx` | ❌ | raw | — | Unclassified |
| `bounce-text` | C | `templates/bounce-text.tsx` | ❌ | raw | — | Unclassified |
| `bubble-pop-text` | C | `templates/bubble-pop-text.tsx` | ❌ | raw | — | Unclassified |
| `camera-shake` | C | `templates/camera-shake.tsx` | ❌ | raw | — | Unclassified |
| `card-flip` | C | `templates/card-flip.tsx` | ❌ | raw | — | Unclassified |
| `chapter-title` | C | `templates/chapter-title.tsx` | ❌ | raw | — | Unclassified |
| `chart-animation` | C | `templates/chart-animation.tsx` | ❌ | raw | — | Unclassified |
| `cinematic-title-intro` | C | `templates/cinematic-title-intro.tsx` | ❌ | raw | — | Unclassified |
| `circular-progress` | C | `templates/circular-progress.tsx` | ❌ | raw | — | Unclassified |
| `clock-wipe` | C | `templates/clock-wipe.tsx` | ❌ | raw | — | Unclassified |
| `comparison-chart` | C | `templates/comparison-chart.tsx` | ❌ | raw | — | Unclassified |
| `countdown-intro` | C | `templates/countdown-intro.tsx` | ❌ | raw | — | Unclassified |
| `countdown-timer` | C | `templates/countdown-timer.tsx` | ❌ | raw | — | Unclassified |
| `credits-roll` | C | `templates/credits-roll.tsx` | ❌ | raw | — | Unclassified |
| `cross-dissolve` | C | `templates/cross-dissolve.tsx` | ❌ | raw | — | Unclassified |
| `donut-chart` | C | `templates/donut-chart.tsx` | ❌ | raw | — | Unclassified |
| `end-card` | C | `templates/end-card.tsx` | ❌ | raw | — | Unclassified |
| `fade-through-black` | C | `templates/fade-through-black.tsx` | ❌ | raw | — | Unclassified |
| `film-burn` | C | `templates/film-burn.tsx` | ❌ | raw | — | Unclassified |
| `floating-bubble-text` | C | `templates/floating-bubble-text.tsx` | ❌ | raw | — | Unclassified |
| `gallery-grid` | C | `templates/gallery-grid.tsx` | ❌ | raw | — | Unclassified |
| `geometric-patterns` | C | `templates/geometric-patterns.tsx` | ❌ | raw | — | Unclassified |
| `glitch-text` | C | `templates/glitch-text.tsx` | ❌ | raw | — | Unclassified |
| `gradient-shift` | C | `templates/gradient-shift.tsx` | ❌ | raw | — | Unclassified |
| `grid-pulse` | C | `templates/grid-pulse.tsx` | ❌ | raw | — | Unclassified |
| `image-carousel` | C | `templates/image-carousel.tsx` | ❌ | raw | — | Unclassified |
| `image-comparison-slider` | C | `templates/image-comparison-slider.tsx` | ❌ | raw | — | Unclassified |
| `image-zoom-reveal` | C | `templates/image-zoom-reveal.tsx` | ❌ | raw | — | Unclassified |
| `iris-transition` | C | `templates/iris-transition.tsx` | ❌ | raw | — | Unclassified |
| `ken-burns` | C | `templates/ken-burns.tsx` | ❌ | raw | — | Unclassified |
| `letterbox-reveal` | C | `templates/letterbox-reveal.tsx` | ❌ | raw | — | Unclassified |
| `line-chart` | C | `templates/line-chart.tsx` | ❌ | raw | — | Unclassified |
| `liquid-wave` | C | `templates/liquid-wave.tsx` | ❌ | raw | — | Unclassified |
| `logo-blur-reveal` | C | `templates/logo-blur-reveal.tsx` | ❌ | raw | — | Unclassified |
| `logo-bounce-drop` | C | `templates/logo-bounce-drop.tsx` | ❌ | raw | — | Unclassified |
| `logo-fade-reveal` | C | `templates/logo-fade-reveal.tsx` | ❌ | raw | — | Unclassified |
| `logo-glitch-reveal` | C | `templates/logo-glitch-reveal.tsx` | ❌ | raw | — | Unclassified |
| `logo-scale-rotate` | C | `templates/logo-scale-rotate.tsx` | ❌ | raw | — | Unclassified |
| `logo-spin-reveal` | C | `templates/logo-spin-reveal.tsx` | ❌ | raw | — | Unclassified |
| `logo-split-reveal` | C | `templates/logo-split-reveal.tsx` | ❌ | raw | — | Unclassified |
| `logo-stroke-draw` | C | `templates/logo-stroke-draw.tsx` | ❌ | raw | — | Unclassified |
| `logo-typewriter` | C | `templates/logo-typewriter.tsx` | ❌ | raw | — | Unclassified |
| `lower-third` | C | `templates/lower-third.tsx` | ❌ | raw | — | Unclassified |
| `masonry-gallery` | C | `templates/masonry-gallery.tsx` | ❌ | raw | — | Unclassified |
| `matrix-rain` | C | `templates/matrix-rain.tsx` | ❌ | raw | — | Unclassified |
| `morph-transition` | C | `templates/morph-transition.tsx` | ❌ | raw | — | Unclassified |
| `noise-grain` | C | `templates/noise-grain.tsx` | ❌ | raw | — | Unclassified |
| `notification-pop` | C | `templates/notification-pop.tsx` | ❌ | raw | — | Unclassified |
| `parallax-pan` | C | `templates/parallax-pan.tsx` | ❌ | raw | — | Unclassified |
| `particle-explosion` | C | `templates/particle-explosion.tsx` | ❌ | raw | — | Unclassified |
| `photo-stack` | C | `templates/photo-stack.tsx` | ❌ | raw | — | Unclassified |
| `picture-in-picture` | C | `templates/picture-in-picture.tsx` | ❌ | raw | — | Unclassified |
| `pie-chart` | C | `templates/pie-chart.tsx` | ❌ | raw | — | Unclassified |
| `pixel-transition` | C | `templates/pixel-transition.tsx` | ❌ | raw | — | Unclassified |
| `polaroid-frame` | C | `templates/polaroid-frame.tsx` | ❌ | raw | — | Unclassified |
| `popping-text` | C | `templates/popping-text.tsx` | ❌ | raw | — | Unclassified |
| `progress-bars` | C | `templates/progress-bars.tsx` | ❌ | raw | — | Unclassified |
| `progress-steps` | C | `templates/progress-steps.tsx` | ❌ | raw | — | Unclassified |
| `pulsing-text` | C | `templates/pulsing-text.tsx` | ❌ | raw | — | Unclassified |
| `push-transition` | C | `templates/push-transition.tsx` | ❌ | raw | — | Unclassified |
| `quote-card` | C | `templates/quote-card.tsx` | ❌ | raw | — | Unclassified |
| `rotating-carousel` | C | `templates/rotating-carousel.tsx` | ❌ | raw | — | Unclassified |
| `slide-text` | C | `templates/slide-text.tsx` | ❌ | raw | — | Unclassified |
| `slide-wipe` | C | `templates/slide-wipe.tsx` | ❌ | raw | — | Unclassified |
| `sound-wave` | C | `templates/sound-wave.tsx` | ❌ | raw | — | Unclassified |
| `split-screen` | C | `templates/split-screen.tsx` | ❌ | raw | — | Unclassified |
| `spotlight-reveal` | C | `templates/spotlight-reveal.tsx` | ❌ | raw | — | Unclassified |
| `starfield` | C | `templates/starfield.tsx` | ❌ | raw | — | Unclassified |
| `stat-counter` | C | `templates/stat-counter.tsx` | ❌ | raw | — | Unclassified |
| `subscribe-reminder` | C | `templates/subscribe-reminder.tsx` | ❌ | raw | — | Unclassified |
| `text-highlight` | C | `templates/text-highlight.tsx` | ❌ | raw | — | Unclassified |
| `title-split` | C | `templates/title-split.tsx` | ❌ | raw | — | Unclassified |
| `typewriter-subtitle` | C | `templates/typewriter-subtitle.tsx` | ❌ | raw | — | Unclassified |
| `vignette-pulse` | C | `templates/vignette-pulse.tsx` | ❌ | raw | — | Unclassified |
| `zoom-pulse` | C | `templates/zoom-pulse.tsx` | ❌ | raw | — | Unclassified |
| `zoom-through` | C | `templates/zoom-through.tsx` | ❌ | raw | — | Unclassified |

```
</details>
