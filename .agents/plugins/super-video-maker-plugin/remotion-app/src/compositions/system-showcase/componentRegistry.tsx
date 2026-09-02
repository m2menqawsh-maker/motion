import React from "react";
import { staticFile } from "remotion";
import { TemplateMeta } from "./types";
import Comp_0_CameraShake from "@/templates/effects/motion/camera-shake";
import Comp_1_GradientShift from "@/templates/effects/motion/gradient-shift";
import Comp_2_GridPulse from "@/templates/effects/motion/grid-pulse";
import Comp_3_LiquidWave from "@/templates/effects/motion/liquid-wave";
import Comp_4_ParallaxPan from "@/templates/effects/motion/parallax-pan";
import Comp_5_ParticleExplosion from "@/templates/effects/motion/particle-explosion";
import Comp_6_SoundWave from "@/templates/effects/motion/sound-wave";
import Comp_7_ZoomPulse from "@/templates/effects/motion/zoom-pulse";
import Comp_8_BokehCircles from "@/templates/effects/overlays/bokeh-circles";
import Comp_9_FilmBurn from "@/templates/effects/overlays/film-burn";
import Comp_10_GeometricPatterns from "@/templates/effects/overlays/geometric-patterns";
import Comp_11_NoiseGrain from "@/templates/effects/overlays/noise-grain";
import Comp_12_VignettePulse from "@/templates/effects/overlays/vignette-pulse";
import Comp_13_BlindsTransition from "@/templates/effects/transitions/blinds-transition";
import { BlurOutUp as Comp_14_BlurOutUp } from "@/templates/effects/transitions/blur-out-up";
import Comp_15_ClockWipe from "@/templates/effects/transitions/clock-wipe";
import Comp_16_CrossDissolve from "@/templates/effects/transitions/cross-dissolve";
import Comp_17_FadeThroughBlack from "@/templates/effects/transitions/fade-through-black";
import Comp_18_Glasswipe from "@/templates/effects/transitions/glass-wipe/glassWipe";
import Comp_19_IrisTransition from "@/templates/effects/transitions/iris-transition";
import Comp_20_MorphTransition from "@/templates/effects/transitions/morph-transition";
import Comp_21_PixelTransition from "@/templates/effects/transitions/pixel-transition";
import Comp_22_PushTransition from "@/templates/effects/transitions/push-transition";
import Comp_23_SlideWipe from "@/templates/effects/transitions/slide-wipe";
import Comp_24_Typemask from "@/templates/effects/transitions/type-mask/typeMask";
import Comp_25_WhipPan from "@/templates/effects/transitions/whip-pan";
import Comp_26_LogoBlurReveal from "@/templates/elements/branding/logo-blur-reveal";
import Comp_27_LogoBounceDrop from "@/templates/elements/branding/logo-bounce-drop";
import Comp_28_LogoFadeReveal from "@/templates/elements/branding/logo-fade-reveal";
import Comp_29_LogoGlitchReveal from "@/templates/elements/branding/logo-glitch-reveal";
import Comp_30_LogoScaleRotate from "@/templates/elements/branding/logo-scale-rotate";
import Comp_31_LogoSpinReveal from "@/templates/elements/branding/logo-spin-reveal";
import Comp_32_LogoSplitReveal from "@/templates/elements/branding/logo-split-reveal";
import Comp_33_LogoStrokeDraw from "@/templates/elements/branding/logo-stroke-draw";
import Comp_34_LogoTypewriter from "@/templates/elements/branding/logo-typewriter";
import Comp_35_LowerThird from "@/templates/elements/branding/lower-third";
import { Captions as Comp_36_Captions } from "@/templates/elements/captions/captions/Captions";
import Comp_37_TextHighlight from "@/templates/elements/captions/text-highlight";
import Comp_38_TypewriterSubtitle from "@/templates/elements/captions/typewriter-subtitle";
import { CodeBlock as Comp_39_Codeblock } from "@/templates/elements/code/code-block/CodeBlock";
import { CodeDiff as Comp_40_Codediff } from "@/templates/elements/code/code-diff/CodeDiff";
import { Terminal as Comp_41_Terminal } from "@/templates/elements/code/terminal/Terminal";
import Comp_42_AreaChart from "@/templates/elements/data/area-chart";
import Comp_43_Audiovisualizer from "@/templates/elements/data/AudioVisualizer";
import Comp_44_ChartAnimation from "@/templates/elements/data/chart-animation";
import Comp_45_CircularProgress from "@/templates/elements/data/circular-progress";
import Comp_46_ComparisonChart from "@/templates/elements/data/comparison-chart";
import Comp_47_DonutChart from "@/templates/elements/data/donut-chart";
import Comp_48_LineChart from "@/templates/elements/data/line-chart";
import Comp_49_PieChart from "@/templates/elements/data/pie-chart";
import Comp_50_ProgressBars from "@/templates/elements/data/progress-bars";
import Comp_51_ProgressSteps from "@/templates/elements/data/progress-steps";
import Comp_52_StatCounter from "@/templates/elements/data/stat-counter";
import { BlurReveal as Comp_54_Blurreveal } from "@/templates/elements/typography/blur-reveal/BlurReveal";
import Comp_55_BounceText from "@/templates/elements/typography/bounce-text";
import Comp_56_BubblePopText from "@/templates/elements/typography/bubble-pop-text";
import { Caret as Comp_57_Caret } from "@/templates/elements/typography/caret";
import Comp_58_FloatingBubbleText from "@/templates/elements/typography/floating-bubble-text";
import Comp_59_GlitchText from "@/templates/elements/typography/glitch-text";
import Comp_60_PoppingText from "@/templates/elements/typography/popping-text";
import Comp_61_PulsingText from "@/templates/elements/typography/pulsing-text";
import { RgbGlitchText as Comp_62_Rgbglitchtext } from "@/templates/elements/typography/rgb-glitch-text/RgbGlitchText";
import Comp_63_SlideText from "@/templates/elements/typography/slide-text";
import { TEXT_REVEAL_DEFAULTS as Comp_64_TextReveal } from "@/templates/elements/typography/text-reveal";
import Comp_65_TitleSplit from "@/templates/elements/typography/title-split";
import { TrackingIn as Comp_66_Trackingin } from "@/templates/elements/typography/tracking-in/TrackingIn";
import { Typewriter as Comp_67_Typewriter } from "@/templates/elements/typography/typewriter/Typewriter";
import { Typewriter as Comp_68_TypewriterRemocn } from "@/templates/elements/typography/typewriter-remocn";
import { WordStagger as Comp_69_Wordstagger } from "@/templates/elements/typography/word-stagger/WordStagger";
import Comp_70_CardFlip from "@/templates/elements/ui/card-flip";
import Comp_71_LetterboxReveal from "@/templates/elements/ui/letterbox-reveal";
import Comp_72_NotificationPop from "@/templates/elements/ui/notification-pop";
import Comp_73_QuoteCard from "@/templates/elements/ui/quote-card";
import { Component as Comp_79_Cardstack } from "@/templates/elements/ui/remotion-bits/CardStack";
import { Component as Comp_80_Carousel } from "@/templates/elements/ui/remotion-bits/Carousel";
import Comp_81_Splitscreen from "@/templates/elements/ui/split-screen/SplitScreen";
import Comp_82_SpotlightReveal from "@/templates/elements/ui/spotlight-reveal";
import Comp_83_CountdownIntro from "@/templates/scenes/cta/countdown-intro";
import Comp_84_CountdownTimer from "@/templates/scenes/cta/countdown-timer";
import Comp_85_CreditsRoll from "@/templates/scenes/cta/credits-roll";
import Comp_86_EndCard from "@/templates/scenes/cta/end-card";
import Comp_87_SubscribeReminder from "@/templates/scenes/cta/subscribe-reminder";
import Comp_88_AnimatedList from "@/templates/scenes/explainers/animated-list";
import Comp_89_SplitScreen from "@/templates/scenes/explainers/split-screen";
import Comp_90_AnimatedText from "@/templates/scenes/hooks/animated-text";
import Comp_91_ChapterTitle from "@/templates/scenes/hooks/chapter-title";
import Comp_92_CinematicTitleIntro from "@/templates/scenes/hooks/cinematic-title-intro";
import Comp_93_MatrixRain from "@/templates/scenes/hooks/matrix-rain";
import Comp_94_Starfield from "@/templates/scenes/hooks/starfield";
import Comp_95_ZoomThrough from "@/templates/scenes/hooks/zoom-through";
import Comp_96_ImageComparisonSlider from "@/templates/scenes/product/image-comparison-slider";
import Comp_97_ImageZoomReveal from "@/templates/scenes/product/image-zoom-reveal";
import { KenBurns as Comp_98_Kenburns } from "@/templates/scenes/product/ken-burns/KenBurns";
import Comp_99_KenBurns from "@/templates/scenes/product/ken-burns";
import Comp_100_GalleryGrid from "@/templates/scenes/social/gallery-grid";
import Comp_101_ImageCarousel from "@/templates/scenes/social/image-carousel";
import Comp_102_MasonryGallery from "@/templates/scenes/social/masonry-gallery";
import Comp_103_PhotoStack from "@/templates/scenes/social/photo-stack";
import Comp_104_PictureInPicture from "@/templates/scenes/social/picture-in-picture";
import Comp_105_PolaroidFrame from "@/templates/scenes/social/polaroid-frame";
import Comp_106_RotatingCarousel from "@/templates/scenes/social/rotating-carousel";
import { SocialClip as Comp_107_Index } from "@/templates/scenes/social/social-clip/index";
import { SocialClip as Comp_108_Socialclip } from "@/templates/scenes/social/SocialClip";

