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
  }
};
