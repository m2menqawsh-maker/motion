# Render Planning Policy & Cost Optimization Model

**Milestone**: S28-R12 (Multi-Engine RenderGraph & Render Planner)  
**Status**: VERIFIED PASS  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Authority**: `planner/planning-policy.ts` & `planner/cost-estimator.ts`

---

## 1. Planning Policy Taxonomy

The `PlanningPolicy` contract governs how candidate renderers are selected and how target quality affects the output:

```typescript
export interface PlanningPolicy {
  targetQuality: "preview" | "draft" | "production" | "final";
  preferredRendererId?: string;
  costTolerance: "minimize_cost" | "balanced" | "maximum_quality";
  allowFallback: boolean;
  enableDecomposition: boolean;
  maxParallelism?: number;
  costBudget?: number;
}
```

---

## 2. Capability Correctness Invariant

### Capability Correctness is Absolute:
1. Under NO circumstances is an incompatible renderer assigned to a node.
2. A renderer must satisfy 100% of the node's required canonical capabilities (`hasAll(requiredCapabilities) === true`).
3. If no registered renderer supports the required capabilities:
   $$\text{Missing Capability} \implies \text{NO\_COMPATIBLE\_RENDERER (Fail-Closed)}$$
   Silent capability degradation or fake feature approximation is strictly forbidden.

---

## 3. Renderer Assignment & Tie-Breaking

When multiple registered engines satisfy 100% of the required capabilities (e.g. for a 2D title card supported by both `CanvasRendererAdapter` and `RemotionRendererAdapter`), the engine is selected based on policy:

```text
1. Preferred Renderer:
   If preferredRendererId is set and compatible, select it immediately.

2. Cost Tolerance Filtering:
   If policy is 'minimize_cost' or 'balanced':
     Sort compatible candidates by relativeComputeCost ASCENDING.
     (Canvas relative compute cost = 1.0 vs Remotion = 4.5).
     Result: Canvas is chosen for lightweight 2D scenes.

3. Priority Tie-Breaker:
   Sort by adapter priority DESCENDING.

4. Capability Breadth:
   Sort by total number of supported capabilities DESCENDING.

5. Lexicographical ID:
   Sort by adapter.id ASCENDING (deterministic guarantee).
```

---

## 4. Cost Profile Specifications

Baselines derived from physical execution benchmarks recorded in milestones S28-R09, R10, and R11:

| Engine | Relative Compute Cost | Startup Overhead | Memory Class | Typical Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **CanvasRendererAdapter** | $1.0\times$ | $50\text{ ms}$ | `low` | 2D vector text, stat cards, shapes, rapid graphics |
| **RemotionRendererAdapter** | $4.5\times$ | $1200\text{ ms}$ | `medium` | Heavy video clips, complex typography, multi-layer audio |
| **MasterCompositor** | $2.0\times$ | $100\text{ ms}$ | `medium` | Final stream concatenation, cross-fades, audio ducking |

### Node Estimated Cost Formula:
$$\text{Cost} = \left(\frac{\text{durationFrames}}{30} \times \text{relativeComputeCost}\right) + \frac{\text{startupOverheadMs}}{1000}$$

---

## 5. Fallback Policy

```text
Preferred Renderer Requested
        │
        ▼
Is Preferred Renderer Compatible?
  ├── YES ──> Select Preferred Renderer
  └── NO
        │
        ▼
Is allowFallback === true?
  ├── YES ──> Fall back to next fully compatible renderer in registry
  └── NO  ──> Fail Closed with QUALITY_REQUIREMENT_UNSATISFIED
```