// Complete bulletproof props providing all required array & object shapes
export const MOCK_PROPS: Record<string, any> = {
  // Text & Typography
  text: "BUILD SOMETHING GREAT",
  title: "Clean Video Pipeline",
  subtitle: "هذا نص عربي تجريبي داخل المحرك",
  name: "Alex Rivera",
  role: "Lead Motion Architect",
  channelName: "Antigravity Studio",
  buttonText: "Explore Platform",
  tag: "v3.0 Release",
  badge: "Verified",
  caption: "Next-generation video synthesis",
  
  // Word & Line Arrays
  words: ["Next-Gen", "Video", "Synthesis", "In", "Action"],
  lines: [
    "Clean Video Architecture",
    "High-Performance Remotion",
    "Commercial Motion Design"
  ],
  items: ["Fast Timeline", "172+ Templates", "Cinematic Engine", "Arabic RTL Ready"],
  
  // Captions & Subtitles Data Structure
  captions: [
    { text: "Next-gen", startMs: 0, endMs: 800 },
    { text: "video", startMs: 800, endMs: 1400 },
    { text: "pipeline", startMs: 1400, endMs: 2200 },
    { text: "in", startMs: 2200, endMs: 2600 },
    { text: "action", startMs: 2600, endMs: 3500 },
    { text: "تكامل", startMs: 3500, endMs: 4200 },
    { text: "عربي", startMs: 4200, endMs: 4800 },
    { text: "كامل", startMs: 4800, endMs: 5500 }
  ],
  subtitles: [
    { text: "Next-gen video pipeline in action", startFrame: 0, endFrame: 60 }
  ],
  
  // Code & Terminal Props
  code: "export const pipeline = 'Clean Video Workspace';\nconsole.log(pipeline);",
  oldCode: "const legacy = true;",
  newCode: "export const pipeline = 'Clean Video Workspace';",
  command: "npx remotion studio",
  prompt: "antigravity-ide:~$",
  output: [
    "npm run studio",
    "Compiled 172 templates",
    "Live preview ready at localhost:3000"
  ],
  chrome: true,
  revealLines: true,
  cursor: true,
  
  // Data & Charts Arrays
  data: [
    { label: "Q1", value: 40 },
    { label: "Q2", value: 65 },
    { label: "Q3", value: 85 },
    { label: "Q4", value: 95 }
  ],
  segments: [
    { label: "Rendering", value: 45, color: "#38bdf8" },
    { label: "Motion", value: 30, color: "#a855f7" },
    { label: "Audio", value: 25, color: "#10b981" }
  ],
  skills: [
    { name: "Animation", level: 90 },
    { name: "Timeline", level: 85 },
    { name: "Design", level: 95 }
  ],
  steps: [
    { title: "Planning", desc: "Storyboard & assets" },
    { title: "Animation", desc: "Remotion timeline" },
    { title: "Delivery", desc: "Studio preview" }
  ],
  values: [40, 65, 85, 45, 95, 75, 100],
  labels: ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"],
  count: 5,
  progress: 78,
  leftTitle: "Legacy Workflow",
  rightTitle: "AI Directed Motion",
  
  // Cards & Social UI Arrays
  cards: [
    { title: "Motion Layer", desc: "Full canvas animation coverage" },
    { title: "Transitions", desc: "13 seamless GL & blur cuts" },
    { title: "Audio Engine", desc: "Frame-accurate SFX and VO sync" }
  ],
  notifications: [
    { title: "System Ready", message: "Showcase compiled successfully", time: "Just now" }
  ],
  credits: [
    { role: "Director", name: "AI Motion Orchestrator" },
    { role: "Engine", name: "Remotion 4" },
    { role: "Workspace", name: "Clean Video Workspace" }
  ],
  photos: [
    staticFile("media/video/coding_keyboard.mp4"),
    staticFile("media/video/bg_ai_final.mp4"),
    staticFile("media/video/bg_code_final.mp4")
  ],
  slides: [
    { title: "Visual Engine", image: staticFile("media/video/coding_keyboard.mp4") },
    { title: "Cyber Canvas", image: staticFile("media/video/bg_ai_final.mp4") }
  ],
  
  // Timing & Geometry
  delay: 0,
  duration: 30,
  durationInFrames: 60,
  holdFrames: 10,
  stagger: 0.1,
  lineDelay: 6,
  typeSpeed: 2,
  glitchDuration: 15,
  glitchPeriod: 45,
  width: "100%",
  height: "100%",
  placement: "center",
  align: "center",
  justify: "center",
  gap: 16,
  ratio: 0.5,
  baseSplit: 50,
  fromScale: 0.8,
  toScale: 1,
  fromTracking: 10,
  tracking: 0,
  fromX: -50,
  toX: 0,
  fromY: 30,
  toY: 0,
  
  // Styling Colors
  fontSize: 44,
  fontWeight: 800,
  fontFamily: "'Inter', sans-serif",
  lineHeight: 1.2,
  letterSpacing: "-0.5px",
  textColor: "#ffffff",
  color: "#ffffff",
  accentColor: "#38bdf8",
  promptColor: "#a855f7",
  commandColor: "#38bdf8",
  outputColor: "#94a3b8",
  keywordColor: "#f43f5e",
  stringColor: "#10b981",
  commentColor: "#64748b",
  numberColor: "#fbbf24",
  tagColor: "#38bdf8",
  
  // Media Paths
  src: staticFile("media/video/coding_keyboard.mp4"),
  beforeImage: staticFile("media/video/coding_keyboard.mp4"),
  afterImage: staticFile("media/video/bg_ai_final.mp4"),
  image: staticFile("media/video/bg_ai_final.mp4"),
  images: [
    staticFile("media/video/coding_keyboard.mp4"),
    staticFile("media/video/bg_ai_final.mp4")
  ],
};

