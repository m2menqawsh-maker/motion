import React from "react";
import type { TemplateEntry } from "./types";
import { TextReveal } from "../templates/TextReveal";
import { KaraokeCaptions } from "../templates/KaraokeCaptions";
import { LogoAssemble } from "../templates/LogoAssemble";
import { LogoFlicker } from "../templates/LogoFlicker";
import { WordCaptions } from "../templates/WordCaptions";
import { TextHighlight } from "../templates/TextHighlight";
import { AnswerStream } from "../templates/AnswerStream";
import { BlockWordmark } from "../templates/BlockWordmark";
import { Caret } from "../templates/Caret";
import { FollowerRush } from "../templates/FollowerRush";
import { HeroLaunch } from "../templates/HeroLaunch";
import { Input } from "../templates/Input";
import { LaptopFrame } from "../templates/LaptopFrame";
import { MoodboardReveal } from "../templates/MoodboardReveal";
import { OrbitGallery } from "../templates/OrbitGallery";
import { PhoneFrame } from "../templates/PhoneFrame";
import { PromptZoom } from "../templates/PromptZoom";
import { PulsingBorder } from "../templates/PulsingBorder";
import { SearchTyping } from "../templates/SearchTyping";
import { SnapCnUI } from "../templates/SnapCnUI";
import { StatusCycle } from "../templates/StatusCycle";
import { TerminalSimulator } from "../templates/TerminalSimulator";
import { TextBuild } from "../templates/TextBuild";
import { TextSwap } from "../templates/TextSwap";
import { TextSwell } from "../templates/TextSwell";
import { WordFlip } from "../templates/WordFlip";
import { AnnounceTitle } from "../templates/AnnounceTitle";
import { Timeline } from "../templates/Timeline";
import { BoundingBox } from "../templates/BoundingBox";
import { Callout } from "../templates/Callout";
import { ChapterCard } from "../templates/ChapterCard";
import { Confetti } from "../templates/Confetti";
import { DynamicGrid } from "../templates/DynamicGrid";
import { EndCard } from "../templates/EndCard";
import { FadeIn } from "../templates/FadeIn";
import { FadeOut } from "../templates/FadeOut";
import { GradientShift } from "../templates/GradientShift";
import { GrainOverlay } from "../templates/GrainOverlay";
import { Highlight } from "../templates/Highlight";
import { ImageReveal } from "../templates/ImageReveal";
import { AudioClip } from "../templates/AudioClip";
import { BarChart } from "../templates/BarChart";
import { CountUp } from "../templates/CountUp";
import { DrawOn } from "../templates/DrawOn";
import { IconPop } from "../templates/IconPop";
import { LineChart } from "../templates/LineChart";
import { LogoSting } from "../templates/LogoSting";
import { LowerThird } from "../templates/LowerThird";
import { Marquee } from "../templates/Marquee";
import { MaskReveal } from "../templates/MaskReveal";
import { MatrixDecode } from "../templates/MatrixDecode";
import { MeshGradient } from "../templates/MeshGradient";
import { NodeGraph } from "../templates/NodeGraph";
import { Parallax } from "../templates/Parallax";
import { PieReveal } from "../templates/PieReveal";
import { ProgressBar } from "../templates/ProgressBar";
import { QuoteCard } from "../templates/QuoteCard";
import { RotateIn } from "../templates/RotateIn";
import { ScaleIn } from "../templates/ScaleIn";
import { ShimmerSweep } from "../templates/ShimmerSweep";
import { SlideIn } from "../templates/SlideIn";
import { SlideOut } from "../templates/SlideOut";
import { SlotMachineRoll } from "../templates/SlotMachineRoll";
import { Spotlight } from "../templates/Spotlight";
import { SpotlightCard } from "../templates/SpotlightCard";
import { StaggerGroup } from "../templates/StaggerGroup";
import { StatCard } from "../templates/StatCard";
import { TextFadeReplace } from "../templates/TextFadeReplace";
import { TitleCard } from "../templates/TitleCard";
import { Underline } from "../templates/Underline";
import { VideoClip } from "../templates/VideoClip";
import { Vignette } from "../templates/Vignette";
import { WordRotate } from "../templates/WordRotate";
import { BlurReveal } from "../templates/BlurReveal";
import { Captions } from "../templates/Captions";
import { CodeBlock } from "../templates/CodeBlock";
import { CodeDiff } from "../templates/CodeDiff";
import { KenBurns } from "../templates/KenBurns";
import { RgbGlitchText } from "../templates/RgbGlitchText";
import { SplitScreen } from "../templates/SplitScreen";
import { Terminal } from "../templates/Terminal";
import { TrackingIn } from "../templates/TrackingIn";
import { Typewriter } from "../templates/Typewriter";
import { WordStagger } from "../templates/WordStagger";

