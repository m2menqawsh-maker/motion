import type { TemplateEntry } from "./types";
import { FadeTransition } from "../templates/effects/FadeTransition";
import { SlideTransition } from "../templates/effects/SlideTransition";
import { WipeTransition } from "../templates/effects/WipeTransition";
import { ClockWipeTransition } from "../templates/effects/ClockWipeTransition";
import { FlipTransition } from "../templates/effects/FlipTransition";
import { CrossZoomTransition } from "../templates/effects/CrossZoomTransition";
import { CrosswarpTransition } from "../templates/effects/CrosswarpTransition";
import { DissolveTransition } from "../templates/effects/DissolveTransition";
import { DreamyZoomTransition } from "../templates/effects/DreamyZoomTransition";
import { FilmBurnTransition } from "../templates/effects/FilmBurnTransition";
import { IrisTransition } from "../templates/effects/IrisTransition";
import { LinearBlurTransition } from "../templates/effects/LinearBlurTransition";
import { PushCutTransition } from "../templates/effects/PushCutTransition";
import { RippleTransition } from "../templates/effects/RippleTransition";
import { SwapTransition } from "../templates/effects/SwapTransition";
import { ZoomBlurTransition } from "../templates/effects/ZoomBlurTransition";
import { ZoomInOutTransition } from "../templates/effects/ZoomInOutTransition";
import { BookFlipTransition } from "../templates/effects/BookFlipTransition";
import { AnimatedTextWrapper } from "../templates/elements/AnimatedTextWrapper";
import { TypeWriterWrapper } from "../templates/elements/TypeWriterWrapper";
import { CodeBlockWrapper } from "../templates/elements/CodeBlockWrapper";
import { MatrixRainWrapper } from "../templates/elements/MatrixRainWrapper";
import { AnimatedCounterWrapper } from "../templates/elements/AnimatedCounterWrapper";
import { ScrollingImagesWrapper } from "../templates/elements/ScrollingImagesWrapper";
import { ParticleSystemWrapper } from "../templates/elements/ParticleSystemWrapper";
import { Scene3DWrapper } from "../templates/elements/Scene3DWrapper";
import { StaggeredMotionWrapper } from "../templates/elements/StaggeredMotionWrapper";
import { GradientWrapper } from "../templates/elements/GradientWrapper";