export function renderLiveComponent(meta: TemplateMeta): React.ReactNode {
  try {
    switch (meta.id) {
      case "effects/motion/camera-shake": {
        const Component = Comp_0_CameraShake as any;
        return (
          <div key="effects/motion/camera-shake" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/motion/gradient-shift": {
        const Component = Comp_1_GradientShift as any;
        return (
          <div key="effects/motion/gradient-shift" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/motion/grid-pulse": {
        const Component = Comp_2_GridPulse as any;
        return (
          <div key="effects/motion/grid-pulse" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/motion/liquid-wave": {
        const Component = Comp_3_LiquidWave as any;
        return (
          <div key="effects/motion/liquid-wave" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/motion/parallax-pan": {
        const Component = Comp_4_ParallaxPan as any;
        return (
          <div key="effects/motion/parallax-pan" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/motion/particle-explosion": {
        const Component = Comp_5_ParticleExplosion as any;
        return (
          <div key="effects/motion/particle-explosion" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/motion/sound-wave": {
        const Component = Comp_6_SoundWave as any;
        return (
          <div key="effects/motion/sound-wave" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/motion/zoom-pulse": {
        const Component = Comp_7_ZoomPulse as any;
        return (
          <div key="effects/motion/zoom-pulse" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/overlays/bokeh-circles": {
        const Component = Comp_8_BokehCircles as any;
        return (
          <div key="effects/overlays/bokeh-circles" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/overlays/film-burn": {
        const Component = Comp_9_FilmBurn as any;
        return (
          <div key="effects/overlays/film-burn" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/overlays/geometric-patterns": {
        const Component = Comp_10_GeometricPatterns as any;
        return (
          <div key="effects/overlays/geometric-patterns" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/overlays/noise-grain": {
        const Component = Comp_11_NoiseGrain as any;
        return (
          <div key="effects/overlays/noise-grain" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/overlays/vignette-pulse": {
        const Component = Comp_12_VignettePulse as any;
        return (
          <div key="effects/overlays/vignette-pulse" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/blinds-transition": {
        const Component = Comp_13_BlindsTransition as any;
        return (
          <div key="effects/transitions/blinds-transition" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/blur-out-up": {
        const Component = Comp_14_BlurOutUp as any;
        return (
          <div key="effects/transitions/blur-out-up" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/clock-wipe": {
        const Component = Comp_15_ClockWipe as any;
        return (
          <div key="effects/transitions/clock-wipe" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/cross-dissolve": {
        const Component = Comp_16_CrossDissolve as any;
        return (
          <div key="effects/transitions/cross-dissolve" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/fade-through-black": {
        const Component = Comp_17_FadeThroughBlack as any;
        return (
          <div key="effects/transitions/fade-through-black" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/glass-wipe/glassWipe": {
        const Component = Comp_18_Glasswipe as any;
        return (
          <div key="effects/transitions/glass-wipe/glassWipe" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/iris-transition": {
        const Component = Comp_19_IrisTransition as any;
        return (
          <div key="effects/transitions/iris-transition" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/morph-transition": {
        const Component = Comp_20_MorphTransition as any;
        return (
          <div key="effects/transitions/morph-transition" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/pixel-transition": {
        const Component = Comp_21_PixelTransition as any;
        return (
          <div key="effects/transitions/pixel-transition" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/push-transition": {
        const Component = Comp_22_PushTransition as any;
        return (
          <div key="effects/transitions/push-transition" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/slide-wipe": {
        const Component = Comp_23_SlideWipe as any;
        return (
          <div key="effects/transitions/slide-wipe" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/type-mask/typeMask": {
        const Component = Comp_24_Typemask as any;
        return (
          <div key="effects/transitions/type-mask/typeMask" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "effects/transitions/whip-pan": {
        const Component = Comp_25_WhipPan as any;
        return (
          <div key="effects/transitions/whip-pan" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-blur-reveal": {
        const Component = Comp_26_LogoBlurReveal as any;
        return (
          <div key="elements/branding/logo-blur-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-bounce-drop": {
        const Component = Comp_27_LogoBounceDrop as any;
        return (
          <div key="elements/branding/logo-bounce-drop" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-fade-reveal": {
        const Component = Comp_28_LogoFadeReveal as any;
        return (
          <div key="elements/branding/logo-fade-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-glitch-reveal": {
        const Component = Comp_29_LogoGlitchReveal as any;
        return (
          <div key="elements/branding/logo-glitch-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-scale-rotate": {
        const Component = Comp_30_LogoScaleRotate as any;
        return (
          <div key="elements/branding/logo-scale-rotate" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-spin-reveal": {
        const Component = Comp_31_LogoSpinReveal as any;
        return (
          <div key="elements/branding/logo-spin-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-split-reveal": {
        const Component = Comp_32_LogoSplitReveal as any;
        return (
          <div key="elements/branding/logo-split-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-stroke-draw": {
        const Component = Comp_33_LogoStrokeDraw as any;
        return (
          <div key="elements/branding/logo-stroke-draw" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/logo-typewriter": {
        const Component = Comp_34_LogoTypewriter as any;
        return (
          <div key="elements/branding/logo-typewriter" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/branding/lower-third": {
        const Component = Comp_35_LowerThird as any;
        return (
          <div key="elements/branding/lower-third" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/captions/captions/Captions": {
        const Component = Comp_36_Captions as any;
        return (
          <div key="elements/captions/captions/Captions" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/captions/text-highlight": {
        const Component = Comp_37_TextHighlight as any;
        return (
          <div key="elements/captions/text-highlight" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/captions/typewriter-subtitle": {
        const Component = Comp_38_TypewriterSubtitle as any;
        return (
          <div key="elements/captions/typewriter-subtitle" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/code/code-block/CodeBlock": {
        const Component = Comp_39_Codeblock as any;
        return (
          <div key="elements/code/code-block/CodeBlock" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/code/code-diff/CodeDiff": {
        const Component = Comp_40_Codediff as any;
        return (
          <div key="elements/code/code-diff/CodeDiff" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/code/terminal/Terminal": {
        const Component = Comp_41_Terminal as any;
        return (
          <div key="elements/code/terminal/Terminal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/area-chart": {
        const Component = Comp_42_AreaChart as any;
        return (
          <div key="elements/data/area-chart" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/AudioVisualizer": {
        const Component = Comp_43_Audiovisualizer as any;
        return (
          <div key="elements/data/AudioVisualizer" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/chart-animation": {
        const Component = Comp_44_ChartAnimation as any;
        return (
          <div key="elements/data/chart-animation" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/circular-progress": {
        const Component = Comp_45_CircularProgress as any;
        return (
          <div key="elements/data/circular-progress" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/comparison-chart": {
        const Component = Comp_46_ComparisonChart as any;
        return (
          <div key="elements/data/comparison-chart" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/donut-chart": {
        const Component = Comp_47_DonutChart as any;
        return (
          <div key="elements/data/donut-chart" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/line-chart": {
        const Component = Comp_48_LineChart as any;
        return (
          <div key="elements/data/line-chart" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/pie-chart": {
        const Component = Comp_49_PieChart as any;
        return (
          <div key="elements/data/pie-chart" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/progress-bars": {
        const Component = Comp_50_ProgressBars as any;
        return (
          <div key="elements/data/progress-bars" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/progress-steps": {
        const Component = Comp_51_ProgressSteps as any;
        return (
          <div key="elements/data/progress-steps" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/data/stat-counter": {
        const Component = Comp_52_StatCounter as any;
        return (
          <div key="elements/data/stat-counter" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/blur-reveal/BlurReveal": {
        const Component = Comp_54_Blurreveal as any;
        return (
          <div key="elements/typography/blur-reveal/BlurReveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/bounce-text": {
        const Component = Comp_55_BounceText as any;
        return (
          <div key="elements/typography/bounce-text" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/bubble-pop-text": {
        const Component = Comp_56_BubblePopText as any;
        return (
          <div key="elements/typography/bubble-pop-text" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/caret": {
        const Component = Comp_57_Caret as any;
        return (
          <div key="elements/typography/caret" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/floating-bubble-text": {
        const Component = Comp_58_FloatingBubbleText as any;
        return (
          <div key="elements/typography/floating-bubble-text" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/glitch-text": {
        const Component = Comp_59_GlitchText as any;
        return (
          <div key="elements/typography/glitch-text" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/popping-text": {
        const Component = Comp_60_PoppingText as any;
        return (
          <div key="elements/typography/popping-text" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/pulsing-text": {
        const Component = Comp_61_PulsingText as any;
        return (
          <div key="elements/typography/pulsing-text" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/rgb-glitch-text/RgbGlitchText": {
        const Component = Comp_62_Rgbglitchtext as any;
        return (
          <div key="elements/typography/rgb-glitch-text/RgbGlitchText" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/slide-text": {
        const Component = Comp_63_SlideText as any;
        return (
          <div key="elements/typography/slide-text" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/text-reveal": {
        const Component = Comp_64_TextReveal as any;
        return (
          <div key="elements/typography/text-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/title-split": {
        const Component = Comp_65_TitleSplit as any;
        return (
          <div key="elements/typography/title-split" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/tracking-in/TrackingIn": {
        const Component = Comp_66_Trackingin as any;
        return (
          <div key="elements/typography/tracking-in/TrackingIn" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/typewriter/Typewriter": {
        const Component = Comp_67_Typewriter as any;
        return (
          <div key="elements/typography/typewriter/Typewriter" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/typewriter-remocn": {
        const Component = Comp_68_TypewriterRemocn as any;
        return (
          <div key="elements/typography/typewriter-remocn" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/typography/word-stagger/WordStagger": {
        const Component = Comp_69_Wordstagger as any;
        return (
          <div key="elements/typography/word-stagger/WordStagger" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/ui/card-flip": {
        const Component = Comp_70_CardFlip as any;
        return (
          <div key="elements/ui/card-flip" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/ui/letterbox-reveal": {
        const Component = Comp_71_LetterboxReveal as any;
        return (
          <div key="elements/ui/letterbox-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/ui/notification-pop": {
        const Component = Comp_72_NotificationPop as any;
        return (
          <div key="elements/ui/notification-pop" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/ui/quote-card": {
        const Component = Comp_73_QuoteCard as any;
        return (
          <div key="elements/ui/quote-card" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/ui/remotion-bits/CardStack": {
        const Component = Comp_79_Cardstack as any;
        return (
          <div key="elements/ui/remotion-bits/CardStack" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/ui/remotion-bits/Carousel": {
        const Component = Comp_80_Carousel as any;
        return (
          <div key="elements/ui/remotion-bits/Carousel" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/ui/split-screen/SplitScreen": {
        const Component = Comp_81_Splitscreen as any;
        return (
          <div key="elements/ui/split-screen/SplitScreen" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "elements/ui/spotlight-reveal": {
        const Component = Comp_82_SpotlightReveal as any;
        return (
          <div key="elements/ui/spotlight-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/cta/countdown-intro": {
        const Component = Comp_83_CountdownIntro as any;
        return (
          <div key="scenes/cta/countdown-intro" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/cta/countdown-timer": {
        const Component = Comp_84_CountdownTimer as any;
        return (
          <div key="scenes/cta/countdown-timer" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/cta/credits-roll": {
        const Component = Comp_85_CreditsRoll as any;
        return (
          <div key="scenes/cta/credits-roll" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/cta/end-card": {
        const Component = Comp_86_EndCard as any;
        return (
          <div key="scenes/cta/end-card" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/cta/subscribe-reminder": {
        const Component = Comp_87_SubscribeReminder as any;
        return (
          <div key="scenes/cta/subscribe-reminder" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/explainers/animated-list": {
        const Component = Comp_88_AnimatedList as any;
        return (
          <div key="scenes/explainers/animated-list" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/explainers/split-screen": {
        const Component = Comp_89_SplitScreen as any;
        return (
          <div key="scenes/explainers/split-screen" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/hooks/animated-text": {
        const Component = Comp_90_AnimatedText as any;
        return (
          <div key="scenes/hooks/animated-text" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/hooks/chapter-title": {
        const Component = Comp_91_ChapterTitle as any;
        return (
          <div key="scenes/hooks/chapter-title" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/hooks/cinematic-title-intro": {
        const Component = Comp_92_CinematicTitleIntro as any;
        return (
          <div key="scenes/hooks/cinematic-title-intro" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/hooks/matrix-rain": {
        const Component = Comp_93_MatrixRain as any;
        return (
          <div key="scenes/hooks/matrix-rain" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/hooks/starfield": {
        const Component = Comp_94_Starfield as any;
        return (
          <div key="scenes/hooks/starfield" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/hooks/zoom-through": {
        const Component = Comp_95_ZoomThrough as any;
        return (
          <div key="scenes/hooks/zoom-through" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/product/image-comparison-slider": {
        const Component = Comp_96_ImageComparisonSlider as any;
        return (
          <div key="scenes/product/image-comparison-slider" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/product/image-zoom-reveal": {
        const Component = Comp_97_ImageZoomReveal as any;
        return (
          <div key="scenes/product/image-zoom-reveal" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/product/ken-burns/KenBurns": {
        const Component = Comp_98_Kenburns as any;
        return (
          <div key="scenes/product/ken-burns/KenBurns" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/product/ken-burns": {
        const Component = Comp_99_KenBurns as any;
        return (
          <div key="scenes/product/ken-burns" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/gallery-grid": {
        const Component = Comp_100_GalleryGrid as any;
        return (
          <div key="scenes/social/gallery-grid" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/image-carousel": {
        const Component = Comp_101_ImageCarousel as any;
        return (
          <div key="scenes/social/image-carousel" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/masonry-gallery": {
        const Component = Comp_102_MasonryGallery as any;
        return (
          <div key="scenes/social/masonry-gallery" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/photo-stack": {
        const Component = Comp_103_PhotoStack as any;
        return (
          <div key="scenes/social/photo-stack" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/picture-in-picture": {
        const Component = Comp_104_PictureInPicture as any;
        return (
          <div key="scenes/social/picture-in-picture" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/polaroid-frame": {
        const Component = Comp_105_PolaroidFrame as any;
        return (
          <div key="scenes/social/polaroid-frame" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/rotating-carousel": {
        const Component = Comp_106_RotatingCarousel as any;
        return (
          <div key="scenes/social/rotating-carousel" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/social-clip/index": {
        const Component = Comp_107_Index as any;
        return (
          <div key="scenes/social/social-clip/index" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      case "scenes/social/SocialClip": {
        const Component = Comp_108_Socialclip as any;
        return (
          <div key="scenes/social/SocialClip" style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", position: "relative" }}>
            <Component {...MOCK_PROPS} />
          </div>
        );
      }
      default:
        return null;
    }
  } catch (err) {
    console.warn(`[LiveComponent] Error rendering ${meta.name}:`, err);
    return null;
  }
}
