import type { TemplateEntry } from "./types";
import { FadeTransition } from "../templates/effects/FadeTransition";

export const TEMPLATE_REGISTRY: Record<string, TemplateEntry> = {
  "fade-transition": {
    id: "fade-transition",
    label: { ar: "انتقال التلاشي", en: "Fade Transition" },
    description: { ar: "تأثير تلاشي سلس بين الألوان", en: "Smooth fade between colors" },
    category: "effect",
    component: FadeTransition,
    defaultDurationFrames: 90,
    schema: {},
    defaults: {}
  }
};