export const TEMPLATE_REGISTRY: Record<string, TemplateEntry> = {
  "text-reveal": {
    id: "text-reveal",
    label: { ar: "TextReveal", en: "TextReveal" },
    description: { ar: "TextReveal description", en: "TextReveal description" },
    category: "text",
    component: TextReveal,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TextReveal",
      animation: "fade_in"
    }
  },
  "karaoke-captions": {
    id: "karaoke-captions",
    label: { ar: "KaraokeCaptions", en: "KaraokeCaptions" },
    description: { ar: "KaraokeCaptions description", en: "KaraokeCaptions description" },
    category: "text",
    component: KaraokeCaptions,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "KaraokeCaptions",
      animation: "fade_in"
    },
    consumes: ["words"]
  },
  "logo-assemble": {
    id: "logo-assemble",
    label: { ar: "LogoAssemble", en: "LogoAssemble" },
    description: { ar: "LogoAssemble description", en: "LogoAssemble description" },
    category: "text",
    component: LogoAssemble,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "LogoAssemble",
      animation: "fade_in"
    }
  },
  "logo-flicker": {
    id: "logo-flicker",
    label: { ar: "LogoFlicker", en: "LogoFlicker" },
    description: { ar: "LogoFlicker description", en: "LogoFlicker description" },
    category: "text",
    component: LogoFlicker,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "LogoFlicker",
      animation: "fade_in"
    }
  },
  "word-captions": {
    id: "word-captions",
    label: { ar: "WordCaptions", en: "WordCaptions" },
    description: { ar: "WordCaptions description", en: "WordCaptions description" },
    category: "text",
    component: WordCaptions,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "WordCaptions",
      animation: "fade_in"
    },
    consumes: ["words"]
  },
  "text-highlight": {
    id: "text-highlight",
    label: { ar: "TextHighlight", en: "TextHighlight" },
    description: { ar: "TextHighlight description", en: "TextHighlight description" },
    category: "text",
    component: TextHighlight,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TextHighlight",
      animation: "fade_in"
    }
  },
  "answer-stream": {
    id: "answer-stream",
    label: { ar: "AnswerStream", en: "AnswerStream" },
    description: { ar: "AnswerStream description", en: "AnswerStream description" },
    category: "text",
    component: AnswerStream,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "AnswerStream",
      animation: "fade_in"
    },
    consumes: ["lines"]
  },
  "block-wordmark": {
    id: "block-wordmark",
    label: { ar: "BlockWordmark", en: "BlockWordmark" },
    description: { ar: "BlockWordmark description", en: "BlockWordmark description" },
    category: "text",
    component: BlockWordmark,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "BlockWordmark",
      animation: "fade_in"
    }
  },
  "caret": {
    id: "caret",
    label: { ar: "Caret", en: "Caret" },
    description: { ar: "Caret description", en: "Caret description" },
    category: "text",
    component: Caret,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Caret",
      animation: "fade_in"
    }
  },
  "follower-rush": {
    id: "follower-rush",
    label: { ar: "FollowerRush", en: "FollowerRush" },
    description: { ar: "FollowerRush description", en: "FollowerRush description" },
    category: "text",
    component: FollowerRush,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "FollowerRush",
      animation: "fade_in"
    }
  },
  "hero-launch": {
    id: "hero-launch",
    label: { ar: "HeroLaunch", en: "HeroLaunch" },
    description: { ar: "HeroLaunch description", en: "HeroLaunch description" },
    category: "text",
    component: HeroLaunch,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "HeroLaunch",
      animation: "fade_in"
    }
  },
  "input": {
    id: "input",
    label: { ar: "Input", en: "Input" },
    description: { ar: "Input description", en: "Input description" },
    category: "text",
    component: Input,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Input",
      animation: "fade_in"
    }
  },
  "laptop-frame": {
    id: "laptop-frame",
    label: { ar: "LaptopFrame", en: "LaptopFrame" },
    description: { ar: "LaptopFrame description", en: "LaptopFrame description" },
    category: "text",
    component: LaptopFrame,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "LaptopFrame",
      animation: "fade_in"
    },
    consumes: ["screen"]
  },
  "moodboard-reveal": {
    id: "moodboard-reveal",
    label: { ar: "MoodboardReveal", en: "MoodboardReveal" },
    description: { ar: "MoodboardReveal description", en: "MoodboardReveal description" },
    category: "text",
    component: MoodboardReveal,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "MoodboardReveal",
      animation: "fade_in"
    },
    consumes: ["images"]
  },
  "orbit-gallery": {
    id: "orbit-gallery",
    label: { ar: "OrbitGallery", en: "OrbitGallery" },
    description: { ar: "OrbitGallery description", en: "OrbitGallery description" },
    category: "text",
    component: OrbitGallery,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "OrbitGallery",
      animation: "fade_in"
    },
    consumes: ["images"]
  },
  "phone-frame": {
    id: "phone-frame",
    label: { ar: "PhoneFrame", en: "PhoneFrame" },
    description: { ar: "PhoneFrame description", en: "PhoneFrame description" },
    category: "text",
    component: PhoneFrame,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "PhoneFrame",
      animation: "fade_in"
    },
    consumes: ["screen"]
  },
  "prompt-zoom": {
    id: "prompt-zoom",
    label: { ar: "PromptZoom", en: "PromptZoom" },
    description: { ar: "PromptZoom description", en: "PromptZoom description" },
    category: "text",
    component: PromptZoom,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "PromptZoom",
      animation: "fade_in"
    }
  },
  "pulsing-border": {
    id: "pulsing-border",
    label: { ar: "PulsingBorder", en: "PulsingBorder" },
    description: { ar: "PulsingBorder description", en: "PulsingBorder description" },
    category: "text",
    component: PulsingBorder,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "PulsingBorder",
      animation: "fade_in"
    }
  },
  "search-typing": {
    id: "search-typing",
    label: { ar: "SearchTyping", en: "SearchTyping" },
    description: { ar: "SearchTyping description", en: "SearchTyping description" },
    category: "text",
    component: SearchTyping,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "SearchTyping",
      animation: "fade_in"
    }
  },
  "snap-cn-ui": {
    id: "snap-cn-ui",
    label: { ar: "SnapCnUI", en: "SnapCnUI" },
    description: { ar: "SnapCnUI description", en: "SnapCnUI description" },
    category: "text",
    component: SnapCnUI,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "SnapCnUI",
      animation: "fade_in"
    }
  },
  "status-cycle": {
    id: "status-cycle",
    label: { ar: "StatusCycle", en: "StatusCycle" },
    description: { ar: "StatusCycle description", en: "StatusCycle description" },
    category: "text",
    component: StatusCycle,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "StatusCycle",
      animation: "fade_in"
    },
    consumes: ["lines"]
  },
  "terminal-simulator": {
    id: "terminal-simulator",
    label: { ar: "TerminalSimulator", en: "TerminalSimulator" },
    description: { ar: "TerminalSimulator description", en: "TerminalSimulator description" },
    category: "text",
    component: TerminalSimulator,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TerminalSimulator",
      animation: "fade_in"
    },
    consumes: ["lines"]
  },
  "text-build": {
    id: "text-build",
    label: { ar: "TextBuild", en: "TextBuild" },
    description: { ar: "TextBuild description", en: "TextBuild description" },
    category: "text",
    component: TextBuild,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TextBuild",
      animation: "fade_in"
    },
    consumes: ["lines"]
  },
  "text-swap": {
    id: "text-swap",
    label: { ar: "TextSwap", en: "TextSwap" },
    description: { ar: "TextSwap description", en: "TextSwap description" },
    category: "text",
    component: TextSwap,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TextSwap",
      animation: "fade_in"
    }
  },
  "text-swell": {
    id: "text-swell",
    label: { ar: "TextSwell", en: "TextSwell" },
    description: { ar: "TextSwell description", en: "TextSwell description" },
    category: "text",
    component: TextSwell,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TextSwell",
      animation: "fade_in"
    }
  },
  "word-flip": {
    id: "word-flip",
    label: { ar: "WordFlip", en: "WordFlip" },
    description: { ar: "WordFlip description", en: "WordFlip description" },
    category: "text",
    component: WordFlip,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "WordFlip",
      animation: "fade_in"
    }
  },
  "announce-title": {
    id: "announce-title",
    label: { ar: "AnnounceTitle", en: "AnnounceTitle" },
    description: { ar: "AnnounceTitle description", en: "AnnounceTitle description" },
    category: "text",
    component: AnnounceTitle,
    defaultDurationFrames: 90,
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "AnnounceTitle",
      animation: "fade_in"
    }
  },

  "timeline": {
    id: "timeline",
    label: { ar: "الخط الزمني", en: "Timeline" },
    description: { ar: "قالب الخط الزمني", en: "Timeline template" },
    category: "layout",
    component: Timeline,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "A",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Timeline",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/timeline"]
  },

  "bounding-box": {
    id: "bounding-box",
    label: { ar: "BoundingBox", en: "BoundingBox" },
    description: { ar: "قالب BoundingBox", en: "BoundingBox template" },
    category: "layout",
    component: BoundingBox,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "BoundingBox",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/bounding-box"]
  },
  "callout": {
    id: "callout",
    label: { ar: "Callout", en: "Callout" },
    description: { ar: "قالب Callout", en: "Callout template" },
    category: "layout",
    component: Callout,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Callout",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/callout"]
  },
  "chapter-card": {
    id: "chapter-card",
    label: { ar: "ChapterCard", en: "ChapterCard" },
    description: { ar: "قالب ChapterCard", en: "ChapterCard template" },
    category: "text",
    component: ChapterCard,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "ChapterCard",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/chapter-card"]
  },
  "confetti": {
    id: "confetti",
    label: { ar: "Confetti", en: "Confetti" },
    description: { ar: "قالب Confetti", en: "Confetti template" },
    category: "effect",
    component: Confetti,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Confetti",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/confetti"]
  },
  "dynamic-grid": {
    id: "dynamic-grid",
    label: { ar: "DynamicGrid", en: "DynamicGrid" },
    description: { ar: "قالب DynamicGrid", en: "DynamicGrid template" },
    category: "effect",
    component: DynamicGrid,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "DynamicGrid",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/dynamic-grid"]
  },
  "end-card": {
    id: "end-card",
    label: { ar: "EndCard", en: "EndCard" },
    description: { ar: "قالب EndCard", en: "EndCard template" },
    category: "text",
    component: EndCard,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "EndCard",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/end-card"]
  },
  "fade-in": {
    id: "fade-in",
    label: { ar: "FadeIn", en: "FadeIn" },
    description: { ar: "قالب FadeIn", en: "FadeIn template" },
    category: "text",
    component: FadeIn,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "FadeIn",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/fade-in"]
  },
  "fade-out": {
    id: "fade-out",
    label: { ar: "FadeOut", en: "FadeOut" },
    description: { ar: "قالب FadeOut", en: "FadeOut template" },
    category: "text",
    component: FadeOut,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "FadeOut",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/fade-out"]
  },
  "gradient-shift": {
    id: "gradient-shift",
    label: { ar: "GradientShift", en: "GradientShift" },
    description: { ar: "قالب GradientShift", en: "GradientShift template" },
    category: "effect",
    component: GradientShift,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "GradientShift",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/gradient-shift"]
  },
  "grain-overlay": {
    id: "grain-overlay",
    label: { ar: "GrainOverlay", en: "GrainOverlay" },
    description: { ar: "قالب GrainOverlay", en: "GrainOverlay template" },
    category: "effect",
    component: GrainOverlay,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "GrainOverlay",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/grain-overlay"]
  },
  "highlight": {
    id: "highlight",
    label: { ar: "Highlight", en: "Highlight" },
    description: { ar: "قالب Highlight", en: "Highlight template" },
    category: "text",
    component: Highlight,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Highlight",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/highlight"]
  },
  "image-reveal": {
    id: "image-reveal",
    label: { ar: "ImageReveal", en: "ImageReveal" },
    description: { ar: "قالب ImageReveal", en: "ImageReveal template" },
    category: "media",
    component: ImageReveal,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "ImageReveal",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/image-reveal"]
  },

  "audio-clip": {
    id: "audio-clip",
    label: { ar: "AudioClip", en: "AudioClip" },
    description: { ar: "قالب AudioClip", en: "AudioClip template" },
    category: "audio",
    component: AudioClip,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "AudioClip",
      animation: "fade_in"
    },
    usesEffects: ["elements/audio/audio-clip"],
    consumes: ["audioRef"]
  },
  "bar-chart": {
    id: "bar-chart",
    label: { ar: "BarChart", en: "BarChart" },
    description: { ar: "قالب BarChart", en: "BarChart template" },
    category: "data",
    component: BarChart,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "BarChart",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/bar-chart"],
    consumes: ["numbers"]
  },
  "count-up": {
    id: "count-up",
    label: { ar: "CountUp", en: "CountUp" },
    description: { ar: "قالب CountUp", en: "CountUp template" },
    category: "text",
    component: CountUp,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "CountUp",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/count-up"],
    consumes: ["range"]
  },
  "draw-on": {
    id: "draw-on",
    label: { ar: "DrawOn", en: "DrawOn" },
    description: { ar: "قالب DrawOn", en: "DrawOn template" },
    category: "effect",
    component: DrawOn,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "DrawOn",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/draw-on"],
    consumes: ["path"]
  },
  "icon-pop": {
    id: "icon-pop",
    label: { ar: "IconPop", en: "IconPop" },
    description: { ar: "قالب IconPop", en: "IconPop template" },
    category: "effect",
    component: IconPop,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "IconPop",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/icon-pop"],
    consumes: ["icons"]
  },
  "line-chart": {
    id: "line-chart",
    label: { ar: "LineChart", en: "LineChart" },
    description: { ar: "قالب LineChart", en: "LineChart template" },
    category: "data",
    component: LineChart,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "LineChart",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/line-chart"],
    consumes: ["numbers"]
  },
  "logo-sting": {
    id: "logo-sting",
    label: { ar: "LogoSting", en: "LogoSting" },
    description: { ar: "قالب LogoSting", en: "LogoSting template" },
    category: "effect",
    component: LogoSting,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "LogoSting",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/logo-sting"],
    consumes: []
  },
  "lower-third": {
    id: "lower-third",
    label: { ar: "LowerThird", en: "LowerThird" },
    description: { ar: "قالب LowerThird", en: "LowerThird template" },
    category: "effect",
    component: LowerThird,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "LowerThird",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/lower-third"],
    consumes: []
  },
  "marquee": {
    id: "marquee",
    label: { ar: "Marquee", en: "Marquee" },
    description: { ar: "قالب Marquee", en: "Marquee template" },
    category: "effect",
    component: Marquee,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Marquee",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/marquee"],
    consumes: []
  },
  "mask-reveal": {
    id: "mask-reveal",
    label: { ar: "MaskReveal", en: "MaskReveal" },
    description: { ar: "قالب MaskReveal", en: "MaskReveal template" },
    category: "effect",
    component: MaskReveal,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "MaskReveal",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/mask-reveal"],
    consumes: []
  },
  "matrix-decode": {
    id: "matrix-decode",
    label: { ar: "MatrixDecode", en: "MatrixDecode" },
    description: { ar: "قالب MatrixDecode", en: "MatrixDecode template" },
    category: "effect",
    component: MatrixDecode,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "MatrixDecode",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/matrix-decode"],
    consumes: []
  },
  "mesh-gradient": {
    id: "mesh-gradient",
    label: { ar: "MeshGradient", en: "MeshGradient" },
    description: { ar: "قالب MeshGradient", en: "MeshGradient template" },
    category: "effect",
    component: MeshGradient,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "MeshGradient",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/mesh-gradient"],
    consumes: []
  },
  "node-graph": {
    id: "node-graph",
    label: { ar: "NodeGraph", en: "NodeGraph" },
    description: { ar: "قالب NodeGraph", en: "NodeGraph template" },
    category: "effect",
    component: NodeGraph,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "NodeGraph",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/node-graph"],
    consumes: []
  },
  "parallax": {
    id: "parallax",
    label: { ar: "Parallax", en: "Parallax" },
    description: { ar: "قالب Parallax", en: "Parallax template" },
    category: "effect",
    component: Parallax,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Parallax",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/parallax"],
    consumes: []
  },
  "pie-reveal": {
    id: "pie-reveal",
    label: { ar: "PieReveal", en: "PieReveal" },
    description: { ar: "قالب PieReveal", en: "PieReveal template" },
    category: "effect",
    component: PieReveal,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "PieReveal",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/pie-reveal"],
    consumes: []
  },
  "progress-bar": {
    id: "progress-bar",
    label: { ar: "ProgressBar", en: "ProgressBar" },
    description: { ar: "قالب ProgressBar", en: "ProgressBar template" },
    category: "effect",
    component: ProgressBar,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "ProgressBar",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/progress-bar"],
    consumes: []
  },
  "quote-card": {
    id: "quote-card",
    label: { ar: "QuoteCard", en: "QuoteCard" },
    description: { ar: "قالب QuoteCard", en: "QuoteCard template" },
    category: "effect",
    component: QuoteCard,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "QuoteCard",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/quote-card"],
    consumes: []
  },
  "rotate-in": {
    id: "rotate-in",
    label: { ar: "RotateIn", en: "RotateIn" },
    description: { ar: "قالب RotateIn", en: "RotateIn template" },
    category: "effect",
    component: RotateIn,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "RotateIn",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/rotate-in"],
    consumes: []
  },

  "scale-in": {
    id: "scale-in",
    label: { ar: "ScaleIn", en: "ScaleIn" },
    description: { ar: "قالب ScaleIn", en: "ScaleIn template" },
    category: "effect",
    component: ScaleIn,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "ScaleIn",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/scale-in"],
    consumes: []
  },
  "shimmer-sweep": {
    id: "shimmer-sweep",
    label: { ar: "ShimmerSweep", en: "ShimmerSweep" },
    description: { ar: "قالب ShimmerSweep", en: "ShimmerSweep template" },
    category: "effect",
    component: ShimmerSweep,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "ShimmerSweep",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/shimmer-sweep"],
    consumes: []
  },
  "slide-in": {
    id: "slide-in",
    label: { ar: "SlideIn", en: "SlideIn" },
    description: { ar: "قالب SlideIn", en: "SlideIn template" },
    category: "effect",
    component: SlideIn,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "SlideIn",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/slide-in"],
    consumes: []
  },
  "slide-out": {
    id: "slide-out",
    label: { ar: "SlideOut", en: "SlideOut" },
    description: { ar: "قالب SlideOut", en: "SlideOut template" },
    category: "effect",
    component: SlideOut,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "SlideOut",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/slide-out"],
    consumes: []
  },
  "slot-machine-roll": {
    id: "slot-machine-roll",
    label: { ar: "SlotMachineRoll", en: "SlotMachineRoll" },
    description: { ar: "قالب SlotMachineRoll", en: "SlotMachineRoll template" },
    category: "effect",
    component: SlotMachineRoll,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "SlotMachineRoll",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/slot-machine-roll"],
    consumes: []
  },
  "spotlight": {
    id: "spotlight",
    label: { ar: "Spotlight", en: "Spotlight" },
    description: { ar: "قالب Spotlight", en: "Spotlight template" },
    category: "effect",
    component: Spotlight,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Spotlight",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/spotlight"],
    consumes: []
  },
  "spotlight-card": {
    id: "spotlight-card",
    label: { ar: "SpotlightCard", en: "SpotlightCard" },
    description: { ar: "قالب SpotlightCard", en: "SpotlightCard template" },
    category: "effect",
    component: SpotlightCard,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "SpotlightCard",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/spotlight-card"],
    consumes: []
  },
  "stagger-group": {
    id: "stagger-group",
    label: { ar: "StaggerGroup", en: "StaggerGroup" },
    description: { ar: "قالب StaggerGroup", en: "StaggerGroup template" },
    category: "effect",
    component: StaggerGroup,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "StaggerGroup",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/stagger-group"],
    consumes: []
  },
  "stat-card": {
    id: "stat-card",
    label: { ar: "StatCard", en: "StatCard" },
    description: { ar: "قالب StatCard", en: "StatCard template" },
    category: "effect",
    component: StatCard,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "StatCard",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/stat-card"],
    consumes: []
  },
  "text-fade-replace": {
    id: "text-fade-replace",
    label: { ar: "TextFadeReplace", en: "TextFadeReplace" },
    description: { ar: "قالب TextFadeReplace", en: "TextFadeReplace template" },
    category: "effect",
    component: TextFadeReplace,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TextFadeReplace",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/text-fade-replace"],
    consumes: []
  },
  "title-card": {
    id: "title-card",
    label: { ar: "TitleCard", en: "TitleCard" },
    description: { ar: "قالب TitleCard", en: "TitleCard template" },
    category: "effect",
    component: TitleCard,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TitleCard",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/title-card"],
    consumes: []
  },
  "underline": {
    id: "underline",
    label: { ar: "Underline", en: "Underline" },
    description: { ar: "قالب Underline", en: "Underline template" },
    category: "effect",
    component: Underline,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Underline",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/underline"],
    consumes: []
  },
  "video-clip": {
    id: "video-clip",
    label: { ar: "VideoClip", en: "VideoClip" },
    description: { ar: "قالب VideoClip", en: "VideoClip template" },
    category: "effect",
    component: VideoClip,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "VideoClip",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/video-clip"],
    consumes: []
  },
  "vignette": {
    id: "vignette",
    label: { ar: "Vignette", en: "Vignette" },
    description: { ar: "قالب Vignette", en: "Vignette template" },
    category: "effect",
    component: Vignette,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Vignette",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/vignette"],
    consumes: []
  },
  "word-rotate": {
    id: "word-rotate",
    label: { ar: "WordRotate", en: "WordRotate" },
    description: { ar: "قالب WordRotate", en: "WordRotate template" },
    category: "effect",
    component: WordRotate,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "B",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "WordRotate",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/word-rotate"],
    consumes: []
  },
  "blur-reveal": {
    id: "blur-reveal",
    label: { ar: "BlurReveal", en: "BlurReveal" },
    description: { ar: "قالب BlurReveal", en: "BlurReveal template" },
    category: "effect",
    component: BlurReveal,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "BlurReveal",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/blur-reveal"],
    consumes: []
  },
  "captions": {
    id: "captions",
    label: { ar: "Captions", en: "Captions" },
    description: { ar: "قالب Captions", en: "Captions template" },
    category: "effect",
    component: Captions,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Captions",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/captions"],
    consumes: []
  },
  "code-block": {
    id: "code-block",
    label: { ar: "CodeBlock", en: "CodeBlock" },
    description: { ar: "قالب CodeBlock", en: "CodeBlock template" },
    category: "effect",
    component: CodeBlock,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "CodeBlock",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/code-block"],
    consumes: []
  },
  "code-diff": {
    id: "code-diff",
    label: { ar: "CodeDiff", en: "CodeDiff" },
    description: { ar: "قالب CodeDiff", en: "CodeDiff template" },
    category: "effect",
    component: CodeDiff,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "CodeDiff",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/code-diff"],
    consumes: []
  },
  "ken-burns": {
    id: "ken-burns",
    label: { ar: "KenBurns", en: "KenBurns" },
    description: { ar: "قالب KenBurns", en: "KenBurns template" },
    category: "effect",
    component: KenBurns,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "KenBurns",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/ken-burns"],
    consumes: []
  },
  "rgb-glitch-text": {
    id: "rgb-glitch-text",
    label: { ar: "RgbGlitchText", en: "RgbGlitchText" },
    description: { ar: "قالب RgbGlitchText", en: "RgbGlitchText template" },
    category: "effect",
    component: RgbGlitchText,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "RgbGlitchText",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/rgb-glitch-text"],
    consumes: []
  },
  "split-screen": {
    id: "split-screen",
    label: { ar: "SplitScreen", en: "SplitScreen" },
    description: { ar: "قالب SplitScreen", en: "SplitScreen template" },
    category: "effect",
    component: SplitScreen,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "SplitScreen",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/split-screen"],
    consumes: []
  },
  "terminal": {
    id: "terminal",
    label: { ar: "Terminal", en: "Terminal" },
    description: { ar: "قالب Terminal", en: "Terminal template" },
    category: "effect",
    component: Terminal,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Terminal",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/terminal"],
    consumes: []
  },
  "tracking-in": {
    id: "tracking-in",
    label: { ar: "TrackingIn", en: "TrackingIn" },
    description: { ar: "قالب TrackingIn", en: "TrackingIn template" },
    category: "effect",
    component: TrackingIn,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "TrackingIn",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/tracking-in"],
    consumes: []
  },
  "typewriter": {
    id: "typewriter",
    label: { ar: "Typewriter", en: "Typewriter" },
    description: { ar: "قالب Typewriter", en: "Typewriter template" },
    category: "effect",
    component: Typewriter,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "Typewriter",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/typewriter"],
    consumes: []
  },
  "word-stagger": {
    id: "word-stagger",
    label: { ar: "WordStagger", en: "WordStagger" },
    description: { ar: "قالب WordStagger", en: "WordStagger template" },
    category: "effect",
    component: WordStagger,
    defaultDurationFrames: 120,
    origin: "docs",
    tier: "C",
    schema: {
      text: { type: "text", label: { ar: "النص", en: "Text" } }
    },
    defaults: {
      text: "WordStagger",
      animation: "fade_in"
    },
    usesEffects: ["elements/ui/remocn-ui/word-stagger"],
    consumes: []
  },
};