export const TEMPLATE_REGISTRY: Record<string, TemplateEntry> = {
  "fade-transition": {
    id: "fade-transition",
    label: { ar: "تلاشي", en: "Fade" },
    description: { ar: "تلاشي سلس", en: "Smooth fade" },
    category: "effect",
    component: FadeTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "slide-transition": {
    id: "slide-transition",
    label: { ar: "انزلاق", en: "Slide" },
    description: { ar: "انزلاق المشهد", en: "Slide transition" },
    category: "effect",
    component: SlideTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "wipe-transition": {
    id: "wipe-transition",
    label: { ar: "مسح", en: "Wipe" },
    description: { ar: "مسح المشهد", en: "Wipe transition" },
    category: "effect",
    component: WipeTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "clock-wipe-transition": {
    id: "clock-wipe-transition",
    label: { ar: "مسح دائري", en: "Clock Wipe" },
    description: { ar: "مسح بشكل عقارب الساعة", en: "Clock wipe transition" },
    category: "effect",
    component: ClockWipeTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "flip-transition": {
    id: "flip-transition",
    label: { ar: "انقلاب", en: "Flip" },
    description: { ar: "انقلاب 3D", en: "3D Flip transition" },
    category: "effect",
    component: FlipTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "cross-zoom-transition": {
    id: "cross-zoom-transition",
    label: { ar: "تقريب متداخل", en: "Cross Zoom" },
    description: { ar: "تقريب متداخل وحركي", en: "Cross zoom transition" },
    category: "effect",
    component: CrossZoomTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "crosswarp-transition": {
    id: "crosswarp-transition",
    label: { ar: "تداخل لولبي", en: "Cross Warp" },
    description: { ar: "تداخل بتشويه لولبي", en: "Cross warp transition" },
    category: "effect",
    component: CrosswarpTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "dissolve-transition": {
    id: "dissolve-transition",
    label: { ar: "ذوبان", en: "Dissolve" },
    description: { ar: "ذوبان بين المشهدين", en: "Dissolve transition" },
    category: "effect",
    component: DissolveTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "dreamy-zoom-transition": {
    id: "dreamy-zoom-transition",
    label: { ar: "تقريب حالم", en: "Dreamy Zoom" },
    description: { ar: "تقريب بضبابية حالمة", en: "Dreamy zoom transition" },
    category: "effect",
    component: DreamyZoomTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "film-burn-transition": {
    id: "film-burn-transition",
    label: { ar: "احتراق فيلم", en: "Film Burn" },
    description: { ar: "تأثير احتراق شريط السينما", en: "Film burn transition" },
    category: "effect",
    component: FilmBurnTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "iris-transition": {
    id: "iris-transition",
    label: { ar: "عدسة دائرية", en: "Iris" },
    description: { ar: "فتحة عدسة الكاميرا", en: "Iris circle transition" },
    category: "effect",
    component: IrisTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "linear-blur-transition": {
    id: "linear-blur-transition",
    label: { ar: "ضباب خطي", en: "Linear Blur" },
    description: { ar: "تداخل بضبابية خطية", en: "Linear blur transition" },
    category: "effect",
    component: LinearBlurTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "push-cut-transition": {
    id: "push-cut-transition",
    label: { ar: "دفع المشهد", en: "Push Cut" },
    description: { ar: "دفع المشهد بقوة", en: "Push cut transition" },
    category: "effect",
    component: PushCutTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "ripple-transition": {
    id: "ripple-transition",
    label: { ar: "تموجات", en: "Ripple" },
    description: { ar: "تأثير قطرة الماء", en: "Ripple transition" },
    category: "effect",
    component: RippleTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "swap-transition": {
    id: "swap-transition",
    label: { ar: "تبديل 3D", en: "Swap 3D" },
    description: { ar: "تبديل المشاهد بخاصية 3D", en: "3D Swap transition" },
    category: "effect",
    component: SwapTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "zoom-blur-transition": {
    id: "zoom-blur-transition",
    label: { ar: "تقريب ضبابي", en: "Zoom Blur" },
    description: { ar: "تقريب بضبابية دائرية", en: "Zoom blur transition" },
    category: "effect",
    component: ZoomBlurTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "zoom-in-out-transition": {
    id: "zoom-in-out-transition",
    label: { ar: "تقريب وإبعاد", en: "Zoom In Out" },
    description: { ar: "تقريب للمشهد الأول وإبعاد للثاني", en: "Zoom in out transition" },
    category: "effect",
    component: ZoomInOutTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "book-flip-transition": {
    id: "book-flip-transition",
    label: { ar: "قلب الصفحة", en: "Book Flip" },
    description: { ar: "تقليب مثل صفحة الكتاب", en: "Book flip transition" },
    category: "effect",
    component: BookFlipTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  },
  "animated-text-element": {
    id: "animated-text-element",
    label: { ar: "نصوص تفاعلية الشامل", en: "Animated Text" },
    description: { ar: "كبسولة التحكم الذكي بتأثيرات النصوص (التشويش، الظهور المتدرج، إلخ)", en: "Smart wrapper for all AnimatedText bits (glitch, fade, etc.)" },
    category: "text",
    component: AnimatedTextWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "typewriter-element": {
    id: "typewriter-element",
    label: { ar: "الآلة الكاتبة الشامل", en: "TypeWriter" },
    description: { ar: "كبسولة التحكم بتأثيرات الآلة الكاتبة وواجهة الأوامر", en: "Smart wrapper for all TypeWriter bits (CLI, multi-text, errors)" },
    category: "text",
    component: TypeWriterWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "codeblock-element": {
    id: "codeblock-element",
    label: { ar: "الأكواد البرمجية", en: "Code Block" },
    description: { ar: "كبسولة عرض الأكواد الملونة", en: "CodeBlock syntax highlighting with animation" },
    category: "ui-block",
    component: CodeBlockWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "matrixrain-element": {
    id: "matrixrain-element",
    label: { ar: "الماتريكس", en: "Matrix Rain" },
    description: { ar: "تأثير سقوط الماتريكس الرقمي", en: "Matrix digital rain effect" },
    category: "overlay",
    component: MatrixRainWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "animatedcounter-element": {
    id: "animatedcounter-element",
    label: { ar: "العداد الرقمي", en: "Animated Counter" },
    description: { ar: "عداد أرقام متحرك", en: "Animated number counter" },
    category: "ui-block",
    component: AnimatedCounterWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "scrollingimages-element": {
    id: "scrollingimages-element",
    label: { ar: "التمرير اللانهائي", en: "Scrolling Images" },
    description: { ar: "تمرير لا نهائي لمجموعة من الصور", en: "Infinite scrolling images" },
    category: "composition",
    component: ScrollingImagesWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "particlesystem-element": {
    id: "particlesystem-element",
    label: { ar: "نظام الجزيئات (Particles)", en: "Particle System" },
    description: { ar: "كبسولة التحكم الذكي بالتأثيرات الفيزيائية (ثلج، نار، يراعات)", en: "Smart wrapper for particle effects (snow, fireflies, burst)" },
    category: "overlay",
    component: ParticleSystemWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "scene3d-element": {
    id: "scene3d-element",
    label: { ar: "المشاهد ثلاثية الأبعاد (Scene 3D)", en: "Scene 3D" },
    description: { ar: "نظام بناء عوالم وكاميرات ثلاثية الأبعاد", en: "3D Scene engine for spatial camera control" },
    category: "composition",
    component: Scene3DWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "staggeredmotion-element": {
    id: "staggeredmotion-element",
    label: { ar: "الحركة المتتالية الشامل", en: "Staggered Motion" },
    description: { ar: "كبسولة تأثيرات الظهور المتتالي للبطاقات والقوائم", en: "Smart wrapper for staggered appearances (card stack, list reveal)" },
    category: "composition",
    component: StaggeredMotionWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  },
  "gradient-element": {
    id: "gradient-element",
    label: { ar: "التدرج اللوني (Gradient)", en: "Gradient Transition" },
    description: { ar: "انتقال أو خلفية بتدرجات لونية حركية", en: "Dynamic gradient transition or background" },
    category: "overlay",
    component: GradientWrapper,
    defaultDurationFrames: 120,
    schema: {},
    defaults: {}
  }
};
