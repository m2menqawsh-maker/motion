import React from "react";
import { EFFECT_COMPONENTS } from "../templates/effects/engine-bridge";
import {
  SEMANTIC_EFFECTS_CATALOG,
  EffectKind,
  EffectSemanticDefinition,
  isKnownEffect as semanticIsKnownEffect,
  isExecutableEffect as semanticIsExecutableEffect,
  getExecutableEffectIds as semanticGetExecutableEffectIds,
  EFFECT_IDS as SEMANTIC_EFFECT_IDS,
} from "../contracts/effects";

export type { EffectKind } from "../contracts/effects";

export interface EffectRuntimeEntry {
  id: string;
  kind: EffectKind;
  paramsSchema: any;
  component?: React.ComponentType<any>;
  sourcePath?: string;
  reason?: string;
}

export const EFFECTS_RUNTIME: Record<string, EffectRuntimeEntry> = {};

for (const [id, semantic] of Object.entries(SEMANTIC_EFFECTS_CATALOG)) {
  const component = semantic.executable ? EFFECT_COMPONENTS[id] : undefined;
  EFFECTS_RUNTIME[id] = {
    id: semantic.id,
    kind: semantic.kind,
    paramsSchema: semantic.paramsSchema,
    component,
    sourcePath: semantic.sourcePath,
    reason: semantic.reason,
  };
}

export const EFFECT_IDS = SEMANTIC_EFFECT_IDS;

export function isKnownEffect(effectId: string): boolean {
  return semanticIsKnownEffect(effectId);
}

export function isExecutableEffect(effectId: string): boolean {
  if (typeof effectId !== "string" || !effectId) return false;
  const entry = EFFECTS_RUNTIME[effectId];
  return Boolean(entry && entry.component);
}

export function getExecutableEffectIds(): string[] {
  return EFFECT_IDS.filter((id) => Boolean(EFFECTS_RUNTIME[id]?.component));
}
