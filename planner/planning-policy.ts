/**
 * planner/planning-policy.ts — Capability-Based Renderer Resolution & Fallback Policy.
 * S28-R12: Resolves compatible renderers deterministically via the RendererRegistry.
 * 
 * Invariants:
 *   - Zero hardcoded engine branching: renderer selection is 100% capability-driven.
 *   - Capability correctness comes first: an incompatible renderer is NEVER chosen.
 *   - Deterministic tie-breaking: cost tolerance -> priority -> capability count -> id.
 *   - Explicit fallback: preferred renderer fallback only if fully compatible.
 *   - Fail-closed: missing capability -> NO_COMPATIBLE_RENDERER / PLAN_UNRESOLVABLE.
 */

import {
  type RendererRegistry,
  type RendererAdapter,
  type CanonicalRendererCapability,
  normalizeCapability,
} from "../contracts/renderer";
import {
  type PlanningPolicy,
  type RenderPlanningErrorCode,
  RenderPlanningError,
} from "../contracts/render-graph";
import { getRendererCostProfile } from "./cost-estimator";

export interface ResolvedRendererResult {
  ok: boolean;
  adapter?: RendererAdapter;
  fallbacks?: RendererAdapter[];
  error?: {
    code: RenderPlanningErrorCode;
    message: string;
    details: Record<string, unknown>;
  };
}

/**
 * Resolves the most suitable compatible renderer for a node based on declared capabilities and policy.
 */
export function resolveCompatibleRenderer(params: {
  nodeId: string;
  requiredCapabilities: Iterable<string>;
  policy: PlanningPolicy;
  registry: RendererRegistry;
}): ResolvedRendererResult {
  const normRequired: CanonicalRendererCapability[] = [];
  for (const cap of params.requiredCapabilities) {
    const norm = normalizeCapability(cap);
    if (!normRequired.includes(norm)) {
      normRequired.push(norm);
    }
  }

  const allAdapters = params.registry.list();
  if (allAdapters.length === 0) {
    return {
      ok: false,
      error: {
        code: "NO_COMPATIBLE_RENDERER",
        message: `No renderers are registered in the RendererRegistry for node '${params.nodeId}'.`,
        details: {
          nodeId: params.nodeId,
          requiredCapabilities: normRequired,
          registeredRenderers: [],
        },
      },
    };
  }

  const compatible: RendererAdapter[] = [];
  const rejections: Array<{
    rendererId: string;
    missingCapabilities: CanonicalRendererCapability[];
  }> = [];

  for (const adapter of allAdapters) {
    const caps = adapter.capabilities();
    const missing = caps.getMissing(normRequired);
    if (missing.length === 0) {
      compatible.push(adapter);
    } else {
      rejections.push({
        rendererId: adapter.id,
        missingCapabilities: missing,
      });
    }
  }

  if (compatible.length === 0) {
    return {
      ok: false,
      error: {
        code: "NO_COMPATIBLE_RENDERER",
        message: `NO_COMPATIBLE_RENDERER: No registered renderer satisfies all required capabilities for node '${params.nodeId}': [${normRequired.join(", ")}].`,
        details: {
          nodeId: params.nodeId,
          requiredCapabilities: normRequired,
          rejections,
        },
      },
    };
  }

  // 1. Check if preferred renderer is requested
  const prefId = params.policy.preferredRendererId;
  if (prefId) {
    const preferredCandidate = compatible.find((a) => a.id === prefId);
    if (preferredCandidate) {
      const otherFallbacks = compatible.filter((a) => a.id !== prefId);
      return {
        ok: true,
        adapter: preferredCandidate,
        fallbacks: otherFallbacks,
      };
    }

    if (params.policy.allowFallback === false) {
      return {
        ok: false,
        error: {
          code: "QUALITY_REQUIREMENT_UNSATISFIED",
          message: `Preferred renderer '${prefId}' is not compatible for node '${params.nodeId}' and fallback is disabled.`,
          details: {
            nodeId: params.nodeId,
            preferredRendererId: prefId,
            requiredCapabilities: normRequired,
            rejections,
          },
        },
      };
    }
  }

  // 2. Deterministic ranking across compatible renderers
  compatible.sort((a, b) => {
    // If minimizing cost or balanced: lower relative compute cost preferred
    if (params.policy.costTolerance === "minimize_cost" || params.policy.costTolerance === "balanced") {
      const costA = getRendererCostProfile(a.id).relativeComputeCost;
      const costB = getRendererCostProfile(b.id).relativeComputeCost;
      if (costA !== costB) return costA - costB;
    }

    // Priority descending
    const prioA = a.priority ?? 0;
    const prioB = b.priority ?? 0;
    if (prioA !== prioB) return prioB - prioA;

    // Capability count descending
    const capsA = a.capabilities().toArray().length;
    const capsB = b.capabilities().toArray().length;
    if (capsA !== capsB) return capsB - capsA;

    // Lexicographical ID ascending
    return a.id.localeCompare(b.id);
  });

  return {
    ok: true,
    adapter: compatible[0],
    fallbacks: compatible.slice(1),
  };
}
