/**
 * planner/cost-estimator.ts — Lightweight Renderer & Node Cost Modeling.
 * S28-R12: Deterministic compute cost, startup overhead, and memory classification.
 * 
 * Baselines derived from S28-R09/R10/R11 measurements:
 *   - CanvasRendererAdapter: sub-second lightweight rasterization, low memory footprint.
 *   - RemotionRendererAdapter: Webpack bundling, Chromium headless launch, higher memory footprint.
 *   - MasterCompositor: subprocess stream assembly, medium memory footprint.
 */

import {
  type CostProfile,
  type MemoryClass,
  type RenderNode,
  type RenderExecutionProfile,
} from "../contracts/render-graph";
import { CANVAS_RENDERER_ID, REMOTION_RENDERER_ID } from "../contracts/renderer";

export const CANVAS_COST_PROFILE: CostProfile = {
  relativeComputeCost: 1.0,
  startupOverheadMs: 50,
  memoryClass: "low",
  expectedExecutionWeight: 1,
};

export const REMOTION_COST_PROFILE: CostProfile = {
  relativeComputeCost: 4.5,
  startupOverheadMs: 1200,
  memoryClass: "medium",
  expectedExecutionWeight: 4,
};

export const MASTER_COMPOSITOR_COST_PROFILE: CostProfile = {
  relativeComputeCost: 2.0,
  startupOverheadMs: 100,
  memoryClass: "medium",
  expectedExecutionWeight: 2,
};

export const DEFAULT_COST_PROFILE: CostProfile = {
  relativeComputeCost: 3.0,
  startupOverheadMs: 500,
  memoryClass: "medium",
  expectedExecutionWeight: 3,
};

/**
 * Returns the estimated cost profile for a given renderer ID.
 */
export function getRendererCostProfile(rendererId?: string): CostProfile {
  if (!rendererId) return DEFAULT_COST_PROFILE;
  if (rendererId === CANVAS_RENDERER_ID) return CANVAS_COST_PROFILE;
  if (rendererId === REMOTION_RENDERER_ID) return REMOTION_COST_PROFILE;
  if (rendererId === "master-compositor") return MASTER_COMPOSITOR_COST_PROFILE;
  return DEFAULT_COST_PROFILE;
}

/**
 * Constructs a full RenderExecutionProfile for a node.
 */
export function createExecutionProfile(
  rendererId: string | undefined,
  durationFrames: number
): RenderExecutionProfile {
  const baseCost = getRendererCostProfile(rendererId);
  const seconds = Math.max(1, durationFrames / 30);
  const weight = Math.max(1, Math.round(seconds * baseCost.relativeComputeCost));

  return {
    costProfile: baseCost,
    memoryClass: baseCost.memoryClass,
    expectedWeight: weight,
    timeoutMs: Math.max(10000, Math.round(seconds * 15000 + baseCost.startupOverheadMs)),
    preferredConcurrency: baseCost.memoryClass === "low" ? 4 : 2,
  };
}

/**
 * Calculates the total estimated cost of all nodes in a plan.
 */
export function estimateTotalPlanCost(nodes: Iterable<RenderNode>): number {
  let totalCost = 0;
  for (const node of nodes) {
    const cost = node.preferredExecutionProfile.costProfile;
    const durSec = node.timeRange.durationFrames / 30;
    const nodeCost = durSec * cost.relativeComputeCost + cost.startupOverheadMs / 1000;
    totalCost += nodeCost;
  }
  return Number(totalCost.toFixed(3));
}
